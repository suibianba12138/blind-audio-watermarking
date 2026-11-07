"""Algorithm-independent evidence and scoring structures for V4-P0."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol, Sequence

import numpy as np

from .metrics import bit_error_rate


@dataclass(frozen=True)
class DetectionEvidence:
    """Blind detector output before any expected-message scoring."""

    detected: bool
    recovered_message: tuple[int, ...]
    confidence: float
    presence_score: float
    reject_reason: str | None


class WatermarkAdapter(Protocol):
    """Minimal adapter boundary for V3, V4, or external model wrappers."""

    name: str
    native_sample_rate: int
    native_message_bits: int

    def embed(self, audio: np.ndarray, message: Sequence[int], config: Any) -> np.ndarray:
        """Return marked audio without receiving evaluation labels."""

    def detect(self, audio: np.ndarray, config: Any) -> DetectionEvidence:
        """Return blind evidence from received audio and public config only."""


@dataclass(frozen=True)
class ScoredDetection:
    """Post-hoc evaluation fields; expected data never enters the detector."""

    detected: bool
    correct_accepted_recovery: bool | None
    wrong_message_acceptance: bool | None
    logical_ber: float | None


def score_detection(
    evidence: DetectionEvidence,
    *,
    expected_message: Sequence[int] | None,
) -> ScoredDetection:
    """Score blind evidence against an expected message outside detection."""

    recovered = tuple(int(value) for value in evidence.recovered_message)
    if expected_message is None:
        return ScoredDetection(
            detected=bool(evidence.detected),
            correct_accepted_recovery=None,
            wrong_message_acceptance=None,
            logical_ber=None,
        )
    expected = tuple(int(value) for value in expected_message)
    exact = recovered == expected
    return ScoredDetection(
        detected=bool(evidence.detected),
        correct_accepted_recovery=bool(evidence.detected and exact),
        wrong_message_acceptance=bool(evidence.detected and not exact),
        logical_ber=bit_error_rate(np.asarray(expected), np.asarray(recovered)),
    )
