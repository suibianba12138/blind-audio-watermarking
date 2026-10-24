from __future__ import annotations

import pytest
from app.session_store import SessionStore


def test_session_tokens_expire_and_paths_are_not_client_selected(tmp_path):
    ticks = [0.0]
    store = SessionStore(ttl_seconds=10, max_sessions=2, sweep_seconds=1,
                         clock=lambda: ticks[0], start_sweeper=False)
    try:
        first = store.create()
        with store.use(first) as session:
            output = session.directory / "watermarked.wav"
            output.write_bytes(b"synthetic test only")
            ticks[0] = 25.0
            assert store.cleanup_expired() == 0
            assert output.exists()
        assert store.cleanup_expired() == 0
        ticks[0] = 36.0
        assert store.cleanup_expired() == 1
        assert not output.exists()
        with pytest.raises(ValueError):
            with store.use(first):
                pass
        with pytest.raises(ValueError):
            with store.use("/etc/passwd"):
                pass
    finally:
        root = store._root
        store.close()
        assert not root.exists()


def test_session_limit_reclaims_idle_sessions():
    store = SessionStore(ttl_seconds=600, max_sessions=1,
                         start_sweeper=False)
    try:
        first = store.create()
        with pytest.raises(RuntimeError):
            store.create()
        store.discard(first)
        assert store.create() != first
    finally:
        store.close()
