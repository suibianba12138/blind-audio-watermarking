"""Isolated send-side adaptive embedding prototype for frozen SilentCipher."""
from __future__ import annotations

import tempfile
import time
from pathlib import Path
from typing import Any, Callable, Sequence

import numpy as np
from scipy import signal
import soundfile as sf

from .silentcipher_adapter import (
    DECODE_ERROR, IDENTIFIED, UNKNOWN, PresencePolicy, classify_decode_result,
)

CANDIDATE_STRENGTHS_DB = (47, 45, 43)
TARGET_CHANNELS = ("clean_wav", "mp3_128k", "aac_lc_m4a_128k")
QUALITY_MIN_SNR_DB = 40.0
QUALITY_MAX_LSD_DB = 5.0
_CHANNEL_OPERATIONS = {
    "mp3_128k": "MP3 128 kbps",
    "aac_lc_m4a_128k": "AAC 128 kbps",
}


def _message_bytes(message: Any) -> bytes:
    try:
        value = bytes(message)
    except Exception as exc:
        raise ValueError("message must be exactly five byte values") from exc
    if len(value) != 5:
        raise ValueError("message must be exactly five byte values")
    return value


def measure_embedding_quality(reference: Any, marked: Any, sample_rate: int) -> dict[str, Any]:
    """Aligned same-length time/SFTF metrics for the embedded waveform pair."""
    ref = np.asarray(reference, dtype=np.float64)
    out = np.asarray(marked, dtype=np.float64)
    if (ref.ndim != 1 or out.ndim != 1 or ref.size == 0 or ref.size != out.size
            or sample_rate <= 0 or not np.isfinite(ref).all() or not np.isfinite(out).all()):
        raise ValueError("quality measurement requires aligned finite mono waveforms")
    diff = out - ref
    sig_power = float(np.mean(ref * ref))
    err_power = float(np.mean(diff * diff))
    snr = float(10.0 * np.log10((sig_power + 1e-30) / (err_power + 1e-30)))
    _, _, ref_stft = signal.stft(ref, fs=sample_rate, window="hann", nperseg=4096,
                                 noverlap=2048, boundary="zeros", padded=True)
    _, _, out_stft = signal.stft(out, fs=sample_rate, window="hann", nperseg=4096,
                                 noverlap=2048, boundary="zeros", padded=True)
    ref_mag, out_mag = np.abs(ref_stft), np.abs(out_stft)
    eps = max(float(ref_mag.max()) * 1e-8, 1e-12)
    log_delta = 20.0 * np.log10(np.maximum(out_mag, eps)) - 20.0 * np.log10(np.maximum(ref_mag, eps))
    ref_clipped = np.abs(ref) >= 1.0
    out_clipped = np.abs(out) >= 1.0
    newly_clipped = int(np.count_nonzero(out_clipped & ~ref_clipped))
    return {
        "snr_db": snr,
        "lsd_db": float(np.sqrt(np.mean(log_delta * log_delta))),
        "reference_peak_abs": float(np.max(np.abs(ref))),
        "watermarked_peak_abs": float(np.max(np.abs(out))),
        "reference_clipped_samples": int(np.count_nonzero(ref_clipped)),
        "watermarked_clipped_samples": int(np.count_nonzero(out_clipped)),
        "newly_clipped_samples": newly_clipped,
        "waveform_difference_rms": float(np.sqrt(err_power)),
        "compared_samples": int(ref.size),
        "sample_rate_hz": int(sample_rate),
        "alignment": "same source sample index; no resampling or time shift",
    }


def blind_detect(model: Any, received_audio: Any, sample_rate: int,
                 presence_policy: PresencePolicy | None = None) -> dict[str, Any]:
    """Decode and apply frozen presence policy; this API has no reference/message input."""
    policy = presence_policy or PresencePolicy()
    try:
        audio = np.asarray(received_audio, dtype=np.float32)
        if audio.ndim != 1 or audio.size == 0 or not np.isfinite(audio).all():
            raise ValueError("invalid received waveform")
        raw = model.decode_wav(audio, int(sample_rate), phase_shift_decoding=False)
        decoded = classify_decode_result(raw)
        state = policy.decide(decoded)
        candidate = decoded.get("candidate")
        return {
            "state": state,
            "candidate": tuple(candidate) if candidate is not None else None,
            "confidence": decoded.get("confidence"),
            "official_status": decoded.get("official_status", False),
            "error_category": decoded.get("error_category"),
            "presence_threshold": policy.threshold,
            "presence_calibration": policy.calibration,
        }
    except Exception as exc:
        return {
            "state": DECODE_ERROR, "candidate": None, "confidence": None,
            "official_status": False,
            "error_category": "INVALID_INPUT" if isinstance(exc, (ValueError, TypeError)) else "MODEL_FAILURE",
            "exception_type": type(exc).__name__,
            "presence_threshold": policy.threshold,
            "presence_calibration": policy.calibration,
        }


