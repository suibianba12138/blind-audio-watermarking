from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pytest

from app.audio_io import (
    FFMPEG_TIMEOUT_SECONDS,
    MAX_DEMO_SECONDS,
    MAX_INPUT_BYTES,
    AudioData,
    decode_audio_file,
    prepare_for_demo,
)
from app.v3_api import detect_message


def test_sessions_have_distinct_roots_and_cannot_escape(tmp_path: Path) -> None:
    from app.session_store import SessionStore

    store = SessionStore(tmp_path)
    first, second = store.create(), store.create()

    assert first.root != second.root
    assert first.path("marked.wav").parent == first.root
    assert first.path("nested/marked.wav").parent == first.root / "nested"

    with pytest.raises(ValueError):
        first.path("../outside.wav")
    with pytest.raises(ValueError):
        first.path(str(tmp_path / "outside.wav"))
    with pytest.raises(ValueError):
        first.path("")


def test_session_path_rejects_symlink_escape(tmp_path: Path) -> None:
    from app.session_store import SessionStore

    store = SessionStore(tmp_path)
    handle = store.create()
    outside = tmp_path / "outside"
    outside.mkdir()
    (handle.root / "linked").symlink_to(outside, target_is_directory=True)

    with pytest.raises(ValueError):
        handle.path("linked/secret.wav")


def test_expired_session_cleanup_is_scoped_to_session_root(tmp_path: Path) -> None:
    from app.session_store import SessionStore

    store = SessionStore(tmp_path, ttl_seconds=1)
    handle = store.create()
    handle.path("marker.txt").write_text("x", encoding="utf-8")
    unrelated = tmp_path / "unrelated.txt"
    unrelated.write_text("keep", encoding="utf-8")

    assert store.cleanup_expired(now=handle.created_at + 2) == 1
    assert not handle.root.exists()
    assert unrelated.read_text(encoding="utf-8") == "keep"
    assert tmp_path.exists()


def test_non_expired_and_manual_cleanup_are_scoped(tmp_path: Path) -> None:
    from app.session_store import SessionStore

    store = SessionStore(tmp_path, ttl_seconds=60)
    handle = store.create()
    sibling = store.create()

    assert store.cleanup_expired(now=handle.created_at + 1) == 0
    assert handle.root.exists()
    handle.cleanup()
    assert not handle.root.exists()
    assert sibling.root.exists()
    sibling.cleanup()
    sibling.cleanup()


def test_session_store_opens_only_live_opaque_session_ids(tmp_path: Path) -> None:
    from app.session_store import SessionStore

    store = SessionStore(tmp_path, ttl_seconds=60)
    handle = store.create()

    reopened = store.open(handle.root.name)

    assert reopened.root == handle.root
    assert reopened.created_at == handle.created_at

    with pytest.raises(ValueError):
        store.open("../outside")
    with pytest.raises(ValueError):
        store.open(str(handle.root))


def test_session_store_rejects_expired_session_ids(tmp_path: Path) -> None:
    from app.session_store import SessionStore

    store = SessionStore(tmp_path, ttl_seconds=1)
    handle = store.create()

    with pytest.raises(FileNotFoundError, match="expired"):
        store.open(handle.root.name, now=handle.created_at + 2)

    assert not handle.root.exists()


def test_session_ttl_requires_a_positive_integer(tmp_path: Path) -> None:
    from app.session_store import SessionStore

    with pytest.raises(ValueError):
        SessionStore(tmp_path, ttl_seconds=0)
    with pytest.raises(ValueError):
        SessionStore(tmp_path, ttl_seconds=-1)
    with pytest.raises(ValueError):
        SessionStore(tmp_path, ttl_seconds=True)


def test_audio_file_over_64_mib_is_rejected_before_decode(tmp_path: Path) -> None:
    oversized = tmp_path / "oversized.wav"
    with oversized.open("wb") as stream:
        stream.truncate(MAX_INPUT_BYTES + 1)

    with pytest.raises(ValueError, match="64 MiB"):
        decode_audio_file(oversized)


def test_decoded_audio_over_30_seconds_is_rejected_by_demo_boundary() -> None:
    audio = AudioData(np.zeros((MAX_DEMO_SECONDS + 1) * 48_000), 48_000)

    with pytest.raises(ValueError, match="30-second"):
        prepare_for_demo(audio, duration_seconds=6)
    with pytest.raises(ValueError, match="30-second"):
        detect_message(audio)


@pytest.mark.parametrize(
    "samples",
    [
        np.array([], dtype=np.float64),
        np.array([math.nan], dtype=np.float64),
        np.array([math.inf], dtype=np.float64),
    ],
)
def test_empty_or_non_finite_audio_has_no_detector_result(samples: np.ndarray) -> None:
    with pytest.raises(ValueError, match="non-empty, finite"):
        AudioData(samples, 48_000)


def test_unsupported_ffmpeg_input_has_readable_error_and_no_detector_result(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    invalid = tmp_path / "invalid.mp3"
    invalid.write_bytes(b"not an audio stream")
    monkeypatch.setattr("app.audio_io.shutil.which", lambda _: None)

    with pytest.raises(RuntimeError, match="FFmpeg is required"):
        decode_audio_file(invalid)


def test_audio_io_limits_remain_frozen() -> None:
    assert MAX_INPUT_BYTES == 64 * 1024 * 1024
    assert MAX_DEMO_SECONDS == 30
    assert FFMPEG_TIMEOUT_SECONDS == 120
