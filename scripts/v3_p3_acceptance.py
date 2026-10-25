#!/usr/bin/env python3
"""Run deterministic, local-only acceptance checks for the V3 P3 candidate.

The command deliberately keeps generated audio in a temporary directory.  The
requested output directory receives only a JSON report containing metadata and
results, so an acceptance run cannot accidentally add media to the repository.
"""

from __future__ import annotations

import argparse
import json
import os
import resource
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import replace
from pathlib import Path
from typing import Any

import numpy as np
from scipy.io import wavfile

ROOT = Path(__file__).resolve().parents[1]
REPORT_NAME = "v3_p3_acceptance.json"
MESSAGES = (0, 1, 173, 255)


def _peak_rss_mb() -> float | None:
    """Return the process peak RSS when the platform exposes it."""

    try:
        value = float(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    except (AttributeError, OSError):
        return None
    # Linux reports KiB; macOS reports bytes.  The execution environment is
    # Linux, but keeping the conversion explicit makes the report portable.
    if sys.platform == "darwin":
        value /= 1024.0 * 1024.0
    else:
        value /= 1024.0
    return round(value, 3)


def _make_fixture(path: Path) -> Path:
    """Write the deterministic music-like fixture used by prior local tests."""

    sample_rate = 48_000
    count = 6 * sample_rate
    time_axis = np.arange(count, dtype=np.float64) / sample_rate
    notes = (220.0, 277.18, 329.63, 440.0, 554.37, 659.25)
    values = sum(
        (0.20 / (1.0 + index / 3.0))
        * np.sin(2.0 * np.pi * frequency * time_axis + index * 0.37)
        for index, frequency in enumerate(notes)
    )
    values *= 0.75 + 0.25 * np.sin(2.0 * np.pi * 0.5 * time_axis) ** 2
    values += 0.025 * np.sin(2.0 * np.pi * 1760.0 * time_axis)
    values /= max(1.0, float(np.max(np.abs(values))) / 0.30)
    wavfile.write(path, sample_rate, values.astype(np.float32))
    return path


def _jsonable(value: object) -> object:
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    return value


def _run_cli(input_path: Path, output_dir: Path) -> tuple[bool, str]:
    environment = os.environ.copy()
    environment["PYTHONPATH"] = os.pathsep.join(
        (str(ROOT / "src"), str(ROOT))
    )
    completed = subprocess.run(
        [
            sys.executable,
            "scripts/v3_demo.py",
            "--input",
            str(input_path),
            "--message",
            "173",
            "--output-dir",
            str(output_dir),
        ],
        cwd=ROOT,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        return False, (completed.stderr or completed.stdout).strip()[-500:]
    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError:
        return False, "CLI did not return JSON"
    detection = payload.get("detection", {})
    passed = (
        detection.get("status") == "IDENTIFIED"
        and detection.get("message") == 173
    )
    return passed, "identified message 173" if passed else "unexpected CLI result"


def _wrong_key_probe(clean_audio: Any, message: int) -> dict[str, object]:
    """Embed with a deterministic alternate frame seed, then detect publicly."""

    from app.audio_io import prepare_for_demo, write_wav
    from app.public_config import build_embedding_config, load_public_selector
    from app.v3_api import _message_bits, detect_message, V3_STRENGTH
    from audio_watermark.b1 import embed_watermark_b1
    from audio_watermark.b2_capacity import encode_capacity_payload

    prepared = prepare_for_demo(clean_audio, duration_seconds=6)
    config = replace(build_embedding_config(), strength=V3_STRENGTH)
    selector = load_public_selector()
    alternate_selector = replace(selector, watermark_seed=991)
    payload = encode_capacity_payload(_message_bits(message), 8)
    wrong_key_samples = embed_watermark_b1(
        prepared.samples, payload, config, alternate_selector
    )
    wrong_key = type(prepared)(wrong_key_samples, prepared.sample_rate)
    result = detect_message(wrong_key)
    return {
        "status": result.status,
        "message": result.message,
        "accepted_as_expected_message": bool(
            result.status == "IDENTIFIED" and result.message == message
        ),
    }


def _session_cleanup_probe(root: Path) -> bool:
    from app.session_store import SessionStore

    store = SessionStore(root)
    session = store.create()
    marker = session.path("marker.txt")
    marker.write_text("temporary", encoding="utf-8")
    session_root = session.root
    session.cleanup()
    session.cleanup()
    return not session_root.exists() and not marker.exists()


def run_acceptance(output_dir: str | Path) -> dict[str, object]:
    """Run the local acceptance smoke and write a metadata-only JSON report."""

    started = time.perf_counter()
    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)
    ffmpeg = shutil.which("ffmpeg")
    report: dict[str, object] = {
        "schema": "V3_P3_LOCAL_ACCEPTANCE_V1",
        "status": "FAIL",
        "blind_detection": "FAIL",
        "negative_unknown": "FAIL",
        "wrong_key": "FAIL",
        "invalid_input": "FAIL",
        "size_duration_guards": "FAIL",
        "session_cleanup": "FAIL",
        "cli_fallback": "FAIL",
        "mp3_roundtrip": "NOT_AVAILABLE" if ffmpeg is None else "FAIL",
        "ffmpeg_available": bool(ffmpeg),
        "ffmpeg_path": ffmpeg,
        "render_feasibility": "LOCAL_PROXY_ONLY",
        "formal_perceptual_gate": "NOT_ESTABLISHED",
        "artifact_policy": "METADATA_ONLY; generated audio stays in TemporaryDirectory",
        "v3_protocol": {
            "messages": list(MESSAGES),
            "sample_rate_hz": 48_000,
            "duration_seconds": 6,
            "effective_payload_bits": 8,
            "physical_payload_bits": 32,
            "selector": "REAL_TOP32",
            "watermark_seed": 7,
            "strength": 1.60,
            "presence_threshold": 0.7855073980199624,
        },
        "message_results": [],
    }

    with tempfile.TemporaryDirectory(prefix="v3_p3_acceptance_") as temporary:
        work = Path(temporary)
        clean_path = _make_fixture(work / "clean.wav")
        from app.audio_io import AudioData, MAX_INPUT_BYTES, decode_audio_file
        from app.v3_api import detect_message, embed_message
        from app.v3_pipeline import detect_uploaded_file, run_v3_demo

        clean_audio = decode_audio_file(clean_path)
        message_results: list[dict[str, object]] = []
        all_identity_passed = True
        for message in MESSAGES:
            message_started = time.perf_counter()
            run = run_v3_demo(
                clean_path,
                message,
                codec="identity",
                output_dir=work / f"identity_{message}",
            )
            passed = run.detection.status == "IDENTIFIED" and run.detection.message == message
            all_identity_passed = all_identity_passed and passed
            message_results.append(
                {
                    "message": message,
                    "status": run.detection.status,
                    "detected_message": run.detection.message,
                    "passed": passed,
                    "elapsed_seconds": round(time.perf_counter() - message_started, 6),
                }
            )
        report["message_results"] = message_results
        report["blind_detection"] = "PASS" if all_identity_passed else "FAIL"

        clean_result = detect_uploaded_file(clean_path)
        report["negative_unknown"] = (
            "PASS"
            if clean_result.status == "UNKNOWN" and clean_result.message is None
            else "FAIL"
        )

        wrong_key = _wrong_key_probe(clean_audio, 173)
        report["wrong_key_result"] = wrong_key
        report["wrong_key"] = (
            "PASS" if not wrong_key["accepted_as_expected_message"] else "FAIL"
        )

        invalid_path = work / "invalid.wav"
        invalid_path.write_bytes(b"not an audio file")
        try:
            detect_uploaded_file(invalid_path)
        except Exception as error:  # Expected rejection at the input boundary.
            report["invalid_input"] = "PASS"
            report["invalid_input_error"] = type(error).__name__
        else:
            report["invalid_input"] = "FAIL"

        oversized = work / "oversized.bin"
        with oversized.open("wb") as stream:
            stream.truncate(MAX_INPUT_BYTES + 1)
        guard_results: dict[str, object] = {}
        try:
            detect_uploaded_file(oversized)
        except ValueError as error:
            guard_results["size"] = "PASS"
            guard_results["size_error"] = str(error)
        else:
            guard_results["size"] = "FAIL"
        try:
            embed_message(AudioData(np.zeros(31 * 48_000), 48_000), 0)
        except ValueError as error:
            guard_results["duration"] = "PASS"
            guard_results["duration_error"] = str(error)
        else:
            guard_results["duration"] = "FAIL"
        report["size_duration_guard_results"] = guard_results
        report["size_duration_guards"] = (
            "PASS"
            if guard_results.get("size") == "PASS"
            and guard_results.get("duration") == "PASS"
            else "FAIL"
        )

        report["session_cleanup"] = (
            "PASS" if _session_cleanup_probe(work / "sessions") else "FAIL"
        )

        cli_passed, cli_detail = _run_cli(clean_path, work / "cli_run")
        report["cli_fallback"] = "PASS" if cli_passed else "FAIL"
        report["cli_fallback_detail"] = cli_detail

        if ffmpeg is not None:
            mp3_run = run_v3_demo(
                clean_path,
                173,
                codec="mp3",
                output_dir=work / "mp3_run",
            )
            mp3_passed = (
                mp3_run.detection.status == "IDENTIFIED"
                and mp3_run.detection.message == 173
                and mp3_run.compressed_mp3 is not None
                and mp3_run.compressed_wav is not None
            )
            report["mp3_roundtrip"] = "PASS" if mp3_passed else "FAIL"
            report["mp3_result"] = {
                "status": mp3_run.detection.status,
                "detected_message": mp3_run.detection.message,
                "bitrate": "128k",
                "codec": "libmp3lame",
                "passed": mp3_passed,
            }

    elapsed = time.perf_counter() - started
    report["elapsed_seconds"] = round(elapsed, 6)
    report["peak_rss_mb"] = _peak_rss_mb()
    required_pass = all(
        report[key] == "PASS"
        for key in (
            "blind_detection",
            "negative_unknown",
            "wrong_key",
            "invalid_input",
            "size_duration_guards",
            "session_cleanup",
            "cli_fallback",
        )
    )
    mp3_acceptable = report["mp3_roundtrip"] in ("PASS", "NOT_AVAILABLE")
    report["status"] = "PASS" if required_pass and mp3_acceptable else "FAIL"
    report_path = destination / REPORT_NAME
    report_path.write_text(
        json.dumps(_jsonable(report), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    report["report_path"] = str(report_path)
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the local V3 P3 acceptance smoke")
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        report = run_acceptance(args.output_dir)
    except Exception as error:
        print(json.dumps({"status": "FAIL", "error": str(error)}, ensure_ascii=False))
        return 2
    print(json.dumps(_jsonable(report), indent=2, sort_keys=True, ensure_ascii=False))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
