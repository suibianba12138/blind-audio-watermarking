"""Record local WavMark CPU prerequisites without downloading or installing anything."""

from __future__ import annotations

import argparse
import importlib.util
import json
import platform
import shutil
import sys
from pathlib import Path


def _module_status(name: str) -> str:
    return "AVAILABLE" if importlib.util.find_spec(name) is not None else "NOT_INSTALLED"


def build_audit() -> dict[str, object]:
    usage = shutil.disk_usage(Path.cwd())
    return {
        "status": "BLOCKED" if _module_status("torch") != "AVAILABLE" else "REQUIRES_WEIGHT_CHECK",
        "python": sys.version,
        "platform": platform.platform(),
        "disk_free_bytes": usage.free,
        "disk_free_gib": round(usage.free / (1024**3), 2),
        "torch": _module_status("torch"),
        "torchaudio": _module_status("torchaudio"),
        "wavmark": _module_status("wavmark"),
        "ffmpeg": "AVAILABLE" if shutil.which("ffmpeg") else "NOT_FOUND",
        "local_weight_status": "NOT_FOUND",
        "download_performed": False,
        "inference_performed": False,
        "message_mode_target": "16-bit public WavMark mode",
        "notes": [
            "This is an environment feasibility audit only; no package or weight was downloaded.",
            "No PyTorch dependency was added to the Render/Course demo environment.",
            "Paper and upstream README claims are not local reproduction results.",
        ],
        "official_references": [
            "https://github.com/wavmark/wavmark",
            "https://huggingface.co/M4869/WavMark",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(build_audit(), indent=2) + "\n", encoding="utf-8")
    print(json.dumps(build_audit(), indent=2))


if __name__ == "__main__":
    main()
