"""
Integration tests for VSCode and GitHub Copilot agent mode.

These tests verify that memcord works correctly with VSCode's MCP integration
and GitHub Copilot agent mode.
"""

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestVSCodeConfiguration:
    """Test VSCode configuration file handling."""

    def test_workspace_mcp_config_valid(self):
        """Test that workspace .vscode/mcp.json format is valid."""
        with open(".vscode/mcp.json.example", "r") as f:
            config = json.load(f)

        assert "servers" in config
        assert "memcord" in config["servers"]

        memcord_config = config["servers"]["memcord"]
        assert memcord_config["command"] == "uv"
        assert "--directory" in memcord_config["args"]
        assert "run" in memcord_config["args"]
        assert "memcord" in memcord_config["args"]
        assert "PYTHONPATH" in memcord_config["env"]

    def test_root_mcp_config_valid(self):
        """Test that root .mcp.json format is valid."""
        with open(".mcp.json.example", "r") as f:
            config = json.load(f)

        assert "servers" in config
        assert "memcord" in config["servers"]

        memcord_config = config["servers"]["memcord"]
        assert "PYTHONPATH" in memcord_config["env"]
        assert "MEMCORD_ENABLE_ADVANCED" in memcord_config["env"]

    def test_vscode_extensions_config_valid(self):
        """Test that .vscode/extensions.json format is valid."""
        with open(".vscode/extensions.json", "r") as f:
            config = json.load(f)

        assert "recommendations" in config
        assert "github.copilot" in config["recommendations"]
        assert "github.copilot-chat" in config["recommendations"]

    def test_package_json_valid(self):
        """Test that package.json format is valid."""
        with open("package.json", "r") as f:
            config = json.load(f)

        assert config["name"] == "memcord"
        assert "mcp" in config
        assert "server" in config["mcp"]
        assert config["mcp"]["server"]["type"] == "stdio"


class TestMCPServerStartup:
    """Test MCP server startup and initialization."""

    @pytest.mark.asyncio
    async def test_server_can_be_instantiated(self):
        """Test that ChatMemoryServer can be created."""
        from memcord.server import ChatMemoryServer

        server = ChatMemoryServer()
        assert server is not None
        assert hasattr(server, "run")

    @pytest.mark.asyncio
    async def test_server_storage_initialization(self):
        """Test that server initializes storage correctly."""
        from memcord.server import ChatMemoryServer

        with tempfile.TemporaryDirectory() as tmpdir:
            server = ChatMemoryServer(memory_dir=tmpdir)

            assert server.storage is not None
            assert Path(tmpdir).exists()

    @pytest.mark.asyncio
    async def test_server_basic_mode_by_default(self):
        """Test that server starts in basic mode (11 tools) by default."""
        from memcord.server import ChatMemoryServer

        # Ensure advanced mode is not enabled
        os.environ.pop("MEMCORD_ENABLE_ADVANCED", None)

        server = ChatMemoryServer(enable_advanced_tools=False)
        tools = await server.list_tools_direct()

        # Basic mode has 11 basic tools
        basic_tools = [
            "memcord_name",
            "memcord_use",
            "memcord_save",
            "memcord_save_progress",
            "memcord_read",
            "memcord_list",
            "memcord_search",
            "memcord_query",
            "memcord_zero",
            "memcord_select_entry",
        ]

        tool_names = [tool.name for tool in tools]
        for basic_tool in basic_tools:
            assert basic_tool in tool_names

    @pytest.mark.asyncio
    async def test_server_advanced_mode_with_env_var(self):
        """Test that server enables advanced mode with environment variable."""
        from memcord.server import ChatMemoryServer

        os.environ["MEMCORD_ENABLE_ADVANCED"] = "true"

        try:
            server = ChatMemoryServer()
            tools = await server.list_tools_direct()

            # Advanced mode has more tools than basic mode
            assert len(tools) > 10  # More than basic mode

            # Check for some advanced tools
            tool_names = [tool.name for tool in tools]
            # Should have at least merge tool
            assert "memcord_merge" in tool_names or len(tools) > 11

        finally:
            os.environ.pop("MEMCORD_ENABLE_ADVANCED", None)


class TestMCPProtocolCompliance:
    """Test MCP protocol compliance."""

    @pytest.mark.asyncio
    async def test_list_tools_returns_valid_format(self):
        """Test that list_tools returns valid MCP format."""
        from memcord.server import ChatMemoryServer

        server = ChatMemoryServer()

        # Simulate list_tools call
        tools = await server.list_tools_direct()

        assert isinstance(tools, list)
        assert len(tools) > 0

        # Check first tool has required MCP fields
        tool = tools[0]
        assert hasattr(tool, "name")
        assert hasattr(tool, "description")
        assert hasattr(tool, "inputSchema")

    @pytest.mark.asyncio
    async def test_tool_call_format(self):
        """Test that tools can be called with proper MCP format."""
        from memcord.server import ChatMemoryServer

        with tempfile.TemporaryDirectory() as tmpdir:
            server = ChatMemoryServer(memory_dir=tmpdir)

            # Test memcord_list (simplest tool)
            result = await server._handle_listmems({})

            assert isinstance(result, list)
            assert len(result) > 0
            assert hasattr(result[0], "text")


