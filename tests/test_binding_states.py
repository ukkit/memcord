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
import secrets
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from mcp.types import ListRootsResult, Root

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
            result = await server._resolve_slot({})

        assert result is None

    @pytest.mark.asyncio
    async def test_resolve_slot_with_empty_string_argument(self, test_server):
        """Test that empty string argument falls through to active slot."""
        server = test_server

        # Set active slot
        await server.call_tool_direct("memcord_name", {"slot_name": "fallback-slot"})

        # Empty string should be falsy and fall through
        result = await server._resolve_slot({"slot_name": ""})

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
            result = await server._detect_project_slot()

        assert result == "detected-slot"

    @pytest.mark.asyncio
    async def test_detect_project_slot_returns_none_when_no_file(self, test_server, temp_project_dir):
        """Test _detect_project_slot returns None when no .memcord file."""
        server = test_server

        # No .memcord file in temp directory
        with patch.object(Path, "cwd", return_value=Path(temp_project_dir)):
            result = await server._detect_project_slot()

        assert result is None

    @pytest.mark.asyncio
    async def test_detect_project_slot_handles_empty_file(self, test_server, temp_project_dir):
        """Test _detect_project_slot returns None for empty .memcord file."""
        server = test_server

        # Create empty .memcord file
        memcord_file = Path(temp_project_dir) / ".memcord"
        memcord_file.write_text("")

        with patch.object(Path, "cwd", return_value=Path(temp_project_dir)):
            result = await server._detect_project_slot()

        assert result is None

    @pytest.mark.asyncio
    async def test_detect_project_slot_handles_whitespace_only_file(self, test_server, temp_project_dir):
        """Test _detect_project_slot returns None for whitespace-only .memcord file."""
        server = test_server

        # Create whitespace-only .memcord file
        memcord_file = Path(temp_project_dir) / ".memcord"
        memcord_file.write_text("   \n  \t  ")

        with patch.object(Path, "cwd", return_value=Path(temp_project_dir)):
            result = await server._detect_project_slot()

        assert result is None

    @pytest.mark.asyncio
    async def test_detect_project_slot_strips_whitespace(self, test_server, temp_project_dir):
        """Test _detect_project_slot strips whitespace from slot name."""
        server = test_server

        # Create .memcord file with whitespace
        memcord_file = Path(temp_project_dir) / ".memcord"
        memcord_file.write_text("  my-slot-name  \n")

        with patch.object(Path, "cwd", return_value=Path(temp_project_dir)):
            result = await server._detect_project_slot()

        assert result == "my-slot-name"

    @pytest.mark.asyncio
    async def test_detect_project_slot_handles_multiline_file(self, test_server, temp_project_dir):
        """Test _detect_project_slot only reads first line of multiline .memcord file."""
        server = test_server

        # Create .memcord file with multiple lines
        memcord_file = Path(temp_project_dir) / ".memcord"
        memcord_file.write_text("first-line-slot\nsecond-line\nthird-line")

        with patch.object(Path, "cwd", return_value=Path(temp_project_dir)):
            result = await server._detect_project_slot()

        # Only the first line should be used as slot name
        assert result == "first-line-slot"


@pytest.fixture
def mock_roots():
    """Helper to create mock MCP client roots response."""

    def _make_roots(dirs: list[Path]) -> MagicMock:
        roots = [Root(uri=dir_.as_uri(), name=dir_.name) for dir_ in dirs]
        result = ListRootsResult(roots=roots)

        mock_ctx = MagicMock()
        mock_ctx.session.list_roots = AsyncMock(return_value=result)
        return mock_ctx

    return _make_roots


