"""Small additive P0 keyed spread-spectrum prototype.

This module is deliberately separate from the frozen B0/B1/Course V2 path.
It uses a keyed, balanced sign sequence over FFT bins, local log-magnitude
normalization, and a soft correlation detector.  It is a research probe, not
an approved V3 algorithm and has no codec or perceptual-quality guarantee.
"""

from __future__ import annotations

from dataclasses import dataclass
from numbers import Integral
from typing import Sequence

import numpy as np
from numpy.typing import ArrayLike, NDArray

from .embed import _validate_audio
from .framing import frame_audio, overlap_add
from .transform import inverse_real_fft, real_fft


@dataclass(frozen=True)
class SpreadSpectrumConfig:
    """Configuration for the single-bit or 8-bit P0 research probe."""

    payload_bits: int
    frames_per_bit: int = 16
    strength: float = 0.08
    sample_rate: int = 48_000
    n_fft: int = 2_048
    hop_length: int = 2_048
    seed: int = 23
    low_hz: float = 1_000.0
    high_hz: float = 10_000.0
    bins_per_frame: int = 256
    local_bands: int = 8

    def __post_init__(self) -> None:
        if self.payload_bits not in (1, 8):
            raise ValueError("P0 prototype payload_bits must be 1 or 8")
        if self.frames_per_bit <= 0 or self.sample_rate <= 0:
            raise ValueError("frames_per_bit and sample_rate must be positive")
        if self.n_fft <= 0 or self.hop_length != self.n_fft:
            raise ValueError("P0 prototype uses non-overlapping rectangular FFT frames")
        if not np.isfinite(self.strength) or self.strength < 0.0:
            raise ValueError("strength must be finite and non-negative")
        if self.seed < 0 or self.bins_per_frame <= 0 or self.local_bands <= 0:
            raise ValueError("seed, bins_per_frame, and local_bands must be valid")
        if not 0.0 <= self.low_hz < self.high_hz <= self.sample_rate / 2.0:
            raise ValueError("frequency band must be inside the Nyquist range")


@dataclass(frozen=True)
class SpreadSpectrumDetection:
    """Blind detection output with signed per-bit soft evidence."""

    payload_bits: tuple[int, ...]
    bit_statistics: tuple[float, ...]
    frame_statistics: tuple[tuple[float, ...], ...]
    confidence: float


def _validate_payload(payload: Sequence[int], expected_size: int) -> tuple[int, ...]:
    values = tuple(payload)
    if len(values) != expected_size:
        raise ValueError("payload length does not match prototype configuration")
    if any(isinstance(value, bool) or int(value) not in (0, 1) for value in values):
        raise ValueError("payload must contain only binary values")
    return tuple(int(value) for value in values)


