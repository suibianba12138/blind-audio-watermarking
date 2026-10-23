#!/usr/bin/env python3
"""Generate a deterministic six-second signal for smoke tests and demos."""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np

from app.audio_io import AudioData, TARGET_SAMPLE_RATE, write_wav


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("/tmp/watermark_test_signal.wav"))
    parser.add_argument("--seconds", type=float, default=6.0)
    args = parser.parse_args()
    if not 6.0 <= args.seconds <= 30.0:
        raise SystemExit("seconds must be between 6 and 30")
    time = np.arange(int(args.seconds * TARGET_SAMPLE_RATE), dtype=np.float64) / TARGET_SAMPLE_RATE
    signal = 0.18 * np.sin(2 * np.pi * 440 * time) + 0.08 * np.sin(2 * np.pi * 880 * time)
    signal += 0.03 * np.sin(2 * np.pi * 1730 * time)
    write_wav(args.output, AudioData(signal, TARGET_SAMPLE_RATE))
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
