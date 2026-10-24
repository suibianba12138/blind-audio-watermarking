"""Tests for the additive R1 presence/rejection contract."""

from __future__ import annotations

import numpy as np
import pytest

from audio_watermark.v3_p0 import SpreadSpectrumDetection
from audio_watermark.v3_p0_r1 import (
    calibrate_presence_threshold,
    classify_presence,
    presence_score,
)


def _detection(frame_statistics: tuple[tuple[float, ...], ...]) -> SpreadSpectrumDetection:
    bit_statistics = tuple(float(np.mean(values)) for values in frame_statistics)
    payload = tuple(int(value >= 0.0) for value in bit_statistics)
    return SpreadSpectrumDetection(
        payload_bits=payload,
        bit_statistics=bit_statistics,
        frame_statistics=frame_statistics,
        confidence=float(np.mean(np.abs(bit_statistics))),
    )


def test_presence_score_penalizes_repetition_disagreement() -> None:
    consistent = _detection(((1.0, 1.0, 1.0, 1.0), (-1.0, -1.0, -1.0, -1.0)))
    disagreement = _detection(((1.0, -1.0, 1.0, -1.0), (-1.0, 1.0, -1.0, 1.0)))

    assert presence_score(consistent) > presence_score(disagreement)


def test_threshold_calibration_uses_development_scores_and_not_reject_all() -> None:
    calibration = calibrate_presence_threshold(
        positive_scores=(0.80, 0.90, 1.00),
        negative_scores=(0.05, 0.10, 0.20),
    )

    assert 0.20 < calibration.threshold < 0.80
    assert calibration.positive_detection_rate == 1.0
    assert calibration.false_positive_rate == 0.0
    assert classify_presence(0.90, calibration.threshold)
    assert not classify_presence(0.10, calibration.threshold)


def test_calibration_rejects_empty_or_nonfinite_scores() -> None:
    with pytest.raises(ValueError):
        calibrate_presence_threshold(positive_scores=(), negative_scores=(0.1,))
    with pytest.raises(ValueError):
        calibrate_presence_threshold(positive_scores=(np.nan,), negative_scores=(0.1,))
