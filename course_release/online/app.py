"""Bounded, reference-assisted C2/C3 online laboratory.

No uploaded media or keys are retained. All computational results are generated
from the current request with a caller-selected public/demo key.
"""
from __future__ import annotations

import asyncio
from collections import Counter, defaultdict, deque
from contextlib import contextmanager
from io import BytesIO
import math
import os
from pathlib import Path
import re
import subprocess
import tempfile
import time
from typing import Annotated

import numpy as np
from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from scipy.io import wavfile

from course_watermark.c2 import Config as C2Config, embed as c2_embed, detect as c2_detect
from course_watermark.c3 import Config as C3Config, embed as c3_embed, detect as c3_detect

SR = 48_000
BLOCK = 6 * SR
ROOT = Path(__file__).resolve().parents[1]
SAMPLE = ROOT / "media" / "selected_c3_16_showcase" / "Original.wav"
MAX_UPLOAD = 32 * 1024 * 1024
MAX_BODY = 68 * 1024 * 1024
KEY_MAX = 100
MAX_REQUESTS_PER_60S = 12
MODES = {
    "c2-8": (6, 2, 0.6226488835443009, C2Config, c2_embed, c2_detect),
    "c3-16": (6, 4, 0.7199080718655814, C3Config, c3_embed, c3_detect),
    "c2-long-id": (72, 8, 0.6226488835443009, C2Config, c2_embed, c2_detect),
    "c3-192": (72, 48, 0.7199080718655814, C3Config, c3_embed, c3_detect),
}
CHANNELS = {"clean", "mp3", "aac", "mp3_aac", "gain_minus6", "gain_plus3", "resample"}
ALLOWED = [origin.strip() for origin in os.getenv(
    "AUDIO_ALLOWED_ORIGINS",
    "https://shengkaini.com,https://www.shengkaini.com,https://suibianba12138.github.io",
).split(",") if origin.strip()]

app = FastAPI(title="Reference-Assisted DSP Audio Watermark Lab", version="1.0.0", docs_url=None, redoc_url=None)
app.add_middleware(CORSMiddleware, allow_origins=ALLOWED, allow_methods=["GET", "POST"],
                   allow_headers=["Content-Type"], expose_headers=["X-Watermark-Mode", "X-Output-Peak", "X-Overfull-Samples"])
_slots = asyncio.Semaphore(1)  # free-tier CPU budget; do not run simultaneous FFT/FFmpeg pipelines
_visits: dict[str, deque[float]] = defaultdict(deque)


@app.middleware("http")
async def protect_size_and_rate(request: Request, call_next):
    if request.method == "POST":
        length = request.headers.get("content-length")
        if length:
            try:
                if int(length) > MAX_BODY:
                    return JSONResponse({"detail": "Uploaded request exceeds 68 MiB"}, status_code=413)
            except ValueError:
                return JSONResponse({"detail": "Invalid Content-Length"}, status_code=400)
        # Origin policy is enforced by browsers; this additional check also disallows
        # unexpected browser origins from spending CPU even if CORS preflight is bypassed.
        origin = request.headers.get("origin")
        if origin and origin not in ALLOWED:
            return JSONResponse({"detail": "Origin not permitted"}, status_code=403)
        ip = request.client.host if request.client else "unknown"
        now = time.monotonic()
        bucket = _visits[ip]
        while bucket and bucket[0] < now - 60:
            bucket.popleft()
        if len(bucket) >= MAX_REQUESTS_PER_60S:
            return JSONResponse({"detail": "Too many requests; retry shortly"}, status_code=429)
        bucket.append(now)
    return await call_next(request)


@app.get("/healthz")
def health():
    return {"status": "ok", "engine": "reference-assisted-c2-c3", "version": "1.0.0"}


@app.get("/api/v1/info")
def info():
    return {
        "backend": "real-computation", "reference_assisted": True,
        "requires_original_and_key_to_detect": True,
        "modes": {k: {"duration_seconds": v[0], "payload_hex_digits": v[1]} for k, v in MODES.items()},
        "channels": sorted(CHANNELS), "max_upload_bytes": MAX_UPLOAD,
        "sample_available": SAMPLE.is_file(), "retention": "request-only temporary files",
        "public_key_notice": "Published frozen experiments used a different key; results from this API are new runs.",
    }


