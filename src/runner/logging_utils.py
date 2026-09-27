"""
Logging utilities for Matibhrom runner.
"""

import logging
import sys
from pathlib import Path


def setup_logging(log_path: str | Path | None = None, level: int = logging.INFO) -> None:
    """Set up logging with file and console handlers."""
    logger = logging.getLogger("matibhrom")
    logger.setLevel(level)

    # Console handler
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(level)
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    console.setFormatter(formatter)
    logger.addHandler(console)

    # File handler
    if log_path:
        log_path = Path(log_path)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(str(log_path), encoding="utf-8")
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)


def get_logger(name: str = "matibhrom") -> logging.Logger:
    """Get a logger instance."""
    return logging.getLogger(name)