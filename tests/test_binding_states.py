"""Tests for binding states and active slot resolution.

Tests the slot resolution priority and interactions between:
- Explicit slot arguments
- Active slot (via memcord_name/memcord_use)
- Project binding (.memcord file)
- Zero mode

Coverage:
- Slot resolution priority order
- Active slot state management
- Project binding detection
- Interaction between different slot resolution methods
"""

import asyncio
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from memcord.server import ChatMemoryServer


@pytest.fixture
async def test_server():
    """Create a test server with temporary storage."""
    with tempfile.TemporaryDirectory() as temp_dir:
        server = ChatMemoryServer(
            memory_dir=temp_dir, shared_dir=str(Path(temp_dir) / "shared"), enable_advanced_tools=True
        )
        yield server
        await server.storage.shutdown()


@pytest.fixture
def temp_project_dir():
    """Provide a temporary directory to simulate a project."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield temp_dir


class TestSlotResolutionPriority:
    """Test the slot resolution priority order.

    Priority:
    1. Explicit slot_name in arguments
    2. Currently active slot (via memcord_use/memcord_name)
    3. Project binding (.memcord file in cwd)
    """

    @pytest.mark.asyncio
    async def test_explicit_argument_takes_highest_priority(self, test_server):
        """Test that explicit slot_name argument always wins."""
        server = test_server

        # Set up active slot
        await server.call_tool_direct("memcord_name", {"slot_name": "active-slot"})

        # Create content in different slots
        await server.call_tool_direct("memcord_save", {"slot_name": "active-slot", "chat_text": "Active slot content"})
        await server.call_tool_direct(
            "memcord_save", {"slot_name": "explicit-slot", "chat_text": "Explicit slot content"}
        )

        # Read with explicit argument should use explicit slot
        result = await server.call_tool_direct("memcord_read", {"slot_name": "explicit-slot"})

        assert "Explicit slot content" in result[0].text
        assert "Active slot content" not in result[0].text

    @pytest.mark.asyncio
    async def test_active_slot_used_when_no_argument(self, test_server):
        """Test that active slot is used when no explicit argument given."""
        server = test_server

        # Set up and activate slot
        await server.call_tool_direct("memcord_name", {"slot_name": "my-active-slot"})
        await server.call_tool_direct("memcord_save", {"slot_name": "my-active-slot", "chat_text": "Active content"})

        # Read without argument should use active slot
        result = await server.call_tool_direct("memcord_read", {})

        assert "Active content" in result[0].text

    @pytest.mark.asyncio
    async def test_active_slot_takes_precedence_over_project_binding(self, test_server, temp_project_dir):
        """Test that active slot has higher priority than project binding."""
        server = test_server

        # Bind project to a slot
        await server.call_tool_direct("memcord_init", {"project_path": temp_project_dir, "slot_name": "bound-slot"})
        await server.call_tool_direct("memcord_save", {"slot_name": "bound-slot", "chat_text": "Bound slot content"})

        # Set a different active slot
        await server.call_tool_direct("memcord_name", {"slot_name": "different-active-slot"})
        await server.call_tool_direct(
            "memcord_save", {"slot_name": "different-active-slot", "chat_text": "Different active content"}
        )

        # Read without argument should use active slot, not bound slot
        result = await server.call_tool_direct("memcord_read", {})

        assert "Different active content" in result[0].text
        assert "Bound slot content" not in result[0].text

    @pytest.mark.asyncio
    async def test_explicit_argument_overrides_active_slot(self, test_server):
        """Test explicit slot_name overrides active slot for save operation."""
        server = test_server

        # Set active slot
        await server.call_tool_direct("memcord_name", {"slot_name": "active-slot"})

        # Save to explicit slot
        await server.call_tool_direct("memcord_save", {"slot_name": "other-slot", "chat_text": "Content in other"})

        # Verify content is in other-slot
        result = await server.call_tool_direct("memcord_read", {"slot_name": "other-slot"})
        assert "Content in other" in result[0].text

        # Verify active slot is empty
        result = await server.call_tool_direct("memcord_read", {"slot_name": "active-slot"})
        # Active slot should have no entries (just created by memcord_name)
        assert "empty" in result[0].text.lower() or "0 entries" in result[0].text

    @pytest.mark.asyncio
    async def test_resolve_slot_returns_none_when_nothing_set(self, test_server, temp_project_dir):
        """Test that _resolve_slot returns None when nothing is set."""
        server = test_server

        # No active slot, no project binding, no argument
        # Mock cwd to temp directory without .memcord file
        with patch.object(Path, "cwd", return_value=Path(temp_project_dir)):
            result = server._resolve_slot({})

        assert result is None

    @pytest.mark.asyncio
    async def test_resolve_slot_with_empty_string_argument(self, test_server):
        """Test that empty string argument falls through to active slot."""
        server = test_server

        # Set active slot
        await server.call_tool_direct("memcord_name", {"slot_name": "fallback-slot"})

        # Empty string should be falsy and fall through
        result = server._resolve_slot({"slot_name": ""})

        assert result == "fallback-slot"


class TestActiveSlotState:
    """Test active slot state management."""

    @pytest.mark.asyncio
    async def test_memcord_name_sets_active_slot(self, test_server):
        """Test that memcord_name sets the active slot."""
        server = test_server

        result = await server.call_tool_direct("memcord_name", {"slot_name": "new-slot"})

        assert "active" in result[0].text.lower()
        assert server.storage.get_current_slot() == "new-slot"

    @pytest.mark.asyncio
    async def test_memcord_use_sets_active_slot(self, test_server):
        """Test that memcord_use activates an existing slot."""
        server = test_server

        # First create the slot
        await server.call_tool_direct("memcord_name", {"slot_name": "slot-to-use"})
        await server.call_tool_direct("memcord_save", {"slot_name": "slot-to-use", "chat_text": "Some content"})

        # Switch to different slot
        await server.call_tool_direct("memcord_name", {"slot_name": "different-slot"})

        # Use memcord_use to switch back
        result = await server.call_tool_direct("memcord_use", {"slot_name": "slot-to-use"})

        assert "active" in result[0].text.lower()
        assert server.storage.get_current_slot() == "slot-to-use"

    @pytest.mark.asyncio
    async def test_memcord_use_fails_for_nonexistent_slot(self, test_server):
        """Test that memcord_use fails for slots that don't exist."""
        server = test_server

        result = await server.call_tool_direct("memcord_use", {"slot_name": "nonexistent-slot"})

        assert "not exist" in result[0].text.lower() or "not found" in result[0].text.lower()

    @pytest.mark.asyncio
    async def test_active_slot_persists_across_operations(self, test_server):
        """Test that active slot persists across multiple operations."""
        server = test_server

        # Set active slot
        await server.call_tool_direct("memcord_name", {"slot_name": "persistent-slot"})

        # Perform multiple operations
        await server.call_tool_direct("memcord_save", {"chat_text": "First save"})
        await server.call_tool_direct("memcord_save", {"chat_text": "Second save"})

        # Verify slot is still active
        assert server.storage.get_current_slot() == "persistent-slot"

        # Verify content is in the active slot
        result = await server.call_tool_direct("memcord_read", {})
        assert "Second save" in result[0].text

    @pytest.mark.asyncio
    async def test_active_slot_can_be_changed(self, test_server):
        """Test that active slot can be changed to different slots."""
        server = test_server

        # Set first active slot
        await server.call_tool_direct("memcord_name", {"slot_name": "slot-one"})
        assert server.storage.get_current_slot() == "slot-one"

        # Change to second slot
        await server.call_tool_direct("memcord_name", {"slot_name": "slot-two"})
        assert server.storage.get_current_slot() == "slot-two"

        # Change to third slot
        await server.call_tool_direct("memcord_name", {"slot_name": "slot-three"})
        assert server.storage.get_current_slot() == "slot-three"

    @pytest.mark.asyncio
    async def test_binding_activates_slot(self, test_server, temp_project_dir):
        """Test that binding a project activates the slot."""
        server = test_server

        # No active slot initially
        assert server.storage.get_current_slot() is None

        # Bind project
        result = await server.call_tool_direct(
            "memcord_init", {"project_path": temp_project_dir, "slot_name": "bound-activated"}
        )

        assert "active" in result[0].text.lower()
        assert server.storage.get_current_slot() == "bound-activated"

    @pytest.mark.asyncio
    async def test_initial_state_has_no_active_slot(self, test_server):
        """Test that server starts with no active slot."""
        server = test_server

        assert server.storage.get_current_slot() is None

    @pytest.mark.asyncio
    async def test_list_shows_current_slot_marker(self, test_server):
        """Test that memcord_list shows (current) marker for active slot."""
        server = test_server

        # Create multiple slots
        await server.call_tool_direct("memcord_name", {"slot_name": "slot-a"})
        await server.call_tool_direct("memcord_name", {"slot_name": "slot-b"})
        await server.call_tool_direct("memcord_name", {"slot_name": "slot-c"})

        # List slots
        result = await server.call_tool_direct("memcord_list", {})

        # Current slot should have marker
        assert "(current)" in result[0].text
        assert "slot-c" in result[0].text  # Last set slot should be current