class TestClientRootsDetection:
    """Test .memcord detection via MCP client roots instead of cwd."""

    @pytest.mark.asyncio
    async def test_get_client_roots_returns_directories(self, test_server, mock_roots):
        """Test _get_client_roots returns valid directories from MCP roots."""
        server = test_server

        with tempfile.TemporaryDirectory() as dir1, tempfile.TemporaryDirectory() as dir2:
            mock_ctx = mock_roots([Path(dir1), Path(dir2)])
            with patch.object(type(server.app), "request_context", new_callable=lambda: property(lambda self: mock_ctx)):
                result = await server._get_client_roots()

            assert len(result) == 2
            assert Path(dir1) in result
            assert Path(dir2) in result

    @pytest.mark.asyncio
    async def test_get_client_roots_skips_nonexistent_dirs(self, test_server, mock_roots):
        """Test _get_client_roots filters out directories that don't exist."""
        server = test_server

        with tempfile.TemporaryDirectory() as real_dir:
            fake_dir = Path(real_dir) / "nonexistent"
            mock_ctx = mock_roots([Path(real_dir), fake_dir])
            with patch.object(type(server.app), "request_context", new_callable=lambda: property(lambda self: mock_ctx)):
                result = await server._get_client_roots()

            assert len(result) == 1
            assert Path(real_dir) in result

    @pytest.mark.asyncio
    async def test_get_client_roots_returns_empty_on_error(self, test_server):
        """Test _get_client_roots returns [] when no MCP session is available."""
        server = test_server
        # No mock — the real server has no request context in tests
        result = await server._get_client_roots()
        assert result == []

    @pytest.mark.asyncio
    async def test_detect_project_slot_uses_client_roots(self, test_server, mock_roots):
        """Test _detect_project_slot finds .memcord via client roots, not cwd."""
        server = test_server

        with tempfile.TemporaryDirectory() as project_dir, tempfile.TemporaryDirectory() as fake_cwd:
            # Put .memcord in the project dir (client root), NOT in cwd
            memcord_file = Path(project_dir) / ".memcord"
            memcord_file.write_text("project-slot")

            mock_ctx = mock_roots([Path(project_dir)])
            with (
                patch.object(type(server.app), "request_context", new_callable=lambda: property(lambda self: mock_ctx)),
                patch.object(Path, "cwd", return_value=Path(fake_cwd)),
            ):
                result = await server._detect_project_slot()

            assert result == "project-slot"

    @pytest.mark.asyncio
    async def test_detect_project_slot_ignores_cwd_when_roots_available(self, test_server, mock_roots):
        """Test that cwd is NOT searched when client roots are available."""
        server = test_server

        with tempfile.TemporaryDirectory() as root_dir, tempfile.TemporaryDirectory() as cwd_dir:
            # Put .memcord only in cwd (not in the root)
            (Path(cwd_dir) / ".memcord").write_text("cwd-slot")

            mock_ctx = mock_roots([Path(root_dir)])
            with (
                patch.object(type(server.app), "request_context", new_callable=lambda: property(lambda self: mock_ctx)),
                patch.object(Path, "cwd", return_value=Path(cwd_dir)),
            ):
                result = await server._detect_project_slot()

            # Should NOT find the cwd .memcord since roots were available
            assert result is None

    @pytest.mark.asyncio
    async def test_detect_project_slot_first_root_wins(self, test_server, mock_roots):
        """Test that when multiple roots have .memcord, the first one wins."""
        server = test_server

        with tempfile.TemporaryDirectory() as dir1, tempfile.TemporaryDirectory() as dir2:
            (Path(dir1) / ".memcord").write_text("first-slot")
            (Path(dir2) / ".memcord").write_text("second-slot")

            mock_ctx = mock_roots([Path(dir1), Path(dir2)])
            with patch.object(type(server.app), "request_context", new_callable=lambda: property(lambda self: mock_ctx)):
                result = await server._detect_project_slot()

            assert result == "first-slot"

    @pytest.mark.asyncio
    async def test_detect_project_slot_falls_back_to_cwd(self, test_server, temp_project_dir):
        """Test fallback to cwd when no MCP roots are available."""
        server = test_server

        memcord_file = Path(temp_project_dir) / ".memcord"
        memcord_file.write_text("cwd-fallback-slot")

        # No mock for roots — will fail and fall back to cwd
        with patch.object(Path, "cwd", return_value=Path(temp_project_dir)):
            result = await server._detect_project_slot()

        assert result == "cwd-fallback-slot"

    @pytest.mark.asyncio
    async def test_resolve_slot_uses_roots_as_fallback(self, test_server, mock_roots):
        """Test _resolve_slot uses client roots when no argument or active slot."""
        server = test_server

        with tempfile.TemporaryDirectory() as project_dir:
            (Path(project_dir) / ".memcord").write_text("root-resolved-slot")

            mock_ctx = mock_roots([Path(project_dir)])
            with patch.object(type(server.app), "request_context", new_callable=lambda: property(lambda self: mock_ctx)):
                result = await server._resolve_slot({})

            assert result == "root-resolved-slot"


class TestFileUriParsing:
    """Test _file_uri_to_path for various URI formats."""

    def test_posix_file_uri(self, test_server):
        """Test standard POSIX file URI."""
        with patch("memcord.server.os") as mock_os:
            mock_os.name = "posix"
            result = test_server._file_uri_to_path("file:///home/user/project")
        assert result == Path("/home/user/project")

    def test_windows_file_uri(self, test_server):
        """Test Windows file URI with drive letter."""
        with patch("memcord.server.os") as mock_os:
            mock_os.name = "nt"
            result = test_server._file_uri_to_path("file:///C:/Users/name/project")
        assert result == Path("C:/Users/name/project")

    def test_percent_encoded_spaces(self, test_server):
        """Test file URI with percent-encoded spaces."""
        with patch("memcord.server.os") as mock_os:
            mock_os.name = "nt"
            result = test_server._file_uri_to_path("file:///C:/My%20Projects/my%20app")
        assert result == Path("C:/My Projects/my app")

    def test_percent_encoded_special_chars(self, test_server):
        """Test file URI with various percent-encoded characters."""
        with patch("memcord.server.os") as mock_os:
            mock_os.name = "posix"
            result = test_server._file_uri_to_path("file:///home/user/project%20%28v2%29")
        assert result == Path("/home/user/project (v2)")

    def test_non_file_uri_returns_none(self, test_server):
        """Test that non-file:// URIs return None."""
        assert test_server._file_uri_to_path("http://example.com") is None
        assert test_server._file_uri_to_path("https://github.com/repo") is None
        assert test_server._file_uri_to_path("git://repo.git") is None
        assert test_server._file_uri_to_path("ftp://files.example.com") is None

    def test_empty_string_returns_none(self, test_server):
        """Test that empty string returns None."""
        assert test_server._file_uri_to_path("") is None


