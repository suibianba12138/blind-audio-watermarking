"""TDD contract for the bounded B1 soft-code pilot."""

from __future__ import annotations

import inspect

import numpy as np
import pytest

from audio_watermark.b1_soft import (
    decode_soft_statistics,
    detect_watermark_b1_soft,
    encode_soft_payload,
    soft_codebook,
)


def test_fixed_codebook_has_256_words_and_minimum_distance_eight() -> None:
    codebook = soft_codebook()
    assert codebook.shape == (256, 32)
    assert np.unique(codebook, axis=0).shape[0] == 256
    distances = np.count_nonzero(codebook[:, None, :] != codebook[None, :, :], axis=2)
    assert int(np.min(distances[np.triu_indices(256, k=1)])) == 8


def test_soft_statistics_decode_a_clean_codeword() -> None:
    payload = (1, 0, 1, 1, 0, 0, 1, 0)
    codeword = encode_soft_payload(payload)
    statistics = np.where(codeword, 0.7, -0.7)

    result = decode_soft_statistics(statistics)

    assert result.payload_bits == payload
    assert result.presence_score > 0.99


def test_soft_decoder_rejects_wrong_physical_length() -> None:
    with pytest.raises(ValueError):
        decode_soft_statistics(np.zeros(31, dtype=np.float64))


def test_b1_soft_detector_is_blind_by_api_contract() -> None:
    parameters = inspect.signature(detect_watermark_b1_soft).parameters
    assert "expected_payload" not in parameters
    assert "clean_audio" not in parameters
