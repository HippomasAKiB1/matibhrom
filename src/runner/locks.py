"""
Atomic lock file helpers for Matibhrom runner.
"""

import os
import time
from pathlib import Path
from typing import Any


class LockError(RuntimeError):
    """Raised when lock operations fail."""
    pass


def create_lock_atomic(lock_path: str | Path) -> int:
    """
    Create a lock file atomically using O_EXCL.

    Args:
        lock_path: Path to the lock file

    Returns:
        File descriptor of the lock file

    Raises:
        LockError: If lock already exists
    """
    lock_path = Path(lock_path)
    lock_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        fd = os.open(str(lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
        return fd
    except FileExistsError:
        raise LockError(f"Lock already exists: {lock_path}")


def release_lock(fd: int) -> None:
    """Release a lock by closing the file descriptor."""
    if fd >= 0:
        os.close(fd)


def remove_lock(lock_path: str | Path) -> None:
    """Remove a lock file."""
    lock_path = Path(lock_path)
    if lock_path.exists():
        lock_path.unlink()


def wait_for_lock(
    lock_path: str | Path,
    timeout: float = 3600,
    poll_interval: float = 1.0
) -> int:
    """
    Wait for a lock to be released, then acquire it.

    Args:
        lock_path: Path to the lock file
        timeout: Maximum time to wait in seconds
        poll_interval: How often to check

    Returns:
        File descriptor of acquired lock

    Raises:
        LockError: If timeout exceeded
    """
    start = time.time()
    while time.time() - start < timeout:
        try:
            return create_lock_atomic(lock_path)
        except LockError:
            time.sleep(poll_interval)
    raise LockError(f"Timeout waiting for lock: {lock_path}")


def write_lock_atomic(lock_path: str | Path, content: str) -> None:
    """
    Write content to a lock file atomically.

    Uses O_EXCL to ensure only one process can create the lock.
    """
    fd = create_lock_atomic(lock_path)
    try:
        os.write(fd, content.encode("utf-8"))
    finally:
        release_lock(fd)


def read_lock(lock_path: str | Path) -> str | None:
    """Read lock file content if it exists."""
    lock_path = Path(lock_path)
    if lock_path.exists():
        return lock_path.read_text(encoding="utf-8")
    return None


class FileLock:
    """Context manager for file locking."""

    def __init__(self, lock_path: str | Path, timeout: float = 3600):
        self.lock_path = Path(lock_path)
        self.timeout = timeout
        self.fd = -1

    def __enter__(self) -> "FileLock":
        self.fd = wait_for_lock(self.lock_path, self.timeout)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        release_lock(self.fd)
        self.fd = -1

    def write(self, content: str) -> None:
        """Write content to the lock file."""
        if self.fd >= 0:
            os.write(self.fd, content.encode("utf-8"))