"""Logging configuration for memcord.

CRITICAL: In STDIO mode, any output to stdout corrupts JSON-RPC messages.
All logging MUST go to stderr. This module ensures proper configuration.

Usage:
    from .logging_config import configure_logging, get_logger

    # In main entry point (server.py):
    configure_logging()

    # In any module:
    logger = get_logger(__name__)
    logger.debug("Debug message")  # Goes to stderr
    logger.warning("Warning message")  # Goes to stderr
"""

import logging
import os
import sys

# Default log level (can be overridden by MEMCORD_LOG_LEVEL env var)
DEFAULT_LOG_LEVEL = "WARNING"

# Suppress noisy third-party loggers
SUPPRESSED_LOGGERS = [
    "httpx",
    "httpcore",
    "urllib3",
    "asyncio",
    "aiofiles",
]


def configure_logging(
    level: str | None = None,
    format_string: str | None = None,
) -> logging.Logger:
    """Configure logging to use stderr only.

    This MUST be called early in the application startup to prevent
    any print statements or logging from corrupting STDIO communication.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
               Defaults to MEMCORD_LOG_LEVEL env var or WARNING.
        format_string: Custom format string for log messages.

    Returns:
        The configured memcord logger.
    """
    # Determine log level
    if level is None:
        level = os.getenv("MEMCORD_LOG_LEVEL", DEFAULT_LOG_LEVEL).upper()

    # Validate log level
    numeric_level = getattr(logging, level, None)
    if not isinstance(numeric_level, int):
        numeric_level = logging.WARNING

    # Create stderr handler (CRITICAL: never use stdout!)
    handler = logging.StreamHandler(sys.stderr)
    handler.setLevel(numeric_level)

    # Set format
    if format_string is None:
        format_string = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    formatter = logging.Formatter(format_string)
    handler.setFormatter(formatter)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)

    # Remove any existing handlers to avoid duplicates
    for existing_handler in root_logger.handlers[:]:
        root_logger.removeHandler(existing_handler)

    root_logger.addHandler(handler)

    # Configure memcord logger specifically
    memcord_logger = logging.getLogger("memcord")
    memcord_logger.setLevel(numeric_level)

    # Suppress noisy third-party loggers
    for logger_name in SUPPRESSED_LOGGERS:
        logging.getLogger(logger_name).setLevel(logging.WARNING)

    return memcord_logger


def get_logger(name: str) -> logging.Logger:
    """Get a logger for the specified module.

    Args:
        name: Module name (usually __name__).

    Returns:
        Logger instance configured to write to stderr.

    Example:
        logger = get_logger(__name__)
        logger.info("Processing request")
    """
    # Ensure name is under memcord namespace
    if not name.startswith("memcord"):
        name = f"memcord.{name}"
    return logging.getLogger(name)


def suppress_stdout():
    """Redirect any accidental stdout writes to stderr.

    WARNING: This is a safety measure for STDIO mode. It should be called
    after configure_logging() but before the MCP server starts.

    This helps catch any print() statements that weren't converted to logging.
    """

    class StdoutToStderr:
        """Wrapper that redirects writes to stderr."""

        def __init__(self):
            self._stderr = sys.stderr

        def write(self, text):
            # Only write non-empty content
            if text.strip():
                self._stderr.write(f"[STDOUT REDIRECT] {text}")

        def flush(self):
            self._stderr.flush()

    # Only suppress in production (not during testing)
    if os.getenv("MEMCORD_SUPPRESS_STDOUT", "false").lower() in ("true", "1", "yes"):
        sys.stdout = StdoutToStderr()


# Convenience function for quick setup
def setup_for_stdio():
    """Quick setup for STDIO mode.

    Combines configure_logging() with stdout suppression for safe STDIO operation.
    """
    configure_logging()
    suppress_stdout()
