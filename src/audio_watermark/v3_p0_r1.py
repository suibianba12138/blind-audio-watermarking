"""Small, blind presence/rejection helpers for the V3-P0-R1 study.

The helpers are deliberately independent of the expected payload.  A message
decoder may produce a candidate payload, while this module decides whether the
received signal has enough repeated signed evidence to accept that candidate.
The threshold is a development-set calibration artifact, not a probability
and not a replacement for an independent validation protocol.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

import numpy as np

from .v3_p0 import SpreadSpectrumDetection


@dataclass(frozen=True)
class PresenceCalibration:
    """Frozen threshold and development-set diagnostics."""

    threshold: float
    positive_detection_rate: float
    false_positive_rate: float
    positive_count: int
    negative_count: int


def presence_score(detection: SpreadSpectrumDetection) -> float:
    """Return blind repeated-evidence strength without using the true payload.

    For each bit, the signed repetition statistics are first aggregated.  The
    absolute aggregate is multiplied by a coherence term,
    ``abs(mean(repetitions)) / mean(abs(repetitions))``.  Thus repetitions
    with conflicting signs cannot look as certain as repetitions with the same
    sign.  The returned mean is a diagnostic score only; it is not calibrated
    probability.
    """

    bit_scores: list[float] = []
    for repetitions in detection.frame_statistics:
        values = np.asarray(repetitions, dtype=np.float64)
        if values.ndim != 1 or values.size == 0 or not np.all(np.isfinite(values)):
            raise ValueError("frame statistics must be finite non-empty vectors")
        mean_value = float(np.mean(values))
        mean_abs = float(np.mean(np.abs(values)))
        coherence = abs(mean_value) / mean_abs if mean_abs > 0.0 else 0.0
        bit_scores.append(abs(mean_value) * coherence)
    return float(np.mean(bit_scores)) if bit_scores else 0.0


def classify_presence(score: float, threshold: float) -> bool:
    """Apply a frozen threshold to one blind presence score."""

    if not np.isfinite(score) or not np.isfinite(threshold):
        raise ValueError("score and threshold must be finite")
    return bool(score >= threshold)


def calibrate_presence_threshold(
    *, positive_scores: Sequence[float], negative_scores: Sequence[float]
) -> PresenceCalibration:
    """Choose a threshold from development scores using Youden's J statistic.

    The two score collections are expected to come from the development split
    only.  The deterministic tie-break prefers higher positive detection and
    then the lower threshold among equally good operating points, while
    excluding a reject-all operating point.
    """

    positive = np.asarray(tuple(positive_scores), dtype=np.float64)
    negative = np.asarray(tuple(negative_scores), dtype=np.float64)
    if positive.ndim != 1 or negative.ndim != 1 or positive.size == 0 or negative.size == 0:
        raise ValueError("positive and negative calibration scores must be non-empty")
    if not np.all(np.isfinite(positive)) or not np.all(np.isfinite(negative)):
        raise ValueError("calibration scores must be finite")

    values = np.unique(np.concatenate((positive, negative)))
    midpoints = (values[:-1] + values[1:]) / 2.0
    candidates = np.unique(np.concatenate((values, midpoints)))
    eligible: list[tuple[float, float, float, float]] = []
    for threshold in candidates:
        tpr = float(np.mean(positive >= threshold))
        fpr = float(np.mean(negative >= threshold))
        if tpr == 0.0:
            continue
        eligible.append((tpr - fpr, tpr, -fpr, -float(threshold)))
    if not eligible:
        threshold = float(np.max(positive))
    else:
        threshold = -max(eligible)[3]
    tpr = float(np.mean(positive >= threshold))
    fpr = float(np.mean(negative >= threshold))
    return PresenceCalibration(
        threshold=threshold,
        positive_detection_rate=tpr,
        false_positive_rate=fpr,
        positive_count=int(positive.size),
        negative_count=int(negative.size),
    )
