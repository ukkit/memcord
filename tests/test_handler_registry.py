"""Tests for the handler registry module.

Tests the handler registration, dispatch, categorization, and tool generation
functionality introduced in the server.py optimization (Phase 1).
"""

import pytest
from mcp.types import TextContent, Tool

from memcord.handler_registry import HandlerInfo, HandlerRegistry, handler_registry


class TestHandlerInfo:
    """Tests for HandlerInfo dataclass."""

    def test_handler_info_creation(self):
        """Test creating a HandlerInfo instance."""

        async def sample_handler(self, args):
            return [TextContent(type="text", text="result")]

        info = HandlerInfo(
            name="test_tool",
            handler=sample_handler,
            category="basic",
            description="Test tool description",
            input_schema={"type": "object", "properties": {}},
            requires_advanced=False,
        )

        assert info.name == "test_tool"
        assert info.handler == sample_handler
        assert info.category == "basic"
        assert info.description == "Test tool description"
        assert info.requires_advanced is False

    def test_handler_info_advanced_default(self):
        """Test that requires_advanced defaults to False."""

        async def sample_handler(self, args):
            return []

        info = HandlerInfo(
            name="test",
            handler=sample_handler,
            category="basic",
            description="Test",
            input_schema={},
        )

        assert info.requires_advanced is False


