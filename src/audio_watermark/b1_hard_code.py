"""Hard-decision control for the frozen 32-to-8 B1 pilot code."""

from __future__ import annotations

from typing import Sequence

import numpy as np

from .b1_soft import encode_soft_payload, soft_codebook


def _validate_bits(values: Sequence[int], expected_length: int, label: str) -> tuple[int, ...]:
    result = tuple(int(value) for value in values)
    if len(result) != expected_length or any(value not in (0, 1) for value in result):
        raise ValueError(f"{label} must contain exactly {expected_length} binary bits")
    return result


def encode_hard_payload(payload: Sequence[int]) -> tuple[int, ...]:
    """Encode one 8-bit payload into the fixed 32-bit pilot codeword."""

    return tuple(int(value) for value in encode_soft_payload(_validate_bits(payload, 8, "payload")))


def decode_hard_physical_bits(bits: Sequence[int]) -> tuple[int, ...]:
    """Decode hard physical bits by minimum Hamming distance.

    ``numpy.argmin`` provides the specified deterministic tie rule: the lowest
    codeword index is selected when several codewords have equal distance.
    """

    observed = np.asarray(_validate_bits(bits, 32, "physical bits"), dtype=np.uint8)
    distances = np.sum(soft_codebook() != observed[None, :], axis=1)
    index = int(np.argmin(distances))
    return tuple((index >> (7 - bit)) & 1 for bit in range(8))
