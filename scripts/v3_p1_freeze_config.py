"""Write the immutable V3-P1 operating-point and source hash record."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _ffmpeg_version() -> str:
    result = subprocess.run(
        ["ffmpeg", "-version"], capture_output=True, text=True, check=False
    )
    return result.stdout.splitlines()[0] if result.stdout else "NOT_AVAILABLE"


def build_freeze_record(manifest_path: Path) -> dict[str, object]:
    from app.public_config import load_public_selector, public_provenance
    from audio_watermark.b1_soft import soft_codebook

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("status") != "FROZEN":
        raise ValueError("P1 configuration requires a FROZEN manifest")
    source_files = {
        "src/audio_watermark/b1_soft.py": ROOT / "src/audio_watermark/b1_soft.py",
        "src/audio_watermark/b1_hard_code.py": ROOT / "src/audio_watermark/b1_hard_code.py",
        "src/audio_watermark/b1.py": ROOT / "src/audio_watermark/b1.py",
        "src/audio_watermark/embed.py": ROOT / "src/audio_watermark/embed.py",
        "src/audio_watermark/detect.py": ROOT / "src/audio_watermark/detect.py",
        "src/audio_watermark/course_v2.py": ROOT / "src/audio_watermark/course_v2.py",
        "configs/real_top32_stability_map.json": ROOT / "configs/real_top32_stability_map.json",
    }
    if any(not path.is_file() for path in source_files.values()):
        raise FileNotFoundError("P1 freeze source file is missing")
    selector = load_public_selector()
    provenance = public_provenance()
    return {
        "stage": "V3_P1_INDEPENDENT_VALIDATION",
        "branch_base": "research/v3-p0@34411a9660c1b8b0bfaf3f6e72b62e18984d8145",
        "strength": 1.60,
        "repeat4_threshold": 0.47678591988959035,
        "hard_code_threshold": 0.47678591988959035,
        "soft_code_threshold": 0.7855073980199624,
        "selector": {
            **provenance,
            "selected_group_ids_sha256": hashlib.sha256(
                json.dumps(selector.selected_group_ids, separators=(",", ":")).encode()
            ).hexdigest(),
        },
        "message_seeds": [101, 202],
        "sample_rate_hz": 48_000,
        "duration_seconds": 6.0,
        "physical_payload_bits": 32,
        "effective_payload_bits": 8,
        "mp3": {"codec": "libmp3lame", "bitrate": "128k", "tool": _ffmpeg_version()},
        "manifest": str(manifest_path),
        "manifest_sha256": _sha256(manifest_path),
        "source_sha256": {key: _sha256(path) for key, path in source_files.items()},
        "soft_codebook_sha256": hashlib.sha256(soft_codebook().tobytes()).hexdigest(),
        "numpy_version": np.__version__,
        "python": sys.version,
        "threshold_provenance": "frozen from V3_B1_SOFT_CODE_PILOT_SUMMARY.json; no P1 refit",
        "detector_contract": "received audio + public/keyed config only; expected payload post-hoc scoring only",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    record = build_freeze_record(args.manifest)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(record, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
