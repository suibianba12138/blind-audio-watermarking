#!/usr/bin/env python3
"""Embed one C2-8 or C3-16 message and blind-to-message detect its WAV readback.

The detector is reference-assisted: it receives the unwatermarked reference WAV.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from scipy.io import wavfile

from course_watermark.c2 import Config as C2Config
from course_watermark.c2 import detect as c2_detect
from course_watermark.c2 import embed as c2_embed
from course_watermark.c3 import Config as C3Config
from course_watermark.c3 import detect as c3_detect
from course_watermark.c3 import embed as c3_embed

SAMPLE_RATE = 48_000
BLOCK_SAMPLES = 6 * SAMPLE_RATE
THRESHOLDS = {"c2-8": 0.6226488835443009, "c3-16": 0.7199080718655814}


def read_mono_float(path: Path) -> np.ndarray:
    sample_rate, raw = wavfile.read(path)
    if sample_rate != SAMPLE_RATE:
        raise ValueError(f"expected 48000 Hz WAV, got {sample_rate} Hz")
    if np.issubdtype(raw.dtype, np.integer):
        info = np.iinfo(raw.dtype)
        audio = raw.astype(np.float64) / max(abs(info.min), info.max)
    elif np.issubdtype(raw.dtype, np.floating):
        audio = raw.astype(np.float64)
    else:
        raise ValueError(f"unsupported WAV dtype: {raw.dtype}")
    if audio.ndim == 2:
        audio = audio.mean(axis=1)
    if audio.ndim != 1 or not np.isfinite(audio).all():
        raise ValueError("input must decode to finite mono audio")
    if audio.size < BLOCK_SAMPLES:
        raise ValueError("input WAV must contain at least 6 seconds")
    return audio[:BLOCK_SAMPLES]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=THRESHOLDS, required=True)
    parser.add_argument("--reference", type=Path, required=True)
    parser.add_argument("--message", required=True, help="2 hex digits for C2 or 4 for C3")
    parser.add_argument("--key", required=True, help="Use the public demo key or your own key")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    raw_message = args.message.removeprefix("0x")
    width = 2 if args.mode == "c2-8" else 4
    if len(raw_message) != width:
        raise SystemExit(f"{args.mode} requires exactly {width} hex digits")
    try:
        message = int(raw_message, 16)
    except ValueError as error:
        raise SystemExit("message must be hexadecimal") from error

    reference = read_mono_float(args.reference)
    if args.mode == "c2-8":
        config = C2Config(key=args.key, target_snr_db=45.0)
        marked = c2_embed(reference, message, config)
    else:
        config = C3Config(key=args.key, target_snr_db=45.0)
        marked = c3_embed(reference, message, config)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    wavfile.write(args.output, SAMPLE_RATE, marked.astype(np.float32))
    read_rate, readback = wavfile.read(args.output)
    if read_rate != SAMPLE_RATE or readback.shape != marked.shape:
        raise RuntimeError("saved WAV readback does not match embedded audio")
    received = readback.astype(np.float64)
    detection_fn = c2_detect if args.mode == "c2-8" else c3_detect
    detection = detection_fn(received, reference, config)
    accepted = (
        detection.presence_stat >= THRESHOLDS[args.mode]
        and detection.reference_similarity >= 0.5
    )
    result = {
        "mode": args.mode,
        "reference_assisted": True,
        "reference": args.reference.name,
        "output": args.output.name,
        "sample_rate_hz": SAMPLE_RATE,
        "block_duration_seconds": 6,
        "samples_after_readback": int(received.size),
        "target_for_scoring_only": f"0x{message:0{width}X}",
        "recovered_message": f"0x{detection.message:0{width}X}",
        "correct": detection.message == message,
        "presence_stat": detection.presence_stat,
        "frozen_threshold": THRESHOLDS[args.mode],
        "reference_similarity": detection.reference_similarity,
        "alignment_lag_samples": detection.alignment_lag_samples,
        "status": "IDENTIFIED" if accepted else "UNKNOWN",
        "samples_over_full_scale": int(np.sum(np.abs(received) > 1.0)),
    }
    result_path = args.output.with_suffix(".json")
    result_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
