"""Run the finite V3-P2 capacity pilot on the frozen P1 development split."""

from __future__ import annotations

import argparse
import csv
import json
import sys
import time
from collections import defaultdict
from dataclasses import replace
from pathlib import Path
from typing import Iterable

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from app.public_config import build_embedding_config, load_public_selector  # noqa: E402
from audio_watermark.b1 import embed_watermark_b1  # noqa: E402
from audio_watermark.b1_soft import detect_watermark_b1_soft  # noqa: E402
from audio_watermark.b2_capacity import (  # noqa: E402
    decode_soft_capacity,
    encode_capacity_payload,
)
from audio_watermark.metrics import bit_error_rate, signal_snr  # noqa: E402
from audio_watermark.v3_p0_r1 import (  # noqa: E402
    calibrate_presence_threshold,
    classify_presence,
)
from audio_watermark.v3_p2 import assign_development_roles, message_for_seed  # noqa: E402
from v3_p0_channel_audit import _ffmpeg_mp3_roundtrip  # noqa: E402
from v3_p0_r1_experiment import (  # noqa: E402
    _fit_length,
    _log_spectral_distortion,
    load_source,
)
from v3_p1_independent_validation import _clipping_fields, _wrong_selector  # noqa: E402


SAMPLE_RATE = 48_000
STRENGTH = 1.60
MESSAGE_SEEDS = (101, 202)
METHOD_BITS = {"soft8_frozen": 8, "degree2_12": 12, "degree2_16": 16}
FROZEN_8_THRESHOLD = 0.7855073980199624


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


def calibrate_capacity_thresholds(rows: list[dict[str, object]]) -> dict[str, dict[str, object]]:
    """Calibrate candidate thresholds from calibration rows only."""

    result: dict[str, dict[str, object]] = {
        "soft8_frozen": {
            "threshold": FROZEN_8_THRESHOLD,
            "source_role": "P1_FROZEN",
            "positive_count": "NOT_APPLICABLE",
            "negative_count": "NOT_APPLICABLE",
        }
    }
    for method in ("degree2_12", "degree2_16"):
        positives = [
            float(row["presence_score"])
            for row in rows
            if row["method"] == method
            and row["p2_role"] == "calibration"
            and row["sample_role"] == "positive"
            and row["condition"] in ("marked_no_attack", "mp3_128k")
        ]
        negatives = [
            float(row["presence_score"])
            for row in rows
            if row["method"] == method
            and row["p2_role"] == "calibration"
            and row["sample_role"] == "negative"
            and row["condition"] in ("clean_no_watermark", "clean_mp3_no_watermark")
        ]
        calibration = calibrate_presence_threshold(
            positive_scores=positives, negative_scores=negatives
        )
        result[method] = {
            "threshold": calibration.threshold,
            "source_role": "calibration",
            "positive_detection_rate": calibration.positive_detection_rate,
            "false_positive_rate": calibration.false_positive_rate,
            "positive_count": calibration.positive_count,
            "negative_count": calibration.negative_count,
        }
    return result


def _apply_thresholds(
    rows: list[dict[str, object]], thresholds: dict[str, dict[str, object]]
) -> None:
    for row in rows:
        threshold = float(thresholds[str(row["method"])] ["threshold"])
        accepted = int(classify_presence(float(row["presence_score"]), threshold))
        row["presence_threshold"] = threshold
        row["presence_accepted"] = accepted
        if row["sample_role"] == "positive":
            exact = int(row["decoded_exact"])
            row["accepted_exact_recovery"] = int(accepted and exact)
            row["wrong_message_acceptance"] = int(accepted and not exact)
        else:
            row["accepted_exact_recovery"] = "NOT_APPLICABLE"
            row["wrong_message_acceptance"] = "NOT_APPLICABLE"


