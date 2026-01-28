"""Main MCP server implementation for chat memory management.

NAMING CONVENTION:
All tool names MUST follow the "memcord_" prefix pattern:
- memcord_name, memcord_save, memcord_read, etc.
- Use underscore_case for multi-word tool names
- Examples: memcord_save_progress, memcord_list_tags

When adding new tools:
1. Name must start with "memcord_"
2. Use descriptive action words after the prefix
3. Update both the tool definition AND the call_tool handler
4. Update all documentation files to include the new tool
"""

import asyncio
import functools
import os
import secrets
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any, cast

from mcp.server import Server
from mcp.types import Resource, TextContent, Tool

from .errors import (
    ErrorHandler,
    MemcordError,
    OperationTimeoutError,
)
from .models import SearchQuery
from .response_builder import handle_errors
from .security import SecurityMiddleware
from .status_monitoring import StatusMonitoringSystem
from .storage import StorageManager


def with_timeout_check(operation_id_key: str = "operation_id"):
    """Decorator to add timeout checking to async methods."""

    def decorator(func):
        @functools.wraps(func)
        async def wrapper(self, *args, **kwargs):
            # Extract operation_id from kwargs or generate one
            operation_id = kwargs.get(operation_id_key) or secrets.token_hex(8)

            # Check timeout if operation is being tracked
            if hasattr(self, "security") and operation_id in self.security.timeout_manager.active_operations:
                timed_out, error_msg = self.security.timeout_manager.check_timeout(operation_id)
                if timed_out:
                    raise OperationTimeoutError(
                        error_msg or f"Operation {func.__name__} timed out", operation=func.__name__
                    )

            return await func(self, *args, **kwargs)

        return wrapper

    return decorator