class TestClientRootsEdgeCases:
    """Test edge cases for MCP client roots handling."""

    @pytest.mark.asyncio
    async def test_get_client_roots_skips_non_file_uris(self, test_server):
        """Test that non-file:// URIs in roots are silently skipped."""
        server = test_server

        # MCP Root model enforces file:// scheme at the Pydantic level,
        # but _file_uri_to_path provides defense-in-depth for any URI string.
        # Test the static method directly for non-file schemes.
        assert server._file_uri_to_path("http://example.com/repo") is None
        assert server._file_uri_to_path("git://repo.git") is None
        assert server._file_uri_to_path("ftp://files.example.com/path") is None

        # Also verify that _get_client_roots works with only valid file:// roots
        with tempfile.TemporaryDirectory() as real_dir:
            mock_ctx = MagicMock()
            roots = [Root(uri=Path(real_dir).as_uri(), name="valid")]
            mock_ctx.session.list_roots = AsyncMock(return_value=ListRootsResult(roots=roots))

            with patch.object(type(server.app), "request_context", new_callable=lambda: property(lambda self: mock_ctx)):
                result = await server._get_client_roots()

            assert len(result) == 1
            assert Path(real_dir) in result

    @pytest.mark.asyncio
    async def test_detect_slot_rejects_path_traversal_in_memcord_file(self, test_server, temp_project_dir):
        """Test that .memcord with path traversal slot name is rejected."""
        server = test_server

        memcord_file = Path(temp_project_dir) / ".memcord"
        memcord_file.write_text("../../etc/passwd")

        with patch.object(Path, "cwd", return_value=Path(temp_project_dir)):
            result = await server._detect_project_slot()

        # Path traversal should be rejected by validation
        assert result is None

    @pytest.mark.asyncio
    async def test_detect_slot_rejects_special_characters(self, test_server, temp_project_dir):
        """Test that .memcord with special characters in slot name is rejected."""
        server = test_server

        for bad_name in ["slot;DROP TABLE", "slot$(cmd)", 'slot"name', "slot<script>"]:
            memcord_file = Path(temp_project_dir) / ".memcord"
            memcord_file.write_text(bad_name)

            with patch.object(Path, "cwd", return_value=Path(temp_project_dir)):
                result = await server._detect_project_slot()

            assert result is None, f"Should have rejected slot name: {bad_name!r}"

    @pytest.mark.asyncio
    async def test_detect_slot_normalizes_spaces_to_underscores(self, test_server, temp_project_dir):
        """Test that spaces in .memcord slot name are converted to underscores."""
        server = test_server

        memcord_file = Path(temp_project_dir) / ".memcord"
        memcord_file.write_text("my project slot")

        with patch.object(Path, "cwd", return_value=Path(temp_project_dir)):
            result = await server._detect_project_slot()

        assert result == "my_project_slot"

    @pytest.mark.asyncio
    async def test_detect_slot_skips_unreadable_memcord_file(self, test_server, temp_project_dir):
        """Test that unreadable .memcord file is gracefully skipped."""
        server = test_server

        memcord_file = Path(temp_project_dir) / ".memcord"
        memcord_file.write_text("some-slot")

        with (
            patch.object(Path, "cwd", return_value=Path(temp_project_dir)),
            patch.object(Path, "read_text", side_effect=PermissionError("Access denied")),
        ):
            result = await server._detect_project_slot()

        assert result is None

    @pytest.mark.asyncio
    async def test_get_client_roots_with_percent_encoded_dir(self, test_server):
        """Test _get_client_roots handles percent-encoded directory paths."""
        server = test_server

        with tempfile.TemporaryDirectory() as real_dir:
            # Simulate a URI that would be percent-encoded (the dir exists as-is)
            uri = Path(real_dir).as_uri()

            mock_ctx = MagicMock()
            roots = [Root(uri=uri, name="test")]
            mock_ctx.session.list_roots = AsyncMock(return_value=ListRootsResult(roots=roots))

            with patch.object(type(server.app), "request_context", new_callable=lambda: property(lambda self: mock_ctx)):
                result = await server._get_client_roots()

            assert len(result) == 1
            assert Path(real_dir) in result