def run_v4_channel(audio: Any, sample_rate: int, channel: str) -> dict[str, Any]:
    """Execute clean PCM16 or the existing P8 MP3/AAC M4A channel implementation."""
    from .audio_io import AudioData
    from .v4_audio_processing import process_channel

    values = np.asarray(audio, dtype=np.float32)
    if values.ndim != 1 or values.size == 0 or not np.isfinite(values).all():
        raise ValueError("channel input must be finite mono audio")
    if channel == "clean_wav":
        clean_started = time.perf_counter()
        with tempfile.TemporaryDirectory(prefix="v4-adaptive-clean-") as tmp:
            path = Path(tmp) / "marked.wav"
            sf.write(path, values, int(sample_rate), subtype="PCM_16")
            received, rate = sf.read(path, dtype="float32")
        return {"audio": np.asarray(received, dtype=np.float32), "sample_rate": int(rate),
                "metadata": {"container": "WAV", "subtype": "PCM_16",
                             "sample_count": int(received.size), "duration_seconds": received.size / rate},
                "channel_seconds": time.perf_counter() - clean_started}
    if channel not in _CHANNEL_OPERATIONS:
        raise ValueError("unsupported target channel")
    with tempfile.TemporaryDirectory(prefix="v4-adaptive-codec-") as tmp:
        start = time.perf_counter()
        result = process_channel(AudioData(values.astype(np.float64), int(sample_rate)),
                                 _CHANNEL_OPERATIONS[channel], Path(tmp))
        received = np.asarray(result["audio"].samples, dtype=np.float32)
        rate = int(result["audio"].sample_rate)
        metadata = {k: result[k] for k in (
            "details", "codec_seconds", "encoded_bytes", "output_duration_seconds",
            "encoded_metadata", "decoded_sample_count_before_trim",
            "effective_sample_range_samples", "leading_samples_discarded",
            "tail_padding_samples_removed") if k in result}
        metadata["container"] = "M4A" if channel == "aac_lc_m4a_128k" else "MP3"
        channel_seconds = time.perf_counter() - start
    return {"audio": received, "sample_rate": rate, "metadata": metadata,
            "channel_seconds": channel_seconds}


