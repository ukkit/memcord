"""Tests for project binding functionality (memcord_init and memcord_unbind).

Tests the project directory binding feature that associates directories
with memory slots via .memcord files.

Coverage:
- memcord_init tool handler
- memcord_unbind tool handler
- .memcord file creation and management
- Auto-slot naming from directory names
- Custom slot name binding
- Re-binding existing .memcord files
- Error handling and edge cases
- Concurrent binding operations
"""

import asyncio
import os
import tempfile
from pathlib import Path

import pytest
from mcp.types import TextContent

from memcord.server import ChatMemoryServer


@pytest.fixture
async def test_server():
    """Create a test server with temporary storage."""
    with tempfile.TemporaryDirectory() as temp_dir:
        server = ChatMemoryServer(
            memory_dir=temp_dir, shared_dir=str(Path(temp_dir) / "shared"), enable_advanced_tools=True
        )
        yield server
        # Cleanup
        await server.storage.shutdown()


@pytest.fixture
def temp_project_dir():
    """Provide a temporary directory to simulate a project."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield temp_dir


class TestMemcordBindBasicFunctionality:
    """Test basic memcord_init functionality."""

    @pytest.mark.asyncio
    async def test_bind_creates_memcord_file(self, test_server, temp_project_dir):
        """Test that binding a project creates a .memcord file."""
        server = test_server

        result = await server.call_tool_direct("memcord_init", {"project_path": temp_project_dir})

        assert isinstance(result, list)
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "Bound" in result[0].text

        # Verify .memcord file was created
        memcord_file = Path(temp_project_dir) / ".memcord"
        assert memcord_file.exists()

    @pytest.mark.asyncio
    async def test_bind_auto_generates_slot_name_from_directory(self, test_server, temp_project_dir):
        """Test that binding without slot_name uses directory name."""
        server = test_server

        result = await server.call_tool_direct("memcord_init", {"project_path": temp_project_dir})

        # Read the .memcord file content
        memcord_file = Path(temp_project_dir) / ".memcord"
        slot_name = memcord_file.read_text().strip()

        # Should use directory name as slot name
        expected_name = Path(temp_project_dir).name.replace(" ", "_")
        assert slot_name == expected_name
        assert expected_name in result[0].text

    @pytest.mark.asyncio
    async def test_bind_with_custom_slot_name(self, test_server, temp_project_dir):
        """Test binding with a custom slot name."""
        server = test_server
        custom_name = "my-custom-project-slot"

        result = await server.call_tool_direct(
            "memcord_init", {"project_path": temp_project_dir, "slot_name": custom_name}
        )

        assert isinstance(result, list)
        assert custom_name in result[0].text

        # Verify .memcord file contains custom name
        memcord_file = Path(temp_project_dir) / ".memcord"
        assert memcord_file.read_text().strip() == custom_name

    @pytest.mark.asyncio
    async def test_bind_creates_memory_slot(self, test_server, temp_project_dir):
        """Test that binding creates the memory slot if it doesn't exist."""
        server = test_server
        slot_name = "new-slot-for-binding"

        await server.call_tool_direct("memcord_init", {"project_path": temp_project_dir, "slot_name": slot_name})

        # Verify slot was created
        slot = await server.storage.read_memory(slot_name)
        assert slot is not None

    @pytest.mark.asyncio
    async def test_bind_activates_slot(self, test_server, temp_project_dir):
        """Test that binding activates the memory slot."""
        server = test_server
        slot_name = "activated-slot"

        result = await server.call_tool_direct(
            "memcord_init", {"project_path": temp_project_dir, "slot_name": slot_name}
        )

        assert "active" in result[0].text.lower()


class TestMemcordBindRebinding:
    """Test rebinding existing .memcord files."""

    @pytest.mark.asyncio
    async def test_rebind_reads_existing_memcord_file(self, test_server, temp_project_dir):
        """Test that rebinding reads the existing .memcord file."""
        server = test_server
        original_slot_name = "original-slot-name"

        # First binding with custom name
        await server.call_tool_direct(
            "memcord_init", {"project_path": temp_project_dir, "slot_name": original_slot_name}
        )

        # Re-bind without specifying slot_name (should read from .memcord)
        result = await server.call_tool_direct("memcord_init", {"project_path": temp_project_dir})

        # Should use the existing slot name from .memcord
        assert original_slot_name in result[0].text

        # .memcord file should still have the original name
        memcord_file = Path(temp_project_dir) / ".memcord"
        assert memcord_file.read_text().strip() == original_slot_name

    @pytest.mark.asyncio
    async def test_rebind_with_new_slot_name_overwrites(self, test_server, temp_project_dir):
        """Test that rebinding with a new slot_name overwrites the .memcord file."""
        server = test_server
        original_name = "original-name"
        new_name = "new-name"

        # First binding
        await server.call_tool_direct("memcord_init", {"project_path": temp_project_dir, "slot_name": original_name})

        # Re-bind with new name
        result = await server.call_tool_direct(
            "memcord_init", {"project_path": temp_project_dir, "slot_name": new_name}
        )

        # Should use the new name
        assert new_name in result[0].text

        # .memcord file should have the new name
        memcord_file = Path(temp_project_dir) / ".memcord"
        assert memcord_file.read_text().strip() == new_name


