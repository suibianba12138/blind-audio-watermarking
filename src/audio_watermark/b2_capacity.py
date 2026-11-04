"""Finite V3-P2 capacity-code adapters over the frozen 32-bit B1 channel.

The module contains no audio processing.  It only maps variable-length binary
messages to 32-bit deterministic Boolean evaluation-code words and decodes the
continuous signed statistics returned by the existing blind B1 detector.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Sequence

import numpy as np
from numpy.typing import ArrayLike


_SUPPORTED_BITS = (8, 12, 16)


@dataclass(frozen=True)
class CapacityDecode:
    """Blind continuous-statistics result for one capacity code."""

    payload_bits: int
    message_bits: tuple[int, ...]
    codeword_index: int
    score: float
    margin: float
    presence_score: float
    hard_physical_bits: tuple[int, ...]


def _validate_payload_bits(payload_bits: int) -> int:
    value = int(payload_bits)
    if value not in _SUPPORTED_BITS:
        raise ValueError(f"payload_bits must be one of {_SUPPORTED_BITS}")
    return value


def _basis_terms(payload_bits: int) -> tuple[tuple[str, int, int | None], ...]:
    payload_bits = _validate_payload_bits(payload_bits)
    terms: list[tuple[str, int, int | None]] = [("constant", 0, None)]
    terms.extend(("linear", coordinate, None) for coordinate in range(5))
    all_pairs = [(left, right) for left in range(5) for right in range(left + 1, 5)]
    if payload_bits == 8:
        pairs = [(0, 1), (0, 2)]
    elif payload_bits == 12:
        pairs = all_pairs[:6]
    else:
        pairs = all_pairs
    terms.extend(("quadratic", left, right) for left, right in pairs)
    return tuple(terms)


def _points() -> np.ndarray:
    return np.asarray(
        [[(index >> coordinate) & 1 for coordinate in range(5)] for index in range(32)],
        dtype=np.uint8,
    )


@lru_cache(maxsize=None)
def _cached_codebook(payload_bits: int) -> np.ndarray:
    payload_bits = _validate_payload_bits(payload_bits)
    points = _points()
    columns = []
    for kind, left, right in _basis_terms(payload_bits):
        if kind == "constant":
            columns.append(np.ones(32, dtype=np.uint8))
        elif kind == "linear":
            columns.append(points[:, left])
        else:
            assert right is not None
            columns.append(points[:, left] & points[:, right])
    basis = np.column_stack(columns)
    codebook = np.empty((2**payload_bits, 32), dtype=np.uint8)
    for index in range(2**payload_bits):
        bits = np.asarray(
            [(index >> (payload_bits - 1 - bit)) & 1 for bit in range(payload_bits)],
            dtype=np.uint8,
        )
        codebook[index] = np.mod(basis @ bits, 2).astype(np.uint8)
    codebook.setflags(write=False)
    return codebook


def capacity_codebook(payload_bits: int) -> np.ndarray:
    """Return a copy of the deterministic 32-position codebook."""

    return _cached_codebook(_validate_payload_bits(payload_bits)).copy()


def _payload_to_index(payload: Sequence[int], payload_bits: int) -> int:
    values = tuple(int(value) for value in payload)
    if len(values) != payload_bits or any(value not in (0, 1) for value in values):
        raise ValueError(f"payload must contain exactly {payload_bits} binary bits")
    index = 0
    for value in values:
        index = (index << 1) | value
    return index


def encode_capacity_payload(payload: Sequence[int], payload_bits: int) -> np.ndarray:
    """Encode a variable-length binary message into 32 physical positions."""

    payload_bits = _validate_payload_bits(payload_bits)
    return _cached_codebook(payload_bits)[_payload_to_index(payload, payload_bits)].copy()


def _index_to_payload(index: int, payload_bits: int) -> tuple[int, ...]:
    return tuple((index >> (payload_bits - 1 - bit)) & 1 for bit in range(payload_bits))


def decode_soft_capacity(statistics: ArrayLike, payload_bits: int) -> CapacityDecode:
    """Blindly decode 32 finite signed statistics for a selected code size."""

    payload_bits = _validate_payload_bits(payload_bits)
    values = np.asarray(statistics, dtype=np.float64)
    if values.ndim != 1 or values.size != 32 or not np.all(np.isfinite(values)):
        raise ValueError("statistics must be a finite one-dimensional vector of length 32")
    scale = float(np.sum(np.abs(values)))
    if scale <= np.finfo(float).tiny:
        scores = np.zeros(2**payload_bits, dtype=np.float64)
    else:
        signs = 2.0 * _cached_codebook(payload_bits).astype(np.float64) - 1.0
        scores = signs @ values / scale
    best = int(np.argmax(scores))
    top = float(scores[best])
    second = float(np.partition(scores, -2)[-2])
    return CapacityDecode(
        payload_bits=payload_bits,
        message_bits=_index_to_payload(best, payload_bits),
        codeword_index=best,
        score=top,
        margin=top - second,
        presence_score=max(0.0, top),
        hard_physical_bits=tuple(int(value >= 0.0) for value in values),
    )