class AdaptiveWatermarkEmbedder:
    """Bounded sender-side strength search with independent channel blind checks.

    ``embed_fn(audio, message, sample_rate, message_sdr_db)`` can see the message.
    ``detect_fn(received_audio, sample_rate)`` receives no message/reference/context.
    ``channel_fn`` returns {audio, sample_rate, metadata?, channel_seconds?}.
    """
    def __init__(self, embed_fn: Callable[..., Any], detect_fn: Callable[..., dict[str, Any]],
                 channel_fn: Callable[..., dict[str, Any]], *, quality_fn: Callable[..., dict[str, Any]] = measure_embedding_quality,
                 strengths_db: Sequence[int] = CANDIDATE_STRENGTHS_DB,
                 min_snr_db: float = QUALITY_MIN_SNR_DB, max_lsd_db: float = QUALITY_MAX_LSD_DB):
        strengths = tuple(int(x) for x in strengths_db)
        if not strengths or len(strengths) > len(CANDIDATE_STRENGTHS_DB) or len(set(strengths)) != len(strengths):
            raise ValueError("at most three unique candidate strengths are allowed")
        if any(x not in CANDIDATE_STRENGTHS_DB for x in strengths):
            raise ValueError("candidate strengths are frozen to 47, 45, and 43 dB")
        if tuple(sorted(strengths, reverse=True)) != strengths:
            raise ValueError("candidate strengths must use fixed descending order")
        self.embed_fn, self.detect_fn, self.channel_fn, self.quality_fn = embed_fn, detect_fn, channel_fn, quality_fn
        self.strengths_db = strengths
        self.min_snr_db = float(min_snr_db)
        self.max_lsd_db = float(max_lsd_db)

    def _quality_pass(self, quality: dict[str, Any]) -> bool:
        try:
            return (float(quality["snr_db"]) >= self.min_snr_db
                    and float(quality["lsd_db"]) <= self.max_lsd_db
                    and int(quality["newly_clipped_samples"]) == 0)
        except (KeyError, TypeError, ValueError):
            return False

    def embed(self, audio: Any, message: Any, sample_rate: int = 44100,
              target_channels: Sequence[str] = TARGET_CHANNELS) -> dict[str, Any]:
        original = np.asarray(audio, dtype=np.float32)
        payload = _message_bytes(message)
        channels = tuple(target_channels)
        if sample_rate != 44100 or original.ndim != 1 or original.size != 12 * 44100:
            raise ValueError("SilentCipher adaptive input must be mono 44.1 kHz and exactly 12 seconds")
        if not np.isfinite(original).all() or float(np.mean(original.astype(np.float64) ** 2)) < 1e-12:
            raise ValueError("audio must be finite and non-silent")
        if not channels or len(set(channels)) != len(channels) or any(c not in TARGET_CHANNELS for c in channels):
            raise ValueError("target channels must be unique supported channel identifiers")

        started = time.perf_counter()
        candidates: list[dict[str, Any]] = []
        successful: list[tuple[dict[str, Any], np.ndarray]] = []
        for strength in self.strengths_db:
            candidate_started = time.perf_counter()
            record: dict[str, Any] = {"message_sdr_db": strength, "channels": {}}
            try:
                embed_started = time.perf_counter()
                marked = np.asarray(self.embed_fn(original.copy(), payload, sample_rate, strength), dtype=np.float32)
                record["embedding_seconds"] = time.perf_counter() - embed_started
                if marked.shape != original.shape or not np.isfinite(marked).all():
                    raise ValueError("embedder returned an invalid waveform")
                quality = self.quality_fn(original, marked, sample_rate)
                record["quality"] = quality
                record["quality_pass"] = self._quality_pass(quality)
                all_channels_pass = True
                codec_elapsed = 0.0
                for channel in channels:
                    channel_record: dict[str, Any] = {}
                    try:
                        transformed = self.channel_fn(marked.copy(), sample_rate, channel)
                        received = np.asarray(transformed["audio"], dtype=np.float32)
                        received_sr = int(transformed.get("sample_rate", sample_rate))
                        if received.ndim != 1 or received.size == 0 or not np.isfinite(received).all():
                            raise ValueError("channel returned invalid audio")
                        detection_started = time.perf_counter()
                        decoded = self.detect_fn(received, received_sr)
                        detection_seconds = time.perf_counter() - detection_started
                        detected_candidate = decoded.get("candidate")
                        detected_candidate = tuple(detected_candidate) if detected_candidate is not None else None
                        exact = detected_candidate == tuple(payload) if detected_candidate is not None else False
                        identified = decoded.get("state") == IDENTIFIED
                        correct_accepted = bool(identified and exact)
                        wrong_accepted = bool(identified and not exact)
                        channel_record = {
                            "state": decoded.get("state", DECODE_ERROR),
                            "candidate_hex": bytes(detected_candidate).hex().upper() if detected_candidate is not None else None,
                            "confidence": decoded.get("confidence"),
                            "exact_message_recovery": bool(exact),
                            "correct_accepted_recovery": correct_accepted,
                            "wrong_message_accepted": wrong_accepted,
                            "presence_threshold": decoded.get("presence_threshold"),
                            "presence_calibration": decoded.get("presence_calibration"),
                            "official_status": decoded.get("official_status"),
                            "detection_seconds": detection_seconds,
                            "channel_metadata": transformed.get("metadata", {}),
                            "channel_seconds": float(transformed.get("channel_seconds", 0.0)),
                        }
                        codec_elapsed += channel_record["channel_seconds"]
                    except Exception as exc:
                        channel_record = {"state": DECODE_ERROR, "candidate_hex": None,
                            "confidence": None, "exact_message_recovery": False,
                            "correct_accepted_recovery": False, "wrong_message_accepted": False,
                            "error_category": "INVALID_INPUT" if isinstance(exc, (ValueError, TypeError)) else "CHANNEL_OR_DETECT_FAILURE",
                            "exception_type": type(exc).__name__}
                    record["channels"][channel] = channel_record
                    all_channels_pass = all_channels_pass and channel_record.get("correct_accepted_recovery", False)
                record["channel_processing_seconds"] = codec_elapsed
                record["robustness_pass"] = bool(record["quality_pass"] and all_channels_pass)
            except Exception as exc:
                record.update({"robustness_pass": False, "quality_pass": False,
                    "error_category": "INVALID_INPUT" if isinstance(exc, (ValueError, TypeError)) else "EMBED_FAILURE",
                    "exception_type": type(exc).__name__})
            record["candidate_total_seconds"] = time.perf_counter() - candidate_started
            candidates.append(record)
            if record.get("robustness_pass"):
                successful.append((record, marked))
                if strength == 47:
                    break

        selected_record = None
        selected_audio = None
        if successful:
            selected_record, selected_audio = max(
                successful,
                key=lambda pair: (float(pair[0]["quality"]["snr_db"]),
                                  -float(pair[0]["quality"]["lsd_db"]),
                                  int(pair[0]["message_sdr_db"])),
            )
        return {
            "status": "ROBUSTNESS_TARGET_MET" if selected_record else "ROBUSTNESS_TARGET_NOT_MET",
            "selected_message_sdr_db": selected_record["message_sdr_db"] if selected_record else None,
            "selected_quality": selected_record["quality"] if selected_record else None,
            "selected_audio": selected_audio,
            "target_channels": list(channels),
            "candidate_results": candidates,
            "total_seconds": time.perf_counter() - started,
            "candidate_count": len(candidates),
            "quality_gate": {"minimum_snr_db": self.min_snr_db, "maximum_lsd_db": self.max_lsd_db,
                             "new_clipping_allowed": False},
            "presence_policy": "frozen; unchanged",
        }
