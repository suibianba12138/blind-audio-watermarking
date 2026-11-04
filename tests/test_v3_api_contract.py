import inspect


def test_public_api_exports_the_blind_contract():
    from app.v3_api import (
        V3DetectionResult,
        V3EmbedResult,
        detect_message,
        embed_message,
    )

    assert tuple(inspect.signature(embed_message).parameters) == ("audio", "message")
    assert tuple(inspect.signature(detect_message).parameters) == ("audio",)
    assert V3EmbedResult.__annotations__["audio"] == "AudioData"
    assert V3DetectionResult.__annotations__["status"] == "str"


def test_detection_result_contract_has_only_the_two_valid_status_values():
    from app.v3_api import VALID_STATUSES

    assert VALID_STATUSES == frozenset({"IDENTIFIED", "UNKNOWN"})
