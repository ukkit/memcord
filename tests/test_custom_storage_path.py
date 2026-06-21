"""Tests for per-slot custom storage path.

Covers:
- SlotConfig.custom_storage_path field
- PathValidator.validate_custom_storage_dir
- StorageManager path resolution honoring a custom directory
- StorageManager.set_custom_storage_path (validate + migrate + persist)
- list_memory_slots discovering custom-path slots
"""

from pathlib import Path

import pytest

from memcord.models import SlotConfig
from memcord.security import PathValidator
from memcord.storage import StorageManager


def _make_storage(tmp_path: Path) -> StorageManager:
    return StorageManager(
        memory_dir=str(tmp_path / "slots"),
        shared_dir=str(tmp_path / "shared"),
        enable_caching=False,
        enable_efficiency=False,
        enable_memory_management=False,
    )


# ---------------------------------------------------------------------------
# SlotConfig model
# ---------------------------------------------------------------------------


class TestSlotConfigCustomStoragePath:
    def test_default_is_none(self):
        config = SlotConfig()
        assert config.custom_storage_path is None

    def test_accepts_absolute_path_string(self):
        config = SlotConfig(custom_storage_path="D:\\Dropbox\\shared")
        assert config.custom_storage_path == "D:\\Dropbox\\shared"

    def test_serialization_roundtrip(self):
        config = SlotConfig(custom_storage_path="D:\\Dropbox\\shared")
        dumped = config.model_dump_json()
        restored = SlotConfig.model_validate_json(dumped)
        assert restored.custom_storage_path == "D:\\Dropbox\\shared"


# ---------------------------------------------------------------------------
# PathValidator.validate_custom_storage_dir
# ---------------------------------------------------------------------------


class TestValidateCustomStorageDir:
    def test_empty_string_rejected(self):
        ok, reason = PathValidator.validate_custom_storage_dir("")
        assert ok is False
        assert reason

    def test_relative_path_rejected(self):
        ok, reason = PathValidator.validate_custom_storage_dir("relative/dir")
        assert ok is False
        assert reason

    def test_traversal_segment_rejected(self, tmp_path):
        ok, reason = PathValidator.validate_custom_storage_dir(str(tmp_path / ".." / "escape"))
        assert ok is False
        assert reason

    def test_reserved_windows_name_component_rejected(self, tmp_path):
        ok, reason = PathValidator.validate_custom_storage_dir(str(tmp_path / "CON"))
        assert ok is False
        assert reason

    def test_dangerous_char_in_component_rejected(self, tmp_path):
        ok, reason = PathValidator.validate_custom_storage_dir(str(tmp_path / "bad?name"))
        assert ok is False
        assert reason

    def test_existing_dir_accepted(self, tmp_path):
        ok, reason = PathValidator.validate_custom_storage_dir(str(tmp_path))
        assert ok is True
        assert reason is None

    def test_creatable_dir_accepted_and_created(self, tmp_path):
        target = tmp_path / "new_shared_folder"
        assert not target.exists()
        ok, reason = PathValidator.validate_custom_storage_dir(str(target))
        assert ok is True
        assert reason is None
        assert target.is_dir()

    def test_windows_drive_letter_path_accepted(self, tmp_path):
        # The drive-letter colon must not be treated as a dangerous character.
        ok, reason = PathValidator.validate_custom_storage_dir(str(tmp_path / "shared"))
        assert ok is True
        assert reason is None


# ---------------------------------------------------------------------------
# StorageManager: custom-path-aware path resolution
# ---------------------------------------------------------------------------


