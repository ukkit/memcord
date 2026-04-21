"""Tests for MCP protocol compliance features added in spec 2025-03-26 / 2025-11-25."""

import tempfile
from pathlib import Path

import pytest

from memcord.server import ChatMemoryServer


@pytest.fixture
async def server_with_slots():
    """Server pre-populated with two memory slots for resource/completion tests."""
    with tempfile.TemporaryDirectory() as temp_dir:
        server = ChatMemoryServer(
            memory_dir=temp_dir,
            shared_dir=str(Path(temp_dir) / "shared"),
            enable_advanced_tools=True,
        )
        # Create two slots with content
        await server.storage.create_or_get_slot("alpha")
        await server.storage.save_memory("alpha", "Alpha slot content for testing")
        await server.storage.create_or_get_slot("beta")
        await server.storage.save_memory("beta", "Beta slot content for testing")
        yield server
        await server.storage.shutdown()


class TestResourceMetadata:
    """Tests for enriched Resource metadata (spec 2025-03-26)."""

    async def test_resources_include_description(self, server_with_slots):
        resources = await server_with_slots.list_resources_direct()
        for res in resources:
            assert res.description is not None, f"Resource {res.uri} missing description"
            assert len(res.description) > 0

    async def test_resource_description_contains_entry_count(self, server_with_slots):
        resources = await server_with_slots.list_resources_direct()
        md_resources = [r for r in resources if str(r.uri).endswith(".md")]
        assert len(md_resources) >= 2
        for res in md_resources:
            assert res.description is not None
            # e.g. "alpha — 1 entry, 31 chars"
            assert "entr" in res.description.lower() or "char" in res.description.lower()

    async def test_resource_size_is_set(self, server_with_slots):
        resources = await server_with_slots.list_resources_direct()
        md_resources = [r for r in resources if str(r.uri).endswith(".md")]
        for res in md_resources:
            assert res.size is not None, f"Resource {res.uri} missing size"
            assert res.size > 0


class TestResourceTemplates:
    """Tests for ResourceTemplate registration (enables completions)."""

    async def test_list_resource_templates_returns_templates(self, server_with_slots):
        templates = await server_with_slots.list_resource_templates_direct()
        assert len(templates) >= 3  # one per format: md, txt, json

    async def test_resource_template_uris_cover_all_formats(self, server_with_slots):
        templates = await server_with_slots.list_resource_templates_direct()
        uris = {str(t.uriTemplate) for t in templates}
        assert "memory://{slot_name}.md" in uris
        assert "memory://{slot_name}.txt" in uris
        assert "memory://{slot_name}.json" in uris

    async def test_resource_templates_have_descriptions(self, server_with_slots):
        templates = await server_with_slots.list_resource_templates_direct()
        for tmpl in templates:
            assert tmpl.description is not None
            assert len(tmpl.description) > 0


class TestProgressNotifications:
    """Tests for progress notification message field (spec 2025-03-26)."""

    async def test_save_progress_emits_progress_messages(self, server_with_slots):
        """_handle_saveprogress must call send_progress_notification with a message."""
        from unittest.mock import AsyncMock, MagicMock

        from mcp.server.lowlevel.server import request_ctx

        mock_session = AsyncMock()
        mock_meta = MagicMock()
        mock_meta.progressToken = "tok-123"
        mock_ctx = MagicMock()
        mock_ctx.meta = mock_meta
        mock_ctx.session = mock_session

        await server_with_slots.storage.create_or_get_slot("prog-test")

        token = request_ctx.set(mock_ctx)
        try:
            await server_with_slots._handle_saveprogress({
                "chat_text": "Hello world " * 50,
                "slot_name": "prog-test",
            })
        finally:
            request_ctx.reset(token)

        assert mock_session.send_progress_notification.called, (
            "_handle_saveprogress should call send_progress_notification"
        )
        call_kwargs = mock_session.send_progress_notification.call_args
        message = (
            call_kwargs.kwargs.get("message")
            or (call_kwargs.args[3] if len(call_kwargs.args) > 3 else None)
        )
        assert message is not None and len(message) > 0, "Progress notification must include a message"

    async def test_progress_skipped_without_progress_token(self, server_with_slots):
        """If no progressToken in request meta, no notification should be sent."""
        from unittest.mock import AsyncMock, MagicMock

        from mcp.server.lowlevel.server import request_ctx

        mock_session = AsyncMock()
        mock_meta = MagicMock()
        mock_meta.progressToken = None
        mock_ctx = MagicMock()
        mock_ctx.meta = mock_meta
        mock_ctx.session = mock_session

        await server_with_slots.storage.create_or_get_slot("no-token-test")

        token = request_ctx.set(mock_ctx)
        try:
            await server_with_slots._handle_saveprogress({
                "chat_text": "Hello world " * 50,
                "slot_name": "no-token-test",
            })
        finally:
            request_ctx.reset(token)

        mock_session.send_progress_notification.assert_not_called()

    async def test_progress_skipped_outside_request_context(self, server_with_slots):
        """Calling handler outside MCP context (LookupError on request_context) must not raise."""
        await server_with_slots.storage.create_or_get_slot("ctx-test")
        # No patching — request_context will raise LookupError in test environment
        result = await server_with_slots._handle_saveprogress({
            "chat_text": "Hello world " * 50,
            "slot_name": "ctx-test",
        })
        # Should return a result normally, not raise
        assert result is not None
        assert len(result) > 0


class TestCompletions:
    """Tests for the completions capability (spec 2025-03-26)."""

    async def test_server_advertises_completions_capability(self, server_with_slots):
        from mcp.server.lowlevel.server import NotificationOptions
        caps = server_with_slots.app.get_capabilities(
            notification_options=NotificationOptions(),
            experimental_capabilities={},
        )
        assert caps.completions is not None, "Server must advertise completions capability"

    async def test_slot_name_completion_returns_existing_slots(self, server_with_slots):
        from mcp.types import (
            Completion,
            CompletionArgument,
            ResourceTemplateReference,
        )
        ref = ResourceTemplateReference(type="ref/resource", uri="memory://{slot_name}.md")
        arg = CompletionArgument(name="slot_name", value="")
        result = await server_with_slots._handle_completion(ref, arg, None)
        assert result is not None
        assert isinstance(result, Completion)
        assert len(result.values) >= 2  # "alpha" and "beta" were created
        assert "alpha" in result.values
        assert "beta" in result.values

    async def test_slot_name_completion_filters_by_prefix(self, server_with_slots):
        from mcp.types import (
            CompletionArgument,
            ResourceTemplateReference,
        )
        ref = ResourceTemplateReference(type="ref/resource", uri="memory://{slot_name}.md")
        arg = CompletionArgument(name="slot_name", value="al")
        result = await server_with_slots._handle_completion(ref, arg, None)
        assert result is not None
        assert "alpha" in result.values
        assert "beta" not in result.values

    async def test_non_slot_name_argument_returns_empty(self, server_with_slots):
        from mcp.types import (
            CompletionArgument,
            ResourceTemplateReference,
        )
        ref = ResourceTemplateReference(type="ref/resource", uri="memory://{slot_name}.md")
        arg = CompletionArgument(name="format", value="")
        result = await server_with_slots._handle_completion(ref, arg, None)
        assert result is None or result.values == []

    async def test_prompt_reference_returns_none(self, server_with_slots):
        from mcp.types import CompletionArgument, PromptReference
        ref = PromptReference(type="ref/prompt", name="unknown_prompt")
        arg = CompletionArgument(name="slot_name", value="")
        result = await server_with_slots._handle_completion(ref, arg, None)
        assert result is None or result.values == []
