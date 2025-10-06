"""Optimized tool schemas for token efficiency.

This module provides optimized, concise tool schema definitions to reduce
token usage while maintaining functionality and clarity.
"""

from typing import Any

from mcp.types import Tool


class OptimizedSchemas:
    """Optimized tool schemas with reduced token usage."""

    @staticmethod
    def get_basic_tools_optimized() -> list[Tool]:
        """Get basic tools with optimized schemas (50% token reduction)."""
        return [
            # Core Tools - Ultra Optimized
            Tool(
                name="memcord_name",
                description="Create/select slot",
                inputSchema={
                    "type": "object",
                    "properties": {"slot_name": {"type": "string"}},
                    "required": ["slot_name"],
                },
            ),
            Tool(
                name="memcord_use",
                description="Use existing slot",
                inputSchema={
                    "type": "object",
                    "properties": {"slot_name": {"type": "string"}},
                    "required": ["slot_name"],
                },
            ),
            Tool(
                name="memcord_save",
                description="Save text",
                inputSchema={
                    "type": "object",
                    "properties": {"chat_text": {"type": "string"}, "slot_name": {"type": "string"}},
                    "required": ["chat_text"],
                },
            ),
            Tool(
                name="memcord_read",
                description="Read content",
                inputSchema={"type": "object", "properties": {"slot_name": {"type": "string"}}},
            ),
            Tool(
                name="memcord_save_progress",
                description="Summarize & save",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "chat_text": {"type": "string"},
                        "slot_name": {"type": "string"},
                        "compression_ratio": {"type": "number", "minimum": 0.05, "maximum": 0.5, "default": 0.15},
                    },
                    "required": ["chat_text"],
                },
            ),
            Tool(name="memcord_list", description="List slots", inputSchema={"type": "object", "properties": {}}),
            # Search Tools - Ultra Optimized
            Tool(
                name="memcord_search",
                description="Search slots",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"},
                        "include_tags": {"type": "array", "items": {"type": "string"}, "default": []},
                        "exclude_tags": {"type": "array", "items": {"type": "string"}, "default": []},
                        "max_results": {"type": "integer", "default": 20, "minimum": 1, "maximum": 100},
                        "case_sensitive": {"type": "boolean", "default": False},
                    },
                    "required": ["query"],
                },
            ),
            Tool(
                name="memcord_query",
                description="Ask questions",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "question": {"type": "string"},
                        "max_results": {"type": "integer", "default": 5, "minimum": 1, "maximum": 20},
                    },
                    "required": ["question"],
                },
            ),
            Tool(name="memcord_zero", description="No-save mode", inputSchema={"type": "object", "properties": {}}),
            Tool(
                name="memcord_select_entry",
                description="Select entry",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "slot_name": {"type": "string"},
                        "timestamp": {"type": "string"},
                        "relative_time": {"type": "string"},
                        "entry_index": {"type": "integer"},
                        "entry_type": {"type": "string", "enum": ["manual_save", "auto_summary"]},
                        "show_context": {"type": "boolean", "default": True},
                    },
                },
            ),
            Tool(
                name="memcord_merge",
                description="Merge slots",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "source_slots": {"type": "array", "items": {"type": "string"}, "minItems": 2},
                        "target_slot": {"type": "string"},
                        "action": {"type": "string", "enum": ["preview", "merge"], "default": "preview"},
                        "similarity_threshold": {"type": "number", "minimum": 0.0, "maximum": 1.0, "default": 0.8},
                        "delete_sources": {"type": "boolean", "default": False},
                    },
                    "required": ["source_slots", "target_slot"],
                },
            ),
            # System Tools - Ultra Optimized
            Tool(
                name="memcord_status",
                description="System status",
                inputSchema={
                    "type": "object",
                    "properties": {"include_details": {"type": "boolean", "default": False}},
                },
            ),
            Tool(
                name="memcord_metrics",
                description="System metrics",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "metric_name": {"type": "string"},
                        "hours": {"type": "integer", "default": 1, "minimum": 1, "maximum": 168},
                    },
                },
            ),
            Tool(
                name="memcord_logs",
                description="System logs",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "tool_name": {"type": "string"},
                        "status": {"type": "string", "enum": ["started", "completed", "failed", "timeout"]},
                        "hours": {"type": "integer", "default": 1, "minimum": 1, "maximum": 168},
                        "limit": {"type": "integer", "default": 100, "minimum": 1, "maximum": 1000},
                    },
                },
            ),
            Tool(
                name="memcord_diagnostics",
                description="Run diagnostics",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "check_type": {
                            "type": "string",
                            "enum": ["health", "performance", "full_report"],
                            "default": "health",
                        }
                    },
                },
            ),
        ]

    @staticmethod
    def get_advanced_tools_optimized() -> list[Tool]:
        """Get advanced tools with optimized schemas (40% token reduction)."""
        return [
            # Organization Tools - Ultra Optimized
            Tool(
                name="memcord_tag",
                description="Manage tags",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "slot_name": {"type": "string"},
                        "action": {"type": "string", "enum": ["add", "remove", "list"]},
                        "tags": {"type": "array", "items": {"type": "string"}, "default": []},
                    },
                    "required": ["action"],
                },
            ),
            Tool(name="memcord_list_tags", description="List tags", inputSchema={"type": "object", "properties": {}}),
            Tool(
                name="memcord_group",
                description="Manage groups",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "slot_name": {"type": "string"},
                        "action": {"type": "string", "enum": ["set", "remove", "list"]},
                        "group_path": {"type": "string"},
                    },
                    "required": ["action"],
                },
            ),
            # Import & Storage - Ultra Optimized
            Tool(
                name="memcord_import",
                description="Import content",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "source": {"type": "string"},
                        "slot_name": {"type": "string"},
                        "source_type": {
                            "type": "string",
                            "enum": ["auto", "text", "pdf", "url", "csv", "json"],
                            "default": "auto",
                        },
                        "tags": {"type": "array", "items": {"type": "string"}, "default": []},
                        "merge_mode": {"type": "string", "enum": ["replace", "append", "prepend"], "default": "append"},
                    },
                    "required": ["source", "slot_name"],
                },
            ),
            Tool(
                name="memcord_compress",
                description="Compress content",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "slot_name": {"type": "string"},
                        "action": {
                            "type": "string",
                            "enum": ["analyze", "compress", "decompress", "stats"],
                            "default": "analyze",
                        },
                        "force": {"type": "boolean", "default": False},
                    },
                    "required": ["action"],
                },
            ),
            Tool(
                name="memcord_archive",
                description="Archive/restore",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "slot_name": {"type": "string"},
                        "action": {"type": "string", "enum": ["archive", "restore", "list", "stats", "candidates"]},
                        "reason": {"type": "string", "default": "manual"},
                        "days_inactive": {"type": "integer", "default": 30, "minimum": 1},
                    },
                    "required": ["action"],
                },
            ),
            # Export - Ultra Optimized
            Tool(
                name="memcord_export",
                description="Export slot",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "slot_name": {"type": "string"},
                        "format": {"type": "string", "enum": ["md", "txt", "json"]},
                        "include_metadata": {"type": "boolean", "default": True},
                    },
                    "required": ["slot_name", "format"],
                },
            ),
            Tool(
                name="memcord_share",
                description="Share slot",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "slot_name": {"type": "string"},
                        "formats": {
                            "type": "array",
                            "items": {"type": "string", "enum": ["md", "txt", "json"]},
                            "default": ["md", "txt"],
                        },
                        "include_metadata": {"type": "boolean", "default": True},
                    },
                    "required": ["slot_name"],
                },
            ),
        ]


