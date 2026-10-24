"""Run the bounded B1 soft-code pilot on a new source-disjoint manifest.

The detector functions in ``audio_watermark.b1_soft`` receive only received
audio and a selector/configuration.  Expected messages are carried here solely
as post-detection evaluation labels.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
import time
from dataclasses import replace
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from app.public_config import build_embedding_config, load_public_selector  # noqa: E402
from audio_watermark.b1 import embed_watermark_b1  # noqa: E402
from audio_watermark.codec_selector import CodecAwareCarrierSelector  # noqa: E402
from audio_watermark.codec_stability import map_from_dict  # noqa: E402
from audio_watermark.metrics import bit_error_rate, signal_snr  # noqa: E402
from audio_watermark.b1_soft import (  # noqa: E402
    decode_b1_soft_detection,
    detect_watermark_b1_soft,
    encode_soft_payload,
)
from audio_watermark.v3_p0_r1 import calibrate_presence_threshold, classify_presence  # noqa: E402
from v3_p0_channel_audit import _ffmpeg_mp3_roundtrip  # noqa: E402
from v3_p0_r1_experiment import load_source, _log_spectral_distortion  # noqa: E402


STRENGTHS = (0.96, 1.28, 1.60)
MESSAGE_SEEDS = (101, 202)
SAMPLE_RATE = 48_000
MANIFEST_DEFAULT = ROOT / "configs" / "v3_b1_soft_pilot_manifest.json"


def _message(seed: int) -> tuple[int, ...]:
    generator = np.random.default_rng(seed)
    return tuple(int(value) for value in generator.integers(0, 2, size=8))


def _wrap_repeat4(payload: tuple[int, ...]) -> tuple[int, ...]:
    return tuple(value for value in payload for _ in range(4))


def _unwrap_repeat4(payload: tuple[int, ...]) -> tuple[int, ...]:
    if len(payload) != 32:
        raise ValueError("repeat4 wrapper requires 32 physical bits")
    return tuple(int(sum(payload[index : index + 4]) >= 2) for index in range(0, 32, 4))


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


def _detect(
    audio: np.ndarray,
    config: object,
    selector: object,
    method: str,
) -> tuple[tuple[int, ...], tuple[int, ...], float, float]:
    """Return decoded payload, hard physical bits, presence, runtime."""

    started = time.perf_counter()
    detection = detect_watermark_b1_soft(audio, config, selector)
    decoded = decode_b1_soft_detection(detection)
    runtime = time.perf_counter() - started
    if method == "repeat4":
        payload = _unwrap_repeat4(detection.hard_physical_bits)
        presence = float(np.mean(np.abs(detection.physical_statistics)))
    elif method == "soft_code":
        payload = decoded.payload_bits
        presence = float(decoded.presence_score)
    else:
        raise ValueError(f"unknown method: {method}")
    return payload, detection.hard_physical_bits, presence, runtime


def _row(
    *,
    record: dict[str, object],
    method: str,
    strength: float,
    message_id: str,
    role: str,
    condition: str,
    expected: tuple[int, ...] | None,
    decoded: tuple[int, ...],
    hard_physical: tuple[int, ...],
    expected_physical: tuple[int, ...] | None,
    presence: float,
    threshold: float | None,
    clean: np.ndarray | None,
    marked: np.ndarray | None,
    received: np.ndarray | None,
    embed_seconds: float,
    detect_seconds: float,
) -> dict[str, object]:
    accepted = classify_presence(presence, threshold) if threshold is not None else None
    exact = int(expected == decoded) if expected is not None else None
    return {
        "method": method,
        "strength": strength,
        "record_id": record["record_id"],
        "category": record["category"],
        "split": record["split"],
        "source_group_id": record["source_group_id"],
        "message_id": message_id,
        "sample_role": role,
        "condition": condition,
        "effective_payload_bits": 8,
        "expected_payload": "" if expected is None else "".join(map(str, expected)),
        "decoded_payload": "".join(map(str, decoded)),
        "physical_raw_ber": (
            float(np.mean(np.asarray(hard_physical) != np.asarray(expected_physical)))
            if expected_physical is not None
            else "NOT_APPLICABLE"
        ),
        "logical_ber": (
            bit_error_rate(expected, decoded) if expected is not None else "NOT_APPLICABLE"
        ),
        "exact_message_recovery": exact if exact is not None else "NOT_APPLICABLE",
        "presence_score": presence,
        "presence_threshold": threshold if threshold is not None else "CALIBRATION_PENDING",
        "presence_accepted": (
            int(accepted) if accepted is not None else "CALIBRATION_PENDING"
        ),
        "wrong_message_acceptance": (
            int(bool(accepted) and exact == 0)
            if accepted is not None and exact is not None
            else "NOT_APPLICABLE"
        ),
        "snr_db": signal_snr(clean, marked) if clean is not None and marked is not None else "NOT_APPLICABLE",
        "spectral_distortion_rms_db": (
            _log_spectral_distortion(clean, marked)
            if clean is not None and marked is not None
            else "NOT_APPLICABLE"
        ),
        "mp3_fidelity_snr_db": (
            signal_snr(marked, received)
            if marked is not None and received is not None and condition == "mp3_128k"
            else "NOT_APPLICABLE"
        ),
        "embed_runtime_seconds": embed_seconds,
        "detect_runtime_seconds": detect_seconds,
        "detector_expected_payload_used": False,
    }


def _write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    fields: list[str] = []
    seen: set[str] = set()
    for row in rows:
        for key in row:
            if key not in seen:
                fields.append(key)
                seen.add(key)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def run(manifest_path: Path, output_dir: Path) -> dict[str, object]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("status") != "FROZEN" or manifest.get("manifest_version") != "V3_B1_SOFT_CODE_PILOT_V1":
        raise ValueError("pilot requires the frozen V3_B1_SOFT_CODE_PILOT_V1 manifest")
    records = list(manifest["records"])
    if len(records) != 60:
        raise ValueError("pilot requires exactly 60 manifest records")
    dataset_root = Path(str(manifest["dataset_root"]))
    base_config = build_embedding_config()
    selector = load_public_selector()
    wrong_selector = _wrong_selector()
    messages = {f"seed_{seed}": _message(seed) for seed in MESSAGE_SEEDS}
    output_dir.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, object]] = []
    clean_cache: dict[str, np.ndarray] = {}
    clean_mp3_cache: dict[str, np.ndarray] = {}

    for index, record in enumerate(records, start=1):
        record_id = str(record["record_id"])
        clean = clean_cache.setdefault(record_id, load_source(record, dataset_root))
        clean_mp3_cache.setdefault(
            record_id, _fit_length(_ffmpeg_mp3_roundtrip(clean, SAMPLE_RATE), clean.size)
        )
        clean_mp3 = clean_mp3_cache[record_id]
        for strength in STRENGTHS:
            config = replace(base_config, strength=strength)
            for message_id, logical_payload in messages.items():
                physical_payloads = {
                    "repeat4": _wrap_repeat4(logical_payload),
                    "soft_code": tuple(int(value) for value in encode_soft_payload(logical_payload)),
                }
                for method, physical_payload in physical_payloads.items():
                    started = time.perf_counter()
                    marked = embed_watermark_b1(clean, physical_payload, config, selector)
                    embed_seconds = time.perf_counter() - started
                    received = _fit_length(
                        _ffmpeg_mp3_roundtrip(marked, SAMPLE_RATE), clean.size
                    )
                    for condition, attacked in (
                        ("marked_no_attack", marked),
                        ("mp3_128k", received),
                    ):
                        decoded, hard_physical, presence, detect_seconds = _detect(
                            attacked, config, selector, method
                        )
                        rows.append(
                            _row(
                                record=record,
                                method=method,
                                strength=strength,
                                message_id=message_id,
                                role="positive",
                                condition=condition,
                                expected=logical_payload,
                                decoded=decoded,
                                hard_physical=hard_physical,
                                expected_physical=physical_payload,
                                presence=presence,
                                threshold=None,
                                clean=clean,
                                marked=marked,
                                received=received,
                                embed_seconds=embed_seconds,
                                detect_seconds=detect_seconds,
                            )
                        )
                    wrong_decoded, wrong_hard, wrong_presence, wrong_runtime = _detect(
                        received, config, wrong_selector, method
                    )
                    rows.append(
                        _row(
                            record=record,
                            method=method,
                            strength=strength,
                            message_id=message_id,
                            role="negative",
                            condition="wrong_key_mp3",
                            expected=None,
                            decoded=wrong_decoded,
                            hard_physical=wrong_hard,
                            expected_physical=None,
                            presence=wrong_presence,
                            threshold=None,
                            clean=None,
                            marked=None,
                            received=None,
                            embed_seconds=embed_seconds,
                            detect_seconds=wrong_runtime,
                        )
                    )
            for method in ("repeat4", "soft_code"):
                for condition, attacked in (("clean", clean), ("clean_mp3", clean_mp3)):
                    decoded, hard_physical, presence, detect_seconds = _detect(
                        attacked, config, selector, method
                    )
                    rows.append(
                        _row(
                            record=record,
                            method=method,
                            strength=strength,
                            message_id="none",
                            role="negative",
                            condition=condition,
                            expected=None,
                            decoded=decoded,
                            hard_physical=hard_physical,
                            expected_physical=None,
                            presence=presence,
                            threshold=None,
                            clean=None,
                            marked=None,
                            received=None,
                            embed_seconds=0.0,
                            detect_seconds=detect_seconds,
                        )
                    )
        if index % 5 == 0:
            print(f"processed {index}/{len(records)} source recordings", flush=True)

    calibrations: dict[str, dict[str, float | int]] = {}
    for method in ("repeat4", "soft_code"):
        for strength in STRENGTHS:
            matching = [
                row
                for row in rows
                if row["method"] == method and float(row["strength"]) == strength
            ]
            positive = [
                float(row["presence_score"])
                for row in matching
                if row["split"] == "dev" and row["sample_role"] == "positive"
            ]
            negative = [
                float(row["presence_score"])
                for row in matching
                if row["split"] == "dev" and row["sample_role"] == "negative"
            ]
            calibration = calibrate_presence_threshold(
                positive_scores=positive,
                negative_scores=negative,
            )
            key = f"{method}@{strength:.2f}"
            calibrations[key] = {
                "threshold": calibration.threshold,
                "positive_detection_rate": calibration.positive_detection_rate,
                "false_positive_rate": calibration.false_positive_rate,
                "positive_count": calibration.positive_count,
                "negative_count": calibration.negative_count,
            }
            for row in matching:
                threshold = calibration.threshold
                row["presence_threshold"] = threshold
                row["presence_accepted"] = int(
                    classify_presence(float(row["presence_score"]), threshold)
                )
                if row["sample_role"] == "positive":
                    exact = row["exact_message_recovery"]
                    row["wrong_message_acceptance"] = int(
                        bool(row["presence_accepted"]) and exact == 0
                    )

    _write_csv(output_dir / "V3_B1_SOFT_CODE_PILOT.csv", rows)
    (output_dir / "V3_B1_SOFT_CODE_CALIBRATION.json").write_text(
        json.dumps(calibrations, indent=2, sort_keys=True), encoding="utf-8"
    )
    summary = {
        "manifest": str(manifest_path),
        "manifest_sha256": _sha256(manifest_path),
        "records": len(records),
        "strengths": list(STRENGTHS),
        "message_seeds": list(MESSAGE_SEEDS),
        "messages": {key: list(value) for key, value in messages.items()},
        "calibrations": calibrations,
        "row_count": len(rows),
        "provenance": "new source-disjoint local MUSAN manifest; no audio copied to repository",
    }
    (output_dir / "V3_B1_SOFT_CODE_PILOT_SUMMARY.json").write_text(
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
    print(json.dumps(run(args.manifest, args.output_dir), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
