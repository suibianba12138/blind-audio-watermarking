"""Run the source-disjoint V3-P0-R1 real-audio paired experiment.

The script never copies source recordings into the repository.  It reads the
frozen metadata manifest, prepares each source using the public demo's fixed
6-second/48-kHz policy, and writes only tabular/JSON diagnostics to the
requested result directory.

The frozen B1 path is wrapped as eight logical bits repeated four times over
its existing 32 physical payload positions.  This is reported as an 8-bit
effective-capacity comparison; it is not a claim about arbitrary 32-bit
message recovery.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
import time
from dataclasses import replace
from pathlib import Path
from typing import Iterable, Sequence

import numpy as np
from scipy.io import wavfile
from scipy.signal import resample_poly

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from app.public_config import build_embedding_config, load_public_selector  # noqa: E402
from audio_watermark.b1 import detect_watermark_b1, embed_watermark_b1  # noqa: E402
from audio_watermark.carrier import carrier_sides  # noqa: E402
from audio_watermark.course_v2 import identity_codeword  # noqa: E402
from audio_watermark.detect import _detection_statistic  # noqa: E402
from audio_watermark.framing import frame_audio  # noqa: E402
from audio_watermark.metrics import bit_error_rate, signal_snr  # noqa: E402
from audio_watermark.transform import real_fft  # noqa: E402
from audio_watermark.v3_p0 import (  # noqa: E402
    SpreadSpectrumConfig,
    detect_spread_spectrum,
    embed_spread_spectrum,
)
from audio_watermark.v3_p0_r1 import (  # noqa: E402
    calibrate_presence_threshold,
    classify_presence,
    presence_score,
)
from v3_p0_channel_audit import _ffmpeg_mp3_roundtrip  # noqa: E402


MANIFEST_DEFAULT = ROOT / "configs" / "v3_p0_r1_real_audio_manifest.json"
SAMPLE_RATE = 48_000
BLOCK_SECONDS = 6
CANDIDATE_STRENGTH = 0.02
CANDIDATE_SEED = 23
MESSAGE_SEEDS = (7, 23)


def _to_float(values: np.ndarray) -> np.ndarray:
    array = np.asarray(values)
    if np.issubdtype(array.dtype, np.integer):
        info = np.iinfo(array.dtype)
        array = array.astype(np.float64) / float(max(abs(info.min), info.max))
    else:
        array = array.astype(np.float64)
    if array.ndim == 2:
        array = np.mean(array, axis=1)
    if array.ndim != 1 or array.size == 0 or not np.all(np.isfinite(array)):
        raise ValueError("source audio must decode to finite non-empty mono samples")
    return array


def load_source(record: dict[str, object], dataset_root: Path) -> np.ndarray:
    """Load one source with the fixed R1 resample-and-first-6-second policy.

    The public demo additionally rejects files longer than 30 seconds.  That
    upload guard is not applied to an already audited local research source;
    applying it here would incorrectly discard long recordings before taking
    the pre-registered six-second prefix.
    """

    path = dataset_root / str(record["relative_path"])
    rate, values = wavfile.read(path)
    samples = _to_float(values)
    source_rate = int(rate)
    if source_rate != SAMPLE_RATE:
        divisor = math.gcd(source_rate, SAMPLE_RATE)
        samples = resample_poly(
            samples, SAMPLE_RATE // divisor, source_rate // divisor
        ).astype(np.float64)
    target_count = BLOCK_SECONDS * SAMPLE_RATE
    if samples.size >= target_count:
        return samples[:target_count]
    return np.pad(samples, (0, target_count - samples.size))


def _fit_length(values: np.ndarray, length: int) -> np.ndarray:
    values = np.asarray(values, dtype=np.float64)
    if values.size >= length:
        return values[:length]
    return np.pad(values, (0, length - values.size))


def _message(seed: int) -> tuple[int, ...]:
    generator = np.random.default_rng(seed)
    return tuple(int(value) for value in generator.integers(0, 2, size=8))


def _wrap_b1(payload: Sequence[int]) -> tuple[int, ...]:
    values = tuple(int(value) for value in payload)
    if len(values) != 8:
        raise ValueError("the R1 B1 wrapper requires exactly eight logical bits")
    return tuple(value for value in values for _ in range(4))


def _unwrap_b1(payload: Sequence[int]) -> tuple[int, ...]:
    values = tuple(int(value) for value in payload)
    if len(values) != 32:
        raise ValueError("the R1 B1 wrapper requires exactly 32 physical bits")
    return tuple(int(sum(values[index : index + 4]) >= 2) for index in range(0, 32, 4))


def _log_spectral_distortion(clean: np.ndarray, other: np.ndarray) -> float:
    n_fft = 2048
    clean_spec = real_fft(frame_audio(clean, n_fft, n_fft, pad_end=True))
    other_spec = real_fft(frame_audio(other, n_fft, n_fft, pad_end=True))
    clean_log = np.log(np.maximum(np.abs(clean_spec), np.finfo(float).tiny))
    other_log = np.log(np.maximum(np.abs(other_spec), np.finfo(float).tiny))
    delta_db = 20.0 / math.log(10.0) * (other_log - clean_log)
    return float(np.sqrt(np.mean(delta_db * delta_db)))


def _embedded_region_snr(clean: np.ndarray, marked: np.ndarray, frame_count: int) -> float:
    region = min(clean.size, frame_count * 2048)
    return signal_snr(clean[:region], marked[:region])


def _candidate_band_stats(
    spectrum: np.ndarray,
    bins: np.ndarray,
    config: object,
) -> tuple[float, float]:
    frequencies = np.fft.rfftfreq(config.n_fft, 1.0 / config.sample_rate)
    band = (frequencies >= config.candidate_band_hz.low_hz) & (
        frequencies <= config.candidate_band_hz.high_hz
    )
    band_energy = 10.0 * np.log10(
        max(float(np.mean(np.abs(spectrum[band]) ** 2)), np.finfo(float).tiny)
    )
    carrier_energy = 10.0 * np.log10(
        max(float(np.mean(np.abs(spectrum[bins]) ** 2)), np.finfo(float).tiny)
    )
    return band_energy, carrier_energy


def b1_per_bit_rows(
    clean: np.ndarray,
    marked: np.ndarray,
    received: np.ndarray,
    expected_physical: Sequence[int],
    config: object,
    selector: object,
    *,
    record: dict[str, object],
    message_id: str,
    attack: str,
) -> list[dict[str, object]]:
    """Return host/marked/received statistics for each physical B1 bit."""

    clean_spec = real_fft(frame_audio(clean, config.n_fft, config.hop_length, pad_end=True))
    marked_spec = real_fft(frame_audio(marked, config.n_fft, config.hop_length, pad_end=True))
    received_spec = real_fft(frame_audio(received, config.n_fft, config.hop_length, pad_end=True))
    rows: list[dict[str, object]] = []
    for bit_index, expected in enumerate(expected_physical):
        host_repetitions: list[float] = []
        marked_repetitions: list[float] = []
        received_repetitions: list[float] = []
        host_band: list[float] = []
        host_carrier: list[float] = []
        for repetition in range(config.frames_per_bit):
            frame_index = bit_index * config.frames_per_bit + repetition
            group = selector.group_for_frame(frame_index)
            a_bins, b_bins = carrier_sides(group)
            host_stat = _detection_statistic(clean_spec[frame_index], group, config.strength)
            marked_stat = _detection_statistic(marked_spec[frame_index], group, config.strength)
            received_stat = _detection_statistic(received_spec[frame_index], group, config.strength)
            band_energy, carrier_energy = _candidate_band_stats(
                clean_spec[frame_index], np.concatenate((a_bins, b_bins)), config
            )
            host_repetitions.append(float(host_stat))
            marked_repetitions.append(float(marked_stat))
            received_repetitions.append(float(received_stat))
            host_band.append(band_energy)
            host_carrier.append(carrier_energy)
        rows.append(
            {
                "record_id": record["record_id"],
                "category": record["category"],
                "split": record["split"],
                "source_group_id": record["source_group_id"],
                "message_id": message_id,
                "attack": attack,
                "physical_bit": bit_index,
                "expected_physical_bit": int(expected),
                "host_stat_repetitions": json.dumps(host_repetitions),
                "marked_stat_repetitions": json.dumps(marked_repetitions),
                "mp3_stat_repetitions": json.dumps(received_repetitions),
                "host_stat_mean": float(np.mean(host_repetitions)),
                "marked_stat_mean": float(np.mean(marked_repetitions)),
                "mp3_stat_mean": float(np.mean(received_repetitions)),
                "host_boundary_distance": float(abs(np.mean(host_repetitions))),
                "marked_boundary_distance": float(abs(np.mean(marked_repetitions))),
                "mp3_boundary_distance": float(abs(np.mean(received_repetitions))),
                "host_to_marked_flip": int(
                    (np.mean(host_repetitions) >= 0.0)
                    != (np.mean(marked_repetitions) >= 0.0)
                ),
                "marked_to_mp3_flip": int(
                    (np.mean(marked_repetitions) >= 0.0)
                    != (np.mean(received_repetitions) >= 0.0)
                ),
                "host_band_energy_db": float(np.mean(host_band)),
                "host_carrier_energy_db": float(np.mean(host_carrier)),
                "host_low_energy_carrier": int(np.mean(host_carrier) < np.mean(host_band)),
            }
        )
    return rows


def _candidate_row(
    *,
    record: dict[str, object],
    message_id: str,
    attack: str,
    expected: tuple[int, ...] | None,
    decoded: tuple[int, ...],
    score: float,
    threshold: float | None,
    clean: np.ndarray,
    marked: np.ndarray | None,
    received: np.ndarray,
    embed_seconds: float,
    detect_seconds: float,
) -> dict[str, object]:
    accepted = threshold is not None and classify_presence(score, threshold)
    return {
        "method": "keyed_spread_spectrum_local_norm",
        "record_id": record["record_id"],
        "category": record["category"],
        "split": record["split"],
        "source_group_id": record["source_group_id"],
        "message_id": message_id,
        "attack": attack,
        "effective_payload_bits": 8,
        "candidate_strength": CANDIDATE_STRENGTH,
        "decoded_payload": "".join(str(value) for value in decoded),
        "expected_payload": (
            "".join(str(value) for value in expected) if expected is not None else ""
        ),
        "raw_ber": (
            bit_error_rate(expected, decoded) if expected is not None else "NOT_APPLICABLE"
        ),
        "exact_message_recovery": (
            int(expected == decoded) if expected is not None else "NOT_APPLICABLE"
        ),
        "presence_score": score,
        "presence_threshold": threshold if threshold is not None else "CALIBRATION_PENDING",
        "presence_accepted": int(accepted) if threshold is not None else "CALIBRATION_PENDING",
        "snr_db": signal_snr(clean, marked) if marked is not None else "NOT_APPLICABLE",
        "mp3_fidelity_snr_db": signal_snr(marked, received) if marked is not None else "NOT_APPLICABLE",
        "spectral_distortion_rms_db": (
            _log_spectral_distortion(clean, marked) if marked is not None else "NOT_APPLICABLE"
        ),
        "embed_runtime_seconds": embed_seconds,
        "detect_runtime_seconds": detect_seconds,
        "detector_expected_payload_used": False,
    }


def _write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    if not rows:
        return
    fieldnames: list[str] = []
    seen: set[str] = set()
    for row in rows:
        for key in row:
            if key not in seen:
                seen.add(key)
                fieldnames.append(key)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=fieldnames,
            extrasaction="ignore",
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(rows)


def run(manifest_path: Path, output_dir: Path) -> dict[str, object]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    records = list(manifest["records"])
    if manifest.get("status") != "FROZEN" or len(records) != 60:
        raise ValueError("R1 requires the frozen 60-record manifest")
    config = build_embedding_config()
    selector = load_public_selector()
    dataset_root = Path(str(manifest["dataset_root"]))
    candidate_config = SpreadSpectrumConfig(
        payload_bits=8,
        frames_per_bit=16,
        strength=CANDIDATE_STRENGTH,
        sample_rate=SAMPLE_RATE,
        seed=CANDIDATE_SEED,
    )
    wrong_key_config = replace(candidate_config, seed=CANDIDATE_SEED + 1)
    messages = {f"seed_{seed}": _message(seed) for seed in MESSAGE_SEEDS}
    output_dir.mkdir(parents=True, exist_ok=True)

    candidate_rows: list[dict[str, object]] = []
    b1_rows: list[dict[str, object]] = []
    negatives: list[dict[str, object]] = []
    source_cache: dict[str, np.ndarray] = {}
    marked_cache: dict[tuple[str, str, str], tuple[np.ndarray, np.ndarray, float]] = {}

    for index, record in enumerate(records, start=1):
        record_key = str(record["record_id"])
        clean = source_cache.setdefault(record_key, load_source(record, dataset_root))
        clean_mp3 = _fit_length(_ffmpeg_mp3_roundtrip(clean, SAMPLE_RATE), clean.size)
        for message_id, logical_payload in messages.items():
            physical_payload = _wrap_b1(logical_payload)
            started = time.perf_counter()
            b1_marked = embed_watermark_b1(clean, physical_payload, config, selector)
            b1_embed_seconds = time.perf_counter() - started
            b1_mp3 = _fit_length(_ffmpeg_mp3_roundtrip(b1_marked, SAMPLE_RATE), clean.size)
            b1_clean_detection = detect_watermark_b1(clean, config, selector)
            b1_marked_detection = detect_watermark_b1(b1_marked, config, selector)
            b1_mp3_detection = detect_watermark_b1(b1_mp3, config, selector)
            b1_rows.extend(
                b1_per_bit_rows(
                    clean,
                    b1_marked,
                    b1_mp3,
                    physical_payload,
                    config,
                    selector,
                    record=record,
                    message_id=message_id,
                    attack="mp3_128k",
                )
            )
            for attack, detected in (
                ("clean", b1_clean_detection),
                ("marked_no_attack", b1_marked_detection),
                ("mp3_128k", b1_mp3_detection),
            ):
                decoded = _unwrap_b1(detected.payload_bits)
                candidate_rows.append(
                    {
                        "method": "frozen_REAL_TOP32_B1_8bit_wrapper",
                        "record_id": record["record_id"],
                        "category": record["category"],
                        "split": record["split"],
                        "source_group_id": record["source_group_id"],
                        "message_id": message_id,
                        "attack": attack,
                        "effective_payload_bits": 8,
                        "decoded_payload": "".join(str(value) for value in decoded),
                        "expected_payload": "".join(str(value) for value in logical_payload),
                        "raw_ber": bit_error_rate(logical_payload, decoded),
                        "exact_message_recovery": int(decoded == logical_payload),
                        "snr_db": signal_snr(clean, b1_marked),
                        "mp3_fidelity_snr_db": signal_snr(b1_marked, b1_mp3),
                        "spectral_distortion_rms_db": _log_spectral_distortion(clean, b1_marked),
                        "embed_runtime_seconds": b1_embed_seconds,
                        "detector_confidence": detected.confidence,
                        "detector_expected_payload_used": False,
                    }
                )

            started = time.perf_counter()
            candidate_marked = embed_spread_spectrum(clean, logical_payload, candidate_config)
            candidate_embed_seconds = time.perf_counter() - started
            candidate_mp3 = _fit_length(
                _ffmpeg_mp3_roundtrip(candidate_marked, SAMPLE_RATE), clean.size
            )
            marked_cache[(record_key, message_id, "correct")] = (
                candidate_marked,
                candidate_mp3,
                candidate_embed_seconds,
            )
            for attack, received in (
                ("marked_no_attack", candidate_marked),
                ("mp3_128k", candidate_mp3),
            ):
                started = time.perf_counter()
                detection = detect_spread_spectrum(received, candidate_config)
                detect_seconds = time.perf_counter() - started
                candidate_rows.append(
                    _candidate_row(
                        record=record,
                        message_id=message_id,
                        attack=attack,
                        expected=logical_payload,
                        decoded=detection.payload_bits,
                        score=presence_score(detection),
                        threshold=None,
                        clean=clean,
                        marked=candidate_marked,
                        received=received,
                        embed_seconds=candidate_embed_seconds,
                        detect_seconds=detect_seconds,
                    )
                )
            wrong_key_received = candidate_mp3
            started = time.perf_counter()
            wrong_key_detection = detect_spread_spectrum(wrong_key_received, wrong_key_config)
            wrong_key_seconds = time.perf_counter() - started
            negatives.append(
                {
                    "method": "keyed_spread_spectrum_local_norm",
                    "record_id": record["record_id"],
                    "category": record["category"],
                    "split": record["split"],
                    "negative_type": "wrong_key_on_marked_mp3",
                    "message_id": message_id,
                    "presence_score": presence_score(wrong_key_detection),
                    "decoded_payload": "".join(str(value) for value in wrong_key_detection.payload_bits),
                    "detect_runtime_seconds": wrong_key_seconds,
                }
            )
        for attack, received in (("clean", clean), ("clean_mp3_128k", clean_mp3)):
            started = time.perf_counter()
            detection = detect_spread_spectrum(received, candidate_config)
            detect_seconds = time.perf_counter() - started
            negatives.append(
                {
                    "method": "keyed_spread_spectrum_local_norm",
                    "record_id": record["record_id"],
                    "category": record["category"],
                    "split": record["split"],
                    "negative_type": attack,
                    "message_id": "none",
                    "presence_score": presence_score(detection),
                    "decoded_payload": "".join(str(value) for value in detection.payload_bits),
                    "detect_runtime_seconds": detect_seconds,
                }
            )
        if index % 5 == 0:
            print(f"processed {index}/{len(records)} source recordings", flush=True)

    dev_positive = [
        float(row["presence_score"])
        for row in candidate_rows
        if row["method"] == "keyed_spread_spectrum_local_norm"
        and row["split"] == "dev"
        and row["attack"] in ("marked_no_attack", "mp3_128k")
    ]
    dev_negative = [
        float(row["presence_score"])
        for row in negatives
        if row["split"] == "dev"
    ]
    calibration = calibrate_presence_threshold(
        positive_scores=dev_positive,
        negative_scores=dev_negative,
    )
    for row in candidate_rows:
        if row["method"] != "keyed_spread_spectrum_local_norm":
            continue
        score = float(row["presence_score"])
        row["presence_threshold"] = calibration.threshold
        row["presence_accepted"] = int(classify_presence(score, calibration.threshold))
    for row in negatives:
        row["presence_threshold"] = calibration.threshold
        row["presence_accepted"] = int(
            classify_presence(float(row["presence_score"]), calibration.threshold)
        )

    _write_csv(output_dir / "V3_P0_R1_PAIRED_RESULTS.csv", candidate_rows)
    _write_csv(output_dir / "V3_P0_R1_QIM_PER_BIT_STATS.csv", b1_rows)
    _write_csv(output_dir / "V3_P0_R1_NEGATIVE_SCORES.csv", negatives)
    summary = {
        "manifest": str(manifest_path),
        "manifest_sha256": _sha256(manifest_path),
        "sample_rate_hz": SAMPLE_RATE,
        "duration_seconds": BLOCK_SECONDS,
        "messages": {key: list(value) for key, value in messages.items()},
        "candidate_config": {
            "strength": CANDIDATE_STRENGTH,
            "frames_per_bit": candidate_config.frames_per_bit,
            "seed": CANDIDATE_SEED,
            "threshold_source": "development_split_only",
        },
        "calibration": {
            "threshold": calibration.threshold,
            "positive_detection_rate": calibration.positive_detection_rate,
            "false_positive_rate": calibration.false_positive_rate,
            "positive_count": calibration.positive_count,
            "negative_count": calibration.negative_count,
        },
        "row_counts": {
            "paired": len(candidate_rows),
            "qim_per_bit": len(b1_rows),
            "negative": len(negatives),
        },
        "source_recordings": len(records),
        "provenance": "local MUSAN metadata-only source manifest; no audio copied to repository",
    }
    (output_dir / "V3_P0_R1_RESULTS.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8"
    )
    return summary


def _sha256(path: Path) -> str:
    import hashlib

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=MANIFEST_DEFAULT)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    summary = run(args.manifest, args.output_dir)
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
