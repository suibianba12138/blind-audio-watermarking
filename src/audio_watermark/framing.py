"""Deterministic frame extraction and overlap-add helpers."""

from __future__ import annotations

from typing import TypeAlias

import numpy as np
from numpy.typing import ArrayLike, NDArray
from scipy.signal import get_window as scipy_get_window

WindowSpec: TypeAlias = str | ArrayLike | None


def get_window(window: WindowSpec, frame_length: int) -> NDArray[np.float64]:
    """Return a validated analysis window of ``frame_length`` samples."""

    if frame_length <= 0:
        raise ValueError("frame_length must be positive")
    if window is None:
        return np.ones(frame_length, dtype=np.float64)
    if isinstance(window, str):
        values = scipy_get_window(window, frame_length, fftbins=True)
    else:
        values = np.asarray(window, dtype=np.float64)
    values = np.asarray(values, dtype=np.float64)
    if values.shape != (frame_length,):
        raise ValueError("window must have exactly frame_length values")
    if not np.all(np.isfinite(values)):
        raise ValueError("window must contain only finite values")
    return values.copy()


def _frame_count(sample_count: int, frame_length: int, hop_length: int, pad_end: bool) -> int:
    if sample_count == 0:
        return 0
    if sample_count <= frame_length:
        return 1 if pad_end or sample_count == frame_length else 0
    available = sample_count - frame_length
    return 1 + ((available + hop_length - 1) // hop_length if pad_end else available // hop_length)


def frame_audio(
    audio: ArrayLike,
    frame_length: int,
    hop_length: int,
    *,
    window: WindowSpec = None,
    pad_end: bool = True,
) -> NDArray[np.float64]:
    """Split one-dimensional audio into zero-padded, optionally windowed frames."""

    if frame_length <= 0 or hop_length <= 0:
        raise ValueError("frame_length and hop_length must be positive")
    samples = np.asarray(audio, dtype=np.float64)
    if samples.ndim != 1:
        raise ValueError("audio must be one-dimensional")
    if not np.all(np.isfinite(samples)):
        raise ValueError("audio must contain only finite values")
    count = _frame_count(samples.size, frame_length, hop_length, pad_end)
    frames = np.zeros((count, frame_length), dtype=np.float64)
    for index in range(count):
        start = index * hop_length
        stop = min(start + frame_length, samples.size)
        frames[index, : max(0, stop - start)] = samples[start:stop]
    if window is not None:
        frames *= get_window(window, frame_length)
    return frames


def overlap_add(
    frames: ArrayLike,
    hop_length: int,
    *,
    window: WindowSpec = None,
    length: int | None = None,
) -> NDArray[np.float64]:
    """Reconstruct audio by overlap-adding frames with window normalization."""

    if hop_length <= 0:
        raise ValueError("hop_length must be positive")
    array = np.asarray(frames, dtype=np.float64)
    if array.ndim != 2:
        raise ValueError("frames must have shape (frame_count, frame_length)")
    if not np.all(np.isfinite(array)):
        raise ValueError("frames must contain only finite values")
    frame_count, frame_length = array.shape
    output_length = 0 if frame_count == 0 else (frame_count - 1) * hop_length + frame_length
    if length is not None and (length < 0 or length > output_length):
        raise ValueError("length must be between zero and the padded output length")
    target_length = output_length if length is None else length
    if frame_count == 0:
        return np.zeros(target_length, dtype=np.float64)

    weights = get_window(window, frame_length)
    result = np.zeros(output_length, dtype=np.float64)
    normalization = np.zeros(output_length, dtype=np.float64)
    for index, frame in enumerate(array):
        start = index * hop_length
        stop = start + frame_length
        result[start:stop] += frame * weights
        normalization[start:stop] += weights * weights
    reconstructed = np.zeros_like(result)
    np.divide(result, normalization, out=reconstructed, where=normalization > np.finfo(float).eps)
    return reconstructed[:target_length]
