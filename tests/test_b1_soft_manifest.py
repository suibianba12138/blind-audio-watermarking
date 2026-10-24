"""Regression checks for the frozen B1 soft-code pilot manifest."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "configs" / "v3_b1_soft_pilot_manifest.json"
R1_MANIFEST = ROOT / "configs" / "v3_p0_r1_real_audio_manifest.json"


def test_soft_code_manifest_is_frozen_balanced_and_r1_disjoint() -> None:
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    r1 = json.loads(R1_MANIFEST.read_text(encoding="utf-8"))
    records = data["records"]

    assert data["status"] == "FROZEN"
    assert data["manifest_version"] == "V3_B1_SOFT_CODE_PILOT_V1"
    assert len(records) == 60
    assert Counter((row["category"], row["split"]) for row in records) == Counter(
        {
            ("speech", "dev"): 10,
            ("speech", "test"): 10,
            ("music", "dev"): 10,
            ("music", "test"): 10,
            ("environment", "dev"): 10,
            ("environment", "test"): 10,
        }
    )
    assert len({row["source_group_id"] for row in records}) == 60
    assert len({row["source_recording_id"] for row in records}) == 60
    assert len({row["sha256"] for row in records}) == 60
    assert all(row["sample_rate_hz"] == 16_000 for row in records)
    assert all(row["channels"] == 1 for row in records)
    assert all(row["duration_seconds"] >= 6.0 for row in records)
    assert all("raw audio is not redistributed" in row["source_license"] for row in records)

    r1_hashes = {row["sha256"] for row in r1["records"]}
    r1_paths = {row["relative_path"] for row in r1["records"]}
    assert not r1_hashes.intersection(row["sha256"] for row in records)
    assert not r1_paths.intersection(row["relative_path"] for row in records)
