import pytest

from audio_watermark.v3_p2 import assign_development_roles, message_for_seed


def _records():
    return [
        {"category": category, "record_id": f"{category}-{index:02d}", "split": "dev"}
        for category in ("music", "speech", "environment")
        for index in range(10)
    ]


def test_development_roles_are_category_balanced_and_order_independent():
    rows = assign_development_roles(list(reversed(_records())), calibration_count=5)
    assert len(rows) == 30
    for category in ("music", "speech", "environment"):
        grouped = [row for row in rows if row["category"] == category]
        assert [row["p2_role"] for row in grouped if row["record_id"].endswith("00")][0] == "calibration"
        assert sum(row["p2_role"] == "calibration" for row in grouped) == 5
        assert sum(row["p2_role"] == "pilot" for row in grouped) == 5


def test_messages_are_deterministic_and_have_requested_capacity():
    assert message_for_seed(101, 12) == message_for_seed(101, 12)
    assert len(message_for_seed(101, 12)) == 12
    assert len(message_for_seed(101, 16)) == 16
    assert message_for_seed(101, 12) != message_for_seed(202, 12)


def test_role_assignment_requires_ten_development_sources_per_category():
    records = _records()[:-1]
    with pytest.raises(ValueError, match="ten development sources"):
        assign_development_roles(records, calibration_count=5)
