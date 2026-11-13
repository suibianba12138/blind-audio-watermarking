import json
import os
import subprocess
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).parents[1]
FIXTURE = ROOT / "media" / "selected_c3_16_showcase" / "Original.wav"


@pytest.mark.parametrize(
    ("mode", "message"),
    [("c2-8", "A7"), ("c3-16", "A7C3")],
)
def test_six_second_cli_saves_and_detects_readback(tmp_path, mode, message):
    output = tmp_path / f"{mode}.wav"
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(ROOT / "src")
    subprocess.run(
        [
            sys.executable,
            str(ROOT / "examples" / "embed_detect_6s.py"),
            "--mode",
            mode,
            "--reference",
            str(FIXTURE),
            "--message",
            message,
            "--key",
            "course-demo-public-v1",
            "--output",
            str(output),
        ],
        check=True,
        capture_output=True,
        text=True,
        env=environment,
    )
    result = json.loads(output.with_suffix(".json").read_text())
    assert result["recovered_message"] == f"0x{message}"
    assert result["correct"] is True
    assert result["status"] == "IDENTIFIED"
    assert result["reference_assisted"] is True


def test_ffmpeg_command_uses_real_128k_codec_parameters():
    sys.path.insert(0, str(ROOT / "examples"))
    from transcode_ffmpeg import build_ffmpeg_command

    mp3 = build_ffmpeg_command(Path("input.wav"), Path("out.mp3"), "mp3")
    aac = build_ffmpeg_command(Path("input.wav"), Path("out.m4a"), "aac")
    assert "libmp3lame" in mp3 and "128k" in mp3
    assert "aac_low" in aac and "128k" in aac and "ipod" in aac
