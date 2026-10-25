from __future__ import annotations

import inspect

import pytest

from app.integration_gui import (
    LEGACY_MODE,
    V3_MODE,
    detect_uploaded_file,
    detect_v3_uploaded_file,
)


def test_integration_gui_builds_without_launching() -> None:
    gr = pytest.importorskip("gradio")
    from app.integration_gui import build_integration_demo

    demo = build_integration_demo()
    try:
        assert isinstance(demo, gr.Blocks)
    finally:
        close = getattr(demo, "close", None)
        if callable(close):
            close()


def test_integration_modes_are_frozen_and_distinct() -> None:
    assert V3_MODE == "V3 8-bit Soft-Code"
    assert LEGACY_MODE == "Legacy Course V2"
    assert V3_MODE != LEGACY_MODE


def test_v3_detection_callbacks_accept_only_received_file() -> None:
    assert list(inspect.signature(detect_uploaded_file).parameters) == ["input_path"]
    assert list(inspect.signature(detect_v3_uploaded_file).parameters) == [
        "received_path"
    ]
    assert "expected" not in inspect.signature(detect_uploaded_file).parameters
    assert "expected" not in inspect.signature(detect_v3_uploaded_file).parameters


def test_v3_detection_formatter_has_no_correctness_input() -> None:
    from app.integration_gui import _format_v3_detection

    assert list(inspect.signature(_format_v3_detection).parameters) == [
        "result",
        "elapsed_seconds",
    ]


def test_local_launcher_is_import_safe_and_uses_localhost(monkeypatch) -> None:
    import gradio_v3_app

    calls: dict[str, object] = {}

    class FakeDemo:
        def launch(self, **kwargs):
            calls.update(kwargs)

    monkeypatch.setenv("GRADIO_SERVER_PORT", "8799")
    monkeypatch.setattr(gradio_v3_app, "build_integration_demo", lambda: FakeDemo())

    gradio_v3_app.main()

    assert calls == {
        "server_name": "127.0.0.1",
        "server_port": 8799,
        "share": False,
        "inbrowser": False,
        "show_error": True,
    }
