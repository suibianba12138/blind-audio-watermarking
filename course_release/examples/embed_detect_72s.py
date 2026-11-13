#!/usr/bin/env python3
"""Demonstrate C2 repeated 32-bit Long-ID or C3-16 independent 192-bit mode."""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

import numpy as np
from scipy.io import wavfile

from course_watermark.c2 import Config as C2Config, detect as c2_detect, embed as c2_embed
from course_watermark.c3 import Config as C3Config, detect as c3_detect, embed as c3_embed
from payload_layout import c2_long_id_block_messages, c3_192bit_block_messages

SAMPLE_RATE = 48_000
BLOCK_SAMPLES = 6 * SAMPLE_RATE
BLOCK_COUNT = 12
THRESHOLD = {"c2-long-id": 0.6226488835443009, "c3-192": 0.7199080718655814}


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
    if audio.size < BLOCK_SAMPLES * BLOCK_COUNT:
        raise ValueError("input WAV must contain at least 72 seconds")
    return audio[: BLOCK_SAMPLES * BLOCK_COUNT]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=THRESHOLD, required=True)
    parser.add_argument("--reference", type=Path, required=True)
    parser.add_argument("--message", required=True, help="8 hex digits for C2 Long-ID; 48 for C3-192")
    parser.add_argument("--key", required=True, help="Use the public demo key or your own key")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    reference = read_mono_float(args.reference)
    if args.mode == "c2-long-id":
        messages = c2_long_id_block_messages(args.message)
        config = C2Config(key=args.key, target_snr_db=45.0)
        embed_fn, detect_fn, width = c2_embed, c2_detect, 2
    else:
        messages = c3_192bit_block_messages(args.message)
        config = C3Config(key=args.key, target_snr_db=45.0)
        embed_fn, detect_fn, width = c3_embed, c3_detect, 4

    marked_blocks = []
    for index, message in enumerate(messages):
        start = index * BLOCK_SAMPLES
        block = reference[start : start + BLOCK_SAMPLES]
        marked_blocks.append(embed_fn(block, message, config))
    marked = np.concatenate(marked_blocks)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    wavfile.write(args.output, SAMPLE_RATE, marked.astype(np.float32))

    read_rate, readback = wavfile.read(args.output)
    if read_rate != SAMPLE_RATE or readback.shape != marked.shape:
        raise RuntimeError("saved WAV readback does not match embedded audio")
    received = readback.astype(np.float64)
    results = []
    for index, target in enumerate(messages):
        start = index * BLOCK_SAMPLES
        received_block = received[start : start + BLOCK_SAMPLES]
        reference_block = reference[start : start + BLOCK_SAMPLES]
        detection = detect_fn(received_block, reference_block, config)
        accepted = (
            detection.presence_stat >= THRESHOLD[args.mode]
            and detection.reference_similarity >= 0.5
        )
        results.append(
            {
                "block": index + 1,
                "start_seconds": index * 6,
                "target_for_scoring_only": f"0x{target:0{width}X}",
                "recovered_message": f"0x{detection.message:0{width}X}",
                "correct": detection.message == target,
                "presence_stat": detection.presence_stat,
                "reference_similarity": detection.reference_similarity,
                "alignment_lag_samples": detection.alignment_lag_samples,
                "status": "IDENTIFIED" if accepted else "UNKNOWN",
            }
        )

    if args.mode == "c2-long-id":
        recovered_bytes = []
        for byte_position in range(4):
            repeated = [
                results[repeat * 4 + byte_position]["recovered_message"]
                for repeat in range(3)
                if results[repeat * 4 + byte_position]["status"] == "IDENTIFIED"
            ]
            values = [int(value, 16) for value in repeated]
            counts = Counter(values)
            winner, votes = counts.most_common(1)[0] if counts else (None, 0)
            recovered_bytes.append(winner if votes >= 2 else None)
        recovered_payload = (
            "".join(f"{value:02X}" for value in recovered_bytes)
            if all(value is not None for value in recovered_bytes)
            else None
        )
    else:
        recovered_payload = (
            "".join(row["recovered_message"][2:] for row in results)
            if all(row["status"] == "IDENTIFIED" for row in results)
            else None
        )

    expected_payload = args.message.removeprefix("0x").removeprefix("0X").upper()
    summary = {
        "mode": args.mode,
        "reference_assisted": True,
        "reference": args.reference.name,
        "output": args.output.name,
        "sample_rate_hz": SAMPLE_RATE,
        "duration_seconds": 72,
        "block_duration_seconds": 6,
        "block_count": BLOCK_COUNT,
        "target_for_scoring_only": "0x" + expected_payload,
        "recovered_payload": "0x" + recovered_payload if recovered_payload else None,
        "complete_match": recovered_payload == expected_payload,
        "threshold": THRESHOLD[args.mode],
        "blocks": results,
    }
    args.output.with_suffix(".json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