def _mode(name: str):
    if name not in MODES:
        raise HTTPException(422, "Unknown C2/C3 mode")
    return MODES[name]


def _key(value: str) -> str:
    if not 4 <= len(value) <= KEY_MAX or not value.isprintable() or any(c in value for c in "\n\r\x00"):
        raise HTTPException(422, "Key must be 4–100 printable characters")
    return value


def _message(value: str, width: int):
    msg = value.strip().removeprefix("0x").removeprefix("0X")
    if not re.fullmatch(r"[0-9a-fA-F]{" + str(width) + r"}", msg):
        raise HTTPException(422, f"Message must have exactly {width} hexadecimal digits")
    return msg.upper()


def _blocks(message: str, mode: str) -> list[int]:
    if mode == "c2-long-id":
        one = [int(message[i:i+2], 16) for i in range(0, 8, 2)]
        return one * 3
    if mode == "c3-192":
        return [int(message[i:i+4], 16) for i in range(0, 48, 4)]
    return [int(message, 16)]


async def _read_limited(upload: UploadFile | None, *, required: bool = True) -> bytes | None:
    if upload is None:
        if required:
            raise HTTPException(422, "Audio file is required")
        return None
    out = bytearray()
    while True:
        chunk = await upload.read(1024 * 1024)
        if not chunk:
            break
        out.extend(chunk)
        if len(out) > MAX_UPLOAD:
            raise HTTPException(413, "Individual audio file exceeds 32 MiB")
    if not out:
        raise HTTPException(422, "Audio file is empty")
    return bytes(out)


@contextmanager
def _temp():
    with tempfile.TemporaryDirectory(prefix="dsp-online-") as directory:
        yield Path(directory)


def _ffmpeg(args: list[str], timeout: int = 55):
    try:
        proc = subprocess.run(
            ["ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error", "-threads", "1", "-y", *args],
            capture_output=True, timeout=timeout, check=False,
        )
    except (subprocess.TimeoutExpired, OSError) as exc:
        raise HTTPException(422, "Audio conversion exceeded limits or FFmpeg is unavailable") from exc
    if proc.returncode:
        raise HTTPException(422, "Unsupported or invalid audio file / audio conversion failed")


def _to_mono_float(raw: bytes, seconds: int, work: Path, *, exact_length: bool) -> np.ndarray:
    source = work / "input-media"
    decoded = work / "decoded.f32"
    source.write_bytes(raw)
    _ffmpeg(["-i", str(source), "-t", str(seconds + 0.20), "-map", "0:a:0", "-vn", "-ac", "1", "-ar", "48000", "-f", "f32le", "-acodec", "pcm_f32le", str(decoded)])
    audio = np.fromfile(decoded, dtype="<f4")
    if audio.size == 0 or not np.isfinite(audio).all():
        raise HTTPException(422, "Audio contains no finite samples")
    needed = seconds * SR
    if exact_length and audio.size < needed:
        raise HTTPException(422, f"This mode requires at least {seconds} seconds of audio")
    return audio[:needed].astype(np.float64)


def _reference(raw: bytes | None, source: str, seconds: int, work: Path) -> np.ndarray:
    if source == "sample":
        if not SAMPLE.is_file():
            raise HTTPException(503, "Bundled licensed demonstration audio is unavailable")
        rate, audio = wavfile.read(SAMPLE)
        if rate != SR or audio.ndim != 1:
            raise HTTPException(503, "Demonstration audio has an unexpected format")
        return np.asarray(audio[:seconds * SR], dtype=np.float64)
    if source != "upload":
        raise HTTPException(422, "Source must be sample or upload")
    if raw is None:
        raise HTTPException(422, "Upload original audio or choose the built-in sample")
    return _to_mono_float(raw, seconds, work, exact_length=True)


def _make_wav(x: np.ndarray) -> bytes:
    stream = BytesIO()
    wavfile.write(stream, SR, np.asarray(x, dtype=np.float32))
    return stream.getvalue()


