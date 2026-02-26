"""Tests for per-slot config (SlotConfig) and the memcord_configure MCP tool."""

import json
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from memcord.models import SlotConfig
from memcord.storage import StorageManager


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_slot_json(memory_dir: Path, slot_name: str) -> Path:
    """Write a minimal but valid slot JSON file to simulate an existing slot."""
    slot_path = memory_dir / f"{slot_name}.json"
    slot_data = {
        "slot_name": slot_name,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "entries": [],
        "current_slot": False,
        "tags": [],
        "group_path": None,
        "description": None,
        "priority": 0,
        "is_archived": False,
        "archived_at": None,
        "archive_reason": None,
    }
    slot_path.write_text(json.dumps(slot_data, indent=2), encoding="utf-8")
    return slot_path


# ---------------------------------------------------------------------------
# SlotConfig model
# ---------------------------------------------------------------------------


class TestSlotConfigModel:
    def test_defaults(self):
        c = SlotConfig()
        assert c.summarizer_backend == "sumy"
        assert c.sumy_algorithm == "lexrank"
        assert c.default_compression_ratio == pytest.approx(0.15)

    def test_custom_values(self):
        c = SlotConfig(summarizer_backend="nltk", sumy_algorithm="lsa", default_compression_ratio=0.2)
        assert c.summarizer_backend == "nltk"
        assert c.sumy_algorithm == "lsa"
        assert c.default_compression_ratio == pytest.approx(0.2)

    def test_compression_ratio_bounds(self):
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            SlotConfig(default_compression_ratio=0.0)
        with pytest.raises(ValidationError):
            SlotConfig(default_compression_ratio=1.0)

    def test_serialization_roundtrip(self):
        c = SlotConfig(summarizer_backend="semantic", semantic_model="all-MiniLM-L6-v2")
        data = json.loads(c.model_dump_json())
        c2 = SlotConfig(**data)
        assert c2.summarizer_backend == "semantic"
        assert c2.semantic_model == "all-MiniLM-L6-v2"


# ---------------------------------------------------------------------------
# StorageManager.load_slot_config / save_slot_config
# ---------------------------------------------------------------------------


class TestSlotConfigStorage:
    @pytest.mark.asyncio
    async def test_new_slot_gets_sumy_default(self, clean_storage_manager):
        """A slot with no .json file → auto-create config with sumy."""
        storage = clean_storage_manager
        config = await storage.load_slot_config("brand_new_slot")
        assert config.summarizer_backend == "sumy"

    @pytest.mark.asyncio
    async def test_existing_slot_gets_nltk_default(self, clean_storage_manager):
        """An existing slot → auto-create config with nltk (preserve behavior)."""
        storage = clean_storage_manager
        # Create the slot first
        await storage.save_memory("existing_slot", "some content")
        config = await storage.load_slot_config("existing_slot")
        assert config.summarizer_backend == "nltk"

    @pytest.mark.asyncio
    async def test_config_persisted_and_reloaded(self, clean_storage_manager):
        storage = clean_storage_manager
        config = SlotConfig(summarizer_backend="semantic", default_compression_ratio=0.25)
        await storage.save_slot_config("myslot", config)

        loaded = await storage.load_slot_config("myslot")
        assert loaded.summarizer_backend == "semantic"
        assert loaded.default_compression_ratio == pytest.approx(0.25)

    @pytest.mark.asyncio
    async def test_config_sidecar_path(self, clean_storage_manager):
        storage = clean_storage_manager
        await storage.load_slot_config("alpha")
        expected = storage.memory_dir / "alpha_config.json"
        assert expected.exists()

    @pytest.mark.asyncio
    async def test_corrupt_config_resets_gracefully(self, clean_storage_manager):
        """Corrupt sidecar JSON → reset to defaults without crashing."""
        storage = clean_storage_manager
        # Write corrupt JSON
        bad_path = storage.memory_dir / "bad_config.json"
        bad_path.write_text("{not valid json", encoding="utf-8")
        # Should not raise — falls back to defaults
        config = await storage.load_slot_config("bad")
        assert isinstance(config, SlotConfig)

    @pytest.mark.asyncio
    async def test_load_idempotent(self, clean_storage_manager):
        """Loading twice returns the same persisted config."""
        storage = clean_storage_manager
        c1 = await storage.load_slot_config("stable_slot")
        c2 = await storage.load_slot_config("stable_slot")
        assert c1.summarizer_backend == c2.summarizer_backend


# ---------------------------------------------------------------------------
# Filesystem-level auto-creation tests
# — pre-seed memory_slots/ on disk, then verify _config.json content
# ---------------------------------------------------------------------------