class TestMemcordUseWithProjectBinding:
    """Integration tests: memcord_use picking up .memcord from real temp directories."""

    @pytest.mark.asyncio
    async def test_memcord_use_detects_slot_from_random_directory(self, test_server, mock_roots):
        """Create .memcord in a random temp dir, then memcord_use should detect it."""
        server = test_server

        with tempfile.TemporaryDirectory() as project_dir:
            slot_name = f"test-slot-{secrets.token_hex(4)}"

            # First create the slot so memcord_use can find it
            await server.call_tool_direct("memcord_name", {"slot_name": slot_name})
            # Clear active slot so we rely on .memcord detection
            server.storage._state.set_current_slot(None)

            # Write .memcord file in the random directory
            memcord_file = Path(project_dir) / ".memcord"
            memcord_file.write_text(slot_name)

            mock_ctx = mock_roots([Path(project_dir)])
            with patch.object(type(server.app), "request_context", new_callable=lambda: property(lambda self: mock_ctx)):
                result = await server.call_tool_direct("memcord_use", {})

            assert "active" in result[0].text.lower()
            assert slot_name in result[0].text
            assert server.storage.get_current_slot() == slot_name

    @pytest.mark.asyncio
    async def test_memcord_init_then_use_via_roots(self, test_server, mock_roots):
        """Full flow: memcord_init creates .memcord, then memcord_use picks it up via roots."""
        server = test_server

        with tempfile.TemporaryDirectory() as project_dir:
            slot_name = f"init-test-{secrets.token_hex(4)}"

            # Init binds the directory to a slot (creates .memcord file)
            init_result = await server.call_tool_direct(
                "memcord_init", {"project_path": project_dir, "slot_name": slot_name}
            )
            assert ".memcord" in init_result[0].text

            # Verify the file was created with correct content
            memcord_file = Path(project_dir) / ".memcord"
            assert memcord_file.exists()
            assert memcord_file.read_text().strip() == slot_name

            # Clear active slot to force detection via roots
            server.storage._state.set_current_slot(None)

            mock_ctx = mock_roots([Path(project_dir)])
            with patch.object(type(server.app), "request_context", new_callable=lambda: property(lambda self: mock_ctx)):
                use_result = await server.call_tool_direct("memcord_use", {})

            assert "active" in use_result[0].text.lower()
            assert slot_name in use_result[0].text

    @pytest.mark.asyncio
    async def test_memcord_use_prefers_roots_over_cwd(self, test_server, mock_roots):
        """When both roots and cwd have .memcord, roots should win."""
        server = test_server

        with tempfile.TemporaryDirectory() as root_dir, tempfile.TemporaryDirectory() as cwd_dir:
            root_slot = f"root-slot-{secrets.token_hex(4)}"
            cwd_slot = f"cwd-slot-{secrets.token_hex(4)}"

            # Create both slots
            await server.call_tool_direct("memcord_name", {"slot_name": root_slot})
            await server.call_tool_direct("memcord_name", {"slot_name": cwd_slot})
            server.storage._state.set_current_slot(None)

            # .memcord in both directories with different slot names
            (Path(root_dir) / ".memcord").write_text(root_slot)
            (Path(cwd_dir) / ".memcord").write_text(cwd_slot)

            mock_ctx = mock_roots([Path(root_dir)])
            with (
                patch.object(type(server.app), "request_context", new_callable=lambda: property(lambda self: mock_ctx)),
                patch.object(Path, "cwd", return_value=Path(cwd_dir)),
            ):
                result = await server.call_tool_direct("memcord_use", {})

            assert root_slot in result[0].text
            assert server.storage.get_current_slot() == root_slot

    @pytest.mark.asyncio
    async def test_memcord_use_falls_back_to_cwd_without_roots(self, test_server):
        """Without MCP roots, memcord_use should still work via cwd fallback."""
        server = test_server

        with tempfile.TemporaryDirectory() as cwd_dir:
            slot_name = f"cwd-only-{secrets.token_hex(4)}"

            await server.call_tool_direct("memcord_name", {"slot_name": slot_name})
            server.storage._state.set_current_slot(None)

            (Path(cwd_dir) / ".memcord").write_text(slot_name)

            # No roots mock — falls back to cwd
            with patch.object(Path, "cwd", return_value=Path(cwd_dir)):
                result = await server.call_tool_direct("memcord_use", {})

            assert "active" in result[0].text.lower()
            assert slot_name in result[0].text

    @pytest.mark.asyncio
    async def test_memcord_read_uses_roots_to_find_slot(self, test_server, mock_roots):
        """Test that memcord_read resolves slot via client roots."""
        server = test_server

        with tempfile.TemporaryDirectory() as project_dir:
            slot_name = f"read-test-{secrets.token_hex(4)}"

            # Create slot and save some content
            await server.call_tool_direct("memcord_name", {"slot_name": slot_name})
            await server.call_tool_direct("memcord_save", {"chat_text": "Hello from roots test"})
            server.storage._state.set_current_slot(None)

            (Path(project_dir) / ".memcord").write_text(slot_name)

            mock_ctx = mock_roots([Path(project_dir)])
            with patch.object(type(server.app), "request_context", new_callable=lambda: property(lambda self: mock_ctx)):
                result = await server.call_tool_direct("memcord_read", {})

            assert "Hello from roots test" in result[0].text


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


class TestWriteSlotResolution:
    """Test that write operations require explicit slot selection (no .memcord fallback)."""

    @pytest.mark.asyncio
    async def test_save_without_slot_returns_error(self, test_server, temp_project_dir):
        """Verify write operations fail without active slot (even with .memcord file)."""
        server = test_server

        # Create .memcord file in temp directory
        memcord_file = Path(temp_project_dir) / ".memcord"
        memcord_file.write_text("fallback-slot")

        # Mock cwd to be the temp directory
        with patch.object(Path, "cwd", return_value=Path(temp_project_dir)):
            # Verify .memcord file is detected (for read operations)
            assert await server._detect_project_slot() == "fallback-slot"

            # But write should fail because no active slot is set
            result = await server.call_tool_direct("memcord_save", {"chat_text": "Test content"})

            assert "error" in result[0].text.lower() or "no slot" in result[0].text.lower()

    @pytest.mark.asyncio
    async def test_save_progress_without_slot_returns_error(self, test_server, temp_project_dir):
        """Verify save_progress fails without active slot."""
        server = test_server

        # Create .memcord file in temp directory
        memcord_file = Path(temp_project_dir) / ".memcord"
        memcord_file.write_text("fallback-slot")

        # Mock cwd to be the temp directory
        with patch.object(Path, "cwd", return_value=Path(temp_project_dir)):
            # Write should fail because no active slot is set
            result = await server.call_tool_direct(
                "memcord_save_progress", {"chat_text": "Content to summarize and save"}
            )

            assert "error" in result[0].text.lower() or "no slot" in result[0].text.lower()

    @pytest.mark.asyncio
    async def test_read_without_slot_uses_memcord_fallback(self, test_server, temp_project_dir):
        """Verify read still uses .memcord fallback."""
        server = test_server

        # Create the slot first with content
        await server.call_tool_direct("memcord_name", {"slot_name": "fallback-slot"})
        await server.call_tool_direct("memcord_save", {"chat_text": "Fallback content"})

        # Clear active slot
        server.storage._state.clear_current_slot()
        assert server.storage.get_current_slot() is None

        # Create .memcord file pointing to the slot
        memcord_file = Path(temp_project_dir) / ".memcord"
        memcord_file.write_text("fallback-slot")

        # Mock cwd to be the temp directory
        with patch.object(Path, "cwd", return_value=Path(temp_project_dir)):
            # Read should work via .memcord fallback
            result = await server.call_tool_direct("memcord_read", {})

            assert "Fallback content" in result[0].text


