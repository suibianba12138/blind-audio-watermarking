"""Small frozen-source SilentCipher P3 gate. Does not write audio to the repo."""
from __future__ import annotations

import hashlib
import json
import os
import resource
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import librosa
import numpy as np
import soundfile as sf
import torch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
MANIFEST = ROOT / "configs/v4_p3_source_manifest.json"
OUT = ROOT / "experiments/v4_p3/RESULTS.json"
THRESHOLD = 0.6805555373430252
TARGET_SR = 44100
MUSAN_ROOT = Path(os.environ["V4_P3_MUSAN_ROOT"])
SC_ROOT = Path(os.environ["SILENTCIPHER_SOURCE_ROOT"])
MODEL_DIR = Path(os.environ["SILENTCIPHER_MODEL_DIR"])


def read_source(source: dict) -> tuple[np.ndarray, np.ndarray]:
    path = MUSAN_ROOT / source["relative_path"]
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if digest != source["sha256"]:
        raise RuntimeError(f"source hash mismatch: {source['source_id']}")
    info = sf.info(path)
    if info.samplerate != source["source_sample_rate_hz"]:
        raise RuntimeError(f"sample-rate mismatch: {source['source_id']}")
    start = int(round(source["crop_start_seconds"] * info.samplerate))
    frames = int(round(source["crop_duration_seconds"] * info.samplerate))
    raw, sr = sf.read(path, start=start, frames=frames, dtype="float32", always_2d=True)
    if len(raw) != frames:
        raise RuntimeError(f"short frozen crop: {source['source_id']}")
    mono = raw.mean(axis=1)
    if sr != TARGET_SR:
        mono = librosa.resample(mono, orig_sr=sr, target_sr=TARGET_SR)
    mono = np.asarray(mono[: TARGET_SR * 12], dtype=np.float32)
    if len(mono) < TARGET_SR * 12:
        mono = np.pad(mono, (0, TARGET_SR * 12 - len(mono)))
    return mono, mono.copy()


def mp3_roundtrip(x: np.ndarray, stem: str) -> tuple[np.ndarray, float, int]:
    with tempfile.TemporaryDirectory(prefix="v4-p3-mp3-") as temp:
        temp = Path(temp)
        wav, mp3, decoded = temp / f"{stem}.wav", temp / f"{stem}.mp3", temp / "decoded.wav"
        sf.write(wav, x, TARGET_SR, subtype="PCM_16")
        started = time.perf_counter()
        subprocess.run(
            ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(wav), "-ac", "1", "-ar", str(TARGET_SR), "-c:a", "libmp3lame", "-b:a", "128k", str(mp3)],
            check=True, timeout=90, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
        )
        subprocess.run(
            ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(mp3), "-ac", "1", "-ar", str(TARGET_SR), "-c:a", "pcm_f32le", "-f", "wav", str(decoded)],
            check=True, timeout=90, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
        )
        seconds = time.perf_counter() - started
        y, _ = sf.read(decoded, dtype="float32")
        y = np.asarray(y[: len(x)], dtype=np.float32)
        if len(y) < len(x):
            y = np.pad(y, (0, len(x) - len(y)))
        return y, seconds, mp3.stat().st_size


def quality(x: np.ndarray, y: np.ndarray) -> tuple[float, float]:
    a = np.asarray(x, dtype=np.float64)
    b = np.asarray(y[: len(x)], dtype=np.float64)
    err = float(np.mean((a - b) ** 2))
    power = float(np.mean(a ** 2))
    snr = float(10 * np.log10((power + 1e-30) / (err + 1e-30)))

    def spec(z: np.ndarray) -> np.ndarray:
        frames = np.lib.stride_tricks.sliding_window_view(z, 4096)[::2048]
        return np.abs(np.fft.rfft(frames * np.hanning(4096), axis=1))

    s0, s1 = spec(a), spec(b)
    eps = max(float(s0.max()) * 1e-8, 1e-12)
    lsd = float(np.sqrt(np.mean((20 * np.log10((s1 + eps) / (s0 + eps))) ** 2)))
    return snr, lsd


