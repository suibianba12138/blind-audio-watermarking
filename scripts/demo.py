#!/usr/bin/env python3
"""Run the public embed -> optional MP3 -> blind-detect demo from the CLI."""

from __future__ import annotations

import argparse
import json

from app.pipeline import run_demo


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="local WAV or FFmpeg-decodable audio")
    parser.add_argument("--identity", choices=["UESTC-001", "UESTC-002", "UESTC-003", "UESTC-004"])
    parser.add_argument("--duration", choices=[6, 15, 30], type=int, default=6)
    parser.add_argument("--codec", choices=["identity", "mp3"], default="identity")
    parser.add_argument("--output-dir", default=None)
    args = parser.parse_args()
    run = run_demo(
        args.input,
        args.identity or "UESTC-001",
        duration_seconds=args.duration,
        codec=args.codec,
        output_dir=args.output_dir,
    )
    print(
        json.dumps(
            {
                "output_dir": str(run.output_dir),
                "original_wav": str(run.original_wav),
                "watermarked_wav": str(run.marked_wav),
                "compressed_mp3": str(run.compressed_mp3) if run.compressed_mp3 else None,
                "received_path": str(run.received_path),
                "block_count": run.block_count,
                "duration_seconds": run.duration_seconds,
                "detection": run.detection,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
