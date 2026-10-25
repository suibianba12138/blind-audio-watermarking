from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest
from scipy.io import wavfile

from app.audio_io import MAX_INPUT_BYTES


def make_wav(path: Path, *, seconds: float = 6.0) -> Path:
    sample_rate = 48_000
    count = int(seconds * sample_rate)
    time = np.arange(count, dtype=np.float64) / sample_rate
    notes = (220.0, 277.18, 329.63, 440.0, 554.37, 659.25)
    values = sum(
        (0.20 / (1.0 + index / 3.0))
        * np.sin(2.0 * np.pi * frequency * time + index * 0.37)
        for index, frequency in enumerate(notes)
    )
    values *= 0.75 + 0.25 * np.sin(2.0 * np.pi * 0.5 * time) ** 2
    values += 0.025 * np.sin(2.0 * np.pi * 1760.0 * time)
    values /= max(1.0, float(np.max(np.abs(values))) / 0.30)
    wavfile.write(path, sample_rate, values.astype(np.float32))
    return path


def test_v3_pipeline_writes_mp3_outputs_and_detects_blindly(tmp_path: Path) -> None:
    if shutil.which("ffmpeg") is None:
        pytest.skip("FFmpeg is required for the real MP3 pipeline test")

    from app.v3_pipeline import run_v3_demo

    run = run_v3_demo(
        make_wav(tmp_path / "input.wav"),
        173,
        codec="mp3",
        output_dir=tmp_path / "run",
    )

    assert run.original_wav.is_file()
    assert run.marked_wav.is_file()
    assert run.compressed_mp3 is not None and run.compressed_mp3.is_file()
    assert run.compressed_wav is not None and run.compressed_wav.is_file()
    assert run.received_path == run.compressed_wav
    assert run.detection.status == "IDENTIFIED"
    assert run.detection.message == 173


def test_v3_pipeline_identity_keeps_successful_outputs(tmp_path: Path) -> None:
    from app.v3_pipeline import run_v3_demo

    output_dir = tmp_path / "identity-run"
    run = run_v3_demo(make_wav(tmp_path / "input.wav"), 0, output_dir=output_dir)

    assert run.codec == "identity"
    assert run.compressed_mp3 is None
    assert run.compressed_wav is None
    assert run.received_path == run.marked_wav
    assert run.detection.status == "IDENTIFIED"
    assert run.detection.message == 0
    assert all(path.is_file() for path in (run.original_wav, run.marked_wav))


def test_uploaded_detector_reads_only_the_received_file(tmp_path: Path) -> None:
    from app.v3_pipeline import detect_uploaded_file

    result = detect_uploaded_file(make_wav(tmp_path / "clean.wav"))

    assert result.status == "UNKNOWN"
    assert result.message is None


def test_v3_pipeline_rejects_unknown_codec_before_writing_outputs(tmp_path: Path) -> None:
    from app.v3_pipeline import run_v3_demo

    output_dir = tmp_path / "bad-run"
    with pytest.raises(ValueError, match="codec must be identity or mp3"):
        run_v3_demo(make_wav(tmp_path / "input.wav"), 173, codec="aac", output_dir=output_dir)
    assert not output_dir.exists()


def test_v3_pipeline_rejects_existing_output_dir_without_overwrite(tmp_path: Path) -> None:
    from app.v3_pipeline import run_v3_demo

    output_dir = tmp_path / "existing-run"
    output_dir.mkdir()
    sentinel = output_dir / "watermarked.wav"
    sentinel.write_bytes(b"preserve this file")

    with pytest.raises(FileExistsError, match="must not already exist"):
        run_v3_demo(make_wav(tmp_path / "input.wav"), 173, output_dir=output_dir)

    assert sentinel.read_bytes() == b"preserve this file"


def test_v3_pipeline_rejects_symlinked_output_dir(tmp_path: Path) -> None:
    from app.v3_pipeline import run_v3_demo

    target = tmp_path / "target"
    target.mkdir()
    output_dir = tmp_path / "linked-run"
    output_dir.symlink_to(target, target_is_directory=True)

    with pytest.raises(FileExistsError, match="must not already exist"):
        run_v3_demo(make_wav(tmp_path / "input.wav"), 173, output_dir=output_dir)

    assert list(target.iterdir()) == []


def test_v3_pipeline_removes_new_partial_output_dir_on_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import app.v3_pipeline as pipeline

    def fail_detection(_received_path: Path) -> object:
        raise RuntimeError("injected detector failure")

    monkeypatch.setattr(pipeline, "_detect_in_subprocess", fail_detection)
    output_dir = tmp_path / "partial-run"

    with pytest.raises(RuntimeError, match="injected detector failure"):
        pipeline.run_v3_demo(make_wav(tmp_path / "input.wav"), 173, output_dir=output_dir)

    assert not output_dir.exists()


def test_uploaded_detector_rejects_oversized_input_before_session_creation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import app.v3_pipeline as pipeline

    oversized = tmp_path / "oversized.wav"
    with oversized.open("wb") as stream:
        stream.truncate(MAX_INPUT_BYTES + 1)

    def session_must_not_be_created() -> object:
        pytest.fail("oversized input allocated a temporary detection session")

    monkeypatch.setattr(pipeline, "_new_session", session_must_not_be_created)
    with pytest.raises(ValueError, match="64 MiB"):
        pipeline.detect_uploaded_file(oversized)


def test_pipeline_rejects_unknown_detector_status() -> None:
    from app.v3_pipeline import _result_from_payload

    payload = {
        "status": "NOT_A_VALID_STATUS",
        "message": None,
        "presence_score": 0.0,
        "threshold": 0.7,
        "margin": -0.7,
        "duration_seconds": 6.0,
        "sample_rate": 48_000,
        "provenance": {},
    }

    with pytest.raises(RuntimeError, match="invalid detector status"):
        _result_from_payload(payload)


def test_cli_embed_emits_structured_json(tmp_path: Path) -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "scripts/v3_demo.py",
            "--input",
            str(make_wav(tmp_path / "input.wav")),
            "--message",
            "173",
            "--output-dir",
            str(tmp_path / "cli-run"),
        ],
        cwd=Path(__file__).parents[1],
        env={**os.environ, "PYTHONPATH": "src:scripts:."},
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    payload = json.loads(completed.stdout)
    assert payload["detection"]["status"] == "IDENTIFIED"
    assert payload["detection"]["message"] == 173


def test_cli_requires_message_for_embed_mode(tmp_path: Path) -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "scripts/v3_demo.py",
            "--input",
            str(make_wav(tmp_path / "input.wav")),
        ],
        cwd=Path(__file__).parents[1],
        env={**os.environ, "PYTHONPATH": "src:scripts:."},
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 2
    payload = json.loads(completed.stdout)
    assert payload["status"] == "ERROR"
    assert "message" in payload["error"]


def test_cli_detect_input_is_blind_and_returns_unknown_for_clean_audio(tmp_path: Path) -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "scripts/v3_demo.py",
            "--detect-input",
            str(make_wav(tmp_path / "clean.wav")),
        ],
        cwd=Path(__file__).parents[1],
        env={**os.environ, "PYTHONPATH": "src:scripts:."},
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    payload = json.loads(completed.stdout)
    assert payload["mode"] == "detect"
    assert payload["detection"]["status"] == "UNKNOWN"
    assert payload["detection"]["message"] is None
