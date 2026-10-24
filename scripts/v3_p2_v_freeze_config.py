"""Write the pre-registered V3-P2-V operating-point freeze record."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
HEAD = "63d3166b1eeb2f0f7e99c8a9ad181934b824370e"
STRENGTH = 1.60
THRESHOLDS = {"soft8_frozen": 0.7855073980199624, "soft12_frozen": 0.903827529676706}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _run(*args: str) -> str:
    result = subprocess.run(args, cwd=ROOT, capture_output=True, text=True, check=False)
    return result.stdout.strip()


def build_freeze(manifest_path: Path) -> dict[str, object]:
    from app.public_config import load_public_selector, public_provenance
    from audio_watermark.b1_soft import soft_codebook
    from audio_watermark.b2_capacity import capacity_codebook

    manifest_path = manifest_path.resolve()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("status") != "FROZEN" or manifest.get("manifest_version") != "V3_P2_V_INDEPENDENT_VALIDATION_V1":
        raise ValueError("V3-P2-V requires its frozen 60-source manifest")
    records = list(manifest["records"])
    if len(records) != 60:
        raise ValueError("V3-P2-V requires exactly 60 source records")
    source_files = {
        "src/audio_watermark/b1.py": ROOT / "src/audio_watermark/b1.py",
        "src/audio_watermark/b1_soft.py": ROOT / "src/audio_watermark/b1_soft.py",
        "src/audio_watermark/b2_capacity.py": ROOT / "src/audio_watermark/b2_capacity.py",
        "src/audio_watermark/course_v2.py": ROOT / "src/audio_watermark/course_v2.py",
        "src/audio_watermark/detect.py": ROOT / "src/audio_watermark/detect.py",
        "src/audio_watermark/embed.py": ROOT / "src/audio_watermark/embed.py",
        "src/audio_watermark/v3_p2.py": ROOT / "src/audio_watermark/v3_p2.py",
        "app/public_config.py": ROOT / "app/public_config.py",
        "configs/real_top32_stability_map.json": ROOT / "configs/real_top32_stability_map.json",
        "configs/v3_p1_independent_manifest.json": ROOT / "configs/v3_p1_independent_manifest.json",
        "experiments/v3_p1/CONFIG_FREEZE.json": ROOT / "experiments/v3_p1/CONFIG_FREEZE.json",
        "experiments/v3_p2/CONFIG_FREEZE.json": ROOT / "experiments/v3_p2/CONFIG_FREEZE.json",
        "scripts/v3_p2_v_freeze_manifest.py": ROOT / "scripts/v3_p2_v_freeze_manifest.py",
    }
    if any(not path.is_file() for path in source_files.values()):
        raise FileNotFoundError("a frozen source/config file is missing")
    selector = load_public_selector()
    codebook8 = soft_codebook()
    codebook12 = capacity_codebook(12)
    return {
        "stage": "V3_P2_V_INDEPENDENT_VALIDATION",
        "base": f"research/v3-p2@{HEAD}",
        "branch": _run("git", "branch", "--show-current"),
        "head_before_validation": _run("git", "rev-parse", "HEAD"),
        "validation_status": "FROZEN_BEFORE_RESULTS",
        "strength": STRENGTH,
        "thresholds": THRESHOLDS,
        "threshold_provenance": {
            "soft8_frozen": "V3-P1 CONFIG_FREEZE.json; no V3-P2-V refit",
            "soft12_frozen": "V3-P2 development calibration; no V3-P2-V refit",
        },
        "selector": {
            **public_provenance(),
            "selected_group_ids_sha256": hashlib.sha256(
                json.dumps(selector.selected_group_ids, separators=(",", ":")).encode("utf-8")
            ).hexdigest(),
        },
        "messages": {
            "seeds": [101, 202],
            "messages_per_source": 2,
            "generator": "src/audio_watermark/v3_p2.py:message_for_seed",
            "expected_payloads_scoring_only": True,
        },
        "signal_protocol": {
            "sample_rate_hz": 48000,
            "duration_seconds": 6.0,
            "physical_payload_bits": 32,
            "methods": {"soft8_frozen": 8, "soft12_frozen": 12},
            "carrier_map": "REAL_TOP32",
            "watermark_seed": 7,
            "n_fft": 2048,
            "hop_length": 2048,
            "frames_per_bit": 4,
        },
        "mp3": {
            "codec": "libmp3lame",
            "bitrate": "128k",
            "tool": _run("ffmpeg", "-version").splitlines()[0] if _run("ffmpeg", "-version") else "NOT_AVAILABLE",
        },
        "negative_controls": [
            "clean_no_watermark",
            "clean_mp3_no_watermark",
            "wrong_key_mp3_positive",
            "wrong_message_acceptance_scored_after_detection",
        ],
        "detector_contract": {
            "blind_inputs": ["received_audio", "public_config", "pre_shared_selector_seed"],
            "forbidden_inputs": ["expected_payload", "clean_audio", "ground_truth", "filename_labels"],
            "expected_payload_role": "post_detection_scoring_only",
        },
        "manifest": {
            "path": str(manifest_path),
            "sha256": _sha256(manifest_path),
            "source_count": len(records),
            "category_counts": {
                category: sum(record["category"] == category for record in records)
                for category in ("speech", "music", "environment")
            },
        },
        "codebook_sha256": {
            "soft8_frozen": hashlib.sha256(np.asarray(codebook8).tobytes()).hexdigest(),
            "soft12_frozen": hashlib.sha256(np.asarray(codebook12).tobytes()).hexdigest(),
        },
        "source_sha256": {key: _sha256(path) for key, path in source_files.items()},
        "no_parameter_selection_on_validation": True,
        "no_audio_copied_to_repository": True,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    record = build_freeze(args.manifest)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(record, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
