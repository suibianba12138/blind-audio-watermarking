"""End-to-end public demo pipeline with an independent detector subprocess."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

from audio_watermark.course_v2 import embed_identity_multiblock

from .audio_io import decode_audio_file, prepare_for_demo, write_wav
from .mp3_codec import encode_decode_mp3
from .public_config import BLOCK_SECONDS, build_embedding_config, load_public_selector, public_provenance


_RELEASE_ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class DemoRun:
    output_dir: Path
    original_wav: Path
    marked_wav: Path
    compressed_mp3: Path | None
    compressed_wav: Path | None
    received_path: Path
    detection: dict[str, object]
    block_count: int
    duration_seconds: float


def _detect_in_subprocess(received_path: Path) -> dict[str, object]:
    environment = os.environ.copy()
    environment.pop("PYTHONPATH", None)
    # Resolve only against this release tree, never against the research
    # worktree that produced the export.
    environment["PYTHONPATH"] = os.pathsep.join(
        (str(_RELEASE_ROOT / "src"), str(_RELEASE_ROOT))
    )
    command = [
        sys.executable,
        "-m",
        "app.detector_worker",
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
            timeout=180,
        )
    except subprocess.CalledProcessError as error:
        detail = (error.stderr or error.stdout or "").strip()[-500:]
        raise RuntimeError(f"blind detector subprocess failed: {detail}") from error
    result = json.loads(completed.stdout)
    if result.get("status") == "ERROR":
        raise RuntimeError(str(result.get("error", "detector failed")))
    return result


def run_demo(
    input_path: str | Path,
    identity: str,
    *,
    duration_seconds: int = 6,
    codec: str = "identity",
    output_dir: str | Path | None = None,
) -> DemoRun:
    """Embed one identity, optionally run real MP3, then invoke blind detection."""

    if codec not in ("identity", "mp3"):
        raise ValueError("codec must be identity or mp3")
    destination = Path(output_dir) if output_dir is not None else Path(
        tempfile.mkdtemp(prefix="blind_watermark_demo_")
    )
    destination.mkdir(parents=True, exist_ok=True)
    selector = load_public_selector()
    config = build_embedding_config()
    source = prepare_for_demo(decode_audio_file(input_path), duration_seconds=duration_seconds)
    marked = embed_identity_multiblock(
        source.samples,
        identity,
        config,
        selector,
        block_seconds=BLOCK_SECONDS,
    )
    original_wav = write_wav(destination / "original_prepared.wav", source)
    marked_wav = write_wav(destination / "watermarked.wav", marked.audio, source.sample_rate)
    compressed_mp3 = compressed_wav = None
    received_path = marked_wav
    if codec == "mp3":
        compressed_mp3, compressed_wav, _ = encode_decode_mp3(
            type(source)(marked.audio, source.sample_rate), destination
        )
        received_path = compressed_wav
    detection = _detect_in_subprocess(received_path)
    detection["codec_path"] = codec
    detection["provenance"] = public_provenance()
    return DemoRun(
        output_dir=destination,
        original_wav=original_wav,
        marked_wav=marked_wav,
        compressed_mp3=compressed_mp3,
        compressed_wav=compressed_wav,
        received_path=received_path,
        detection=detection,
        block_count=len(marked.blocks),
        duration_seconds=source.samples.size / source.sample_rate,
    )