def aggregate_pilot_metrics(
    rows: list[dict[str, object]], method: str, *, condition: str = "mp3_128k"
) -> dict[str, object]:
    """Aggregate one method/condition on the held-out P2 pilot role."""

    positive = [
        row
        for row in rows
        if row["method"] == method
        and row["p2_role"] == "pilot"
        and row["sample_role"] == "positive"
        and row["condition"] == condition
    ]
    negative = [
        row
        for row in rows
        if row["method"] == method
        and row["p2_role"] == "pilot"
        and row["sample_role"] == "negative"
        and row["condition"] == ("clean_mp3_no_watermark" if condition == "mp3_128k" else "clean_no_watermark")
    ]
    wrong_key = [
        row
        for row in rows
        if row["method"] == method
        and row["p2_role"] == "pilot"
        and row["sample_role"] == "wrong_key_positive"
    ]
    source_positive: dict[str, list[dict[str, object]]] = defaultdict(list)
    source_negative: dict[str, list[dict[str, object]]] = defaultdict(list)
    source_wrong_key: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in positive:
        source_positive[str(row["record_id"])].append(row)
    for row in negative:
        source_negative[str(row["record_id"])].append(row)
    for row in wrong_key:
        source_wrong_key[str(row["record_id"])].append(row)
    return {
        "positive_trials": len(positive),
        "accepted_trials": sum(int(row["presence_accepted"]) for row in positive),
        "unknown_trials": sum(not int(row["presence_accepted"]) for row in positive),
        "exact_recovery_trials": sum(int(row["decoded_exact"]) for row in positive),
        "accepted_exact_recovery_trials": sum(
            int(row.get("accepted_exact_recovery", int(row["presence_accepted"]) and int(row["decoded_exact"])))
            for row in positive
        ),
        "wrong_message_acceptance_trials": sum(int(row["wrong_message_acceptance"]) for row in positive),
        "negative_trials": len(negative),
        "negative_accepted_trials": sum(int(row["presence_accepted"]) for row in negative),
        "wrong_key_trials": len(wrong_key),
        "wrong_key_accepted_trials": sum(int(row["presence_accepted"]) for row in wrong_key),
        "positive_acceptance_rate": (
            float(np.mean([int(row["presence_accepted"]) for row in positive]))
            if positive
            else None
        ),
        "exact_recovery_rate": (
            float(np.mean([int(row["decoded_exact"]) for row in positive])) if positive else None
        ),
        "accepted_exact_recovery_rate": (
            float(
                np.mean(
                    [
                        int(row.get("accepted_exact_recovery", int(row["presence_accepted"]) and int(row["decoded_exact"])))
                        for row in positive
                    ]
                )
            )
            if positive
            else None
        ),
        "negative_fpr": (
            float(np.mean([int(row["presence_accepted"]) for row in negative])) if negative else None
        ),
        "wrong_key_acceptance_rate": (
            float(np.mean([int(row["presence_accepted"]) for row in wrong_key]))
            if wrong_key
            else None
        ),
        "source_recordings": len(source_positive),
        "source_both_messages_exact": sum(
            all(int(row["decoded_exact"]) for row in source_rows)
            for source_rows in source_positive.values()
        ),
        "source_both_messages_accepted_exact": sum(
            all(
                int(row.get("accepted_exact_recovery", int(row["presence_accepted"]) and int(row["decoded_exact"])))
                for row in source_rows
            )
            for source_rows in source_positive.values()
        ),
        "source_any_positive_acceptance": sum(
            any(int(row["presence_accepted"]) for row in source_rows)
            for source_rows in source_positive.values()
        ),
        "source_negative_accepted": sum(
            any(int(row["presence_accepted"]) for row in source_rows)
            for source_rows in source_negative.values()
        ),
        "source_wrong_key_accepted": sum(
            any(int(row["presence_accepted"]) for row in source_rows)
            for source_rows in source_wrong_key.values()
        ),
        "physical_ber_mean": (
            float(np.mean([float(row["physical_raw_ber"]) for row in positive])) if positive else None
        ),
        "logical_ber_mean": (
            float(np.mean([float(row["logical_ber"]) for row in positive])) if positive else None
        ),
    }


