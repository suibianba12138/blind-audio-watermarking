"""Independent blind identity detector process for the public demo."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from audio_watermark.course_v2 import detect_identity_multiblock

from .audio_io import decode_audio_file, prepare_for_demo
from .public_config import (
    BLOCK_SECONDS,
    REJECTION_THRESHOLD,
    build_embedding_config,
    load_public_selector,
    public_provenance,
)


def detect_file(input_path: str | Path, map_path: str | Path | None = None) -> dict[str, object]:
    """Detect an identity using only the received file and public configuration."""

    decoded = decode_audio_file(input_path)
    prepared = prepare_for_demo(decoded)
    selector = load_public_selector(map_path)
    decision = detect_identity_multiblock(
        prepared.samples,
        build_embedding_config(),
        selector,
        max_hamming_distance=REJECTION_THRESHOLD,
        block_seconds=BLOCK_SECONDS,
    )
    aggregate = decision.aggregate
    return {
        "status": aggregate.status,
        "identity": aggregate.identity,
        "minimum_distance": aggregate.minimum_distance,
        "rejection_threshold": REJECTION_THRESHOLD,
        "tied": aggregate.tied,
        "confidence": aggregate.confidence,
        "distances": dict(aggregate.distances),
        "recovered_bits": list(aggregate.recovered_bits),
        "block_count": len(decision.blocks),
        "block_statuses": [item.status for item in decision.block_decisions],
        "sample_rate": prepared.sample_rate,
        "duration_seconds": prepared.samples.size / prepared.sample_rate,
        "provenance": public_provenance(map_path),
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Blind public identity detector")
    parser.add_argument("--input", required=True, help="received WAV/MP3 path")
    parser.add_argument("--map", default=None, help="optional public map path")
    parser.add_argument("--json", action="store_true", help="emit one JSON object")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        result = detect_file(args.input, args.map)
    except Exception as error:  # CLI boundary: return a readable failure, not a traceback.
        payload = {"status": "ERROR", "error": str(error)}
        print(json.dumps(payload, ensure_ascii=False))
        return 2
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
