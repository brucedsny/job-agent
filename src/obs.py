"""Minimal logging. Level from JOB_AGENT_LOG env or Settings.log_level."""

from __future__ import annotations

import logging
import os

_CONFIGURED = False


def get_logger(level: str | None = None) -> logging.Logger:
    global _CONFIGURED
    logger = logging.getLogger("job_agent")
    if not _CONFIGURED:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
        logger.addHandler(handler)
        lvl = (os.getenv("JOB_AGENT_LOG") or level or "WARNING").upper()
        logger.setLevel(getattr(logging, lvl, logging.WARNING))
        _CONFIGURED = True
    return logger
