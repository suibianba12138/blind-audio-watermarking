"""Analyze frozen V3-P1 CSVs without changing any operating point."""

from __future__ import annotations

import argparse
import csv
import json
import math
from collections import defaultdict
from pathlib import Path
from statistics import mean


Z95 = 1.959963984540054


def _bit(row: dict[str, str], field: str) -> int:
    return int(row[field])


def _number(row: dict[str, str], field: str) -> float:
    return float(row[field])


def _mean_numeric(rows: list[dict[str, str]], field: str) -> float | None:
    values = [float(row[field]) for row in rows if row[field] != "NOT_APPLICABLE"]
    return sum(values) / len(values) if values else None


def wilson_interval(successes: int, total: int, z: float = Z95) -> list[float]:
    """Return a two-sided Wilson score interval for a binomial proportion."""

    if total <= 0:
        return [float("nan"), float("nan")]
    proportion = successes / total
    denominator = 1.0 + z * z / total
    center = (proportion + z * z / (2.0 * total)) / denominator
    half_width = z * math.sqrt(
        proportion * (1.0 - proportion) / total + z * z / (4.0 * total * total)
    ) / denominator
    return [max(0.0, center - half_width), min(1.0, center + half_width)]


def _binomial_probability(k: int, n: int) -> float:
    return math.comb(n, k) / (2.0**n)


def exact_binomial_two_sided(k: int, n: int) -> float:
    """Return the exact two-sided p-value for a 0.5-binomial test."""

    if n == 0:
        return 1.0
    observed = _binomial_probability(k, n)
    return min(
        1.0,
        sum(
            _binomial_probability(i, n)
            for i in range(n + 1)
            if _binomial_probability(i, n) <= observed + 1e-15
        ),
    )


def mcnemar_exact(left: dict[str, bool], right: dict[str, bool]) -> dict[str, object]:
    keys = sorted(set(left) & set(right))
    left_only = sum(left[key] and not right[key] for key in keys)
    right_only = sum(right[key] and not left[key] for key in keys)
    return {
        "paired_units": len(keys),
        "left_success_right_failure": left_only,
        "left_failure_right_success": right_only,
        "exact_two_sided_p": exact_binomial_two_sided(left_only, left_only + right_only),
    }


def _rate(successes: int, total: int) -> dict[str, object]:
    return {
        "successes": successes,
        "total": total,
        "rate": successes / total if total else None,
        "wilson_95_ci": wilson_interval(successes, total),
    }


def _source_groups(rows: list[dict[str, str]]) -> dict[str, list[dict[str, str]]]:
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        grouped[row["record_id"]].append(row)
    return dict(grouped)


def _positive_metric(rows: list[dict[str, str]]) -> dict[str, object]:
    exact = sum(_bit(row, "exact_message_recovery") for row in rows)
    accepted = sum(_bit(row, "presence_accepted") for row in rows)
    wrong_acceptance = sum(_bit(row, "wrong_message_acceptance") for row in rows)
    source = _source_groups(rows)
    source_all = sum(
        len(group) == 2 and all(_bit(row, "exact_message_recovery") for row in group)
        for group in source.values()
    )
    source_any = sum(any(_bit(row, "exact_message_recovery") for row in group) for group in source.values())
    return {
        "trial_count": len(rows),
        "physical_ber_mean": mean(_number(row, "physical_raw_ber") for row in rows),
        "logical_ber_mean": mean(_number(row, "logical_ber") for row in rows),
        "exact_trial_recovery": _rate(exact, len(rows)),
        "source_all_two_messages_exact": _rate(source_all, len(source)),
        "source_any_message_exact": _rate(source_any, len(source)),
        "presence_acceptance": _rate(accepted, len(rows)),
        "wrong_message_acceptance": _rate(wrong_acceptance, len(rows)),
        "snr_db_mean": _mean_numeric(rows, "snr_db"),
        "spectral_distortion_rms_db_mean": _mean_numeric(
            rows, "spectral_distortion_rms_db"
        ),
        "mp3_fidelity_snr_db_mean": _mean_numeric(rows, "mp3_fidelity_snr_db"),
        "clean_clipping_flags": sum(_bit(row, "clean_clipping_flag") for row in rows),
        "clipping_flags": sum(_bit(row, "clipping_flag") for row in rows),
        "introduced_clipping_flags": sum(
            _bit(row, "introduced_clipping_flag") for row in rows
        ),
        "embed_runtime_seconds_mean": mean(_number(row, "embed_runtime_seconds") for row in rows),
        "detect_runtime_seconds_mean": mean(_number(row, "detect_runtime_seconds") for row in rows),
        "peak_rss_mb_max": max(_number(row, "peak_rss_mb") for row in rows),
    }


