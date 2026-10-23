"""Small, explicit audio I/O and sample-domain utilities.

This module deliberately does not resample audio. A caller must choose and
record any resampling policy before passing audio to later research stages.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TypeAlias

import numpy as np
from numpy.typing import ArrayLike, NDArray

AudioArray: TypeAlias = NDArray[np.float64]


@dataclass(frozen=True)
class AudioData:
    """Audio samples together with their declared sample rate."""

    samples: AudioArray
    sample_rate: int

    def __post_init__(self) -> None:
        samples = np.asarray(self.samples, dtype=np.float64)
        if samples.ndim not in (1, 2):
            raise ValueError("samples must have shape (frames,) or (frames, channels)")
        if not np.all(np.isfinite(samples)):
            raise ValueError("samples must contain only finite values")
        if self.sample_rate <= 0:
            raise ValueError("sample_rate must be positive")
        object.__setattr__(self, "samples", samples)


def to_mono(samples: ArrayLike) -> AudioArray:
    """Convert mono or interleaved multi-channel samples to mono."""

    array = np.asarray(samples, dtype=np.float64)
    if array.ndim == 1:
        mono = array.copy()
    elif array.ndim == 2:
        if array.shape[1] == 0:
            raise ValueError("multi-channel samples must contain at least one channel")
        mono = np.mean(array, axis=1)
    else:
        raise ValueError("samples must have shape (frames,) or (frames, channels)")
    if not np.all(np.isfinite(mono)):
        raise ValueError("samples must contain only finite values")
    return mono


def validate_sample_rate(actual: int, expected: int) -> None:
    """Raise ``ValueError`` unless two sample-rate declarations agree."""

    if actual <= 0 or expected <= 0:
        raise ValueError("sample rates must be positive")
    if actual != expected:
        raise ValueError(f"sample-rate mismatch: got {actual} Hz, expected {expected} Hz")


def load_audio(
    path: str | Path,
    *,
    mono: bool = True,
    expected_sample_rate: int | None = None,
) -> AudioData:
    """Load an audio file without implicit resampling."""

    try:
        import soundfile as sf
    except ModuleNotFoundError as error:
        raise RuntimeError(
            "load_audio requires the project runtime dependency 'soundfile'"
        ) from error
    samples, sample_rate = sf.read(path, dtype="float64", always_2d=True)
    if expected_sample_rate is not None:
        validate_sample_rate(int(sample_rate), expected_sample_rate)
    prepared = to_mono(samples) if mono else np.asarray(samples, dtype=np.float64)
    return AudioData(prepared, int(sample_rate))


def normalize_peak(samples: ArrayLike, *, target_peak: float = 1.0) -> AudioArray:
    """Scale samples to a requested absolute peak without modifying input."""

    if target_peak <= 0:
        raise ValueError("target_peak must be positive")
    array = np.asarray(samples, dtype=np.float64)
    if array.ndim not in (1, 2):
        raise ValueError("samples must have shape (frames,) or (frames, channels)")
    if not np.all(np.isfinite(array)):
        raise ValueError("samples must contain only finite values")
    peak = float(np.max(np.abs(array))) if array.size else 0.0
    if peak == 0.0:
        return array.copy()
    return array * (target_peak / peak)
