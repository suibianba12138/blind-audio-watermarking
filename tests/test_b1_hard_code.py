"""TDD contract for the P1 hard-decision control."""

from __future__ import annotations

import itertools

import pytest

from audio_watermark.b1_hard_code import decode_hard_physical_bits, encode_hard_payload


def test_hard_code_round_trips_every_eight_bit_payload() -> None:
    for values in itertools.product((0, 1), repeat=8):
        physical = encode_hard_payload(values)
        assert len(physical) == 32
        assert decode_hard_physical_bits(physical) == values


def test_hard_code_corrects_one_physical_bit_error() -> None:
    payload = (1, 0, 1, 1, 0, 0, 1, 0)
    physical = list(encode_hard_payload(payload))
    physical[13] ^= 1
    assert decode_hard_physical_bits(physical) == payload


def test_hard_code_rejects_invalid_payload_and_physical_lengths() -> None:
    with pytest.raises(ValueError):
        encode_hard_payload((0, 1))
    with pytest.raises(ValueError):
        encode_hard_payload((0,) * 7 + (2,))
    with pytest.raises(ValueError):
        decode_hard_physical_bits((0,) * 31)


def test_hard_code_ties_choose_lowest_codeword_index() -> None:
    zero = encode_hard_payload((0,) * 8)
    one = encode_hard_payload((0, 0, 0, 0, 0, 0, 0, 1))
    differing = [index for index, (a, b) in enumerate(zip(zero, one)) if a != b]
    midpoint = list(zero)
    for index in differing[: len(differing) // 2]:
        midpoint[index] = one[index]
    assert decode_hard_physical_bits(midpoint) == (0,) * 8
