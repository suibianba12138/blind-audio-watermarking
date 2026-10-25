"""Independent blind detector process for the frozen V3 8-bit candidate."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

from .audio_io import decode_audio_file
from .public_config import load_public_selector
from .v3_api import detect_message


def detect_file(input_path: str | Path, map_path: str | Path | None = None) -> dict[str, object]:
    """Detect a V3 message using only a received file and public configuration.

    The optional map is validated against the frozen public selector contract.
    The V3 API itself owns the selector used for detection; no expected message,
    clean audio, filename label, or embedding-session state enters this call.
    """

    if map_path is not None:
        load_public_selector(map_path)
    result = detect_message(decode_audio_file(input_path))
    return asdict(result)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Blind V3 8-bit message detector")
    parser.add_argument("--input", required=True, help="received WAV/MP3 path")
    parser.add_argument(
        "--map",
        default=None,
        help="optional frozen map path to validate only; detection uses the frozen selector",
    )
    parser.add_argument("--json", action="store_true", help="emit one JSON object")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        result = detect_file(args.input, args.map)
    except Exception as error:  # CLI boundary: return a structured failure.
        print(json.dumps({"status": "ERROR", "error": str(error)}, ensure_ascii=False))
        return 2
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
