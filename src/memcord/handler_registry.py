"""Handler registry for centralized tool dispatch.

This module provides a registry system that eliminates the need for
large if/elif chains when routing tool calls to their handlers.
"""

from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass
from typing import Any

from mcp.types import TextContent, Tool


@dataclass
class HandlerInfo:
    """Information about a registered handler."""

    name: str
    handler: Callable[..., Awaitable[Sequence[TextContent]]]
    category: str  # "basic", "advanced", "monitoring"
    description: str
    input_schema: dict[str, Any]
    requires_advanced: bool = False


class HandlerRegistry:
    """Registry for tool handlers with O(1) dispatch.

    Usage:
        registry = HandlerRegistry()

        @registry.register(
            "memcord_save",
            category="basic",
            description="Save chat text to memory slot",
            input_schema={...}
        )
        async def _handle_savemem(self, arguments):
            ...

        # Later, dispatch to handler:
        handler_info = registry.dispatch("memcord_save")
        if handler_info:
            result = await handler_info.handler(self, arguments)
    """

    def __init__(self):
        self._handlers: dict[str, HandlerInfo] = {}
        self._by_category: dict[str, list[str]] = {}

    def register(
        self,
        name: str,
        category: str,
        description: str,
        input_schema: dict[str, Any],
        requires_advanced: bool = False,
    ):
        """Decorator for handler registration.

        Args:
            name: Tool name (e.g., "memcord_save")
            category: Tool category ("basic", "advanced", "monitoring")
            description: Tool description for MCP
            input_schema: JSON schema for tool input
            requires_advanced: Whether this tool requires advanced mode enabled
        """

        def decorator(func: Callable[..., Awaitable[Sequence[TextContent]]]):
            self._handlers[name] = HandlerInfo(
                name=name,
                handler=func,
                category=category,
                description=description,
                input_schema=input_schema,
                requires_advanced=requires_advanced,
            )

            # Track by category
            if category not in self._by_category:
                self._by_category[category] = []
            self._by_category[category].append(name)

            return func

        return decorator

    def dispatch(self, name: str) -> HandlerInfo | None:
        """Get handler info by name. O(1) lookup."""
        return self._handlers.get(name)

    def get_all(self) -> dict[str, HandlerInfo]:
        """Get all registered handlers."""
        return self._handlers.copy()

    def get_by_category(self, category: str) -> list[HandlerInfo]:
        """Get all handlers in a category."""
        names = self._by_category.get(category, [])
        return [self._handlers[name] for name in names if name in self._handlers]

    def get_tools(self, include_advanced: bool = False) -> list[Tool]:
        """Generate Tool objects from registered handlers.

        Args:
            include_advanced: Whether to include tools that require advanced mode
        """
        tools = []
        for handler_info in self._handlers.values():
            if handler_info.requires_advanced and not include_advanced:
                continue
            tools.append(
                Tool(
                    name=handler_info.name,
                    description=handler_info.description,
                    inputSchema=handler_info.input_schema,
                )
            )
        return tools

    def is_advanced_tool(self, name: str) -> bool:
        """Check if a tool requires advanced mode."""
        handler_info = self._handlers.get(name)
        return handler_info.requires_advanced if handler_info else False

    def __contains__(self, name: str) -> bool:
        """Check if a handler is registered."""
        return name in self._handlers

    def __len__(self) -> int:
        """Return number of registered handlers."""
        return len(self._handlers)


# Global registry instance
handler_registry = HandlerRegistry()