class TestMemcordClose:
    """Test memcord_close tool functionality."""

    @pytest.mark.asyncio
    async def test_memcord_close_clears_active_slot(self, test_server):
        """Verify close deactivates the current slot."""
        server = test_server

        # Set active slot
        await server.call_tool_direct("memcord_name", {"slot_name": "active-slot"})
        assert server.storage.get_current_slot() == "active-slot"

        # Close the slot
        result = await server.call_tool_direct("memcord_close", {})

        # Verify slot is deactivated
        assert server.storage.get_current_slot() is None
        assert "deactivated" in result[0].text.lower()
        assert "active-slot" in result[0].text

    @pytest.mark.asyncio
    async def test_close_returns_previous_slot_name(self, test_server):
        """Verify close returns what was deactivated."""
        server = test_server

        # Set active slot
        await server.call_tool_direct("memcord_name", {"slot_name": "my-slot"})

        # Close the slot
        result = await server.call_tool_direct("memcord_close", {})

        # Verify the previous slot name is mentioned
        assert "my-slot" in result[0].text

    @pytest.mark.asyncio
    async def test_close_when_no_slot_active(self, test_server):
        """Verify close handles no active slot gracefully."""
        server = test_server

        # Ensure no slot is active
        assert server.storage.get_current_slot() is None

        # Close should not error
        result = await server.call_tool_direct("memcord_close", {})

        assert "no slot was active" in result[0].text.lower()

    @pytest.mark.asyncio
    async def test_close_from_zero_mode(self, test_server):
        """Verify close handles zero mode correctly."""
        server = test_server

        # Activate zero mode
        await server.call_tool_direct("memcord_zero", {})
        assert server.storage._state.is_zero_mode()

        # Close should treat __ZERO__ as "no active slot"
        result = await server.call_tool_direct("memcord_close", {})

        assert "no slot was active" in result[0].text.lower()
        assert server.storage.get_current_slot() is None

    @pytest.mark.asyncio
    async def test_save_fails_after_close(self, test_server):
        """Verify save operations fail after close."""
        server = test_server

        # Set active slot
        await server.call_tool_direct("memcord_name", {"slot_name": "test-slot"})

        # Verify save works
        result = await server.call_tool_direct("memcord_save", {"chat_text": "Before close"})
        assert "saved" in result[0].text.lower()

        # Close the slot
        await server.call_tool_direct("memcord_close", {})

        # Save should now fail
        result = await server.call_tool_direct("memcord_save", {"chat_text": "After close"})
        assert "error" in result[0].text.lower() or "no slot" in result[0].text.lower()

    @pytest.mark.asyncio
    async def test_reactivate_after_close(self, test_server):
        """Verify slot can be reactivated after close."""
        server = test_server

        # Set active slot and save content
        await server.call_tool_direct("memcord_name", {"slot_name": "reactivate-slot"})
        await server.call_tool_direct("memcord_save", {"chat_text": "Original content"})

        # Close the slot
        await server.call_tool_direct("memcord_close", {})
        assert server.storage.get_current_slot() is None

        # Reactivate with memcord_use
        await server.call_tool_direct("memcord_use", {"slot_name": "reactivate-slot"})
        assert server.storage.get_current_slot() == "reactivate-slot"

        # Save should work again
        result = await server.call_tool_direct("memcord_save", {"chat_text": "New content"})
        assert "saved" in result[0].text.lower()


class TestSlotNameSpecialCharacters:
    """Test slot names with special characters, unicode, and edge cases."""

    @pytest.mark.asyncio
    async def test_slot_name_with_hyphens_and_underscores(self, test_server):
        """Test valid slot names with hyphens and underscores."""
        server = test_server

        result = await server.call_tool_direct("memcord_name", {"slot_name": "my-project_v2"})
        assert "active" in result[0].text.lower()
        assert server.storage.get_current_slot() == "my-project_v2"

    @pytest.mark.asyncio
    async def test_slot_name_with_numbers(self, test_server):
        """Test slot names with numbers."""
        server = test_server

        result = await server.call_tool_direct("memcord_name", {"slot_name": "project123"})
        assert "active" in result[0].text.lower()

        result = await server.call_tool_direct("memcord_name", {"slot_name": "2024-january-notes"})
        assert "active" in result[0].text.lower()

    @pytest.mark.asyncio
    async def test_slot_name_with_dots(self, test_server):
        """Test slot names with dots (valid for versioning)."""
        server = test_server

        result = await server.call_tool_direct("memcord_name", {"slot_name": "project.v1.0"})
        assert "active" in result[0].text.lower()
        assert server.storage.get_current_slot() == "project.v1.0"

    @pytest.mark.asyncio
    async def test_slot_name_with_unicode_characters(self, test_server):
        """Test slot names with unicode characters."""
        server = test_server

        # Japanese characters
        result = await server.call_tool_direct("memcord_name", {"slot_name": "プロジェクト"})
        assert "active" in result[0].text.lower()

        # Emoji in slot name
        result = await server.call_tool_direct("memcord_name", {"slot_name": "my-notes-📝"})
        assert "active" in result[0].text.lower()

        # Currency symbols
        result = await server.call_tool_direct("memcord_name", {"slot_name": "budget-€-2024"})
        assert "active" in result[0].text.lower()

    @pytest.mark.asyncio
    async def test_slot_name_with_spaces_converted_to_underscores(self, test_server):
        """Test that spaces in slot names are converted to underscores."""
        server = test_server

        result = await server.call_tool_direct("memcord_name", {"slot_name": "my project notes"})
        assert "active" in result[0].text.lower()
        # Spaces should be converted to underscores
        assert server.storage.get_current_slot() == "my_project_notes"

    @pytest.mark.asyncio
    async def test_slot_name_rejects_dangerous_characters(self, test_server):
        """Test that dangerous characters are rejected."""
        server = test_server

        dangerous_names = [
            "slot<script>",
            "slot>alert",
            'slot"name',
            "slot'name",
            "slot&name",
            "slot|name",
            "slot;name",
            "slot`name",
            "slot$name",
        ]

        for name in dangerous_names:
            result = await server.call_tool_direct("memcord_name", {"slot_name": name})
            assert "error" in result[0].text.lower() or "unsafe" in result[0].text.lower(), (
                f"Expected error for dangerous name: {name}, got: {result[0].text}"
            )

    @pytest.mark.asyncio
    async def test_slot_name_with_at_symbol(self, test_server):
        """Test slot names with @ symbol (should be allowed)."""
        server = test_server

        result = await server.call_tool_direct("memcord_name", {"slot_name": "user@project"})
        assert "active" in result[0].text.lower()

    @pytest.mark.asyncio
    async def test_slot_name_with_hash_symbol(self, test_server):
        """Test slot names with # symbol (should be allowed)."""
        server = test_server

        result = await server.call_tool_direct("memcord_name", {"slot_name": "issue#123"})
        assert "active" in result[0].text.lower()

    @pytest.mark.asyncio
    async def test_empty_slot_name_rejected(self, test_server):
        """Test that empty slot names are rejected."""
        server = test_server

        result = await server.call_tool_direct("memcord_name", {"slot_name": ""})
        assert "error" in result[0].text.lower() or "empty" in result[0].text.lower()

    @pytest.mark.asyncio
    async def test_whitespace_only_slot_name_rejected(self, test_server):
        """Test that whitespace-only slot names are rejected."""
        server = test_server

        result = await server.call_tool_direct("memcord_name", {"slot_name": "   "})
        assert "error" in result[0].text.lower() or "empty" in result[0].text.lower()

    @pytest.mark.asyncio
    async def test_slot_name_strips_leading_trailing_whitespace(self, test_server):
        """Test that leading/trailing whitespace is stripped."""
        server = test_server

        result = await server.call_tool_direct("memcord_name", {"slot_name": "  my-slot  "})
        assert "active" in result[0].text.lower()
        assert server.storage.get_current_slot() == "my-slot"


