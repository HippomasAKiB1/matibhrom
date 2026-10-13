"""
Atomic lock file helpers for Matibhrom runner.
"""

import json
import os
import time
from pathlib import Path
from typing import Any


class LockError(RuntimeError):
    """Raised when lock operations fail."""
    pass


def is_pid_alive(pid: int) -> bool:
    """Check if process with given PID is currently alive."""
    if pid <= 0:
        return False
    try:
        import psutil
        return psutil.pid_exists(pid)
    except ImportError:
        try:
            os.kill(pid, 0)
            return True
        except OSError:
            return False


def is_lock_stale(lock_path: str | Path, stale_timeout: float = 300.0) -> bool:
    """Return True if lock file is stale (owning process died or lock timed out)."""
    path = Path(lock_path)
    if not path.exists():
        return False
    try:
        content = path.read_text(encoding="utf-8").strip()
        if not content:
            # Empty lock file - check age
            age = time.time() - path.stat().st_mtime
            return age > 30.0
        data = json.loads(content)
        pid = data.get("pid")
        timestamp = data.get("timestamp", 0)
        if pid is not None and not is_pid_alive(pid):
            return True
        if timestamp and (time.time() - timestamp > stale_timeout):
            return True
        return False
    except Exception:
        try:
            return (time.time() - path.stat().st_mtime) > 30.0
        except OSError:
            return False


def clean_stale_locks(locks_dir: str | Path, stale_timeout: float = 300.0) -> int:
    """Remove any stale lock files in locks_dir. Returns number of removed locks."""
    p = Path(locks_dir)
    if not p.exists():
        return 0
    removed = 0
    for lock_file in p.glob("*.lock"):
        if is_lock_stale(lock_file, stale_timeout=stale_timeout):
            try:
                lock_file.unlink()
                removed += 1
            except OSError:
                pass
    return removed


def create_lock_atomic(lock_path: str | Path, stale_timeout: float = 300.0) -> int:
    """
    Create a lock file atomically using O_EXCL.
    Writes PID and timestamp to enable stale lock detection.
    If an existing lock is stale (process died or timed out), it is cleaned up.

    Args:
        lock_path: Path to the lock file
        stale_timeout: Seconds after which a lock is considered timed out

    Returns:
        File descriptor of the lock file

    Raises:
        LockError: If an active lock is already held
    """
    lock_path = Path(lock_path)
    lock_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        fd = os.open(str(lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
        payload = json.dumps({"pid": os.getpid(), "timestamp": time.time()}).encode("utf-8")
        os.write(fd, payload)
        return fd
    except FileExistsError:
        if is_lock_stale(lock_path, stale_timeout=stale_timeout):
            try:
                lock_path.unlink()
            except OSError:
                pass
            try:
                fd = os.open(str(lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
                payload = json.dumps({"pid": os.getpid(), "timestamp": time.time()}).encode("utf-8")
                os.write(fd, payload)
                return fd
            except FileExistsError:
                pass
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