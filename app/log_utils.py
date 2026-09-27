"""Rotating local logging for PetCare+.

Logs are kept under the D: drive storage root and rotated so they cannot grow
without bound. Sensitive user content is never written to the log.
"""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from app.config import LOG_FILE, LOG_DIR


def setup_logging(level: int = logging.INFO) -> logging.Logger:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("petcare")
    if logger.handlers:
        return logger
    logger.setLevel(level)
    logger.propagate = False

    try:
        handler = RotatingFileHandler(
            LOG_FILE, maxBytes=2_000_000, backupCount=5, encoding="utf-8"
        )
    except Exception:
        # If the log file cannot be created, fall back to stderr only.
        handler = logging.StreamHandler()

    fmt = logging.Formatter(
        "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    handler.setFormatter(fmt)
    logger.addHandler(handler)
    return logger


def get_logger(name: str = "petcare") -> logging.Logger:
    return logging.getLogger(name)
