"""MCP progress notification support for long-running operations.

This module provides helpers for sending MCP progress notifications
during long-running operations like merge and import.

Usage:
    # In server handler
    from .mcp_progress import MCPProgressReporter, get_progress_token

    progress_token = get_progress_token(arguments)
    reporter = MCPProgressReporter(progress_token)

    # In operation
    for i, item in enumerate(items):
        await reporter.report(i + 1, len(items), f"Processing {item}")
        # ... process item ...

    await reporter.complete("Operation finished")
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


def get_progress_token(arguments: dict[str, Any]) -> str | int | None:
    """
    Extract progress token from tool call arguments.

    MCP clients can include _meta.progressToken in tool calls to
    receive progress notifications for long-running operations.

    Args:
        arguments: The tool call arguments dict

    Returns:
        The progress token if provided, None otherwise
    """
    meta = arguments.get("_meta", {})
    if isinstance(meta, dict):
        return meta.get("progressToken")
    return None


class MCPProgressReporter:
    """
    Reporter for sending MCP progress notifications.

    All operations are best-effort - failures are logged but don't
    break the calling operation.
    """

    def __init__(self, progress_token: str | int | None = None):
        """
        Initialize progress reporter.

        Args:
            progress_token: Token provided by client in tool call _meta.
                           If None, progress notifications are silently skipped.
        """
        self.progress_token = progress_token
        self._last_progress = -1  # Track to avoid duplicate notifications

    async def report(
        self,
        current: float,
        total: float,
        message: str = "",
    ) -> bool:
        """
        Send a progress notification.

        Args:
            current: Current progress value (e.g., items processed)
            total: Total items to process
            message: Optional status message

        Returns:
            True if notification was sent, False otherwise
        """
        if self.progress_token is None:
            return False

        # Avoid sending duplicate progress for same value
        if current == self._last_progress:
            return False
        self._last_progress = current

        try:
            from mcp.shared.context import request_ctx

            ctx = request_ctx.get()
            if ctx and hasattr(ctx, "session") and ctx.session:
                await ctx.session.send_progress_notification(
                    progress_token=self.progress_token,
                    progress=current,
                    total=total,
                    message=message if message else None,
                )
                logger.debug(f"Progress: {current}/{total} - {message}")
                return True
            else:
                logger.debug("No session available for progress notification")
                return False
        except LookupError:
            # No active request context
            logger.debug("No request context for progress notification")
            return False
        except AttributeError as e:
            # Session doesn't support progress notifications
            logger.debug(f"Session doesn't support progress notifications: {e}")
            return False
        except Exception as e:
            # Best effort - don't fail operations
            logger.warning(f"Failed to send progress notification: {e}")
            return False

    async def start(self, total: float, message: str = "Starting...") -> bool:
        """
        Send initial progress notification (0/total).

        Args:
            total: Total items to process
            message: Status message

        Returns:
            True if notification was sent
        """
        return await self.report(0, total, message)

    async def complete(self, message: str = "Complete") -> bool:
        """
        Send completion notification.

        Args:
            message: Completion message

        Returns:
            True if notification was sent
        """
        # Send 100% progress
        return await self.report(1, 1, message)

    async def increment(
        self,
        current: int,
        total: int,
        item_name: str = "",
    ) -> bool:
        """
        Report progress for item-based operations.

        Convenience method that formats a message like "Processing item 3/10: name"

        Args:
            current: Current item number (1-based)
            total: Total items
            item_name: Optional name of current item

        Returns:
            True if notification was sent
        """
        if item_name:
            message = f"Processing {current}/{total}: {item_name}"
        else:
            message = f"Processing {current}/{total}"
        return await self.report(current, total, message)


async def create_progress_callback(
    arguments: dict[str, Any],
) -> "ProgressCallback | None":
    """
    Create a progress callback function from tool arguments.

    This returns a simple async callback function that can be passed
    to operations that support progress reporting.

    Args:
        arguments: Tool call arguments (may contain _meta.progressToken)

    Returns:
        Async callback function (current, total, message) -> None, or None
    """
    progress_token = get_progress_token(arguments)
    if progress_token is None:
        return None

    reporter = MCPProgressReporter(progress_token)

    async def callback(current: float, total: float, message: str = "") -> None:
        await reporter.report(current, total, message)

    return callback


# Type alias for progress callback
ProgressCallback = Any  # Actually: Callable[[float, float, str], Awaitable[None]]
