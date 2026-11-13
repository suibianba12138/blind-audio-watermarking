"""Payload layout helpers for the two documented 72-second modes."""
from __future__ import annotations


def _parse_hex(value: str, digits: int) -> str:
    normalized = value.removeprefix("0x").removeprefix("0X")
    if len(normalized) != digits:
        raise ValueError(f"payload requires exactly {digits} hexadecimal digits")
    try:
        int(normalized, 16)
    except ValueError as error:
        raise ValueError("payload must be hexadecimal") from error
    return normalized.upper()


def c2_long_id_block_messages(payload32_hex: str) -> list[int]:
    """Return 12 bytes: four ID bytes repeated three times over 72 seconds."""
    payload = _parse_hex(payload32_hex, 8)
    one_pass = [int(payload[index : index + 2], 16) for index in range(0, 8, 2)]
    return one_pass * 3


def c3_192bit_block_messages(payload192_hex: str) -> list[int]:
    """Return twelve independent 16-bit messages from a 192-bit payload."""
    payload = _parse_hex(payload192_hex, 48)
    return [int(payload[index : index + 4], 16) for index in range(0, 48, 4)]
