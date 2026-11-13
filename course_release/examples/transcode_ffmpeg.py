#!/usr/bin/env python3
"""Encode a WAV as real MP3 128 kbps or AAC-LC/M4A 128 kbps with FFmpeg."""
from __future__ import annotations

import argparse
import subprocess
from pathlib import Path


def build_ffmpeg_command(input_wav: Path, output: Path, codec: str) -> list[str]:
    common = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(input_wav), "-vn"]
    if codec == "mp3":
        return common + ["-c:a", "libmp3lame", "-b:a", "128k", str(output)]
    if codec == "aac":
        return common + [
            "-c:a", "aac", "-profile:a", "aac_low", "-b:a", "128k", "-f", "ipod", str(output)
        ]
    raise ValueError("codec must be 'mp3' or 'aac'")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input_wav", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--codec", choices=("mp3", "aac"), required=True)
    parser.add_argument("--decode-to", type=Path, help="Optionally decode the encoded file to float32 WAV")
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(build_ffmpeg_command(args.input_wav, args.output, args.codec), check=True)
    if args.decode_to:
        args.decode_to.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            [
                "ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(args.output),
                "-c:a", "pcm_f32le", str(args.decode_to),
            ],
            check=True,
        )
    print(f"Wrote {args.output}")


if __name__ == "__main__":
    main()
