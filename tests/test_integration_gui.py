from __future__ import annotations

import json
import inspect
from pathlib import Path

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


def test_v3_received_upload_component_preserves_file_bytes() -> None:
    import app.integration_gui as gui

    source = inspect.getsource(gui.build_integration_demo)

    assert 'v3_received_audio = gr.File(' in source
    assert 'file_types=["audio"]' in source
    assert 'v3_received_audio = gr.Audio(' not in source


def test_v3_mp3_callback_returns_mp3_received_filepath_and_separate_state(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import app.integration_gui as gui
    from app.session_store import SessionStore

    store = SessionStore(tmp_path / "gui-store")
    session = store.create()
    marked_path = session.path("watermarked.wav")
    marked_path.write_bytes(b"marked")
    decoded_path = session.path("compressed_128k_decoded.wav")
    mp3_path = session.path("compressed_128k.mp3")

    monkeypatch.setattr(gui, "_GUI_SESSION_STORE", store)
    monkeypatch.setattr(gui, "decode_audio_file", lambda path: object())

    def fake_encode_decode(marked, output_dir):
        assert output_dir == session.root
        mp3_path.write_bytes(b"mp3")
        decoded_path.write_bytes(b"decoded")
        return mp3_path, decoded_path, object()

    monkeypatch.setattr(gui, "encode_decode_mp3", fake_encode_decode)
    state = json.dumps({"session_id": session.root.name})

    outputs = gui._compress_v3_action(state)

    assert outputs[0] == str(mp3_path)
    assert outputs[1] == str(decoded_path)
    assert outputs[2] == str(mp3_path)
    assert outputs[2] != outputs[1]
    assert json.loads(outputs[3]) == {"session_id": session.root.name}


def test_v3_gui_state_cannot_supply_arbitrary_paths(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import app.integration_gui as gui
    from app.session_store import SessionStore

    store = SessionStore(tmp_path / "gui-store")
    monkeypatch.setattr(gui, "_GUI_SESSION_STORE", store)
    outside = tmp_path / "outside.wav"
    outside.write_bytes(b"must not be read")

    outputs = gui._compress_v3_action(
        json.dumps(
            {
                "session_id": "../outside",
                "marked_path": str(outside),
                "output_dir": str(tmp_path),
            }
        )
    )

    assert outputs[:4] == (None, None, None, None)
    assert "失败" in outputs[4]


def test_v3_mp3_callback_cleans_session_after_encoding_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import app.integration_gui as gui
    from app.session_store import SessionStore

    store = SessionStore(tmp_path / "gui-store")
    session = store.create()
    session.path("watermarked.wav").write_bytes(b"marked")
    monkeypatch.setattr(gui, "_GUI_SESSION_STORE", store)
    monkeypatch.setattr(gui, "decode_audio_file", lambda path: object())

    def fail_encode_decode(marked, output_dir):
        raise RuntimeError("injected FFmpeg failure")

    monkeypatch.setattr(gui, "encode_decode_mp3", fail_encode_decode)

    outputs = gui._compress_v3_action(
        json.dumps({"session_id": session.root.name})
    )

    assert outputs[:4] == (None, None, None, None)
    assert "injected FFmpeg failure" in outputs[4]
    assert not session.root.exists()


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