def _detect_row(
    *,
    audio: np.ndarray,
    config: object,
    selector: object,
    method: str,
    expected: tuple[int, ...] | None,
    record: dict[str, object],
    message_id: str,
    sample_role: str,
    condition: str,
    clean: np.ndarray | None,
    marked: np.ndarray | None,
    received: np.ndarray | None,
    expected_physical: tuple[int, ...] | None,
    embed_seconds: float | str,
) -> dict[str, object]:
    started = time.perf_counter()
    detection = detect_watermark_b1_soft(audio, config, selector)
    decoded = decode_soft_capacity(detection.physical_statistics, METHOD_BITS[method])
    detect_seconds = time.perf_counter() - started
    decoded_bits = tuple(int(value) for value in decoded.message_bits)
    decoded_exact = int(expected is not None and decoded_bits == expected)
    snr = signal_snr(clean, marked) if clean is not None and marked is not None else "NOT_APPLICABLE"
    return {
        "method": method,
        "capacity_bits": METHOD_BITS[method],
        "strength": STRENGTH,
        "record_id": record["record_id"],
        "category": record["category"],
        "split": record["split"],
        "p2_role": record["p2_role"],
        "source_group_id": record["source_group_id"],
        "message_id": message_id,
        "sample_role": sample_role,
        "condition": condition,
        "expected_payload": "" if expected is None else "".join(map(str, expected)),
        "decoded_payload": "".join(map(str, decoded_bits)),
        "presence_score": decoded.presence_score,
        "score_margin": decoded.margin,
        "physical_raw_ber": (
            bit_error_rate(expected_physical, detection.hard_physical_bits)
            if expected_physical is not None
            else "NOT_APPLICABLE"
        ),
        "logical_ber": (
            bit_error_rate(expected, decoded_bits) if expected is not None else "NOT_APPLICABLE"
        ),
        "decoded_exact": decoded_exact if expected is not None else "NOT_APPLICABLE",
        "accepted_exact_recovery": "PENDING_THRESHOLD",
        "wrong_message_acceptance": "PENDING_THRESHOLD",
        "presence_threshold": "PENDING_THRESHOLD",
        "presence_accepted": "PENDING_THRESHOLD",
        "snr_db": snr,
        "spectral_distortion_rms_db": (
            _log_spectral_distortion(clean, marked)
            if clean is not None and marked is not None
            else "NOT_APPLICABLE"
        ),
        "mp3_fidelity_snr_db": (
            signal_snr(marked, received)
            if marked is not None and received is not None and condition in ("mp3_128k", "wrong_key_mp3")
            else "NOT_APPLICABLE"
        ),
        "detector_expected_payload_used": False,
        "embed_runtime_seconds": embed_seconds,
        "detect_runtime_seconds": detect_seconds,
        **(
            _clipping_fields(clean, marked)
            if clean is not None and marked is not None
            else {
                "peak_abs_clean": "NOT_APPLICABLE",
                "peak_abs_marked": "NOT_APPLICABLE",
                "clean_clipping_flag": "NOT_APPLICABLE",
                "clipping_flag": "NOT_APPLICABLE",
                "introduced_clipping_flag": "NOT_APPLICABLE",
            }
        ),
    }