def _execute_embed(raw: bytes | None, source: str, mode: str, msg: str, key: str):
    seconds, _, _, Cfg, embedding, _ = _mode(mode)
    with _temp() as work:
        reference = _reference(raw, source, seconds, work)
        if reference.size != seconds * SR:
            raise HTTPException(422, "Audio is shorter than the mode duration")
        cfg = Cfg(key=key, target_snr_db=45.0)
        result = [embedding(reference[i*BLOCK:(i+1)*BLOCK], payload, cfg)
                  for i, payload in enumerate(_blocks(msg, mode))]
        marked = np.concatenate(result)
        if not np.isfinite(marked).all():
            raise HTTPException(422, "Embedding produced invalid sample values")
        return _make_wav(marked), float(np.max(np.abs(marked))), int(np.count_nonzero(np.abs(marked) > 1))


def _execute_detect(original_bytes: bytes | None, received_bytes: bytes, source: str, mode: str, key: str):
    seconds, _, threshold, Cfg, _, detect = _mode(mode)
    per_width = 2 if mode.startswith("c2") else 4
    with _temp() as work:
        original = _reference(original_bytes, source, seconds, work)
        with _temp() as received_work:
            received = _to_mono_float(received_bytes, seconds, received_work, exact_length=False)
        if len(received) < seconds * SR * 0.8:
            raise HTTPException(422, "Received audio is too short")
        cfg = Cfg(key=key, target_snr_db=45.0)
        output = []
        for i in range(seconds // 6):
            a = original[i*BLOCK:(i+1)*BLOCK]
            b = received[i*BLOCK:(i+1)*BLOCK]
            if len(b) < BLOCK * 0.8:
                output.append({"block": i+1, "start_seconds": i*6, "status": "UNKNOWN", "recovered": None})
                continue
            try:
                d = detect(b, a, cfg)
                accepted = d.presence_stat >= threshold and d.reference_similarity >= 0.5
                output.append({
                    "block": i+1, "start_seconds": i*6, "status": "IDENTIFIED" if accepted else "UNKNOWN",
                    "recovered": f"{d.message:0{per_width}X}" if accepted else None,
                    "candidate": f"{d.message:0{per_width}X}",
                    "presence_stat": round(float(d.presence_stat), 6),
                    "threshold": threshold,
                    "reference_similarity": round(float(d.reference_similarity), 6),
                    "alignment_lag_samples": int(d.alignment_lag_samples),
                })
            except (ValueError, FloatingPointError):
                output.append({"block": i+1, "start_seconds": i*6, "status": "UNKNOWN", "recovered": None})
        if mode == "c2-long-id":
            consensus = []
            for pos in range(4):
                all_votes = [output[repeat*4+pos].get("recovered") for repeat in range(3)]
                counts = Counter(x for x in all_votes if x is not None)
                vote = counts.most_common(1)[0] if counts else (None, 0)
                consensus.append(vote[0] if vote[1] >= 2 else None)
            payload = "".join(consensus) if all(x is not None for x in consensus) else None
        else:
            payload = "".join(row["recovered"] for row in output) if all(row.get("recovered") is not None for row in output) else None
        return {
            "mode": mode, "reference_assisted": True,
            "duration_seconds": seconds, "block_count": len(output),
            "status": "IDENTIFIED" if payload is not None else "UNKNOWN",
            "recovered_payload": payload,
            "accepted_blocks": sum(r["status"] == "IDENTIFIED" for r in output),
            "threshold": threshold,
            "blocks": output,
            "notice": "Detected with the caller-supplied key and matching original. No expected message was passed to the detector.",
        }


def _execute_process(raw: bytes, channel: str, seconds: int):
    if channel not in CHANNELS:
        raise HTTPException(422, "Unknown processing channel")
    if seconds not in (6, 72):
        raise HTTPException(422, "Processing duration must be 6 or 72")
    with _temp() as work:
        decoded = _to_mono_float(raw, seconds, work, exact_length=True)
        source = work / "marked.wav"
        wavfile.write(source, SR, np.asarray(decoded, dtype=np.float32))
        if channel == "clean":
            return _make_wav(decoded), "audio/wav", "received-clean.wav"
        if channel in {"mp3", "aac", "mp3_aac"}:
            mp3 = work / "received.mp3"
            aac = work / "received.m4a"
            if channel in ("mp3", "mp3_aac"):
                _ffmpeg(["-i", str(source), "-vn", "-c:a", "libmp3lame", "-b:a", "128k", str(mp3)])
            if channel in ("aac", "mp3_aac"):
                _ffmpeg(["-i", str(mp3 if channel == "mp3_aac" else source), "-vn", "-c:a", "aac", "-profile:a", "aac_low", "-b:a", "128k", "-f", "ipod", str(aac)])
            if channel == "mp3":
                return mp3.read_bytes(), "audio/mpeg", "received-mp3.mp3"
            return aac.read_bytes(), "audio/mp4", "received-aac.m4a"
        target = work / "processed.wav"
        if channel in ("gain_minus6", "gain_plus3"):
            volume = "-6dB" if channel == "gain_minus6" else "+3dB"
            _ffmpeg(["-i", str(source), "-vn", "-filter:a", f"volume={volume}", "-c:a", "pcm_f32le", str(target)])
        elif channel == "resample":
            mid = work / "mid_44k.wav"
            _ffmpeg(["-i", str(source), "-vn", "-ar", "44100", "-c:a", "pcm_f32le", str(mid)])
            _ffmpeg(["-i", str(mid), "-vn", "-ar", "48000", "-c:a", "pcm_f32le", str(target)])
        return target.read_bytes(), "audio/wav", "received-processed.wav"


async def _compute(fn, *args):
    try:
        await asyncio.wait_for(_slots.acquire(), timeout=0.1)
    except asyncio.TimeoutError as exc:
        raise HTTPException(429, "The online lab is busy; retry shortly") from exc
    try:
        # Do not cancel a CPU thread while releasing the semaphore: Python cannot
        # interrupt to_thread safely. FFmpeg calls each enforce their own timeout.
        return await asyncio.to_thread(fn, *args)
    finally:
        _slots.release()


@app.post("/api/v1/embed")
async def embed_endpoint(mode: Annotated[str, Form()], message: Annotated[str, Form()], key: Annotated[str, Form()],
                         source: Annotated[str, Form()] = "sample", reference: UploadFile | None = File(None)):
    seconds, width, *_ = _mode(mode)
    msg = _message(message, width)
    k = _key(key)
    raw = await _read_limited(reference, required=source == "upload")
    data, peak, overfull = await _compute(_execute_embed, raw, source, mode, msg, k)
    return Response(data, media_type="audio/wav", headers={
        "Content-Disposition": 'attachment; filename="watermarked.wav"',
        "Cache-Control": "no-store", "X-Watermark-Mode": mode,
        "X-Output-Peak": f"{peak:.6f}", "X-Overfull-Samples": str(overfull),
    })


@app.post("/api/v1/process")
async def process_endpoint(channel: Annotated[str, Form()], seconds: Annotated[int, Form()], audio: UploadFile = File(...)):
    if channel not in CHANNELS or seconds not in (6, 72):
        raise HTTPException(422, "Unsupported processing condition")
    raw = await _read_limited(audio)
    data, mime, filename = await _compute(_execute_process, raw, channel, seconds)
    return Response(data, media_type=mime, headers={"Content-Disposition": f'attachment; filename="{filename}"', "Cache-Control": "no-store"})


@app.post("/api/v1/detect")
async def detect_endpoint(mode: Annotated[str, Form()], key: Annotated[str, Form()],
                          source: Annotated[str, Form()] = "sample",
                          reference: UploadFile | None = File(None),
                          received: UploadFile = File(...)):
    _mode(mode)
    k = _key(key)
    ref = await _read_limited(reference, required=source == "upload")
    recv = await _read_limited(received)
    result = await _compute(_execute_detect, ref, recv, source, mode, k)
    return JSONResponse(result, headers={"Cache-Control": "no-store"})