def decode(model, x: np.ndarray, source_id: str, condition: str, message_id: str | None, expected: list[int] | None) -> dict:
    started = time.perf_counter()
    error = None
    trace = None
    raw_status = False
    candidate = None
    candidate_raw = None
    candidate_parse_error = None
    confidence = None
    try:
        result = model.decode_wav(x, TARGET_SR, phase_shift_decoding=False)
        if isinstance(result, list):
            result = result[0] if result else {}
        raw_status = bool(result.get("status", False))
        messages = result.get("messages") or []
        confidences = result.get("confidences") or []
        if messages:
            try:
                candidate_raw = [int(v) for v in messages[0]]
                if len(candidate_raw) == 5 and all(0 <= v <= 255 for v in candidate_raw):
                    candidate = candidate_raw
                else:
                    candidate_parse_error = "NOT_FIVE_BYTE_MESSAGE"
            except Exception as exc:
                candidate_parse_error = type(exc).__name__
        if confidences:
            confidence = float(confidences[0])
    except Exception as exc:  # Save only stable exception type, never host details.
        error = type(exc).__name__
    decode_s = time.perf_counter() - started
    if candidate is None or not raw_status:
        try:
            from app.silentcipher_diagnostics import trace_official_decoder
            trace = trace_official_decoder(model, x, TARGET_SR)
        except Exception as exc:
            trace = {"trace_error_type": type(exc).__name__}
    exact = bool(expected is not None and candidate == expected)
    accepted = bool(raw_status and candidate is not None and confidence is not None and confidence >= THRESHOLD)
    record = {
        "source_id": source_id, "condition": condition, "message_id": message_id,
        "official_status": raw_status, "candidate_hex": bytes(candidate).hex().upper() if candidate is not None else None,
        "candidate_raw_symbols": candidate_raw, "candidate_parse_error": candidate_parse_error,
        "confidence": confidence, "exact_message_recovery": exact if expected is not None else None,
        "correct_accepted_recovery": bool(accepted and exact) if expected is not None else None,
        "wrong_message_acceptance": bool(accepted and not exact) if expected is not None else None,
        "negative_acceptance": accepted if expected is None else None,
        "presence_decision": "IDENTIFIED" if accepted else ("DECODE_ERROR" if error else "UNKNOWN"),
        "decode_error_type": error,
        "trace_error_type": trace.get("trace_error_type") if isinstance(trace, dict) else None,
        "trace_status": trace.get("status") if isinstance(trace, dict) else None,
        "terminator_missing": bool(trace and any(d.get("parse_error") == "MISSING_TERMINATOR" for d in trace.get("per_decoder", []))),
        "trace_stage_by_decoder": [d.get("stage") for d in trace.get("per_decoder", [])] if trace else [],
        "frame_confidence_by_decoder": [d.get("confidence") for d in trace.get("per_decoder", [])] if trace else [],
        "decode_seconds": decode_s,
    }
    return record


def main() -> None:
    if hashlib.sha256(MANIFEST.read_bytes()).hexdigest() != os.environ["V4_P3_MANIFEST_SHA256"]:
        raise RuntimeError("frozen manifest hash mismatch")
    manifest = json.loads(MANIFEST.read_text())
    messages = [list(bytes.fromhex(value)) for value in manifest["payloads_40bit"]]
    torch.set_num_threads(4)
    sys.path.insert(0, str(SC_ROOT / "src"))
    from silentcipher import get_model

    load_started = time.perf_counter()
    model = get_model(model_type="44.1k", ckpt_path=str(MODEL_DIR), config_path=str(MODEL_DIR / "hparams.yaml"), device="cpu")
    model_load_seconds = time.perf_counter() - load_started
    records, source_quality = [], {}

    def save_partial(completed_sources: list[str]) -> None:
        OUT.parent.mkdir(parents=True, exist_ok=True)
        partial = {"status": "RUNNING", "completed_source_ids": completed_sources,
                   "protocol_id": manifest["protocol_id"],
                   "manifest_sha256": hashlib.sha256(MANIFEST.read_bytes()).hexdigest(),
                   "model_load_seconds": model_load_seconds, "records": records,
                   "source_results": source_quality}
        OUT.write_text(json.dumps(partial, indent=2, sort_keys=True) + "\n")

    completed_sources: list[str] = []
    for source in manifest["sources"]:
        sid = source["source_id"]
        original, _ = read_source(source)
        negative_mp3, negative_codec_s, negative_bytes = mp3_roundtrip(original, f"{sid}-neg")
        for cond, audio in (("negative_clean", original), ("negative_mp3_128k", negative_mp3)):
            records.append(decode(model, audio, sid, cond, None, None))
        for mi, message in enumerate(messages):
            started = time.perf_counter()
            marked, reported_sdr = model.encode_wav(original, TARGET_SR, message, calc_sdr=True)
            embed_s = time.perf_counter() - started
            marked = np.asarray(marked, dtype=np.float32)
            snr, lsd = quality(original, marked)
            positive_mp3, codec_s, mp3_bytes = mp3_roundtrip(marked, f"{sid}-m{mi}")
            for cond, audio in (("positive_clean", marked), ("positive_mp3_128k", positive_mp3)):
                rec = decode(model, audio, sid, cond, f"M{mi+1}", message)
                rec.update({"embedding_seconds": embed_s, "reported_sdr_db": float(reported_sdr), "embedding_snr_db": snr,
                            "embedding_lsd_db": lsd, "mp3_codec_seconds": codec_s if cond == "positive_mp3_128k" else None,
                            "mp3_bytes": mp3_bytes if cond == "positive_mp3_128k" else None})
                records.append(rec)
        source_quality[sid] = {"negative_mp3_codec_seconds": negative_codec_s, "negative_mp3_bytes": negative_bytes}
        completed_sources.append(sid)
        save_partial(completed_sources)
        print(f"SOURCE_DONE {sid}", flush=True)
    rss_kib = int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    result = {
        "status": "RUNTIME_COMPLETE", "protocol_id": manifest["protocol_id"],
        "manifest_sha256": hashlib.sha256(MANIFEST.read_bytes()).hexdigest(),
        "model": manifest["model"], "model_load_seconds": model_load_seconds,
        "torch_version": torch.__version__, "python_version": sys.version.split()[0],
        "torch_threads": torch.get_num_threads(), "device": "cpu", "presence_threshold": THRESHOLD,
        "threshold_source": "P1 frozen exploratory threshold; not reselected",
        "peak_rss_kib": rss_kib, "source_results": source_quality, "records": records,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": result["status"], "records": len(records), "model_load_seconds": model_load_seconds,
                      "peak_rss_kib": rss_kib, "manifest_sha256": result["manifest_sha256"]}, indent=2), flush=True)


if __name__ == "__main__":
    main()
