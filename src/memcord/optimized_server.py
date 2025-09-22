"""Optimized MCP server with token-efficient schemas and responses.

This module provides an optimized version of the ChatMemoryServer that uses
reduced-token schemas and response optimization for better performance.
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

from .server import ChatMemoryServer
from .optimized_schemas import OptimizedSchemas
from .response_optimizer import ResponseOptimizer


class OptimizedChatMemoryServer(ChatMemoryServer):
    """Token-optimized version of ChatMemoryServer."""
    
    def __init__(self, memory_dir: str = "memory_slots", shared_dir: str = "shared_memories", 
                 enable_advanced_tools: bool = None, enable_response_optimization: bool = True):
        """Initialize optimized server.
        
        Args:
            memory_dir: Directory for memory storage
            shared_dir: Directory for shared memories  
            enable_advanced_tools: Enable advanced tools
            enable_response_optimization: Enable response optimization
        """
        super().__init__(memory_dir, shared_dir, enable_advanced_tools)
        
        # Initialize optimizers
        self.schema_optimizer = OptimizedSchemas()
        self.response_optimizer = ResponseOptimizer() if enable_response_optimization else None
        
        # Override setup to use optimized schemas
        self._setup_optimized_handlers()
    
    def _get_basic_tools(self) -> List[Tool]:
        """Get optimized basic tools (overrides parent method)."""
        return self.schema_optimizer.get_basic_tools_optimized()
    
    def _get_advanced_tools(self) -> List[Tool]:
        """Get optimized advanced tools (overrides parent method)."""
        return self.schema_optimizer.get_advanced_tools_optimized()
    
    def _optimize_response(self, content: str) -> List[TextContent]:
        """Optimize response content if optimization is enabled."""
        if self.response_optimizer:
            return self.response_optimizer.optimize_response(content, mode="auto")
        else:
            return [TextContent(type="text", text=content)]
    
    def _setup_optimized_handlers(self):
        """Set up MCP server handlers with response optimization."""
        
        @self.app.list_tools()
        async def list_tools() -> List[Tool]:
            """List available optimized tools."""
            tools = self._get_basic_tools()
            if self.enable_advanced_tools:
                tools.extend(self._get_advanced_tools())
            return tools

        @self.app.call_tool()
        async def call_tool(name: str, arguments: Dict[str, Any]) -> Sequence[TextContent]:
            """Handle tool calls with security validation and response optimization."""
            operation_id = secrets.token_hex(8)
            client_id = "default"
            
            try:
                # Security validation
                allowed, error_msg = self.security.validate_request(client_id, name, arguments)
                if not allowed:
                    return self._optimize_response(f"🚫 Security check failed: {error_msg}")
                
                # Start operation timeout tracking
                deadline = self.security.timeout_manager.start_operation(operation_id, name)
                
                try:
                    # Get response from parent implementation
                    result = await super().call_tool_direct(name, arguments)
                    
                    # Optimize the response if enabled
                    if result and len(result) > 0:
                        original_text = result[0].text
                        return self._optimize_response(original_text)
                    else:
                        return result
                    
                finally:
                    # Clean up operation tracking
                    self.security.timeout_manager.finish_operation(operation_id)
                    
            except Exception as e:
                # Handle errors with optimization
                handled_error = self.error_handler.handle_error(e, name, {'operation_id': operation_id})
                return self._optimize_response(handled_error.get_user_message())

        @self.app.list_resources()
        async def list_resources() -> List[Resource]:
            """List MCP file resources for memory slots."""
            # Use parent implementation
            resources = []
            slots_info = await self.storage.list_memory_slots()
            
            for slot_info in slots_info:
                slot_name = slot_info["name"]
                for fmt in ["md", "txt", "json"]:
                    resources.append(Resource(
                        uri=f"memory://{slot_name}.{fmt}",
                        name=f"{slot_name} ({fmt.upper()})",
                        mimeType=self._get_mime_type(fmt),
                        description=f"Memory slot '{slot_name}' in {fmt.upper()} format"
                    ))
            
            return resources

        @self.app.read_resource()
        async def read_resource(uri: str) -> str:
            """Read MCP file resource with optimization."""
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
                
                # Optimize resource content if large
                if len(content) > 2000 and self.response_optimizer:
                    optimized_result = self.response_optimizer.optimize_response(content, mode="compress")
                    return optimized_result[0].text if optimized_result else content
                
                return content
                
            except Exception as e:
                raise ValueError(f"Error reading resource '{uri}': {str(e)}")
    
    def get_optimization_stats(self) -> Dict[str, Any]:
        """Get optimization statistics."""
        # Calculate schema savings
        original_basic = super()._get_basic_tools()
        original_advanced = super()._get_advanced_tools()
        optimized_basic = self._get_basic_tools()
        optimized_advanced = self._get_advanced_tools()
        
        def calculate_tool_size(tools):
            total_size = 0
            for tool in tools:
                tool_json = json.dumps({
                    "name": tool.name,
                    "description": tool.description,
                    "inputSchema": tool.inputSchema
                }, indent=None)
                total_size += len(tool_json)
            return total_size
        
        original_basic_size = calculate_tool_size(original_basic)
        original_advanced_size = calculate_tool_size(original_advanced)
        optimized_basic_size = calculate_tool_size(optimized_basic)
        optimized_advanced_size = calculate_tool_size(optimized_advanced)
        
        total_original = original_basic_size + original_advanced_size
        total_optimized = optimized_basic_size + optimized_advanced_size
        
        schema_reduction = ((total_original - total_optimized) / total_original) * 100
        tokens_saved = (total_original - total_optimized) // 4  # Rough estimate
        
        return {
            "schema_optimization": {
                "original_size": total_original,
                "optimized_size": total_optimized, 
                "reduction_percentage": schema_reduction,
                "tokens_saved": tokens_saved
            },
            "response_optimization": {
                "enabled": self.response_optimizer is not None,
                "compression_threshold": self.response_optimizer.compression_threshold if self.response_optimizer else None
            },
            "tools_count": {
                "basic": len(optimized_basic),
                "advanced": len(optimized_advanced) if self.enable_advanced_tools else 0,
                "total": len(optimized_basic) + (len(optimized_advanced) if self.enable_advanced_tools else 0)
            }
        }


class TokenUsageMonitor:
    """Monitor and track token usage for optimization analysis."""
    
    def __init__(self):
        self.request_stats = []
        self.response_stats = []
        
    def record_request(self, tool_name: str, arguments: Dict[str, Any], schema_size: int):
        """Record a tool request for analysis."""
        self.request_stats.append({
            "tool_name": tool_name,
            "arguments": arguments,
            "schema_size": schema_size,
            "timestamp": time.time()
        })
    
    def record_response(self, tool_name: str, original_size: int, optimized_size: int, optimization_time: float):
        """Record a response optimization for analysis."""
        self.response_stats.append({
            "tool_name": tool_name,
            "original_size": original_size,
            "optimized_size": optimized_size,
            "optimization_time": optimization_time,
            "reduction_pct": ((original_size - optimized_size) / original_size) * 100 if original_size > 0 else 0,
            "timestamp": time.time()
        })
    
    def get_summary_stats(self) -> Dict[str, Any]:
        """Get summary statistics."""
        if not self.response_stats:
            return {"message": "No optimization data recorded"}
        
        total_original = sum(stat["original_size"] for stat in self.response_stats)
        total_optimized = sum(stat["optimized_size"] for stat in self.response_stats)
        total_reduction = ((total_original - total_optimized) / total_original) * 100 if total_original > 0 else 0
        
        avg_optimization_time = sum(stat["optimization_time"] for stat in self.response_stats) / len(self.response_stats)
        
        return {
            "requests_processed": len(self.request_stats),
            "responses_optimized": len(self.response_stats),
            "total_original_size": total_original,
            "total_optimized_size": total_optimized,
            "total_reduction_pct": total_reduction,
            "tokens_saved": (total_original - total_optimized) // 4,
            "avg_optimization_time_ms": avg_optimization_time * 1000,
            "most_optimized_tool": max(self.response_stats, key=lambda x: x["reduction_pct"])["tool_name"] if self.response_stats else None
        }


def create_optimized_server(memory_dir: str = "memory_slots", 
                          shared_dir: str = "shared_memories",
                          enable_advanced_tools: bool = None,
                          enable_response_optimization: bool = True) -> OptimizedChatMemoryServer:
    """Create an optimized ChatMemoryServer instance.
    
    Args:
        memory_dir: Directory for memory storage
        shared_dir: Directory for shared memories
        enable_advanced_tools: Enable advanced tools (None = auto-detect from env)
        enable_response_optimization: Enable response optimization
    
    Returns:
        Optimized server instance
    """
    return OptimizedChatMemoryServer(
        memory_dir=memory_dir,
        shared_dir=shared_dir, 
        enable_advanced_tools=enable_advanced_tools,
        enable_response_optimization=enable_response_optimization
    )