"""Bounded P5 paired decoder/strength experiment; official model stays untouched."""
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
from app.v4_p5_decoder import decode_official_scores, decode_soft_scores

P1 = json.loads((ROOT / "configs/v4_p1_source_manifest.json").read_text())
P3 = json.loads((ROOT / "configs/v4_p3_source_manifest.json").read_text())
HOLDOUT = json.loads((ROOT / "configs/v4_p5_eval_manifest.json").read_text())
THRESHOLD = float(HOLDOUT["presence_threshold"])
STRENGTHS = HOLDOUT["strengths_message_sdr_db"]
PAYLOADS = [bytes.fromhex(x) for x in HOLDOUT["payloads_40bit_hex"]]
SR = 44100
EXPECTED_CHECKPOINT_SHA256 = {
    "enc_c.ckpt": "ff64f80d2391fdfc888e4103c499be4a2c958e59626587a1eab6db93204814c7",
    "dec_c.ckpt": "c23b57635172b2fbd3a8531d15ba76b5885a10d0fe902ccb823c521c56041b33",
    "dec_m_0.ckpt": "829540c058270d29788f05294894d45bf436e44add0e1099422242ebb94b7088",
}


def _source_path(source: dict, p1: bool = False) -> Path:
    if p1 and source["category"] == "music":
        return Path(os.environ["V4_P1_MUSIC_ROOT"]) / source["relative_path"]
    root_env = "V4_P1_MUSAN_ROOT" if p1 else source.get("root_env", "V4_P3_MUSAN_ROOT")
    if source.get("root_env"):
        root_env = source["root_env"]
    return Path(os.environ[root_env]) / source["relative_path"]


def _load_source(source: dict, p1: bool = False) -> np.ndarray:
    path = _source_path(source, p1)
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if digest != source["sha256"]:
        raise RuntimeError(f"source hash mismatch: {source['source_id']}")
    start = source.get("start_seconds", source.get("crop_start_seconds", 0.0))
    duration = float(source.get("duration_seconds", source.get("crop_duration_seconds", 12.0)))
    with sf.SoundFile(path) as f:
        f.seek(int(start * f.samplerate))
        x = f.read(frames=int(duration * f.samplerate), dtype="float32", always_2d=True)
        rate = f.samplerate
    x = x.mean(axis=1)
    if rate != SR:
        x = librosa.resample(x, orig_sr=rate, target_sr=SR)
    n = SR * 12
    if len(x) < n:
        x = np.pad(x, (0, n - len(x)))
    return np.asarray(x[:n], dtype=np.float32)


def _mp3_roundtrip(audio: np.ndarray) -> np.ndarray:
    with tempfile.TemporaryDirectory(prefix="v4-p5-mp3-") as td:
        td = Path(td)
        wav, mp3, out = td / "in.wav", td / "out.mp3", td / "decoded.wav"
        sf.write(wav, audio, SR, subtype="PCM_16")
        subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(wav), "-ac", "1", "-ar", str(SR), "-c:a", "libmp3lame", "-b:a", "128k", str(mp3)], check=True, timeout=60)
        subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(mp3), "-ac", "1", "-ar", str(SR), "-c:a", "pcm_f32le", "-f", "wav", str(out)], check=True, timeout=60)
        y, _ = sf.read(out, dtype="float32")
    return np.asarray(y[:len(audio)], dtype=np.float32)


def _quality(reference: np.ndarray, marked: np.ndarray) -> tuple[float, float]:
    n = min(len(reference), len(marked))
    ref, out = reference[:n], marked[:n]
    noise = out - ref
    snr = float(10 * np.log10((np.mean(ref ** 2) + 1e-20) / (np.mean(noise ** 2) + 1e-20)))
    a = np.abs(librosa.stft(ref, n_fft=4096, hop_length=2048, window="hann"))
    b = np.abs(librosa.stft(out, n_fft=4096, hop_length=2048, window="hann"))
    eps = max(float(a.max()) * 1e-8, 1e-12)
    lsd = float(np.sqrt(np.mean((20 * np.log10(np.maximum(a, eps)) - 20 * np.log10(np.maximum(b, eps))) ** 2)))
    return snr, lsd


def _raw_scores(model, audio: np.ndarray) -> tuple[np.ndarray, float]:
    power = float(np.mean(audio ** 2))
    if not np.isfinite(power) or power <= 0:
        raise ValueError("zero_or_invalid_power")
    normalized = audio * np.sqrt(model.average_energy_VCTK / power)
    tensor = torch.as_tensor(normalized, dtype=torch.float32, device=model.device)[None, None]
    start = time.perf_counter()
    with torch.no_grad():
        carrier, _ = model.stft.transform(tensor.squeeze(1))
        logits = model.dec_m[0](carrier[:, None])[0, 0].transpose(0, 1).contiguous()
    elapsed = time.perf_counter() - start
    return logits.detach().cpu().numpy(), elapsed


