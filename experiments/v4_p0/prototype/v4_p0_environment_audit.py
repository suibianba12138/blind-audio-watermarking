"""Write a no-install V4-P0 runtime and resource audit."""

from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HOME_ROOT = Path.home()
ENVIRONMENTS = (
    HOME_ROOT / "robot" / "HumanoidRobotMujoco" / ".venv" / "bin" / "python",
    HOME_ROOT / "robot" / ".venv" / "bin" / "python",
    HOME_ROOT / "anaconda3" / "envs" / "unitree-rl" / "bin" / "python",
    HOME_ROOT / "anaconda3" / "bin" / "python",
)


def _probe(path: Path) -> dict[str, object]:
    if not path.is_file():
        return {"path": str(path), "available": False}
    code = r'''
import importlib.util, json, sys
out = {"path": sys.executable, "python": sys.version.split()[0]}
for name in ("torch", "torchaudio", "numpy", "scipy", "librosa", "soundfile"):
    try:
        module = __import__(name)
        out[name] = getattr(module, "__version__", "available")
    except Exception as exc:
        out[name] = "UNAVAILABLE:" + type(exc).__name__
try:
    import torch
    out["cuda_available"] = bool(torch.cuda.is_available())
    out["gpu_count"] = int(torch.cuda.device_count())
except Exception:
    out["cuda_available"] = False
    out["gpu_count"] = 0
print(json.dumps(out, sort_keys=True))
'''
    try:
        completed = subprocess.run(
            [str(path), "-c", code], capture_output=True, text=True, timeout=30, check=False
        )
        payload = json.loads(completed.stdout.strip().splitlines()[-1])
        payload["available"] = completed.returncode == 0
        return payload
    except Exception as exc:
        return {"path": str(path), "available": False, "error": type(exc).__name__}


def run(output: Path) -> dict[str, object]:
    usage = shutil.disk_usage(Path(os.environ.get("V4_DISK_ROOT", str(Path.home()))))
    result = {
        "status": "AUDITED_NO_INSTALL",
        "project": str(ROOT),
        "python_invoked": sys.version,
        "platform": platform.platform(),
        "ffmpeg": shutil.which("ffmpeg"),
        "free_disk_bytes": usage.free,
        "free_disk_gib": usage.free / (1024**3),
        "environments": [_probe(path) for path in ENVIRONMENTS],
        "nvidia_smi": shutil.which("nvidia-smi"),
        "robot_environment_modified": False,
        "virtual_environment_created": False,
        "policy": "no conda/venv creation; no unreviewed dependency upgrade or downgrade",
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
