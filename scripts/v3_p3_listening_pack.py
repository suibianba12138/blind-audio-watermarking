#!/usr/bin/env python3
"""Create an explicit A/B listening pack for the frozen V3 local demo."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.v3_pipeline import run_v3_demo


def build_listening_pack(
    input_path: str | Path,
    output_dir: str | Path,
    *,
    message: int = 173,
) -> dict[str, object]:
    """Write original/marked/MP3 files and a Chinese preliminary checklist."""

    source = Path(input_path)
    destination = Path(output_dir)
    run = run_v3_demo(source, message, codec="mp3", output_dir=destination)
    checklist = destination / "LISTENING_CHECKLIST_ZH.md"
    checklist.write_text(
        "# V3 P3 初步试听筛查清单\n\n"
        "本目录仅用于小规模、非正式的 A/B 试听筛查，不构成正式感知质量实验。\n\n"
        "## 文件\n\n"
        f"- 原始准备音频：`{run.original_wav.name}`\n"
        f"- 水印 WAV：`{run.marked_wav.name}`\n"
        f"- MP3（FFmpeg libmp3lame 128 kbps）：`{run.compressed_mp3.name if run.compressed_mp3 else 'NOT_AVAILABLE'}`\n"
        f"- MP3 解码 WAV：`{run.compressed_wav.name if run.compressed_wav else 'NOT_AVAILABLE'}`\n\n"
        "## 建议流程\n\n"
        "1. 随机化 A/B 播放顺序，使用耳机或稳定音箱。\n"
        "2. 分别记录是否听到噪声、金属感、泵动、突变、削波或其他异常。\n"
        "3. 先比较原始 WAV 与水印 WAV，再比较水印 WAV 与 MP3 解码 WAV。\n"
        "4. 不将一次试听结果写成统计显著性或正式不可感知性结论。\n\n"
        "`FORMAL_PERCEPTUAL_GATE = NOT_ESTABLISHED`\n"
        "`LISTENING_STATUS = PRELIMINARY_SCREENING_ONLY`\n",
        encoding="utf-8",
    )
    return {
        "status": "PASS",
        "message": message,
        "input_path": str(source),
        "output_dir": str(destination),
        "original_wav": str(run.original_wav),
        "marked_wav": str(run.marked_wav),
        "compressed_mp3": str(run.compressed_mp3) if run.compressed_mp3 else None,
        "compressed_wav": str(run.compressed_wav) if run.compressed_wav else None,
        "checklist": str(checklist),
        "formal_perceptual_gate": "NOT_ESTABLISHED",
        "listening_status": "PRELIMINARY_SCREENING_ONLY",
        "detection": {
            "status": run.detection.status,
            "message": run.detection.message,
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Create a V3 A/B listening pack")
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--message", type=int, default=173)
    args = parser.parse_args(argv)
    try:
        result = build_listening_pack(args.input, args.output_dir, message=args.message)
    except Exception as error:
        print(json.dumps({"status": "FAIL", "error": str(error)}, ensure_ascii=False))
        return 2
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