class ChatMemoryServer:
    """MCP server for chat memory management."""

    # Error message constants (eliminate duplication)
    ERROR_NO_SLOT_SELECTED = "Error: No slot selected. Use memcord_name <slot> or memcord_use <slot> first."
    ERROR_EMPTY_CHAT_TEXT = "Error: Chat text cannot be empty"
    ERROR_EMPTY_SLOT_NAME = "Error: Slot name cannot be empty"
    ERROR_EMPTY_QUERY = "Error: Search query cannot be empty"
    ERROR_EMPTY_QUESTION = "Error: Question cannot be empty"
    ERROR_EMPTY_SOURCE = "Error: Source cannot be empty"
    WARNING_ZERO_MODE = (
        "⚠️ Zero mode active - content NOT saved.\n\n"
        "💡 To save this content:\n"
        "1. Use 'memcord_name [slot_name]' to select a memory slot\n"
        "2. Then retry your save command"
    )
    WARNING_ZERO_MODE_PROGRESS = (
        "⚠️ Zero mode active - progress NOT saved.\n\n"
        "💡 To save this progress:\n"
        "1. Use 'memcord_name [slot_name]' to select a memory slot\n"
        "2. Then retry your save progress command"
    )

    def __init__(
        self,
        memory_dir: str = "memory_slots",
        shared_dir: str = "shared_memories",
        enable_advanced_tools: bool | None = None,
    ):
        self.storage = StorageManager(memory_dir, shared_dir)
        self.app = Server("chat-memory")

        # Security and error handling
        self.security = SecurityMiddleware()
        self.error_handler = ErrorHandler()

        # Determine if advanced tools should be enabled
        if enable_advanced_tools is None:
            # Check environment variable
            env_value = os.getenv("MEMCORD_ENABLE_ADVANCED", "false").lower()
            self.enable_advanced_tools = env_value in ("true", "1", "yes", "on")
        else:
            self.enable_advanced_tools = enable_advanced_tools

        # Status monitoring system
        self.status_monitor = StatusMonitoringSystem(storage_manager=self.storage, data_dir=memory_dir)

        # Pre-populate tool cache for faster first list_tools() call
        self._tool_cache = self._get_basic_tools()
        if self.enable_advanced_tools:
            self._tool_cache.extend(self._get_advanced_tools())

        # Pre-load summarizer for faster first save_progress call
        from .summarizer import TextSummarizer

        self._summarizer = TextSummarizer()
        self._query_processor = None
        self._importer = None
        self._merger = None
        self._merge_service = None
        self._monitoring_service = None
        self._compression_service = None
        self._archive_service = None
        self._import_service = None
        self._select_entry_service = None

        self._setup_handlers()

        # Build handler dispatch map for O(1) lookup
        self._handler_map = self._build_handler_map()

    def _build_handler_map(self) -> dict[str, tuple[Callable[..., Any], bool]]:
        """Build handler dispatch map.

        Returns:
            Dict mapping tool name to (handler_method, requires_advanced) tuple
        """
        return {
            # Basic tools (always available)
            "memcord_name": (self._handle_memname, False),
            "memcord_use": (self._handle_memuse, False),
            "memcord_save": (self._handle_savemem, False),
            "memcord_read": (self._handle_readmem, False),
            "memcord_save_progress": (self._handle_saveprogress, False),
            "memcord_list": (self._handle_listmems, False),
            "memcord_ping": (self._handle_ping, False),
            "memcord_search": (self._handle_searchmem, False),
            "memcord_query": (self._handle_querymem, False),
            "memcord_zero": (self._handle_zeromem, False),
            "memcord_close": (self._handle_closemem, False),
            "memcord_select_entry": (self._handle_select_entry, False),
            # Project Binding tools
            "memcord_init": (self._handle_bind, False),
            "memcord_unbind": (self._handle_unbind, False),
            # Status & Monitoring tools
            "memcord_status": (self._handle_status, False),
            "memcord_metrics": (self._handle_metrics, False),
            "memcord_logs": (self._handle_logs, False),
            "memcord_diagnostics": (self._handle_diagnostics, False),
            # Advanced tools (require MEMCORD_ENABLE_ADVANCED=true)
            "memcord_tag": (self._handle_tagmem, True),
            "memcord_list_tags": (self._handle_listtags, True),
            "memcord_group": (self._handle_groupmem, True),
            "memcord_import": (self._handle_importmem, True),
            "memcord_merge": (self._handle_mergemem, True),
            "memcord_archive": (self._handle_archivemem, True),
            "memcord_export": (self._handle_exportmem, True),
            "memcord_share": (self._handle_sharemem, True),
            "memcord_compress": (self._handle_compressmem, True),
        }

    async def _dispatch_handler(self, name: str, arguments: dict[str, Any]) -> Sequence[TextContent]:
        """Dispatch to handler using O(1) lookup.

        Args:
            name: Tool name
            arguments: Tool arguments

        Returns:
            Handler result or error message
        """
        handler_entry = self._handler_map.get(name)

        if handler_entry is None:
            return [TextContent(type="text", text=f"Error: Unknown tool: {name}")]

        handler, requires_advanced = handler_entry

        if requires_advanced and not self.enable_advanced_tools:
            return [
                TextContent(
                    type="text",
                    text=(
                        f"Error: Advanced tool '{name}' is not enabled. "
                        "Set MEMCORD_ENABLE_ADVANCED=true to enable advanced features."
                    ),
                )
            ]

        return cast(Sequence[TextContent], await handler(arguments))

    @property
    def summarizer(self):
        """Lazy-loaded TextSummarizer instance."""
        if self._summarizer is None:
            from .summarizer import TextSummarizer

            self._summarizer = TextSummarizer()
        return self._summarizer

    @property
    def query_processor(self):
        """Lazy-loaded SimpleQueryProcessor instance."""
        if self._query_processor is None:
            from .query import SimpleQueryProcessor

            self._query_processor = SimpleQueryProcessor(self.storage._search_engine)
        return self._query_processor

    @property
    def importer(self):
        """Lazy-loaded ContentImporter instance."""
        if self._importer is None:
            from .importer import ContentImporter

            self._importer = ContentImporter()
        return self._importer

    @property
    def merger(self):
        """Lazy-loaded MemorySlotMerger instance."""
        if self._merger is None:
            from .merger import MemorySlotMerger

            self._merger = MemorySlotMerger()
        return self._merger

    @property
    def merge_service(self):
        """Lazy-loaded MergeService instance."""
        if self._merge_service is None:
            from .services import MergeService

            self._merge_service = MergeService(self.storage, self.merger)
        return self._merge_service

    @property
    def monitoring_service(self):
        """Lazy-loaded MonitoringService instance."""
        if self._monitoring_service is None:
            from .services import MonitoringService

            self._monitoring_service = MonitoringService(self.status_monitor)
        return self._monitoring_service

    @property
    def compression_service(self):
        """Lazy-loaded CompressionService instance."""
        if self._compression_service is None:
            from .services import CompressionService

            self._compression_service = CompressionService(self.storage)
        return self._compression_service

    @property
    def archive_service(self):
        """Lazy-loaded ArchiveService instance."""
        if self._archive_service is None:
            from .services import ArchiveService

            self._archive_service = ArchiveService(self.storage)
        return self._archive_service

    @property
    def import_service(self):
        """Lazy-loaded ImportService instance."""
        if self._import_service is None:
            from .services import ImportService

            self._import_service = ImportService(self.storage, self.importer)
        return self._import_service

    @property
    def select_entry_service(self):
        """Lazy-loaded SelectEntryService instance."""
        if self._select_entry_service is None:
            from .services import SelectEntryService

            self._select_entry_service = SelectEntryService(self.storage)
        return self._select_entry_service

    def _detect_project_slot(self) -> str | None:
        """Check for .memcord file in current working directory.

        Returns the slot name from the .memcord file if it exists,
        otherwise returns None.
        """
        memcord_file = Path.cwd() / ".memcord"
        if memcord_file.exists():
            try:
                slot_name = memcord_file.read_text().strip()
                if slot_name:
                    return slot_name
            except OSError:
                pass
        return None

    def _resolve_slot(self, arguments: dict[str, Any], key: str = "slot_name") -> str | None:
        """Resolve slot name from arguments, current slot, or project binding.

        Priority order:
        1. Explicit slot_name in arguments
        2. Currently active slot (via memcord_use/memcord_name)
        3. Project binding (.memcord file in cwd)
        """
        return arguments.get(key) or self.storage.get_current_slot() or self._detect_project_slot()

    def _resolve_slot_for_write(self, arguments: dict[str, Any], key: str = "slot_name") -> str | None:
        """Resolve slot for write operations (no .memcord fallback).

        Priority:
        1. Explicit slot_name in arguments
        2. Currently active slot (via memcord_use/memcord_name)

        Returns None if no slot selected (caller should return error).
        This prevents accidental writes to wrong slots when MCP server
        runs from a different directory than the user's project.
        """
        return arguments.get(key) or self.storage.get_current_slot()

    async def call_tool_direct(self, name: str, arguments: dict[str, Any]) -> Sequence[TextContent]:
        """Direct tool calling method for testing purposes."""
        try:
            return await self._dispatch_handler(name, arguments)
        except Exception as e:
            return [TextContent(type="text", text=f"Error: {str(e)}")]

    async def list_tools_direct(self) -> list[Tool]:
        """Direct tools listing method for testing purposes."""
        if self._tool_cache is None:
            tools = self._get_basic_tools()
            if self.enable_advanced_tools:
                tools.extend(self._get_advanced_tools())
            self._tool_cache = tools
        return self._tool_cache

    async def list_resources_direct(self) -> list[Resource]:
        """Direct resources listing method for testing purposes."""
        resources = []
        slots_info = await self.storage.list_memory_slots()

        for slot_info in slots_info:
            slot_name = slot_info["name"]
            for fmt in ["md", "txt", "json"]:
                resources.append(
                    Resource(
                        uri=f"memory://{slot_name}.{fmt}",  # type: ignore[arg-type]
                        name=f"{slot_name} ({fmt.upper()})",
                        description=f"Memory slot {slot_name} in {fmt.upper()} format",
                        mimeType=f"text/{fmt}" if fmt in ["txt", "md"] else f"application/{fmt}",
                    )
                )

        return resources

    async def read_resource_direct(self, uri: str) -> str:
        """Direct resource reading method for testing purposes."""
        # Parse URI: memory://slot_name.format
        if not uri.startswith("memory://"):
            raise ValueError("Invalid URI scheme")

        path_part = uri[9:]  # Remove "memory://"
        if "." not in path_part:
            raise ValueError("Invalid URI format")

        slot_name, format_ext = path_part.rsplit(".", 1)

        # Check if slot exists
        slot = await self.storage._load_slot(slot_name)
        if not slot:
            raise ValueError(f"Memory slot '{slot_name}' not found")

        # Check if format is valid
        if format_ext not in ["md", "txt", "json"]:
            raise ValueError(f"Unsupported format: {format_ext}")

        # Generate content in requested format
        if format_ext == "md":
            return self.storage._format_as_markdown(slot)
        elif format_ext == "txt":
            return self.storage._format_as_text(slot)
        elif format_ext == "json":
            return self.storage._format_as_json(slot)
        else:
            raise ValueError(f"Unsupported format: {format_ext}")

    def _get_basic_tools(self) -> list[Tool]:
        """Get the list of basic tools (always available)."""
        return [
            # Core Tools
            Tool(
                name="memcord_name",
                description="Set or create a named memory slot",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "slot_name": {"type": "string", "description": "Name of the memory slot to create or select"}
                    },
                    "required": ["slot_name"],
                },
            ),
            Tool(
                name="memcord_use",
                description="Activate an existing memory slot (does not create new slots)",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "slot_name": {"type": "string", "description": "Name of the existing memory slot to activate"}
                    },
                    "required": ["slot_name"],
                },
            ),
            Tool(
                name="memcord_save",
                description="Save chat text to memory slot (overwrites existing content)",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "chat_text": {"type": "string", "description": "Chat text to save"},
                        "slot_name": {
                            "type": "string",
                            "description": "Memory slot name (optional, uses current slot if not specified)",
                        },
                    },
                    "required": ["chat_text"],
                },
            ),
            Tool(
                name="memcord_read",
                description="Retrieve full content from memory slot",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "slot_name": {
                            "type": "string",
                            "description": "Memory slot name (optional, uses current slot if not specified)",
                        }
                    },
                },
            ),
            Tool(
                name="memcord_save_progress",
                description="Generate summary and append to memory slot",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "chat_text": {"type": "string", "description": "Chat text to summarize and save"},
                        "slot_name": {
                            "type": "string",
                            "description": "Memory slot name (optional, uses current slot if not specified)",
                        },
                        "compression_ratio": {
                            "type": "number",
                            "description": "Target compression ratio (0.1 = 10%, default 0.15)",
                            "minimum": 0.05,
                            "maximum": 0.5,
                            "default": 0.15,
                        },
                    },
                    "required": ["chat_text"],
                },
            ),
            Tool(
                name="memcord_list",
                description="List all available memory slots with metadata",
                inputSchema={"type": "object", "properties": {}},
            ),
            Tool(
                name="memcord_ping",
                description=(
                    "Lightweight health check for server warm-up. "
                    "Returns minimal response to confirm server is running."
                ),
                inputSchema={"type": "object", "properties": {}},
            ),
            # Search & Intelligence Tools
            Tool(
                name="memcord_search",
                description="Search across all memory slots with advanced filtering",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search query with optional Boolean operators (AND, OR, NOT)",
                        },
                        "include_tags": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Include slots with these tags",
                            "default": [],
                        },
                        "exclude_tags": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Exclude slots with these tags",
                            "default": [],
                        },
                        "max_results": {
                            "type": "integer",
                            "description": "Maximum number of results",
                            "default": 20,
                            "minimum": 1,
                            "maximum": 100,
                        },
                        "case_sensitive": {
                            "type": "boolean",
                            "description": "Whether search is case sensitive",
                            "default": False,
                        },
                    },
                    "required": ["query"],
                },
            ),
            Tool(
                name="memcord_query",
                description="Ask natural language questions about your memory contents",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "question": {"type": "string", "description": "Natural language question about your memories"},
                        "max_results": {
                            "type": "integer",
                            "description": "Maximum number of results to consider",
                            "default": 5,
                            "minimum": 1,
                            "maximum": 20,
                        },
                    },
                    "required": ["question"],
                },
            ),
            Tool(
                name="memcord_zero",
                description="Activate zero mode - no memory will be saved until switched to another slot",
                inputSchema={"type": "object", "properties": {}},
            ),
            Tool(
                name="memcord_close",
                description=(
                    "Deactivate the current memory slot. "
                    "Use before ending a session to prevent cross-project contamination."
                ),
                inputSchema={"type": "object", "properties": {}, "required": []},
            ),
            Tool(
                name="memcord_select_entry",
                description=(
                    "Select and retrieve a specific memory entry by timestamp, "
                    "relative time, or index within a memory slot"
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "slot_name": {
                            "type": "string",
                            "description": "Target memory slot (optional, uses current if not specified)",
                        },
                        "timestamp": {
                            "type": "string",
                            "description": "Exact timestamp in ISO format (e.g., '2025-07-21T17:30:00')",
                        },
                        "relative_time": {
                            "type": "string",
                            "description": "Human descriptions like 'latest', 'oldest', '2 hours ago', 'yesterday'",
                        },
                        "entry_index": {
                            "type": "integer",
                            "description": "Direct numeric index (0-based, negative for reverse indexing)",
                        },
                        "entry_type": {
                            "type": "string",
                            "enum": ["manual_save", "auto_summary"],
                            "description": "Filter by entry type",
                        },
                        "show_context": {
                            "type": "boolean",
                            "default": True,
                            "description": "Include timeline position and adjacent entries info",
                        },
                    },
                },
            ),
            Tool(
                name="memcord_merge",
                description="Merge multiple memory slots into one with duplicate detection",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "source_slots": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of memory slot names to merge",
                            "minItems": 2,
                        },
                        "target_slot": {"type": "string", "description": "Name for the merged memory slot"},
                        "action": {
                            "type": "string",
                            "enum": ["preview", "merge"],
                            "description": "Action to perform: 'preview' to see merge preview, 'merge' to execute",
                            "default": "preview",
                        },
                        "similarity_threshold": {
                            "type": "number",
                            "minimum": 0.0,
                            "maximum": 1.0,
                            "description": "Threshold for duplicate detection (0.0-1.0, default 0.8)",
                            "default": 0.8,
                        },
                        "delete_sources": {
                            "type": "boolean",
                            "description": "Whether to delete source slots after successful merge",
                            "default": False,
                        },
                    },
                    "required": ["source_slots", "target_slot"],
                },
            ),
            # Status & Monitoring Tools
            Tool(
                name="memcord_status",
                description="Get current system health status and overview",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "include_details": {
                            "type": "boolean",
                            "description": "Include detailed health check results",
                            "default": False,
                        }
                    },
                },
            ),
            Tool(
                name="memcord_metrics",
                description="Get performance metrics and system statistics",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "metric_name": {
                            "type": "string",
                            "description": "Specific metric name to retrieve (optional, shows all if not specified)",
                        },
                        "hours": {
                            "type": "integer",
                            "description": "Number of hours of data to retrieve",
                            "default": 1,
                            "minimum": 1,
                            "maximum": 168,
                        },
                    },
                },
            ),
            Tool(
                name="memcord_logs",
                description="Get operation execution logs and history",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "tool_name": {"type": "string", "description": "Filter logs by specific tool name"},
                        "status": {
                            "type": "string",
                            "description": "Filter logs by operation status",
                            "enum": ["started", "completed", "failed", "timeout"],
                        },
                        "hours": {
                            "type": "integer",
                            "description": "Number of hours of logs to retrieve",
                            "default": 1,
                            "minimum": 1,
                            "maximum": 168,
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of log entries to return",
                            "default": 100,
                            "minimum": 1,
                            "maximum": 1000,
                        },
                    },
                },
            ),
            Tool(
                name="memcord_diagnostics",
                description="Run comprehensive system diagnostics and generate health report",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "check_type": {
                            "type": "string",
                            "description": "Type of diagnostic check to run",
                            "enum": ["health", "performance", "full_report"],
                            "default": "health",
                        }
                    },
                },
            ),
            # Project Binding Tools
            Tool(
                name="memcord_init",
                description=(
                    "Initialize memcord for a project directory by binding it to a memory slot. "
                    "Creates .memcord file in the project."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "project_path": {
                            "type": "string",
                            "description": "Path to the project directory to bind",
                        },
                        "slot_name": {
                            "type": "string",
                            "description": "Memory slot name to bind (optional, uses directory name if not specified)",
                        },
                    },
                    "required": ["project_path"],
                },
            ),
            Tool(
                name="memcord_unbind",
                description="Remove .memcord binding from a project directory",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "project_path": {
                            "type": "string",
                            "description": "Path to the project directory",
                        },
                    },
                    "required": ["project_path"],
                },
            ),
        ]

    def _get_advanced_tools(self) -> list[Tool]:
        """Get the list of advanced tools (optional)."""
        return [
            # Organization Tools
            Tool(
                name="memcord_tag",
                description="Add or remove tags from a memory slot",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "slot_name": {
                            "type": "string",
                            "description": "Memory slot name (optional, uses current slot if not specified)",
                        },
                        "action": {
                            "type": "string",
                            "enum": ["add", "remove", "list"],
                            "description": "Action to perform with tags",
                        },
                        "tags": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Tags to add or remove",
                            "default": [],
                        },
                    },
                    "required": ["action"],
                },
            ),
            Tool(
                name="memcord_list_tags",
                description="List all tags used across memory slots",
                inputSchema={"type": "object", "properties": {}},
            ),
            Tool(
                name="memcord_group",
                description="Manage memory slot groups/folders",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "slot_name": {
                            "type": "string",
                            "description": "Memory slot name (optional, uses current slot if not specified)",
                        },
                        "action": {
                            "type": "string",
                            "enum": ["set", "remove", "list"],
                            "description": "Action to perform with groups",
                        },
                        "group_path": {"type": "string", "description": "Group path (e.g., 'project/client/meetings')"},
                    },
                    "required": ["action"],
                },
            ),
            # Import & Integration Tools
            Tool(
                name="memcord_import",
                description="Import content from various sources into memory slots",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "source": {"type": "string", "description": "Source file path, URL, or '-' for clipboard"},
                        "slot_name": {"type": "string", "description": "Target memory slot name"},
                        "source_type": {
                            "type": "string",
                            "enum": ["auto", "text", "pdf", "url", "csv", "json"],
                            "description": "Type of source content (auto-detect if not specified)",
                            "default": "auto",
                        },
                        "tags": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Tags to add to imported content",
                            "default": [],
                        },
                        "merge_mode": {
                            "type": "string",
                            "enum": ["replace", "append", "prepend"],
                            "description": "How to handle existing content in slot",
                            "default": "append",
                        },
                    },
                    "required": ["source", "slot_name"],
                },
            ),
            # Storage Optimization Tools
            Tool(
                name="memcord_compress",
                description="Compress memory slot content to save storage space",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "slot_name": {
                            "type": "string",
                            "description": (
                                "Memory slot name to compress (optional, processes all slots if not specified)"
                            ),
                        },
                        "action": {
                            "type": "string",
                            "enum": ["analyze", "compress", "decompress", "stats"],
                            "description": "Action to perform: analyze (preview), compress, decompress, or stats",
                            "default": "analyze",
                        },
                        "force": {
                            "type": "boolean",
                            "description": "Force compression even for already compressed content",
                            "default": False,
                        },
                    },
                    "required": ["action"],
                },
            ),
            Tool(
                name="memcord_archive",
                description="Archive or restore memory slots for long-term storage",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "slot_name": {"type": "string", "description": "Memory slot name to archive/restore"},
                        "action": {
                            "type": "string",
                            "enum": ["archive", "restore", "list", "stats", "candidates"],
                            "description": "Action to perform with archives",
                        },
                        "reason": {
                            "type": "string",
                            "description": "Reason for archiving (optional)",
                            "default": "manual",
                        },
                        "days_inactive": {
                            "type": "integer",
                            "description": "Days of inactivity for finding archive candidates",
                            "default": 30,
                            "minimum": 1,
                        },
                    },
                    "required": ["action"],
                },
            ),
            # Export & Sharing Tools
            Tool(
                name="memcord_export",
                description="Export memory slot as MCP file resource",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "slot_name": {"type": "string", "description": "Memory slot name to export"},
                        "format": {"type": "string", "enum": ["md", "txt", "json"], "description": "Export format"},
                        "include_metadata": {
                            "type": "boolean",
                            "default": True,
                            "description": "Include metadata in export",
                        },
                    },
                    "required": ["slot_name", "format"],
                },
            ),
            Tool(
                name="memcord_share",
                description="Generate shareable memory files in multiple formats",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "slot_name": {"type": "string", "description": "Memory slot name to share"},
                        "formats": {
                            "type": "array",
                            "items": {"type": "string", "enum": ["md", "txt", "json"]},
                            "description": "List of formats to generate",
                            "default": ["md", "txt"],
                        },
                        "include_metadata": {
                            "type": "boolean",
                            "default": True,
                            "description": "Include metadata in shared files",
                        },
                    },
                    "required": ["slot_name"],
                },
            ),
        ]

    def _setup_handlers(self):
        """Set up MCP server handlers."""

        @self.app.list_tools()
        async def list_tools() -> list[Tool]:
            """List available tools.

            IMPORTANT: All tool names must follow the "memcord_" prefix convention.
            When adding new tools, ensure the name starts with "memcord_" followed
            by the action in underscore_case format.

            Tools are categorized as basic (always available) and advanced (configurable).
            """
            if self._tool_cache is None:
                tools = self._get_basic_tools()
                if self.enable_advanced_tools:
                    tools.extend(self._get_advanced_tools())
                self._tool_cache = tools
            return self._tool_cache

        @self.app.call_tool()
        async def call_tool(name: str, arguments: dict[str, Any]) -> Sequence[TextContent]:
            """Handle tool calls with security validation."""
            operation_id = secrets.token_hex(8)
            client_id = "default"  # In future versions, extract from request context

            try:
                # Security validation
                allowed, error_msg = self.security.validate_request(client_id, name, arguments)
                if not allowed:
                    return [TextContent(type="text", text=f"🚫 Security check failed: {error_msg}")]

                # Start operation timeout tracking
                self.security.timeout_manager.start_operation(operation_id, name)

                try:
                    # O(1) dispatch using handler map
                    return await self._dispatch_handler(name, arguments)

                finally:
                    # Clean up operation tracking
                    self.security.timeout_manager.finish_operation(operation_id)

            except MemcordError as e:
                # Handle known memcord errors with proper formatting
                return [TextContent(type="text", text=e.get_user_message())]
            except Exception as e:
                # Handle unexpected errors
                handled_error = self.error_handler.handle_error(e, name, {"operation_id": operation_id})
                return [TextContent(type="text", text=handled_error.get_user_message())]

        @self.app.list_resources()
        async def list_resources() -> list[Resource]:
            """List MCP file resources for memory slots."""
            resources = []
            slots_info = await self.storage.list_memory_slots()

            for slot_info in slots_info:
                slot_name = slot_info["name"]
                for fmt in ["md", "txt", "json"]:
                    resources.append(
                        Resource(
                            uri=f"memory://{slot_name}.{fmt}",  # type: ignore[arg-type]
                            name=f"{slot_name} ({fmt.upper()})",
                            mimeType=self._get_mime_type(fmt),
                            description=f"Memory slot '{slot_name}' in {fmt.upper()} format",
                        )
                    )

            return resources

        @self.app.read_resource()
        async def read_resource(uri: str) -> str:
            """Read MCP file resource."""
            try:
                # Parse URI: memory://slot_name.format
                if not uri.startswith("memory://"):
                    raise ValueError("Invalid URI scheme")

                path_part = uri[9:]  # Remove "memory://"
                if "." not in path_part:
                    raise ValueError("Invalid URI format")

                slot_name, format_ext = path_part.rsplit(".", 1)

                # Load slot and format content
                slot = await self.storage.read_memory(slot_name)
                if not slot:
                    raise ValueError(f"Memory slot '{slot_name}' not found")

                if format_ext == "md":
                    content = self.storage._format_as_markdown(slot)
                elif format_ext == "txt":
                    content = self.storage._format_as_text(slot)
                elif format_ext == "json":
                    content = self.storage._format_as_json(slot)
                else:
                    raise ValueError(f"Unsupported format: {format_ext}")

                return content

            except Exception as e:
                raise ValueError(f"Error reading resource '{uri}': {str(e)}") from e

    @staticmethod
    def _get_mime_type(format: str) -> str:
        """Get MIME type for format."""
        mime_types = {"md": "text/markdown", "txt": "text/plain", "json": "application/json"}
        return mime_types.get(format, "text/plain")

    @handle_errors(default_error_message="Naming operation failed")
    async def _handle_memname(self, arguments: dict[str, Any]) -> list[TextContent]:
        """Handle memname tool call."""
        import logging

        logging.basicConfig(level=logging.DEBUG)
        logger = logging.getLogger(__name__)

        slot_name = arguments["slot_name"]
        logger.debug(f"DEBUG: memcord_name called with slot_name: {slot_name}")

        if not slot_name or not slot_name.strip():
            return [TextContent(type="text", text="Error: Slot name cannot be empty")]

        # Clean slot name
        slot_name = slot_name.strip().replace(" ", "_")
        logger.debug(f"DEBUG: cleaned slot_name: {slot_name}")

        # Check if slot already exists before creating
        existing_slot = await self.storage._load_slot(slot_name)
        if existing_slot:
            logger.debug("DEBUG: slot already exists, just setting current")
            self.storage._state.set_current_slot(slot_name)
            return [
                TextContent(
                    type="text",
                    text=(
                        f"Memory slot '{slot_name}' is now active. "
                        f"Created: {existing_slot.created_at.strftime('%Y-%m-%d %H:%M:%S')}"
                    ),
                )
            ]

        logger.debug("DEBUG: creating new slot")
        slot = await self.storage.create_or_get_slot(slot_name)
        logger.debug("DEBUG: slot created/retrieved successfully")

        return [
            TextContent(
                type="text",
                text=(
                    f"Memory slot '{slot_name}' is now active. Created: {slot.created_at.strftime('%Y-%m-%d %H:%M:%S')}"
                ),
            )
        ]

    @handle_errors(default_error_message="Use operation failed")
    async def _handle_memuse(self, arguments: dict[str, Any]) -> list[TextContent]:
        """Handle memuse tool call - activate existing memory slots only."""
        slot_name = arguments["slot_name"]

        if not slot_name or not slot_name.strip():
            return [TextContent(type="text", text="Error: Slot name cannot be empty")]

        # Clean slot name
        slot_name = slot_name.strip().replace(" ", "_")

        # Check if slot exists (DO NOT CREATE)
        existing_slot = await self.storage._load_slot(slot_name)
        if existing_slot:
            self.storage._state.set_current_slot(slot_name)
            return [
                TextContent(
                    type="text",
                    text=(
                        f"Memory slot '{slot_name}' is now active. "
                        f"Created: {existing_slot.created_at.strftime('%Y-%m-%d %H:%M:%S')}"
                    ),
                )
            ]
        else:
            return [
                TextContent(
                    type="text",
                    text=(
                        f"Error: Memory slot '{slot_name}' does not exist. "
                        "Use 'memcord_name' to create new slots or 'memcord_list' to see available slots."
                    ),
                )
            ]

    @handle_errors(default_error_message="Save failed")
    async def _handle_savemem(self, arguments: dict[str, Any]) -> list[TextContent]:
        """Handle savemem tool call."""
        chat_text = arguments["chat_text"]
        slot_name = self._resolve_slot_for_write(arguments)

        if not slot_name:
            return [TextContent(type="text", text=self.ERROR_NO_SLOT_SELECTED)]

        # Check for zero mode
        if self.storage._state.is_zero_mode():
            return [TextContent(type="text", text=self.WARNING_ZERO_MODE)]

        if not chat_text.strip():
            return [TextContent(type="text", text=self.ERROR_EMPTY_CHAT_TEXT)]

        entry = await self.storage.save_memory(slot_name, chat_text.strip())

        return [
            TextContent(
                type="text",
                text=(
                    f"Saved {len(chat_text)} characters to memory slot '{slot_name}' "
                    f"at {entry.timestamp.strftime('%Y-%m-%d %H:%M:%S')}"
                ),
            )
        ]

    @handle_errors(default_error_message="Read failed")
    async def _handle_readmem(self, arguments: dict[str, Any]) -> list[TextContent]:
        """Handle readmem tool call."""
        slot_name = self._resolve_slot(arguments)

        if not slot_name:
            return [TextContent(type="text", text=self.ERROR_NO_SLOT_SELECTED)]

        slot = await self.storage.read_memory(slot_name)
        if not slot:
            return [TextContent(type="text", text=f"Error: Memory slot '{slot_name}' not found.")]

        if not slot.entries:
            return [TextContent(type="text", text=f"Memory slot '{slot_name}' is empty.")]

        # Format content for display
        content_parts = []
        for i, entry in enumerate(slot.entries):
            entry_type = "Manual Save" if entry.type == "manual_save" else "Auto Summary"
            timestamp = entry.timestamp.strftime("%Y-%m-%d %H:%M:%S")

            content_parts.append(f"=== {entry_type} ({timestamp}) ===")

            if entry.type == "auto_summary" and entry.original_length and entry.summary_length:
                compression = (entry.summary_length / entry.original_length) * 100
                content_parts.append(
                    f"Summary: {entry.summary_length}/{entry.original_length} chars ({compression:.1f}%)"
                )

            content_parts.append(entry.content)

            if i < len(slot.entries) - 1:
                content_parts.append("")

        full_content = "\n".join(content_parts)

        return [
            TextContent(type="text", text=f"Memory slot '{slot_name}' ({len(slot.entries)} entries):\n\n{full_content}")
        ]

    @handle_errors(default_error_message="Save progress failed")
    async def _handle_saveprogress(self, arguments: dict[str, Any]) -> list[TextContent]:
        """Handle saveprogress tool call."""
        chat_text = arguments["chat_text"]
        slot_name = self._resolve_slot_for_write(arguments)
        compression_ratio = arguments.get("compression_ratio", 0.15)

        if not slot_name:
            return [TextContent(type="text", text=self.ERROR_NO_SLOT_SELECTED)]

        # Check for zero mode
        if self.storage._state.is_zero_mode():
            return [TextContent(type="text", text=self.WARNING_ZERO_MODE_PROGRESS)]

        if not chat_text.strip():
            return [TextContent(type="text", text=self.ERROR_EMPTY_CHAT_TEXT)]

        # Generate summary
        summary = self.summarizer.summarize(chat_text.strip(), compression_ratio)

        # Save summary to slot
        entry = await self.storage.add_summary_entry(slot_name, chat_text.strip(), summary)

        # Get statistics
        stats = self.summarizer.get_summary_stats(chat_text, summary)

        return [
            TextContent(
                type="text",
                text=f"Progress saved to '{slot_name}' at {entry.timestamp.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                f"Summary ({stats['summary_length']}/{stats['original_length']} chars, "
                f"{stats['compression_ratio']:.1%} compression):\n\n{summary}",
            )
        ]

    @handle_errors(default_error_message="List operation failed")
    async def _handle_listmems(self, arguments: dict[str, Any]) -> list[TextContent]:
        """Handle listmems tool call."""
        slots_info = await self.storage.list_memory_slots()
        current_slot = self.storage.get_current_slot()

        # Check for zero mode and show status
        if self.storage._state.is_zero_mode():
            lines = ["🚫 ZERO MODE ACTIVE - No memory will be saved", ""]
            if not slots_info:
                lines.append("No memory slots found.")
            else:
                lines.append("Available memory slots:")
                for slot_info in slots_info:
                    name = slot_info["name"]
                    marker = " (current)" if name == current_slot else ""
                    lines.append(
                        f"• {name}{marker} - {slot_info['entry_count']} entries, "
                        f"{slot_info['total_length']} chars, "
                        f"updated {slot_info['updated_at'][:19]}"
                    )
            lines.extend(["", "💡 Use 'memcord_name [slot_name]' to resume saving"])
        else:
            if not slots_info:
                return [TextContent(type="text", text="No memory slots found.")]

            lines = ["Available memory slots:"]
            for slot_info in slots_info:
                name = slot_info["name"]
                marker = " (current)" if name == current_slot else ""
                lines.append(
                    f"• {name}{marker} - {slot_info['entry_count']} entries, "
                    f"{slot_info['total_length']} chars, "
                    f"updated {slot_info['updated_at'][:19]}"
                )

        return [TextContent(type="text", text="\n".join(lines))]

    @handle_errors(default_error_message="Ping failed")
    async def _handle_ping(self, arguments: dict[str, Any]) -> list[TextContent]:
        """Handle ping tool call - lightweight health check for server warm-up."""
        return [TextContent(type="text", text="pong")]

    @handle_errors(default_error_message="Zero mode operation failed")
    async def _handle_zeromem(self, arguments: dict[str, Any]) -> list[TextContent]:
        """Handle zeromem tool call - activate zero mode."""
        # Activate zero mode by setting current slot to special __ZERO__ slot
        self.storage._state.activate_zero_mode()

        return [
            TextContent(
                type="text",
                text="🚫 Zero mode activated. No memory will be saved until you switch to another memory slot.\n\n"
                "ℹ️  Use 'memcord_name [slot_name]' to resume saving.",
            )
        ]

    @handle_errors(default_error_message="Close operation failed")
    async def _handle_closemem(self, arguments: dict[str, Any]) -> list[TextContent]:
        """Handle memcord_close tool call - deactivate current slot."""
        previous_slot = self.storage._state.clear_current_slot()

        if previous_slot and previous_slot != "__ZERO__":
            return [
                TextContent(
                    type="text",
                    text=f"Memory slot '{previous_slot}' deactivated. No slot is currently active.\n\n"
                    "Use 'memcord_name <slot>' or 'memcord_use <slot>' to activate a slot.",
                )
            ]
        else:
            return [
                TextContent(
                    type="text",
                    text="No slot was active. Use 'memcord_name <slot>' to activate a slot.",
                )
            ]

    @handle_errors(default_error_message="Error selecting entry")
    async def _handle_select_entry(self, arguments: dict[str, Any]) -> list[TextContent]:
        """Handle memcord_select_entry tool call - delegates to SelectEntryService."""
        from .services import SelectionRequest

        # Get slot name (use current if not specified, or project binding)
        slot_name = self._resolve_slot(arguments)
        if not slot_name:
            return [
                TextContent(
                    type="text",
                    text="❌ No memory slot selected. Use 'memcord_name [slot_name]' to select a slot first.",
                )
            ]

        # Check if in zero mode
        if self.storage._state.is_zero_mode():
            return [
                TextContent(
                    type="text",
                    text="🚫 Zero mode is active. Use 'memcord_name [slot_name]' to select a memory slot first.",
                )
            ]

        # Build request and delegate to service
        request = SelectionRequest(
            slot_name=slot_name,
            timestamp=arguments.get("timestamp"),
            relative_time=arguments.get("relative_time"),
            entry_index=arguments.get("entry_index"),
            entry_type=arguments.get("entry_type"),
            show_context=arguments.get("show_context", True),
        )
        result = await self.select_entry_service.select_entry(request)
        return self._format_select_entry_result(result)

    def _format_select_entry_result(self, result) -> list[TextContent]:
        """Format select entry result for display."""
        if not result.success:
            error_msg = f"❌ {result.error}"
            if result.available_entries:
                error_msg += f"\n\nAvailable entries in '{result.slot_name}':\n"
                for entry in result.available_entries:
                    entry_line = (
                        f"• Index {entry['index']}: {entry['timestamp']} "
                        f"({entry['type']}) - {entry['time_description']}\n"
                    )
                    error_msg += entry_line
            return [TextContent(type="text", text=error_msg)]

        lines = [
            f"✅ Selected entry from '{result.slot_name}':",
            f"📅 **Timestamp:** {result.timestamp.isoformat()}",
            f"📝 **Type:** {result.entry_type}",
            f"🔍 **Selection method:** {result.selection_method.replace('_', ' ')} ('{result.selection_query}')",
        ]
        if result.tolerance_applied:
            lines.append("⚠️ **Note:** Closest match found (not exact timestamp)")
        lines.extend(["", "**Content:**", result.content, ""])

        # Timeline context
        if result.context:
            lines.append(f"📍 **Timeline Position:** {result.context.get('position', '')}")
            if "previous_entry" in result.context:
                prev = result.context["previous_entry"]
                lines.append(f"⬅️ **Previous:** {prev['timestamp']} ({prev['type']}) - {prev['time_description']}")
                lines.append(f"   Preview: {prev['content_preview']}")
            if "next_entry" in result.context:
                next_entry = result.context["next_entry"]
                next_line = (
                    f"➡️ **Next:** {next_entry['timestamp']} ({next_entry['type']}) - {next_entry['time_description']}"
                )
                lines.append(next_line)
                lines.append(f"   Preview: {next_entry['content_preview']}")

        return [TextContent(type="text", text="\n".join(lines))]

    @handle_errors(default_error_message="Export failed")
    async def _handle_exportmem(self, arguments: dict[str, Any]) -> list[TextContent]:
        """Handle exportmem tool call."""
        slot_name = arguments["slot_name"]
        format = arguments["format"]

        try:
            output_path = await self.storage.export_slot_to_file(slot_name, format)

            return [
                TextContent(
                    type="text",
                    text=f"Memory slot '{slot_name}' exported to {output_path}\n"
                    f"MCP resource available at: memory://{slot_name}.{format}",
                )
            ]
        except ValueError as e:
            return [TextContent(type="text", text=f"Error: {str(e)}")]

    @handle_errors(default_error_message="Share operation failed")
    async def _handle_sharemem(self, arguments: dict[str, Any]) -> list[TextContent]:
        """Handle sharemem tool call."""
        slot_name = arguments["slot_name"]
        formats = arguments.get("formats", ["md", "txt"])

        try:
            exported_files = []
            for format in formats:
                output_path = await self.storage.export_slot_to_file(slot_name, format)
                exported_files.append(f"• {output_path}")

            resources = [f"• memory://{slot_name}.{fmt}" for fmt in formats]

            return [
                TextContent(
                    type="text",
                    text=f"Memory slot '{slot_name}' shared in {len(formats)} formats:\n\n"
                    f"Files created:\n" + "\n".join(exported_files) + "\n\n"
                    "MCP resources available:\n" + "\n".join(resources),
                )
            ]
        except ValueError as e:
            return [TextContent(type="text", text=f"Error: {str(e)}")]

    @handle_errors(default_error_message="Search failed")
    async def _handle_searchmem(self, arguments: dict[str, Any]) -> list[TextContent]:
        """Handle searchmem tool call."""
        query_text = arguments["query"]
        include_tags = arguments.get("include_tags", [])
        exclude_tags = arguments.get("exclude_tags", [])
        max_results = arguments.get("max_results", 20)
        case_sensitive = arguments.get("case_sensitive", False)

        if not query_text.strip():
            return [TextContent(type="text", text="Error: Search query cannot be empty")]

        # Create search query
        search_query = SearchQuery(
            query=query_text.strip(),
            include_tags=include_tags,
            exclude_tags=exclude_tags,
            max_results=max_results,
            case_sensitive=case_sensitive,
        )

        # Perform search
        results = await self.storage.search_memory(search_query)

        if not results:
            return [TextContent(type="text", text=f"No results found for: '{query_text}'")]

        # Format results
        lines = [f"Search results for '{query_text}' ({len(results)} found):"]
        lines.append("")

        for i, result in enumerate(results[:max_results], 1):
            match_indicator = {"slot": "📁", "entry": "📝", "tag": "🏷️", "group": "📂"}.get(result.match_type, "🔍")

            lines.append(f"{i}. {match_indicator} {result.slot_name} (score: {result.relevance_score:.2f})")

            if result.tags:
                lines.append(f"   Tags: {', '.join(result.tags)}")

            if result.group_path:
                lines.append(f"   Group: {result.group_path}")

            lines.append(f"   {result.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
            lines.append(f"   {result.snippet}")
            lines.append("")

        return [TextContent(type="text", text="\n".join(lines))]

    @handle_errors(default_error_message="Tag operation failed")
    async def _handle_tagmem(self, arguments: dict[str, Any]) -> list[TextContent]:
        """Handle tagmem tool call."""
        action = arguments["action"]
        slot_name = self._resolve_slot(arguments)
        tags = arguments.get("tags", [])

        if action in ["add", "remove"] and not slot_name:
            return [TextContent(type="text", text=self.ERROR_NO_SLOT_SELECTED)]

        if action == "add":
            if not tags:
                return [TextContent(type="text", text="Error: No tags specified to add")]

            if not slot_name:
                return [TextContent(type="text", text=self.ERROR_NO_SLOT_SELECTED)]

            results = []
            for tag in tags:
                success = await self.storage.add_tag_to_slot(slot_name, tag)
                if success:
                    results.append(f"Added tag '{tag}' to '{slot_name}'")
                else:
                    results.append(f"Failed to add tag '{tag}' to '{slot_name}'")

            return [TextContent(type="text", text="\n".join(results))]

        elif action == "remove":
            if not tags:
                return [TextContent(type="text", text="Error: No tags specified to remove")]

            if not slot_name:
                return [TextContent(type="text", text=self.ERROR_NO_SLOT_SELECTED)]

            results = []
            for tag in tags:
                success = await self.storage.remove_tag_from_slot(slot_name, tag)
                if success:
                    results.append(f"Removed tag '{tag}' from '{slot_name}'")
                else:
                    results.append(f"Tag '{tag}' not found in '{slot_name}'")

            return [TextContent(type="text", text="\n".join(results))]

        elif action == "list":
            if not slot_name:
                return [TextContent(type="text", text=self.ERROR_NO_SLOT_SELECTED)]

            slot = await self.storage.read_memory(slot_name)
            if not slot:
                return [TextContent(type="text", text=f"Memory slot '{slot_name}' not found")]

            if not slot.tags:
                return [TextContent(type="text", text=f"No tags found for memory slot '{slot_name}'")]

            tag_list = sorted(slot.tags)
            return [TextContent(type="text", text=f"Tags for '{slot_name}': {', '.join(tag_list)}")]

        else:
            return [TextContent(type="text", text=f"Error: Unknown action: {action}")]

    @handle_errors(default_error_message="Failed to list tags")
    async def _handle_listtags(self, arguments: dict[str, Any]) -> list[TextContent]:
        """Handle listtags tool call."""
        all_tags = await self.storage.list_all_tags()

        if not all_tags:
            return [TextContent(type="text", text="No tags found across memory slots")]

        return [TextContent(type="text", text=f"All tags ({len(all_tags)}): {', '.join(all_tags)}")]

    @handle_errors(default_error_message="Group operation failed")
    async def _handle_groupmem(self, arguments: dict[str, Any]) -> list[TextContent]:
        """Handle groupmem tool call."""
        action = arguments["action"]
        slot_name = self._resolve_slot(arguments)
        group_path = arguments.get("group_path")

        if action in ["set", "remove"] and not slot_name:
            return [TextContent(type="text", text=self.ERROR_NO_SLOT_SELECTED)]

        if action == "set":
            if not group_path:
                return [TextContent(type="text", text="Error: Group path is required for 'set' action")]

            if not slot_name:
                return [TextContent(type="text", text=self.ERROR_NO_SLOT_SELECTED)]

            success = await self.storage.set_slot_group(slot_name, group_path)
            if success:
                return [TextContent(type="text", text=f"Set group '{group_path}' for memory slot '{slot_name}'")]
            else:
                return [TextContent(type="text", text=f"Failed to set group for '{slot_name}'")]

        elif action == "remove":
            if not slot_name:
                return [TextContent(type="text", text=self.ERROR_NO_SLOT_SELECTED)]

            success = await self.storage.set_slot_group(slot_name, None)
            if success:
                return [TextContent(type="text", text=f"Removed group assignment from memory slot '{slot_name}'")]
            else:
                return [TextContent(type="text", text=f"Failed to remove group from '{slot_name}'")]

        elif action == "list":
            groups = await self.storage.list_groups()

            if not groups:
                return [TextContent(type="text", text="No memory groups found")]

            lines = [f"Memory groups ({len(groups)}):"]
            for group in sorted(groups, key=lambda g: g.path):
                lines.append(f"• {group.path} ({group.member_count} slots)")
                if group.description:
                    lines.append(f"  Description: {group.description}")

            return [TextContent(type="text", text="\n".join(lines))]

        else:
            return [TextContent(type="text", text=f"Error: Unknown action: {action}")]

    @handle_errors(default_error_message="Query failed")
    async def _handle_querymem(self, arguments: dict[str, Any]) -> list[TextContent]:
        """Handle querymem tool call."""
        question = arguments["question"]
        max_results = arguments.get("max_results", 5)

        if not question.strip():
            return [TextContent(type="text", text="Error: Question cannot be empty")]

        answer = await self.query_processor.answer_question(question.strip(), max_results)
        return [TextContent(type="text", text=answer)]

    @handle_errors(default_error_message="Import failed")
    async def _handle_importmem(self, arguments: dict[str, Any]) -> list[TextContent]:
        """Handle importmem tool call - delegates to ImportService."""
        source = arguments["source"]
        slot_name = self._resolve_slot(arguments)
        description = arguments.get("description")
        tags = arguments.get("tags", [])
        group_path = arguments.get("group_path")

        result = await self.import_service.import_content(source, slot_name, description, tags, group_path)
        return self._format_import_result(result)

    def _format_import_result(self, result) -> list[TextContent]:
        """Format import result for display."""
        if not result.success:
            return [TextContent(type="text", text=f"Error: {result.error}")]

        size_info = f"{result.content_length} characters"
        if result.file_size:
            size_info += f" from {result.file_size} byte file"

        response_parts = [
            f"Successfully imported {result.source_type} content to '{result.slot_name}'",
            f"Content: {size_info}",
            f"Source: {result.source_location or result.source}",
            f"Timestamp: {result.timestamp.strftime('%Y-%m-%d %H:%M:%S') if result.timestamp else 'unknown'}",
        ]

        if result.tags_applied:
            response_parts.append(f"Tags applied: {', '.join(result.tags_applied)}")

        if result.group_path:
            response_parts.append(f"Group: {result.group_path}")

        # Add specific metadata based on source type
        if result.source_type == "pdf" and "page_count" in result.metadata:
            response_parts.append(f"Pages processed: {result.metadata['page_count']}")
        elif result.source_type == "web_url" and "title" in result.metadata:
            response_parts.append(f"Page title: {result.metadata['title']}")
        elif result.source_type == "structured_data":
            if "rows" in result.metadata:
                response_parts.append(f"Rows: {result.metadata['rows']}")
            if "columns" in result.metadata:
                response_parts.append(f"Columns: {result.metadata['columns']}")

        return [TextContent(type="text", text="\n".join(response_parts))]

    @handle_errors(default_error_message="Merge operation failed")
    async def _handle_mergemem(self, arguments: dict[str, Any]) -> list[TextContent]:
        """Handle mergemem tool call - delegates to MergeService."""
        source_slots = arguments["source_slots"]
        target_slot = arguments["target_slot"]
        action = arguments.get("action", "preview")
        similarity_threshold = arguments.get("similarity_threshold", 0.8)
        delete_sources = arguments.get("delete_sources", False)

        if action == "preview":
            result = await self.merge_service.preview_merge(source_slots, target_slot, similarity_threshold)
            return self._format_merge_preview(result)
        elif action == "merge":
            result = await self.merge_service.execute_merge(
                source_slots, target_slot, similarity_threshold, delete_sources
            )
            return self._format_merge_result(result)
        else:
            return [TextContent(type="text", text=f"Error: Unknown action '{action}'. Use 'preview' or 'merge'.")]

    def _format_merge_preview(self, result) -> list[TextContent]:
        """Format merge preview result for display."""

        if not result.success:
            error_msg = f"Error: {result.error}"
            if result.debug_info:
                error_msg += f"\n\n{result.debug_info}"
            return [TextContent(type="text", text=error_msg)]

        response_parts = [
            f"=== MERGE PREVIEW: {result.target_slot} ===",
            f"Source slots: {', '.join(result.source_slots)}",
            f"Total content length: {result.total_content_length:,} characters",
            f"Duplicate content to remove: {result.duplicate_content_removed} sections",
            f"Similarity threshold: {result.similarity_threshold:.1%}",
            "",
            (
                f"Merged tags ({len(result.merged_tags)}): "
                f"{', '.join(sorted(result.merged_tags)) if result.merged_tags else 'None'}"
            ),
            (
                f"Merged groups ({len(result.merged_groups)}): "
                f"{', '.join(sorted(result.merged_groups)) if result.merged_groups else 'None'}"
            ),
            "",
            "Chronological order:",
        ]

        for slot_name, timestamp in result.chronological_order:
            response_parts.append(f"  - {slot_name}: {timestamp.strftime('%Y-%m-%d %H:%M:%S')}")

        if result.target_exists:
            response_parts.extend(
                ["", f"⚠️  WARNING: Target slot '{result.target_slot}' already exists and will be overwritten!"]
            )

        response_parts.extend(
            [
                "",
                "Content preview:",
                "=" * 40,
                result.content_preview,
                "=" * 40,
                "",
                "To execute the merge, call mergemem again with action='merge'",
            ]
        )

        return [TextContent(type="text", text="\n".join(response_parts))]

    def _format_merge_result(self, result) -> list[TextContent]:
        """Format merge execution result for display."""

        if not result.success:
            return [TextContent(type="text", text=f"Merge failed: {result.error}")]

        response_parts = [
            f"✅ Successfully merged {len(result.source_slots)} slots into '{result.target_slot}'",
            f"Final content: {result.content_length:,} characters",
            f"Duplicates removed: {result.duplicates_removed} sections",
            f"Merged at: {result.merged_at.strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            f"Source slots: {', '.join(result.source_slots)}",
        ]

        if result.tags_merged:
            response_parts.append(f"Tags merged: {', '.join(result.tags_merged)}")

        if result.groups_merged:
            response_parts.append(f"Groups merged: {', '.join(result.groups_merged)}")

        if result.deleted_sources:
            response_parts.extend(["", f"🗑️  Deleted source slots: {', '.join(result.deleted_sources)}"])

        return [TextContent(type="text", text="\n".join(response_parts))]

    @handle_errors(default_error_message="Compression operation failed")
    async def _handle_compressmem(self, arguments: dict[str, Any]) -> list[TextContent]:
        """Handle compress tool call - delegates to CompressionService."""
        action = arguments.get("action", "analyze")
        slot_name = self._resolve_slot(arguments)
        force = arguments.get("force", False)

        if action == "stats":
            result = await self.compression_service.get_stats(slot_name)
            return self._format_compression_stats(result)
        elif action == "analyze":
            result = await self.compression_service.analyze(slot_name)
            return self._format_compression_analysis(result)
        elif action == "compress":
            if slot_name:
                result = await self.compression_service.compress_slot(slot_name, force)
                return self._format_compression_result(result)
            else:
                result = await self.compression_service.compress_all_slots(force)
                return self._format_bulk_compression_result(result)
        elif action == "decompress":
            result = await self.compression_service.decompress_slot(slot_name)
            return self._format_decompression_result(result)
        else:
            return [
                TextContent(
                    type="text",
                    text=f"Error: Unknown action '{action}'. Use 'analyze', 'compress', 'decompress', or 'stats'.",
                )
            ]

    def _format_compression_stats(self, result) -> list[TextContent]:
        """Format compression stats for display."""
        from .compression import format_size

        if result.slot_name:
            response = [
                f"# Compression Statistics: {result.slot_name}",
                "",
                f"**Total Entries:** {result.total_entries}",
                f"**Compressed Entries:** {result.compressed_entries} ({result.compression_percentage:.1f}%)",
                f"**Original Size:** {format_size(result.total_original_size)}",
                f"**Compressed Size:** {format_size(result.total_compressed_size)}",
                f"**Space Saved:** {format_size(result.space_saved)} ({result.space_saved_percentage:.1f}%)",
                f"**Compression Ratio:** {result.compression_ratio:.3f}",
            ]
        else:
            response = [
                "# Overall Compression Statistics",
                "",
                f"**Total Slots:** {result.total_slots}",
                f"**Total Entries:** {result.total_entries}",
                f"**Compressed Entries:** {result.compressed_entries}",
                f"**Original Size:** {format_size(result.total_original_size)}",
                f"**Compressed Size:** {format_size(result.total_compressed_size)}",
                f"**Space Saved:** {format_size(result.space_saved)} ({result.space_saved_percentage:.1f}%)",
                f"**Average Compression Ratio:** {result.compression_ratio:.3f}",
            ]
        return [TextContent(type="text", text="\n".join(response))]

    def _format_compression_analysis(self, result) -> list[TextContent]:
        """Format compression analysis for display."""
        if not result.success:
            return [TextContent(type="text", text=f"Error: {result.error}")]
        return [TextContent(type="text", text=result.report)]

    def _format_compression_result(self, result) -> list[TextContent]:
        """Format single slot compression result for display."""
        from .compression import format_size

        if not result.success:
            return [TextContent(type="text", text=f"Error: {result.error}")]
        response = [
            f"✅ Compression completed for '{result.slot_name}'",
            "",
            f"**Entries Processed:** {result.entries_processed}",
            f"**Entries Compressed:** {result.entries_compressed}",
            f"**Original Size:** {format_size(result.original_size)}",
            f"**Compressed Size:** {format_size(result.compressed_size)}",
            f"**Space Saved:** {format_size(result.space_saved)}",
            f"**Compression Ratio:** {result.compression_ratio:.3f}",
        ]
        return [TextContent(type="text", text="\n".join(response))]

    def _format_bulk_compression_result(self, result) -> list[TextContent]:
        """Format bulk compression result for display."""
        from .compression import format_size

        if not result.success:
            return [TextContent(type="text", text=f"Error: {result.error}")]
        response = [
            "✅ Bulk compression completed",
            "",
            f"**Slots Processed:** {result.slots_processed}",
            f"**Total Entries Processed:** {result.total_entries_processed}",
            f"**Total Entries Compressed:** {result.total_entries_compressed}",
            f"**Total Original Size:** {format_size(result.total_original_size)}",
            f"**Total Compressed Size:** {format_size(result.total_compressed_size)}",
            f"**Total Space Saved:** {format_size(result.total_space_saved)}",
            f"**Overall Compression Ratio:** {result.overall_compression_ratio:.3f}",
        ]
        return [TextContent(type="text", text="\n".join(response))]

    def _format_decompression_result(self, result) -> list[TextContent]:
        """Format decompression result for display."""
        if not result.success:
            return [TextContent(type="text", text=f"Error: {result.error}")]
        response = [
            f"✅ Decompression completed for '{result.slot_name}'",
            "",
            f"**Entries Processed:** {result.entries_processed}",
            f"**Entries Decompressed:** {result.entries_decompressed}",
            f"**Success:** {'Yes' if result.decompressed_successfully else 'Partial'}",
        ]
        return [TextContent(type="text", text="\n".join(response))]

    @handle_errors(default_error_message="Archive operation failed")
    async def _handle_archivemem(self, arguments: dict[str, Any]) -> list[TextContent]:
        """Handle archive tool call - delegates to ArchiveService."""
        action = arguments.get("action")
        slot_name = self._resolve_slot(arguments)
        reason = arguments.get("reason", "manual")
        days_inactive = arguments.get("days_inactive", 30)

        if action == "archive":
            result = await self.archive_service.archive_slot(slot_name, reason)
            return self._format_archive_result(result)
        elif action == "restore":
            result = await self.archive_service.restore_slot(slot_name)
            return self._format_restore_result(result)
        elif action == "list":
            result = await self.archive_service.list_archives()
            return self._format_archive_list(result)
        elif action == "stats":
            result = await self.archive_service.get_stats()
            return self._format_archive_stats(result)
        elif action == "candidates":
            result = await self.archive_service.find_candidates(days_inactive)
            return self._format_archive_candidates(result)
        else:
            msg = f"Error: Unknown action '{action}'. Use 'archive', 'restore', 'list', 'stats', or 'candidates'."
            return [TextContent(type="text", text=msg)]

    def _format_archive_result(self, result) -> list[TextContent]:
        """Format archive result for display."""
        from .compression import format_size

        if not result.success:
            return [TextContent(type="text", text=f"Error: {result.error}")]
        response = [
            f"✅ Memory slot '{result.slot_name}' archived successfully",
            "",
            f"**Archived At:** {result.archived_at}",
            f"**Reason:** {result.archive_reason}",
            f"**Original Size:** {format_size(result.original_size)}",
            f"**Archived Size:** {format_size(result.archived_size)}",
            f"**Space Saved:** {format_size(result.space_saved)}",
            f"**Compression Ratio:** {result.compression_ratio:.3f}",
            "",
            "The slot has been moved to archive storage and removed from active memory.",
        ]
        return [TextContent(type="text", text="\n".join(response))]

    def _format_restore_result(self, result) -> list[TextContent]:
        """Format restore result for display."""
        if not result.success:
            return [TextContent(type="text", text=f"Error: {result.error}")]
        response = [
            f"✅ Memory slot '{result.slot_name}' restored from archive",
            "",
            f"**Restored At:** {result.restored_at}",
            f"**Entry Count:** {result.entry_count}",
            f"**Total Size:** {result.total_size:,} characters",
            "",
            "The slot is now available in active memory storage.",
        ]
        return [TextContent(type="text", text="\n".join(response))]

    def _format_archive_list(self, result) -> list[TextContent]:
        """Format archive list for display."""
        from .compression import format_size

        if not result.success:
            return [TextContent(type="text", text=f"Error: {result.error}")]
        if not result.archives:
            return [TextContent(type="text", text="No archived memory slots found.")]

        response = [f"# Archived Memory Slots ({len(result.archives)} total)", ""]
        for archive in result.archives:
            archive_info = [
                f"## {archive.slot_name}",
                f"- **Archived:** {archive.days_ago} days ago ({archive.archived_at[:10]})",
                f"- **Reason:** {archive.archive_reason}",
                f"- **Entries:** {archive.entry_count}",
                f"- **Original Size:** {format_size(archive.original_size)}",
                f"- **Archived Size:** {format_size(archive.archived_size)}",
                f"- **Space Saved:** {format_size(archive.space_saved)}",
            ]
            if archive.tags:
                archive_info.append(f"- **Tags:** {', '.join(archive.tags)}")
            if archive.group_path:
                archive_info.append(f"- **Group:** {archive.group_path}")
            response.extend(archive_info)
            response.append("")
        return [TextContent(type="text", text="\n".join(response))]

    def _format_archive_stats(self, result) -> list[TextContent]:
        """Format archive stats for display."""
        from .compression import format_size

        if result.total_archives == 0:
            return [TextContent(type="text", text="No archived memory slots found.")]
        response = [
            "# Archive Storage Statistics",
            "",
            f"**Total Archives:** {result.total_archives}",
            f"**Original Size:** {format_size(result.total_original_size)}",
            f"**Archived Size:** {format_size(result.total_archived_size)}",
            f"**Space Saved:** {format_size(result.total_savings)} ({result.savings_percentage:.1f}%)",
            f"**Average Compression:** {result.average_compression_ratio:.3f}",
        ]
        return [TextContent(type="text", text="\n".join(response))]

    def _format_archive_candidates(self, result) -> list[TextContent]:
        """Format archive candidates for display."""
        from .compression import format_size

        if not result.success:
            return [TextContent(type="text", text=f"Error: {result.error}")]
        if not result.candidates:
            return [
                TextContent(
                    type="text",
                    text=f"No memory slots found that have been inactive for {result.days_inactive_threshold}+ days.",
                )
            ]

        response = [
            f"# Archive Candidates (inactive for {result.days_inactive_threshold}+ days)",
            "",
            f"Found {len(result.candidates)} memory slots that could be archived:",
            "",
        ]
        for candidate in result.candidates:
            response.extend(
                [
                    f"## {candidate.slot_name}",
                    f"- **Last Updated:** {candidate.last_updated} ({candidate.days_inactive} days ago)",
                    f"- **Entries:** {candidate.entry_count}",
                    f"- **Size:** {format_size(candidate.current_size)}",
                ]
            )
            if candidate.tags:
                response.append(f"- **Tags:** {', '.join(candidate.tags)}")
            if candidate.group_path:
                response.append(f"- **Group:** {candidate.group_path}")
            response.append("")

        threshold = result.days_inactive_threshold
        response.extend(
            [
                "To archive any of these slots, use:",
                f'`memcord_archive slot_name="<slot_name>" action="archive" reason="inactive_{threshold}d"`',
            ]
        )
        return [TextContent(type="text", text="\n".join(response))]

    @handle_errors(default_error_message="Status check failed")
    async def _handle_status(self, arguments: dict[str, Any]) -> list[TextContent]:
        """Handle system status check - delegates to MonitoringService."""
        include_details = arguments.get("include_details", False)
        result = await self.monitoring_service.get_status(include_details)
        return self._format_status_report(result, include_details)

    def _format_status_report(self, result, include_details: bool) -> list[TextContent]:
        """Format status report for display."""
        if not result.success:
            return [TextContent(type="text", text=f"Status check failed: {result.error}")]

        response = [
            f"🏥 System Status: {result.overall_status.upper()}",
            f"📊 Uptime: {result.uptime_seconds:.0f}s ({result.uptime_hours:.1f}h)",
            f"⚡ Active Operations: {result.active_operations}",
            "",
        ]

        if result.total_operations > 0:
            response.extend(
                [
                    "📈 Recent Activity (Last Hour):",
                    f"  • Total Operations: {result.total_operations}",
                    f"  • Success Rate: {result.success_rate:.1f}%",
                    f"  • Average Duration: {result.avg_duration_ms:.0f}ms",
                    "",
                ]
            )

        response.extend([f"🔍 Health Checks: {result.healthy_checks}/{result.total_checks} healthy", ""])

        if result.cpu_percent or result.memory_percent or result.disk_usage_percent:
            response.extend(
                [
                    "💻 Resource Usage:",
                    f"  • CPU: {result.cpu_percent:.1f}%",
                    f"  • Memory: {result.memory_percent:.1f}%",
                    f"  • Disk: {result.disk_usage_percent:.1f}%",
                    "",
                ]
            )

        if include_details and result.health_checks:
            response.extend(["🔍 Detailed Health Checks:", ""])
            for check in result.health_checks:
                status_emoji = {"healthy": "✅", "degraded": "⚠️", "unhealthy": "❌"}.get(check.status, "❓")
                response.append(f"  {status_emoji} {check.service}: {check.status} ({check.response_time:.1f}ms)")
                if check.error_message:
                    response.append(f"    Error: {check.error_message}")
                if check.details:
                    for key, value in check.details.items():
                        if not isinstance(value, dict):
                            response.append(f"    {key}: {value}")
            response.append("")

        response.append("💡 Use `memcord_diagnostics` for detailed analysis or `memcord_metrics` for performance data.")
        return [TextContent(type="text", text="\n".join(response))]

    @handle_errors(default_error_message="Metrics retrieval failed")
    async def _handle_metrics(self, arguments: dict[str, Any]) -> list[TextContent]:
        """Handle performance metrics request - delegates to MonitoringService."""
        metric_name = arguments.get("metric_name")
        hours = arguments.get("hours", 1)
        result = self.monitoring_service.get_metrics(metric_name, hours)
        return self._format_metrics_report(result)

    def _format_metrics_report(self, result) -> list[TextContent]:
        """Format metrics report for display."""
        if not result.success:
            return [TextContent(type="text", text=f"Metrics request failed: {result.error}")]

        if result.metric_name:
            # Specific metric response
            response = [
                f"📊 Performance Metric: {result.metric_name}",
                f"📅 Time Window: {result.hours} hour(s)",
                f"📈 Data Points: {result.data_points}",
                "",
            ]
            if result.summary and result.summary.count > 0:
                s = result.summary
                response.extend(
                    [
                        "📋 Summary:",
                        f"  • Count: {s.count}",
                        f"  • Average: {s.avg:.2f}{s.unit}",
                        f"  • Min: {s.min:.2f}{s.unit}",
                        f"  • Max: {s.max:.2f}{s.unit}",
                        f"  • Latest: {s.latest:.2f}{s.unit}",
                        "",
                    ]
                )
            else:
                response.append("No data available for this metric in the specified time window.")
        else:
            # All metrics overview
            response = [
                "📊 Performance Metrics Overview",
                f"📅 Time Window: {result.hours} hour(s)",
                f"📈 Available Metrics: {len(result.available_metrics)}",
                "",
            ]
            if result.summaries:
                response.append("📋 Metrics Summary:")
                for name, s in result.summaries.items():
                    if s.count > 0:
                        response.append(f"  • {name}: avg={s.avg:.2f}{s.unit}, count={s.count}")
                response.append("")

            if result.available_metrics:
                response.extend(
                    [
                        "🔍 Available Metrics:",
                        "  " + ", ".join(result.available_metrics),
                        "",
                        '💡 Use `memcord_metrics metric_name="<name>"` for detailed metric data.',
                    ]
                )
            else:
                response.append("No metrics available yet. Metrics are collected as operations are performed.")

        return [TextContent(type="text", text="\n".join(response))]

    @handle_errors(default_error_message="Log retrieval failed")
    async def _handle_logs(self, arguments: dict[str, Any]) -> list[TextContent]:
        """Handle operation logs request - delegates to MonitoringService."""
        tool_name = arguments.get("tool_name")
        status = arguments.get("status")
        hours = arguments.get("hours", 1)
        limit = arguments.get("limit", 100)
        result = self.monitoring_service.get_logs(tool_name, status, hours, limit)
        return self._format_logs_report(result)

    def _format_logs_report(self, result) -> list[TextContent]:
        """Format logs report for display."""
        if not result.success:
            return [TextContent(type="text", text=f"Logs request failed: {result.error}")]

        response = [
            "📋 Operation Logs",
            f"📅 Time Window: {result.hours} hour(s)",
            f"🔍 Filters: tool={result.tool_filter or 'all'}, status={result.status_filter or 'all'}",
            f"📊 Showing {result.shown_count} of {result.total_count} logs",
            "",
        ]

        if result.total_operations > 0:
            response.extend(
                [
                    "📈 Statistics:",
                    f"  • Total Operations: {result.total_operations}",
                    f"  • Success Rate: {result.success_rate:.1f}%",
                    f"  • Failed Operations: {result.failed_operations}",
                ]
            )
            if result.avg_duration_ms:
                response.append(f"  • Average Duration: {result.avg_duration_ms:.0f}ms")
            response.append("")

        if result.logs:
            response.append("🔍 Recent Operations:")
            status_emojis = {"completed": "✅", "failed": "❌", "started": "🔄", "timeout": "⏰"}
            for log in result.logs:
                time_str = log.start_time.strftime("%H:%M:%S")
                status_emoji = status_emojis.get(log.status, "❓")
                duration_str = f" ({log.duration_ms:.0f}ms)" if log.duration_ms else ""
                response.append(f"  {status_emoji} {time_str} {log.tool_name}{duration_str}")
                if log.error_message:
                    response.append(f"    Error: {log.error_message}")
            if result.total_count > result.shown_count:
                response.append(f"  ... and {result.total_count - result.shown_count} more entries")
        else:
            response.append("No logs found matching the specified criteria.")

        response.extend(["", '💡 Use `memcord_diagnostics check_type="performance"` for detailed analysis.'])
        return [TextContent(type="text", text="\n".join(response))]

    @handle_errors(default_error_message="Diagnostics failed")
    async def _handle_diagnostics(self, arguments: dict[str, Any]) -> list[TextContent]:
        """Handle system diagnostics request - delegates to MonitoringService."""
        check_type = arguments.get("check_type", "health")
        result = await self.monitoring_service.run_diagnostics(check_type)
        return self._format_diagnostics_report(result)

    def _format_diagnostics_report(self, result) -> list[TextContent]:
        """Format diagnostics report for display."""
        if not result.success:
            if result.error and "Unknown check type" in result.error:
                msg = f"Invalid check_type '{result.check_type}'. Use 'health', 'performance', or 'full_report'."
                return [TextContent(type="text", text=msg)]
            return [TextContent(type="text", text=f"Diagnostics failed: {result.error}")]

        response = []

        if result.check_type == "health":
            response = ["🏥 System Health Diagnostics", "=" * 40, ""]
            health_emojis = {"healthy": "✅", "degraded": "⚠️", "unhealthy": "❌", "unknown": "❓"}
            for check in result.health_checks:
                status_emoji = health_emojis.get(check.status, "❓")
                response.append(f"{status_emoji} {check.service.upper()}: {check.status}")
                response.append(f"  Response Time: {check.response_time:.1f}ms")
                if check.error_message:
                    response.append(f"  Error: {check.error_message}")
                if check.details:
                    if "slot_count" in check.details:
                        response.append(f"  Memory Slots: {check.details['slot_count']}")
                    if "process_memory_mb" in check.details:
                        response.append(f"  Memory Usage: {check.details['process_memory_mb']:.1f}MB")
                    if "disk_free_gb" in check.details:
                        response.append(f"  Disk Free: {check.details['disk_free_gb']:.1f}GB")
                    if "python_version" in check.details:
                        response.append(f"  Python: {check.details['python_version'].split()[0]}")
                response.append("")

        elif result.check_type == "performance":
            response = ["📊 Performance Analysis", "=" * 40, f"Analysis Time: {result.timestamp}", ""]
            if result.issues:
                response.append("⚠️ Issues Detected:")
                for issue in result.issues:
                    severity_emoji = {"critical": "🚨", "warning": "⚠️", "info": "ℹ️"}.get(issue.severity, "❓")
                    response.append(f"  {severity_emoji} {issue.description}")
                response.append("")
            else:
                response.extend(["✅ No performance issues detected.", ""])
            if result.recommendations:
                response.append("💡 Recommendations:")
                for rec in result.recommendations:
                    response.append(f"  • {rec}")
                response.append("")

        elif result.check_type == "full_report":
            report = result.full_report_data
            response = ["📋 Comprehensive System Report", "=" * 50, f"Generated: {result.timestamp}", ""]

            health_checks = report.get("health_checks", [])
            healthy_count = sum(1 for c in health_checks if c["status"] == "healthy")
            response.extend([f"🏥 Health Status: {healthy_count}/{len(health_checks)} services healthy", ""])

            resources = report.get("resource_usage", {})
            if resources:
                mem_pct = resources.get("memory_percent", 0)
                mem_mb = resources.get("memory_used_mb", 0)
                disk_pct = resources.get("disk_usage_percent", 0)
                disk_free = resources.get("disk_free_gb", 0)
                response.extend(
                    [
                        "💻 Current Resource Usage:",
                        f"  • CPU: {resources.get('cpu_percent', 0):.1f}%",
                        f"  • Memory: {mem_pct:.1f}% ({mem_mb:.0f}MB)",
                        f"  • Disk: {disk_pct:.1f}% ({disk_free:.1f}GB free)",
                        "",
                    ]
                )

            op_stats = report.get("operation_stats", {})
            if op_stats.get("total_operations", 0) > 0:
                response.extend(
                    [
                        "📊 Operation Statistics (24h):",
                        f"  • Total Operations: {op_stats.get('total_operations', 0)}",
                        f"  • Success Rate: {op_stats.get('success_rate', 0):.1f}%",
                        f"  • Average Duration: {op_stats.get('avg_duration_ms', 0):.0f}ms",
                        "",
                    ]
                )

            perf_analysis = report.get("performance_analysis", {})
            issues = perf_analysis.get("issues", [])
            if issues:
                response.append(f"⚠️ {len(issues)} performance issues detected")
                response.append('   Use `memcord_diagnostics check_type="performance"` for details')
            else:
                response.append("✅ No performance issues detected")

            response.extend(
                [
                    "",
                    "💡 For detailed analysis of specific areas, use:",
                    '  • `memcord_diagnostics check_type="health"` - Health checks',
                    '  • `memcord_diagnostics check_type="performance"` - Performance analysis',
                    "  • `memcord_metrics` - Performance metrics",
                    "  • `memcord_logs` - Operation logs",
                ]
            )

        return [TextContent(type="text", text="\n".join(response))]

    @handle_errors(default_error_message="Bind operation failed")
    async def _handle_bind(self, arguments: dict[str, Any]) -> list[TextContent]:
        """Bind project directory to a memory slot."""
        project_path = Path(arguments["project_path"]).expanduser().resolve()

        if not project_path.is_dir():
            return [TextContent(type="text", text=f"Error: '{project_path}' is not a valid directory")]

        memcord_file = project_path / ".memcord"

        # Determine slot name
        slot_name = arguments.get("slot_name")
        if not slot_name:
            # Check if .memcord already exists
            if memcord_file.exists():
                slot_name = memcord_file.read_text().strip()
            else:
                # Use directory name as slot name
                slot_name = project_path.name.replace(" ", "_")

        # Create or get the slot (auto-creates if missing)
        await self.storage.create_or_get_slot(slot_name)

        # Write .memcord file
        memcord_file.write_text(slot_name)

        return [
            TextContent(
                type="text",
                text=f"Bound '{project_path}' to memory slot '{slot_name}'. .memcord file created. Slot is now active.",
            )
        ]

    @handle_errors(default_error_message="Unbind failed")
    async def _handle_unbind(self, arguments: dict[str, Any]) -> list[TextContent]:
        """Remove .memcord binding from project."""
        project_path = Path(arguments["project_path"]).expanduser().resolve()
        memcord_file = project_path / ".memcord"

        if memcord_file.exists():
            memcord_file.unlink()
            return [TextContent(type="text", text=f"Removed .memcord binding from '{project_path}'")]
        else:
            return [TextContent(type="text", text=f"No .memcord file found in '{project_path}'")]

    async def run(self):
        """Run the MCP server."""
        from mcp.server.stdio import stdio_server

        async with stdio_server() as (read_stream, write_stream):
            await self.app.run(read_stream, write_stream, self.app.create_initialization_options())


def main():
    """Main entry point."""
    # Configure logging FIRST - before any other code runs
    # This ensures all output goes to stderr, not stdout (critical for STDIO mode)
    from .logging_config import configure_logging

    configure_logging()

    server = ChatMemoryServer()
    asyncio.run(server.run())


if __name__ == "__main__":
    main()
