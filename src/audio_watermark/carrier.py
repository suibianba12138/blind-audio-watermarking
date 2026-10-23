"""Deterministic carriers for the fixed P1 baseline and deferred interfaces."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class FrequencyBand:
    """Inclusive frequency range in hertz for a future carrier pool."""

    low_hz: float
    high_hz: float

    def __post_init__(self) -> None:
        if not np.isfinite(self.low_hz) or not np.isfinite(self.high_hz):
            raise ValueError("frequency band must contain finite values")
        if self.low_hz < 0 or self.high_hz <= self.low_hz:
            raise ValueError("frequency band must satisfy 0 <= low_hz < high_hz")


@dataclass(frozen=True)
class CarrierGroup:
    """A future Patchwork A/B group represented by FFT bins and signs."""

    bins: tuple[int, ...]
    signs: tuple[int, ...]

    def __post_init__(self) -> None:
        if not self.bins or len(self.bins) != len(self.signs):
            raise ValueError("bins and signs must be non-empty and equally sized")
        if any(index < 0 for index in self.bins):
            raise ValueError("carrier bins must be non-negative")
        if any(sign not in (-1, 1) for sign in self.signs):
            raise ValueError("carrier signs must be -1 or 1")


def generate_candidate_carriers(
    *,
    sample_rate: int,
    n_fft: int,
    band: FrequencyBand,
    bins_per_group: int,
    patches_per_bit: int,
    seed: int,
) -> tuple[CarrierGroup, ...]:
    """Generate one deterministic, balanced A/B carrier group.

    The group contains ``bins_per_group * patches_per_bit`` positive-sign bins
    and the same number of negative-sign bins. The name and shape retain the
    P0 contract while making the fixed P1 carrier reproducible.
    """

    if sample_rate <= 0 or n_fft <= 0:
        raise ValueError("sample_rate and n_fft must be positive")
    if bins_per_group <= 0 or patches_per_bit <= 0:
        raise ValueError("bins_per_group and patches_per_bit must be positive")
    if seed < 0:
        raise ValueError("seed must be non-negative")
    if band.high_hz > sample_rate / 2:
        raise ValueError("carrier band must lie below the Nyquist frequency")

    low_bin = max(1, int(np.ceil(band.low_hz * n_fft / sample_rate)))
    high_bin = min(n_fft // 2 - 1, int(np.floor(band.high_hz * n_fft / sample_rate)))
    available = np.arange(low_bin, high_bin + 1, dtype=np.int64)
    bins_per_side = bins_per_group * patches_per_bit
    required = 2 * bins_per_side
    if available.size < required:
        raise ValueError("carrier band does not contain enough FFT bins")

    generator = np.random.default_rng(seed)
    selected = generator.choice(available, size=required, replace=False)
    signs = np.concatenate(
        (np.ones(bins_per_side, dtype=np.int8), -np.ones(bins_per_side, dtype=np.int8))
    )
    return (CarrierGroup(tuple(int(value) for value in selected), tuple(int(value) for value in signs)),)


def carrier_for_frame(
    *,
    sample_rate: int,
    n_fft: int,
    band: FrequencyBand,
    bins_per_group: int,
    patches_per_bit: int,
    seed: int,
    frame_index: int,
) -> CarrierGroup:
    """Rebuild the same fixed carrier assignment for one frame."""

    if frame_index < 0:
        raise ValueError("frame_index must be non-negative")
    derived_seed = int(
        np.random.SeedSequence([seed, frame_index]).generate_state(1, dtype=np.uint64)[0]
    )
    return generate_candidate_carriers(
        sample_rate=sample_rate,
        n_fft=n_fft,
        band=band,
        bins_per_group=bins_per_group,
        patches_per_bit=patches_per_bit,
        seed=derived_seed,
    )[0]


def carrier_sides(group: CarrierGroup) -> tuple[np.ndarray, np.ndarray]:
    """Return the positive-sign (A) and negative-sign (B) bin arrays."""

    bins = np.asarray(group.bins, dtype=np.int64)
    signs = np.asarray(group.signs, dtype=np.int8)
    return bins[signs == 1], bins[signs == -1]


def select_codec_aware_carriers(*, carrier_pool: tuple[CarrierGroup, ...], stability_map: object) -> tuple[CarrierGroup, ...]:
    """Define the future codec-aware carrier-selection contract."""

    raise NotImplementedError(
        "codec-aware carrier selection is intentionally deferred beyond P0"
    )