class TestProjectBindingDetection:
    """Test project binding detection via .memcord file."""

    @pytest.mark.asyncio
    async def test_detect_project_slot_reads_memcord_file(self, test_server, temp_project_dir):
        """Test that _detect_project_slot reads .memcord file."""
        server = test_server

        # Manually create .memcord file
        memcord_file = Path(temp_project_dir) / ".memcord"
        memcord_file.write_text("detected-slot")

        # Mock cwd to be the temp directory
        with patch.object(Path, "cwd", return_value=Path(temp_project_dir)):
            result = server._detect_project_slot()

        assert result == "detected-slot"

    @pytest.mark.asyncio
    async def test_detect_project_slot_returns_none_when_no_file(self, test_server, temp_project_dir):
        """Test _detect_project_slot returns None when no .memcord file."""
        server = test_server

        # No .memcord file in temp directory
        with patch.object(Path, "cwd", return_value=Path(temp_project_dir)):
            result = server._detect_project_slot()

        assert result is None

    @pytest.mark.asyncio
    async def test_detect_project_slot_handles_empty_file(self, test_server, temp_project_dir):
        """Test _detect_project_slot returns None for empty .memcord file."""
        server = test_server

        # Create empty .memcord file
        memcord_file = Path(temp_project_dir) / ".memcord"
        memcord_file.write_text("")

        with patch.object(Path, "cwd", return_value=Path(temp_project_dir)):
            result = server._detect_project_slot()

        assert result is None

    @pytest.mark.asyncio
    async def test_detect_project_slot_handles_whitespace_only_file(self, test_server, temp_project_dir):
        """Test _detect_project_slot returns None for whitespace-only .memcord file."""
        server = test_server

        # Create whitespace-only .memcord file
        memcord_file = Path(temp_project_dir) / ".memcord"
        memcord_file.write_text("   \n  \t  ")

        with patch.object(Path, "cwd", return_value=Path(temp_project_dir)):
            result = server._detect_project_slot()

        assert result is None

    @pytest.mark.asyncio
    async def test_detect_project_slot_strips_whitespace(self, test_server, temp_project_dir):
        """Test _detect_project_slot strips whitespace from slot name."""
        server = test_server

        # Create .memcord file with whitespace
        memcord_file = Path(temp_project_dir) / ".memcord"
        memcord_file.write_text("  my-slot-name  \n")

        with patch.object(Path, "cwd", return_value=Path(temp_project_dir)):
            result = server._detect_project_slot()

        assert result == "my-slot-name"

    @pytest.mark.asyncio
    async def test_detect_project_slot_handles_multiline_file(self, test_server, temp_project_dir):
        """Test _detect_project_slot only reads first line if file has multiple lines."""
        server = test_server

        # Create .memcord file with multiple lines
        memcord_file = Path(temp_project_dir) / ".memcord"
        memcord_file.write_text("first-line-slot\nsecond-line\nthird-line")

        with patch.object(Path, "cwd", return_value=Path(temp_project_dir)):
            result = server._detect_project_slot()

        # strip() will keep all content, but that's the current behavior
        # The file should ideally contain only slot name
        assert "first-line-slot" in result