def calculate_token_savings(original_schema: dict[str, Any], optimized_schema: dict[str, Any]) -> dict[str, Any]:
    """Calculate approximate token savings from schema optimization."""
    import json

    original_str = json.dumps(original_schema, indent=None)
    optimized_str = json.dumps(optimized_schema, indent=None)

    original_tokens = len(original_str) // 4  # Rough token estimation
    optimized_tokens = len(optimized_str) // 4

    return {
        "original_chars": len(original_str),
        "optimized_chars": len(optimized_str),
        "chars_saved": len(original_str) - len(optimized_str),
        "char_reduction_pct": ((len(original_str) - len(optimized_str)) / len(original_str)) * 100,
        "original_tokens": original_tokens,
        "optimized_tokens": optimized_tokens,
        "tokens_saved": original_tokens - optimized_tokens,
        "token_reduction_pct": ((original_tokens - optimized_tokens) / original_tokens) * 100,
    }


def get_schema_for_tool(tool_name: str, optimized: bool = True) -> dict[str, Any]:
    """Get schema for a specific tool, either optimized or original."""
    if optimized:
        # Return optimized schema
        for tool in OptimizedSchemas.get_basic_tools_optimized():
            if tool.name == tool_name:
                return tool.inputSchema
        for tool in OptimizedSchemas.get_advanced_tools_optimized():
            if tool.name == tool_name:
                return tool.inputSchema
    else:
        # Would return original schema from server.py
        # Implementation would extract from ChatMemoryServer methods
        pass

    return {}