class TestConfigAutoCreationOnDisk:
    """Verify _config.json files are created on disk with the correct backend
    depending on whether the slot .json already exists."""

    @pytest.mark.asyncio
    async def test_existing_slot_file_creates_nltk_config_on_disk(self, tmp_path):
        """If {slot}.json exists before load_slot_config is called, the sidecar
        should be written with summarizer_backend='nltk'."""
        memory_dir = tmp_path / "slots"
        memory_dir.mkdir()
        _write_slot_json(memory_dir, "legacy_slot")

        storage = StorageManager(
            memory_dir=str(memory_dir),
            shared_dir=str(tmp_path / "shared"),
            enable_caching=False,
            enable_efficiency=False,
            enable_memory_management=False,
        )

        config = await storage.load_slot_config("legacy_slot")

        # In-memory value
        assert config.summarizer_backend == "nltk"

        # On-disk sidecar exists and has the right content
        config_path = memory_dir / "legacy_slot_config.json"
        assert config_path.exists(), "sidecar _config.json was not written to disk"
        disk_data = json.loads(config_path.read_text(encoding="utf-8"))
        assert disk_data["summarizer_backend"] == "nltk"

    @pytest.mark.asyncio
    async def test_new_slot_creates_sumy_config_on_disk(self, tmp_path):
        """If {slot}.json does NOT exist, the sidecar should be written with
        summarizer_backend='sumy'."""
        memory_dir = tmp_path / "slots"
        memory_dir.mkdir()

        storage = StorageManager(
            memory_dir=str(memory_dir),
            shared_dir=str(tmp_path / "shared"),
            enable_caching=False,
            enable_efficiency=False,
            enable_memory_management=False,
        )

        config = await storage.load_slot_config("fresh_slot")

        assert config.summarizer_backend == "sumy"

        config_path = memory_dir / "fresh_slot_config.json"
        assert config_path.exists(), "sidecar _config.json was not written to disk"
        disk_data = json.loads(config_path.read_text(encoding="utf-8"))
        assert disk_data["summarizer_backend"] == "sumy"

    @pytest.mark.asyncio
    async def test_multiple_existing_slots_each_get_nltk_config(self, tmp_path):
        """Multiple pre-existing slots each get their own sidecar with nltk."""
        memory_dir = tmp_path / "slots"
        memory_dir.mkdir()
        slot_names = ["project_a", "project_b", "project_c"]
        for name in slot_names:
            _write_slot_json(memory_dir, name)

        storage = StorageManager(
            memory_dir=str(memory_dir),
            shared_dir=str(tmp_path / "shared"),
            enable_caching=False,
            enable_efficiency=False,
            enable_memory_management=False,
        )

        for name in slot_names:
            config = await storage.load_slot_config(name)
            assert config.summarizer_backend == "nltk", f"{name} should default to nltk"
            config_path = memory_dir / f"{name}_config.json"
            assert config_path.exists(), f"sidecar missing for {name}"
            disk_data = json.loads(config_path.read_text(encoding="utf-8"))
            assert disk_data["summarizer_backend"] == "nltk"

    @pytest.mark.asyncio
    async def test_mixed_existing_and_new_slots(self, tmp_path):
        """Existing slot → nltk; new slot → sumy. Both on the same storage dir."""
        memory_dir = tmp_path / "slots"
        memory_dir.mkdir()
        _write_slot_json(memory_dir, "old_slot")

        storage = StorageManager(
            memory_dir=str(memory_dir),
            shared_dir=str(tmp_path / "shared"),
            enable_caching=False,
            enable_efficiency=False,
            enable_memory_management=False,
        )

        old_config = await storage.load_slot_config("old_slot")
        new_config = await storage.load_slot_config("new_slot")

        assert old_config.summarizer_backend == "nltk"
        assert new_config.summarizer_backend == "sumy"

        assert (memory_dir / "old_slot_config.json").exists()
        assert (memory_dir / "new_slot_config.json").exists()

    @pytest.mark.asyncio
    async def test_sidecar_not_recreated_if_already_exists(self, tmp_path):
        """If a sidecar already exists with custom settings, load_slot_config
        should NOT overwrite it."""
        memory_dir = tmp_path / "slots"
        memory_dir.mkdir()
        _write_slot_json(memory_dir, "configured_slot")

        # Write a custom sidecar ahead of time
        custom_config = SlotConfig(summarizer_backend="semantic", sumy_algorithm="lsa")
        config_path = memory_dir / "configured_slot_config.json"
        config_path.write_text(custom_config.model_dump_json(indent=2), encoding="utf-8")

        storage = StorageManager(
            memory_dir=str(memory_dir),
            shared_dir=str(tmp_path / "shared"),
            enable_caching=False,
            enable_efficiency=False,
            enable_memory_management=False,
        )

        loaded = await storage.load_slot_config("configured_slot")
        assert loaded.summarizer_backend == "semantic"
        assert loaded.sumy_algorithm == "lsa"

    @pytest.mark.asyncio
    async def test_save_progress_creates_sidecar_for_existing_slot(self, tmp_path):
        """Calling save_progress on an existing slot (via ChatMemoryServer) should
        trigger sidecar creation with summarizer_backend='nltk'."""
        from memcord.server import ChatMemoryServer

        memory_dir = tmp_path / "slots"
        memory_dir.mkdir()
        _write_slot_json(memory_dir, "legacy_work")

        server = ChatMemoryServer(
            memory_dir=str(memory_dir),
            shared_dir=str(tmp_path / "shared"),
        )
        server.storage._state.set_current_slot("legacy_work")

        long_text = " ".join([f"Sentence {i} about the project architecture and decisions." for i in range(15)])
        await server._handle_saveprogress({"chat_text": long_text})

        config_path = memory_dir / "legacy_work_config.json"
        assert config_path.exists(), "_config.json not created by save_progress"
        disk_data = json.loads(config_path.read_text(encoding="utf-8"))
        assert disk_data["summarizer_backend"] == "nltk"

    @pytest.mark.asyncio
    async def test_save_progress_creates_sidecar_for_new_slot(self, tmp_path):
        """Calling save_progress on a brand-new slot should create sidecar
        with summarizer_backend='sumy'."""
        from memcord.server import ChatMemoryServer

        memory_dir = tmp_path / "slots"
        memory_dir.mkdir()
        # No pre-existing slot file

        server = ChatMemoryServer(
            memory_dir=str(memory_dir),
            shared_dir=str(tmp_path / "shared"),
        )
        server.storage._state.set_current_slot("brand_new_work")

        long_text = " ".join([f"Sentence {i} about the project architecture and decisions." for i in range(15)])
        await server._handle_saveprogress({"chat_text": long_text})

        config_path = memory_dir / "brand_new_work_config.json"
        assert config_path.exists(), "_config.json not created by save_progress"
        disk_data = json.loads(config_path.read_text(encoding="utf-8"))
        assert disk_data["summarizer_backend"] == "sumy"