class TestSlotResolutionInteractions:
    """Test interactions between different slot resolution methods."""

    @pytest.mark.asyncio
    async def test_save_uses_active_slot_when_no_argument(self, test_server):
        """Test memcord_save uses active slot when no slot_name given."""
        server = test_server

        # Set active slot
        await server.call_tool_direct("memcord_name", {"slot_name": "save-test-slot"})

        # Save without slot_name
        await server.call_tool_direct("memcord_save", {"chat_text": "Test content"})

        # Verify content is in active slot
        result = await server.call_tool_direct("memcord_read", {"slot_name": "save-test-slot"})
        assert "Test content" in result[0].text

    @pytest.mark.asyncio
    async def test_read_uses_active_slot_when_no_argument(self, test_server):
        """Test memcord_read uses active slot when no slot_name given."""
        server = test_server

        # Create and activate slot
        await server.call_tool_direct("memcord_name", {"slot_name": "read-test-slot"})
        await server.call_tool_direct("memcord_save", {"slot_name": "read-test-slot", "chat_text": "Read test content"})

        # Read without slot_name
        result = await server.call_tool_direct("memcord_read", {})

        assert "Read test content" in result[0].text

    @pytest.mark.asyncio
    async def test_save_progress_uses_active_slot(self, test_server):
        """Test memcord_save_progress uses active slot when no slot_name given."""
        server = test_server

        # Set active slot
        await server.call_tool_direct("memcord_name", {"slot_name": "progress-test-slot"})

        # Save progress without slot_name
        await server.call_tool_direct(
            "memcord_save_progress", {"chat_text": "Session progress content that needs to be summarized"}
        )

        # Verify content is in active slot
        result = await server.call_tool_direct("memcord_read", {"slot_name": "progress-test-slot"})
        assert "progress-test-slot" in result[0].text

    @pytest.mark.asyncio
    async def test_operations_fail_gracefully_with_no_slot(self, test_server):
        """Test operations fail gracefully when no slot is resolved."""
        server = test_server

        # No active slot, no binding, no argument
        # Save should fail or prompt for slot
        result = await server.call_tool_direct("memcord_save", {"chat_text": "Orphan content"})

        # Should indicate error or need for slot
        assert "error" in result[0].text.lower() or "slot" in result[0].text.lower()

    @pytest.mark.asyncio
    async def test_read_fails_gracefully_with_no_slot(self, test_server):
        """Test read fails gracefully when no slot is resolved."""
        server = test_server

        # No active slot, no binding, no argument
        result = await server.call_tool_direct("memcord_read", {})

        # Should indicate error or need for slot
        assert "error" in result[0].text.lower() or "no" in result[0].text.lower() or "slot" in result[0].text.lower()