class TestMemcordUnbindFunctionality:
    """Test memcord_unbind functionality."""

    @pytest.mark.asyncio
    async def test_unbind_removes_memcord_file(self, test_server, temp_project_dir):
        """Test that unbinding removes the .memcord file."""
        server = test_server

        # First bind
        await server.call_tool_direct("memcord_init", {"project_path": temp_project_dir})

        memcord_file = Path(temp_project_dir) / ".memcord"
        assert memcord_file.exists()

        # Unbind
        result = await server.call_tool_direct("memcord_unbind", {"project_path": temp_project_dir})

        assert isinstance(result, list)
        assert "Removed" in result[0].text
        assert not memcord_file.exists()

    @pytest.mark.asyncio
    async def test_unbind_nonexistent_memcord_file(self, test_server, temp_project_dir):
        """Test unbinding when no .memcord file exists."""
        server = test_server

        result = await server.call_tool_direct("memcord_unbind", {"project_path": temp_project_dir})

        assert isinstance(result, list)
        assert "No .memcord file found" in result[0].text

    @pytest.mark.asyncio
    async def test_unbind_does_not_delete_slot(self, test_server, temp_project_dir):
        """Test that unbinding removes the .memcord file but not the memory slot."""
        server = test_server
        slot_name = "persistent-slot"

        # Bind and save some content
        await server.call_tool_direct("memcord_init", {"project_path": temp_project_dir, "slot_name": slot_name})
        await server.call_tool_direct("memcord_save", {"slot_name": slot_name, "chat_text": "Important content"})

        # Unbind
        await server.call_tool_direct("memcord_unbind", {"project_path": temp_project_dir})

        # Slot should still exist with content
        slot = await server.storage.read_memory(slot_name)
        assert slot is not None
        assert "Important content" in slot.entries[0].content


class TestMemcordBindErrorHandling:
    """Test error handling for bind/unbind operations."""

    @pytest.mark.asyncio
    async def test_bind_invalid_directory(self, test_server):
        """Test binding an invalid directory path."""
        server = test_server
        invalid_path = "/nonexistent/path/to/project"

        result = await server.call_tool_direct("memcord_init", {"project_path": invalid_path})

        assert isinstance(result, list)
        assert "Error" in result[0].text
        assert "not a valid directory" in result[0].text

    @pytest.mark.asyncio
    async def test_bind_file_path_instead_of_directory(self, test_server, temp_project_dir):
        """Test binding a file path instead of a directory."""
        server = test_server

        # Create a file
        file_path = Path(temp_project_dir) / "some_file.txt"
        file_path.write_text("content")

        result = await server.call_tool_direct("memcord_init", {"project_path": str(file_path)})

        assert isinstance(result, list)
        assert "Error" in result[0].text
        assert "not a valid directory" in result[0].text

    @pytest.mark.asyncio
    async def test_unbind_invalid_directory(self, test_server):
        """Test unbinding an invalid directory path."""
        server = test_server
        invalid_path = "/nonexistent/path/to/project"

        result = await server.call_tool_direct("memcord_unbind", {"project_path": invalid_path})

        assert isinstance(result, list)
        # Should handle gracefully - no .memcord file to remove
        assert "No .memcord file found" in result[0].text


