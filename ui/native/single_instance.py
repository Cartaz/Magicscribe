"""Single-instance guard for the Linux desktop runtime.

The lock lives under XDG_RUNTIME_DIR when available and is held by the
process kernel-side with flock(2), so crashes release it automatically.
"""

from __future__ import annotations

import fcntl
import os
from pathlib import Path
from typing import TextIO

from config.constants import AppMeta, PathDefaults


def _default_lock_path() -> Path:
    runtime_dir = os.environ.get("XDG_RUNTIME_DIR")
    if runtime_dir:
        return Path(runtime_dir) / AppMeta.ORG_NAME / "runtime.lock"
    return PathDefaults.LOG_DIR / "runtime.lock"


class SingleInstanceGuard:
    """Owns a non-blocking process lock for one MagicScribe runtime."""

    def __init__(self, path: Path | None = None) -> None:
        self._path = path or _default_lock_path()
        self._handle: TextIO | None = None

    @property
    def path(self) -> Path:
        return self._path

    def acquire(self) -> bool:
        if self._handle is not None:
            return True

        self._path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        handle = self._path.open("a+", encoding="ascii")
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            handle.close()
            return False

        handle.seek(0)
        handle.truncate()
        handle.write(f"{os.getpid()}\n")
        handle.flush()
        self._handle = handle
        return True

    def release(self) -> None:
        handle = self._handle
        if handle is None:
            return
        self._handle = None
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        finally:
            handle.close()
