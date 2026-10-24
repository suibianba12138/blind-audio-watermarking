import json
import csv
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FREEZE = ROOT / "experiments" / "v3_p2" / "CONFIG_FREEZE.json"


def test_p2_freeze_records_immutable_eight_bit_operating_point():
    record = json.loads(FREEZE.read_text(encoding="utf-8"))
    assert record["stage"] == "V3_P2_CAPACITY_DESIGN"
    assert record["effective_payload_bits"] == 8
    assert record["physical_payload_bits"] == 32
    assert record["strength"] == 1.60
    assert record["soft_code_threshold"] == 0.7855073980199624
    assert record["physical_threshold"] == 0.47678591988959035
    assert record["message_seeds"] == [101, 202]
    assert record["selector"]["watermark_seed"] == 7
    assert record["source_sha256"]
    assert record["manifest_sha256"]
    assert record["soft_codebook_sha256"]
    assert "expected_payload" in record["detector_contract_scoring_only"]


def test_p2_freeze_declares_dev_only_calibration_and_no_p1_test_tuning():
    record = json.loads(FREEZE.read_text(encoding="utf-8"))
    assert record["calibration_policy"]["formal_test_used_for_selection"] is False
    assert record["calibration_policy"]["development_split"] == "dev"
    assert record["calibration_policy"]["future_validation_status"] == "NOT_ESTABLISHED"


def test_p2_pilot_artifacts_are_paired_and_development_only():
    pilot = ROOT / "V3_P2_CAPACITY_PILOT.csv"
    with pilot.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 900
    assert {row["split"] for row in rows} == {"dev"}
    assert {row["method"] for row in rows} == {"soft8_frozen", "degree2_12", "degree2_16"}
    assert {row["p2_role"] for row in rows} == {"calibration", "pilot"}
    summary = json.loads(
        (ROOT / "experiments" / "v3_p2" / "V3_P2_CAPACITY_PILOT_SUMMARY.json").read_text(
            encoding="utf-8"
        )
    )
    assert summary["formal_test_used"] is False
    assert summary["independent_validation"] == "NOT_ESTABLISHED"
    assert summary["qim_physical_embedder_changed"] is False
    for method in summary["methods"].values():
        assert method["mp3_128k"]["source_recordings"] == 15


def test_p2_channel_diagnostics_exclude_formal_test_sources():
    diagnostics = ROOT / "experiments" / "v3_p2" / "V3_P2_CHANNEL_DIAGNOSTICS.csv"
    with diagnostics.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 3840
    assert {row["split"] for row in rows} == {"dev"}
    assert {row["condition"] for row in rows} == {"marked_no_attack", "mp3_128k"}