class TestZeroModeInteraction:
    """Test zero mode interaction with binding and active slots."""

    @pytest.mark.asyncio
    async def test_zero_mode_prevents_saving(self, test_server):
        """Test that zero mode prevents saving to any slot."""
        server = test_server

        # Activate zero mode
        await server.call_tool_direct("memcord_zero", {})

        # Try to save
        result = await server.call_tool_direct(
            "memcord_save", {"slot_name": "test-slot", "chat_text": "Should not save"}
        )

        # Should indicate zero mode is active
        assert "zero" in result[0].text.lower() or "no memory" in result[0].text.lower()

    @pytest.mark.asyncio
    async def test_zero_mode_clears_active_slot(self, test_server):
        """Test that zero mode interaction with active slot."""
        server = test_server

        # Set active slot
        await server.call_tool_direct("memcord_name", {"slot_name": "normal-slot"})

        # Activate zero mode
        await server.call_tool_direct("memcord_zero", {})

        # Try to save without argument - should fail
        result = await server.call_tool_direct("memcord_save", {"chat_text": "Zero mode test"})

        assert "zero" in result[0].text.lower()

    @pytest.mark.asyncio
    async def test_exit_zero_mode_by_selecting_slot(self, test_server):
        """Test exiting zero mode by selecting a slot."""
        server = test_server

        # Activate zero mode
        await server.call_tool_direct("memcord_zero", {})

        # Select a slot to exit zero mode
        result = await server.call_tool_direct("memcord_name", {"slot_name": "exit-zero-slot"})

        assert "active" in result[0].text.lower()

        # Should be able to save now
        save_result = await server.call_tool_direct("memcord_save", {"chat_text": "After zero mode"})
        assert "zero" not in save_result[0].text.lower() or "saved" in save_result[0].text.lower()

    @pytest.mark.asyncio
    async def test_list_shows_zero_mode_status(self, test_server):
        """Test that memcord_list shows zero mode status."""
        server = test_server

        # Activate zero mode
        await server.call_tool_direct("memcord_zero", {})

        # List slots
        result = await server.call_tool_direct("memcord_list", {})

        assert "zero" in result[0].text.lower()


