"""Packet-shape contracts for payload, sync, and future error correction."""

from __future__ import annotations

from dataclasses import dataclass
from numbers import Integral
from typing import Sequence


def _bits(
    values: Sequence[int], *, name: str, allow_empty: bool = False
) -> tuple[int, ...]:
    normalized = tuple(value for value in values)
    if not normalized and not allow_empty:
        raise ValueError(f"{name} must not be empty")
    if any(not isinstance(value, Integral) or int(value) not in (0, 1) for value in normalized):
        raise ValueError(f"{name} must contain only 0 and 1")
    return tuple(int(value) for value in normalized)


def normalize_bits(values: Sequence[int], *, name: str = "bits") -> tuple[int, ...]:
    """Validate and normalize a non-empty binary sequence."""

    return _bits(values, name=name)


@dataclass(frozen=True)
class WatermarkPacket:
    """A future packet carrying payload and optional synchronization bits."""

    payload_bits: tuple[int, ...]
    sync_bits: tuple[int, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "payload_bits", _bits(self.payload_bits, name="payload_bits"))
        object.__setattr__(
            self,
            "sync_bits",
            _bits(self.sync_bits, name="sync_bits", allow_empty=True),
        )


def encode_packet(packet: WatermarkPacket) -> tuple[int, ...]:
    """Define the future packet encoder; CRC/ECC policy is not fixed in P0."""

    raise NotImplementedError("packet encoding is intentionally deferred beyond P0")


def decode_packet(bits: Sequence[int]) -> WatermarkPacket:
    """Define the future packet decoder; CRC/ECC policy is not fixed in P0."""

    raise NotImplementedError("packet decoding is intentionally deferred beyond P0")