def _carrier(config: SpreadSpectrumConfig, frame_index: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return bins, balanced signs, and local-band labels for one frame."""

    low_bin = max(1, int(np.ceil(config.low_hz * config.n_fft / config.sample_rate)))
    high_bin = min(
        config.n_fft // 2 - 1,
        int(np.floor(config.high_hz * config.n_fft / config.sample_rate)),
    )
    available = np.arange(low_bin, high_bin + 1, dtype=np.int64)
    count = min(config.bins_per_frame, available.size)
    generator = np.random.default_rng(
        np.random.SeedSequence([config.seed, int(frame_index)])
    )
    bins = np.sort(generator.choice(available, size=count, replace=False))
    band_ids = np.minimum(
        config.local_bands - 1,
        ((bins - low_bin) * config.local_bands // max(1, high_bin - low_bin + 1)),
    ).astype(np.int64)
    signs = np.empty(count, dtype=np.float64)
    for band in range(config.local_bands):
        positions = np.flatnonzero(band_ids == band)
        if positions.size == 0:
            continue
        values = np.ones(positions.size, dtype=np.float64)
        values[: positions.size // 2] = -1.0
        generator.shuffle(values)
        signs[positions] = values
    return bins, signs, band_ids


def _energy_weights(
    log_magnitudes: np.ndarray,
    bins: np.ndarray,
    band_ids: np.ndarray,
    local_bands: int,
) -> tuple[np.ndarray, np.ndarray]:
    """Return locally centered log magnitudes and received-side weights."""

    selected = log_magnitudes[bins]
    centered = np.empty_like(selected)
    weights = np.empty_like(selected)
    for band in range(local_bands):
        positions = np.flatnonzero(band_ids == band)
        if positions.size == 0:
            continue
        values = selected[positions]
        center = float(np.mean(values))
        centered[positions] = values - center
        median_magnitude = float(np.exp(np.median(values)))
        magnitude = np.exp(values)
        weights[positions] = np.clip(
            magnitude / max(median_magnitude, np.finfo(float).tiny), 0.25, 1.0
        )
    return centered, weights


def _modify_spectrum(
    spectrum: np.ndarray,
    config: SpreadSpectrumConfig,
    frame_index: int,
    bit: int,
) -> np.ndarray:
    modified = np.asarray(spectrum, dtype=np.complex128).copy()
    if config.strength == 0.0:
        return modified
    bins, signs, band_ids = _carrier(config, frame_index)
    magnitudes = np.maximum(np.abs(spectrum), np.finfo(float).tiny)
    log_magnitudes = np.log(magnitudes)
    _, weights = _energy_weights(log_magnitudes, bins, band_ids, config.local_bands)
    direction = 1.0 if bit else -1.0
    log_magnitudes[bins] += direction * config.strength * signs * weights
    modified[bins] = np.exp(log_magnitudes[bins]) * np.exp(1j * np.angle(spectrum[bins]))
    return modified


def _frame_statistic(
    spectrum: np.ndarray,
    config: SpreadSpectrumConfig,
    frame_index: int,
) -> float:
    bins, signs, band_ids = _carrier(config, frame_index)
    magnitudes = np.maximum(np.abs(spectrum), np.finfo(float).tiny)
    centered, weights = _energy_weights(
        np.log(magnitudes), bins, band_ids, config.local_bands
    )
    denominator = float(np.sqrt(np.sum(weights * weights)))
    if denominator <= 0.0:
        raise FloatingPointError("prototype carrier normalization is zero")
    return float(np.sum(centered * signs * weights) / denominator)


def embed_spread_spectrum(
    audio: ArrayLike,
    payload: Sequence[int],
    config: SpreadSpectrumConfig,
) -> NDArray[np.float64]:
    """Embed one-bit or eight-bit payload using the additive P0 probe."""

    samples = _validate_audio(audio)
    bits = _validate_payload(payload, config.payload_bits)
    frames = frame_audio(
        samples,
        frame_length=config.n_fft,
        hop_length=config.hop_length,
        window=None,
        pad_end=True,
    )
    required_frames = config.payload_bits * config.frames_per_bit
    if frames.shape[0] < required_frames:
        raise ValueError("audio does not have enough framing capacity for payload")
    spectra = real_fft(frames)
    for bit_index, bit in enumerate(bits):
        for repetition in range(config.frames_per_bit):
            frame_index = bit_index * config.frames_per_bit + repetition
            spectra[frame_index] = _modify_spectrum(
                spectra[frame_index], config, frame_index, bit
            )
    marked = overlap_add(
        inverse_real_fft(spectra, config.n_fft), config.hop_length, window=None, length=samples.size
    )
    if not np.all(np.isfinite(marked)):
        raise FloatingPointError("P0 prototype produced non-finite samples")
    return np.asarray(marked, dtype=np.float64)


def detect_spread_spectrum(
    audio: ArrayLike,
    config: SpreadSpectrumConfig,
) -> SpreadSpectrumDetection:
    """Blindly recover the P0 probe from received audio only."""

    if config.strength == 0.0:
        raise ValueError("positive strength is required for prototype detection")
    samples = _validate_audio(audio)
    frames = frame_audio(
        samples,
        frame_length=config.n_fft,
        hop_length=config.hop_length,
        window=None,
        pad_end=True,
    )
    required_frames = config.payload_bits * config.frames_per_bit
    if frames.shape[0] < required_frames:
        raise ValueError("audio does not have enough framing capacity for payload")
    spectra = real_fft(frames)
    frame_statistics: list[tuple[float, ...]] = []
    bit_statistics: list[float] = []
    recovered: list[int] = []
    for bit_index in range(config.payload_bits):
        repetitions = tuple(
            _frame_statistic(
                spectra[bit_index * config.frames_per_bit + repetition],
                config,
                bit_index * config.frames_per_bit + repetition,
            )
            for repetition in range(config.frames_per_bit)
        )
        statistic = float(np.mean(repetitions))
        frame_statistics.append(repetitions)
        bit_statistics.append(statistic)
        recovered.append(int(statistic >= 0.0))
    confidence = float(np.mean(np.abs(bit_statistics))) if bit_statistics else 0.0
    return SpreadSpectrumDetection(
        payload_bits=tuple(recovered),
        bit_statistics=tuple(bit_statistics),
        frame_statistics=tuple(frame_statistics),
        confidence=confidence,
    )