def _negative_metric(rows: list[dict[str, str]]) -> dict[str, object]:
    accepted = sum(_bit(row, "presence_accepted") for row in rows)
    source = _source_groups(rows)
    source_any = sum(any(_bit(row, "presence_accepted") for row in group) for group in source.values())
    return {
        "trial_acceptance": _rate(accepted, len(rows)),
        "source_any_acceptance": _rate(source_any, len(source)),
        "mean_presence_score": mean(_number(row, "presence_score") for row in rows),
        "max_presence_score": max(_number(row, "presence_score") for row in rows),
    }


def analyze(positive_path: Path, negative_path: Path) -> dict[str, object]:
    positive = list(csv.DictReader(positive_path.open(newline="", encoding="utf-8")))
    negative = list(csv.DictReader(negative_path.open(newline="", encoding="utf-8")))
    test_positive = [row for row in positive if row["split"] == "test"]
    test_negative = [row for row in negative if row["split"] == "test"]
    methods = ("repeat4", "hard_code", "soft_code")
    positive_summary: dict[str, object] = {}
    negative_summary: dict[str, object] = {}
    category_summary: dict[str, object] = {}
    for method in methods:
        method_mp3 = [
            row
            for row in test_positive
            if row["method"] == method and row["condition"] == "mp3_128k"
        ]
        method_clean = [
            row
            for row in test_negative
            if row["method"] == method and row["condition"] in {"clean", "clean_mp3"}
        ]
        method_wrong = [
            row
            for row in test_negative
            if row["method"] == method and row["condition"] == "wrong_key_mp3"
        ]
        no_attack = [
            row
            for row in test_positive
            if row["method"] == method and row["condition"] == "marked_no_attack"
        ]
        positive_summary[method] = {
            "no_attack": _positive_metric(no_attack),
            "mp3_128k": _positive_metric(method_mp3),
        }
        negative_summary[method] = {
            "clean": _negative_metric([row for row in method_clean if row["condition"] == "clean"]),
            "clean_mp3": _negative_metric([row for row in method_clean if row["condition"] == "clean_mp3"]),
            "clean_combined_trials": _negative_metric(method_clean),
            "wrong_key_mp3": _negative_metric(method_wrong),
        }
        category_summary[method] = {
            category: _positive_metric(
                [row for row in method_mp3 if row["category"] == category]
            )
            for category in ("speech", "music", "environment")
        }

    source_success: dict[str, dict[str, bool]] = {}
    for method in methods:
        rows = [
            row
            for row in test_positive
            if row["method"] == method and row["condition"] == "mp3_128k"
        ]
        source_success[method] = {
            record_id: len(group) == 2 and all(_bit(row, "exact_message_recovery") for row in group)
            for record_id, group in _source_groups(rows).items()
        }

    fidelity: dict[str, object] = {}
    repeat_rows = {
        (row["record_id"], row["message_id"]): row
        for row in test_positive
        if row["method"] == "repeat4" and row["condition"] == "mp3_128k"
    }
    for method in ("hard_code", "soft_code"):
        paired = [
            (
                _number(row, "snr_db")
                - _number(repeat_rows[(row["record_id"], row["message_id"])], "snr_db"),
                _number(row, "spectral_distortion_rms_db")
                - _number(
                    repeat_rows[(row["record_id"], row["message_id"])],
                    "spectral_distortion_rms_db",
                ),
            )
            for row in test_positive
            if row["method"] == method and row["condition"] == "mp3_128k"
        ]
        fidelity[method] = {
            "snr_difference_mean_db": mean(value[0] for value in paired),
            "snr_difference_max_abs_db": max(abs(value[0]) for value in paired),
            "spectral_distortion_difference_mean_db": mean(value[1] for value in paired),
        }

    return {
        "protocol": {
            "formal_split": "test",
            "source_count": len(source_success["repeat4"]),
            "messages_per_source": 2,
            "methods": list(methods),
            "thresholds_not_refit": True,
        },
        "positive": positive_summary,
        "negative": negative_summary,
        "category_mp3": category_summary,
        "source_level_mcnemar": {
            "soft_vs_repeat4": mcnemar_exact(source_success["soft_code"], source_success["repeat4"]),
            "hard_vs_repeat4": mcnemar_exact(source_success["hard_code"], source_success["repeat4"]),
        },
        "matched_fidelity": fidelity,
        "input_rows": {"positive": len(positive), "negative": len(negative)},
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--positive", type=Path, required=True)
    parser.add_argument("--negative", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = analyze(args.positive, args.negative)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