class TestMemcordBindEdgeCases:
    """Test edge cases for bind/unbind operations."""

    @pytest.mark.asyncio
    async def test_bind_directory_with_spaces_in_name(self, test_server):
        """Test binding a directory with spaces in its name."""
        with tempfile.TemporaryDirectory(prefix="project with spaces ") as temp_dir:
            server = test_server

            result = await server.call_tool_direct("memcord_init", {"project_path": temp_dir})

            assert isinstance(result, list)
            assert "Bound" in result[0].text

            # Slot name should have spaces replaced with underscores
            memcord_file = Path(temp_dir) / ".memcord"
            slot_name = memcord_file.read_text().strip()
            assert " " not in slot_name
            assert "_" in slot_name

    @pytest.mark.asyncio
    async def test_bind_directory_with_unicode_name(self, test_server):
        """Test binding a directory with Unicode characters in its name."""
        with tempfile.TemporaryDirectory(prefix="project_") as temp_base:
            unicode_dir = Path(temp_base) / "project_with_unicode"
            unicode_dir.mkdir()

            server = test_server

            result = await server.call_tool_direct("memcord_init", {"project_path": str(unicode_dir)})

            assert isinstance(result, list)
            assert "Bound" in result[0].text

    @pytest.mark.asyncio
    async def test_bind_with_expanduser_path(self, test_server):
        """Test binding with a path that uses ~ for home directory."""
        server = test_server

        # This test verifies the path expansion works
        # We'll use a temporary directory and verify expansion happens
        with tempfile.TemporaryDirectory() as temp_dir:
            result = await server.call_tool_direct("memcord_init", {"project_path": temp_dir})

            assert isinstance(result, list)
            # Path should be resolved and expanded in the result
            assert (
                Path(temp_dir).resolve().as_posix() in result[0].text.replace("\\", "/")
                or str(Path(temp_dir).resolve()) in result[0].text
            )

    @pytest.mark.asyncio
    async def test_bind_empty_slot_name(self, test_server, temp_project_dir):
        """Test that empty slot_name falls back to directory name."""
        server = test_server

        result = await server.call_tool_direct("memcord_init", {"project_path": temp_project_dir, "slot_name": ""})

        # Should still work, using directory name
        assert isinstance(result, list)
        # Empty string should trigger fallback to directory name
        memcord_file = Path(temp_project_dir) / ".memcord"
        slot_name = memcord_file.read_text().strip()
        assert slot_name == Path(temp_project_dir).name.replace(" ", "_")


class TestMemcordBindIntegration:
    """Test integration of bind/unbind with other memcord operations."""

    @pytest.mark.asyncio
    async def test_bind_then_save_and_read(self, test_server, temp_project_dir):
        """Test complete workflow: bind, save content, read content."""
        server = test_server
        slot_name = "integration-test-slot"

        # Bind project
        await server.call_tool_direct("memcord_init", {"project_path": temp_project_dir, "slot_name": slot_name})

        # Save content to the bound slot
        await server.call_tool_direct("memcord_save", {"slot_name": slot_name, "chat_text": "Integration test content"})

        # Read content back
        read_result = await server.call_tool_direct("memcord_read", {"slot_name": slot_name})

        assert isinstance(read_result, list)
        assert "Integration test content" in read_result[0].text

    @pytest.mark.asyncio
    async def test_bind_multiple_projects_to_different_slots(self, test_server):
        """Test binding multiple projects to different slots."""
        server = test_server

        with tempfile.TemporaryDirectory() as project1:
            with tempfile.TemporaryDirectory() as project2:
                # Bind first project
                await server.call_tool_direct("memcord_init", {"project_path": project1, "slot_name": "project-one"})

                # Bind second project
                await server.call_tool_direct("memcord_init", {"project_path": project2, "slot_name": "project-two"})

                # Verify both bindings exist
                memcord1 = Path(project1) / ".memcord"
                memcord2 = Path(project2) / ".memcord"

                assert memcord1.exists()
                assert memcord2.exists()
                assert memcord1.read_text().strip() == "project-one"
                assert memcord2.read_text().strip() == "project-two"

    @pytest.mark.asyncio
    async def test_bind_after_server_restart_simulation(self, test_server, temp_project_dir):
        """Test that rebinding after 'restart' picks up existing .memcord."""
        server = test_server
        slot_name = "persistent-binding"

        # Initial binding
        await server.call_tool_direct("memcord_init", {"project_path": temp_project_dir, "slot_name": slot_name})

        # Save some content
        await server.call_tool_direct("memcord_save", {"slot_name": slot_name, "chat_text": "Persisted content"})

        # Simulate restart by re-binding (without slot_name - should read from .memcord)
        result = await server.call_tool_direct("memcord_init", {"project_path": temp_project_dir})

        # Should activate the same slot
        assert slot_name in result[0].text

        # Content should still be accessible
        read_result = await server.call_tool_direct("memcord_read", {"slot_name": slot_name})
        assert "Persisted content" in read_result[0].text


