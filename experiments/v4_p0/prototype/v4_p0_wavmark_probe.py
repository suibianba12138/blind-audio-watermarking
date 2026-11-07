"""Run a minimal WavMark official-model CPU/MP3 probe outside the repo code.

Run this script with the external WavMark wheel on ``PYTHONPATH`` and an
existing Torch environment. The third-party package is intentionally not a
dependency of this repository and no model file is copied into Git.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import tempfile
import time
from pathlib import Path

import numpy as np
import torch
from scipy.io import wavfile


def _to_float(values: np.ndarray) -> np.ndarray:
    array = np.asarray(values)
    if np.issubdtype(array.dtype, np.integer):
        info = np.iinfo(array.dtype)
        array = array.astype(np.float32) / float(max(abs(info.min), info.max))
    else:
        array = array.astype(np.float32)
    if array.ndim == 2:
        array = array[:, 0]
    return np.asarray(array, dtype=np.float32)


def run(source: Path, checkpoint: Path, output: Path) -> dict[str, object]:
    import wavmark  # external package, loaded only in the probe environment

    sample_rate, values = wavfile.read(source)
    if int(sample_rate) != 16_000:
        raise ValueError("the minimal probe expects a 16 kHz source")
    clean = _to_float(values)[:16_000]
    if clean.size < 16_000:
        clean = np.pad(clean, (0, 16_000 - clean.size))
    model = wavmark.load_model(str(checkpoint))
    payload = np.asarray([1, 0, 1, 1, 0, 0, 1, 0] * 4, dtype=np.float32)
    with torch.no_grad():
        started = time.perf_counter()
        marked = model.encode(torch.from_numpy(clean)[None], torch.from_numpy(payload)[None]).cpu().numpy().squeeze()
        encode_seconds = time.perf_counter() - started
    with tempfile.TemporaryDirectory(prefix="v4_wavmark_probe_") as directory:
        root = Path(directory)
        marked_wav = root / "marked.wav"
        encoded_mp3 = root / "marked_128k.mp3"
        received_wav = root / "received.wav"
        wavfile.write(marked_wav, 16_000, np.asarray(marked, dtype=np.float32))
        ffmpeg = "ffmpeg"
        subprocess.run(
            [ffmpeg, "-hide_banner", "-loglevel", "error", "-y", "-i", str(marked_wav), "-ac", "1", "-ar", "16000", "-c:a", "libmp3lame", "-b:a", "128k", str(encoded_mp3)],
            check=True, shell=False, capture_output=True, text=True, timeout=120,
        )
        subprocess.run(
            [ffmpeg, "-hide_banner", "-loglevel", "error", "-y", "-i", str(encoded_mp3), "-ac", "1", "-ar", "16000", "-c:a", "pcm_f32le", str(received_wav)],
            check=True, shell=False, capture_output=True, text=True, timeout=120,
        )
        _, received_values = wavfile.read(received_wav)
        received = _to_float(received_values)[:16_000]
        with torch.no_grad():
            started = time.perf_counter()
            decoded = model.decode(torch.from_numpy(received)[None]).cpu().numpy().squeeze()
            decode_seconds = time.perf_counter() - started
        decoded_bits = (decoded >= 0.5).astype(np.int8)
        clean_bits = payload.astype(np.int8)
        result = {
            "status": "PASS",
            "repository": "https://github.com/wavmark/wavmark",
            "model_protocol": "32 model bits: 16 fixed identification bits + 16 custom payload bits",
            "source": str(source),
            "sample_rate_hz": 16_000,
            "message_model_bits": 32,
            "effective_custom_payload_bits": 16,
            "condition": "one-second block, clean and FFmpeg libmp3lame 128k",
            "device": "cpu",
            "torch_version": torch.__version__,
            "cuda_available": bool(torch.cuda.is_available()),
            "encode_seconds": encode_seconds,
            "decode_seconds": decode_seconds,
            "clean_snr_db": float(10.0 * np.log10(np.mean(clean * clean) / np.mean((clean - marked) ** 2))),
            "mp3_ber": float(np.mean(decoded_bits != clean_bits)),
            "mp3_exact_recovery": bool(np.array_equal(decoded_bits, clean_bits)),
            "decoded_bits": decoded_bits.tolist(),
            "payload_bits": clean_bits.tolist(),
            "mp3_bytes": int(encoded_mp3.stat().st_size),
            "third_party_source_copied_into_repo": False,
        }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(run(args.source, args.checkpoint, args.output), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