class TestHandlerRegistry:
    """Tests for HandlerRegistry class."""

    @pytest.fixture
    def registry(self):
        """Provide a fresh registry for each test."""
        return HandlerRegistry()

    def test_registry_initialization(self, registry):
        """Test registry initializes empty."""
        assert len(registry) == 0
        assert registry.get_all() == {}

    def test_register_basic_handler(self, registry):
        """Test registering a basic handler."""

        @registry.register(
            "memcord_test",
            category="basic",
            description="Test tool",
            input_schema={"type": "object", "properties": {}},
        )
        async def test_handler(self, arguments):
            return [TextContent(type="text", text="test")]

        assert len(registry) == 1
        assert "memcord_test" in registry
        assert registry.dispatch("memcord_test") is not None

    def test_register_advanced_handler(self, registry):
        """Test registering an advanced handler."""

        @registry.register(
            "memcord_advanced",
            category="advanced",
            description="Advanced tool",
            input_schema={"type": "object"},
            requires_advanced=True,
        )
        async def advanced_handler(self, arguments):
            return []

        info = registry.dispatch("memcord_advanced")
        assert info is not None
        assert info.requires_advanced is True
        assert info.category == "advanced"

    def test_register_multiple_handlers(self, registry):
        """Test registering multiple handlers."""

        @registry.register("tool_1", category="basic", description="Tool 1", input_schema={})
        async def handler_1(self, args):
            return []

        @registry.register("tool_2", category="basic", description="Tool 2", input_schema={})
        async def handler_2(self, args):
            return []

        @registry.register("tool_3", category="advanced", description="Tool 3", input_schema={}, requires_advanced=True)
        async def handler_3(self, args):
            return []

        assert len(registry) == 3
        assert "tool_1" in registry
        assert "tool_2" in registry
        assert "tool_3" in registry

    def test_dispatch_returns_handler_info(self, registry):
        """Test dispatch returns correct HandlerInfo."""

        @registry.register(
            "dispatch_test",
            category="basic",
            description="Dispatch test",
            input_schema={"type": "object", "properties": {"arg1": {"type": "string"}}},
        )
        async def dispatch_handler(self, arguments):
            return [TextContent(type="text", text=arguments.get("arg1", ""))]

        info = registry.dispatch("dispatch_test")

        assert info is not None
        assert info.name == "dispatch_test"
        assert info.category == "basic"
        assert info.description == "Dispatch test"
        assert "arg1" in info.input_schema["properties"]

    def test_dispatch_unknown_handler(self, registry):
        """Test dispatch returns None for unknown handlers."""
        result = registry.dispatch("nonexistent_tool")
        assert result is None

    def test_get_all_handlers(self, registry):
        """Test getting all registered handlers."""

        @registry.register("all_test_1", category="basic", description="Test 1", input_schema={})
        async def handler_1(self, args):
            return []

        @registry.register("all_test_2", category="basic", description="Test 2", input_schema={})
        async def handler_2(self, args):
            return []

        all_handlers = registry.get_all()

        assert len(all_handlers) == 2
        assert "all_test_1" in all_handlers
        assert "all_test_2" in all_handlers
        # Ensure it's a copy, not the original dict
        all_handlers["new_key"] = "test"
        assert "new_key" not in registry.get_all()

    def test_get_by_category(self, registry):
        """Test getting handlers by category."""

        @registry.register("basic_1", category="basic", description="Basic 1", input_schema={})
        async def basic_handler_1(self, args):
            return []

        @registry.register("basic_2", category="basic", description="Basic 2", input_schema={})
        async def basic_handler_2(self, args):
            return []

        @registry.register("advanced_1", category="advanced", description="Advanced 1", input_schema={})
        async def advanced_handler_1(self, args):
            return []

        @registry.register("monitoring_1", category="monitoring", description="Monitoring 1", input_schema={})
        async def monitoring_handler_1(self, args):
            return []

        basic_handlers = registry.get_by_category("basic")
        advanced_handlers = registry.get_by_category("advanced")
        monitoring_handlers = registry.get_by_category("monitoring")
        unknown_handlers = registry.get_by_category("unknown")

        assert len(basic_handlers) == 2
        assert len(advanced_handlers) == 1
        assert len(monitoring_handlers) == 1
        assert len(unknown_handlers) == 0

        assert all(h.category == "basic" for h in basic_handlers)
        assert all(h.category == "advanced" for h in advanced_handlers)

    def test_get_tools_basic_only(self, registry):
        """Test generating Tool objects excluding advanced tools."""

        @registry.register("basic_tool", category="basic", description="Basic tool", input_schema={"type": "object"})
        async def basic_handler(self, args):
            return []

        @registry.register(
            "advanced_tool",
            category="advanced",
            description="Advanced tool",
            input_schema={"type": "object"},
            requires_advanced=True,
        )
        async def advanced_handler(self, args):
            return []

        tools = registry.get_tools(include_advanced=False)

        assert len(tools) == 1
        assert tools[0].name == "basic_tool"
        assert all(isinstance(t, Tool) for t in tools)

    def test_get_tools_include_advanced(self, registry):
        """Test generating Tool objects including advanced tools."""

        @registry.register("basic_tool", category="basic", description="Basic tool", input_schema={"type": "object"})
        async def basic_handler(self, args):
            return []

        @registry.register(
            "advanced_tool",
            category="advanced",
            description="Advanced tool",
            input_schema={"type": "object"},
            requires_advanced=True,
        )
        async def advanced_handler(self, args):
            return []

        tools = registry.get_tools(include_advanced=True)

        assert len(tools) == 2
        tool_names = [t.name for t in tools]
        assert "basic_tool" in tool_names
        assert "advanced_tool" in tool_names

    def test_get_tools_schema_format(self, registry):
        """Test that generated Tools have correct schema format."""

        input_schema = {
            "type": "object",
            "properties": {
                "slot_name": {"type": "string", "description": "Memory slot name"},
                "content": {"type": "string", "description": "Content to save"},
            },
            "required": ["content"],
        }

        @registry.register(
            "schema_test",
            category="basic",
            description="Schema test tool",
            input_schema=input_schema,
        )
        async def schema_handler(self, args):
            return []

        tools = registry.get_tools()

        assert len(tools) == 1
        tool = tools[0]
        assert tool.name == "schema_test"
        assert tool.description == "Schema test tool"
        assert tool.inputSchema == input_schema

    def test_is_advanced_tool(self, registry):
        """Test checking if a tool requires advanced mode."""

        @registry.register("basic", category="basic", description="Basic", input_schema={})
        async def basic_handler(self, args):
            return []

        @registry.register(
            "advanced", category="advanced", description="Advanced", input_schema={}, requires_advanced=True
        )
        async def advanced_handler(self, args):
            return []

        assert registry.is_advanced_tool("basic") is False
        assert registry.is_advanced_tool("advanced") is True
        assert registry.is_advanced_tool("nonexistent") is False

    def test_contains_operator(self, registry):
        """Test __contains__ operator."""

        @registry.register("exists", category="basic", description="Exists", input_schema={})
        async def exists_handler(self, args):
            return []

        assert "exists" in registry
        assert "does_not_exist" not in registry

    def test_len_operator(self, registry):
        """Test __len__ operator."""
        assert len(registry) == 0

        @registry.register("test1", category="basic", description="Test 1", input_schema={})
        async def handler1(self, args):
            return []

        assert len(registry) == 1

        @registry.register("test2", category="basic", description="Test 2", input_schema={})
        async def handler2(self, args):
            return []

        assert len(registry) == 2


class TestGlobalHandlerRegistry:
    """Tests for the global handler_registry instance."""

    def test_global_registry_exists(self):
        """Test that global registry instance exists."""
        assert handler_registry is not None
        assert isinstance(handler_registry, HandlerRegistry)

    @pytest.mark.asyncio
    async def test_global_registry_integration_with_server(self):
        """Test that ChatMemoryServer uses the global handler_registry.

        The server module uses @handler_registry.register decorators to
        register handlers. This test verifies the integration by checking
        that the server can use the registry for tool dispatch.

        Note: Due to Python import caching, we test via the server class
        rather than re-importing the module.
        """
        import tempfile

        from memcord.server import ChatMemoryServer

        # The server should be instantiable
        with tempfile.TemporaryDirectory() as temp_dir:
            server = ChatMemoryServer(memory_dir=temp_dir)

            # The server should have tools (via registry)
            # list_tools_direct() returns Tool objects from the registry
            tools = await server.list_tools_direct()

            # Should have tools registered
            assert len(tools) > 0

            # Core tools should be present
            tool_names = [t.name for t in tools]
            core_tools = ["memcord_name", "memcord_save", "memcord_read", "memcord_list"]
            for tool in core_tools:
                assert tool in tool_names, f"Core tool {tool} not found in server tools"