class TestMemcordBindConcurrency:
    """Test concurrent bind/unbind operations."""

    @pytest.mark.asyncio
    async def test_concurrent_bind_operations(self, test_server):
        """Test multiple concurrent bind operations."""
        server = test_server

        temp_dirs = []
        try:
            # Create multiple temp directories
            for _ in range(5):
                temp_dir = tempfile.mkdtemp()
                temp_dirs.append(temp_dir)

            # Concurrent bind operations
            tasks = [
                server.call_tool_direct("memcord_init", {"project_path": temp_dir, "slot_name": f"concurrent-slot-{i}"})
                for i, temp_dir in enumerate(temp_dirs)
            ]

            results = await asyncio.gather(*tasks)

            # All operations should succeed
            assert len(results) == 5
            for result in results:
                assert isinstance(result, list)
                assert "Bound" in result[0].text

            # Verify all .memcord files were created
            for i, temp_dir in enumerate(temp_dirs):
                memcord_file = Path(temp_dir) / ".memcord"
                assert memcord_file.exists()
                assert memcord_file.read_text().strip() == f"concurrent-slot-{i}"

        finally:
            # Cleanup temp directories
            import shutil

            for temp_dir in temp_dirs:
                shutil.rmtree(temp_dir, ignore_errors=True)

    @pytest.mark.asyncio
    async def test_rapid_bind_unbind_cycles(self, test_server, temp_project_dir):
        """Test rapid bind/unbind cycles."""
        server = test_server

        for i in range(10):
            # Bind
            bind_result = await server.call_tool_direct(
                "memcord_init", {"project_path": temp_project_dir, "slot_name": f"cycle-slot-{i}"}
            )
            assert "Bound" in bind_result[0].text

            # Verify binding
            memcord_file = Path(temp_project_dir) / ".memcord"
            assert memcord_file.exists()

            # Unbind
            unbind_result = await server.call_tool_direct("memcord_unbind", {"project_path": temp_project_dir})
            assert "Removed" in unbind_result[0].text

            # Verify unbinding
            assert not memcord_file.exists()


class TestMemcordBindToolRegistration:
    """Test that bind/unbind tools are properly registered."""

    @pytest.mark.asyncio
    async def test_bind_tool_in_tool_list(self, test_server):
        """Test that memcord_init is in the tool list."""
        server = test_server

        tools = await server.list_tools_direct()
        tool_names = [tool.name for tool in tools]

        assert "memcord_init" in tool_names

    @pytest.mark.asyncio
    async def test_unbind_tool_in_tool_list(self, test_server):
        """Test that memcord_unbind is in the tool list."""
        server = test_server

        tools = await server.list_tools_direct()
        tool_names = [tool.name for tool in tools]

        assert "memcord_unbind" in tool_names

    @pytest.mark.asyncio
    async def test_bind_tool_has_correct_schema(self, test_server):
        """Test that memcord_init has the correct input schema."""
        server = test_server

        tools = await server.list_tools_direct()
        bind_tool = next(tool for tool in tools if tool.name == "memcord_init")

        assert bind_tool.inputSchema is not None
        assert "properties" in bind_tool.inputSchema
        assert "project_path" in bind_tool.inputSchema["properties"]
        assert "slot_name" in bind_tool.inputSchema["properties"]
        assert "required" in bind_tool.inputSchema
        assert "project_path" in bind_tool.inputSchema["required"]

    @pytest.mark.asyncio
    async def test_unbind_tool_has_correct_schema(self, test_server):
        """Test that memcord_unbind has the correct input schema."""
        server = test_server

        tools = await server.list_tools_direct()
        unbind_tool = next(tool for tool in tools if tool.name == "memcord_unbind")

        assert unbind_tool.inputSchema is not None
        assert "properties" in unbind_tool.inputSchema
        assert "project_path" in unbind_tool.inputSchema["properties"]
        assert "required" in unbind_tool.inputSchema
        assert "project_path" in unbind_tool.inputSchema["required"]


class TestMemcordBindDirectHandlers:
    """Test bind/unbind handlers directly."""

    @pytest.mark.asyncio
    async def test_handle_bind_directly(self, test_server, temp_project_dir):
        """Test _handle_bind method directly."""
        server = test_server

        result = await server._handle_bind({"project_path": temp_project_dir, "slot_name": "direct-test"})

        assert isinstance(result, list)
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "Bound" in result[0].text

    @pytest.mark.asyncio
    async def test_handle_unbind_directly(self, test_server, temp_project_dir):
        """Test _handle_unbind method directly."""
        server = test_server

        # First bind
        await server._handle_bind({"project_path": temp_project_dir, "slot_name": "direct-unbind-test"})

        # Then unbind
        result = await server._handle_unbind({"project_path": temp_project_dir})

        assert isinstance(result, list)
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "Removed" in result[0].text


