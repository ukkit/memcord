"""Response builder and error handling utilities for handlers.

Provides consistent response formatting and error handling decoration
for memcord tool handlers.
"""

import functools
from collections.abc import Awaitable, Callable, Sequence
from typing import Any

from mcp.types import TextContent

from .errors import ErrorHandler, MemcordError


class ResponseBuilder:
    """Builder for consistent MCP responses."""

    @staticmethod
    def success(message: str) -> list[TextContent]:
        """Create a success response.

        Args:
            message: Success message text

        Returns:
            List containing TextContent with the message
        """
        return [TextContent(type="text", text=message)]

    @staticmethod
    def error(error: MemcordError) -> list[TextContent]:
        """Create an error response from a MemcordError.

        Args:
            error: MemcordError instance

        Returns:
            List containing TextContent with formatted error message
        """
        return [TextContent(type="text", text=error.get_user_message())]

    @staticmethod
    def error_message(message: str) -> list[TextContent]:
        """Create a simple error response.

        Args:
            message: Error message text

        Returns:
            List containing TextContent with error prefix
        """
        return [TextContent(type="text", text=f"Error: {message}")]

    @staticmethod
    def from_lines(lines: list[str]) -> list[TextContent]:
        """Create a response from a list of lines.

        Args:
            lines: List of text lines

        Returns:
            List containing TextContent with joined lines
        """
        return [TextContent(type="text", text="\n".join(lines))]

    @staticmethod
    def empty() -> list[TextContent]:
        """Create an empty response.

        Returns:
            Empty list
        """
        return []


def handle_errors(
    error_handler: ErrorHandler | None = None,
    default_error_message: str = "Operation failed",
):
    """Decorator to standardize error handling in handlers.

    This decorator catches exceptions and converts them to appropriate
    MCP responses using the MemcordError system.

    Args:
        error_handler: Optional ErrorHandler instance for enhanced error handling
        default_error_message: Default message for unhandled exceptions

    Usage:
        @handle_errors()
        async def _handle_something(self, arguments):
            # Handler code that may raise exceptions
            ...
    """

    def decorator(
        func: Callable[..., Awaitable[Sequence[TextContent]]],
    ) -> Callable[..., Awaitable[Sequence[TextContent]]]:
        @functools.wraps(func)
        async def wrapper(self, arguments: dict[str, Any]) -> Sequence[TextContent]:
            try:
                return await func(self, arguments)
            except MemcordError as e:
                # Known memcord errors - use their formatted message
                return ResponseBuilder.error(e)
            except Exception as e:
                # Unknown errors - wrap in MemcordError if handler available
                handler = error_handler or getattr(self, "error_handler", None)
                if handler:
                    wrapped_error = handler.handle_error(e, func.__name__, {"arguments": arguments})
                    return ResponseBuilder.error(wrapped_error)
                else:
                    return ResponseBuilder.error_message(f"{default_error_message}: {e}")

        return wrapper

    return decorator


def validate_required_args(*required_args: str):
    """Decorator to validate required arguments.

    Args:
        required_args: Names of required arguments

    Usage:
        @validate_required_args("slot_name", "content")
        async def _handle_something(self, arguments):
            ...
    """

    def decorator(
        func: Callable[..., Awaitable[Sequence[TextContent]]],
    ) -> Callable[..., Awaitable[Sequence[TextContent]]]:
        @functools.wraps(func)
        async def wrapper(self, arguments: dict[str, Any]) -> Sequence[TextContent]:
            missing = [arg for arg in required_args if not arguments.get(arg)]
            if missing:
                return ResponseBuilder.error_message(f"Missing required arguments: {', '.join(missing)}")
            return await func(self, arguments)

        return wrapper

    return decorator


def validate_slot_selected(
    slot_arg: str = "slot_name",
    error_message: str = "No memory slot selected. Use 'memname' first.",
):
    """Decorator to validate that a slot is selected.

    Uses _resolve_slot if available on the handler's class.

    Args:
        slot_arg: Name of the slot argument
        error_message: Error message if no slot is selected

    Usage:
        @validate_slot_selected()
        async def _handle_something(self, arguments):
            ...
    """

    def decorator(
        func: Callable[..., Awaitable[Sequence[TextContent]]],
    ) -> Callable[..., Awaitable[Sequence[TextContent]]]:
        @functools.wraps(func)
        async def wrapper(self, arguments: dict[str, Any]) -> Sequence[TextContent]:
            # Try to resolve slot using the class method if available
            if hasattr(self, "_resolve_slot"):
                slot_name = self._resolve_slot(arguments, slot_arg)
            else:
                slot_name = arguments.get(slot_arg)

            if not slot_name:
                return ResponseBuilder.error_message(error_message)

            # Add resolved slot to arguments for the handler
            arguments[f"_resolved_{slot_arg}"] = slot_name
            return await func(self, arguments)

        return wrapper

    return decorator
