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
import json
import os
import secrets
import time
from typing import Any, Sequence, Dict, List
from pathlib import Path

from mcp.server import Server
from mcp.types import (
    Tool, 
    TextContent, 
    Resource,
    TextResourceContents,
    CallToolResult
)

from .storage import StorageManager
from .summarizer import TextSummarizer
from .models import MemorySlot, SearchQuery
from .query import SimpleQueryProcessor
from .importer import ContentImporter
from .merger import MemorySlotMerger
from .security import SecurityMiddleware
from .errors import ErrorHandler, MemcordError, ValidationError, RateLimitError, OperationTimeoutError, handle_async_errors
from .status_monitoring import StatusMonitoringSystem
from datetime import datetime
import functools
import uuid


def with_timeout_check(operation_id_key: str = 'operation_id'):
    """Decorator to add timeout checking to async methods."""
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(self, *args, **kwargs):
            # Extract operation_id from kwargs or generate one
            operation_id = kwargs.get(operation_id_key) or secrets.token_hex(8)
            
            # Check timeout if operation is being tracked
            if hasattr(self, 'security') and operation_id in self.security.timeout_manager.active_operations:
                timed_out, error_msg = self.security.timeout_manager.check_timeout(operation_id)
                if timed_out:
                    raise OperationTimeoutError(
                        error_msg or f"Operation {func.__name__} timed out",
                        operation=func.__name__
                    )
            
            return await func(self, *args, **kwargs)
        return wrapper
    return decorator


