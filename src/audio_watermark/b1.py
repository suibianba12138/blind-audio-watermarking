"""Independent B1 codec-stable carrier path.

The default B0 embedder and detector are intentionally untouched. B1 shares
their transform, lattice, and detection primitives but receives its carrier
group from a frozen public selector.
"""

from __future__ import annotations

from typing import Protocol, Sequence

import numpy as np
from numpy.typing import ArrayLike, NDArray

from .carrier import CarrierGroup
from .detect import (
    DetectionResult,
    _confidence_from_repetitions,
    _detection_statistic,
)
from .embed import EmbeddingConfig, _embed_spectrum, _validate_audio
from .framing import frame_audio, overlap_add
from .packet import normalize_bits
from .transform import inverse_real_fft, real_fft


class CarrierSelector(Protocol):
    """Public selector contract available to both blind B1 endpoints."""

    def group_for_frame(self, frame_index: int) -> CarrierGroup:
        """Return the public deterministic carrier group for one frame."""


def embed_watermark_b1(
    audio: ArrayLike,
    payload: Sequence[int],
    config: EmbeddingConfig,
    selector: CarrierSelector,
) -> NDArray[np.float64]:
    """Embed with a frozen codec-aware selector and the unchanged B0 lattice."""

    _validate_b1_inputs(config, selector)
    samples = _validate_audio(audio)
    bits = normalize_bits(payload, name="payload")
    if len(bits) != config.payload_bits:
        raise ValueError("payload length does not match config.payload_bits")
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
    for bit_index, bit in enumerate(bits):
        for repetition in range(config.frames_per_bit):
            frame_index = bit_index * config.frames_per_bit + repetition
            spectra[frame_index] = _embed_spectrum(
                spectra[frame_index],
                selector.group_for_frame(frame_index),
                bit,
                config.strength,
            )
    reconstructed_frames = inverse_real_fft(spectra, config.n_fft)
    marked = overlap_add(
        reconstructed_frames,
        config.hop_length,
        window=config.window,
        length=samples.size,
    )
    if not np.all(np.isfinite(marked)):
        raise FloatingPointError("B1 embedding produced non-finite samples")
    return np.asarray(marked, dtype=np.float64)


def detect_watermark_b1(
    audio: ArrayLike,
    config: EmbeddingConfig,
    selector: CarrierSelector,
) -> DetectionResult:
    """Blindly detect B1 using received audio, config, map, and public seed."""

    _validate_b1_inputs(config, selector)
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
            repetitions.append(
                _detection_statistic(
                    spectra[frame_index],
                    selector.group_for_frame(frame_index),
                    config.strength,
                )
            )
        statistic = float(np.mean(repetitions))
        repetition_statistics.append(repetitions)
        recovered.append(1 if statistic >= 0.0 else 0)
    confidence = _confidence_from_repetitions(repetition_statistics)
    if not np.isfinite(confidence):
        raise FloatingPointError("B1 detection produced a non-finite confidence")
    return DetectionResult(tuple(recovered), confidence)


def _validate_b1_inputs(config: EmbeddingConfig, selector: CarrierSelector) -> None:
    if not isinstance(config, EmbeddingConfig):
        raise TypeError("config must be an EmbeddingConfig")
    if config.mode != "fixed":
        raise NotImplementedError("B1 currently supports the fixed B0 framing only")
    if selector is None or not callable(getattr(selector, "group_for_frame", None)):
        raise TypeError("B1 requires a public carrier selector")
