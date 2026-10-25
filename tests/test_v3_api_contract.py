import inspect


def test_public_api_exports_the_blind_contract():
    from app.v3_api import detect_message, embed_message

    assert tuple(inspect.signature(embed_message).parameters) == ("audio", "message")
    assert tuple(inspect.signature(detect_message).parameters) == ("audio",)
