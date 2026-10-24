"""Analyze the frozen 32-position B1 channel on P1 development sources only."""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Iterable

import numpy as np
from dataclasses import replace

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from app.public_config import build_embedding_config, load_public_selector  # noqa: E402
from audio_watermark.b1 import embed_watermark_b1  # noqa: E402
from audio_watermark.b1_soft import encode_soft_payload  # noqa: E402
from audio_watermark.v3_p2 import assign_development_roles, message_for_seed  # noqa: E402
from v3_p0_channel_audit import _ffmpeg_mp3_roundtrip  # noqa: E402
from v3_p0_r1_experiment import (  # noqa: E402
    _fit_length,
    b1_per_bit_rows,
    load_source,
)


SAMPLE_RATE = 48_000
STRENGTH = 1.60
MESSAGE_SEEDS = (101, 202)


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


def _sign(value: float) -> int:
    return 1 if value >= 0.0 else -1


def _safe_corr(x: Iterable[float], y: Iterable[float]) -> float | None:
    left = np.asarray(tuple(x), dtype=np.float64)
    right = np.asarray(tuple(y), dtype=np.float64)
    if left.size < 2 or np.std(left) == 0.0 or np.std(right) == 0.0:
        return None
    return float(np.corrcoef(left, right)[0, 1])


def _safe_corr_matrix(values: np.ndarray) -> np.ndarray:
    """Return a correlation matrix without warnings for constant columns."""

    centered = values - np.mean(values, axis=0, keepdims=True)
    numerator = centered.T @ centered
    scale = np.sqrt(np.sum(centered * centered, axis=0))
    denominator = np.outer(scale, scale)
    result = np.full(denominator.shape, np.nan, dtype=np.float64)
    np.divide(numerator, denominator, out=result, where=denominator > 0.0)
    return result


def _error_runs(values: Iterable[int]) -> list[int]:
    runs: list[int] = []
    current = 0
    for value in values:
        if int(value):
            current += 1
        elif current:
            runs.append(current)
            current = 0
    if current:
        runs.append(current)
    return runs


def summarize_channel_rows(rows: list[dict[str, object]]) -> dict[str, object]:
    """Compute diagnostics from rows without fitting a new code or threshold."""

    mp3_rows = [row for row in rows if row["condition"] == "mp3_128k"]
    marked_rows = [row for row in rows if row["condition"] == "marked_no_attack"]
    grouped: dict[tuple[str, str], list[dict[str, object]]] = defaultdict(list)
    for row in mp3_rows:
        grouped[(str(row["record_id"]), str(row["message_id"]))].append(row)
    trial_counts = {
        f"{record_id}|{message_id}": int(sum(int(row["physical_error"]) for row in trial_rows))
        for (record_id, message_id), trial_rows in grouped.items()
    }
    error_counts = np.asarray(tuple(trial_counts.values()), dtype=np.float64)
    errors = np.asarray([int(row["physical_error"]) for row in mp3_rows], dtype=np.float64)
    p = float(np.mean(errors)) if errors.size else 0.0
    error_matrix = np.asarray(
        [
            [int(row["physical_error"]) for row in grouped[key]]
            for key in sorted(grouped)
        ],
        dtype=np.float64,
    )
    correlation_matrix = (
        _safe_corr_matrix(error_matrix)
        if error_matrix.shape[0] >= 2
        else np.full((32, 32), np.nan)
    )
    upper = correlation_matrix[np.triu_indices(32, k=1)]
    finite_upper = upper[np.isfinite(upper)]
    adjacent = np.diag(correlation_matrix, k=1)
    finite_adjacent = adjacent[np.isfinite(adjacent)]
    per_bit: dict[str, dict[str, float | int]] = {}
    for bit in range(32):
        bit_rows = [row for row in mp3_rows if int(row["physical_bit"]) == bit]
        bit_errors = [int(row["physical_error"]) for row in bit_rows]
        per_bit[str(bit)] = {
            "n": len(bit_rows),
            "ber": float(np.mean(bit_errors)) if bit_errors else 0.0,
            "error_count": int(sum(bit_errors)),
            "mean_abs_statistic": float(np.mean([float(row["stat_abs_margin"]) for row in bit_rows])),
            "mean_mp3_drift": float(np.mean([float(row["mp3_minus_marked_stat"]) for row in bit_rows])),
        }
    category_rows: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in mp3_rows:
        category_rows[str(row["category"])].append(row)
    category_ber = {
        category: float(np.mean([int(row["physical_error"]) for row in category_rows[category]]))
        for category in sorted(category_rows)
    }
    runs = _error_runs(
        [
            int(row["physical_error"])
            for key in sorted(grouped)
            for row in sorted(grouped[key], key=lambda item: int(item["physical_bit"]))
        ]
    )
    observed_variance = float(np.var(error_counts)) if error_counts.size else 0.0
    iid_variance = 32.0 * p * (1.0 - p)
    reliability = _safe_corr(
        [float(row["stat_abs_margin"]) for row in mp3_rows],
        [int(row["physical_error"]) for row in mp3_rows],
    )
    host_alignment = [float(row["expected_sign"]) * float(row["host_stat_before_embedding"]) for row in rows]
    marked_alignment = [float(row["expected_sign"]) * float(row["marked_stat"]) for row in marked_rows]
    return {
        "status": "CONFIRMED",
        "source_recordings": len({str(row["record_id"]) for row in mp3_rows}),
        "paired_messages": len(grouped),
        "physical_observations_mp3": len(mp3_rows),
        "physical_ber_mp3": p,
        "physical_ber_marked_no_attack": float(np.mean([int(row["physical_error"]) for row in marked_rows]))
        if marked_rows
        else 0.0,
        "category_physical_ber_mp3": category_ber,
        "per_physical_bit": per_bit,
        "physical_error_count_distribution": dict(
            sorted(Counter(int(value) for value in error_counts).items())
        ),
        "physical_error_count_mean": float(np.mean(error_counts)) if error_counts.size else 0.0,
        "physical_error_count_variance": observed_variance,
        "iid_expected_error_count_mean": 32.0 * p,
        "iid_expected_error_count_variance": iid_variance,
        "iid_dispersion_ratio": observed_variance / iid_variance if iid_variance > 0 else None,
        "mean_abs_off_diagonal_error_correlation": float(np.mean(finite_upper))
        if finite_upper.size
        else None,
        "mean_adjacent_error_correlation": float(np.mean(finite_adjacent))
        if finite_adjacent.size
        else None,
        "soft_reliability_error_correlation": reliability,
        "error_run_count": len(runs),
        "max_contiguous_error_run": max(runs, default=0),
        "mean_contiguous_error_run": float(np.mean(runs)) if runs else 0.0,
        "host_alignment_mean": float(np.mean(host_alignment)) if host_alignment else 0.0,
        "marked_alignment_mean": float(np.mean(marked_alignment)) if marked_alignment else 0.0,
        "mean_mp3_minus_marked_stat": float(
            np.mean([float(row["mp3_minus_marked_stat"]) for row in mp3_rows])
        )
        if mp3_rows
        else 0.0,
        "selection_or_training_on_p1_formal_test": False,
        "formal_independent_validation": "NOT_ESTABLISHED",
    }