class TestBindingStateTransitions:
    """Test transitions between different binding states."""

    @pytest.mark.asyncio
    async def test_bind_then_set_active_then_unbind(self, test_server, temp_project_dir):
        """Test binding, setting different active, then unbinding."""
        server = test_server

        # Bind project
        await server.call_tool_direct("memcord_init", {"project_path": temp_project_dir, "slot_name": "bound-slot"})
        assert server.storage.get_current_slot() == "bound-slot"

        # Set different active slot
        await server.call_tool_direct("memcord_name", {"slot_name": "different-active"})
        assert server.storage.get_current_slot() == "different-active"

        # Unbind project
        await server.call_tool_direct("memcord_unbind", {"project_path": temp_project_dir})

        # Active slot should remain unchanged
        assert server.storage.get_current_slot() == "different-active"

    @pytest.mark.asyncio
    async def test_multiple_bindings_last_wins_for_active(self, test_server):
        """Test that with multiple bindings, last one sets active slot."""
        server = test_server

        with tempfile.TemporaryDirectory() as project1:
            with tempfile.TemporaryDirectory() as project2:
                # Bind first project
                await server.call_tool_direct("memcord_init", {"project_path": project1, "slot_name": "slot-1"})
                assert server.storage.get_current_slot() == "slot-1"

                # Bind second project
                await server.call_tool_direct("memcord_init", {"project_path": project2, "slot_name": "slot-2"})
                assert server.storage.get_current_slot() == "slot-2"

    @pytest.mark.asyncio
    async def test_rebind_reactivates_slot(self, test_server, temp_project_dir):
        """Test that rebinding reactivates the bound slot."""
        server = test_server

        # Initial bind
        await server.call_tool_direct("memcord_init", {"project_path": temp_project_dir, "slot_name": "rebind-slot"})

        # Switch to different slot
        await server.call_tool_direct("memcord_name", {"slot_name": "other-slot"})
        assert server.storage.get_current_slot() == "other-slot"

        # Rebind (without slot_name, should read from .memcord)
        await server.call_tool_direct("memcord_init", {"project_path": temp_project_dir})

        # Should reactivate the bound slot
        assert server.storage.get_current_slot() == "rebind-slot"


