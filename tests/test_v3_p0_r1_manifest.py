"""Regression checks for the frozen R1 metadata manifest."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path


MANIFEST = Path(__file__).resolve().parents[1] / "configs" / "v3_p0_r1_real_audio_manifest.json"


def test_r1_manifest_is_source_disjoint_and_balanced() -> None:
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    records = data["records"]

    assert data["status"] == "FROZEN"
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
