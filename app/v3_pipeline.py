"""Local V3 embed, MP3, and independent blind-detection pipeline."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from .audio_io import (
    MAX_INPUT_BYTES,
    AudioData,
    decode_audio_file,
    prepare_for_demo,
    write_wav,
)
from .mp3_codec import encode_decode_mp3
from .v3_session_store import SessionHandle, SessionStore
from .v3_api import VALID_STATUSES, V3DetectionResult, embed_message


_RELEASE_ROOT = Path(__file__).resolve().parents[1]
_DETECT_TIMEOUT_SECONDS = 180


@dataclass(frozen=True)
class V3DemoRun:
    """Successful V3 demo artifacts and the blind detector result."""

    output_dir: Path
    original_wav: Path
    marked_wav: Path
    compressed_mp3: Path | None
    compressed_wav: Path | None
    received_path: Path
    detection: V3DetectionResult
    message: int
    codec: str
    duration_seconds: float


def _result_from_payload(payload: Mapping[str, object]) -> V3DetectionResult:
    if payload.get("status") == "ERROR":
        raise RuntimeError(str(payload.get("error", "blind detector failed")))
    required = {
        "status",
        "message",
        "presence_score",
        "threshold",
        "margin",
        "duration_seconds",
        "sample_rate",
        "provenance",
    }
    missing = required.difference(payload)
    if missing:
        raise RuntimeError("blind detector response missing: " + ", ".join(sorted(missing)))
    status = str(payload["status"])
    if status not in VALID_STATUSES:
        raise RuntimeError(f"invalid detector status: {status}")
    return V3DetectionResult(
        status=status,
        message=None if payload["message"] is None else int(payload["message"]),
        presence_score=float(payload["presence_score"]),
        threshold=float(payload["threshold"]),
        margin=float(payload["margin"]),
        duration_seconds=float(payload["duration_seconds"]),
        sample_rate=int(payload["sample_rate"]),
        provenance=dict(payload["provenance"]),
    )


def _detect_in_subprocess(received_path: Path) -> V3DetectionResult:
    """Invoke the detector in a clean process with only a received path."""

    environment = os.environ.copy()
    environment["PYTHONPATH"] = os.pathsep.join(
        (str(_RELEASE_ROOT / "src"), str(_RELEASE_ROOT))
    )
    command = [
        sys.executable,
        "-m",
        "app.v3_detector_worker",
        "--input",
        str(received_path),
        "--json",
    ]
    try:
        completed = subprocess.run(
            command,
            cwd=_RELEASE_ROOT,
            env=environment,
            check=True,
            shell=False,
            capture_output=True,
            text=True,
            timeout=_DETECT_TIMEOUT_SECONDS,
        )
    except subprocess.CalledProcessError as error:
        detail = (error.stderr or error.stdout or "").strip()[-500:]
        raise RuntimeError(f"blind V3 detector subprocess failed: {detail}") from error
    except subprocess.TimeoutExpired as error:
        raise RuntimeError("blind V3 detector subprocess timed out") from error
    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError as error:
        raise RuntimeError("blind V3 detector returned invalid JSON") from error
    return _result_from_payload(payload)


def _new_session() -> tuple[tempfile.TemporaryDirectory[str], SessionHandle]:
    temporary_root = tempfile.TemporaryDirectory(prefix="blind_audio_v3_pipeline_")
    store = SessionStore(Path(temporary_root.name))
    return temporary_root, store.create()


def _cleanup_session(
    temporary_root: tempfile.TemporaryDirectory[str], session: SessionHandle
) -> None:
    try:
        session.cleanup()
    finally:
        temporary_root.cleanup()


def _create_output_dir(output_dir: str | Path | None) -> Path:
    """Create an exclusive artifact directory, refusing reuse or symlinks."""

    if output_dir is None:
        return Path(tempfile.mkdtemp(prefix="blind_audio_v3_demo_"))
    destination = Path(output_dir)
    if destination.is_symlink() or destination.exists():
        raise FileExistsError(
            f"output_dir must not already exist or be a symlink: {destination}"
        )
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.mkdir()
    return destination


def _assert_artifacts_absent(destination: Path, names: tuple[str, ...]) -> None:
    for name in names:
        path = destination / name
        if path.exists() or path.is_symlink():
            raise FileExistsError(f"output artifact already exists: {path}")


def _validate_upload_source(input_path: str | Path) -> Path:
    source = Path(input_path)
    if not source.is_file():
        raise FileNotFoundError(f"audio file not found: {source}")
    if source.stat().st_size > MAX_INPUT_BYTES:
        raise ValueError("audio file exceeds the 16 MiB public-demo limit")
    return source


def run_v3_demo(
    input_path: str | Path,
    message: int,
    codec: str = "identity",
    output_dir: str | Path | None = None,
) -> V3DemoRun:
    """Embed a message, optionally round-trip MP3, then detect blindly."""

    if codec not in ("identity", "mp3"):
        raise ValueError("codec must be identity or mp3")
    temporary_root, session = _new_session()
    destination: Path | None = None
    try:
        destination = _create_output_dir(output_dir)
        artifact_names = (
            "original_prepared.wav",
            "watermarked.wav",
            "compressed_128k.mp3",
            "compressed_128k_decoded.wav",
        )
        _assert_artifacts_absent(destination, artifact_names)
        decoded = decode_audio_file(input_path)
        prepared = prepare_for_demo(decoded, duration_seconds=6)
        embedded = embed_message(prepared, message)
        original_wav = write_wav(session.path("original_prepared.wav"), prepared)
        marked_wav = write_wav(destination / "watermarked.wav", embedded.audio)
        public_original = destination / "original_prepared.wav"
        shutil.copyfile(original_wav, public_original)

        compressed_mp3 = compressed_wav = None
        received_path = marked_wav
        if codec == "mp3":
            compressed_mp3, compressed_wav, _decoded = encode_decode_mp3(
                embedded.audio,
                destination,
            )
            received_path = compressed_wav

        detection = _detect_in_subprocess(received_path)
        return V3DemoRun(
            output_dir=destination,
            original_wav=public_original,
            marked_wav=marked_wav,
            compressed_mp3=compressed_mp3,
            compressed_wav=compressed_wav,
            received_path=received_path,
            detection=detection,
            message=embedded.message,
            codec=codec,
            duration_seconds=embedded.duration_seconds,
        )
    except Exception:
        if destination is not None:
            shutil.rmtree(destination, ignore_errors=True)
        raise
    finally:
        _cleanup_session(temporary_root, session)


def detect_uploaded_file(input_path: str | Path) -> V3DetectionResult:
    """Blindly detect one independently staged uploaded file.

    The temporary staging session contains only a copy of the received file.
    It has no embedding state and is removed on both success and failure.
    """

    source = _validate_upload_source(input_path)
    temporary_root, session = _new_session()
    try:
        staged = session.path("received" + source.suffix.lower())
        shutil.copyfile(source, staged)
        return _detect_in_subprocess(staged)
    finally:
        _cleanup_session(temporary_root, session)
