import sys
from pathlib import Path

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / "examples"))

from payload_layout import c2_long_id_block_messages, c3_192bit_block_messages


def test_c2_long_id_repeats_one_32bit_identity_three_times():
    assert c2_long_id_block_messages("0x12345678") == [0x12, 0x34, 0x56, 0x78] * 3


def test_c3_192bit_splits_into_twelve_independent_16bit_messages():
    payload = "000102030405060708090A0B0C0D0E0F1011121314151617"
    assert c3_192bit_block_messages(payload) == [
        0x0001, 0x0203, 0x0405, 0x0607, 0x0809, 0x0A0B,
        0x0C0D, 0x0E0F, 0x1011, 0x1213, 0x1415, 0x1617,
    ]
