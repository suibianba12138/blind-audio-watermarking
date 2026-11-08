"""Thin, independent adapters for the frozen V3 and SilentCipher engines."""
from __future__ import annotations

import importlib
import os
import sys
import time
import types
from pathlib import Path
from typing import Any

import numpy as np

from .audio_io import AudioData
from .silentcipher_adapter import SilentCipherAdapter, UNKNOWN, IDENTIFIED, DECODE_ERROR

_SILENTCIPHER: SilentCipherAdapter | None = None
_V3_API: Any = None


def silentcipher_backend() -> SilentCipherAdapter:
    global _SILENTCIPHER
    if _SILENTCIPHER is None:
        _SILENTCIPHER = SilentCipherAdapter(cpu_threads=int(os.environ.get("V4_CPU_THREADS", "4")))
    return _SILENTCIPHER


def _v3_api():
    global _V3_API
    if _V3_API is not None:
        return _V3_API
    root_value = os.environ.get("V3_SOURCE_ROOT")
    if not root_value:
        raise RuntimeError("V3_CONFIGURATION_MISSING")
    root = Path(root_value).resolve()
    if not (root / "app/v3_api.py").is_file() or not (root / "src/audio_watermark").is_dir():
        raise RuntimeError("V3_FILES_MISSING")
    sys.path.insert(0, str(root / "src"))
    package_name = "_v4_frozen_v3_app"
    if package_name not in sys.modules:
        package = types.ModuleType(package_name)
        package.__path__ = [str(root / "app")]
        package.__package__ = package_name
        sys.modules[package_name] = package
    _V3_API = importlib.import_module(f"{package_name}.v3_api")
    return _V3_API


def embed_neural(samples: np.ndarray, message: tuple[int, ...], sample_rate: int) -> dict[str, Any]:
    if sample_rate != 44100 or len(samples) != sample_rate * 12:
        raise ValueError("SilentCipher requires exactly 12 seconds at 44.1 kHz")
    return silentcipher_backend().embed(samples, message, sample_rate)


def decode_neural(samples: np.ndarray, sample_rate: int) -> dict[str, Any]:
    """Decode candidate from received samples only. No reference/session args."""
    if sample_rate != 44100 or len(samples) != sample_rate * 12:
        raise ValueError("SilentCipher requires exactly 12 seconds at 44.1 kHz")
    return silentcipher_backend().decode(samples, sample_rate)


def detect_neural(samples: np.ndarray, sample_rate: int) -> dict[str, Any]:
    if sample_rate != 44100 or len(samples) != sample_rate * 12:
        raise ValueError("SilentCipher requires exactly 12 seconds at 44.1 kHz")
    return silentcipher_backend().detect(samples, sample_rate)


def embed_classic(samples: np.ndarray, message: int, sample_rate: int = 48000) -> dict[str, Any]:
    if sample_rate != 48000 or len(samples) != sample_rate * 6:
        raise ValueError("Classic DSP requires exactly 6 seconds at 48 kHz")
    api = _v3_api()
    audio = api.AudioData(np.asarray(samples, dtype=np.float64), sample_rate)
    started = time.perf_counter()
    result = api.embed_message(audio, message)
    marked = np.asarray(result.audio.samples, dtype=np.float32)
    error = np.asarray(samples, dtype=np.float64) - marked.astype(np.float64)
    power = float(np.mean(np.asarray(samples, dtype=np.float64) ** 2))
    distortion = float(np.mean(error ** 2))
    snr = 10 * np.log10((power + 1e-30) / (distortion + 1e-30))
    return {"audio": marked, "sample_rate": sample_rate, "message": message,
            "embedding_snr_db": float(snr), "seconds": time.perf_counter() - started,
            "model_load_seconds": None}


def detect_classic(samples: np.ndarray, sample_rate: int = 48000) -> dict[str, Any]:
    """Frozen V3 blind detector: accepts received audio only."""
    if sample_rate != 48000 or len(samples) != sample_rate * 6:
        raise ValueError("Classic DSP requires exactly 6 seconds at 48 kHz")
    api = _v3_api()
    audio = api.AudioData(np.asarray(samples, dtype=np.float64), sample_rate)
    started = time.perf_counter()
    result = api.detect_message(audio)
    status = result.status if result.status in {IDENTIFIED, UNKNOWN} else DECODE_ERROR
    return {"state": status, "candidate": result.message,
            "confidence": float(result.presence_score), "threshold": float(result.threshold),
            "margin": float(result.margin), "seconds": time.perf_counter() - started,
            "presence_calibration": "FROZEN_V3_POLICY"}


def embed(backend: str, samples: np.ndarray, message: bytes | int, sample_rate: int) -> dict[str, Any]:
    if backend == "Advanced Neural":
        return embed_neural(samples, tuple(message), sample_rate)
    if backend == "Classic DSP":
        return embed_classic(samples, int(message), sample_rate)
    raise ValueError("Unknown watermark backend")


def detect(backend: str, samples: np.ndarray, sample_rate: int) -> dict[str, Any]:
    if backend == "Advanced Neural":
        return detect_neural(samples, sample_rate)
    if backend == "Classic DSP":
        return detect_classic(samples, sample_rate)
    raise ValueError("Unknown detection backend")