def run(manifest_path: Path, output_dir: Path) -> dict[str, object]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    records = assign_development_roles(manifest["records"])
    dataset_root = Path(str(manifest["dataset_root"]))
    config = replace(build_embedding_config(), strength=STRENGTH)
    selector = load_public_selector()
    wrong_selector = _wrong_selector()
    rows: list[dict[str, object]] = []
    clean_cache: dict[str, np.ndarray] = {}
    clean_mp3_cache: dict[str, np.ndarray] = {}
    for record in records:
        record_id = str(record["record_id"])
        clean = clean_cache.setdefault(record_id, load_source(record, dataset_root))
        clean_mp3 = clean_mp3_cache.setdefault(
            record_id, _fit_length(_ffmpeg_mp3_roundtrip(clean, SAMPLE_RATE), clean.size)
        )
        for seed in MESSAGE_SEEDS:
            message_by_method = {
                method: message_for_seed(seed, bits) for method, bits in METHOD_BITS.items()
            }
            for method, bits in METHOD_BITS.items():
                expected = message_by_method[method]
                codeword = encode_capacity_payload(expected, bits)
                started = time.perf_counter()
                marked = embed_watermark_b1(clean, codeword, config, selector)
                embed_seconds = time.perf_counter() - started
                received = _fit_length(_ffmpeg_mp3_roundtrip(marked, SAMPLE_RATE), clean.size)
                rows.extend(
                    [
                        _detect_row(
                            audio=marked,
                            config=config,
                            selector=selector,
                            method=method,
                            expected=expected,
                            record=record,
                            message_id=f"seed_{seed}",
                            sample_role="positive",
                            condition="marked_no_attack",
                            clean=clean,
                            marked=marked,
                            received=None,
                            expected_physical=tuple(int(value) for value in codeword),
                            embed_seconds=embed_seconds,
                        ),
                        _detect_row(
                            audio=received,
                            config=config,
                            selector=selector,
                            method=method,
                            expected=expected,
                            record=record,
                            message_id=f"seed_{seed}",
                            sample_role="positive",
                            condition="mp3_128k",
                            clean=clean,
                            marked=marked,
                            received=received,
                            expected_physical=tuple(int(value) for value in codeword),
                            embed_seconds=embed_seconds,
                        ),
                        _detect_row(
                            audio=received,
                            config=config,
                            selector=wrong_selector,
                            method=method,
                            expected=expected,
                            record=record,
                            message_id=f"seed_{seed}",
                            sample_role="wrong_key_positive",
                            condition="wrong_key_mp3",
                            clean=clean,
                            marked=marked,
                            received=received,
                            expected_physical=tuple(int(value) for value in codeword),
                            embed_seconds=embed_seconds,
                        ),
                    ]
                )
                rows.extend(
                    [
                        _detect_row(
                            audio=clean,
                            config=config,
                            selector=selector,
                            method=method,
                            expected=None,
                            record=record,
                            message_id="negative_clean",
                            sample_role="negative",
                            condition="clean_no_watermark",
                            clean=None,
                            marked=None,
                            received=None,
                            expected_physical=None,
                            embed_seconds="NOT_APPLICABLE",
                        ),
                        _detect_row(
                            audio=clean_mp3,
                            config=config,
                            selector=selector,
                            method=method,
                            expected=None,
                            record=record,
                            message_id="negative_clean_mp3",
                            sample_role="negative",
                            condition="clean_mp3_no_watermark",
                            clean=None,
                            marked=None,
                            received=None,
                            expected_physical=None,
                            embed_seconds="NOT_APPLICABLE",
                        ),
                    ]
                )
    thresholds = calibrate_capacity_thresholds(rows)
    _apply_thresholds(rows, thresholds)
    output_dir.mkdir(parents=True, exist_ok=True)
    _write_csv(output_dir / "V3_P2_CAPACITY_PILOT.csv", rows)
    methods: dict[str, object] = {}
    for method in METHOD_BITS:
        methods[method] = {
            "capacity_bits": METHOD_BITS[method],
            "threshold": thresholds[method],
            "marked_no_attack": aggregate_pilot_metrics(rows, method, condition="marked_no_attack"),
            "mp3_128k": aggregate_pilot_metrics(rows, method, condition="mp3_128k"),
            "snr_db_mean": float(
                np.mean(
                    [
                        float(row["snr_db"])
                        for row in rows
                        if row["method"] == method
                        and row["p2_role"] == "pilot"
                        and row["sample_role"] == "positive"
                        and row["condition"] == "mp3_128k"
                    ]
                )
            ),
            "spectral_distortion_rms_db_mean": float(
                np.mean(
                    [
                        float(row["spectral_distortion_rms_db"])
                        for row in rows
                        if row["method"] == method
                        and row["p2_role"] == "pilot"
                        and row["sample_role"] == "positive"
                        and row["condition"] == "mp3_128k"
                    ]
                )
            ),
            "introduced_clipping_count": sum(
                int(row["introduced_clipping_flag"])
                for row in rows
                if row["method"] == method
                and row["p2_role"] == "pilot"
                and row["sample_role"] == "positive"
                and row["condition"] == "mp3_128k"
            ),
        }
    summary = {
        "status": "DEVELOPMENT_PILOT_ONLY",
        "manifest": str(manifest_path),
        "records_total": len(records),
        "calibration_sources": 15,
        "pilot_sources": 15,
        "messages_per_source": 2,
        "methods": methods,
        "thresholds": thresholds,
        "negative_unit": "source recording; clean and clean-MP3 rows are paired within source",
        "formal_test_used": False,
        "independent_validation": "NOT_ESTABLISHED",
        "qim_physical_embedder_changed": False,
    }
    (output_dir / "V3_P2_CAPACITY_PILOT_SUMMARY.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=ROOT / "configs/v3_p1_independent_manifest.json")
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(run(args.manifest, args.output_dir), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
