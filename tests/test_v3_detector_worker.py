from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import numpy as np
from scipy.io import wavfile


def make_wav(path: Path, *, seconds: float = 6.0) -> Path:
    sample_rate = 48_000
    count = int(seconds * sample_rate)
    rng = np.random.default_rng(20261026)
    wavfile.write(
        path,
        sample_rate,
        (0.04 * rng.standard_normal(count)).astype(np.float32),
    )
    return path


def test_worker_has_no_expected_message_option() -> None:
    completed = subprocess.run(
        [sys.executable, "-m", "app.v3_detector_worker", "--help"],
        cwd=Path(__file__).parents[1],
        env={**os.environ, "PYTHONPATH": "src:scripts:."},
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0
    assert "expected" not in completed.stdout.lower()
    assert "--input" in completed.stdout
    assert "--map" in completed.stdout
    assert "validate only" in completed.stdout


def test_worker_emits_one_unknown_json_object_for_clean_audio(tmp_path: Path) -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "app.v3_detector_worker",
            "--input",
            str(make_wav(tmp_path / "clean.wav")),
            "--json",
        ],
        cwd=Path(__file__).parents[1],
        env={**os.environ, "PYTHONPATH": "src:scripts:."},
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    payload = json.loads(completed.stdout)
    assert payload["status"] == "UNKNOWN"
    assert payload["message"] is None


def test_worker_maps_decode_errors_to_json_and_exit_code_two(tmp_path: Path) -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "app.v3_detector_worker",
            "--input",
            str(tmp_path / "missing.wav"),
            "--json",
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
    assert "not found" in payload["error"]
