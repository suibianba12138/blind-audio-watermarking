"""Frozen, self-contained configuration for the public Course V2 release.

This module deliberately exposes the existing REAL_TOP32 selector and identity
wrapper without importing calibration code or any research-data loader.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Sequence

from audio_watermark.codec_selector import CodecAwareCarrierSelector
from audio_watermark.codec_stability import map_from_dict
from audio_watermark.carrier import FrequencyBand
from audio_watermark.embed import EmbeddingConfig


SAMPLE_RATE = 48_000
BLOCK_SECONDS = 6
STRENGTH = 1.28
REJECTION_THRESHOLD = 8
PAYLOAD_SEED = 7
TOP_K = 32
REAL_TOP32_MAP_SHA256 = (
    "82c213813123239daaa86619e198b8e74f0880ac1c713518acedc0d6c109e3a9"
)
REAL_TOP32_SELECTOR_SHA256 = (
    "99fa9b0a3b864401184746040353e6aacf2b7d56914d5a18a77886c3ab53199d"
)

_RELEASE_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MAP_PATH = _RELEASE_ROOT / "configs" / "real_top32_stability_map.json"


def build_embedding_config() -> EmbeddingConfig:
    """Return the frozen fixed REAL_TOP32 embedding configuration."""

    return EmbeddingConfig(
        mode="fixed",
        strength=STRENGTH,
        sample_rate=SAMPLE_RATE,
        n_fft=2048,
        hop_length=2048,
        window=None,
        payload_bits=32,
        frames_per_bit=4,
        seed=PAYLOAD_SEED,
        candidate_band_hz=FrequencyBand(1000.0, 10000.0),
        bins_per_group=4,
        patches_per_bit=8,
    )


def selector_hash(group_ids: Sequence[int]) -> str:
    """Hash selected map group IDs using the frozen selector contract."""

    encoded = json.dumps([int(value) for value in group_ids], separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def load_public_selector(map_path: str | Path | None = None) -> CodecAwareCarrierSelector:
    """Load and validate the sanitized public REAL_TOP32 selector."""

    path = Path(map_path) if map_path is not None else DEFAULT_MAP_PATH
    if not path.is_file():
        raise FileNotFoundError(f"public REAL_TOP32 map not found: {path}")
    raw = json.loads(path.read_text(encoding="utf-8"))
    if raw.get("stage") != "P3E_B1_REAL_CALIBRATION_MAP":
        raise ValueError("public map stage does not match REAL_TOP32")
    if raw.get("status") != "PASS":
        raise ValueError("public map is not marked PASS")
    if int(raw.get("top_k", 0)) != TOP_K:
        raise ValueError("public map top_k does not match frozen REAL_TOP32")
    stability_map = map_from_dict(
        {
            "pool_seed": raw["pool_seed"],
            "codec_names": raw["codec_names"],
            "formula": raw["formula"],
            "entries": raw["entries"],
        }
    )
    if stability_map.sha256 != raw.get("map_sha256"):
        raise ValueError("public map self-hash is invalid")
    if stability_map.sha256 != REAL_TOP32_MAP_SHA256:
        raise ValueError("public map hash does not match the frozen contract")
    selector = CodecAwareCarrierSelector.from_stability_map(
        stability_map, top_k=TOP_K, watermark_seed=PAYLOAD_SEED
    )
    if selector_hash(selector.selected_group_ids) != REAL_TOP32_SELECTOR_SHA256:
        raise ValueError("public selector hash does not match the frozen contract")
    return selector


def public_provenance(map_path: str | Path | None = None) -> dict[str, object]:
    """Return non-sensitive provenance shown by CLI and GUI outputs."""

    path = Path(map_path) if map_path is not None else DEFAULT_MAP_PATH
    selector = load_public_selector(path)
    return {
        "selector": "REAL_TOP32",
        "map_file": path.name,
        "map_sha256": REAL_TOP32_MAP_SHA256,
        "selector_sha256": selector_hash(selector.selected_group_ids),
        "top_k": TOP_K,
        "watermark_seed": PAYLOAD_SEED,
        "strength": STRENGTH,
        "rejection_threshold": REJECTION_THRESHOLD,
    }