class ChatMemoryServer:
    """MCP server for chat memory management."""
    
    def __init__(self, memory_dir: str = "memory_slots", shared_dir: str = "shared_memories", enable_advanced_tools: bool = None):
        self.storage = StorageManager(memory_dir, shared_dir)
        self.summarizer = TextSummarizer()
        self.query_processor = SimpleQueryProcessor(self.storage._search_engine)
        self.importer = ContentImporter()
        self.merger = MemorySlotMerger()
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
            
        self._setup_handlers()
    
    async def call_tool_direct(self, name: str, arguments: Dict[str, Any]) -> Sequence[TextContent]:
        """Direct tool calling method for testing purposes."""
        try:
            # Basic tools (always available)
            if name == "memcord_name":
                return await self._handle_memname(arguments)
            elif name == "memcord_use":
                return await self._handle_memuse(arguments)
            elif name == "memcord_save":
                return await self._handle_savemem(arguments)
            elif name == "memcord_read":
                return await self._handle_readmem(arguments)
            elif name == "memcord_save_progress":
                return await self._handle_saveprogress(arguments)
            elif name == "memcord_list":
                return await self._handle_listmems(arguments)
            elif name == "memcord_search":
                return await self._handle_searchmem(arguments)
            elif name == "memcord_query":
                return await self._handle_querymem(arguments)
            elif name == "memcord_zero":
                return await self._handle_zeromem(arguments)
            elif name == "memcord_select_entry":
                return await self._handle_select_entry(arguments)
            
            # Status & Monitoring tools
            elif name == "memcord_status":
                return await self._handle_status(arguments)
            elif name == "memcord_metrics":
                return await self._handle_metrics(arguments)
            elif name == "memcord_logs":
                return await self._handle_logs(arguments)
            elif name == "memcord_diagnostics":
                return await self._handle_diagnostics(arguments)
            
            # Advanced tools (check if enabled)
            elif name in ["memcord_tag", "memcord_list_tags", "memcord_group", "memcord_import", "memcord_merge", "memcord_archive", "memcord_export", "memcord_share", "memcord_compress"]:
                if not self.enable_advanced_tools:
                    return [TextContent(type="text", text=f"Error: Advanced tool '{name}' is not enabled. Set MEMCORD_ENABLE_ADVANCED=true to enable advanced features.")]
                
                if name == "memcord_tag":
                    return await self._handle_tagmem(arguments)
                elif name == "memcord_list_tags":
                    return await self._handle_listtags(arguments)
                elif name == "memcord_group":
                    return await self._handle_groupmem(arguments)
                elif name == "memcord_import":
                    return await self._handle_importmem(arguments)
                elif name == "memcord_merge":
                    return await self._handle_mergemem(arguments)
                elif name == "memcord_archive":
                    return await self._handle_archivemem(arguments)
                elif name == "memcord_export":
                    return await self._handle_exportmem(arguments)
                elif name == "memcord_share":
                    return await self._handle_sharemem(arguments)
                elif name == "memcord_compress":
                    return await self._handle_compressmem(arguments)
                else:
                    return [TextContent(type="text", text=f"Error: Unknown advanced tool: {name}")]
            else:
                return [TextContent(type="text", text=f"Error: Unknown tool: {name}")]
        except Exception as e:
            return [TextContent(type="text", text=f"Error: {str(e)}")]
    
    async def list_tools_direct(self) -> List[Tool]:
        """Direct tools listing method for testing purposes."""
        tools = self._get_basic_tools()
        if self.enable_advanced_tools:
            tools.extend(self._get_advanced_tools())
        return tools
    
    async def list_resources_direct(self) -> List[Resource]:
        """Direct resources listing method for testing purposes."""
        resources = []
        slots_info = await self.storage.list_memory_slots()
        
        for slot_info in slots_info:
            slot_name = slot_info["name"]
            for fmt in ["md", "txt", "json"]:
                resources.append(Resource(
                    uri=str(f"memory://{slot_name}.{fmt}"),
                    name=f"{slot_name} ({fmt.upper()})",
                    description=f"Memory slot {slot_name} in {fmt.upper()} format",
                    mimeType=f"text/{fmt}" if fmt in ["txt", "md"] else f"application/{fmt}"
                ))
        
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
    
    def _get_basic_tools(self) -> List[Tool]:
        """Get the list of basic tools (always available)."""
        return [
            # Core Tools
            Tool(
                name="memcord_name",
                description="Set or create a named memory slot",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "slot_name": {
                            "type": "string",
                            "description": "Name of the memory slot to create or select"
                        }
                    },
                    "required": ["slot_name"]
                }
            ),
            Tool(
                name="memcord_use",
                description="Activate an existing memory slot (does not create new slots)",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "slot_name": {
                            "type": "string",
                            "description": "Name of the existing memory slot to activate"
                        }
                    },
                    "required": ["slot_name"]
                }
            ),
            Tool(
                name="memcord_save",
                description="Save chat text to memory slot (overwrites existing content)",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "chat_text": {
                            "type": "string",
                            "description": "Chat text to save"
                        },
                        "slot_name": {
                            "type": "string",
                            "description": "Memory slot name (optional, uses current slot if not specified)"
                        }
                    },
                    "required": ["chat_text"]
                }
            ),
            Tool(
                name="memcord_read",
                description="Retrieve full content from memory slot",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "slot_name": {
                            "type": "string",
                            "description": "Memory slot name (optional, uses current slot if not specified)"
                        }
                    }
                }
            ),
            Tool(
                name="memcord_save_progress",
                description="Generate summary and append to memory slot",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "chat_text": {
                            "type": "string",
                            "description": "Chat text to summarize and save"
                        },
                        "slot_name": {
                            "type": "string",
                            "description": "Memory slot name (optional, uses current slot if not specified)"
                        },
                        "compression_ratio": {
                            "type": "number",
                            "description": "Target compression ratio (0.1 = 10%, default 0.15)",
                            "minimum": 0.05,
                            "maximum": 0.5,
                            "default": 0.15
                        }
                    },
                    "required": ["chat_text"]
                }
            ),
            Tool(
                name="memcord_list",
                description="List all available memory slots with metadata",
                inputSchema={
                    "type": "object",
                    "properties": {}
                }
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
                            "description": "Search query with optional Boolean operators (AND, OR, NOT)"
                        },
                        "include_tags": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Include slots with these tags",
                            "default": []
                        },
                        "exclude_tags": {
                            "type": "array", 
                            "items": {"type": "string"},
                            "description": "Exclude slots with these tags",
                            "default": []
                        },
                        "max_results": {
                            "type": "integer",
                            "description": "Maximum number of results",
                            "default": 20,
                            "minimum": 1,
                            "maximum": 100
                        },
                        "case_sensitive": {
                            "type": "boolean",
                            "description": "Whether search is case sensitive",
                            "default": False
                        }
                    },
                    "required": ["query"]
                }
            ),
            Tool(
                name="memcord_query",
                description="Ask natural language questions about your memory contents",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "question": {
                            "type": "string",
                            "description": "Natural language question about your memories"
                        },
                        "max_results": {
                            "type": "integer",
                            "description": "Maximum number of results to consider",
                            "default": 5,
                            "minimum": 1,
                            "maximum": 20
                        }
                    },
                    "required": ["question"]
                }
            ),
            Tool(
                name="memcord_zero",
                description="Activate zero mode - no memory will be saved until switched to another slot",
                inputSchema={
                    "type": "object",
                    "properties": {}
                }
            ),
            Tool(
                name="memcord_select_entry",
                description="Select and retrieve a specific memory entry by timestamp, relative time, or index within a memory slot",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "slot_name": {
                            "type": "string",
                            "description": "Target memory slot (optional, uses current if not specified)"
                        },
                        "timestamp": {
                            "type": "string",
                            "description": "Exact timestamp in ISO format (e.g., '2025-07-21T17:30:00')"
                        },
                        "relative_time": {
                            "type": "string",
                            "description": "Human descriptions like 'latest', 'oldest', '2 hours ago', 'yesterday'"
                        },
                        "entry_index": {
                            "type": "integer",
                            "description": "Direct numeric index (0-based, negative for reverse indexing)"
                        },
                        "entry_type": {
                            "type": "string",
                            "enum": ["manual_save", "auto_summary"],
                            "description": "Filter by entry type"
                        },
                        "show_context": {
                            "type": "boolean",
                            "default": True,
                            "description": "Include timeline position and adjacent entries info"
                        }
                    }
                }
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
                            "minItems": 2
                        },
                        "target_slot": {
                            "type": "string",
                            "description": "Name for the merged memory slot"
                        },
                        "action": {
                            "type": "string",
                            "enum": ["preview", "merge"],
                            "description": "Action to perform: 'preview' to see merge preview, 'merge' to execute",
                            "default": "preview"
                        },
                        "similarity_threshold": {
                            "type": "number",
                            "minimum": 0.0,
                            "maximum": 1.0,
                            "description": "Threshold for duplicate detection (0.0-1.0, default 0.8)",
                            "default": 0.8
                        },
                        "delete_sources": {
                            "type": "boolean",
                            "description": "Whether to delete source slots after successful merge",
                            "default": False
                        }
                    },
                    "required": ["source_slots", "target_slot"]
                }
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
                            "default": False
                        }
                    }
                }
            ),
            Tool(
                name="memcord_metrics",
                description="Get performance metrics and system statistics",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "metric_name": {
                            "type": "string",
                            "description": "Specific metric name to retrieve (optional, shows all if not specified)"
                        },
                        "hours": {
                            "type": "integer",
                            "description": "Number of hours of data to retrieve",
                            "default": 1,
                            "minimum": 1,
                            "maximum": 168
                        }
                    }
                }
            ),
            Tool(
                name="memcord_logs",
                description="Get operation execution logs and history",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "tool_name": {
                            "type": "string",
                            "description": "Filter logs by specific tool name"
                        },
                        "status": {
                            "type": "string",
                            "description": "Filter logs by operation status",
                            "enum": ["started", "completed", "failed", "timeout"]
                        },
                        "hours": {
                            "type": "integer",
                            "description": "Number of hours of logs to retrieve",
                            "default": 1,
                            "minimum": 1,
                            "maximum": 168
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of log entries to return",
                            "default": 100,
                            "minimum": 1,
                            "maximum": 1000
                        }
                    }
                }
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
                            "default": "health"
                        }
                    }
                }
            )
        ]
    
    def _get_advanced_tools(self) -> List[Tool]:
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
                            "description": "Memory slot name (optional, uses current slot if not specified)"
                        },
                        "action": {
                            "type": "string",
                            "enum": ["add", "remove", "list"],
                            "description": "Action to perform with tags"
                        },
                        "tags": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Tags to add or remove",
                            "default": []
                        }
                    },
                    "required": ["action"]
                }
            ),
            Tool(
                name="memcord_list_tags", 
                description="List all tags used across memory slots",
                inputSchema={
                    "type": "object",
                    "properties": {}
                }
            ),
            Tool(
                name="memcord_group",
                description="Manage memory slot groups/folders",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "slot_name": {
                            "type": "string",
                            "description": "Memory slot name (optional, uses current slot if not specified)"
                        },
                        "action": {
                            "type": "string",
                            "enum": ["set", "remove", "list"],
                            "description": "Action to perform with groups"
                        },
                        "group_path": {
                            "type": "string",
                            "description": "Group path (e.g., 'project/client/meetings')"
                        }
                    },
                    "required": ["action"]
                }
            ),
            # Import & Integration Tools
            Tool(
                name="memcord_import",
                description="Import content from various sources into memory slots",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "source": {
                            "type": "string",
                            "description": "Source file path, URL, or '-' for clipboard"
                        },
                        "slot_name": {
                            "type": "string",
                            "description": "Target memory slot name"
                        },
                        "source_type": {
                            "type": "string",
                            "enum": ["auto", "text", "pdf", "url", "csv", "json"],
                            "description": "Type of source content (auto-detect if not specified)",
                            "default": "auto"
                        },
                        "tags": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Tags to add to imported content",
                            "default": []
                        },
                        "merge_mode": {
                            "type": "string",
                            "enum": ["replace", "append", "prepend"],
                            "description": "How to handle existing content in slot",
                            "default": "append"
                        }
                    },
                    "required": ["source", "slot_name"]
                }
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
                            "description": "Memory slot name to compress (optional, processes all slots if not specified)"
                        },
                        "action": {
                            "type": "string",
                            "enum": ["analyze", "compress", "decompress", "stats"],
                            "description": "Action to perform: analyze (preview), compress, decompress, or stats",
                            "default": "analyze"
                        },
                        "force": {
                            "type": "boolean",
                            "description": "Force compression even for already compressed content",
                            "default": False
                        }
                    },
                    "required": ["action"]
                }
            ),
            Tool(
                name="memcord_archive",
                description="Archive or restore memory slots for long-term storage",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "slot_name": {
                            "type": "string",
                            "description": "Memory slot name to archive/restore"
                        },
                        "action": {
                            "type": "string",
                            "enum": ["archive", "restore", "list", "stats", "candidates"],
                            "description": "Action to perform with archives"
                        },
                        "reason": {
                            "type": "string",
                            "description": "Reason for archiving (optional)",
                            "default": "manual"
                        },
                        "days_inactive": {
                            "type": "integer",
                            "description": "Days of inactivity for finding archive candidates",
                            "default": 30,
                            "minimum": 1
                        }
                    },
                    "required": ["action"]
                }
            ),
            # Export & Sharing Tools
            Tool(
                name="memcord_export",
                description="Export memory slot as MCP file resource",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "slot_name": {
                            "type": "string",
                            "description": "Memory slot name to export"
                        },
                        "format": {
                            "type": "string",
                            "enum": ["md", "txt", "json"],
                            "description": "Export format"
                        },
                        "include_metadata": {
                            "type": "boolean",
                            "default": True,
                            "description": "Include metadata in export"
                        }
                    },
                    "required": ["slot_name", "format"]
                }
            ),
            Tool(
                name="memcord_share",
                description="Generate shareable memory files in multiple formats",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "slot_name": {
                            "type": "string",
                            "description": "Memory slot name to share"
                        },
                        "formats": {
                            "type": "array",
                            "items": {"type": "string", "enum": ["md", "txt", "json"]},
                            "description": "List of formats to generate",
                            "default": ["md", "txt"]
                        },
                        "include_metadata": {
                            "type": "boolean",
                            "default": True,
                            "description": "Include metadata in shared files"
                        }
                    },
                    "required": ["slot_name"]
                }
            )
        ]

    def _setup_handlers(self):
        """Set up MCP server handlers."""
        
        @self.app.list_tools()
        async def list_tools() -> List[Tool]:
            """List available tools.
            
            IMPORTANT: All tool names must follow the "memcord_" prefix convention.
            When adding new tools, ensure the name starts with "memcord_" followed
            by the action in underscore_case format.
            
            Tools are categorized as basic (always available) and advanced (configurable).
            """
            tools = self._get_basic_tools()
            if self.enable_advanced_tools:
                tools.extend(self._get_advanced_tools())
            return tools

        @self.app.call_tool()
        async def call_tool(name: str, arguments: Dict[str, Any]) -> Sequence[TextContent]:
            """Handle tool calls with security validation."""
            operation_id = secrets.token_hex(8)
            client_id = "default"  # In future versions, extract from request context
            
            try:
                # Security validation
                allowed, error_msg = self.security.validate_request(client_id, name, arguments)
                if not allowed:
                    return [TextContent(type="text", text=f"🚫 Security check failed: {error_msg}")]
                
                # Start operation timeout tracking
                deadline = self.security.timeout_manager.start_operation(operation_id, name)
                
                try:
                    # Basic tools (always available)
                    if name == "memcord_name":
                        return await self._handle_memname(arguments)
                    elif name == "memcord_use":
                        return await self._handle_memuse(arguments)
                    elif name == "memcord_save":
                        return await self._handle_savemem(arguments)
                    elif name == "memcord_read":
                        return await self._handle_readmem(arguments)
                    elif name == "memcord_save_progress":
                        return await self._handle_saveprogress(arguments)
                    elif name == "memcord_list":
                        return await self._handle_listmems(arguments)
                    elif name == "memcord_search":
                        return await self._handle_searchmem(arguments)
                    elif name == "memcord_query":
                        return await self._handle_querymem(arguments)
                    elif name == "memcord_zero":
                        return await self._handle_zeromem(arguments)
                    elif name == "memcord_select_entry":
                        return await self._handle_select_entry(arguments)
                    
                    # Status & Monitoring tools
                    elif name == "memcord_status":
                        return await self._handle_status(arguments)
                    elif name == "memcord_metrics":
                        return await self._handle_metrics(arguments)
                    elif name == "memcord_logs":
                        return await self._handle_logs(arguments)
                    elif name == "memcord_diagnostics":
                        return await self._handle_diagnostics(arguments)
                    
                    else:
                        return [TextContent(type="text", text=f"Error: Unknown tool: {name}")]
                    
                finally:
                    # Clean up operation tracking
                    self.security.timeout_manager.finish_operation(operation_id)
                    
            except MemcordError as e:
                # Handle known memcord errors with proper formatting
                return [TextContent(type="text", text=e.get_user_message())]
            except Exception as e:
                # Handle unexpected errors
                handled_error = self.error_handler.handle_error(e, name, {'operation_id': operation_id})
                return [TextContent(type="text", text=handled_error.get_user_message())]

        @self.app.list_resources()
        async def list_resources() -> List[Resource]:
            """List MCP file resources for memory slots."""
            resources = []
            slots_info = await self.storage.list_memory_slots()
            
            for slot_info in slots_info:
                slot_name = slot_info["name"]
                for fmt in ["md", "txt", "json"]:
                    resources.append(Resource(
                        uri=str(f"memory://{slot_name}.{fmt}"),
                        name=f"{slot_name} ({fmt.upper()})",
                        mimeType=self._get_mime_type(fmt),
                        description=f"Memory slot '{slot_name}' in {fmt.upper()} format"
                    ))
            
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
                raise ValueError(f"Error reading resource '{uri}': {str(e)}")
    
    def _get_mime_type(self, format: str) -> str:
        """Get MIME type for format."""
        mime_types = {
            "md": "text/markdown",
            "txt": "text/plain", 
            "json": "application/json"
        }
        return mime_types.get(format, "text/plain")
    
    async def _handle_memname(self, arguments: Dict[str, Any]) -> List[TextContent]:
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
            logger.debug(f"DEBUG: slot already exists, just setting current")
            self.storage._state.set_current_slot(slot_name)
            return [TextContent(
                type="text",
                text=f"Memory slot '{slot_name}' is now active. Created: {existing_slot.created_at.strftime('%Y-%m-%d %H:%M:%S')}"
            )]
        
        logger.debug(f"DEBUG: creating new slot")
        slot = await self.storage.create_or_get_slot(slot_name)
        logger.debug(f"DEBUG: slot created/retrieved successfully")
        
        return [TextContent(
            type="text",
            text=f"Memory slot '{slot_name}' is now active. Created: {slot.created_at.strftime('%Y-%m-%d %H:%M:%S')}"
        )]
    
    async def _handle_memuse(self, arguments: Dict[str, Any]) -> List[TextContent]:
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
            return [TextContent(
                type="text",
                text=f"Memory slot '{slot_name}' is now active. Created: {existing_slot.created_at.strftime('%Y-%m-%d %H:%M:%S')}"
            )]
        else:
            return [TextContent(
                type="text", 
                text=f"Error: Memory slot '{slot_name}' does not exist. Use 'memcord_name' to create new slots or 'memcord_list' to see available slots."
            )]
    
    async def _handle_savemem(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """Handle savemem tool call."""
        chat_text = arguments["chat_text"]
        slot_name = arguments.get("slot_name") or self.storage.get_current_slot()
        
        if not slot_name:
            return [TextContent(type="text", text="Error: No memory slot selected. Use 'memname' first.")]
        
        # Check for zero mode
        if self.storage._state.is_zero_mode():
            return [TextContent(
                type="text", 
                text="⚠️ Zero mode active - content NOT saved.\n\n"
                     "💡 To save this content:\n"
                     "1. Use 'memcord_name [slot_name]' to select a memory slot\n"
                     "2. Then retry your save command"
            )]
        
        if not chat_text.strip():
            return [TextContent(type="text", text="Error: Chat text cannot be empty")]
        
        entry = await self.storage.save_memory(slot_name, chat_text.strip())
        
        return [TextContent(
            type="text",
            text=f"Saved {len(chat_text)} characters to memory slot '{slot_name}' at {entry.timestamp.strftime('%Y-%m-%d %H:%M:%S')}"
        )]
    
    async def _handle_readmem(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """Handle readmem tool call."""
        slot_name = arguments.get("slot_name") or self.storage.get_current_slot()
        
        if not slot_name:
            return [TextContent(type="text", text="Error: No memory slot selected. Use 'memname' first.")]
        
        slot = await self.storage.read_memory(slot_name)
        if not slot:
            return [TextContent(type="text", text=f"Error: Memory slot '{slot_name}' not found.")]
        
        if not slot.entries:
            return [TextContent(type="text", text=f"Memory slot '{slot_name}' is empty.")]
        
        # Format content for display
        content_parts = []
        for i, entry in enumerate(slot.entries):
            entry_type = "Manual Save" if entry.type == "manual_save" else "Auto Summary"
            timestamp = entry.timestamp.strftime('%Y-%m-%d %H:%M:%S')
            
            content_parts.append(f"=== {entry_type} ({timestamp}) ===")
            
            if entry.type == "auto_summary" and entry.original_length and entry.summary_length:
                compression = (entry.summary_length / entry.original_length) * 100
                content_parts.append(f"Summary: {entry.summary_length}/{entry.original_length} chars ({compression:.1f}%)")
            
            content_parts.append(entry.content)
            
            if i < len(slot.entries) - 1:
                content_parts.append("")
        
        full_content = "\n".join(content_parts)
        
        return [TextContent(
            type="text",
            text=f"Memory slot '{slot_name}' ({len(slot.entries)} entries):\n\n{full_content}"
        )]
    
    async def _handle_saveprogress(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """Handle saveprogress tool call."""
        chat_text = arguments["chat_text"]
        slot_name = arguments.get("slot_name") or self.storage.get_current_slot()
        compression_ratio = arguments.get("compression_ratio", 0.15)
        
        if not slot_name:
            return [TextContent(type="text", text="Error: No memory slot selected. Use 'memname' first.")]
        
        # Check for zero mode
        if self.storage._state.is_zero_mode():
            return [TextContent(
                type="text", 
                text="⚠️ Zero mode active - progress NOT saved.\n\n"
                     "💡 To save this progress:\n"
                     "1. Use 'memcord_name [slot_name]' to select a memory slot\n"
                     "2. Then retry your save progress command"
            )]
        
        if not chat_text.strip():
            return [TextContent(type="text", text="Error: Chat text cannot be empty")]
        
        # Generate summary
        summary = self.summarizer.summarize(chat_text.strip(), compression_ratio)
        
        # Save summary to slot
        entry = await self.storage.add_summary_entry(slot_name, chat_text.strip(), summary)
        
        # Get statistics
        stats = self.summarizer.get_summary_stats(chat_text, summary)
        
        return [TextContent(
            type="text",
            text=f"Progress saved to '{slot_name}' at {entry.timestamp.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                 f"Summary ({stats['summary_length']}/{stats['original_length']} chars, "
                 f"{stats['compression_ratio']:.1%} compression):\n\n{summary}"
        )]
    
    async def _handle_listmems(self, arguments: Dict[str, Any]) -> List[TextContent]:
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
    
    async def _handle_zeromem(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """Handle zeromem tool call - activate zero mode."""
        # Activate zero mode by setting current slot to special __ZERO__ slot
        self.storage._state.activate_zero_mode()
        
        return [TextContent(
            type="text",
            text="🚫 Zero mode activated. No memory will be saved until you switch to another memory slot.\n\n"
                 "ℹ️  Use 'memcord_name [slot_name]' to resume saving."
        )]

    async def _handle_select_entry(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """Handle memcord_select_entry tool call - select specific memory entry by timestamp, relative time, or index."""
        from .temporal_parser import TemporalParser
        
        # Get slot name (use current if not specified)
        slot_name = arguments.get("slot_name", self.storage.get_current_slot())
        if not slot_name:
            return [TextContent(
                type="text",
                text="❌ No memory slot selected. Use 'memcord_name [slot_name]' to select a slot first."
            )]
        
        # Check if in zero mode
        if self.storage._state.is_zero_mode():
            return [TextContent(
                type="text",
                text="🚫 Zero mode is active. Use 'memcord_name [slot_name]' to select a memory slot first."
            )]
        
        # Load the memory slot
        try:
            slot = await self.storage.read_memory(slot_name)
            if not slot:
                return [TextContent(
                    type="text",
                    text=f"❌ Memory slot '{slot_name}' not found. Use 'memcord_list' to see available slots."
                )]
        except Exception as e:
            return [TextContent(
                type="text",
                text=f"❌ Error loading memory slot '{slot_name}': {str(e)}"
            )]
        
        # Check if slot has entries
        if not slot.entries:
            return [TextContent(
                type="text",
                text=f"📭 Memory slot '{slot_name}' is empty. No entries to select."
            )]
        
        # Extract and validate selection parameters
        timestamp = arguments.get("timestamp")
        relative_time = arguments.get("relative_time")
        entry_index = arguments.get("entry_index")
        entry_type = arguments.get("entry_type")
        show_context = arguments.get("show_context", True)
        
        # Validate that exactly one selection method is provided
        is_valid, error_msg = TemporalParser.validate_selection_input(timestamp, relative_time, entry_index)
        if not is_valid:
            return [TextContent(
                type="text",
                text=f"❌ {error_msg}\n\n"
                     f"Available selection methods:\n"
                     f"• timestamp: '2025-07-21T17:30:00'\n"
                     f"• relative_time: 'latest', 'oldest', '2 hours ago', 'yesterday'\n"
                     f"• entry_index: 0 (oldest), -1 (latest), etc."
            )]
        
        # Find the entry based on selection method
        selected_entry = None
        selected_index = -1
        selection_method = ""
        selection_query = ""
        tolerance_applied = False
        
        try:
            if timestamp:
                # Parse timestamp and find closest entry
                parsed_time = TemporalParser.parse_timestamp(timestamp)
                if not parsed_time:
                    return [TextContent(
                        type="text",
                        text=f"❌ Invalid timestamp format: '{timestamp}'\n\n"
                             f"Expected formats:\n"
                             f"• ISO format: '2025-07-21T17:30:00'\n"
                             f"• Date only: '2025-07-21'\n"
                             f"• With timezone: '2025-07-21T17:30:00Z'"
                    )]
                
                result = slot.get_entry_by_timestamp(parsed_time)
                if result:
                    selected_index, selected_entry = result
                    selection_method = "timestamp_exact"
                    selection_query = timestamp
                    # Check if tolerance was needed (not exact match)
                    if abs(selected_entry.timestamp - parsed_time).total_seconds() > 60:
                        tolerance_applied = True
                
            elif relative_time:
                # Parse relative time expression
                result = slot.get_entry_by_relative_time(relative_time)
                if result:
                    selected_index, selected_entry = result
                    selection_method = "relative_time"
                    selection_query = relative_time
                
            elif entry_index is not None:
                # Get entry by index
                result = slot.get_entry_by_index(entry_index)
                if result:
                    selected_index, selected_entry = result
                    selection_method = "index"
                    selection_query = str(entry_index)
            
            # Filter by entry type if specified
            if selected_entry and entry_type and selected_entry.type != entry_type:
                selected_entry = None
                selected_index = -1
            
            # Handle no match found
            if not selected_entry:
                available_timestamps = slot.get_available_timestamps()
                available_info = f"\n\nAvailable entries in '{slot_name}':\n"
                for i, ts in enumerate(available_timestamps):
                    entry = slot.entries[i]
                    time_desc = TemporalParser.format_time_description(entry.timestamp)
                    available_info += f"• Index {i}: {ts} ({entry.type}) - {time_desc}\n"
                
                return [TextContent(
                    type="text",
                    text=f"❌ No matching entry found for {selection_method.replace('_', ' ')}: '{selection_query}'"
                         f"{available_info}"
                )]
            
            # Build the response
            response_lines = []
            
            # Selected entry info
            response_lines.append(f"✅ Selected entry from '{slot_name}':")
            response_lines.append(f"📅 **Timestamp:** {selected_entry.timestamp.isoformat()}")
            response_lines.append(f"📝 **Type:** {selected_entry.type}")
            response_lines.append(f"🔍 **Selection method:** {selection_method.replace('_', ' ')} ('{selection_query}')")
            if tolerance_applied:
                response_lines.append("⚠️ **Note:** Closest match found (not exact timestamp)")
            response_lines.append("")
            
            # Entry content
            response_lines.append("**Content:**")
            response_lines.append(selected_entry.content)
            response_lines.append("")
            
            # Timeline context if requested
            if show_context:
                context = slot.get_timeline_context(selected_index)
                if context:
                    response_lines.append(f"📍 **Timeline Position:** {context['position']}")
                    
                    if "previous_entry" in context:
                        prev = context["previous_entry"]
                        response_lines.append(f"⬅️ **Previous:** {prev['timestamp']} ({prev['type']}) - {prev['time_description']}")
                        response_lines.append(f"   Preview: {prev['content_preview']}")
                    
                    if "next_entry" in context:
                        next_entry = context["next_entry"]
                        response_lines.append(f"➡️ **Next:** {next_entry['timestamp']} ({next_entry['type']}) - {next_entry['time_description']}")
                        response_lines.append(f"   Preview: {next_entry['content_preview']}")
            
            return [TextContent(
                type="text",
                text="\n".join(response_lines)
            )]
            
        except Exception as e:
            return [TextContent(
                type="text",
                text=f"❌ Error selecting entry: {str(e)}\n\n"
                     f"Please check your selection parameters and try again."
            )]
    
    async def _handle_exportmem(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """Handle exportmem tool call."""
        slot_name = arguments["slot_name"]
        format = arguments["format"]
        
        try:
            output_path = await self.storage.export_slot_to_file(slot_name, format)
            
            return [TextContent(
                type="text",
                text=f"Memory slot '{slot_name}' exported to {output_path}\n"
                     f"MCP resource available at: memory://{slot_name}.{format}"
            )]
        except ValueError as e:
            return [TextContent(type="text", text=f"Error: {str(e)}")]
    
    async def _handle_sharemem(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """Handle sharemem tool call."""
        slot_name = arguments["slot_name"]
        formats = arguments.get("formats", ["md", "txt"])
        
        try:
            exported_files = []
            for format in formats:
                output_path = await self.storage.export_slot_to_file(slot_name, format)
                exported_files.append(f"• {output_path}")
            
            resources = [f"• memory://{slot_name}.{fmt}" for fmt in formats]
            
            return [TextContent(
                type="text",
                text=f"Memory slot '{slot_name}' shared in {len(formats)} formats:\n\n"
                     f"Files created:\n" + "\n".join(exported_files) + "\n\n"
                     f"MCP resources available:\n" + "\n".join(resources)
            )]
        except ValueError as e:
            return [TextContent(type="text", text=f"Error: {str(e)}")]
    
    async def _handle_searchmem(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """Handle searchmem tool call."""
        query_text = arguments["query"]
        include_tags = arguments.get("include_tags", [])
        exclude_tags = arguments.get("exclude_tags", [])
        max_results = arguments.get("max_results", 20)
        case_sensitive = arguments.get("case_sensitive", False)
        
        if not query_text.strip():
            return [TextContent(type="text", text="Error: Search query cannot be empty")]
        
        try:
            # Create search query
            search_query = SearchQuery(
                query=query_text.strip(),
                include_tags=include_tags,
                exclude_tags=exclude_tags,
                max_results=max_results,
                case_sensitive=case_sensitive
            )
            
            # Perform search
            results = await self.storage.search_memory(search_query)
            
            if not results:
                return [TextContent(type="text", text=f"No results found for: '{query_text}'")]
            
            # Format results
            lines = [f"Search results for '{query_text}' ({len(results)} found):"]
            lines.append("")
            
            for i, result in enumerate(results[:max_results], 1):
                match_indicator = {
                    'slot': '📁',
                    'entry': '📝', 
                    'tag': '🏷️',
                    'group': '📂'
                }.get(result.match_type, '🔍')
                
                lines.append(f"{i}. {match_indicator} {result.slot_name} (score: {result.relevance_score:.2f})")
                
                if result.tags:
                    lines.append(f"   Tags: {', '.join(result.tags)}")
                
                if result.group_path:
                    lines.append(f"   Group: {result.group_path}")
                
                lines.append(f"   {result.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
                lines.append(f"   {result.snippet}")
                lines.append("")
            
            return [TextContent(type="text", text="\n".join(lines))]
            
        except Exception as e:
            return [TextContent(type="text", text=f"Search failed: {str(e)}")]
    
    async def _handle_tagmem(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """Handle tagmem tool call."""
        action = arguments["action"]
        slot_name = arguments.get("slot_name") or self.storage.get_current_slot()
        tags = arguments.get("tags", [])
        
        if action in ["add", "remove"] and not slot_name:
            return [TextContent(type="text", text="Error: No memory slot selected. Use 'memname' first.")]
        
        try:
            if action == "add":
                if not tags:
                    return [TextContent(type="text", text="Error: No tags specified to add")]
                
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
                
                results = []
                for tag in tags:
                    success = await self.storage.remove_tag_from_slot(slot_name, tag)
                    if success:
                        results.append(f"Removed tag '{tag}' from '{slot_name}'")
                    else:
                        results.append(f"Tag '{tag}' not found in '{slot_name}'")
                
                return [TextContent(type="text", text="\n".join(results))]
            
            elif action == "list":
                slot = await self.storage.read_memory(slot_name)
                if not slot:
                    return [TextContent(type="text", text=f"Memory slot '{slot_name}' not found")]
                
                if not slot.tags:
                    return [TextContent(type="text", text=f"No tags found for memory slot '{slot_name}'")]
                
                tag_list = sorted(list(slot.tags))
                return [TextContent(type="text", text=f"Tags for '{slot_name}': {', '.join(tag_list)}")]
            
            else:
                return [TextContent(type="text", text=f"Error: Unknown action: {action}")]
                
        except Exception as e:
            return [TextContent(type="text", text=f"Tag operation failed: {str(e)}")]
    
    async def _handle_listtags(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """Handle listtags tool call."""
        try:
            all_tags = await self.storage.list_all_tags()
            
            if not all_tags:
                return [TextContent(type="text", text="No tags found across memory slots")]
            
            return [TextContent(type="text", text=f"All tags ({len(all_tags)}): {', '.join(all_tags)}")]
            
        except Exception as e:
            return [TextContent(type="text", text=f"Failed to list tags: {str(e)}")]
    
    async def _handle_groupmem(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """Handle groupmem tool call."""
        action = arguments["action"]
        slot_name = arguments.get("slot_name")
        group_path = arguments.get("group_path")
        
        if action in ["set", "remove"] and not slot_name:
            slot_name = self.storage.get_current_slot()
            if not slot_name:
                return [TextContent(type="text", text="Error: No memory slot selected. Use 'memname' first.")]
        
        try:
            if action == "set":
                if not group_path:
                    return [TextContent(type="text", text="Error: Group path is required for 'set' action")]
                
                success = await self.storage.set_slot_group(slot_name, group_path)
                if success:
                    return [TextContent(type="text", text=f"Set group '{group_path}' for memory slot '{slot_name}'")]
                else:
                    return [TextContent(type="text", text=f"Failed to set group for '{slot_name}'")]
            
            elif action == "remove":
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
                
        except Exception as e:
            return [TextContent(type="text", text=f"Group operation failed: {str(e)}")]
    
    async def _handle_querymem(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """Handle querymem tool call."""
        question = arguments["question"]
        max_results = arguments.get("max_results", 5)
        
        if not question.strip():
            return [TextContent(type="text", text="Error: Question cannot be empty")]
        
        try:
            answer = await self.query_processor.answer_question(question.strip(), max_results)
            return [TextContent(type="text", text=answer)]
            
        except Exception as e:
            return [TextContent(type="text", text=f"Query failed: {str(e)}")]
    
    async def _handle_importmem(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """Handle importmem tool call."""
        source = arguments["source"]
        slot_name = arguments.get("slot_name") or self.storage.get_current_slot()
        description = arguments.get("description")
        tags = arguments.get("tags", [])
        group_path = arguments.get("group_path")
        
        if not source.strip():
            return [TextContent(type="text", text="Error: Source cannot be empty")]
        
        if not slot_name:
            return [TextContent(type="text", text="Error: No memory slot selected. Use 'memname' first.")]
        
        try:
            # Import content using the importer
            import_result = await self.importer.import_content(source.strip())
            
            if not import_result.success:
                return [TextContent(type="text", text=f"Error: Import failed: {import_result.error}")]
            
            # Prepare content with import metadata
            content_parts = []
            
            # Add import header
            import_header = (
                f"=== IMPORTED CONTENT ===\n"
                f"Source: {import_result.source_location or source}\n"
                f"Type: {import_result.source_type}\n"
                f"Imported: {import_result.metadata.get('imported_at', 'unknown')}\n"
            )
            
            if description:
                import_header += f"Description: {description}\n"
            
            import_header += "========================\n\n"
            content_parts.append(import_header)
            content_parts.append(import_result.content)
            
            final_content = "".join(content_parts)
            
            # Save to memory slot
            entry = await self.storage.save_memory(slot_name, final_content)
            
            # Apply metadata if provided
            if tags or group_path:
                slot = await self.storage.read_memory(slot_name)
                if slot:
                    # Update tags
                    if tags:
                        existing_tags = set(slot.tags or [])
                        existing_tags.update(tags)
                        slot.tags = list(existing_tags)
                    
                    # Update group
                    if group_path:
                        slot.group_path = group_path
                    
                    # Update description
                    if description and not slot.description:
                        slot.description = description
                    
                    # Save updated slot
                    await self.storage._save_slot(slot)
            
            # Format success message
            size_info = f"{len(import_result.content)} characters"
            if 'file_size' in import_result.metadata:
                file_size = import_result.metadata['file_size']
                size_info += f" from {file_size} byte file"
            
            response_parts = [
                f"Successfully imported {import_result.source_type} content to '{slot_name}'",
                f"Content: {size_info}",
                f"Source: {import_result.source_location or source}",
                f"Timestamp: {entry.timestamp.strftime('%Y-%m-%d %H:%M:%S')}"
            ]
            
            if tags:
                response_parts.append(f"Tags applied: {', '.join(tags)}")
            
            if group_path:
                response_parts.append(f"Group: {group_path}")
            
            # Add specific metadata based on source type
            if import_result.source_type == "pdf" and "page_count" in import_result.metadata:
                response_parts.append(f"Pages processed: {import_result.metadata['page_count']}")
            elif import_result.source_type == "web_url" and "title" in import_result.metadata:
                response_parts.append(f"Page title: {import_result.metadata['title']}")
            elif import_result.source_type == "structured_data":
                if "rows" in import_result.metadata:
                    response_parts.append(f"Rows: {import_result.metadata['rows']}")
                if "columns" in import_result.metadata:
                    response_parts.append(f"Columns: {import_result.metadata['columns']}")
            
            return [TextContent(type="text", text="\n".join(response_parts))]
            
        except Exception as e:
            return [TextContent(type="text", text=f"Import failed: {str(e)}")]
    
    async def _handle_mergemem(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """Handle mergemem tool call."""
        source_slots = arguments["source_slots"]
        target_slot = arguments["target_slot"]
        action = arguments.get("action", "preview")
        similarity_threshold = arguments.get("similarity_threshold", 0.8)
        delete_sources = arguments.get("delete_sources", False)
        
        if not source_slots or len(source_slots) < 2:
            return [TextContent(type="text", text="Error: At least 2 source slots are required for merging")]
        
        if not target_slot.strip():
            return [TextContent(type="text", text="Error: Target slot name cannot be empty")]
        
        # Clean and validate slot names
        source_slots = [name.strip() for name in source_slots if name.strip()]
        target_slot = target_slot.strip().replace(" ", "_")
        
        if len(source_slots) < 2:
            return [TextContent(type="text", text="Error: At least 2 valid source slots are required")]
        
        try:
            # Load source memory slots
            slots = []
            missing_slots = []
            
            for slot_name in source_slots:
                slot = await self.storage.read_memory(slot_name)
                if slot:
                    slots.append(slot)
                else:
                    missing_slots.append(slot_name)
            
            if missing_slots:
                return [TextContent(
                    type="text", 
                    text=f"Error: Memory slots not found: {', '.join(missing_slots)}"
                )]
            
            if len(slots) < 2:
                return [TextContent(type="text", text="Error: Not enough valid slots found for merging")]
            
            # Check if target slot already exists
            existing_target = await self.storage.read_memory(target_slot)
            
            if action == "preview":
                # Create merge preview with comprehensive error handling
                try:
                    preview = self.merger.create_merge_preview(slots, target_slot, similarity_threshold)
                except Exception as e:
                    # Enhanced debug information for any errors
                    debug_info = []
                    for i, slot in enumerate(slots):
                        debug_info.append(f"Slot {i} ({slot.slot_name}):")
                        debug_info.append(f"  - type: {type(slot)}")
                        debug_info.append(f"  - has_content: {hasattr(slot, 'content')}")
                        debug_info.append(f"  - has_name: {hasattr(slot, 'name')}")
                        debug_info.append(f"  - has_entries: {hasattr(slot, 'entries')}")
                        debug_info.append(f"  - entries_count: {len(slot.entries) if hasattr(slot, 'entries') else 'N/A'}")
                        
                        # Try to access the properties that are failing
                        try:
                            content = slot.content
                            debug_info.append(f"  - content_access: SUCCESS (length: {len(content)})")
                        except Exception as content_error:
                            debug_info.append(f"  - content_access: FAILED ({content_error})")
                        
                        try:
                            name = slot.name
                            debug_info.append(f"  - name_access: SUCCESS ({name})")
                        except Exception as name_error:
                            debug_info.append(f"  - name_access: FAILED ({name_error})")
                    
                    import traceback
                    error_msg = f"Merge operation failed: {e}\n\nFull traceback:\n{traceback.format_exc()}\n\nDebug info:\n" + "\n".join(debug_info)
                    return [TextContent(type="text", text=error_msg)]
                
                response_parts = [
                    f"=== MERGE PREVIEW: {target_slot} ===",
                    f"Source slots: {', '.join(preview.source_slots)}",
                    f"Total content length: {preview.total_content_length:,} characters",
                    f"Duplicate content to remove: {preview.duplicate_content_removed} sections",
                    f"Similarity threshold: {similarity_threshold:.1%}",
                    "",
                    f"Merged tags ({len(preview.merged_tags)}): {', '.join(sorted(preview.merged_tags)) if preview.merged_tags else 'None'}",
                    f"Merged groups ({len(preview.merged_groups)}): {', '.join(sorted(preview.merged_groups)) if preview.merged_groups else 'None'}",
                    "",
                    "Chronological order:"
                ]
                
                for slot_name, timestamp in preview.chronological_order:
                    response_parts.append(f"  - {slot_name}: {timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
                
                if existing_target:
                    response_parts.extend([
                        "",
                        f"⚠️  WARNING: Target slot '{target_slot}' already exists and will be overwritten!"
                    ])
                
                response_parts.extend([
                    "",
                    "Content preview:",
                    "=" * 40,
                    preview.content_preview,
                    "=" * 40,
                    "",
                    f"To execute the merge, call mergemem again with action='merge'"
                ])
                
                return [TextContent(type="text", text="\n".join(response_parts))]
            
            elif action == "merge":
                # Execute the merge
                merge_result = self.merger.merge_slots(slots, target_slot, similarity_threshold)
                
                if not merge_result.success:
                    return [TextContent(type="text", text=f"Merge failed: {merge_result.error}")]
                
                # Get the merged content
                preview = self.merger.create_merge_preview(slots, target_slot, similarity_threshold)
                merged_content = self.merger._merge_content(slots, similarity_threshold)
                
                # Create or update the target slot
                entry = await self.storage.save_memory(target_slot, merged_content)
                
                # Apply merged metadata
                target_memory_slot = await self.storage.read_memory(target_slot)
                if target_memory_slot and (merge_result.tags_merged or merge_result.groups_merged):
                    if merge_result.tags_merged:
                        target_memory_slot.tags = merge_result.tags_merged
                    
                    if merge_result.groups_merged:
                        # Use the first group path if multiple
                        target_memory_slot.group_path = merge_result.groups_merged[0] if merge_result.groups_merged else None
                    
                    # Save updated metadata
                    await self.storage._save_slot(target_memory_slot)
                
                # Delete source slots if requested
                deleted_sources = []
                if delete_sources:
                    for source_slot in source_slots:
                        try:
                            success = await self.storage.delete_slot(source_slot)
                            if success:
                                deleted_sources.append(source_slot)
                        except Exception as e:
                            # Continue with other deletions even if one fails
                            pass
                
                # Format success response
                response_parts = [
                    f"✅ Successfully merged {len(source_slots)} slots into '{target_slot}'",
                    f"Final content: {merge_result.content_length:,} characters",
                    f"Duplicates removed: {merge_result.duplicates_removed} sections",
                    f"Merged at: {entry.timestamp.strftime('%Y-%m-%d %H:%M:%S')}",
                    "",
                    f"Source slots: {', '.join(source_slots)}"
                ]
                
                if merge_result.tags_merged:
                    response_parts.append(f"Tags merged: {', '.join(merge_result.tags_merged)}")
                
                if merge_result.groups_merged:
                    response_parts.append(f"Groups merged: {', '.join(merge_result.groups_merged)}")
                
                if deleted_sources:
                    response_parts.extend([
                        "",
                        f"🗑️  Deleted source slots: {', '.join(deleted_sources)}"
                    ])
                
                return [TextContent(type="text", text="\n".join(response_parts))]
            
            else:
                return [TextContent(type="text", text=f"Error: Unknown action '{action}'. Use 'preview' or 'merge'.")]
                
        except Exception as e:
            # Enhanced error reporting with debug info
            import traceback
            error_trace = traceback.format_exc()
            
            # Try to get debug info about loaded slots if available
            debug_info = ""
            try:
                if 'slots' in locals():
                    debug_info = f"\n\nDebug info:\n"
                    for i, slot in enumerate(slots):
                        debug_info += f"Slot {i} ({slot.slot_name}): has_content={hasattr(slot, 'content')}, has_name={hasattr(slot, 'name')}, type={type(slot)}\n"
            except:
                debug_info = "\n\nCould not retrieve debug info"
            
            return [TextContent(type="text", text=f"Merge operation failed: {str(e)}{debug_info}\n\nFull trace:\n{error_trace}")]

    async def _handle_compressmem(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """Handle compress tool call."""
        action = arguments.get("action", "analyze")
        slot_name = arguments.get("slot_name")
        force = arguments.get("force", False)
        
        try:
            if action == "stats":
                # Get compression statistics
                stats = await self.storage.get_compression_stats(slot_name)
                
                if slot_name:
                    # Single slot stats
                    from .compression import format_size
                    
                    response = [
                        f"# Compression Statistics: {slot_name}",
                        "",
                        f"**Total Entries:** {stats['total_entries']}",
                        f"**Compressed Entries:** {stats['compressed_entries']} ({stats['compression_percentage']:.1f}%)",
                        f"**Original Size:** {format_size(stats['total_original_size'])}",
                        f"**Compressed Size:** {format_size(stats['total_compressed_size'])}",
                        f"**Space Saved:** {format_size(stats['space_saved'])} ({stats['space_saved_percentage']:.1f}%)",
                        f"**Compression Ratio:** {stats['compression_ratio']:.3f}"
                    ]
                else:
                    # All slots stats
                    from .compression import format_size
                    
                    response = [
                        "# Overall Compression Statistics",
                        "",
                        f"**Total Slots:** {stats['total_slots']}",
                        f"**Total Entries:** {stats['total_entries']}",
                        f"**Compressed Entries:** {stats['compressed_entries']}",
                        f"**Original Size:** {format_size(stats['total_original_size'])}",
                        f"**Compressed Size:** {format_size(stats['total_compressed_size'])}",
                        f"**Space Saved:** {format_size(stats['space_saved'])} ({stats['space_saved_percentage']:.1f}%)",
                        f"**Average Compression Ratio:** {stats['compression_ratio']:.3f}"
                    ]
                
                return [TextContent(type="text", text="\n".join(response))]
            
            elif action == "analyze":
                # Analyze compression potential
                from .compression import ContentCompressor, format_compression_report
                
                compressor = ContentCompressor()
                
                if slot_name:
                    # Analyze single slot
                    slot = await self.storage.read_memory(slot_name)
                    if not slot:
                        return [TextContent(type="text", text=f"Memory slot '{slot_name}' not found")]
                    
                    slot_data = [slot.model_dump()]
                    stats = compressor.get_compression_stats(slot_data)
                    report = format_compression_report(stats)
                    
                    return [TextContent(type="text", text=report)]
                else:
                    # Analyze all slots
                    slots_info = await self.storage.list_memory_slots()
                    slot_data = []
                    
                    for slot_info in slots_info:
                        slot = await self.storage.read_memory(slot_info["name"])
                        if slot:
                            slot_data.append(slot.model_dump())
                    
                    stats = compressor.get_compression_stats(slot_data)
                    report = format_compression_report(stats)
                    
                    return [TextContent(type="text", text=report)]
            
            elif action == "compress":
                # Perform compression
                if slot_name:
                    # Compress single slot
                    compression_stats = await self.storage.compress_slot(slot_name, force)
                    
                    from .compression import format_size
                    
                    response = [
                        f"✅ Compression completed for '{slot_name}'",
                        "",
                        f"**Entries Processed:** {compression_stats['entries_processed']}",
                        f"**Entries Compressed:** {compression_stats['entries_compressed']}",
                        f"**Original Size:** {format_size(compression_stats['original_size'])}",
                        f"**Compressed Size:** {format_size(compression_stats['compressed_size'])}",
                        f"**Space Saved:** {format_size(compression_stats['space_saved'])}",
                        f"**Compression Ratio:** {compression_stats['compression_ratio']:.3f}"
                    ]
                    
                    return [TextContent(type="text", text="\n".join(response))]
                else:
                    # Compress all slots
                    slots_info = await self.storage.list_memory_slots()
                    total_stats = {
                        "slots_processed": 0,
                        "total_entries_processed": 0,
                        "total_entries_compressed": 0,
                        "total_original_size": 0,
                        "total_compressed_size": 0,
                        "total_space_saved": 0
                    }
                    
                    for slot_info in slots_info:
                        try:
                            compression_stats = await self.storage.compress_slot(slot_info["name"], force)
                            total_stats["slots_processed"] += 1
                            total_stats["total_entries_processed"] += compression_stats["entries_processed"]
                            total_stats["total_entries_compressed"] += compression_stats["entries_compressed"]
                            total_stats["total_original_size"] += compression_stats["original_size"]
                            total_stats["total_compressed_size"] += compression_stats["compressed_size"]
                            total_stats["total_space_saved"] += compression_stats["space_saved"]
                        except Exception:
                            continue
                    
                    from .compression import format_size
                    
                    overall_ratio = (total_stats["total_compressed_size"] / total_stats["total_original_size"] 
                                   if total_stats["total_original_size"] > 0 else 1.0)
                    
                    response = [
                        "✅ Bulk compression completed",
                        "",
                        f"**Slots Processed:** {total_stats['slots_processed']}",
                        f"**Total Entries Processed:** {total_stats['total_entries_processed']}",
                        f"**Total Entries Compressed:** {total_stats['total_entries_compressed']}",
                        f"**Total Original Size:** {format_size(total_stats['total_original_size'])}",
                        f"**Total Compressed Size:** {format_size(total_stats['total_compressed_size'])}",
                        f"**Total Space Saved:** {format_size(total_stats['total_space_saved'])}",
                        f"**Overall Compression Ratio:** {overall_ratio:.3f}"
                    ]
                    
                    return [TextContent(type="text", text="\n".join(response))]
            
            elif action == "decompress":
                # Perform decompression
                if not slot_name:
                    return [TextContent(type="text", text="Error: slot_name is required for decompress action")]
                
                decompression_stats = await self.storage.decompress_slot(slot_name)
                
                response = [
                    f"✅ Decompression completed for '{slot_name}'",
                    "",
                    f"**Entries Processed:** {decompression_stats['entries_processed']}",
                    f"**Entries Decompressed:** {decompression_stats['entries_decompressed']}",
                    f"**Success:** {'Yes' if decompression_stats['decompressed_successfully'] else 'Partial'}"
                ]
                
                return [TextContent(type="text", text="\n".join(response))]
            
            else:
                return [TextContent(type="text", text=f"Error: Unknown action '{action}'. Use 'analyze', 'compress', 'decompress', or 'stats'.")]
        
        except Exception as e:
            return [TextContent(type="text", text=f"Error: {str(e)}")]

    async def _handle_archivemem(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """Handle archive tool call."""
        action = arguments.get("action")
        slot_name = arguments.get("slot_name")
        reason = arguments.get("reason", "manual")
        days_inactive = arguments.get("days_inactive", 30)
        
        try:
            if action == "archive":
                # Archive a memory slot
                if not slot_name:
                    return [TextContent(type="text", text="Error: slot_name is required for archive action")]
                
                archive_result = await self.storage.archive_slot(slot_name, reason)
                
                from .compression import format_size
                
                response = [
                    f"✅ Memory slot '{slot_name}' archived successfully",
                    "",
                    f"**Archived At:** {archive_result['archived_at']}",
                    f"**Reason:** {archive_result['archive_reason']}",
                    f"**Original Size:** {format_size(archive_result['original_size'])}",
                    f"**Archived Size:** {format_size(archive_result['archived_size'])}",
                    f"**Space Saved:** {format_size(archive_result['space_saved'])}",
                    f"**Compression Ratio:** {archive_result['compression_ratio']:.3f}",
                    "",
                    f"The slot has been moved to archive storage and removed from active memory."
                ]
                
                return [TextContent(type="text", text="\n".join(response))]
            
            elif action == "restore":
                # Restore from archive
                if not slot_name:
                    return [TextContent(type="text", text="Error: slot_name is required for restore action")]
                
                restore_result = await self.storage.restore_from_archive(slot_name)
                
                response = [
                    f"✅ Memory slot '{slot_name}' restored from archive",
                    "",
                    f"**Restored At:** {restore_result['restored_at']}",
                    f"**Entry Count:** {restore_result['entry_count']}",
                    f"**Total Size:** {restore_result['total_size']:,} characters",
                    "",
                    f"The slot is now available in active memory storage."
                ]
                
                return [TextContent(type="text", text="\n".join(response))]
            
            elif action == "list":
                # List archived slots
                archives = await self.storage.list_archives(include_stats=True)
                
                if not archives:
                    return [TextContent(type="text", text="No archived memory slots found.")]
                
                response = [
                    f"# Archived Memory Slots ({len(archives)} total)",
                    ""
                ]
                
                from .compression import format_size
                
                for archive in archives:
                    days_ago = (datetime.now() - datetime.fromisoformat(archive["archived_at"])).days
                    
                    archive_info = [
                        f"## {archive['slot_name']}",
                        f"- **Archived:** {days_ago} days ago ({archive['archived_at'][:10]})",
                        f"- **Reason:** {archive['archive_reason']}",
                        f"- **Entries:** {archive['entry_count']}",
                        f"- **Original Size:** {format_size(archive['original_size'])}",
                        f"- **Archived Size:** {format_size(archive['archived_size'])}",
                        f"- **Space Saved:** {format_size(archive['space_saved'])}",
                    ]
                    
                    if archive.get("tags"):
                        archive_info.append(f"- **Tags:** {', '.join(archive['tags'])}")
                    
                    if archive.get("group_path"):
                        archive_info.append(f"- **Group:** {archive['group_path']}")
                    
                    response.extend(archive_info)
                    response.append("")
                
                return [TextContent(type="text", text="\n".join(response))]
            
            elif action == "stats":
                # Get archive statistics
                stats = await self.storage.get_archive_stats()
                
                if stats["total_archives"] == 0:
                    return [TextContent(type="text", text="No archived memory slots found.")]
                
                from .compression import format_size
                
                response = [
                    "# Archive Storage Statistics",
                    "",
                    f"**Total Archives:** {stats['total_archives']}",
                    f"**Original Size:** {format_size(stats['total_original_size'])}",
                    f"**Archived Size:** {format_size(stats['total_archived_size'])}",
                    f"**Space Saved:** {format_size(stats['total_savings'])} ({stats['savings_percentage']:.1f}%)",
                    f"**Average Compression:** {stats['average_compression_ratio']:.3f}"
                ]
                
                return [TextContent(type="text", text="\n".join(response))]
            
            elif action == "candidates":
                # Find archival candidates
                candidates = await self.storage.find_archival_candidates(days_inactive)
                
                if not candidates:
                    return [TextContent(type="text", text=f"No memory slots found that have been inactive for {days_inactive}+ days.")]
                
                response = [
                    f"# Archive Candidates (inactive for {days_inactive}+ days)",
                    "",
                    f"Found {len(candidates)} memory slots that could be archived:",
                    ""
                ]
                
                from .compression import format_size
                
                for slot_name, info in candidates:
                    response.extend([
                        f"## {slot_name}",
                        f"- **Last Updated:** {info['last_updated'][:10]} ({info['days_inactive']} days ago)",
                        f"- **Entries:** {info['entry_count']}",
                        f"- **Size:** {format_size(info['current_size'])}",
                    ])
                    
                    if info.get("tags"):
                        response.append(f"- **Tags:** {', '.join(info['tags'])}")
                    
                    if info.get("group_path"):
                        response.append(f"- **Group:** {info['group_path']}")
                    
                    response.append("")
                
                response.extend([
                    "To archive any of these slots, use:",
                    f"`memcord_archive slot_name=\"<slot_name>\" action=\"archive\" reason=\"inactive_{days_inactive}d\"`"
                ])
                
                return [TextContent(type="text", text="\n".join(response))]
            
            else:
                return [TextContent(type="text", text=f"Error: Unknown action '{action}'. Use 'archive', 'restore', 'list', 'stats', or 'candidates'.")]
        
        except Exception as e:
            return [TextContent(type="text", text=f"Error: Archive operation failed: {str(e)}")]

    async def _handle_status(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """Handle system status check."""
        try:
            include_details = arguments.get("include_details", False)
            
            # Get system status
            status = await self.status_monitor.get_system_status()
            
            response = [
                f"🏥 System Status: {status['overall_status'].upper()}",
                f"📊 Uptime: {status['uptime_seconds']:.0f}s ({status['uptime_seconds']/3600:.1f}h)",
                f"⚡ Active Operations: {status['active_operations']}",
                ""
            ]
            
            # Recent operation stats
            op_stats = status.get('recent_operation_stats', {})
            if op_stats.get('total_operations', 0) > 0:
                response.extend([
                    "📈 Recent Activity (Last Hour):",
                    f"  • Total Operations: {op_stats.get('total_operations', 0)}",
                    f"  • Success Rate: {op_stats.get('success_rate', 0):.1f}%",
                    f"  • Average Duration: {op_stats.get('avg_duration_ms', 0):.0f}ms",
                    ""
                ])
            
            # Health checks summary
            healthy = sum(1 for check in status['health_checks'] if check['status'] == 'healthy')
            total_checks = len(status['health_checks'])
            response.extend([
                f"🔍 Health Checks: {healthy}/{total_checks} healthy",
                ""
            ])
            
            # Resource usage
            resources = status.get('resource_usage', {})
            if resources:
                response.extend([
                    "💻 Resource Usage:",
                    f"  • CPU: {resources.get('cpu_percent', 0):.1f}%",
                    f"  • Memory: {resources.get('memory_percent', 0):.1f}%",
                    f"  • Disk: {resources.get('disk_usage_percent', 0):.1f}%",
                    ""
                ])
            
            if include_details:
                response.extend([
                    "🔍 Detailed Health Checks:",
                    ""
                ])
                for check in status['health_checks']:
                    status_emoji = {"healthy": "✅", "degraded": "⚠️", "unhealthy": "❌"}.get(check['status'], "❓")
                    response.append(f"  {status_emoji} {check['service']}: {check['status']} ({check['response_time']:.1f}ms)")
                    if check.get('error_message'):
                        response.append(f"    Error: {check['error_message']}")
                    if check.get('details'):
                        for key, value in check['details'].items():
                            if isinstance(value, dict):
                                continue  # Skip complex nested objects
                            response.append(f"    {key}: {value}")
                
                response.append("")
            
            response.append("💡 Use `memcord_diagnostics` for detailed analysis or `memcord_metrics` for performance data.")
            
            return [TextContent(type="text", text="\n".join(response))]
        
        except Exception as e:
            return [TextContent(type="text", text=f"Status check failed: {str(e)}")]

    async def _handle_metrics(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """Handle performance metrics request."""
        try:
            metric_name = arguments.get("metric_name")
            hours = arguments.get("hours", 1)
            
            if metric_name:
                # Get specific metric
                metrics_data = self.status_monitor.get_performance_metrics(metric_name, hours)
                
                response = [
                    f"📊 Performance Metric: {metric_name}",
                    f"📅 Time Window: {hours} hour(s)",
                    f"📈 Data Points: {metrics_data.get('data_points', 0)}",
                    ""
                ]
                
                summary = metrics_data.get('summary', {})
                if summary.get('count', 0) > 0:
                    unit = summary.get('unit', '')
                    response.extend([
                        "📋 Summary:",
                        f"  • Count: {summary.get('count', 0)}",
                        f"  • Average: {summary.get('avg', 0):.2f}{unit}",
                        f"  • Min: {summary.get('min', 0):.2f}{unit}",
                        f"  • Max: {summary.get('max', 0):.2f}{unit}",
                        f"  • Latest: {summary.get('latest', 0):.2f}{unit}",
                        ""
                    ])
                else:
                    response.append("No data available for this metric in the specified time window.")
            
            else:
                # Get all metrics summary
                metrics_data = self.status_monitor.get_performance_metrics(hours=hours)
                available_metrics = metrics_data.get('available_metrics', [])
                summaries = metrics_data.get('summaries', {})
                
                response = [
                    f"📊 Performance Metrics Overview",
                    f"📅 Time Window: {hours} hour(s)",
                    f"📈 Available Metrics: {len(available_metrics)}",
                    ""
                ]
                
                if summaries:
                    response.append("📋 Metrics Summary:")
                    for metric, summary in summaries.items():
                        if summary.get('count', 0) > 0:
                            unit = summary.get('unit', '')
                            response.append(f"  • {metric}: avg={summary.get('avg', 0):.2f}{unit}, count={summary.get('count', 0)}")
                    response.append("")
                
                if available_metrics:
                    response.extend([
                        "🔍 Available Metrics:",
                        "  " + ", ".join(available_metrics),
                        "",
                        "💡 Use `memcord_metrics metric_name=\"<name>\"` for detailed metric data."
                    ])
                else:
                    response.append("No metrics available yet. Metrics are collected as operations are performed.")
            
            return [TextContent(type="text", text="\n".join(response))]
        
        except Exception as e:
            return [TextContent(type="text", text=f"Metrics request failed: {str(e)}")]

    async def _handle_logs(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """Handle operation logs request."""
        try:
            tool_name = arguments.get("tool_name")
            status = arguments.get("status")
            hours = arguments.get("hours", 1)
            limit = arguments.get("limit", 100)
            
            # Convert hours to datetime
            from datetime import timedelta
            since = datetime.now() - timedelta(hours=hours)
            
            # Get filtered logs
            filters = {}
            if tool_name:
                filters['tool_name'] = tool_name
            if status:
                filters['status'] = status
            filters['since'] = since
            filters['limit'] = limit
            
            logs_data = self.status_monitor.get_operation_logs(**filters)
            logs = logs_data.get('logs', [])
            stats = logs_data.get('stats', {})
            
            response = [
                f"📋 Operation Logs",
                f"📅 Time Window: {hours} hour(s)",
                f"🔍 Filters: tool={tool_name or 'all'}, status={status or 'all'}",
                f"📊 Showing {len(logs)} of {logs_data.get('total_count', 0)} logs",
                ""
            ]
            
            # Show overall stats
            if stats.get('total_operations', 0) > 0:
                response.extend([
                    "📈 Statistics:",
                    f"  • Total Operations: {stats.get('total_operations', 0)}",
                    f"  • Success Rate: {stats.get('success_rate', 0):.1f}%",
                    f"  • Failed Operations: {stats.get('failed_operations', 0)}",
                ])
                
                if stats.get('avg_duration_ms'):
                    response.append(f"  • Average Duration: {stats.get('avg_duration_ms', 0):.0f}ms")
                
                response.append("")
            
            # Show recent logs
            if logs:
                response.append("🔍 Recent Operations:")
                for log in logs[:20]:  # Show last 20 logs
                    start_time = datetime.fromisoformat(log['start_time'].replace('Z', '+00:00')) if isinstance(log['start_time'], str) else log['start_time']
                    time_str = start_time.strftime("%H:%M:%S")
                    
                    status_emoji = {
                        "completed": "✅",
                        "failed": "❌",
                        "started": "🔄",
                        "timeout": "⏰"
                    }.get(log['status'], "❓")
                    
                    duration_str = f" ({log['duration_ms']:.0f}ms)" if log.get('duration_ms') else ""
                    
                    response.append(f"  {status_emoji} {time_str} {log['tool_name']}{duration_str}")
                    
                    if log.get('error_message'):
                        response.append(f"    Error: {log['error_message']}")
                
                if len(logs) > 20:
                    response.append(f"  ... and {len(logs) - 20} more entries")
            
            else:
                response.append("No logs found matching the specified criteria.")
            
            response.extend([
                "",
                "💡 Use `memcord_diagnostics check_type=\"performance\"` for detailed analysis."
            ])
            
            return [TextContent(type="text", text="\n".join(response))]
        
        except Exception as e:
            return [TextContent(type="text", text=f"Logs request failed: {str(e)}")]

    async def _handle_diagnostics(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """Handle system diagnostics request."""
        try:
            check_type = arguments.get("check_type", "health")
            
            if check_type == "health":
                # Run health checks
                health_checks = await self.status_monitor.diagnostic_tool.run_health_checks()
                
                response = [
                    "🏥 System Health Diagnostics",
                    "=" * 40,
                    ""
                ]
                
                for check in health_checks:
                    status_emoji = {"healthy": "✅", "degraded": "⚠️", "unhealthy": "❌", "unknown": "❓"}.get(check.status, "❓")
                    response.extend([
                        f"{status_emoji} {check.service.upper()}: {check.status}",
                        f"  Response Time: {check.response_time:.1f}ms",
                    ])
                    
                    if check.error_message:
                        response.append(f"  Error: {check.error_message}")
                    
                    # Show relevant details
                    details = check.details
                    if details:
                        if 'slot_count' in details:
                            response.append(f"  Memory Slots: {details['slot_count']}")
                        if 'process_memory_mb' in details:
                            response.append(f"  Memory Usage: {details['process_memory_mb']:.1f}MB")
                        if 'disk_free_gb' in details:
                            response.append(f"  Disk Free: {details['disk_free_gb']:.1f}GB")
                        if 'python_version' in details:
                            version = details['python_version'].split()[0]
                            response.append(f"  Python: {version}")
                    
                    response.append("")
                
            elif check_type == "performance":
                # Performance analysis
                analysis = self.status_monitor.diagnostic_tool.analyze_performance_issues(
                    self.status_monitor.metrics_collector,
                    self.status_monitor.operation_logger
                )
                
                response = [
                    "📊 Performance Analysis",
                    "=" * 40,
                    f"Analysis Time: {analysis['timestamp']}",
                    ""
                ]
                
                issues = analysis.get('issues', [])
                if issues:
                    response.append("⚠️ Issues Detected:")
                    for issue in issues:
                        severity_emoji = {"critical": "🚨", "warning": "⚠️", "info": "ℹ️"}.get(issue['severity'], "❓")
                        response.append(f"  {severity_emoji} {issue['description']}")
                    response.append("")
                else:
                    response.append("✅ No performance issues detected.")
                    response.append("")
                
                recommendations = analysis.get('recommendations', [])
                if recommendations:
                    response.append("💡 Recommendations:")
                    for rec in recommendations:
                        response.append(f"  • {rec}")
                    response.append("")
            
            elif check_type == "full_report":
                # Generate comprehensive report
                report = await self.status_monitor.generate_full_report()
                
                response = [
                    "📋 Comprehensive System Report",
                    "=" * 50,
                    f"Generated: {report['timestamp']}",
                    ""
                ]
                
                # Health summary
                health_checks = report.get('health_checks', [])
                healthy_count = sum(1 for check in health_checks if check['status'] == 'healthy')
                response.extend([
                    f"🏥 Health Status: {healthy_count}/{len(health_checks)} services healthy",
                    ""
                ])
                
                # Resource usage
                resources = report.get('resource_usage', {})
                if resources:
                    response.extend([
                        "💻 Current Resource Usage:",
                        f"  • CPU: {resources.get('cpu_percent', 0):.1f}%",
                        f"  • Memory: {resources.get('memory_percent', 0):.1f}% ({resources.get('memory_used_mb', 0):.0f}MB)",
                        f"  • Disk: {resources.get('disk_usage_percent', 0):.1f}% ({resources.get('disk_free_gb', 0):.1f}GB free)",
                        ""
                    ])
                
                # Operation statistics
                op_stats = report.get('operation_stats', {})
                if op_stats.get('total_operations', 0) > 0:
                    response.extend([
                        "📊 Operation Statistics (24h):",
                        f"  • Total Operations: {op_stats.get('total_operations', 0)}",
                        f"  • Success Rate: {op_stats.get('success_rate', 0):.1f}%",
                        f"  • Average Duration: {op_stats.get('avg_duration_ms', 0):.0f}ms",
                        ""
                    ])
                
                # Performance analysis summary
                perf_analysis = report.get('performance_analysis', {})
                issues = perf_analysis.get('issues', [])
                if issues:
                    response.append(f"⚠️ {len(issues)} performance issues detected")
                    response.append("   Use `memcord_diagnostics check_type=\"performance\"` for details")
                else:
                    response.append("✅ No performance issues detected")
                
                response.extend([
                    "",
                    "💡 For detailed analysis of specific areas, use:",
                    "  • `memcord_diagnostics check_type=\"health\"` - Health checks",
                    "  • `memcord_diagnostics check_type=\"performance\"` - Performance analysis",
                    "  • `memcord_metrics` - Performance metrics",
                    "  • `memcord_logs` - Operation logs"
                ])
            
            else:
                return [TextContent(type="text", text=f"Invalid check_type '{check_type}'. Use 'health', 'performance', or 'full_report'.")]
            
            return [TextContent(type="text", text="\n".join(response))]
        
        except Exception as e:
            return [TextContent(type="text", text=f"Diagnostics failed: {str(e)}")]

    async def run(self):
        """Run the MCP server."""
        from mcp.server.stdio import stdio_server
        
        async with stdio_server() as (read_stream, write_stream):
            await self.app.run(
                read_stream, 
                write_stream, 
                self.app.create_initialization_options()
            )


def main():
    """Main entry point."""
    server = ChatMemoryServer()
    asyncio.run(server.run())


if __name__ == "__main__":
    main()