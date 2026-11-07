import numpy as np
import pytest

from audio_watermark.v4_tf import (
    V4TFConfig,
    detect_v4_tf,
    embed_v4_tf,
    stft_roundtrip,
)


def _audio(sample_rate: int, seconds: float = 6.0) -> np.ndarray:
    generator = np.random.default_rng(20261025)
    return 0.25 * generator.standard_normal(int(sample_rate * seconds))


def test_hann_stft_roundtrip_is_numerically_reversible_after_center_padding():
    audio = _audio(48_000)
    reconstructed = stft_roundtrip(audio, sample_rate=48_000)
    assert reconstructed.shape == audio.shape
    assert np.max(np.abs(reconstructed - audio)) < 1e-10


def test_v4_embedding_is_deterministic_and_nontrivial():
    audio = _audio(48_000)
    config = V4TFConfig(payload_bits=8, strength=0.04)
    payload = (1, 0, 1, 1, 0, 0, 1, 0)
    first = embed_v4_tf(audio, payload, config)
    second = embed_v4_tf(audio, payload, config)
    assert np.array_equal(first, second)
    assert not np.array_equal(first, audio)
    assert np.all(np.isfinite(first))


def test_v4_detector_is_blind_and_returns_structured_evidence():
    audio = _audio(48_000)
    config = V4TFConfig(payload_bits=8, strength=0.08, presence_threshold=0.01)
    payload = (1, 0, 1, 1, 0, 0, 1, 0)
    marked = embed_v4_tf(audio, payload, config)
    result = detect_v4_tf(marked, config)
    assert result.recovered_payload == payload
    assert result.detected is True
    assert len(result.bit_statistics) == 8
    assert result.reject_reason is None
    assert result.used_frames > 0


def test_v4_detector_rejects_clean_audio_with_a_high_threshold():
    audio = _audio(48_000)
    config = V4TFConfig(payload_bits=8, strength=0.04, presence_threshold=10.0)
    result = detect_v4_tf(audio, config)
    assert result.detected is False
    assert result.recovered_payload is not None
    assert result.reject_reason == "presence_score_below_threshold"


def test_v4_config_allows_only_requested_capacity():
    with pytest.raises(ValueError):
        V4TFConfig(payload_bits=7, strength=0.04)
