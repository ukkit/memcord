"""Response builder and error handling utilities for handlers.

Provides consistent response formatting and error handling decoration
for memcord tool handlers.
"""

import functools
import inspect
from collections.abc import Awaitable, Callable, Sequence
from typing import Any

from mcp.types import TextContent

from .errors import ErrorHandler, MemcordError


class ErrorResult(list):
    """Marker subclass for tool execution errors (MCP spec: isError=true).

    Behaves exactly like a list[TextContent] so existing code that indexes
    result[0].text continues to work.  The MCP call_tool boundary checks
    isinstance(result, ErrorResult) and wraps it in CallToolResult(isError=True)
    so the client can enable LLM self-correction per spec §tools/error-handling.
    """


class ResponseBuilder:
    """Builder for consistent MCP responses."""

    @staticmethod
    def success(message: str) -> list[TextContent]:
        return [TextContent(type="text", text=message)]

    @staticmethod
    def error(error: MemcordError) -> ErrorResult:
        return ErrorResult([TextContent(type="text", text=error.get_user_message())])

    @staticmethod
    def error_message(message: str) -> ErrorResult:
        return ErrorResult([TextContent(type="text", text=f"Error: {message}")])

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

    Catches exceptions and returns ErrorResult so the MCP boundary can set
    isError=True per spec §tools/error-handling.
    """

    def decorator(
        func: Callable[..., Awaitable[Sequence[TextContent]]],
    ) -> Callable[..., Awaitable[Sequence[TextContent] | ErrorResult]]:
        @functools.wraps(func)
        async def wrapper(self, arguments: dict[str, Any]) -> Sequence[TextContent] | ErrorResult:
            try:
                return await func(self, arguments)
            except MemcordError as e:
                return ResponseBuilder.error(e)
            except Exception as e:
                handler = error_handler or getattr(self, "error_handler", None)
                if handler:
                    wrapped_error = handler.handle_error(e, func.__name__, {"arguments": arguments})
                    return ResponseBuilder.error(wrapped_error)
                else:
                    return ResponseBuilder.error_message(f"{default_error_message}: {e}")

        return wrapper

    return decorator


def validate_required_args(*required_args: str):
    """Decorator to validate required arguments, returning ErrorResult on failure."""

    def decorator(
        func: Callable[..., Awaitable[Sequence[TextContent]]],
    ) -> Callable[..., Awaitable[Sequence[TextContent] | ErrorResult]]:
        @functools.wraps(func)
        async def wrapper(self, arguments: dict[str, Any]) -> Sequence[TextContent] | ErrorResult:
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
    """Decorator to validate that a slot is selected, returning ErrorResult on failure."""

    def decorator(
        func: Callable[..., Awaitable[Sequence[TextContent]]],
    ) -> Callable[..., Awaitable[Sequence[TextContent] | ErrorResult]]:
        @functools.wraps(func)
        async def wrapper(self, arguments: dict[str, Any]) -> Sequence[TextContent] | ErrorResult:
            if hasattr(self, "_resolve_slot"):
                if inspect.iscoroutinefunction(self._resolve_slot):
                    slot_name = await self._resolve_slot(arguments, slot_arg)
                else:
                    slot_name = self._resolve_slot(arguments, slot_arg)
            else:
                slot_name = arguments.get(slot_arg)

            if not slot_name:
                return ResponseBuilder.error_message(error_message)

            arguments[f"_resolved_{slot_arg}"] = slot_name
            return await func(self, arguments)

        return wrapper

    return decorator
