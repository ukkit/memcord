"""Tests for memcord_auto_save tool and MEMCORD_DEFAULT_SLOT fallback in _resolve_slot.

Covers:
- memcord_auto_save: saves to default slot without prior setup
- memcord_auto_save: auto-creates slot on first use
- memcord_auto_save: respects MEMCORD_DEFAULT_SLOT env var
- memcord_auto_save: empty text returns error
- memcord_auto_save: zero mode returns warning (no persistence)
- _resolve_slot: MEMCORD_DEFAULT_SLOT as 4th fallback for memcord_read
- _resolve_slot: env var not used when explicit slot_name is provided
- _resolve_slot: env var not used when current slot is active
- Tool listing: memcord_auto_save appears in basic tools
"""

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
from mcp.types import TextContent

from memcord.server import ChatMemoryServer


@pytest.fixture
async def server():
    with tempfile.TemporaryDirectory() as tmp:
        s = ChatMemoryServer(
            memory_dir=tmp,
            shared_dir=str(Path(tmp) / "shared"),
            enable_advanced_tools=False,
        )
        yield s
        await s.storage.shutdown()


# ---------------------------------------------------------------------------
# memcord_auto_save handler
# ---------------------------------------------------------------------------


class TestHandleAutoSave:
    @pytest.mark.asyncio
    async def test_saves_to_default_slot_without_prior_setup(self, server):
        result = await server._handle_auto_save({"chat_text": "hello world"})

        assert isinstance(result, list)
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "Saved" in result[0].text
        assert "default" in result[0].text

    @pytest.mark.asyncio
    async def test_auto_creates_slot_on_first_use(self, server):
        existing = await server.storage._load_slot("default")
        assert existing is None

        await server._handle_auto_save({"chat_text": "first message"})

        slot = await server.storage.read_memory("default")
        assert slot is not None
        assert slot.entries[0].content == "first message"

    @pytest.mark.asyncio
    async def test_respects_memcord_default_slot_env_var(self, server):
        with patch.dict("os.environ", {"MEMCORD_DEFAULT_SLOT": "openclaw"}):
            result = await server._handle_auto_save({"chat_text": "gateway save"})

        assert "openclaw" in result[0].text
        slot = await server.storage.read_memory("openclaw")
        assert slot is not None
        assert slot.entries[0].content == "gateway save"

    @pytest.mark.asyncio
    async def test_empty_env_var_falls_back_to_default(self, server):
        with patch.dict("os.environ", {"MEMCORD_DEFAULT_SLOT": ""}):
            result = await server._handle_auto_save({"chat_text": "fallback test"})

        assert "default" in result[0].text

    @pytest.mark.asyncio
    async def test_empty_chat_text_returns_error(self, server):
        result = await server._handle_auto_save({"chat_text": "   "})

        assert "Error" in result[0].text or "cannot be empty" in result[0].text.lower()

    @pytest.mark.asyncio
    async def test_zero_mode_returns_warning(self, server):
        server.storage._state.activate_zero_mode()
        try:
            result = await server._handle_auto_save({"chat_text": "should not persist"})
        finally:
            server.storage._state.clear_current_slot()

        assert "Zero mode" in result[0].text or "zero mode" in result[0].text.lower()
        slot = await server.storage._load_slot("default")
        assert slot is None

    @pytest.mark.asyncio
    async def test_subsequent_saves_overwrite(self, server):
        """save_memory with type=manual_save replaces all entries — same as memcord_save."""
        await server._handle_auto_save({"chat_text": "first"})
        await server._handle_auto_save({"chat_text": "second"})

        slot = await server.storage.read_memory("default")
        assert len(slot.entries) == 1
        assert slot.entries[0].content == "second"

    @pytest.mark.asyncio
    async def test_result_contains_character_count(self, server):
        text = "hello openClaw"
        result = await server._handle_auto_save({"chat_text": text})

        assert str(len(text)) in result[0].text


# ---------------------------------------------------------------------------
# _resolve_slot MEMCORD_DEFAULT_SLOT fallback
# ---------------------------------------------------------------------------


class TestResolveSlotDefaultFallback:
    @pytest.mark.asyncio
    async def test_env_var_used_as_fourth_fallback(self, server):
        with patch.object(server, "_detect_project_slot", return_value=None):
            with patch.dict("os.environ", {"MEMCORD_DEFAULT_SLOT": "main"}):
                resolved = await server._resolve_slot({})

        assert resolved == "main"

    @pytest.mark.asyncio
    async def test_explicit_arg_takes_priority_over_env_var(self, server):
        with patch.dict("os.environ", {"MEMCORD_DEFAULT_SLOT": "main"}):
            resolved = await server._resolve_slot({"slot_name": "explicit"})

        assert resolved == "explicit"

    @pytest.mark.asyncio
    async def test_current_slot_takes_priority_over_env_var(self, server):
        server.storage._state.set_current_slot("active")
        try:
            with patch.dict("os.environ", {"MEMCORD_DEFAULT_SLOT": "main"}):
                resolved = await server._resolve_slot({})
        finally:
            server.storage._state.clear_current_slot()

        assert resolved == "active"

    @pytest.mark.asyncio
    async def test_env_var_not_set_returns_none(self, server):
        import os

        with patch.object(server, "_detect_project_slot", return_value=None):
            os.environ.pop("MEMCORD_DEFAULT_SLOT", None)
            resolved = await server._resolve_slot({})

        assert resolved is None

    @pytest.mark.asyncio
    async def test_memcord_read_uses_env_var_slot(self, server):
        await server._handle_auto_save({"chat_text": "some content"})

        with patch.dict("os.environ", {"MEMCORD_DEFAULT_SLOT": "default"}):
            result = await server._handle_readmem({})

        assert "some content" in result[0].text


# ---------------------------------------------------------------------------
# Tool listing
# ---------------------------------------------------------------------------


class TestAutoSaveToolListing:
    @pytest.mark.asyncio
    async def test_auto_save_in_basic_tools(self, server):
        tools = server._get_basic_tools()
        names = [t.name for t in tools]
        assert "memcord_auto_save" in names

    @pytest.mark.asyncio
    async def test_auto_save_has_no_slot_name_parameter(self, server):
        tools = server._get_basic_tools()
        auto_save = next(t for t in tools if t.name == "memcord_auto_save")
        props = auto_save.inputSchema.get("properties", {})
        assert "chat_text" in props
        assert "slot_name" not in props

    @pytest.mark.asyncio
    async def test_auto_save_requires_chat_text(self, server):
        tools = server._get_basic_tools()
        auto_save = next(t for t in tools if t.name == "memcord_auto_save")
        assert "chat_text" in auto_save.inputSchema.get("required", [])

    @pytest.mark.asyncio
    async def test_auto_save_has_additional_properties_false(self, server):
        tools = server._get_basic_tools()
        auto_save = next(t for t in tools if t.name == "memcord_auto_save")
        assert auto_save.inputSchema.get("additionalProperties") is False