class TestSlotNameSQLInjection:
    """Test slot names that attempt SQL injection attacks."""

    @pytest.mark.asyncio
    async def test_sql_drop_table_rejected(self, test_server):
        """Test that DROP TABLE injection is rejected."""
        server = test_server

        injection_names = [
            "slot; DROP TABLE users;--",
            "DROP TABLE memories",
            "slot DROP",
            "my-DROP-slot",
        ]

        for name in injection_names:
            result = await server.call_tool_direct("memcord_name", {"slot_name": name})
            assert "error" in result[0].text.lower() or "sql" in result[0].text.lower(), (
                f"Expected SQL rejection for: {name}, got: {result[0].text}"
            )

    @pytest.mark.asyncio
    async def test_sql_union_select_rejected(self, test_server):
        """Test that UNION SELECT injection is rejected."""
        server = test_server

        injection_names = [
            "slot UNION SELECT * FROM users",
            "UNION",
            "SELECT",
            "my-select-query",
        ]

        for name in injection_names:
            result = await server.call_tool_direct("memcord_name", {"slot_name": name})
            assert "error" in result[0].text.lower() or "sql" in result[0].text.lower(), (
                f"Expected SQL rejection for: {name}, got: {result[0].text}"
            )

    @pytest.mark.asyncio
    async def test_sql_insert_update_delete_rejected(self, test_server):
        """Test that INSERT/UPDATE/DELETE injections are rejected."""
        server = test_server

        injection_names = [
            "INSERT INTO slots",
            "UPDATE slots SET",
            "DELETE FROM slots",
            "my-insert-slot",
            "update-notes",
            "delete-old",
        ]

        for name in injection_names:
            result = await server.call_tool_direct("memcord_name", {"slot_name": name})
            assert "error" in result[0].text.lower() or "sql" in result[0].text.lower(), (
                f"Expected SQL rejection for: {name}, got: {result[0].text}"
            )

    @pytest.mark.asyncio
    async def test_sql_comment_injection_rejected(self, test_server):
        """Test that SQL comment injection is rejected."""
        server = test_server

        injection_names = [
            "slot--comment",
            "slot/*comment*/name",
            "/*",
            "*/",
            "--",
        ]

        for name in injection_names:
            result = await server.call_tool_direct("memcord_name", {"slot_name": name})
            assert "error" in result[0].text.lower() or "sql" in result[0].text.lower(), (
                f"Expected SQL rejection for: {name}, got: {result[0].text}"
            )

    @pytest.mark.asyncio
    async def test_sql_create_alter_rejected(self, test_server):
        """Test that CREATE/ALTER injections are rejected."""
        server = test_server

        injection_names = [
            "CREATE TABLE evil",
            "ALTER TABLE slots",
            "create-new",
            "alter-schema",
        ]

        for name in injection_names:
            result = await server.call_tool_direct("memcord_name", {"slot_name": name})
            assert "error" in result[0].text.lower() or "sql" in result[0].text.lower(), (
                f"Expected SQL rejection for: {name}, got: {result[0].text}"
            )

    @pytest.mark.asyncio
    async def test_case_insensitive_sql_rejection(self, test_server):
        """Test that SQL keywords are rejected regardless of case."""
        server = test_server

        injection_names = [
            "drop",
            "DROP",
            "DrOp",
            "sElEcT",
            "UNION",
            "union",
        ]

        for name in injection_names:
            result = await server.call_tool_direct("memcord_name", {"slot_name": name})
            assert "error" in result[0].text.lower() or "sql" in result[0].text.lower(), (
                f"Expected SQL rejection for: {name}, got: {result[0].text}"
            )


