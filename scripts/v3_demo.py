#!/usr/bin/env python3
"""CLI fallback for the frozen V3 8-bit blind demo."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, is_dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from app.v3_pipeline import detect_uploaded_file, run_v3_demo  # noqa: E402


def _jsonable(value: object) -> object:
    if isinstance(value, Path):
        return str(value)
    if is_dataclass(value):
        return _jsonable(asdict(value))
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    return value


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the frozen V3 8-bit blind demo")
    parser.add_argument("--input", default=None, help="clean local audio for embed mode")
    parser.add_argument("--message", default=None, help="integer message in [0, 255]")
    parser.add_argument("--codec", choices=("identity", "mp3"), default="identity")
    parser.add_argument("--output-dir", default=None)
    parser.add_argument("--detect-input", default=None, help="received audio for blind-only mode")
    return parser


def _error(message: str) -> int:
    print(json.dumps({"status": "ERROR", "error": message}, ensure_ascii=False))
    return 2


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.detect_input is not None:
            if args.input is not None or args.message is not None:
                return _error("--detect-input cannot be combined with --input or --message")
            result = detect_uploaded_file(args.detect_input)
            print(json.dumps(_jsonable({"mode": "detect", "detection": result}), ensure_ascii=False, sort_keys=True))
            return 0

        if args.input is None:
            return _error("--input is required for embed mode")
        if args.message is None:
            return _error("--message is required for embed mode")
        try:
            message = int(args.message)
        except (TypeError, ValueError) as error:
            raise ValueError("message must be an integer in the range [0, 255]") from error
        run = run_v3_demo(
            args.input,
            message,
            codec=args.codec,
            output_dir=args.output_dir,
        )
        print(json.dumps(_jsonable(run), ensure_ascii=False, sort_keys=True))
        return 0
    except Exception as error:
        return _error(str(error))


if __name__ == "__main__":
    raise SystemExit(main())
