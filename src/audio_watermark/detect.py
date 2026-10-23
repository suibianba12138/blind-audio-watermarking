"""Blind detection for the fixed P1 Patchwork-style baseline."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

import numpy as np
from numpy.typing import ArrayLike

from .carrier import carrier_for_frame, carrier_sides
from .embed import EmbeddingConfig
from .framing import frame_audio
from .transform import real_fft


@dataclass(frozen=True)
class DetectionResult:
    """Recovered payload and absolute aggregate decision margin."""

    payload_bits: tuple[int, ...]
    confidence: float


def detect_watermark(
    audio: ArrayLike,
    config: EmbeddingConfig,
    *,
    carrier_groups: object | None = None,
) -> DetectionResult:
    """Recover the fixed payload using only the received audio and public config."""

    if config.mode != "fixed":
        raise NotImplementedError("adaptive detection is outside the P1 scope")
    if config.strength == 0.0:
        raise ValueError("positive strength is required for blind detection")
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

    recovered: list[int] = []
    repetition_statistics: list[list[float]] = []
    for bit_index in range(config.payload_bits):
        repetitions: list[float] = []
        for repetition in range(config.frames_per_bit):
            frame_index = bit_index * config.frames_per_bit + repetition
            group = carrier_for_frame(
                sample_rate=config.sample_rate,
                n_fft=config.n_fft,
                band=config.candidate_band_hz,
                bins_per_group=config.bins_per_group,
                patches_per_bit=config.patches_per_bit,
                seed=config.seed,
                frame_index=frame_index,
            )
            repetitions.append(
                _detection_statistic(spectra[frame_index], group, config.strength)
            )
        statistic = float(np.mean(repetitions))
        repetition_statistics.append(repetitions)
        recovered.append(1 if statistic >= 0.0 else 0)

    confidence = _confidence_from_repetitions(repetition_statistics)
    if not np.isfinite(confidence):
        raise FloatingPointError("detection produced a non-finite confidence")
    return DetectionResult(tuple(recovered), confidence)


def _confidence_from_repetitions(
    repetition_statistics: Sequence[Sequence[float]],
) -> float:
    """Return mean absolute bit margin after aggregating repetitions."""

    if not repetition_statistics:
        return 0.0
    bit_margins: list[float] = []
    for statistics in repetition_statistics:
        values = np.asarray(statistics, dtype=np.float64)
        if values.ndim != 1 or values.size == 0:
            raise ValueError("each bit must have non-empty repetition statistics")
        if not np.all(np.isfinite(values)):
            raise FloatingPointError("detection statistics must be finite")
        bit_margins.append(float(np.mean(values)))
    return float(np.mean(np.abs(bit_margins)))


def _detection_statistic(
    spectrum: np.ndarray, group: object, strength: float
) -> float:
    """Return the signed distance margin between the two bit lattices."""

    if strength <= 0.0:
        raise ValueError("strength must be positive for a detection statistic")
    a_bins, b_bins = carrier_sides(group)
    magnitudes = np.maximum(np.abs(spectrum), np.finfo(np.float64).tiny)
    log_magnitudes = np.log(magnitudes)
    received_difference = float(
        np.sum(log_magnitudes[a_bins]) - np.sum(log_magnitudes[b_bins])
    )
    lattice_spacing = 2.0 * strength
    zero_target = lattice_spacing * np.rint(received_difference / lattice_spacing)
    one_target = lattice_spacing * np.rint(
        (received_difference - strength) / lattice_spacing
    ) + strength
    distance_zero = abs(received_difference - zero_target)
    distance_one = abs(received_difference - one_target)
    return float(distance_zero - distance_one)
