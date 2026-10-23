"""Real FFmpeg MP3 128 kbps round-trip used by the public demo."""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path

from .audio_io import (
    AudioData,
    FFMPEG_TIMEOUT_SECONDS,
    TARGET_SAMPLE_RATE,
    decode_audio_file,
    write_wav,
)


def encode_decode_mp3(
    marked: AudioData,
    output_dir: str | Path,
    *,
    bitrate_kbps: int = 128,
) -> tuple[Path, Path, AudioData]:
    """Encode marked audio to MP3 and decode it back using FFmpeg."""

    if bitrate_kbps != 128:
        raise ValueError("the public demo freezes MP3 at 128 kbps")
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        raise RuntimeError("FFmpeg is required for the MP3 demo")
    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="watermark_mp3_") as directory:
        temporary_input = write_wav(Path(directory) / "input.wav", marked)
        temporary_mp3 = Path(directory) / "encoded.mp3"
        temporary_decoded = Path(directory) / "decoded.wav"
        encode = [
            ffmpeg,
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-i",
            str(temporary_input),
            "-ac",
            "1",
            "-ar",
            str(TARGET_SAMPLE_RATE),
            "-c:a",
            "libmp3lame",
            "-b:a",
            "128k",
            "-f",
            "mp3",
            str(temporary_mp3),
        ]
        decode = [
            ffmpeg,
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-i",
            str(temporary_mp3),
            "-vn",
            "-ac",
            "1",
            "-ar",
            str(TARGET_SAMPLE_RATE),
            "-c:a",
            "pcm_f32le",
            "-f",
            "wav",
            str(temporary_decoded),
        ]
        for command, label in ((encode, "encode"), (decode, "decode")):
            try:
                subprocess.run(
                    command,
                    check=True,
                    shell=False,
                    capture_output=True,
                    text=True,
                    timeout=FFMPEG_TIMEOUT_SECONDS,
                )
            except subprocess.CalledProcessError as error:
                detail = (error.stderr or "").strip()[-500:]
                raise RuntimeError(f"FFmpeg MP3 {label} failed: {detail}") from error
            except subprocess.TimeoutExpired as error:
                raise RuntimeError(f"FFmpeg MP3 {label} timed out") from error
        public_mp3 = destination / "compressed_128k.mp3"
        public_wav = destination / "compressed_128k_decoded.wav"
        shutil.copyfile(temporary_mp3, public_mp3)
        shutil.copyfile(temporary_decoded, public_wav)
    decoded = decode_audio_file(public_wav)
    return public_mp3, public_wav, decoded
