from __future__ import annotations

import numpy as np

from app.audio_io import TARGET_SAMPLE_RATE
from app.public_config import build_embedding_config, load_public_selector
from audio_watermark.course_v2 import (
    CODEBOOK_MIN_DISTANCE,
    IDENTITY_CODEBOOK,
    IDENTITY_NAMES,
    codebook_pairwise_distances,
    detect_identity_multiblock,
    embed_identity_multiblock,
    identify_bits,
)


def _signal(seconds: int = 6) -> np.ndarray:
    rng = np.random.default_rng(20261023)
    samples = rng.normal(0.0, 0.12, seconds * TARGET_SAMPLE_RATE)
    time = np.arange(samples.size) / TARGET_SAMPLE_RATE
    return samples + 0.08 * np.sin(2 * np.pi * 440.0 * time)


def test_public_codebook_has_four_identities_and_min_distance_21() -> None:
    distances = codebook_pairwise_distances()
    assert set(IDENTITY_CODEBOOK) == set(IDENTITY_NAMES)
    assert all(len(codeword) == 32 for codeword in IDENTITY_CODEBOOK.values())
    assert sorted(distances.values()) == [21, 21, 21, 21, 22, 22]
    assert CODEBOOK_MIN_DISTANCE == 21


def test_identity_roundtrip_is_blind_and_deterministic() -> None:
    clean = _signal()
    config = build_embedding_config()
    selector = load_public_selector()
    first = embed_identity_multiblock(clean, "UESTC-003", config, selector)
    second = embed_identity_multiblock(clean, "UESTC-003", config, selector)
    assert np.array_equal(first.audio, second.audio)
    decision = detect_identity_multiblock(
        first.audio,
        config,
        selector,
        max_hamming_distance=8,
    ).aggregate
    assert decision.status == "IDENTIFIED"
    assert decision.identity == "UESTC-003"
    assert decision.minimum_distance == 0


def test_identity_rejects_over_threshold_corruption() -> None:
    bits = list(IDENTITY_CODEBOOK["UESTC-001"])
    for index in range(9):
        bits[index] = 1 - bits[index]
    decision = identify_bits(bits, max_hamming_distance=8)
    assert decision.status == "UNKNOWN"
    assert decision.identity is None
    assert decision.minimum_distance >= 9
