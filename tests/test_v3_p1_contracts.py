"""Regression checks for the frozen V3-P1 operating point."""

from __future__ import annotations

import inspect
import json
from pathlib import Path

from audio_watermark.b1_soft import detect_watermark_b1_soft
from audio_watermark.detect import DetectionResult
from scripts.v3_p1_independent_validation import _clipping_fields, _frozen_payload_bits


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "experiments" / "v3_p1" / "CONFIG_FREEZE.json"


def test_p1_configuration_freezes_pilot_operating_point() -> None:
    data = json.loads(CONFIG.read_text(encoding="utf-8"))
    assert data["stage"] == "V3_P1_INDEPENDENT_VALIDATION"
    assert data["strength"] == 1.60
    assert data["soft_code_threshold"] == 0.7855073980199624
    assert data["repeat4_threshold"] == 0.47678591988959035
    assert data["message_seeds"] == [101, 202]
    assert data["sample_rate_hz"] == 48_000
    assert data["duration_seconds"] == 6.0
    assert data["manifest_sha256"]
    assert data["source_sha256"]["src/audio_watermark/b1_soft.py"]
    assert data["selector"]["watermark_seed"] == 7


def test_p1_soft_detector_has_blind_audio_only_contract() -> None:
    parameters = set(inspect.signature(detect_watermark_b1_soft).parameters)
    assert parameters == {"audio", "config", "selector"}
    assert not {"expected_payload", "clean_audio", "identity"}.intersection(parameters)


def test_p1_uses_the_frozen_detection_result_payload_bits_field() -> None:
    result = DetectionResult((1, 0, 1), 0.5)
    assert _frozen_payload_bits(result) == (1, 0, 1)


def test_p1_clipping_report_distinguishes_preexisting_and_introduced_overflow() -> None:
    assert _clipping_fields((0.8, -0.9), (1.1, -0.9)) == {
        "peak_abs_clean": 0.9,
        "peak_abs_marked": 1.1,
        "clean_clipping_flag": 0,
        "clipping_flag": 1,
        "introduced_clipping_flag": 1,
    }
    assert _clipping_fields((1.1, -0.9), (1.2, -0.9))["introduced_clipping_flag"] == 0
