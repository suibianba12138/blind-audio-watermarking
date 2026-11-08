"""Private, TTL-cleaned artifacts for the local V4 demo."""
from __future__ import annotations
import os
import shutil
import tempfile
import time
import uuid
from pathlib import Path


class ArtifactStore:
    def __init__(self, root: str | Path | None = None, ttl_seconds: int = 3600):
        self.root = Path(root or tempfile.mkdtemp(prefix="v4-p2-artifacts-")).resolve()
        self.root.mkdir(mode=0o700, parents=True, exist_ok=True)
        self.ttl_seconds = max(60, int(ttl_seconds))

    def new_job(self) -> Path:
        self.cleanup_expired()
        path = (self.root / uuid.uuid4().hex).resolve()
        path.mkdir(mode=0o700)
        return path

    def checked_path(self, job: str | Path, name: str) -> Path:
        base = Path(job).resolve()
        candidate = (base / name).resolve()
        if base.parent != self.root or candidate.parent != base or not name or name in (".", ".."):
            raise ValueError("artifact path is outside its private job")
        return candidate

    def cleanup_expired(self, now: float | None = None) -> int:
        self.root.mkdir(mode=0o700, parents=True, exist_ok=True)
        current = time.time() if now is None else now
        removed = 0
        for child in self.root.iterdir():
            if child.is_dir() and not child.is_symlink() and current - child.stat().st_mtime > self.ttl_seconds:
                shutil.rmtree(child)
                removed += 1
        return removed

    def cleanup(self) -> None:
        shutil.rmtree(self.root, ignore_errors=True)
