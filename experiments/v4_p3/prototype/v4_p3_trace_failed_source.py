"""Read-only focused trace for P3's single failed source; no model changes."""
from __future__ import annotations

import hashlib
import json
import os
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
RESULTS = ROOT / "experiments/v4_p3/RESULTS.json"
OUT = ROOT / "experiments/v4_p3/SPEECH02_FAILURE_TRACE.json"
TARGET_SR = 44100


def main() -> None:
    manifest = json.loads(MANIFEST.read_text())
    source = next(s for s in manifest["sources"] if s["source_id"] == "speech_02")
    path = Path(os.environ["V4_P3_MUSAN_ROOT"]) / source["relative_path"]
    if hashlib.sha256(path.read_bytes()).hexdigest() != source["sha256"]:
        raise RuntimeError("source hash mismatch")
    info = sf.info(path)
    x, sr = sf.read(path, start=int(source["crop_start_seconds"] * info.samplerate),
                    frames=int(12 * info.samplerate), dtype="float32", always_2d=True)
    x = x.mean(axis=1)
    if sr != TARGET_SR:
        x = librosa.resample(x, orig_sr=sr, target_sr=TARGET_SR)
    torch.set_num_threads(4)
    sc_root = Path(os.environ["SILENTCIPHER_SOURCE_ROOT"])
    model_dir = Path(os.environ["SILENTCIPHER_MODEL_DIR"])
    sys.path.insert(0, str(sc_root / "src"))
    from silentcipher import get_model
    from app.silentcipher_diagnostics import trace_official_decoder

    model = get_model(model_type="44.1k", ckpt_path=str(model_dir),
                      config_path=str(model_dir / "hparams.yaml"), device="cpu")
    rows = []
    for mi, payload_hex in enumerate(manifest["payloads_40bit"], 1):
        marked, _ = model.encode_wav(x, TARGET_SR, list(bytes.fromhex(payload_hex)), calc_sdr=True)
        marked = np.asarray(marked, dtype=np.float32)
        arrays = {"positive_clean": marked}
        with tempfile.TemporaryDirectory(prefix="v4-p3-trace-") as td:
            td = Path(td)
            wav, mp3, decoded = td / "marked.wav", td / "marked.mp3", td / "decoded.wav"
            sf.write(wav, marked, TARGET_SR, subtype="PCM_16")
            subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(wav), "-ac", "1", "-ar", str(TARGET_SR), "-c:a", "libmp3lame", "-b:a", "128k", str(mp3)], check=True, timeout=90)
            subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(mp3), "-ac", "1", "-ar", str(TARGET_SR), "-c:a", "pcm_f32le", "-f", "wav", str(decoded)], check=True, timeout=90)
            y, _ = sf.read(decoded, dtype="float32")
            arrays["positive_mp3_128k"] = np.asarray(y[:len(marked)], dtype=np.float32)
        for condition, audio in arrays.items():
            decoded_result = model.decode_wav(audio, TARGET_SR, phase_shift_decoding=False)
            if isinstance(decoded_result, list):
                decoded_result = decoded_result[0] if decoded_result else {}
            trace = trace_official_decoder(model, audio, TARGET_SR)
            decoders = trace.get("per_decoder", [])
            rows.append({
                "source_id": "speech_02", "condition": condition, "message_id": f"M{mi}",
                "expected_message_hex": payload_hex,
                "official_status": bool(decoded_result.get("status", False)),
                "candidate": decoded_result.get("messages", []),
                "confidence": decoded_result.get("confidences", []),
                "trace_status": trace.get("status"),
                "decoders": [{k: d.get(k) for k in (
                    "decoder_index", "stage", "parse_error", "terminator_index", "confidence",
                    "frame_count", "group_count", "modal_symbols", "candidate", "frame_symbol_histogram",
                )} for d in decoders],
            })
    supplement = {"status": "RUNTIME_COMPLETE", "purpose": "focused decoder trace; does not alter or tune model",
                  "protocol_id": manifest["protocol_id"], "presence_threshold": manifest["presence_threshold"], "records": rows}
    OUT.write_text(json.dumps(supplement, indent=2, sort_keys=True) + "\n")
    result = json.loads(RESULTS.read_text())
    for trace_record in rows:
        match = next(r for r in result["records"] if r["source_id"] == trace_record["source_id"] and
                     r["condition"] == trace_record["condition"] and r["message_id"] == trace_record["message_id"])
        decoders = trace_record["decoders"]
        match["trace_status"] = trace_record["trace_status"]
        match["trace_stage_by_decoder"] = [d["stage"] for d in decoders]
        match["trace_parse_error_by_decoder"] = [d["parse_error"] for d in decoders]
        match["trace_terminator_index_by_decoder"] = [d["terminator_index"] for d in decoders]
        match["frame_confidence_by_decoder"] = [d["confidence"] for d in decoders]
        match["terminator_missing"] = any(d["parse_error"] == "MISSING_TERMINATOR" for d in decoders)
        match["focused_trace_rerun"] = True
    RESULTS.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": supplement["status"], "records": len(rows),
                      "missing_terminator": sum(any(d["parse_error"] == "MISSING_TERMINATOR" for d in r["decoders"]) for r in rows),
                      "wrong_message_candidates": sum(any(d["candidate"] is not None for d in r["decoders"]) and r["condition"] == "positive_mp3_128k" and r["candidate"] != [[int(r["expected_message_hex"][i:i+2], 16) for i in range(0, 10, 2)]] for r in rows)}, indent=2))


if __name__ == "__main__":
    main()
