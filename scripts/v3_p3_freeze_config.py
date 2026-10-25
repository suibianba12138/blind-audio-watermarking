"""Generate the immutable V3 8-bit candidate freeze record.

This script records the already validated V3-P2-V operating point.  It does
not select parameters and it does not modify any watermark implementation.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
BASE_COMMIT = "2c6f53cddf7ba67ffcabe9f3f3744f6279a71cdc"
STRENGTH = 1.60
PRESENCE_THRESHOLD = 0.7855073980199624


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _run(*args: str) -> str:
    result = subprocess.run(
        args,
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    return result.stdout.strip()


def _require_base_ancestor() -> None:
    result = subprocess.run(
        ["git", "merge-base", "--is-ancestor", BASE_COMMIT, "HEAD"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(
            "current HEAD does not descend from the approved V3-P2-V base "
            f"{BASE_COMMIT}"
        )


def _source_files() -> dict[str, Path]:
    return {
        "src/audio_watermark/b1.py": ROOT / "src/audio_watermark/b1.py",
        "src/audio_watermark/b1_soft.py": ROOT / "src/audio_watermark/b1_soft.py",
        "src/audio_watermark/b2_capacity.py": ROOT / "src/audio_watermark/b2_capacity.py",
        "src/audio_watermark/embed.py": ROOT / "src/audio_watermark/embed.py",
        "src/audio_watermark/detect.py": ROOT / "src/audio_watermark/detect.py",
        "src/audio_watermark/v3_p2.py": ROOT / "src/audio_watermark/v3_p2.py",
        "app/public_config.py": ROOT / "app/public_config.py",
        "configs/real_top32_stability_map.json": ROOT / "configs/real_top32_stability_map.json",
        "experiments/v3_p1/CONFIG_FREEZE.json": ROOT / "experiments/v3_p1/CONFIG_FREEZE.json",
        "experiments/v3_p2/CONFIG_FREEZE.json": ROOT / "experiments/v3_p2/CONFIG_FREEZE.json",
        "experiments/v3_p2_v/CONFIG_FREEZE.json": ROOT / "experiments/v3_p2_v/CONFIG_FREEZE.json",
        "V3_P2_V_INDEPENDENT_VALIDATION.md": ROOT / "V3_P2_V_INDEPENDENT_VALIDATION.md",
        "V3_P2_V_DETECTION_REPORT.md": ROOT / "V3_P2_V_DETECTION_REPORT.md",
        "V3_P2_V_DECISION.md": ROOT / "V3_P2_V_DECISION.md",
        "V3_P2_V_PAIRED_RESULTS.csv": ROOT / "V3_P2_V_PAIRED_RESULTS.csv",
    }


def build_freeze_record() -> dict[str, object]:
    """Return a hash-complete record of the frozen V3 8-bit candidate."""

    _require_base_ancestor()
    from app.public_config import load_public_selector, public_provenance
    from audio_watermark.b1_soft import soft_codebook

    source_files = _source_files()
    missing = [name for name, path in source_files.items() if not path.is_file()]
    if missing:
        raise FileNotFoundError("missing freeze inputs: " + ", ".join(missing))

    selector = load_public_selector()
    codebook = np.asarray(soft_codebook())
    selector_provenance = public_provenance()
    return {
        "stage": "V3_P3_V3_8BIT_CANDIDATE",
        "base": f"research/v3-p2-validation@{BASE_COMMIT}",
        "branch_at_generation": _run("git", "branch", "--show-current"),
        "head_at_generation": _run("git", "rev-parse", "HEAD"),
        "validation_basis": "V3-P2-V independent validation; no P3 parameter selection",
        "strength": STRENGTH,
        "presence_threshold": PRESENCE_THRESHOLD,
        "threshold_provenance": "V3-P1 freeze record; not refit on P2-V",
        "protocol": {
            "sample_rate_hz": 48000,
            "duration_seconds": 6,
            "physical_payload_bits": 32,
            "effective_payload_bits": 8,
            "selector": "REAL_TOP32",
            "watermark_seed": 7,
            "n_fft": 2048,
            "hop_length": 2048,
            "frames_per_bit": 4,
        },
        "mp3": {"codec": "libmp3lame", "bitrate": "128k"},
        "selector": {
            **selector_provenance,
            "selected_group_ids_sha256": hashlib.sha256(
                json.dumps(
                    selector.selected_group_ids,
                    separators=(",", ":"),
                ).encode("utf-8")
            ).hexdigest(),
        },
        "soft_codebook_sha256": hashlib.sha256(codebook.tobytes()).hexdigest(),
        "source_sha256": {
            name: _sha256(path) for name, path in source_files.items()
        },
        "detector_contract": {
            "blind_inputs": [
                "received_audio",
                "public_config",
                "pre_shared_selector_seed",
            ],
            "expected_payload_role": "post_detection_scoring_only",
            "forbidden_inputs": [
                "expected_payload",
                "clean_audio",
                "ground_truth",
                "filename_labels",
            ],
        },
        "parameter_selection_on_p2v": False,
        "historical_artifacts_unchanged": True,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    record = build_freeze_record()
    output = args.output if args.output.is_absolute() else ROOT / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(record, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(record, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
