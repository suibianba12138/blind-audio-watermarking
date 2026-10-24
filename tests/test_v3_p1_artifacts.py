"""Artifact and provenance gates for the frozen P1 validation."""

from __future__ import annotations

import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "configs" / "v3_p1_independent_manifest.json"
RESULTS = ROOT / "experiments" / "v3_p1"


def _rows(name: str) -> list[dict[str, str]]:
    with (RESULTS / name).open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def test_p1_manifest_and_result_rows_are_source_disjoint_and_blind() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    pilot = json.loads(
        (ROOT / "configs" / "v3_b1_soft_pilot_manifest.json").read_text(encoding="utf-8")
    )
    r1 = json.loads(
        (ROOT / "configs" / "v3_p0_r1_real_audio_manifest.json").read_text(encoding="utf-8")
    )
    records = manifest["records"]
    assert manifest["manifest_version"] == "V3_P1_INDEPENDENT_VALIDATION_V1"
    assert manifest["status"] == "FROZEN"
    assert len(records) == 60
    assert not {r["sha256"] for r in records}.intersection(
        {r["sha256"] for r in pilot["records"]} | {r["sha256"] for r in r1["records"]}
    )

    positive = _rows("V3_P1_PAIRED_RESULTS.csv")
    negative = _rows("V3_P1_DETECTION_RESULTS.csv")
    assert len(positive) == 720
    assert len(negative) == 720
    assert {row["method"] for row in positive} == {"repeat4", "hard_code", "soft_code"}
    assert all(row["detector_expected_payload_used"] == "False" for row in positive + negative)


def test_p1_analysis_records_frozen_soft_code_result_and_mcnemar() -> None:
    analysis = json.loads((RESULTS / "V3_P1_ANALYSIS.json").read_text(encoding="utf-8"))
    soft = analysis["positive"]["soft_code"]["mp3_128k"]
    assert soft["exact_trial_recovery"]["successes"] == 60
    assert soft["source_all_two_messages_exact"]["successes"] == 30
    assert analysis["negative"]["soft_code"]["clean_combined_trials"]["trial_acceptance"]["successes"] == 0
    assert analysis["negative"]["soft_code"]["wrong_key_mp3"]["trial_acceptance"]["successes"] == 0
    assert analysis["source_level_mcnemar"]["soft_vs_repeat4"]["exact_two_sided_p"] == 0.001953125