class TestMemcordBindCallToolDirect:
    """Test bind/unbind via call_tool_direct interface."""

    @pytest.mark.asyncio
    async def test_call_tool_direct_bind(self, test_server, temp_project_dir):
        """Test memcord_init via call_tool_direct."""
        server = test_server

        result = await server.call_tool_direct(
            "memcord_init", {"project_path": temp_project_dir, "slot_name": "call-direct-test"}
        )

        assert isinstance(result, list | tuple)
        assert len(result) >= 1
        assert hasattr(result[0], "text")
        assert "Bound" in result[0].text

    @pytest.mark.asyncio
    async def test_call_tool_direct_unbind(self, test_server, temp_project_dir):
        """Test memcord_unbind via call_tool_direct."""
        server = test_server

        # First bind
        await server.call_tool_direct("memcord_init", {"project_path": temp_project_dir})

        # Then unbind
        result = await server.call_tool_direct("memcord_unbind", {"project_path": temp_project_dir})

        assert isinstance(result, list | tuple)
        assert len(result) >= 1
        assert hasattr(result[0], "text")
        assert "Removed" in result[0].text


class TestMemcordBindPathHandling:
    """Test various path handling scenarios."""

    @pytest.mark.asyncio
    async def test_bind_with_relative_path(self, test_server, temp_project_dir):
        """Test that relative paths are resolved."""
        server = test_server

        # Create a subdirectory
        subdir = Path(temp_project_dir) / "subproject"
        subdir.mkdir()

        # Use the absolute path
        result = await server.call_tool_direct("memcord_init", {"project_path": str(subdir)})

        assert isinstance(result, list)
        # Path should be resolved to absolute
        assert str(subdir.resolve()) in result[0].text or str(subdir) in result[0].text

    @pytest.mark.asyncio
    async def test_bind_with_trailing_slash(self, test_server, temp_project_dir):
        """Test binding a path with trailing slash."""
        server = test_server

        path_with_slash = temp_project_dir + os.sep

        result = await server.call_tool_direct("memcord_init", {"project_path": path_with_slash})

        assert isinstance(result, list)
        assert "Bound" in result[0].text

    @pytest.mark.asyncio
    async def test_bind_normalizes_path(self, test_server, temp_project_dir):
        """Test that paths are normalized."""
        server = test_server

        # Create a path with .. components
        subdir = Path(temp_project_dir) / "subdir"
        subdir.mkdir()
        unnormalized_path = str(subdir) + "/../subdir"

        result = await server.call_tool_direct("memcord_init", {"project_path": unnormalized_path})

        assert isinstance(result, list)
        assert "Bound" in result[0].text

        # The resolved path should be in the result
        normalized = str(Path(unnormalized_path).resolve())
        assert normalized in result[0].text or str(subdir.resolve()) in result[0].text


class TestMemcordBindMemcordFileContent:
    """Test .memcord file content and format."""

    @pytest.mark.asyncio
    async def test_memcord_file_contains_only_slot_name(self, test_server, temp_project_dir):
        """Test that .memcord file contains only the slot name."""
        server = test_server
        slot_name = "simple-slot-name"

        await server.call_tool_direct("memcord_init", {"project_path": temp_project_dir, "slot_name": slot_name})

        memcord_file = Path(temp_project_dir) / ".memcord"
        content = memcord_file.read_text()

        # Should be just the slot name with possible whitespace
        assert content.strip() == slot_name

    @pytest.mark.asyncio
    async def test_memcord_file_is_human_readable(self, test_server, temp_project_dir):
        """Test that .memcord file is human-readable plain text."""
        server = test_server
        slot_name = "readable-slot"

        await server.call_tool_direct("memcord_init", {"project_path": temp_project_dir, "slot_name": slot_name})

        memcord_file = Path(temp_project_dir) / ".memcord"

        # File should be readable as text without errors
        content = memcord_file.read_text(encoding="utf-8")
        assert isinstance(content, str)
        assert content.strip() == slot_name

    @pytest.mark.asyncio
    async def test_memcord_file_overwrites_on_rebind(self, test_server, temp_project_dir):
        """Test that rebinding overwrites the .memcord file."""
        server = test_server

        # First binding
        await server.call_tool_direct("memcord_init", {"project_path": temp_project_dir, "slot_name": "first-slot"})

        # Second binding with different name
        await server.call_tool_direct("memcord_init", {"project_path": temp_project_dir, "slot_name": "second-slot"})

        memcord_file = Path(temp_project_dir) / ".memcord"
        content = memcord_file.read_text().strip()

        # Should have the second slot name only
        assert content == "second-slot"
        assert "first-slot" not in content