class TestToolFunctionality:
    """Test individual tool functionality in VSCode context."""

    @pytest.mark.asyncio
    async def test_memcord_name_creates_slot(self):
        """Test that memcord_name creates a memory slot."""
        from memcord.server import ChatMemoryServer

        with tempfile.TemporaryDirectory() as tmpdir:
            server = ChatMemoryServer(memory_dir=tmpdir)
            result = await server._handle_memname({"slot_name": "test-project"})

            assert isinstance(result, list)
            assert len(result) > 0
            assert "test-project" in result[0].text
            # Check slot file was created
            slot_file = Path(tmpdir) / "test-project.json"
            assert slot_file.exists()

    @pytest.mark.asyncio
    async def test_memcord_save_stores_content(self):
        """Test that memcord_save stores content in active slot."""
        from memcord.server import ChatMemoryServer

        with tempfile.TemporaryDirectory() as tmpdir:
            server = ChatMemoryServer(memory_dir=tmpdir)

            # Create slot first
            await server._handle_memname({"slot_name": "test-project"})

            # Save content
            content = "This is test content for VSCode integration"
            result = await server._handle_savemem({"chat_text": content})

            assert isinstance(result, list)
            assert len(result) > 0
            assert "saved" in result[0].text.lower()

            # Verify content was saved
            slot_file = Path(tmpdir) / "test-project.json"
            with open(slot_file, "r") as f:
                data = json.load(f)
                assert len(data["entries"]) > 0
                assert content in data["entries"][0]["content"]

    @pytest.mark.asyncio
    async def test_memcord_search_finds_content(self):
        """Test that memcord_search can find saved content."""
        from memcord.server import ChatMemoryServer

        with tempfile.TemporaryDirectory() as tmpdir:
            server = ChatMemoryServer(memory_dir=tmpdir)

            # Create slot and save searchable content
            await server._handle_memname({"slot_name": "test-project"})
            await server._handle_savemem({"chat_text": "VSCode integration test with authentication"})

            # Search for content
            result = await server._handle_searchmem({"query": "authentication"})

            assert isinstance(result, list)
            assert len(result) > 0
            result_text = result[0].text.lower()
            assert "authentication" in result_text or "found" in result_text


class TestCopilotAgentMode:
    """Test GitHub Copilot agent mode compatibility."""

    @pytest.mark.asyncio
    async def test_tools_have_descriptive_names(self):
        """Test that all tools have user-friendly names for Copilot."""
        from memcord.server import ChatMemoryServer

        server = ChatMemoryServer()
        tools = await server.list_tools_direct()

        for tool in tools:
            # Tool names should start with memcord_
            assert tool.name.startswith("memcord_")

            # Tool descriptions should be present and meaningful
            assert tool.description
            assert len(tool.description) > 10  # Not just a stub

    @pytest.mark.asyncio
    async def test_tools_have_clear_parameters(self):
        """Test that tool parameters are clearly documented."""
        from memcord.server import ChatMemoryServer

        server = ChatMemoryServer()
        tools = await server.list_tools_direct()

        for tool in tools:
            # Each tool should have input schema
            assert tool.inputSchema
            assert "type" in tool.inputSchema

            # If tool has parameters, they should be documented
            if "properties" in tool.inputSchema:
                for param_name, param_def in tool.inputSchema["properties"].items():
                    # Each parameter should have a description
                    assert "description" in param_def or "title" in param_def


class TestErrorHandling:
    """Test error handling in VSCode context."""

    @pytest.mark.asyncio
    async def test_invalid_slot_name_handled(self):
        """Test that invalid slot names are handled gracefully."""
        from memcord.server import ChatMemoryServer
        from pydantic_core import ValidationError

        with tempfile.TemporaryDirectory() as tmpdir:
            server = ChatMemoryServer(memory_dir=tmpdir)

            # Try to create slot with path traversal characters
            # Should raise ValidationError due to Pydantic validation
            with pytest.raises(ValidationError) as exc_info:
                await server._handle_memname({"slot_name": "../../etc/passwd"})

            # Verify the error is about path traversal
            assert "path traversal" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_save_without_active_slot_handled(self):
        """Test that saving without active slot is handled."""
        from memcord.server import ChatMemoryServer

        with tempfile.TemporaryDirectory() as tmpdir:
            server = ChatMemoryServer(memory_dir=tmpdir)

            # Try to save without selecting a slot first
            result = await server._handle_savemem({"chat_text": "test content"})

            assert isinstance(result, list)
            assert len(result) > 0
            # Should provide clear error or create default slot
            result_text = result[0].text.lower()
            assert "error" in result_text or "slot" in result_text or "saved" in result_text


