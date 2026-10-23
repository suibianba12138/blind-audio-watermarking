from __future__ import annotations

import numpy as np

from app.audio_io import TARGET_SAMPLE_RATE
from app.public_config import build_embedding_config, load_public_selector
from audio_watermark.b1 import detect_watermark_b1, embed_watermark_b1


def test_arbitrary_32_bit_payload_roundtrip() -> None:
    rng = np.random.default_rng(7)
    clean = rng.normal(0.0, 0.15, 6 * TARGET_SAMPLE_RATE)
    payload = tuple(int(value) for value in rng.integers(0, 2, 32))
    config = build_embedding_config()
    selector = load_public_selector()
    marked = embed_watermark_b1(clean, payload, config, selector)
    result = detect_watermark_b1(marked, config, selector)
    assert result.payload_bits == payload