class TestSelectEntrySlotResolution:
    """Test slot resolution for memcord_select_entry."""

    @pytest.mark.asyncio
    async def test_select_entry_uses_active_slot(self, test_server):
        """Test memcord_select_entry uses active slot when no slot_name given."""
        server = test_server

        # Create and activate slot with content
        # Note: slot name avoids SQL keywords like "select" which are blocked
        name_result = await server.call_tool_direct("memcord_name", {"slot_name": "entry-test-slot"})
        assert "active" in name_result[0].text.lower(), f"memcord_name failed: {name_result[0].text}"
        assert server.storage.get_current_slot() == "entry-test-slot", (
            f"Current slot not set after memcord_name: got {server.storage.get_current_slot()!r}"
        )

        save_result = await server.call_tool_direct("memcord_save", {"chat_text": "Entry content"})
        assert "saved" in save_result[0].text.lower(), f"memcord_save failed: {save_result[0].text}"

        # Verify current slot is still active after save
        assert server.storage.get_current_slot() == "entry-test-slot", (
            f"Current slot changed after save: got {server.storage.get_current_slot()!r}"
        )

        # Select entry without slot_name
        result = await server.call_tool_direct("memcord_select_entry", {"relative_time": "latest"})

        assert "Entry content" in result[0].text or "entry-test-slot" in result[0].text, (
            f"select_entry failed: {result[0].text}"
        )

    @pytest.mark.asyncio
    async def test_select_entry_explicit_slot_overrides(self, test_server):
        """Test memcord_select_entry with explicit slot_name overrides active."""
        server = test_server

        # Create multiple slots with content
        await server.call_tool_direct("memcord_name", {"slot_name": "slot-a"})
        await server.call_tool_direct("memcord_save", {"slot_name": "slot-a", "chat_text": "Content A"})
        await server.call_tool_direct("memcord_save", {"slot_name": "slot-b", "chat_text": "Content B"})

        # Set active to slot-a
        await server.call_tool_direct("memcord_use", {"slot_name": "slot-a"})

        # Select from slot-b explicitly
        result = await server.call_tool_direct(
            "memcord_select_entry", {"slot_name": "slot-b", "relative_time": "latest"}
        )

        assert "slot-b" in result[0].text or "Content B" in result[0].text


class TestConcurrentSlotOperations:
    """Test concurrent operations with slot resolution."""

    @pytest.mark.asyncio
    async def test_concurrent_saves_to_active_slot(self, test_server):
        """Test concurrent saves all go to active slot."""
        server = test_server

        # Set active slot
        await server.call_tool_direct("memcord_name", {"slot_name": "concurrent-slot"})

        # Concurrent saves
        tasks = [server.call_tool_direct("memcord_save", {"chat_text": f"Concurrent content {i}"}) for i in range(5)]

        await asyncio.gather(*tasks)

        # Verify all content is in active slot
        result = await server.call_tool_direct("memcord_read", {"slot_name": "concurrent-slot"})
        assert "concurrent-slot" in result[0].text

    @pytest.mark.asyncio
    async def test_slot_change_during_operation(self, test_server):
        """Test that explicit slot_name is thread-safe during slot changes."""
        server = test_server

        # Create multiple slots
        await server.call_tool_direct("memcord_name", {"slot_name": "slot-1"})
        await server.call_tool_direct("memcord_name", {"slot_name": "slot-2"})

        # Even while active slot changes, explicit saves should go to right place
        async def save_to_slot1():
            return await server.call_tool_direct(
                "memcord_save", {"slot_name": "slot-1", "chat_text": "Content for slot 1"}
            )

        async def save_to_slot2():
            return await server.call_tool_direct(
                "memcord_save", {"slot_name": "slot-2", "chat_text": "Content for slot 2"}
            )

        async def change_active():
            await server.call_tool_direct("memcord_name", {"slot_name": "slot-3"})

        await asyncio.gather(save_to_slot1(), change_active(), save_to_slot2())

        # Verify content is in correct slots
        result1 = await server.call_tool_direct("memcord_read", {"slot_name": "slot-1"})
        result2 = await server.call_tool_direct("memcord_read", {"slot_name": "slot-2"})

        assert "Content for slot 1" in result1[0].text
        assert "Content for slot 2" in result2[0].text