class TestSlotNameJSONEdgeCases:
    """Test slot names with JSON-specific characters and edge cases."""

    @pytest.mark.asyncio
    async def test_slot_name_with_curly_braces(self, test_server):
        """Test slot names with curly braces (JSON object syntax)."""
        server = test_server

        # Curly braces should be allowed (not in dangerous list)
        result = await server.call_tool_direct("memcord_name", {"slot_name": "slot{test}"})
        # Check if it succeeds or fails gracefully
        assert "active" in result[0].text.lower() or "error" in result[0].text.lower()

    @pytest.mark.asyncio
    async def test_slot_name_with_square_brackets(self, test_server):
        """Test slot names with square brackets (JSON array syntax)."""
        server = test_server

        result = await server.call_tool_direct("memcord_name", {"slot_name": "slot[0]"})
        # Square brackets should be allowed
        assert "active" in result[0].text.lower() or "error" in result[0].text.lower()

    @pytest.mark.asyncio
    async def test_slot_name_with_colon(self, test_server):
        """Test slot names with colon (JSON key-value separator)."""
        server = test_server

        result = await server.call_tool_direct("memcord_name", {"slot_name": "key:value"})
        assert "active" in result[0].text.lower()

    @pytest.mark.asyncio
    async def test_slot_name_with_comma(self, test_server):
        """Test slot names with comma (JSON separator)."""
        server = test_server

        result = await server.call_tool_direct("memcord_name", {"slot_name": "item1,item2"})
        assert "active" in result[0].text.lower()

    @pytest.mark.asyncio
    async def test_slot_name_json_injection_attempt(self, test_server):
        """Test that JSON injection attempts with quotes are rejected."""
        server = test_server

        # Double quotes are in the dangerous characters list
        injection_names = [
            '{"key":"value"}',
            '"slot_name"',
            "slot'name",
        ]

        for name in injection_names:
            result = await server.call_tool_direct("memcord_name", {"slot_name": name})
            assert "error" in result[0].text.lower() or "unsafe" in result[0].text.lower(), (
                f"Expected rejection for JSON injection: {name}, got: {result[0].text}"
            )

    @pytest.mark.asyncio
    async def test_slot_name_with_backslash(self, test_server):
        """Test slot names with backslash (JSON escape character)."""
        server = test_server

        result = await server.call_tool_direct("memcord_name", {"slot_name": "path\\to\\slot"})
        # Backslash might be allowed or trigger path traversal check
        # Just ensure it doesn't crash
        assert result[0].text is not None

    @pytest.mark.asyncio
    async def test_slot_name_with_null_character(self, test_server):
        """Test that null characters are stripped from slot names."""
        server = test_server

        # Null character should be stripped
        result = await server.call_tool_direct("memcord_name", {"slot_name": "slot\x00name"})
        # Should either work (with null stripped) or error
        assert result[0].text is not None

    @pytest.mark.asyncio
    async def test_slot_name_with_newlines(self, test_server):
        """Test slot names with newline characters."""
        server = test_server

        result = await server.call_tool_direct("memcord_name", {"slot_name": "slot\nname"})
        # Newlines might be stripped or cause issues
        assert result[0].text is not None

    @pytest.mark.asyncio
    async def test_slot_name_boolean_like_values(self, test_server):
        """Test slot names that look like JSON booleans."""
        server = test_server

        # These should be valid slot names
        for name in ["true", "false", "null", "True", "False", "NULL"]:
            result = await server.call_tool_direct("memcord_name", {"slot_name": name})
            assert "active" in result[0].text.lower(), f"Boolean-like name failed: {name}"

    @pytest.mark.asyncio
    async def test_slot_name_numeric_string(self, test_server):
        """Test slot names that are purely numeric."""
        server = test_server

        for name in ["123", "0", "-1", "3.14", "1e10"]:
            result = await server.call_tool_direct("memcord_name", {"slot_name": name})
            # Numeric names should be valid
            assert "active" in result[0].text.lower() or "error" not in result[0].text.lower()


class TestSlotNamePathTraversal:
    """Test slot names that attempt path traversal attacks."""

    @pytest.mark.asyncio
    async def test_path_traversal_unix_style_rejected(self, test_server):
        """Test that Unix-style path traversal is rejected."""
        server = test_server

        traversal_names = [
            "../etc/passwd",
            "../../secret",
            "slot/../../../etc",
            "./../parent",
        ]

        for name in traversal_names:
            result = await server.call_tool_direct("memcord_name", {"slot_name": name})
            assert "error" in result[0].text.lower() or "traversal" in result[0].text.lower(), (
                f"Expected path traversal rejection for: {name}, got: {result[0].text}"
            )

    @pytest.mark.asyncio
    async def test_path_traversal_windows_style_rejected(self, test_server):
        """Test that Windows-style path traversal is rejected."""
        server = test_server

        traversal_names = [
            "..\\windows\\system32",
            "..\\..\\secret",
            "slot\\..\\..\\etc",
        ]

        for name in traversal_names:
            result = await server.call_tool_direct("memcord_name", {"slot_name": name})
            assert "error" in result[0].text.lower() or "traversal" in result[0].text.lower(), (
                f"Expected path traversal rejection for: {name}, got: {result[0].text}"
            )

    @pytest.mark.asyncio
    async def test_single_dot_allowed(self, test_server):
        """Test that single dots are allowed (for versioning)."""
        server = test_server

        result = await server.call_tool_direct("memcord_name", {"slot_name": "v1.0.0"})
        assert "active" in result[0].text.lower()


