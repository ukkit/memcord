"""Tests for per-slot custom storage path.

Covers:
- PathValidator.validate_custom_storage_dir
- StorageManager path resolution honoring the local _storage_links.json registry
- StorageManager.set_custom_storage_path (validate + migrate data + migrate config + persist)
- list_memory_slots discovering custom-path slots
- Settings (SlotConfig) traveling with the data once linked
- Legacy migration of the v4.1.0/v4.1.1 inline custom_storage_path field
"""

import json
from pathlib import Path

import pytest

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
# StorageManager: registry-aware path resolution
# ---------------------------------------------------------------------------


class TestStorageManagerCustomPath:
    async def test_get_slot_path_defaults_to_memory_dir(self, tmp_path):
        storage = _make_storage(tmp_path)
        path = await storage._get_slot_path("test")
        assert path == storage.memory_dir / "test.json"

    async def test_get_slot_path_honors_registry_link(self, tmp_path):
        storage = _make_storage(tmp_path)
        external = tmp_path / "external"
        await storage.set_custom_storage_path("test", str(external))

        path = await storage._get_slot_path("test")

        assert path == external / "test.json"

    async def test_save_and_load_roundtrip_at_custom_path(self, tmp_path):
        storage = _make_storage(tmp_path)
        external = tmp_path / "external"
        await storage.set_custom_storage_path("test", str(external))

        await storage.save_memory("test", "hello from custom path")

        assert (external / "test.json").exists()
        assert not (storage.memory_dir / "test.json").exists()

        slot = await storage.read_memory("test")
        assert slot is not None
        assert slot.entries[-1].content == "hello from custom path"

    async def test_list_memory_slots_discovers_custom_path_slot(self, tmp_path):
        storage = _make_storage(tmp_path)
        external = tmp_path / "external"
        await storage.set_custom_storage_path("remote_slot", str(external))
        await storage.save_memory("remote_slot", "remote content")
        await storage.save_memory("local_slot", "local content")

        slots = await storage.list_memory_slots()
        names = {s["name"] for s in slots}

        assert names == {"remote_slot", "local_slot"}

    async def test_list_memory_slots_skips_missing_custom_file(self, tmp_path):
        storage = _make_storage(tmp_path)
        external = tmp_path / "external"
        await storage.set_custom_storage_path("ghost_slot", str(external))
        # No save_memory call -> no file exists at the custom path.

        slots = await storage.list_memory_slots()

        assert slots == []


# ---------------------------------------------------------------------------
# StorageManager.set_custom_storage_path
# ---------------------------------------------------------------------------