class TestVSCodeVariables:
    """Test VSCode variable resolution in configuration."""

    def test_workspace_folder_variable_in_config(self):
        """Test that ${workspaceFolder} variable is used in config."""
        with open(".vscode/mcp.json.example", "r") as f:
            content = f.read()

        assert "${workspaceFolder}" in content

    def test_config_uses_relative_paths(self):
        """Test that root config uses relative paths."""
        with open(".mcp.json.example", "r") as f:
            config = json.load(f)

        memcord_config = config["servers"]["memcord"]

        # Check that args use relative paths
        args = memcord_config["args"]
        directory_idx = args.index("--directory")
        directory_path = args[directory_idx + 1]

        assert directory_path == "." or not directory_path.startswith("/")


class TestPrompts:
    """Test MCP prompts feature."""

    def test_prompts_module_exists(self):
        """Test that prompts module can be imported."""
        from memcord.prompts import PROMPTS, list_prompts

        assert PROMPTS
        assert len(PROMPTS) > 0

        prompts = list_prompts()
        assert len(prompts) > 0

    def test_all_prompts_have_required_fields(self):
        """Test that all prompts have required fields."""
        from memcord.prompts import PROMPTS

        required_fields = ["name", "description", "prompt", "categories"]

        for prompt_name, prompt_def in PROMPTS.items():
            for field in required_fields:
                assert field in prompt_def, f"Prompt '{prompt_name}' missing field '{field}'"

    def test_prompts_categorized(self):
        """Test that prompts have meaningful categories."""
        from memcord.prompts import list_categories

        categories = list_categories()
        assert len(categories) > 0
        assert "documentation" in categories

    def test_prompt_aliases_work(self):
        """Test that prompt aliases resolve correctly."""
        from memcord.prompts import resolve_alias

        assert resolve_alias("project") == "project-memory"
        assert resolve_alias("review") == "code-review-save"
        assert resolve_alias("adr") == "architecture-decision"


class TestVerificationScript:
    """Test the verification script."""

    def test_verification_script_exists(self):
        """Test that verification script exists and is executable."""
        script_path = Path("utilities/verify_vscode_setup.py")
        assert script_path.exists()

        # Check if file has shebang
        with open(script_path, "r") as f:
            first_line = f.readline()
            assert first_line.startswith("#!")

    def test_verification_script_can_be_imported(self):
        """Test that verification script can be imported as module."""
        import sys

        sys.path.insert(0, str(Path("utilities")))

        try:
            import verify_vscode_setup

            assert hasattr(verify_vscode_setup, "main")
            assert hasattr(verify_vscode_setup, "check_python_version")
            assert hasattr(verify_vscode_setup, "find_mcp_config")
        finally:
            sys.path.pop(0)


@pytest.mark.integration
class TestEndToEndWorkflow:
    """End-to-end integration tests simulating VSCode usage."""

    @pytest.mark.asyncio
    async def test_complete_project_workflow(self):
        """Test a complete project workflow as would be used in VSCode."""
        from memcord.server import ChatMemoryServer

        with tempfile.TemporaryDirectory() as tmpdir:
            server = ChatMemoryServer(memory_dir=tmpdir)

            # 1. Create project memory
            result = await server._handle_memname({"slot_name": "vscode-project"})
            assert isinstance(result, list) and len(result) > 0
            assert "vscode-project" in result[0].text

            # 2. Save initial context
            result = await server._handle_savemem({
                "chat_text": "Project: VSCode Extension\nStack: TypeScript, Node.js\nGoal: MCP integration"
            })
            assert isinstance(result, list) and len(result) > 0
            assert "saved" in result[0].text.lower()

            # 3. Save progress with summary
            result = await server._handle_saveprogress({
                "chat_text": "Discussed MCP integration approach and API design"
            })
            assert isinstance(result, list) and len(result) > 0
            assert "summary" in result[0].text.lower() or "saved" in result[0].text.lower()

            # 4. List all slots
            result = await server._handle_listmems({})
            assert isinstance(result, list) and len(result) > 0
            assert "vscode-project" in result[0].text

            # 5. Search for content
            result = await server._handle_searchmem({"query": "TypeScript"})
            assert isinstance(result, list) and len(result) > 0
            result_text = result[0].text
            assert "TypeScript" in result_text or "vscode-project" in result_text or "found" in result_text.lower()

            # 6. Read slot contents
            result = await server._handle_readmem({})
            assert isinstance(result, list) and len(result) > 0
            result_text = result[0].text
            assert "VSCode Extension" in result_text or "vscode-project" in result_text or "entries" in result_text.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
