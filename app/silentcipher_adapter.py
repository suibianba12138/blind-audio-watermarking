"""Isolated CPU adapter for the official SilentCipher 44.1 kHz release."""
from __future__ import annotations

import os
import threading
import time
from dataclasses import dataclass
from typing import Any, Callable

import numpy as np

IDENTIFIED = "IDENTIFIED"
UNKNOWN = "UNKNOWN"
DECODE_ERROR = "DECODE_ERROR"
DEFAULT_THRESHOLD = 0.680556


def validate_message(message: Any) -> tuple[int, ...]:
    try:
        values = tuple(int(v) for v in message)
    except Exception as exc:
        raise ValueError("message must contain exactly five byte values") from exc
    if len(values) != 5 or any(v < 0 or v > 255 for v in values):
        raise ValueError("message must contain exactly five byte values")
    return values


def validate_audio(audio: Any, sample_rate: int) -> np.ndarray:
    values = np.asarray(audio, dtype=np.float32)
    if sample_rate <= 0 or values.ndim not in (1, 2) or values.size == 0:
        raise ValueError("audio must be non-empty mono or multichannel audio with a valid sample rate")
    if values.ndim == 2 and values.shape[1] not in (1, 2):
        raise ValueError("audio must have one or two channels")
    if not np.all(np.isfinite(values)):
        raise ValueError("audio contains invalid numeric samples")
    if float(np.mean(values.astype(np.float64) ** 2)) < 1e-12:
        raise ValueError("audio signal is silent or too weak")
    if values.shape[0] < int(sample_rate * 1.0) or values.shape[0] > int(sample_rate * 60):
        raise ValueError("audio duration must be between 1 and 60 seconds")
    return values


def _normalize_result(result: Any) -> dict[str, Any]:
    if isinstance(result, list):
        result = result[0] if result else {}
    if not isinstance(result, dict):
        raise TypeError("decoder returned an unsupported result")
    messages = result.get("messages") or []
    confs = result.get("confidences") or []
    candidate = None
    if messages:
        candidate = validate_message(messages[0])
    confidence = float(confs[0]) if confs else None
    if confidence is not None and not np.isfinite(confidence):
        confidence = None
    return {
        "official_status": bool(result.get("status", False)),
        "candidate": candidate,
        "confidence": confidence,
        "error_category": "NO_MESSAGE" if not candidate else None,
    }


def classify_decode_result(result: Any) -> dict[str, Any]:
    """Return a raw candidate only; official status never means presence."""
    try:
        raw = _normalize_result(result)
        return {"state": UNKNOWN, **raw}
    except Exception:
        return {"state": DECODE_ERROR, "official_status": False, "candidate": None,
                "confidence": None, "error_category": "INVALID_DECODER_RESULT"}


def sanitize_exception(error: BaseException) -> dict[str, Any]:
    """Expose a stable category, never exception text or traceback."""
    name = type(error).__name__
    if isinstance(error, (ValueError, TypeError)):
        category = "INVALID_INPUT"
    elif isinstance(error, TimeoutError):
        category = "TIMEOUT"
    elif isinstance(error, MemoryError):
        category = "RESOURCE_LIMIT"
    else:
        category = "MODEL_FAILURE"
    return {"state": DECODE_ERROR, "official_status": False, "candidate": None,
            "confidence": None, "error_category": category, "exception_type": name}


@dataclass
class PresencePolicy:
    threshold: float = DEFAULT_THRESHOLD
    calibration: str = "PROVISIONAL"

    def decide(self, decoded: dict[str, Any]) -> str:
        score = decoded.get("confidence")
        if decoded.get("state") == DECODE_ERROR:
            return DECODE_ERROR
        if decoded.get("candidate") is not None and decoded.get("official_status") and score is not None and score >= self.threshold:
            return IDENTIFIED
        return UNKNOWN


class SilentCipherAdapter:
    def __init__(self, model: Any = None, *, model_factory: Callable[[], Any] | None = None,
                 presence_policy: PresencePolicy | None = None, cpu_threads: int = 4):
        self._model = model
        self._model_factory = model_factory
        self.model_load_seconds = None
        self._policy = presence_policy or PresencePolicy()
        self._lock = threading.RLock()
        self._cpu_threads = max(1, min(int(cpu_threads), 8))
        if model is None and model_factory is None:
            self._model_factory = load_official_model

    def _get_model(self):
        if self._model is None:
            import torch
            torch.set_num_threads(self._cpu_threads)
            try:
                torch.set_num_interop_threads(self._cpu_threads)
            except RuntimeError:
                # Another imported library may already have started the pool.
                pass
            started = time.perf_counter()
            self._model = self._model_factory()
            self.model_load_seconds = time.perf_counter() - started
        return self._model

    @property
    def presence_policy(self) -> PresencePolicy:
        return self._policy

    def embed(self, audio: Any, message: Any, sample_rate: int = 44100) -> dict[str, Any]:
        values = validate_audio(audio, sample_rate)
        payload = validate_message(message)
        with self._lock:
            start = time.perf_counter()
            try:
                marked, reported_sdr = self._get_model().encode_wav(values, sample_rate, payload, calc_sdr=True)
                marked = np.asarray(marked, dtype=np.float32)
                if marked.shape != values.shape or not np.all(np.isfinite(marked)):
                    raise RuntimeError("model returned invalid audio")
                noise = values.astype(np.float64) - marked.astype(np.float64)
                power = float(np.mean(values.astype(np.float64) ** 2))
                error = float(np.mean(noise ** 2))
                snr = float(10 * np.log10((power + 1e-30) / (error + 1e-30)))
                return {"audio": marked, "sample_rate": sample_rate, "message_bytes": list(payload),
                        "embedding_snr_db": snr, "reported_sdr_db": float(reported_sdr),
                        "seconds": time.perf_counter() - start,
                        "model_load_seconds": self.model_load_seconds}
            except Exception as exc:
                raise RuntimeError("EMBED_FAILED") from exc

    def decode(self, received_audio: Any, sample_rate: int = 44100) -> dict[str, Any]:
        values = validate_audio(received_audio, sample_rate)
        with self._lock:
            start = time.perf_counter()
            try:
                result = self._get_model().decode_wav(values, sample_rate, phase_shift_decoding=False)
                decoded = classify_decode_result(result)
            except Exception as exc:
                decoded = sanitize_exception(exc)
            decoded["seconds"] = time.perf_counter() - start
            decoded["model_load_seconds"] = self.model_load_seconds
            decoded["presence_calibration"] = self._policy.calibration
            decoded["presence_threshold"] = self._policy.threshold
            return decoded

    def detect(self, received_audio: Any, sample_rate: int = 44100) -> dict[str, Any]:
        decoded = self.decode(received_audio, sample_rate)
        decoded["state"] = self._policy.decide(decoded)
        return decoded


def load_official_model():
    """Load exactly the already downloaded official model; no network fallback."""
    source = os.environ.get("SILENTCIPHER_SOURCE_ROOT")
    model_dir = os.environ.get("SILENTCIPHER_MODEL_DIR")
    if not source or not model_dir:
        raise RuntimeError("MODEL_CONFIGURATION_MISSING")
    from pathlib import Path
    import sys
    model_path = Path(model_dir).resolve()
    config_path = model_path / "hparams.yaml"
    if not config_path.is_file() or not (model_path / "enc_c.ckpt").is_file():
        raise RuntimeError("MODEL_FILES_MISSING")
    sys.path.insert(0, str(Path(source).resolve() / "src"))
    from silentcipher import get_model
    return get_model(model_type="44.1k", ckpt_path=str(model_path), config_path=str(config_path), device="cpu")
