"""Small real-FFT transforms used by the P1 baseline."""

from __future__ import annotations

import numpy as np
from numpy.typing import ArrayLike, NDArray


def real_fft(frames: ArrayLike) -> NDArray[np.complex128]:
    """Compute an ``rfft`` independently for each 2-D frame."""

    array = np.asarray(frames, dtype=np.float64)
    if array.ndim != 2:
        raise ValueError("frames must have shape (frame_count, frame_length)")
    if not np.all(np.isfinite(array)):
        raise ValueError("frames must contain only finite values")
    spectra = np.asarray(np.fft.rfft(array, axis=1), dtype=np.complex128)
    if not np.all(np.isfinite(spectra.real)) or not np.all(np.isfinite(spectra.imag)):
        raise FloatingPointError("forward FFT produced non-finite coefficients")
    return spectra


def inverse_real_fft(spectra: ArrayLike, n_fft: int) -> NDArray[np.float64]:
    """Return real frames from one-sided spectra of a declared FFT length."""

    if n_fft <= 0:
        raise ValueError("n_fft must be positive")
    array = np.asarray(spectra, dtype=np.complex128)
    if array.ndim != 2 or array.shape[1] != n_fft // 2 + 1:
        raise ValueError("spectra shape is inconsistent with n_fft")
    if not np.all(np.isfinite(array.real)) or not np.all(np.isfinite(array.imag)):
        raise ValueError("spectra must contain only finite values")
    frames = np.asarray(np.fft.irfft(array, n=n_fft, axis=1), dtype=np.float64)
    if not np.all(np.isfinite(frames)):
        raise FloatingPointError("inverse FFT produced non-finite samples")
    return frames
