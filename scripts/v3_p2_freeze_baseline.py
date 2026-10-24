"""Freeze the V3-P1 eight-bit operating point for the bounded P2 design pilot."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
P1_HEAD = "82f80138654b283e05da4d41bea71144a20f1120"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _run(*args: str) -> str:
    result = subprocess.run(args, cwd=ROOT, capture_output=True, text=True, check=False)
    return result.stdout.strip()


def _ffmpeg_version() -> str:
    return _run("ffmpeg", "-version").splitlines()[0] if _run("ffmpeg", "-version") else "NOT_AVAILABLE"


def build_freeze_record(manifest_path: Path) -> dict[str, object]:
    from app.public_config import load_public_selector, public_provenance
    from audio_watermark.b1_soft import soft_codebook

    manifest_path = manifest_path.resolve()
    if not manifest_path.is_file():
        raise FileNotFoundError(manifest_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("status") not in (None, "FROZEN"):
        raise ValueError("P1 manifest is not frozen-compatible")
    source_files = {
        "src/audio_watermark/b1_soft.py": ROOT / "src/audio_watermark/b1_soft.py",
        "src/audio_watermark/b1_hard_code.py": ROOT / "src/audio_watermark/b1_hard_code.py",
        "src/audio_watermark/b1.py": ROOT / "src/audio_watermark/b1.py",
        "src/audio_watermark/embed.py": ROOT / "src/audio_watermark/embed.py",
        "src/audio_watermark/detect.py": ROOT / "src/audio_watermark/detect.py",
        "src/audio_watermark/course_v2.py": ROOT / "src/audio_watermark/course_v2.py",
        "app/public_config.py": ROOT / "app/public_config.py",
        "configs/real_top32_stability_map.json": ROOT / "configs/real_top32_stability_map.json",
        "configs/v3_p1_independent_manifest.json": ROOT / "configs/v3_p1_independent_manifest.json",
        "experiments/v3_p1/CONFIG_FREEZE.json": ROOT / "experiments/v3_p1/CONFIG_FREEZE.json",
    }
    if any(not path.is_file() for path in source_files.values()):
        raise FileNotFoundError("a P2 freeze source file is missing")
    selector = load_public_selector()
    provenance = public_provenance()
    codebook = soft_codebook()
    min_distance = int(
        np.min(
            [
                np.count_nonzero(codebook[i] != codebook[j])
                for i in range(codebook.shape[0])
                for j in range(i + 1, codebook.shape[0])
            ]
        )
    )
    return {
        "stage": "V3_P2_CAPACITY_DESIGN",
        "base": f"research/v3-p1@{P1_HEAD}",
        "branch": _run("git", "branch", "--show-current"),
        "head": _run("git", "rev-parse", "HEAD"),
        "strength": 1.60,
        "soft_code_threshold": 0.7855073980199624,
        "physical_threshold": 0.47678591988959035,
        "selector": {
            **provenance,
            "selected_group_ids_sha256": hashlib.sha256(
                json.dumps(selector.selected_group_ids, separators=(",", ":")).encode("utf-8")
            ).hexdigest(),
        },
        "message_seeds": [101, 202],
        "sample_rate_hz": 48_000,
        "duration_seconds": 6.0,
        "physical_payload_bits": 32,
        "effective_payload_bits": 8,
        "code_family": "fixed_boolean_evaluation_subcode",
        "codebook_shape": list(codebook.shape),
        "codebook_minimum_hamming_distance": min_distance,
        "mp3": {"codec": "libmp3lame", "bitrate": "128k", "tool": _ffmpeg_version()},
        "manifest": str(manifest_path),
        "manifest_sha256": _sha256(manifest_path),
        "source_sha256": {key: _sha256(path) for key, path in source_files.items()},
        "soft_codebook_sha256": hashlib.sha256(codebook.tobytes()).hexdigest(),
        "numpy_version": np.__version__,
        "python": sys.version,
        "threshold_provenance": "frozen from V3_P1 CONFIG_FREEZE.json; no P2 formal-test refit",
        "detector_contract_scoring_only": {
            "blind_inputs": ["received_audio", "public_config", "pre_shared_selector_seed"],
            "expected_payload": "scoring_only_after_detection",
            "clean_audio": "not_an_input",
            "ground_truth": "not_an_input",
            "filename_labels": "not_an_input",
        },
        "calibration_policy": {
            "development_split": "dev",
            "calibration_role": "first_five_sources_per_category",
            "pilot_role": "last_five_sources_per_category",
            "formal_test_used_for_selection": False,
            "future_validation_status": "NOT_ESTABLISHED",
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=ROOT / "configs/v3_p1_independent_manifest.json")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    record = build_freeze_record(args.manifest)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(record, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
