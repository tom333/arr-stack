"""structlog setup. JSON when not TTY (CronJob), pretty when TTY (dev)."""

from __future__ import annotations

import logging
import sys
from typing import Any

import structlog


def configure_logging(level: str = "INFO") -> None:
    """Configure structlog with TTY-aware rendering (D-07).

    JSON output for non-TTY (cluster CronJob log pipeline), pretty colored
    console output for TTY (local dev DX).
    """
    log_level = getattr(logging, level.upper(), logging.INFO)
    is_tty = sys.stderr.isatty()
    processors: list[Any] = [
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.dev.set_exc_info,
    ]
    if is_tty:
        processors.append(structlog.dev.ConsoleRenderer(colors=True))
    else:
        processors.append(structlog.processors.JSONRenderer())
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        cache_logger_on_first_use=True,
    )
