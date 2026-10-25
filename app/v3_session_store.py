"""Scoped temporary storage for the V3 local demo.

Each session gets its own temporary directory.  Path construction and cleanup
are deliberately constrained to that directory so a user-supplied filename
cannot escape into the repository or another session.
"""

from __future__ import annotations

import math
import shutil
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path


_SESSION_PREFIX = "blind_audio_v3_"
_CREATED_AT_FILE = ".session_created_at"


def _validate_ttl(ttl_seconds: int) -> int:
    if isinstance(ttl_seconds, bool) or not isinstance(ttl_seconds, int):
        raise ValueError("ttl_seconds must be a positive integer")
    if ttl_seconds <= 0:
        raise ValueError("ttl_seconds must be a positive integer")
    return ttl_seconds


def _validate_now(now: float | None) -> float:
    value = time.time() if now is None else now
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("now must be a finite timestamp")
    timestamp = float(value)
    if not math.isfinite(timestamp):
        raise ValueError("now must be a finite timestamp")
    return timestamp


def _safe_session_root(root: Path, store_root: Path) -> Path:
    """Validate that *root* is one direct, real session child of the store."""

    candidate = Path(root)
    if candidate.is_symlink():
        raise RuntimeError("session root must not be a symbolic link")
    resolved = candidate.resolve(strict=False)
    parent = store_root.resolve(strict=False)
    if resolved == parent or resolved.parent != parent:
        raise RuntimeError("session root is outside the session store")
    if not resolved.name.startswith(_SESSION_PREFIX):
        raise RuntimeError("invalid session root")
    return resolved


def _remove_session_root(root: Path, store_root: Path) -> bool:
    """Remove one validated session directory, returning whether it existed."""

    resolved = _safe_session_root(root, store_root)
    if not resolved.exists():
        return False
    if not resolved.is_dir():
        raise RuntimeError("session root is not a directory")
    shutil.rmtree(resolved)
    return True


@dataclass(frozen=True)
class SessionHandle:
    """A handle to one isolated V3 session directory."""

    root: Path
    created_at: float
    _store_root: Path = field(repr=False, compare=False)

    def path(self, name: str) -> Path:
        """Return a path inside this session, rejecting traversal and escapes."""

        if not isinstance(name, str) or not name or "\x00" in name:
            raise ValueError("session path name must be a non-empty string")
        relative = Path(name)
        if relative.is_absolute():
            raise ValueError("session path must be relative")

        session_root = self.root.resolve(strict=False)
        candidate = (self.root / relative).resolve(strict=False)
        if candidate == session_root:
            raise ValueError("session path must name a path inside the session")
        try:
            candidate.relative_to(session_root)
        except ValueError as error:
            raise ValueError("session path escapes the session root") from error
        return candidate

    def cleanup(self) -> None:
        """Remove only this session directory; repeated cleanup is harmless."""

        _remove_session_root(self.root, self._store_root)


class SessionStore:
    """Create and expire isolated temporary directories for demo sessions."""

    def __init__(self, root: Path | None = None, ttl_seconds: int = 3600) -> None:
        self.ttl_seconds = _validate_ttl(ttl_seconds)
        if root is None:
            self.root = Path(
                tempfile.mkdtemp(prefix="blind_audio_v3_store_")
            ).resolve()
        else:
            self.root = Path(root).resolve()
            self.root.mkdir(parents=True, exist_ok=True)
            if not self.root.is_dir():
                raise NotADirectoryError(f"session store is not a directory: {self.root}")

    def create(self) -> SessionHandle:
        """Create a unique session root below this store."""

        self.cleanup_expired()
        self.root.mkdir(parents=True, exist_ok=True)
        session_root = Path(
            tempfile.mkdtemp(prefix=_SESSION_PREFIX, dir=str(self.root))
        ).resolve()
        created_at = time.time()
        (session_root / _CREATED_AT_FILE).write_text(
            f"{created_at:.17g}\n", encoding="utf-8"
        )
        return SessionHandle(session_root, created_at, self.root)

    def open(self, session_id: str, now: float | None = None) -> SessionHandle:
        """Open one live session by its opaque direct-child identifier.

        The identifier is deliberately not a path. It is resolved only below
        this store, and expired or malformed sessions are rejected before a
        caller can access an artifact.
        """

        if (
            not isinstance(session_id, str)
            or not session_id
            or "\x00" in session_id
            or Path(session_id).name != session_id
            or session_id in {".", ".."}
            or not session_id.startswith(_SESSION_PREFIX)
        ):
            raise ValueError("invalid session id")
        timestamp = _validate_now(now)
        candidate = self.root / session_id
        resolved = _safe_session_root(candidate, self.root)
        if not resolved.exists() or not resolved.is_dir():
            raise FileNotFoundError("session not found")
        marker = resolved / _CREATED_AT_FILE
        if marker.is_symlink() or not marker.is_file():
            raise FileNotFoundError("session metadata not found")
        try:
            created_at = float(marker.read_text(encoding="utf-8").strip())
        except (OSError, ValueError) as error:
            raise FileNotFoundError("session metadata is invalid") from error
        if not math.isfinite(created_at):
            raise FileNotFoundError("session metadata is invalid")
        if timestamp - created_at >= self.ttl_seconds:
            _remove_session_root(resolved, self.root)
            raise FileNotFoundError("session expired")
        return SessionHandle(resolved, created_at, self.root)

    def cleanup_expired(self, now: float | None = None) -> int:
        """Remove expired session children and return the number removed."""

        timestamp = _validate_now(now)
        removed = 0
        for candidate in tuple(self.root.iterdir()):
            if not candidate.name.startswith(_SESSION_PREFIX):
                continue
            if candidate.is_symlink() or not candidate.is_dir():
                continue
            marker = candidate / _CREATED_AT_FILE
            if marker.is_symlink() or not marker.is_file():
                continue
            try:
                created_at = float(marker.read_text(encoding="utf-8").strip())
            except (OSError, ValueError):
                continue
            if not math.isfinite(created_at) or timestamp - created_at < self.ttl_seconds:
                continue
            if _remove_session_root(candidate, self.root):
                removed += 1
        return removed