class TestStorageManagerCustomPath:
    async def test_get_slot_path_defaults_to_memory_dir(self, tmp_path):
        storage = _make_storage(tmp_path)
        path = await storage._get_slot_path("test")
        assert path == storage.memory_dir / "test.json"

    async def test_get_slot_path_honors_sidecar_custom_path(self, tmp_path):
        storage = _make_storage(tmp_path)
        external = tmp_path / "external"
        await storage.save_slot_config("test", SlotConfig(custom_storage_path=str(external)))

        path = await storage._get_slot_path("test")

        assert path == external / "test.json"

    async def test_save_and_load_roundtrip_at_custom_path(self, tmp_path):
        storage = _make_storage(tmp_path)
        external = tmp_path / "external"
        await storage.save_slot_config("test", SlotConfig(custom_storage_path=str(external)))

        await storage.save_memory("test", "hello from custom path")

        assert (external / "test.json").exists()
        assert not (storage.memory_dir / "test.json").exists()

        slot = await storage.read_memory("test")
        assert slot is not None
        assert slot.entries[-1].content == "hello from custom path"

    async def test_list_memory_slots_discovers_custom_path_slot(self, tmp_path):
        storage = _make_storage(tmp_path)
        external = tmp_path / "external"
        await storage.save_slot_config("remote_slot", SlotConfig(custom_storage_path=str(external)))
        await storage.save_memory("remote_slot", "remote content")
        await storage.save_memory("local_slot", "local content")

        slots = await storage.list_memory_slots()
        names = {s["name"] for s in slots}

        assert names == {"remote_slot", "local_slot"}

    async def test_list_memory_slots_skips_missing_custom_file(self, tmp_path):
        storage = _make_storage(tmp_path)
        external = tmp_path / "external"
        await storage.save_slot_config("ghost_slot", SlotConfig(custom_storage_path=str(external)))
        # No save_memory call -> no file exists at the custom path.

        slots = await storage.list_memory_slots()

        assert slots == []


# ---------------------------------------------------------------------------
# StorageManager.set_custom_storage_path
# ---------------------------------------------------------------------------


class TestSetCustomStoragePath:
    async def test_set_on_slot_with_no_data_just_writes_config(self, tmp_path):
        storage = _make_storage(tmp_path)
        external = tmp_path / "external"

        await storage.set_custom_storage_path("fresh_slot", str(external))

        config = await storage.load_slot_config("fresh_slot")
        assert config.custom_storage_path == str(external)
        assert not (external / "fresh_slot.json").exists()

    async def test_set_on_slot_with_existing_data_migrates_file(self, tmp_path):
        storage = _make_storage(tmp_path)
        external = tmp_path / "external"
        await storage.save_memory("data_slot", "original content")
        old_path = storage.memory_dir / "data_slot.json"
        assert old_path.exists()

        await storage.set_custom_storage_path("data_slot", str(external))

        assert not old_path.exists()
        assert (external / "data_slot.json").exists()
        slot = await storage.read_memory("data_slot")
        assert slot is not None
        assert slot.entries[-1].content == "original content"

    async def test_set_adopts_remote_file_when_no_local_original(self, tmp_path):
        storage = _make_storage(tmp_path)
        external = tmp_path / "external"
        # Simulate another device having already created the shared file.
        other_device_root = tmp_path / "other_device"
        other_device_root.mkdir()
        other_storage = _make_storage(other_device_root)
        await other_storage.save_slot_config("shared_slot", SlotConfig(custom_storage_path=str(external)))
        await other_storage.save_memory("shared_slot", "from other device")

        await storage.set_custom_storage_path("shared_slot", str(external))

        slot = await storage.read_memory("shared_slot")
        assert slot is not None
        assert slot.entries[-1].content == "from other device"

    async def test_set_raises_on_collision_with_both_local_and_remote_data(self, tmp_path):
        storage = _make_storage(tmp_path)
        external = tmp_path / "external"
        external.mkdir()
        (external / "collide_slot.json").write_text("not valid json but present", encoding="utf-8")
        await storage.save_memory("collide_slot", "local original")

        with pytest.raises(ValueError):
            await storage.set_custom_storage_path("collide_slot", str(external))

        # Nothing should have moved.
        assert (storage.memory_dir / "collide_slot.json").exists()
        config = await storage.load_slot_config("collide_slot")
        assert config.custom_storage_path is None

    async def test_clear_after_previously_set_migrates_back(self, tmp_path):
        storage = _make_storage(tmp_path)
        external = tmp_path / "external"
        await storage.save_memory("roundtrip_slot", "content")
        await storage.set_custom_storage_path("roundtrip_slot", str(external))

        await storage.set_custom_storage_path("roundtrip_slot", None)

        assert (storage.memory_dir / "roundtrip_slot.json").exists()
        assert not (external / "roundtrip_slot.json").exists()
        config = await storage.load_slot_config("roundtrip_slot")
        assert config.custom_storage_path is None

    async def test_invalid_path_raises_and_does_not_change_state(self, tmp_path):
        storage = _make_storage(tmp_path)
        await storage.save_memory("untouched_slot", "content")

        with pytest.raises(ValueError):
            await storage.set_custom_storage_path("untouched_slot", "relative/dir")

        assert (storage.memory_dir / "untouched_slot.json").exists()
        config = await storage.load_slot_config("untouched_slot")
        assert config.custom_storage_path is None
