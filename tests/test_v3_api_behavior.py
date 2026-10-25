from __future__ import annotations

import inspect

import numpy as np
import pytest

from app.audio_io import AudioData


def make_probe(seconds: float = 6.0, sample_rate: int = 48_000) -> np.ndarray:
    """Return a deterministic, low-level broadband probe for API tests."""

    count = int(seconds * sample_rate)
    rng = np.random.default_rng(20261025)
    return (0.04 * rng.standard_normal(count)).astype(np.float64)


def test_embed_and_detect_round_trip_integer_message():
    from app.v3_api import embed_message, detect_message

    clean = AudioData(make_probe(6), 48_000)
    marked = embed_message(clean, 173)
    result = detect_message(marked.audio)

    assert marked.message == 173
    assert marked.audio.sample_rate == 48_000
    assert marked.audio.samples.size == 6 * 48_000
    assert result.status == "IDENTIFIED"
    assert result.message == 173
    assert result.threshold == 0.7855073980199624


def test_api_rejects_non_integer_and_out_of_range_messages():
    from app.v3_api import embed_message

    clean = AudioData(make_probe(6), 48_000)
    for message in (-1, 256, 1.5, "7"):
        with pytest.raises(ValueError):
            embed_message(clean, message)


def test_clean_audio_is_unknown_and_detector_has_no_expected_message_argument():
    from app.v3_api import detect_message

    clean = AudioData(make_probe(6), 48_000)

    result = detect_message(clean)

    assert result.status == "UNKNOWN"
    assert result.message is None
    assert "expected" not in inspect.signature(detect_message).parameters


def test_short_input_is_zero_padded_to_the_frozen_six_second_protocol():
    from app.v3_api import embed_message

    short = AudioData(make_probe(1.0), 48_000)
    result = embed_message(short, 0)

    assert result.audio.sample_rate == 48_000
    assert result.audio.samples.size == 6 * 48_000


def test_inputs_longer_than_public_bound_are_rejected():
    from app.v3_api import embed_message

    long_audio = AudioData(np.zeros(31 * 48_000, dtype=np.float64), 48_000)

    with pytest.raises(ValueError, match="30-second"):
        embed_message(long_audio, 0)
