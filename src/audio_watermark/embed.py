"""Fixed Patchwork-style transform-domain embedding for the P1 baseline."""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Literal, Sequence

import numpy as np
from numpy.typing import ArrayLike, NDArray

from .carrier import FrequencyBand, carrier_for_frame, carrier_sides
from .framing import WindowSpec, frame_audio, overlap_add
from .packet import normalize_bits
from .transform import inverse_real_fft, real_fft


@dataclass(frozen=True)
class EmbeddingConfig:
    """Configuration for the validated fixed, blind P1 baseline.

    P1 deliberately uses rectangular, non-overlapping FFT blocks.  The
    framing and overlap-add helpers remain the shared signal path, while this
    restriction prevents independently modified overlapping spectra from
    being mixed during synthesis.  Overlapping/windowed spectral embedding is
    deferred until it has a separately validated reconstruction contract.
    """

    mode: Literal["fixed", "adaptive"]
    strength: float
    sample_rate: int = 48000
    n_fft: int = 2048
    hop_length: int = 2048
    window: WindowSpec = None
    payload_bits: int = 32
    frames_per_bit: int = 4
    seed: int = 7
    candidate_band_hz: FrequencyBand = FrequencyBand(1000.0, 10000.0)
    bins_per_group: int = 4
    patches_per_bit: int = 8

    def __post_init__(self) -> None:
        if self.mode not in ("fixed", "adaptive"):
            raise ValueError("mode must be 'fixed' or 'adaptive'")
        if not isfinite(self.strength) or self.strength < 0:
            raise ValueError("strength must be finite and non-negative")
        if self.sample_rate <= 0 or self.n_fft <= 0 or self.hop_length <= 0:
            raise ValueError("sample_rate, n_fft, and hop_length must be positive")
        if self.hop_length > self.n_fft:
            raise ValueError("hop_length must not exceed n_fft")
        if self.mode == "fixed" and self.hop_length != self.n_fft:
            raise ValueError(
                "P1 fixed embedding requires non-overlapping blocks: hop_length must equal n_fft"
            )
        if self.mode == "fixed" and self.window is not None:
            raise ValueError("P1 fixed embedding requires a rectangular window (window=None)")
        if self.payload_bits <= 0 or self.frames_per_bit <= 0:
            raise ValueError("payload_bits and frames_per_bit must be positive")
        if self.seed < 0 or self.bins_per_group <= 0 or self.patches_per_bit <= 0:
            raise ValueError("seed, bin count, and patch count must be valid")
        if self.candidate_band_hz.high_hz > self.sample_rate / 2:
            raise ValueError("carrier band must lie below the Nyquist frequency")


def embed_watermark(
    audio: ArrayLike,
    payload: Sequence[int],
    config: EmbeddingConfig,
    *,
    carrier_groups: object | None = None,
    content_scores: object | None = None,
) -> NDArray:
    """Embed a fixed-strength, pairwise Patchwork-style payload blindly decodable later.

    Each frame's aggregate A/B log-magnitude difference is quantized onto one
    of two public binary lattices. The quantization correction is distributed
    symmetrically over the selected A/B bins, preserving every pair midpoint.
    The carrier assignment is derived independently for each frame from the
    public seed.
    """

    if config.mode != "fixed":
        raise NotImplementedError("adaptive embedding is outside the P1 scope")
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
            group = carrier_for_frame(
                sample_rate=config.sample_rate,
                n_fft=config.n_fft,
                band=config.candidate_band_hz,
                bins_per_group=config.bins_per_group,
                patches_per_bit=config.patches_per_bit,
                seed=config.seed,
                frame_index=frame_index,
            )
            spectra[frame_index] = _embed_spectrum(spectra[frame_index], group, bit, config.strength)

    reconstructed_frames = inverse_real_fft(spectra, config.n_fft)
    marked = overlap_add(
        reconstructed_frames,
        config.hop_length,
        window=config.window,
        length=samples.size,
    )
    if not np.all(np.isfinite(marked)):
        raise FloatingPointError("embedding produced non-finite samples")
    return marked


def _validate_audio(audio: ArrayLike) -> NDArray[np.float64]:
    samples = np.asarray(audio, dtype=np.float64)
    if samples.ndim != 1:
        raise ValueError("audio must be one-dimensional")
    if samples.size == 0 or not np.all(np.isfinite(samples)):
        raise ValueError("audio must be non-empty and finite")
    return samples


def _embed_spectrum(
    spectrum: NDArray[np.complex128],
    group: object,
    bit: int,
    strength: float,
) -> NDArray[np.complex128]:
    """Apply host-preserving binary lattice quantization while preserving phase."""

    a_bins, b_bins = carrier_sides(group)
    modified = np.asarray(spectrum, dtype=np.complex128).copy()
    if strength == 0.0:
        return modified

    magnitudes = np.maximum(np.abs(spectrum), np.finfo(np.float64).tiny)
    log_magnitudes = np.log(magnitudes)
    host_difference = float(
        np.sum(log_magnitudes[a_bins]) - np.sum(log_magnitudes[b_bins])
    )
    lattice_spacing = 2.0 * strength
    lattice_offset = strength if bit == 1 else 0.0
    target_difference = lattice_spacing * np.rint(
        (host_difference - lattice_offset) / lattice_spacing
    ) + lattice_offset
    correction = target_difference - host_difference
    per_bin_correction = correction / (2.0 * a_bins.size)
    for a_bin, b_bin in zip(a_bins, b_bins):
        a_magnitude = np.exp(log_magnitudes[a_bin] + per_bin_correction)
        b_magnitude = np.exp(log_magnitudes[b_bin] - per_bin_correction)
        modified[a_bin] = a_magnitude * np.exp(1j * np.angle(spectrum[a_bin]))
        modified[b_bin] = b_magnitude * np.exp(1j * np.angle(spectrum[b_bin]))
    return modified