def run(manifest_path: Path, output_dir: Path) -> dict[str, object]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    records = assign_development_roles(manifest["records"])
    dataset_root = Path(str(manifest["dataset_root"]))
    config = replace(build_embedding_config(), strength=STRENGTH)
    selector = load_public_selector()
    rows: list[dict[str, object]] = []
    for record in records:
        clean = load_source(record, dataset_root)
        for seed in MESSAGE_SEEDS:
            message = message_for_seed(seed, 8)
            expected = tuple(int(value) for value in encode_soft_payload(message))
            marked = embed_watermark_b1(clean, expected, config, selector)
            received = _fit_length(_ffmpeg_mp3_roundtrip(marked, SAMPLE_RATE), clean.size)
            base_rows = b1_per_bit_rows(
                clean,
                marked,
                received,
                expected,
                config,
                selector,
                record=record,
                message_id=f"seed_{seed}",
                attack="mp3_128k",
            )
            for base in base_rows:
                for condition, statistic_key in (
                    ("marked_no_attack", "marked_stat_mean"),
                    ("mp3_128k", "mp3_stat_mean"),
                ):
                    observed = float(base[statistic_key])
                    marked_stat = float(base["marked_stat_mean"])
                    expected_sign = 1 if int(base["expected_physical_bit"]) else -1
                    row = dict(base)
                    row.update(
                        {
                            "p2_role": record["p2_role"],
                            "condition": condition,
                            "observed_statistic": observed,
                            "expected_sign": expected_sign,
                            "physical_error": int(_sign(observed) != expected_sign),
                            "stat_abs_margin": abs(observed),
                            "host_stat_before_embedding": float(base["host_stat_mean"]),
                            "marked_stat": marked_stat,
                            "mp3_minus_marked_stat": float(base["mp3_stat_mean"]) - marked_stat,
                            "detector_expected_payload_used": False,
                        }
                    )
                    rows.append(row)
    output_dir.mkdir(parents=True, exist_ok=True)
    _write_csv(output_dir / "V3_P2_CHANNEL_DIAGNOSTICS.csv", rows)
    summary = summarize_channel_rows(rows)
    (output_dir / "V3_P2_CHANNEL_ANALYSIS.json").write_text(
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
