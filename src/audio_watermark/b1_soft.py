"""Additive B1 soft-statistics and bounded 32-to-8 code pilot.

This module does not change the frozen B1 embedder or hard detector.  It
reuses their continuous signed QIM statistic and adds a fixed binary
evaluation code with 32 physical positions and 8 logical payload bits.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

import numpy as np
from numpy.typing import ArrayLike

from .b1 import CarrierSelector, _validate_b1_inputs
from .detect import _detection_statistic
from .embed import EmbeddingConfig
from .framing import frame_audio
from .transform import real_fft


@dataclass(frozen=True)
class SoftB1Detection:
    """Continuous signed evidence for the 32 physical B1 positions."""

    physical_statistics: tuple[float, ...]
    repetition_statistics: tuple[tuple[float, ...], ...]
    hard_physical_bits: tuple[int, ...]


@dataclass(frozen=True)
class SoftCodeDecode:
    """Blind soft-code result and diagnostic evidence."""

    payload_bits: tuple[int, ...]
    codeword_index: int
    score: float
    margin: float
    presence_score: float
    hard_physical_bits: tuple[int, ...]


def soft_codebook() -> np.ndarray:
    """Return the fixed `[32, 8, 8]` binary evaluation-code codebook.

    Positions enumerate all five-bit points.  The eight basis functions are
    one constant, five linear coordinates, and two quadratic coordinates.
    This is a fixed subcode of the second-order Boolean evaluation code; its
    minimum pairwise Hamming distance is verified by regression tests.
    """

    points = np.asarray(
        [[(index >> coordinate) & 1 for coordinate in range(5)] for index in range(32)],
        dtype=np.uint8,
    )
    basis = np.column_stack(
        (
            np.ones(32, dtype=np.uint8),
            points,
            points[:, 0] & points[:, 1],
            points[:, 0] & points[:, 2],
        )
    )
    codebook = np.empty((256, 32), dtype=np.uint8)
    for index in range(256):
        message_bits = np.asarray(
            [(index >> (7 - bit)) & 1 for bit in range(8)], dtype=np.uint8
        )
        codebook[index] = np.mod(basis @ message_bits, 2).astype(np.uint8)
    return codebook


def _payload_to_index(payload: Sequence[int]) -> int:
    values = tuple(payload)
    if len(values) != 8 or any(int(value) not in (0, 1) for value in values):
        raise ValueError("soft-code payload must contain exactly eight binary bits")
    result = 0
    for value in values:
        result = (result << 1) | int(value)
    return result


def _index_to_payload(index: int) -> tuple[int, ...]:
    return tuple((index >> (7 - bit)) & 1 for bit in range(8))


def encode_soft_payload(payload: Sequence[int]) -> np.ndarray:
    """Encode an 8-bit payload into one fixed 32-bit physical codeword."""

    return soft_codebook()[_payload_to_index(payload)].copy()


def decode_soft_statistics(statistics: ArrayLike) -> SoftCodeDecode:
    """Decode 32 continuous signed B1 statistics without expected payload."""

    values = np.asarray(statistics, dtype=np.float64)
    if values.ndim != 1 or values.size != 32 or not np.all(np.isfinite(values)):
        raise ValueError("soft statistics must be a finite one-dimensional vector of length 32")
    scale = float(np.sum(np.abs(values)))
    if scale <= np.finfo(float).tiny:
        scores = np.zeros(256, dtype=np.float64)
    else:
        signs = 2.0 * soft_codebook().astype(np.float64) - 1.0
        scores = signs @ values / scale
    best = int(np.argmax(scores))
    ordered = np.sort(scores)
    second = float(ordered[-2])
    top = float(scores[best])
    return SoftCodeDecode(
        payload_bits=_index_to_payload(best),
        codeword_index=best,
        score=top,
        margin=top - second,
        presence_score=max(0.0, top),
        hard_physical_bits=tuple(int(value >= 0.0) for value in values),
    )


def detect_watermark_b1_soft(
    audio: ArrayLike,
    config: EmbeddingConfig,
    selector: CarrierSelector,
) -> SoftB1Detection:
    """Blindly return continuous B1 evidence from received audio only."""

    _validate_b1_inputs(config, selector)
    if config.strength == 0.0:
        raise ValueError("positive strength is required for blind detection")
    if config.payload_bits != 32:
        raise ValueError("the bounded soft-code pilot requires 32 physical positions")
    samples = np.asarray(audio, dtype=np.float64)
    if samples.ndim != 1 or samples.size == 0 or not np.all(np.isfinite(samples)):
        raise ValueError("audio must be non-empty, one-dimensional, and finite")
    frames = frame_audio(
        samples,
        frame_length=config.n_fft,
        hop_length=config.hop_length,
        window=config.window,
        pad_end=True,
    )
    required_frames = config.payload_bits * config.frames_per_bit
    if frames.shape[0] < required_frames:
        raise ValueError("audio does not have enough framing capacity for payload")
    spectra = real_fft(frames)
    physical_statistics: list[float] = []
    repetition_statistics: list[tuple[float, ...]] = []
    for bit_index in range(config.payload_bits):
        repetitions = tuple(
            float(
                _detection_statistic(
                    spectra[bit_index * config.frames_per_bit + repetition],
                    selector.group_for_frame(bit_index * config.frames_per_bit + repetition),
                    config.strength,
                )
            )
            for repetition in range(config.frames_per_bit)
        )
        repetition_statistics.append(repetitions)
        physical_statistics.append(float(np.mean(repetitions)))
    return SoftB1Detection(
        physical_statistics=tuple(physical_statistics),
        repetition_statistics=tuple(repetition_statistics),
        hard_physical_bits=tuple(int(value >= 0.0) for value in physical_statistics),
    )


def decode_b1_soft_detection(detection: SoftB1Detection) -> SoftCodeDecode:
    """Decode a previously obtained blind B1 soft detection."""

    return decode_soft_statistics(detection.physical_statistics)
