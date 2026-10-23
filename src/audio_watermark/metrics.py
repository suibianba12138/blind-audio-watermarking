"""Simple deterministic metrics used by later experiment reports."""

from __future__ import annotations

import numpy as np
from numpy.typing import ArrayLike


def _validated_bits(bits: ArrayLike, *, name: str) -> np.ndarray:
    values = np.asarray(bits)
    if values.ndim != 1 or values.size == 0:
        raise ValueError(f"{name} must be a non-empty one-dimensional sequence")
    if not np.all(np.isin(values, (0, 1))):
        raise ValueError(f"{name} must contain only 0 and 1")
    return values.astype(np.uint8, copy=False)


def bit_error_rate(reference: ArrayLike, estimate: ArrayLike) -> float:
    """Return the fraction of bit positions that differ."""

    expected = _validated_bits(reference, name="reference")
    actual = _validated_bits(estimate, name="estimate")
    if expected.shape != actual.shape:
        raise ValueError("reference and estimate must have the same shape")
    return float(np.count_nonzero(expected != actual) / expected.size)


def signal_snr(reference: ArrayLike, estimate: ArrayLike) -> float:
    """Return signal-to-noise ratio in dB for a reference and estimate."""

    expected = np.asarray(reference, dtype=np.float64)
    actual = np.asarray(estimate, dtype=np.float64)
    if expected.shape != actual.shape:
        raise ValueError("reference and estimate must have the same shape")
    if expected.ndim == 0 or expected.size == 0:
        raise ValueError("reference and estimate must be non-empty arrays")
    if not np.all(np.isfinite(expected)) or not np.all(np.isfinite(actual)):
        raise ValueError("reference and estimate must be finite arrays")
    signal_power = float(np.mean(expected * expected))
    noise_power = float(np.mean((expected - actual) ** 2))
    if noise_power == 0.0:
        return float("inf")
    if signal_power == 0.0:
        return float("-inf")
    return float(10.0 * np.log10(signal_power / noise_power))