# ---------------------------------------------------------------------------
# add_summary_entry with metadata
# ---------------------------------------------------------------------------


class TestAddSummaryEntryMetadata:
    @pytest.mark.asyncio
    async def test_metadata_stored(self, clean_storage_manager):
        storage = clean_storage_manager
        meta = {"summarizer": "sumy", "algorithm": "lexrank"}
        entry = await storage.add_summary_entry("slot1", "original text " * 20, "short summary.", metadata=meta)
        assert entry.metadata["summarizer"] == "sumy"
        assert entry.metadata["algorithm"] == "lexrank"

    @pytest.mark.asyncio
    async def test_no_metadata_defaults_to_empty(self, clean_storage_manager):
        storage = clean_storage_manager
        entry = await storage.add_summary_entry("slot2", "original text " * 20, "short summary.")
        assert entry.metadata == {}

    @pytest.mark.asyncio
    async def test_metadata_persisted(self, clean_storage_manager):
        storage = clean_storage_manager
        meta = {"summarizer": "nltk"}
        await storage.add_summary_entry("persist_slot", "long text " * 20, "summary text.", metadata=meta)

        slot = await storage.read_memory("persist_slot")
        assert slot is not None
        summary_entry = next(e for e in slot.entries if e.type == "auto_summary")
        assert summary_entry.metadata["summarizer"] == "nltk"


# ---------------------------------------------------------------------------
# memcord_configure MCP handler
# ---------------------------------------------------------------------------


@pytest.fixture
async def server_with_temp_dir():
    """ChatMemoryServer instance with isolated temp storage."""
    from memcord.server import ChatMemoryServer

    with tempfile.TemporaryDirectory() as tmp:
        server = ChatMemoryServer(
            memory_dir=tmp,
            shared_dir=str(Path(tmp) / "shared"),
        )
        server.storage._state.set_current_slot("testslot")
        yield server


class TestConfigureToolGet:
    @pytest.mark.asyncio
    async def test_get_returns_config_text(self, server_with_temp_dir):
        server = server_with_temp_dir
        result = await server._handle_configure({"action": "get"})
        text = result[0].text
        assert "testslot" in text
        assert "summarizer_backend" in text

    @pytest.mark.asyncio
    async def test_get_no_slot_returns_error(self, server_with_temp_dir):
        server = server_with_temp_dir
        server.storage._state.current_slot = None
        # Patch _detect_project_slot to avoid picking up any .memcord in the project root
        with patch.object(server, "_detect_project_slot", new=AsyncMock(return_value=None)):
            result = await server._handle_configure({"action": "get"})
        assert "Error" in result[0].text


