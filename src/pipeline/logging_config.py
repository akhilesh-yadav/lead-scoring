"""
Structured logging to stdout as an unbuffered event stream (12-factor XI).
Level controlled via LOG_LEVEL env var.
"""
import logging
import os
import sys


def setup_logging() -> logging.Logger:
    """Configure the pipeline logger. Level from LOG_LEVEL env var (default: INFO)."""
    logger = logging.getLogger("lead_scorer")

    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter(
            fmt="%(asctime)s | %(levelname)-5s | %(name)s.%(funcName)s | %(message)s",
            datefmt="%H:%M:%S",
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    level = os.environ.get("LOG_LEVEL", "INFO").upper()
    logger.setLevel(getattr(logging, level, logging.INFO))
    return logger


logger = setup_logging()
