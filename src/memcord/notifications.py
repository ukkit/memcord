"""MCP notification helpers for resource and tool list changes.

These helpers send MCP notifications when server state changes,
allowing clients to refresh their cached lists automatically.

All notifications are best-effort - failures are logged but
don't break the calling operation.
"""

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


async def send_resource_list_changed_safe() -> bool:
    """
    Send resource list changed notification if session is available.

    Best-effort: silently fails if no active session context.
    Call this after operations that add/remove memory slots:
    - create_or_get_slot() when creating new slot
    - delete_slot()
    - archive_slot()
    - restore_from_archive()

    Returns:
        True if notification was sent, False otherwise.
    """
    try:
        from mcp.shared.context import request_ctx

        ctx = request_ctx.get()
        if ctx and hasattr(ctx, "session") and ctx.session:
            await ctx.session.send_resource_list_changed()
            logger.debug("Sent resource_list_changed notification")
            return True
        else:
            logger.debug("No session available for resource_list_changed")
            return False
    except LookupError:
        # No active request context (e.g., during initialization or testing)
        logger.debug("No request context for resource_list_changed notification")
        return False
    except AttributeError as e:
        # Session doesn't support this notification method
        logger.debug(f"Session doesn't support resource_list_changed: {e}")
        return False
    except Exception as e:
        # Best effort - don't fail operations due to notification issues
        logger.warning(f"Failed to send resource_list_changed notification: {e}")
        return False


async def send_tool_list_changed_safe() -> bool:
    """
    Send tool list changed notification if session is available.

    Best-effort: silently fails if no active session context.
    Call this after operations that change available tools:
    - Toggling advanced tools on/off

    Returns:
        True if notification was sent, False otherwise.
    """
    try:
        from mcp.shared.context import request_ctx

        ctx = request_ctx.get()
        if ctx and hasattr(ctx, "session") and ctx.session:
            await ctx.session.send_tool_list_changed()
            logger.debug("Sent tool_list_changed notification")
            return True
        else:
            logger.debug("No session available for tool_list_changed")
            return False
    except LookupError:
        # No active request context
        logger.debug("No request context for tool_list_changed notification")
        return False
    except AttributeError as e:
        # Session doesn't support this notification method
        logger.debug(f"Session doesn't support tool_list_changed: {e}")
        return False
    except Exception as e:
        # Best effort - don't fail operations due to notification issues
        logger.warning(f"Failed to send tool_list_changed notification: {e}")
        return False
