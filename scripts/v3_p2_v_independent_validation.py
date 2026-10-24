"""Run the frozen V3-P2-V source-disjoint 8/12-bit validation.

The detector receives only the audio, public embedding configuration, and a
selector.  Expected messages are attached to rows only after detection for
scoring.  No threshold or operating point is learned in this script.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import resource
import sys
import time
from collections import defaultdict
from dataclasses import replace
from pathlib import Path
from typing import Iterable

import numpy as np
from scipy.stats import binomtest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from app.public_config import build_embedding_config, load_public_selector  # noqa: E402
from audio_watermark.b1 import embed_watermark_b1  # noqa: E402
from audio_watermark.b1_soft import detect_watermark_b1_soft  # noqa: E402
from audio_watermark.b2_capacity import decode_soft_capacity, encode_capacity_payload  # noqa: E402
from audio_watermark.metrics import bit_error_rate, signal_snr  # noqa: E402
from v3_p0_channel_audit import _ffmpeg_mp3_roundtrip  # noqa: E402
from v3_p0_r1_experiment import _fit_length, _log_spectral_distortion, load_source  # noqa: E402
from v3_p1_independent_validation import _clipping_fields, _wrong_selector  # noqa: E402
from audio_watermark.v3_p2 import message_for_seed  # noqa: E402


SAMPLE_RATE = 48_000
STRENGTH = 1.60
MESSAGE_SEEDS = (101, 202)
METHOD_BITS = {"soft8_frozen": 8, "soft12_frozen": 12}
THRESHOLDS = {"soft8_frozen": 0.7855073980199624, "soft12_frozen": 0.903827529676706}


def wilson_interval(successes: int, trials: int, z: float = 1.959963984540054) -> tuple[float, float]:
    """Return a two-sided Wilson interval for a binomial proportion."""

    if trials <= 0:
        return (float("nan"), float("nan"))
    successes = max(0, min(int(successes), int(trials)))
    n = float(trials)
    p = successes / n
    denominator = 1.0 + z * z / n
    centre = (p + z * z / (2.0 * n)) / denominator
    radius = z * math.sqrt((p * (1.0 - p) + z * z / (4.0 * n)) / n) / denominator
    return (max(0.0, centre - radius), min(1.0, centre + radius))


def mcnemar_two_sided(first_only: int, second_only: int) -> float:
    """Exact two-sided McNemar p-value from discordant source counts."""

    discordant = int(first_only) + int(second_only)
    if discordant == 0:
        return 1.0
    return float(binomtest(min(int(first_only), int(second_only)), discordant, 0.5).pvalue)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _peak_rss_mb() -> float:
    return float(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss) / 1024.0


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


def _detect(audio: np.ndarray, config: object, selector: object, payload_bits: int) -> tuple[object, float]:
    """Blind detection and capacity decoding; no expected payload is accepted."""

    started = time.perf_counter()
    detection = detect_watermark_b1_soft(audio, config, selector)
    decoded = decode_soft_capacity(detection.physical_statistics, payload_bits)
    return decoded, time.perf_counter() - started


def _row(
    *,
    record: dict[str, object],
    method: str,
    message_id: str,
    sample_role: str,
    condition: str,
    expected: tuple[int, ...] | None,
    expected_physical: tuple[int, ...] | None,
    decoded: object,
    clean: np.ndarray | None,
    marked: np.ndarray | None,
    received: np.ndarray | None,
    embed_seconds: float | str,
    detect_seconds: float,
) -> dict[str, object]:
    decoded_bits = tuple(int(value) for value in decoded.message_bits)
    physical = tuple(int(value) for value in decoded.hard_physical_bits)
    accepted = int(float(decoded.presence_score) >= THRESHOLDS[method])
    exact = int(expected is not None and decoded_bits == expected) if expected is not None else "NOT_APPLICABLE"
    snr = signal_snr(clean, marked) if clean is not None and marked is not None else "NOT_APPLICABLE"
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
        "capacity_bits": METHOD_BITS[method],
        "strength": STRENGTH,
        "record_id": record["record_id"],
        "category": record["category"],
        "split": record["split"],
        "source_group_id": record["source_group_id"],
        "message_id": message_id,
        "sample_role": sample_role,
        "condition": condition,
        "expected_payload": "" if expected is None else "".join(map(str, expected)),
        "decoded_payload": "".join(map(str, decoded_bits)),
        "presence_score": float(decoded.presence_score),
        "score_margin": float(decoded.margin),
        "presence_threshold": THRESHOLDS[method],
        "presence_accepted": accepted,
        "decoded_exact": exact,
        "accepted_exact_recovery": int(accepted and exact) if expected is not None else "NOT_APPLICABLE",
        "wrong_message_acceptance": int(accepted and not exact) if expected is not None else "NOT_APPLICABLE",
        "physical_raw_ber": (
            bit_error_rate(expected_physical, physical)
            if expected_physical is not None
            else "NOT_APPLICABLE"
        ),
        "logical_ber": bit_error_rate(expected, decoded_bits) if expected is not None else "NOT_APPLICABLE",
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
        **clipping,
        "embed_runtime_seconds": embed_seconds,
        "detect_runtime_seconds": detect_seconds,
        "peak_rss_mb": _peak_rss_mb(),
        "detector_expected_payload_used": False,
    }


def _positive(rows: Iterable[dict[str, object]], method: str, condition: str) -> list[dict[str, object]]:
    return [
        row
        for row in rows
        if row["method"] == method and row["sample_role"] == "positive" and row["condition"] == condition
    ]


def _source_both(rows: list[dict[str, object]], field: str) -> tuple[int, int]:
    grouped: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        grouped[str(row["record_id"])].append(row)
    total = len(grouped)
    successes = sum(len(values) == 2 and all(int(value[field]) for value in values) for values in grouped.values())
    return int(successes), int(total)


def _rate(successes: int, trials: int) -> dict[str, object]:
    lower, upper = wilson_interval(successes, trials)
    return {"successes": successes, "trials": trials, "rate": successes / trials if trials else None, "wilson95": [lower, upper]}


def _aggregate_method_condition(rows: list[dict[str, object]], method: str, condition: str) -> dict[str, object]:
    positive = _positive(rows, method, condition)
    exact = sum(int(row["decoded_exact"]) for row in positive)
    accepted = sum(int(row["presence_accepted"]) for row in positive)
    accepted_exact = sum(int(row["accepted_exact_recovery"]) for row in positive)
    unknown = len(positive) - accepted
    wrong_message = sum(int(row["wrong_message_acceptance"]) for row in positive)
    source_exact, source_total = _source_both(positive, "decoded_exact")
    source_accepted_exact, _ = _source_both(positive, "accepted_exact_recovery")
    by_category: dict[str, object] = {}
    for category in ("speech", "music", "environment"):
        subset = [row for row in positive if row["category"] == category]
        cat_exact, cat_sources = _source_both(subset, "decoded_exact")
        cat_accepted, _ = _source_both(subset, "accepted_exact_recovery")
        by_category[category] = {
            "trial_raw_exact": _rate(sum(int(row["decoded_exact"]) for row in subset), len(subset)),
            "trial_accepted_exact": _rate(sum(int(row["accepted_exact_recovery"]) for row in subset), len(subset)),
            "source_both_raw_exact": _rate(cat_exact, cat_sources),
            "source_both_accepted_exact": _rate(cat_accepted, cat_sources),
        }
    numeric = lambda field: [float(row[field]) for row in positive if row[field] != "NOT_APPLICABLE"]
    return {
        "condition": condition,
        "trial_raw_exact": _rate(exact, len(positive)),
        "trial_accepted_exact": _rate(accepted_exact, len(positive)),
        "trial_acceptance": _rate(accepted, len(positive)),
        "unknown_rate": _rate(unknown, len(positive)),
        "wrong_message_acceptance": _rate(wrong_message, len(positive)),
        "source_both_raw_exact": _rate(source_exact, source_total),
        "source_both_accepted_exact": _rate(source_accepted_exact, source_total),
        "physical_ber_mean": float(np.mean(numeric("physical_raw_ber"))) if numeric("physical_raw_ber") else None,
        "logical_ber_mean": float(np.mean(numeric("logical_ber"))) if numeric("logical_ber") else None,
        "snr_mean_db": float(np.mean(numeric("snr_db"))) if numeric("snr_db") else None,
        "spectral_distortion_mean_db": float(np.mean(numeric("spectral_distortion_rms_db"))) if numeric("spectral_distortion_rms_db") else None,
        "mp3_fidelity_snr_mean_db": float(np.mean(numeric("mp3_fidelity_snr_db"))) if numeric("mp3_fidelity_snr_db") else None,
        "by_category": by_category,
    }


def _aggregate_negatives(rows: list[dict[str, object]], method: str, condition: str) -> dict[str, object]:
    subset = [row for row in rows if row["method"] == method and row["condition"] == condition]
    accepted = sum(int(row["presence_accepted"]) for row in subset)
    grouped: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in subset:
        grouped[str(row["record_id"])].append(row)
    source_accepted = sum(any(int(row["presence_accepted"]) for row in values) for values in grouped.values())
    return {
        "trial_fpr": _rate(accepted, len(subset)),
        "source_fpr": _rate(source_accepted, len(grouped)),
        "rows": len(subset),
        "sources": len(grouped),
    }


def _pairwise_source(rows: list[dict[str, object]], condition: str) -> dict[str, object]:
    source: dict[tuple[str, str], dict[str, bool]] = {}
    for method in METHOD_BITS:
        positive = _positive(rows, method, condition)
        grouped: dict[str, list[dict[str, object]]] = defaultdict(list)
        for row in positive:
            grouped[str(row["record_id"])].append(row)
        for record_id, values in grouped.items():
            source.setdefault((record_id, condition), {})[method] = all(int(row["accepted_exact_recovery"]) for row in values)
    pairs = [values for (record_id, _condition), values in source.items() if set(values) == set(METHOD_BITS)]
    first_only = sum(value["soft8_frozen"] and not value["soft12_frozen"] for value in pairs)
    second_only = sum(value["soft12_frozen"] and not value["soft8_frozen"] for value in pairs)
    both = sum(value["soft8_frozen"] and value["soft12_frozen"] for value in pairs)
    neither = sum(not value["soft8_frozen"] and not value["soft12_frozen"] for value in pairs)
    return {
        "condition": condition,
        "sources": len(pairs),
        "soft8_only": first_only,
        "soft12_only": second_only,
        "both": both,
        "neither": neither,
        "mcnemar_p_two_sided": mcnemar_two_sided(first_only, second_only),
    }


def aggregate(rows: list[dict[str, object]], manifest: dict[str, object], freeze: dict[str, object]) -> dict[str, object]:
    methods: dict[str, object] = {}
    for method in METHOD_BITS:
        methods[method] = {
            condition: _aggregate_method_condition(rows, method, condition)
            for condition in ("marked_no_attack", "mp3_128k")
        }
        methods[method]["negative_clean"] = _aggregate_negatives(rows, method, "clean_no_watermark")
        methods[method]["negative_clean_mp3"] = _aggregate_negatives(rows, method, "clean_mp3_no_watermark")
        methods[method]["wrong_key_mp3"] = _aggregate_negatives(rows, method, "wrong_key_mp3")
    fidelity = {}
    for condition in ("marked_no_attack", "mp3_128k"):
        eight = methods["soft8_frozen"][condition]
        twelve = methods["soft12_frozen"][condition]
        fidelity[condition] = {
            "snr_difference_12_minus_8_db": twelve["snr_mean_db"] - eight["snr_mean_db"],
            "spectral_distortion_difference_12_minus_8_db": twelve["spectral_distortion_mean_db"] - eight["spectral_distortion_mean_db"],
        }
    return {
        "manifest_sha256": _sha256(Path(str(freeze["manifest"]["path"]))),
        "freeze_record_sha256": _sha256(ROOT / "experiments/v3_p2_v/CONFIG_FREEZE.json"),
        "source_count": len(manifest["records"]),
        "message_seeds": list(MESSAGE_SEEDS),
        "methods": methods,
        "paired_source_acceptance": {
            condition: _pairwise_source(rows, condition)
            for condition in ("marked_no_attack", "mp3_128k")
        },
        "matched_fidelity": fidelity,
        "negative_sample_limitations": "60 matched source negatives; zero observed rates do not establish population FPR below 1%; Wilson upper bounds are reported",
        "detector_contract_verified": all(row["detector_expected_payload_used"] is False for row in rows),
    }


def run(manifest_path: Path, freeze_path: Path, output_csv: Path, output_summary: Path) -> dict[str, object]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    freeze = json.loads(freeze_path.read_text(encoding="utf-8"))
    if manifest.get("status") != "FROZEN" or manifest.get("manifest_version") != "V3_P2_V_INDEPENDENT_VALIDATION_V1":
        raise ValueError("V3-P2-V manifest is not frozen")
    if freeze.get("validation_status") != "FROZEN_BEFORE_RESULTS":
        raise ValueError("V3-P2-V freeze record is not pre-result frozen")
    if freeze.get("head_before_validation") != "63d3166b1eeb2f0f7e99c8a9ad181934b824370e":
        raise ValueError("unexpected validation base HEAD")
    if freeze.get("thresholds") != THRESHOLDS or float(freeze.get("strength")) != STRENGTH:
        raise ValueError("frozen operating point mismatch")
    records = list(manifest["records"])
    if len(records) != 60:
        raise ValueError("V3-P2-V requires 60 sources")
    dataset_root = Path(str(manifest["dataset_root"]))
    config = replace(build_embedding_config(), strength=STRENGTH)
    selector = load_public_selector()
    wrong_selector = _wrong_selector()
    rows: list[dict[str, object]] = []
    for index, record in enumerate(records, start=1):
        clean = load_source(record, dataset_root)
        clean_mp3 = _fit_length(_ffmpeg_mp3_roundtrip(clean, SAMPLE_RATE), clean.size)
        for method, bits in METHOD_BITS.items():
            for condition, audio in (("clean_no_watermark", clean), ("clean_mp3_no_watermark", clean_mp3)):
                decoded, detect_seconds = _detect(audio, config, selector, bits)
                rows.append(
                    _row(
                        record=record,
                        method=method,
                        message_id="negative",
                        sample_role="negative",
                        condition=condition,
                        expected=None,
                        expected_physical=None,
                        decoded=decoded,
                        clean=None,
                        marked=None,
                        received=None,
                        embed_seconds="NOT_APPLICABLE",
                        detect_seconds=detect_seconds,
                    )
                )
            for seed in MESSAGE_SEEDS:
                expected = message_for_seed(seed, bits)
                expected_physical = tuple(int(value) for value in encode_capacity_payload(expected, bits))
                started = time.perf_counter()
                marked = embed_watermark_b1(clean, expected_physical, config, selector)
                embed_seconds = time.perf_counter() - started
                received = _fit_length(_ffmpeg_mp3_roundtrip(marked, SAMPLE_RATE), clean.size)
                for condition, audio in (("marked_no_attack", marked), ("mp3_128k", received)):
                    decoded, detect_seconds = _detect(audio, config, selector, bits)
                    rows.append(
                        _row(
                            record=record,
                            method=method,
                            message_id=f"seed_{seed}",
                            sample_role="positive",
                            condition=condition,
                            expected=expected,
                            expected_physical=expected_physical,
                            decoded=decoded,
                            clean=clean,
                            marked=marked,
                            received=received if condition == "mp3_128k" else None,
                            embed_seconds=embed_seconds,
                            detect_seconds=detect_seconds,
                        )
                    )
                decoded, detect_seconds = _detect(received, config, wrong_selector, bits)
                rows.append(
                    _row(
                        record=record,
                        method=method,
                        message_id=f"seed_{seed}",
                        sample_role="wrong_key_positive",
                        condition="wrong_key_mp3",
                        expected=expected,
                        expected_physical=None,
                        decoded=decoded,
                        clean=clean,
                        marked=marked,
                        received=received,
                        embed_seconds=embed_seconds,
                        detect_seconds=detect_seconds,
                    )
                )
        if index % 10 == 0:
            print(f"processed {index}/{len(records)} sources", flush=True)
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    output_summary.parent.mkdir(parents=True, exist_ok=True)
    _write_csv(output_csv, rows)
    summary = aggregate(rows, manifest, freeze)
    output_summary.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=ROOT / "configs/v3_p2_v_independent_manifest.json")
    parser.add_argument("--freeze", type=Path, default=ROOT / "experiments/v3_p2_v/CONFIG_FREEZE.json")
    parser.add_argument("--output-csv", type=Path, default=ROOT / "V3_P2_V_PAIRED_RESULTS.csv")
    parser.add_argument("--output-summary", type=Path, default=ROOT / "experiments/v3_p2_v/VALIDATION_SUMMARY.json")
    args = parser.parse_args()
    print(json.dumps(run(args.manifest, args.freeze, args.output_csv, args.output_summary), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