class TestConfigureToolSet:
    @pytest.mark.asyncio
    async def test_set_summarizer_backend(self, server_with_temp_dir):
        server = server_with_temp_dir
        result = await server._handle_configure(
            {"action": "set", "key": "summarizer_backend", "value": "semantic"}
        )
        assert "semantic" in result[0].text
        # Verify persisted
        config = await server.storage.load_slot_config("testslot")
        assert config.summarizer_backend == "semantic"

    @pytest.mark.asyncio
    async def test_set_compression_ratio(self, server_with_temp_dir):
        server = server_with_temp_dir
        result = await server._handle_configure(
            {"action": "set", "key": "default_compression_ratio", "value": "0.25"}
        )
        assert "0.25" in result[0].text
        config = await server.storage.load_slot_config("testslot")
        assert config.default_compression_ratio == pytest.approx(0.25)

    @pytest.mark.asyncio
    async def test_set_unknown_key_returns_error(self, server_with_temp_dir):
        server = server_with_temp_dir
        result = await server._handle_configure(
            {"action": "set", "key": "nonexistent_key", "value": "foo"}
        )
        assert "Error" in result[0].text

    @pytest.mark.asyncio
    async def test_set_missing_key_returns_error(self, server_with_temp_dir):
        server = server_with_temp_dir
        result = await server._handle_configure({"action": "set", "value": "foo"})
        assert "Error" in result[0].text

    @pytest.mark.asyncio
    async def test_set_sumy_algorithm(self, server_with_temp_dir):
        server = server_with_temp_dir
        await server._handle_configure({"action": "set", "key": "sumy_algorithm", "value": "lsa"})
        config = await server.storage.load_slot_config("testslot")
        assert config.sumy_algorithm == "lsa"


class TestConfigureToolReset:
    @pytest.mark.asyncio
    async def test_reset_on_new_slot_uses_sumy(self, server_with_temp_dir):
        server = server_with_temp_dir
        # testslot has no .json file → reset should default to sumy
        result = await server._handle_configure({"action": "reset"})
        assert "sumy" in result[0].text
        config = await server.storage.load_slot_config("testslot")
        assert config.summarizer_backend == "sumy"

    @pytest.mark.asyncio
    async def test_reset_on_existing_slot_uses_nltk(self, server_with_temp_dir):
        server = server_with_temp_dir
        # Create the slot file first
        await server.storage.save_memory("testslot", "some content")
        result = await server._handle_configure({"action": "reset"})
        assert "nltk" in result[0].text
        config = await server.storage.load_slot_config("testslot")
        assert config.summarizer_backend == "nltk"


class TestConfigureToolInvalidAction:
    @pytest.mark.asyncio
    async def test_unknown_action_returns_error(self, server_with_temp_dir):
        server = server_with_temp_dir
        result = await server._handle_configure({"action": "explode"})
        assert "Error" in result[0].text


# ---------------------------------------------------------------------------
# Integration: save_progress uses per-slot config
# ---------------------------------------------------------------------------


class TestSaveProgressUsesSlotConfig:
    @pytest.mark.asyncio
    async def test_save_progress_stores_summarizer_in_metadata(self, server_with_temp_dir):
        """save_progress should store which backend was used in entry.metadata."""
        server = server_with_temp_dir
        # Force nltk backend
        await server._handle_configure({"action": "set", "key": "summarizer_backend", "value": "nltk"})

        long_text = (
            "We decided on the architecture during the planning session. "
            "The backend will be built with FastAPI and PostgreSQL. "
            "Frontend uses React with TypeScript for type safety. "
            "Authentication is handled by JWT tokens with refresh logic. "
            "Deployment targets AWS ECS with auto-scaling groups. "
            "CI/CD runs on GitHub Actions with test and lint gates. "
            "Code reviews are required before any merge to main. "
            "Performance budgets are enforced in the CI pipeline."
        )
        result = await server._handle_saveprogress({"chat_text": long_text})
        assert result[0].text  # non-empty response

        # Check metadata in stored entry
        slot = await server.storage.read_memory("testslot")
        assert slot is not None
        summary_entries = [e for e in slot.entries if e.type == "auto_summary"]
        assert summary_entries
        assert summary_entries[-1].metadata.get("summarizer") == "nltk"

    @pytest.mark.asyncio
    async def test_save_progress_respects_compression_ratio_override(self, server_with_temp_dir):
        """Explicit compression_ratio argument overrides config default."""
        server = server_with_temp_dir
        long_text = " ".join([f"Sentence number {i} about important project decisions." for i in range(20)])
        result = await server._handle_saveprogress({"chat_text": long_text, "compression_ratio": 0.4})
        assert result[0].text  # non-empty response

    @pytest.mark.asyncio
    async def test_configure_tool_in_tool_list(self, server_with_temp_dir):
        """memcord_configure must appear in the basic tools list."""
        server = server_with_temp_dir
        tools = await server.list_tools_direct()
        tool_names = [t.name for t in tools]
        assert "memcord_configure" in tool_names