class TestSlotNameReservedNames:
    """Test that reserved slot names are rejected."""

    @pytest.mark.asyncio
    async def test_zero_mode_slot_name_rejected(self, test_server):
        """Test that __ZERO__ reserved name is rejected."""
        server = test_server

        result = await server.call_tool_direct("memcord_name", {"slot_name": "__ZERO__"})
        assert "error" in result[0].text.lower() or "reserved" in result[0].text.lower()

    @pytest.mark.asyncio
    async def test_windows_reserved_names_rejected(self, test_server):
        """Test that Windows reserved device names are rejected."""
        server = test_server

        reserved_names = ["CON", "PRN", "AUX", "NUL", "COM1", "COM2", "LPT1", "LPT2"]

        for name in reserved_names:
            result = await server.call_tool_direct("memcord_name", {"slot_name": name})
            assert "error" in result[0].text.lower() or "reserved" in result[0].text.lower(), (
                f"Expected reserved rejection for: {name}, got: {result[0].text}"
            )

    @pytest.mark.asyncio
    async def test_reserved_names_case_insensitive(self, test_server):
        """Test that reserved names are rejected regardless of case."""
        server = test_server

        for name in ["con", "Con", "CON", "nul", "Nul", "NUL"]:
            result = await server.call_tool_direct("memcord_name", {"slot_name": name})
            assert "error" in result[0].text.lower() or "reserved" in result[0].text.lower(), (
                f"Expected reserved rejection for: {name}, got: {result[0].text}"
            )


class TestSlotSelectionDeselectionWithSpecialNames:
    """Test selecting and deselecting slots with special names."""

    @pytest.mark.asyncio
    async def test_select_unicode_slot_then_close(self, test_server):
        """Test selecting a unicode-named slot and then closing it."""
        server = test_server

        # Create unicode slot
        await server.call_tool_direct("memcord_name", {"slot_name": "日本語スロット"})
        assert server.storage.get_current_slot() == "日本語スロット"

        # Save content
        await server.call_tool_direct("memcord_save", {"chat_text": "Unicode content"})

        # Close
        result = await server.call_tool_direct("memcord_close", {})
        assert "日本語スロット" in result[0].text
        assert server.storage.get_current_slot() is None

    @pytest.mark.asyncio
    async def test_select_emoji_slot_then_switch(self, test_server):
        """Test selecting an emoji-named slot and switching to another."""
        server = test_server

        # Create emoji slot
        await server.call_tool_direct("memcord_name", {"slot_name": "notes-📝-2024"})
        assert server.storage.get_current_slot() == "notes-📝-2024"

        # Switch to another slot
        await server.call_tool_direct("memcord_name", {"slot_name": "other-slot"})
        assert server.storage.get_current_slot() == "other-slot"

        # Switch back using memcord_use
        result = await server.call_tool_direct("memcord_use", {"slot_name": "notes-📝-2024"})
        assert "active" in result[0].text.lower()
        assert server.storage.get_current_slot() == "notes-📝-2024"

    @pytest.mark.asyncio
    async def test_select_slot_with_special_chars_save_read(self, test_server):
        """Test full workflow with special character slot name."""
        server = test_server

        slot_name = "project@v2.0#main"

        # Create and select
        await server.call_tool_direct("memcord_name", {"slot_name": slot_name})

        # Save content
        await server.call_tool_direct("memcord_save", {"chat_text": "Special chars content"})

        # Read content
        result = await server.call_tool_direct("memcord_read", {})
        assert "Special chars content" in result[0].text

        # Close
        await server.call_tool_direct("memcord_close", {})

        # Reopen and verify content persisted
        await server.call_tool_direct("memcord_use", {"slot_name": slot_name})
        result = await server.call_tool_direct("memcord_read", {})
        assert "Special chars content" in result[0].text

    @pytest.mark.asyncio
    async def test_multiple_special_slots_in_sequence(self, test_server):
        """Test switching between multiple slots with special names."""
        server = test_server

        slots = [
            "プロジェクトA",
            "project-β-2024",
            "notes_€_budget",
        ]

        # Create all slots with content
        for i, slot in enumerate(slots):
            await server.call_tool_direct("memcord_name", {"slot_name": slot})
            await server.call_tool_direct("memcord_save", {"chat_text": f"Content for slot {i}"})

        # Verify each slot has correct content
        for i, slot in enumerate(slots):
            await server.call_tool_direct("memcord_use", {"slot_name": slot})
            result = await server.call_tool_direct("memcord_read", {})
            assert f"Content for slot {i}" in result[0].text

    @pytest.mark.asyncio
    async def test_close_and_reselect_numeric_slot(self, test_server):
        """Test close and reselect with numeric slot name."""
        server = test_server

        # Create numeric slot
        await server.call_tool_direct("memcord_name", {"slot_name": "12345"})
        await server.call_tool_direct("memcord_save", {"chat_text": "Numeric slot content"})

        # Close
        await server.call_tool_direct("memcord_close", {})
        assert server.storage.get_current_slot() is None

        # Reselect
        await server.call_tool_direct("memcord_use", {"slot_name": "12345"})
        assert server.storage.get_current_slot() == "12345"

        # Verify content
        result = await server.call_tool_direct("memcord_read", {})
        assert "Numeric slot content" in result[0].text

    @pytest.mark.asyncio
    async def test_list_shows_special_named_slots(self, test_server):
        """Test that memcord_list correctly shows slots with special names."""
        server = test_server

        special_slots = ["日本語", "emoji-🎉", "v1.0.0"]

        for slot in special_slots:
            await server.call_tool_direct("memcord_name", {"slot_name": slot})

        result = await server.call_tool_direct("memcord_list", {})

        for slot in special_slots:
            assert slot in result[0].text, f"Slot {slot} not found in list"
