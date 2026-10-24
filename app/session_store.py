"""Private, bounded, expiring files for the public Gradio audio demo."""
from __future__ import annotations

import atexit
import secrets
import shutil
import tempfile
import threading
import time
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterator


@dataclass
class SessionFiles:
    directory: Path
    created_at: float
    last_touch: float
    in_use: int = 0

    @property
    def marked(self) -> Path:
        return self.directory / "watermarked.wav"

    @property
    def received(self) -> Path:
        return self.directory / "compressed_128k_decoded.wav"


class SessionStore:
    """Opaque tokens prevent users from passing filesystem paths as state.

    Cleanup is restricted to directories this object itself created. The TTL
    is based on last use but never deletes an active in-flight operation.
    """

    def __init__(
        self,
        *,
        ttl_seconds: int = 1200,
        max_sessions: int = 8,
        sweep_seconds: int = 60,
        clock: Callable[[], float] = time.monotonic,
        start_sweeper: bool = True,
    ) -> None:
        if min(ttl_seconds, max_sessions, sweep_seconds) <= 0:
            raise ValueError("session limits must be positive")
        self._clock = clock
        self._ttl = ttl_seconds
        self._limit = max_sessions
        self._sweep_seconds = sweep_seconds
        self._root = Path(tempfile.mkdtemp(prefix="blind_audio_sessions_"))
        self._root.chmod(0o700)
        self._records: dict[str, SessionFiles] = {}
        self._lock = threading.RLock()
        self._stop = threading.Event()
        self._worker: threading.Thread | None = None
        if start_sweeper:
            self._worker = threading.Thread(target=self._background_cleanup, daemon=True)
            self._worker.start()
        atexit.register(self.close)

    def _background_cleanup(self) -> None:
        while not self._stop.wait(self._sweep_seconds):
            self.cleanup_expired()

    def _remove_locked(self, token: str) -> None:
        record = self._records.pop(token, None)
        if record is not None:
            shutil.rmtree(record.directory, ignore_errors=True)

    def cleanup_expired(self) -> int:
        """Reclaim idle audio regardless of whether browser tabs stay open."""
        with self._lock:
            now = self._clock()
            expired = [token for token, r in self._records.items()
                       if r.in_use == 0 and now - r.last_touch >= self._ttl]
            for token in expired:
                self._remove_locked(token)
            return len(expired)

    def create(self) -> str:
        with self._lock:
            self.cleanup_expired()
            if len(self._records) >= self._limit:
                raise RuntimeError("demo is busy; retry after sessions expire")
            token = secrets.token_urlsafe(24)
            while token in self._records:
                token = secrets.token_urlsafe(24)
            folder = Path(tempfile.mkdtemp(prefix="run_", dir=self._root))
            folder.chmod(0o700)
            now = self._clock()
            self._records[token] = SessionFiles(folder, now, now)
            return token

    @contextmanager
    def use(self, token: str) -> Iterator[SessionFiles]:
        with self._lock:
            self.cleanup_expired()
            record = self._records.get(token)
            if record is None:
                raise ValueError("session expired or invalid; embed again")
            record.in_use += 1
            record.last_touch = self._clock()
        try:
            yield record
        finally:
            with self._lock:
                record.in_use -= 1
                record.last_touch = self._clock()

    def discard(self, token: str | None) -> None:
        if not token:
            return
        with self._lock:
            record = self._records.get(token)
            if record is not None and record.in_use == 0:
                self._remove_locked(token)

    def close(self) -> None:
        self._stop.set()
        with self._lock:
            for token in list(self._records):
                self._remove_locked(token)
            if self._root.exists():
                try:
                    self._root.rmdir()
                except OSError:
                    pass
