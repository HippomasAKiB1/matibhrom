"""
Atomic JSONL writer for Matibhrom.
Uses fcntl.flock for cross-process locking and a single background writer
thread per output file to serialize appends within this process.
"""

try:
    import fcntl
except ImportError:
    fcntl = None  # Windows compatibility fallback

import json
import queue as queue_mod
import threading
from pathlib import Path
from typing import Any

_writer_queues: dict[Path, "queue_mod.Queue"] = {}
_writer_threads: dict[Path, threading.Thread] = {}
_lock = threading.Lock()


def _writer_thread(path: Path, q: "queue_mod.Queue", corrupt_path: Path) -> None:
    """Background thread that writes to file under exclusive lock."""
    with open(path, "a", encoding="utf-8") as f:
        while True:
            item = q.get()
            if item is None:  # sentinel to stop
                q.task_done()
                break
            try:
                if fcntl is not None:
                    fcntl.flock(f.fileno(), fcntl.LOCK_EX)
                try:
                    f.write(json.dumps(item, ensure_ascii=False) + "\n")
                    f.flush()
                finally:
                    if fcntl is not None:
                        fcntl.flock(f.fileno(), fcntl.LOCK_UN)
            except Exception as exc:
                with open(corrupt_path, "a", encoding="utf-8") as cf:
                    cf.write(f"Write error: {exc}\nRecord: {item!r}\n")
            q.task_done()


def _start_writer(path: Path) -> None:
    """Start the background writer for a file if not already running."""
    with _lock:
        if path in _writer_threads:
            return
        q: "queue_mod.Queue" = queue_mod.Queue()
        corrupt_path = path.with_suffix(path.suffix + ".partial")
        thread = threading.Thread(
            target=_writer_thread, args=(path, q, corrupt_path), daemon=True
        )
        thread.start()
        _writer_queues[path] = q
        _writer_threads[path] = thread


def write_jsonl_atomic(path: str | Path, record: dict[str, Any]) -> None:
    """Write a record atomically to a JSONL file.

    Uses a single writer thread per file (serializing appends made by this
    process) plus an flock around each write (serializing appends made by
    other processes sharing the same file).
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path not in _writer_queues:
        _start_writer(path)
    q = _writer_queues[path]
    q.put(record)


def flush_writer(path: str | Path, timeout: float = 5.0) -> None:
    """Block until all queued writes for `path` have been flushed to disk."""
    path = Path(path)
    with _lock:
        q = _writer_queues.get(path)
    if q is not None:
        q.join()


def stop_all_writers(timeout: float = 5.0) -> None:
    """Stop all background writer threads. For testing/shutdown."""
    with _lock:
        items = list(_writer_queues.items())
        _writer_queues.clear()
        threads = dict(_writer_threads)
        _writer_threads.clear()
    for path, q in items:
        q.put(None)  # sentinel to stop
        thread = threads.get(path)
        if thread is not None:
            thread.join(timeout=timeout)
