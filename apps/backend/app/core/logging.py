"""Logging bootstrap (Phase 0 shim).

Provide a single place to configure standard or structured logging. For now, this
does not alter the existing logging behavior; it's a placeholder for future setup.
"""

import logging


def configure_logging(level: int | str = "INFO") -> None:
    logging.basicConfig(level=level)
