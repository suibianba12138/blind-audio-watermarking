"""Record local feasibility checks for external watermarking baselines.

This script does not clone or import third-party source.  It is intentionally
conservative: a missing local dependency is recorded as unavailable rather
than repaired by changing the public project's environment.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import platform
import shutil
import subprocess
import sys
from pathlib import Path


PROJECTS = {
    "audiowmark": {
        "repository": "https://github.com/swesterfeld/audiowmark",
        "license": "GPL-3-or-later",
        "message_bits": 128,
        "notes": "standalone CLI; 1024-sample frames; reports long-block operation",
    },
    "wavmark": {
        "repository": "https://github.com/wavmark/wavmark",
        "license": "MIT (repository metadata; verify model artifact separately)",
        "message_bits": "32 model / 16 identification+16 custom in README usage",
        "notes": "single-channel 16 kHz; 1-second example; PyTorch model",
    },
    "silentcipher": {
        "repository": "https://github.com/sony/silentcipher",
        "license": "MIT",
        "message_bits": 40,
        "notes": "five 8-bit characters; official 16 kHz and 44.1 kHz models",
    },
    "audioseal": {
        "repository": "https://github.com/facebookresearch/audioseal",
        "license": "MIT (code and weights stated by official README)",
        "message_bits": 16,
        "notes": "localized detector; default models target 16/24 kHz, 48 kHz mainly speech",
    },
    "craw": {
        "repository": "https://github.com/DavidC1212/craw",
        "license": "REVIEW_REQUIRED",
        "message_bits": "binary message; exact public protocol not independently verified",
        "notes": "Python 3.8; bundled checkpoint described by README; attack dependencies separate",
    },
    "omnisealbench": {
        "repository": "https://github.com/facebookresearch/omnisealbench",
        "license": "MIT common code; model licenses vary",
        "message_bits": "model-dependent",
        "notes": "benchmark harness; checkpoints and PyTorch environment required",
    },
}


def _git_probe(url: str) -> dict[str, object]:
    try:
        result = subprocess.run(
            ["git", "ls-remote", "--heads", url],
            check=False,
            capture_output=True,
            text=True,
            timeout=15,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        return {"status": "UNAVAILABLE", "detail": type(error).__name__}
    if result.returncode == 0:
        return {"status": "REACHABLE", "detail": result.stdout.splitlines()[:3]}
    return {
        "status": "UNAVAILABLE",
        "detail": (result.stderr or result.stdout).strip()[:300],
    }


def run() -> dict[str, object]:
    modules = {
        name: bool(importlib.util.find_spec(name))
        for name in ("torch", "torchaudio", "soundfile", "librosa", "wavmark", "silentcipher", "audioseal", "omnisealbench")
    }
    projects: dict[str, object] = {}
    for name, metadata in PROJECTS.items():
        projects[name] = {
            **metadata,
            "git_probe": _git_probe(metadata["repository"] + ".git"),
        }
    return {
        "runtime": {
            "python": sys.version,
            "platform": platform.platform(),
            "ffmpeg": shutil.which("ffmpeg"),
            "audiowmark_cli": shutil.which("audiowmark"),
            "modules": modules,
        },
        "projects": projects,
        "policy": "review only; no external source or model was copied into this repository",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = run()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
