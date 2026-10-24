import numpy as np
import pytest

from audio_watermark.b1_soft import soft_codebook
from audio_watermark.b2_capacity import (
    capacity_codebook,
    decode_soft_capacity,
    encode_capacity_payload,
)


def test_eight_bit_codebook_is_exactly_the_frozen_soft_codebook():
    np.testing.assert_array_equal(capacity_codebook(8), soft_codebook())


@pytest.mark.parametrize("payload_bits", [12, 16])
def test_variable_capacity_payload_round_trips_through_codeword(payload_bits):
    payload = tuple((index * 3 + 1) % 2 for index in range(payload_bits))
    codeword = encode_capacity_payload(payload, payload_bits)
    result = decode_soft_capacity(2.0 * codeword.astype(float) - 1.0, payload_bits)
    assert result.message_bits == payload
    assert result.score == pytest.approx(1.0)
    assert result.presence_score == pytest.approx(1.0)


@pytest.mark.parametrize("payload_bits", [12, 16])
def test_degree_two_capacity_code_has_32_positions_and_minimum_distance_eight(payload_bits):
    codebook = capacity_codebook(payload_bits)
    assert codebook.shape == (2**payload_bits, 32)
    assert np.all(np.sum(codebook[1:] != codebook[0], axis=1) >= 8)
    distances = [
        int(np.count_nonzero(codebook[index] != codebook[index + 1]))
        for index in range(min(256, codebook.shape[0] - 1))
    ]
    assert min(distances) >= 8


def test_inverted_statistics_decode_to_the_complementary_codeword():
    payload = tuple([0, 1] * 4)
    codeword = encode_capacity_payload(payload, 8)
    result = decode_soft_capacity(-(2.0 * codeword.astype(float) - 1.0), 8)
    assert result.message_bits != payload
    assert result.score == pytest.approx(1.0)


@pytest.mark.parametrize("payload_bits", [7, 9, 17])
def test_unsupported_capacity_is_rejected(payload_bits):
    with pytest.raises(ValueError):
        capacity_codebook(payload_bits)
