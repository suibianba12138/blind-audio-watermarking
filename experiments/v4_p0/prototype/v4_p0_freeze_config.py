"""Record the bounded V4-P0 candidate configuration and source hashes."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run(output: Path) -> dict[str, object]:
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()
    files = {
        "src/audio_watermark/v4_tf.py": ROOT / "src/audio_watermark/v4_tf.py",
        "src/audio_watermark/evaluation.py": ROOT / "src/audio_watermark/evaluation.py",
        "scripts/v4_p0_development_experiment.py": ROOT / "scripts/v4_p0_development_experiment.py",
        "docs/V4_P0_ALGORITHM_DESIGN.md": ROOT / "docs/V4_P0_ALGORITHM_DESIGN.md",
    }
    result = {
        "status": "FROZEN_FOR_P0_DEVELOPMENT_ONLY",
        "branch": subprocess.run(["git", "branch", "--show-current"], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip(),
        "head_at_generation": head,
        "candidate": "V4-TF-SS",
        "payload_bits_tested": [8, 16],
        "strength_candidates": [0.04, 0.08],
        "sample_rate_hz": 48000,
        "n_fft": 2048,
        "hop_length": 512,
        "window": "hann",
        "center_padding": "reflect n_fft//2 on both sides",
        "carrier_band_hz": [1500.0, 12000.0],
        "bins_per_frame": 96,
        "seed": 20261025,
        "detector_contract": {
            "blind_inputs": ["received_audio", "V4TFConfig", "public seed"],
            "forbidden_inputs": ["expected message", "clean audio", "ground truth", "filename labels", "embedding search records"],
            "presence_score": "mean(abs(per-bit signed correlation))",
            "threshold_status": "initial development value 0.02; not independently calibrated",
        },
        "parameter_selection_policy": "bounded development observation only; no independent test selection",
        "source_sha256": {name: _sha256(path) for name, path in files.items()},
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(run(args.output), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
