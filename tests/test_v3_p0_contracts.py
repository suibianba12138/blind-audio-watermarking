"""Contract tests for the additive V3 P0 prototype only."""

from __future__ import annotations

import numpy as np

from audio_watermark.v3_p0 import (
    SpreadSpectrumConfig,
    detect_spread_spectrum,
    embed_spread_spectrum,
)


def _fixture(seconds: float = 6.0, sample_rate: int = 48_000) -> np.ndarray:
    time = np.arange(int(seconds * sample_rate), dtype=np.float64) / sample_rate
    return 0.25 * (
        np.sin(2.0 * np.pi * 220.0 * time)
        + 0.35 * np.sin(2.0 * np.pi * 440.0 * time)
    )


def test_single_bit_is_blind_and_deterministic() -> None:
    config = SpreadSpectrumConfig(payload_bits=1, frames_per_bit=32, strength=0.08)
    clean = _fixture()
    marked_a = embed_spread_spectrum(clean, (1,), config)
    marked_b = embed_spread_spectrum(clean, (1,), config)
    assert np.array_equal(marked_a, marked_b)
    detected = detect_spread_spectrum(marked_a, config)
    assert detected.payload_bits == (1,)


def test_eight_bit_no_attack_round_trip() -> None:
    config = SpreadSpectrumConfig(payload_bits=8, frames_per_bit=16, strength=0.08)
    payload = (1, 0, 1, 1, 0, 0, 1, 0)
    marked = embed_spread_spectrum(_fixture(), payload, config)
    assert detect_spread_spectrum(marked, config).payload_bits == payload


def test_prototype_rejects_non_supported_payload_size() -> None:
    with np.testing.assert_raises(ValueError):
        SpreadSpectrumConfig(payload_bits=2, frames_per_bit=16, strength=0.08)