class TestSetCustomStoragePath:
    async def test_set_on_slot_with_no_data_just_registers_link(self, tmp_path):
        storage = _make_storage(tmp_path)
        external = tmp_path / "external"

        await storage.set_custom_storage_path("fresh_slot", str(external))

        assert storage.get_custom_storage_path("fresh_slot") == str(external)
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

    async def test_set_moves_config_sidecar_with_data(self, tmp_path):
        storage = _make_storage(tmp_path)
        external = tmp_path / "external"
        await storage.save_memory("cfg_slot", "content")
        config = await storage.load_slot_config("cfg_slot")
        config.sumy_algorithm = "lsa"
        await storage.save_slot_config("cfg_slot", config)
        old_config_path = storage.memory_dir / "cfg_slot_config.json"
        assert old_config_path.exists()

        await storage.set_custom_storage_path("cfg_slot", str(external))

        assert not old_config_path.exists()
        assert (external / "cfg_slot_config.json").exists()
        reloaded = await storage.load_slot_config("cfg_slot")
        assert reloaded.sumy_algorithm == "lsa"

    async def test_set_adopts_remote_file_when_no_local_original(self, tmp_path):
        storage = _make_storage(tmp_path)
        external = tmp_path / "external"
        # Simulate another device having already created the shared file.
        other_device_root = tmp_path / "other_device"
        other_device_root.mkdir()
        other_storage = _make_storage(other_device_root)
        await other_storage.set_custom_storage_path("shared_slot", str(external))
        await other_storage.save_memory("shared_slot", "from other device")

        await storage.set_custom_storage_path("shared_slot", str(external))

        slot = await storage.read_memory("shared_slot")
        assert slot is not None
        assert slot.entries[-1].content == "from other device"

    async def test_set_does_not_overwrite_existing_remote_config(self, tmp_path):
        storage = _make_storage(tmp_path)
        external = tmp_path / "external"
        external.mkdir()
        (external / "guard_slot_config.json").write_text(
            '{"summarizer_backend": "sumy", "sumy_algorithm": "lsa"}', encoding="utf-8"
        )
        await storage.save_memory("guard_slot", "local content")
        local_config = await storage.load_slot_config("guard_slot")
        local_config.sumy_algorithm = "edmundson"
        await storage.save_slot_config("guard_slot", local_config)

        await storage.set_custom_storage_path("guard_slot", str(external))

        reloaded = await storage.load_slot_config("guard_slot")
        assert reloaded.sumy_algorithm == "lsa"

    async def test_two_devices_share_settings_via_linked_directory(self, tmp_path):
        external = tmp_path / "external"
        device_a_root = tmp_path / "device_a"
        device_b_root = tmp_path / "device_b"
        device_a_root.mkdir()
        device_b_root.mkdir()
        device_a = _make_storage(device_a_root)
        device_b = _make_storage(device_b_root)

        await device_a.set_custom_storage_path("shared_slot", str(external))
        await device_a.save_memory("shared_slot", "hello")
        await device_b.set_custom_storage_path("shared_slot", str(external))

        config_a = await device_a.load_slot_config("shared_slot")
        config_a.sumy_algorithm = "lsa"
        await device_a.save_slot_config("shared_slot", config_a)

        config_b = await device_b.load_slot_config("shared_slot")
        assert config_b.sumy_algorithm == "lsa"

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
        assert storage.get_custom_storage_path("collide_slot") is None

    async def test_clear_after_previously_set_migrates_back(self, tmp_path):
        storage = _make_storage(tmp_path)
        external = tmp_path / "external"
        await storage.save_memory("roundtrip_slot", "content")
        await storage.set_custom_storage_path("roundtrip_slot", str(external))

        await storage.set_custom_storage_path("roundtrip_slot", None)

        assert (storage.memory_dir / "roundtrip_slot.json").exists()
        assert not (external / "roundtrip_slot.json").exists()
        assert storage.get_custom_storage_path("roundtrip_slot") is None

    async def test_invalid_path_raises_and_does_not_change_state(self, tmp_path):
        storage = _make_storage(tmp_path)
        await storage.save_memory("untouched_slot", "content")

        with pytest.raises(ValueError):
            await storage.set_custom_storage_path("untouched_slot", "relative/dir")

        assert (storage.memory_dir / "untouched_slot.json").exists()
        assert storage.get_custom_storage_path("untouched_slot") is None


# ---------------------------------------------------------------------------
# Legacy migration: inline custom_storage_path field from v4.1.0/v4.1.1
# ---------------------------------------------------------------------------


class TestLegacyCustomStoragePathMigration:
    async def test_legacy_inline_field_migrates_to_registry(self, tmp_path):
        storage = _make_storage(tmp_path)
        external = tmp_path / "external"
        legacy_config_path = storage.memory_dir / "legacy_slot_config.json"
        legacy_config_path.write_text(
            json.dumps({"summarizer_backend": "nltk", "custom_storage_path": str(external)}),
            encoding="utf-8",
        )

        config = await storage.load_slot_config("legacy_slot")

        assert config.summarizer_backend == "nltk"
        assert storage.get_custom_storage_path("legacy_slot") == str(external)
        assert not legacy_config_path.exists()
        assert (external / "legacy_slot_config.json").exists()

    async def test_legacy_migration_failure_leaves_registry_and_local_sidecar_intact(self, tmp_path, monkeypatch):
        storage = _make_storage(tmp_path)
        external = tmp_path / "external"
        legacy_config_path = storage.memory_dir / "legacy_slot_config.json"
        legacy_config_path.write_text(
            json.dumps({"summarizer_backend": "nltk", "custom_storage_path": str(external)}),
            encoding="utf-8",
        )

        # Simulate the relocation write failing, e.g. an unmounted/unwritable
        # custom directory, by making mkdir raise for the target directory.
        original_mkdir = Path.mkdir

        def failing_mkdir(self, *args, **kwargs):
            if self == external:
                raise OSError("simulated unavailable custom storage directory")
            return original_mkdir(self, *args, **kwargs)

        monkeypatch.setattr(Path, "mkdir", failing_mkdir)

        config = await storage.load_slot_config("legacy_slot")

        # The migration must not have half-completed: no registry entry,
        # and the original local sidecar must still exist with the user's
        # original settings intact.
        assert config.summarizer_backend == "nltk"
        assert storage.get_custom_storage_path("legacy_slot") is None
        assert legacy_config_path.exists()
        assert not (external / "legacy_slot_config.json").exists()

        monkeypatch.undo()

        # A subsequent load should simply retry the migration rather than
        # silently losing the data.
        config_retry = await storage.load_slot_config("legacy_slot")
        assert config_retry.summarizer_backend == "nltk"
        assert storage.get_custom_storage_path("legacy_slot") == str(external)
        assert not legacy_config_path.exists()
        assert (external / "legacy_slot_config.json").exists()
