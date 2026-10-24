"""Run the frozen three-method V3-P1 independent validation.

The script uses one new source-disjoint manifest and two fixed messages per
source. Expected payloads are passed only to the row scorer after blind
detection has returned.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import resource
import sys
import time
from dataclasses import replace
from pathlib import Path
from typing import Sequence

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from app.public_config import build_embedding_config, load_public_selector  # noqa: E402
from audio_watermark.b1 import detect_watermark_b1, embed_watermark_b1  # noqa: E402
from audio_watermark.b1_hard_code import decode_hard_physical_bits, encode_hard_payload  # noqa: E402
from audio_watermark.b1_soft import (  # noqa: E402
    decode_b1_soft_detection,
    detect_watermark_b1_soft,
)
from audio_watermark.metrics import bit_error_rate, signal_snr  # noqa: E402
from audio_watermark.codec_selector import CodecAwareCarrierSelector  # noqa: E402
from audio_watermark.codec_stability import map_from_dict  # noqa: E402
from v3_p0_channel_audit import _ffmpeg_mp3_roundtrip  # noqa: E402
from v3_p0_r1_experiment import load_source, _log_spectral_distortion  # noqa: E402


MANIFEST_DEFAULT = ROOT / "configs" / "v3_p1_independent_manifest.json"
SAMPLE_RATE = 48_000
STRENGTH = 1.60
MESSAGE_SEEDS = (101, 202)
THRESHOLDS = {
    "repeat4": 0.47678591988959035,
    "hard_code": 0.47678591988959035,
    "soft_code": 0.7855073980199624,
}


def _message(seed: int) -> tuple[int, ...]:
    generator = np.random.default_rng(seed)
    return tuple(int(value) for value in generator.integers(0, 2, size=8))


def _wrap_repeat4(payload: Sequence[int]) -> tuple[int, ...]:
    values = tuple(int(value) for value in payload)
    if len(values) != 8:
        raise ValueError("repeat-4 wrapper requires exactly eight logical bits")
    return tuple(value for value in values for _ in range(4))


def _unwrap_repeat4(bits: Sequence[int]) -> tuple[int, ...]:
    values = tuple(int(value) for value in bits)
    if len(values) != 32:
        raise ValueError("repeat-4 decoder requires exactly 32 physical bits")
    return tuple(int(sum(values[index : index + 4]) >= 2) for index in range(0, 32, 4))


def _fit_length(values: np.ndarray, length: int) -> np.ndarray:
    values = np.asarray(values, dtype=np.float64)
    if values.size >= length:
        return values[:length]
    return np.pad(values, (0, length - values.size))


def _wrong_selector() -> object:
    raw = json.loads((ROOT / "configs" / "real_top32_stability_map.json").read_text())
    stability_map = map_from_dict(
        {
            "pool_seed": raw["pool_seed"],
            "codec_names": raw["codec_names"],
            "formula": raw["formula"],
            "entries": raw["entries"],
        }
    )
    return CodecAwareCarrierSelector.from_stability_map(
        stability_map, top_k=32, watermark_seed=8
    )


def _peak_rss_mb() -> float:
    return float(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss) / 1024.0


def _clipping_fields(clean: Sequence[float], marked: Sequence[float]) -> dict[str, object]:
    clean_peak = max(abs(float(value)) for value in clean)
    marked_peak = max(abs(float(value)) for value in marked)
    clean_flag = int(clean_peak > 1.0)
    marked_flag = int(marked_peak > 1.0)
    return {
        "peak_abs_clean": clean_peak,
        "peak_abs_marked": marked_peak,
        "clean_clipping_flag": clean_flag,
        "clipping_flag": marked_flag,
        "introduced_clipping_flag": int(marked_flag and not clean_flag),
    }


def _spectral_or_none(clean: np.ndarray, marked: np.ndarray) -> float:
    return float(_log_spectral_distortion(clean, marked))


def _frozen_payload_bits(detection: object) -> tuple[int, ...]:
    """Read the payload bits field from the frozen DetectionResult contract."""

    return tuple(int(value) for value in detection.payload_bits)


def _detect(
    audio: np.ndarray,
    config: object,
    selector: object,
    method: str,
) -> tuple[tuple[int, ...], tuple[int, ...], float, bool, float]:
    """Return decoded bits, physical bits, score, accepted, and runtime."""

    started = time.perf_counter()
    soft_detection = detect_watermark_b1_soft(audio, config, selector)
    if method == "repeat4":
        frozen_detection = detect_watermark_b1(audio, config, selector)
        physical = _frozen_payload_bits(frozen_detection)
        if physical != soft_detection.hard_physical_bits:
            raise AssertionError("frozen and additive B1 hard decisions disagree")
        decoded = _unwrap_repeat4(physical)
        presence = float(np.mean(np.abs(soft_detection.physical_statistics)))
    elif method == "hard_code":
        physical = soft_detection.hard_physical_bits
        decoded = decode_hard_physical_bits(physical)
        presence = float(np.mean(np.abs(soft_detection.physical_statistics)))
    elif method == "soft_code":
        physical = soft_detection.hard_physical_bits
        decoded = decode_b1_soft_detection(soft_detection).payload_bits
        presence = float(decode_b1_soft_detection(soft_detection).presence_score)
    else:
        raise ValueError(f"unknown method: {method}")
    runtime = time.perf_counter() - started
    accepted = bool(presence >= THRESHOLDS[method])
    return tuple(decoded), tuple(physical), presence, accepted, runtime


def _row(
    *,
    record: dict[str, object],
    method: str,
    message_id: str,
    sample_role: str,
    condition: str,
    expected: tuple[int, ...] | None,
    expected_physical: tuple[int, ...] | None,
    decoded: tuple[int, ...],
    physical: tuple[int, ...],
    presence: float,
    accepted: bool,
    clean: np.ndarray | None,
    marked: np.ndarray | None,
    received: np.ndarray | None,
    embed_seconds: float,
    detect_seconds: float,
) -> dict[str, object]:
    exact = int(expected == decoded) if expected is not None else "NOT_APPLICABLE"
    clipping = (
        _clipping_fields(clean, marked)
        if clean is not None and marked is not None
        else {
            "peak_abs_clean": "NOT_APPLICABLE",
            "peak_abs_marked": "NOT_APPLICABLE",
            "clean_clipping_flag": "NOT_APPLICABLE",
            "clipping_flag": "NOT_APPLICABLE",
            "introduced_clipping_flag": "NOT_APPLICABLE",
        }
    )
    return {
        "method": method,
        "strength": STRENGTH,
        "record_id": record["record_id"],
        "category": record["category"],
        "split": record["split"],
        "source_group_id": record["source_group_id"],
        "message_id": message_id,
        "sample_role": sample_role,
        "condition": condition,
        "effective_payload_bits": 8,
        "expected_payload": "" if expected is None else "".join(map(str, expected)),
        "decoded_payload": "".join(map(str, decoded)),
        "physical_raw_ber": (
            bit_error_rate(expected_physical, physical)
            if expected_physical is not None
            else "NOT_APPLICABLE"
        ),
        "logical_ber": bit_error_rate(expected, decoded) if expected is not None else "NOT_APPLICABLE",
        "exact_message_recovery": exact,
        "presence_score": presence,
        "presence_threshold": THRESHOLDS[method],
        "presence_accepted": int(accepted),
        "wrong_message_acceptance": (
            int(accepted and exact == 0) if expected is not None else "NOT_APPLICABLE"
        ),
        "snr_db": signal_snr(clean, marked) if clean is not None and marked is not None else "NOT_APPLICABLE",
        "spectral_distortion_rms_db": (
            _spectral_or_none(clean, marked)
            if clean is not None and marked is not None
            else "NOT_APPLICABLE"
        ),
        "mp3_fidelity_snr_db": (
            signal_snr(marked, received)
            if marked is not None and received is not None and condition == "mp3_128k"
            else "NOT_APPLICABLE"
        ),
        **clipping,
        "embed_runtime_seconds": embed_seconds,
        "detect_runtime_seconds": detect_seconds,
        "peak_rss_mb": _peak_rss_mb(),
        "detector_expected_payload_used": False,
    }


def _write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    fields: list[str] = []
    seen: set[str] = set()
    for row in rows:
        for field in row:
            if field not in seen:
                fields.append(field)
                seen.add(field)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run(manifest_path: Path, output_dir: Path) -> dict[str, object]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("status") != "FROZEN" or manifest.get("manifest_version") != "V3_P1_INDEPENDENT_VALIDATION_V1":
        raise ValueError("P1 requires the frozen V3_P1_INDEPENDENT_VALIDATION_V1 manifest")
    records = list(manifest["records"])
    if len(records) != 60:
        raise ValueError("P1 requires exactly 60 independent source records")
    dataset_root = Path(str(manifest["dataset_root"]))
    base_config = replace(build_embedding_config(), strength=STRENGTH)
    selector = load_public_selector()
    wrong_selector = _wrong_selector()
    messages = {f"seed_{seed}": _message(seed) for seed in MESSAGE_SEEDS}
    output_dir.mkdir(parents=True, exist_ok=True)
    positive_rows: list[dict[str, object]] = []
    negative_rows: list[dict[str, object]] = []
    clean_cache: dict[str, np.ndarray] = {}
    clean_mp3_cache: dict[str, np.ndarray] = {}

    for index, record in enumerate(records, start=1):
        record_id = str(record["record_id"])
        clean = clean_cache.setdefault(record_id, load_source(record, dataset_root))
        clean_mp3_cache.setdefault(
            record_id, _fit_length(_ffmpeg_mp3_roundtrip(clean, SAMPLE_RATE), clean.size)
        )
        clean_mp3 = clean_mp3_cache[record_id]
        for message_id, logical_payload in messages.items():
            expected = {
                "repeat4": _wrap_repeat4(logical_payload),
                "hard_code": encode_hard_payload(logical_payload),
                "soft_code": encode_hard_payload(logical_payload),
            }
            marked: dict[str, np.ndarray] = {}
            received: dict[str, np.ndarray] = {}
            embed_seconds: dict[str, float] = {}
            for method in ("repeat4", "hard_code", "soft_code"):
                if method == "soft_code" and "hard_code" in marked:
                    marked[method] = marked["hard_code"]
                    received[method] = received["hard_code"]
                    embed_seconds[method] = embed_seconds["hard_code"]
                    continue
                started = time.perf_counter()
                marked[method] = embed_watermark_b1(clean, expected[method], base_config, selector)
                embed_seconds[method] = time.perf_counter() - started
                received[method] = _fit_length(
                    _ffmpeg_mp3_roundtrip(marked[method], SAMPLE_RATE), clean.size
                )
            for method in ("repeat4", "hard_code", "soft_code"):
                for condition, attacked in (
                    ("marked_no_attack", marked[method]),
                    ("mp3_128k", received[method]),
                ):
                    decoded, physical, presence, accepted, detect_seconds = _detect(
                        attacked, base_config, selector, method
                    )
                    positive_rows.append(
                        _row(
                            record=record,
                            method=method,
                            message_id=message_id,
                            sample_role="positive",
                            condition=condition,
                            expected=logical_payload,
                            expected_physical=expected[method],
                            decoded=decoded,
                            physical=physical,
                            presence=presence,
                            accepted=accepted,
                            clean=clean,
                            marked=marked[method],
                            received=received[method],
                            embed_seconds=embed_seconds[method],
                            detect_seconds=detect_seconds,
                        )
                    )
                wrong_decoded, wrong_physical, wrong_presence, wrong_accepted, wrong_runtime = _detect(
                    received[method], base_config, wrong_selector, method
                )
                negative_rows.append(
                    _row(
                        record=record,
                        method=method,
                        message_id=message_id,
                        sample_role="negative",
                        condition="wrong_key_mp3",
                        expected=None,
                        expected_physical=None,
                        decoded=wrong_decoded,
                        physical=wrong_physical,
                        presence=wrong_presence,
                        accepted=wrong_accepted,
                        clean=None,
                        marked=None,
                        received=None,
                        embed_seconds=embed_seconds[method],
                        detect_seconds=wrong_runtime,
                    )
                )
        for method in ("repeat4", "hard_code", "soft_code"):
            for condition, attacked in (("clean", clean), ("clean_mp3", clean_mp3)):
                decoded, physical, presence, accepted, detect_seconds = _detect(
                    attacked, base_config, selector, method
                )
                negative_rows.append(
                    _row(
                        record=record,
                        method=method,
                        message_id="none",
                        sample_role="negative",
                        condition=condition,
                        expected=None,
                        expected_physical=None,
                        decoded=decoded,
                        physical=physical,
                        presence=presence,
                        accepted=accepted,
                        clean=None,
                        marked=None,
                        received=None,
                        embed_seconds=0.0,
                        detect_seconds=detect_seconds,
                    )
                )
        if index % 5 == 0:
            print(f"processed {index}/{len(records)} source recordings", flush=True)

    _write_csv(output_dir / "V3_P1_PAIRED_RESULTS.csv", positive_rows)
    _write_csv(output_dir / "V3_P1_DETECTION_RESULTS.csv", negative_rows)
    summary = {
        "manifest": str(manifest_path),
        "manifest_sha256": _sha256(manifest_path),
        "records": len(records),
        "message_seeds": list(MESSAGE_SEEDS),
        "messages": {key: list(value) for key, value in messages.items()},
        "strength": STRENGTH,
        "thresholds": THRESHOLDS,
        "positive_row_count": len(positive_rows),
        "negative_row_count": len(negative_rows),
        "peak_rss_mb": _peak_rss_mb(),
        "provenance": "new source-disjoint metadata-only manifest; raw audio remains outside repository",
    }
    (output_dir / "V3_P1_SUMMARY.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=MANIFEST_DEFAULT)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(run(args.manifest, args.output_dir), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