def _record_detection(model, audio: np.ndarray, source_id: str, condition: str,
                      message_hex: str | None = None, sdr_db: int | None = None) -> list[dict]:
    scores, elapsed = _raw_scores(model, audio)
    out = []
    for method, decoder in (("official", decode_official_scores), ("soft", decode_soft_scores)):
        result = decoder(scores, message_len=model.message_len)
        candidate = result["candidate"]
        valid = bool(candidate and len(candidate) == 10)
        accepted = valid and result["confidence"] >= THRESHOLD
        correct = candidate == message_hex if message_hex is not None else None
        out.append({
            "source_id": source_id, "condition": condition, "message_hex": message_hex,
            "message_sdr_db": sdr_db, "decoder": method,
            "candidate_hex": candidate, "confidence": result["confidence"],
            "terminator_index": result["terminator_index"], "parse_error": result["parse_error"],
            "raw_exact": bool(correct) if correct is not None else None,
            "accepted": bool(accepted),
            "correct_accepted": bool(accepted and correct) if correct is not None else None,
            "wrong_message_accepted": bool(accepted and not correct) if correct is not None else None,
            "negative_acceptance": bool(accepted) if correct is None else None,
            "decode_seconds_network_forward": elapsed,
            "frame_count": result["frame_count"], "group_count": result["group_count"],
            "selected_mean_score": result["selected_mean_score"],
        })
    return out


def _p1_p3_dev_sources() -> list[tuple[dict, bool, list[bytes]]]:
    p1_m = next(s for s in P1["sources"] if s["source_id"] == "music_03")
    p3 = {s["source_id"]: s for s in P3["sources"]}
    return [
        (p1_m, True, [bytes(P1["messages_40bit"][0])]),
        (p3["speech_02"], False, [bytes.fromhex(x) for x in P3["payloads_40bit"]]),
        (p3["music_01"], False, [bytes.fromhex(x) for x in P3["payloads_40bit"]]),
        (p3["speech_03"], False, [bytes.fromhex(x) for x in P3["payloads_40bit"]]),
        (p3["environment_01"], False, [bytes.fromhex(x) for x in P3["payloads_40bit"]]),
    ]


def run_partition(model, sources, partition: str) -> dict:
    records: list[dict] = []
    source_manifest = []
    for source, is_p1, messages in sources:
        source_id = ("p1_" if is_p1 else "p3_") + source["source_id"] if partition == "development" else source["source_id"]
        x = _load_source(source, is_p1)
        source_manifest.append({"source_id": source_id, "category": source["category"], "sha256": source["sha256"],
                                "source_sample_rate_hz": source.get("source_sample_rate_hz"),
                                "clip_seconds": 12.0})
        neg_mp3 = _mp3_roundtrip(x)
        records.extend(_record_detection(model, x, source_id, "negative_clean"))
        records.extend(_record_detection(model, neg_mp3, source_id, "negative_mp3_128k"))
        for msg in messages:
            msg_hex = msg.hex().upper()
            for strength in STRENGTHS:
                t0 = time.perf_counter()
                marked, _ = model.encode_wav(x, SR, list(msg), message_sdr=strength, calc_sdr=True)
                embed_seconds = time.perf_counter() - t0
                marked = np.asarray(marked, dtype=np.float32)
                snr, lsd = _quality(x, marked)
                attacked = _mp3_roundtrip(marked)
                for condition, y in (("clean", marked), ("mp3_128k", attacked)):
                    these = _record_detection(model, y, source_id, condition, msg_hex, strength)
                    for r in these:
                        r.update({"embed_seconds": embed_seconds, "embedding_snr_db": snr,
                                  "embedding_lsd_db": lsd})
                    records.extend(these)
        print(f"{partition}: {source_id} complete ({len(records)} records)", flush=True)
    return {"partition": partition, "threshold_frozen": THRESHOLD,
            "strengths_message_sdr_db": STRENGTHS, "sources": source_manifest,
            "records": records, "peak_rss_kib_process": int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)}


def main() -> None:
    official_root = Path(os.environ["SILENTCIPHER_SOURCE_ROOT"])
    model_dir = Path(os.environ["SILENTCIPHER_MODEL_DIR"])
    observed_hashes = {name: hashlib.sha256((model_dir / name).read_bytes()).hexdigest()
                       for name in EXPECTED_CHECKPOINT_SHA256}
    if observed_hashes != EXPECTED_CHECKPOINT_SHA256:
        raise RuntimeError("official checkpoint hash mismatch; aborting before inference")
    sys.path.insert(0, str(official_root / "src"))
    torch.set_num_threads(4)
    torch.set_num_interop_threads(1)
    start = time.perf_counter()
    from silentcipher import get_model
    model = get_model(model_type="44.1k", ckpt_path=str(model_dir),
                      config_path=str(model_dir / "hparams.yaml"), device="cpu")
    model_load = time.perf_counter() - start

    dev = run_partition(model, _p1_p3_dev_sources(), "development")
    dev["model_load_seconds"] = model_load
    dev["checkpoint_sha256"] = observed_hashes
    dev_path = ROOT / "experiments/v4_p5/DEVELOPMENT_RESULTS.json"
    dev_path.write_text(json.dumps(dev, indent=2, sort_keys=True) + "\n")

    holdout_sources = [(s, False, PAYLOADS) for s in HOLDOUT["sources"]]
    holdout = run_partition(model, holdout_sources, "holdout")
    holdout["model_load_seconds"] = model_load
    holdout["checkpoint_sha256"] = dev["checkpoint_sha256"]
    holdout["manifest_sha256"] = hashlib.sha256((ROOT / "configs/v4_p5_eval_manifest.json").read_bytes()).hexdigest()
    (ROOT / "experiments/v4_p5/HOLDOUT_RESULTS.json").write_text(json.dumps(holdout, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"model_load_seconds": model_load, "development_records": len(dev["records"]),
                      "holdout_records": len(holdout["records"]),
                      "peak_rss_kib": max(dev["peak_rss_kib_process"], holdout["peak_rss_kib_process"])}))


if __name__ == "__main__":
    main()
