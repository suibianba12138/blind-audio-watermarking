"""Bounded audio input/output helpers for the public demo.

Only local files are accepted. Decoding uses WAV support from SciPy and an
explicit FFmpeg argument list for compressed inputs; no shell command is used.
"""

from __future__ import annotations

import math
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from scipy.io import wavfile
from scipy.signal import resample_poly


TARGET_SAMPLE_RATE = 48_000
MIN_DEMO_SECONDS = 6
MAX_DEMO_SECONDS = 30
MAX_INPUT_BYTES = 16 * 1024 * 1024
FFMPEG_TIMEOUT_SECONDS = 120


@dataclass(frozen=True)
class AudioData:
    samples: np.ndarray
    sample_rate: int

    def __post_init__(self) -> None:
        values = np.asarray(self.samples, dtype=np.float64)
        if values.ndim != 1 or values.size == 0 or not np.all(np.isfinite(values)):
            raise ValueError("audio must be non-empty, finite, and mono")
        if self.sample_rate <= 0:
            raise ValueError("sample_rate must be positive")
        object.__setattr__(self, "samples", values)


def _check_input(path: str | Path) -> Path:
    candidate = Path(path)
    if not candidate.is_file():
        raise FileNotFoundError(f"audio file not found: {candidate}")
    if candidate.stat().st_size > MAX_INPUT_BYTES:
        raise ValueError("audio file exceeds the 16 MiB public-demo limit")
    return candidate


def _to_float(samples: np.ndarray) -> np.ndarray:
    values = np.asarray(samples)
    if np.issubdtype(values.dtype, np.integer):
        info = np.iinfo(values.dtype)
        scale = float(max(abs(info.min), info.max))
        values = values.astype(np.float64) / scale
    else:
        values = values.astype(np.float64)
    if values.ndim == 2:
        if values.shape[1] == 0:
            raise ValueError("audio has no channels")
        values = np.mean(values, axis=1)
    if values.ndim != 1 or values.size == 0 or not np.all(np.isfinite(values)):
        raise ValueError("decoded audio is not finite mono audio")
    return values


def _decode_with_ffmpeg(path: Path) -> AudioData:
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        raise RuntimeError("FFmpeg is required to decode non-WAV input")
    with tempfile.TemporaryDirectory(prefix="watermark_decode_") as directory:
        output = Path(directory) / "decoded.wav"
        command = [
            ffmpeg,
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-i",
            str(path),
            "-vn",
            "-ac",
            "1",
            "-ar",
            str(TARGET_SAMPLE_RATE),
            "-c:a",
            "pcm_f32le",
            "-f",
            "wav",
            str(output),
        ]
        try:
            subprocess.run(
                command,
                check=True,
                shell=False,
                capture_output=True,
                text=True,
                timeout=FFMPEG_TIMEOUT_SECONDS,
            )
        except subprocess.CalledProcessError as error:
            detail = (error.stderr or "").strip()[-500:]
            raise RuntimeError(f"FFmpeg decode failed: {detail}") from error
        except subprocess.TimeoutExpired as error:
            raise RuntimeError("FFmpeg decode timed out") from error
        rate, samples = wavfile.read(output)
        return AudioData(_to_float(samples), int(rate))


def decode_audio_file(path: str | Path) -> AudioData:
    """Decode a local WAV or compressed audio file with size limits."""

    candidate = _check_input(path)
    if candidate.suffix.lower() == ".wav":
        rate, samples = wavfile.read(candidate)
        return AudioData(_to_float(samples), int(rate))
    return _decode_with_ffmpeg(candidate)


def resample_audio(audio: AudioData, target_sample_rate: int = TARGET_SAMPLE_RATE) -> AudioData:
    """Resample mono audio deterministically with polyphase filtering."""

    if audio.sample_rate == target_sample_rate:
        return audio
    divisor = math.gcd(audio.sample_rate, target_sample_rate)
    up = target_sample_rate // divisor
    down = audio.sample_rate // divisor
    values = resample_poly(audio.samples, up, down).astype(np.float64)
    return AudioData(values, target_sample_rate)


def prepare_for_demo(
    audio: AudioData,
    *,
    duration_seconds: int | None = None,
    target_sample_rate: int = TARGET_SAMPLE_RATE,
) -> AudioData:
    """Resample, bound, and zero-pad audio for a 6/15/30-second demo mode."""

    if duration_seconds not in (None, 6, 15, 30):
        raise ValueError("duration_seconds must be one of 6, 15, 30, or None")
    prepared = resample_audio(audio, target_sample_rate)
    if prepared.samples.size > MAX_DEMO_SECONDS * target_sample_rate:
        raise ValueError("audio exceeds the 30-second public-demo duration limit")
    requested = duration_seconds or max(MIN_DEMO_SECONDS, int(math.ceil(prepared.samples.size / target_sample_rate)))
    requested = min(requested, MAX_DEMO_SECONDS)
    target_count = requested * target_sample_rate
    values = prepared.samples[:target_count]
    if values.size < target_count:
        values = np.pad(values, (0, target_count - values.size))
    return AudioData(values, target_sample_rate)


def write_wav(path: str | Path, audio: AudioData | np.ndarray, sample_rate: int | None = None) -> Path:
    """Write finite mono float32 WAV samples and return the path."""

    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(audio, AudioData):
        values, rate = audio.samples, audio.sample_rate
    else:
        if sample_rate is None:
            raise ValueError("sample_rate is required for an array")
        values, rate = np.asarray(audio, dtype=np.float64), int(sample_rate)
    if values.ndim != 1 or values.size == 0 or not np.all(np.isfinite(values)):
        raise ValueError("WAV samples must be non-empty, finite, and mono")
    wavfile.write(target, rate, values.astype(np.float32))
    return target
