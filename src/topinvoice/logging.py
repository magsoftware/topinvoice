from __future__ import annotations

import logging

LOGGER_NAME = "topinvoice"


def get_logger() -> logging.Logger:
    """Return the application logger instance.

    Returns:
        Logger configured for the application namespace.
    """
    return logging.getLogger(LOGGER_NAME)


def configure_logging() -> None:
    """Configure basic logging for CLI execution."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
