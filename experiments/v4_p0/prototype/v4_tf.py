"""Bounded V4-P0 time-frequency watermarking candidate.

This module is intentionally independent of the frozen V3 B1/Course V2 path.
It uses a centered Hann-window STFT, key-derived balanced carriers over many
time-frequency frames, local energy scaling, and a blind presence rejector.
It is a development candidate, not a validated production algorithm.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import ceil, floor, isfinite
from typing import Sequence

import numpy as np
from numpy.typing import ArrayLike, NDArray

from .framing import frame_audio, overlap_add
from .transform import inverse_real_fft, real_fft


@dataclass(frozen=True)
class V4TFConfig:
    """Fixed P0 configuration for an 8- or 16-bit payload."""

    payload_bits: int
    strength: float
    sample_rate: int = 48_000
    n_fft: int = 2_048
    hop_length: int = 512
    seed: int = 2_026_1025
    low_hz: float = 1_500.0
    high_hz: float = 12_000.0
    bins_per_frame: int = 96
    presence_threshold: float = 0.02
    window: str = "hann"

    def __post_init__(self) -> None:
        if self.payload_bits not in (8, 16):
            raise ValueError("payload_bits must be 8 or 16")
        if not isfinite(float(self.strength)) or self.strength < 0.0:
            raise ValueError("strength must be finite and non-negative")
        if self.sample_rate <= 0 or self.n_fft <= 0 or self.hop_length <= 0:
            raise ValueError("sample_rate, n_fft, and hop_length must be positive")
        if self.hop_length >= self.n_fft:
            raise ValueError("V4-P0 requires an overlapping STFT: hop_length < n_fft")
        if self.seed < 0 or self.bins_per_frame <= 0 or self.bins_per_frame % 2:
            raise ValueError("seed must be non-negative and bins_per_frame must be positive and even")
        if not 0.0 <= self.low_hz < self.high_hz <= self.sample_rate / 2.0:
            raise ValueError("carrier band must be inside the Nyquist range")
        if not isfinite(float(self.presence_threshold)) or self.presence_threshold < 0.0:
            raise ValueError("presence_threshold must be finite and non-negative")


@dataclass(frozen=True)
class V4TFDetection:
    """Blind V4-P0 output with payload and rejector evidence."""

    detected: bool
    recovered_payload: tuple[int, ...]
    bit_statistics: tuple[float, ...]
    frame_statistics: tuple[tuple[float, ...], ...]
    confidence: float
    presence_score: float
    margin: float
    reject_reason: str | None
    used_frames: int


def _validate_audio(audio: ArrayLike) -> NDArray[np.float64]:
    samples = np.asarray(audio, dtype=np.float64)
    if samples.ndim != 1 or samples.size == 0 or not np.all(np.isfinite(samples)):
        raise ValueError("audio must be non-empty, one-dimensional, and finite")
    return samples


def _centered_frames(
    samples: NDArray[np.float64], config: V4TFConfig
) -> tuple[NDArray[np.float64], int, int]:
    """Return padded/windowed frames and crop metadata for centered STFT."""

    edge = config.n_fft // 2
    mode = "reflect" if samples.size > 1 else "edge"
    padded = np.pad(samples, (edge, edge), mode=mode)
    remainder = (padded.size - config.n_fft) % config.hop_length
    if remainder:
        padded = np.pad(padded, (0, config.hop_length - remainder), mode=mode)
    frames = frame_audio(
        padded,
        frame_length=config.n_fft,
        hop_length=config.hop_length,
        window=config.window,
        pad_end=False,
    )
    return frames, edge, padded.size


def _synthesis(
    spectra: NDArray[np.complex128],
    config: V4TFConfig,
    *,
    edge: int,
    original_length: int,
    padded_length: int,
) -> NDArray[np.float64]:
    reconstructed = overlap_add(
        inverse_real_fft(spectra, config.n_fft),
        config.hop_length,
        window=config.window,
        length=padded_length,
    )
    result = reconstructed[edge : edge + original_length]
    if result.size != original_length or not np.all(np.isfinite(result)):
        raise FloatingPointError("V4-P0 synthesis produced invalid output")
    return np.asarray(result, dtype=np.float64)


def _carrier(config: V4TFConfig, frame_index: int) -> tuple[NDArray[np.int64], NDArray[np.float64]]:
    low_bin = max(1, int(ceil(config.low_hz * config.n_fft / config.sample_rate)))
    high_bin = min(
        config.n_fft // 2 - 1,
        int(floor(config.high_hz * config.n_fft / config.sample_rate)),
    )
    available = np.arange(low_bin, high_bin + 1, dtype=np.int64)
    count = min(config.bins_per_frame, available.size)
    if count % 2:
        count -= 1
    if count < 2:
        raise ValueError("carrier band does not contain enough FFT bins")
    generator = np.random.default_rng(np.random.SeedSequence([config.seed, int(frame_index)]))
    bins = np.sort(generator.choice(available, size=count, replace=False))
    signs = np.ones(count, dtype=np.float64)
    signs[: count // 2] = -1.0
    generator.shuffle(signs)
    return bins, signs


def _salience(log_magnitudes: NDArray[np.float64], bins: NDArray[np.int64]) -> NDArray[np.float64]:
    selected = log_magnitudes[bins]
    center = float(np.median(selected))
    ratio = np.exp(np.clip(selected - center, -4.0, 4.0))
    return np.clip(np.sqrt(ratio), 0.25, 1.0)


def _embed_frame(
    spectrum: NDArray[np.complex128], config: V4TFConfig, frame_index: int, bit: int
) -> NDArray[np.complex128]:
    modified = np.asarray(spectrum, dtype=np.complex128).copy()
    if config.strength == 0.0:
        return modified
    bins, signs = _carrier(config, frame_index)
    magnitudes = np.maximum(np.abs(spectrum), np.finfo(float).tiny)
    logs = np.log(magnitudes)
    weights = _salience(logs, bins)
    delta = (1.0 if bit else -1.0) * float(config.strength) * signs * weights
    delta -= float(np.mean(delta))
    logs[bins] += delta
    modified[bins] = np.exp(logs[bins]) * np.exp(1j * np.angle(spectrum[bins]))
    return modified


def _frame_statistic(
    spectrum: NDArray[np.complex128], config: V4TFConfig, frame_index: int
) -> float:
    bins, signs = _carrier(config, frame_index)
    logs = np.log(np.maximum(np.abs(spectrum), np.finfo(float).tiny))
    values = logs[bins]
    weights = _salience(logs, bins)
    centered = values - float(np.mean(values))
    denominator = float(np.sqrt(np.sum(weights * weights)))
    return float(np.sum(centered * signs * weights) / max(denominator, np.finfo(float).tiny))


def stft_roundtrip(audio: ArrayLike, *, sample_rate: int = 48_000) -> NDArray[np.float64]:
    """Reconstruct audio through the centered Hann STFT without embedding."""

    samples = _validate_audio(audio)
    config = V4TFConfig(payload_bits=8, strength=0.0, sample_rate=sample_rate)
    frames, edge, padded_length = _centered_frames(samples, config)
    return _synthesis(real_fft(frames), config, edge=edge, original_length=samples.size, padded_length=padded_length)


def embed_v4_tf(
    audio: ArrayLike, payload: Sequence[int], config: V4TFConfig
) -> NDArray[np.float64]:
    """Embed an 8- or 16-bit payload over all available STFT frames."""

    samples = _validate_audio(audio)
    bits = tuple(int(value) for value in payload)
    if len(bits) != config.payload_bits or any(value not in (0, 1) for value in bits):
        raise ValueError("payload length or values do not match V4-TF config")
    frames, edge, padded_length = _centered_frames(samples, config)
    spectra = real_fft(frames)
    for frame_index in range(spectra.shape[0]):
        bit = bits[frame_index % config.payload_bits]
        spectra[frame_index] = _embed_frame(spectra[frame_index], config, frame_index, bit)
    return _synthesis(
        spectra,
        config,
        edge=edge,
        original_length=samples.size,
        padded_length=padded_length,
    )


def detect_v4_tf(audio: ArrayLike, config: V4TFConfig) -> V4TFDetection:
    """Blindly decode the V4-TF candidate from received audio only."""

    samples = _validate_audio(audio)
    frames, _, _ = _centered_frames(samples, config)
    spectra = real_fft(frames)
    per_bit: list[list[float]] = [[] for _ in range(config.payload_bits)]
    for frame_index, spectrum in enumerate(spectra):
        per_bit[frame_index % config.payload_bits].append(
            _frame_statistic(spectrum, config, frame_index)
        )
    frame_statistics = tuple(tuple(values) for values in per_bit)
    bit_statistics = tuple(float(np.mean(values)) for values in per_bit)
    recovered = tuple(int(value >= 0.0) for value in bit_statistics)
    presence_score = float(np.mean(np.abs(bit_statistics)))
    confidence = float(np.mean(np.abs(bit_statistics)))
    margin = float(np.min(np.abs(bit_statistics)))
    detected = bool(presence_score >= config.presence_threshold)
    reject_reason = None if detected else "presence_score_below_threshold"
    return V4TFDetection(
        detected=detected,
        recovered_payload=recovered,
        bit_statistics=bit_statistics,
        frame_statistics=frame_statistics,
        confidence=confidence,
        presence_score=presence_score,
        margin=margin,
        reject_reason=reject_reason,
        used_frames=int(spectra.shape[0]),
    )
