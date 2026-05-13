"""Structured logging setup for src."""

from __future__ import annotations

import logging
import sys
from pathlib import Path


def get_logger(name: str) -> logging.Logger:
    """Return a logger with console and file handlers configured."""
    logger = logging.getLogger(name)

    if logger.handlers:
        return logger

    from src.utils.config import settings

    level = getattr(logging, settings.TALAASH_LOG_LEVEL.upper(), logging.INFO)
    logger.setLevel(level)

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(level)
    logger.addHandler(console_handler)

    log_path = Path("src.log")
    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setFormatter(formatter)
    file_handler.setLevel(level)
    logger.addHandler(file_handler)

    logger.propagate = False
    return logger
