"""Tests for the local storage-links registry (_storage_links.json)."""

from pathlib import Path

from memcord.storage import StorageManager


def _make_storage(tmp_path: Path) -> StorageManager:
    return StorageManager(
        memory_dir=str(tmp_path / "slots"),
        shared_dir=str(tmp_path / "shared"),
        enable_caching=False,
        enable_efficiency=False,
        enable_memory_management=False,
    )


class TestStorageLinksRegistry:
    def test_load_returns_empty_dict_when_file_absent(self, tmp_path):
        storage = _make_storage(tmp_path)
        assert storage._load_storage_links() == {}

    def test_save_then_load_roundtrip(self, tmp_path):
        storage = _make_storage(tmp_path)
        storage._save_storage_links({"slot_a": "D:\\Dropbox\\slots"})
        assert storage._load_storage_links() == {"slot_a": "D:\\Dropbox\\slots"}

    def test_save_writes_file_at_memory_dir_root(self, tmp_path):
        storage = _make_storage(tmp_path)
        storage._save_storage_links({"slot_a": "D:\\Dropbox\\slots"})
        assert (storage.memory_dir / "_storage_links.json").exists()

    def test_save_empty_dict_removes_file(self, tmp_path):
        storage = _make_storage(tmp_path)
        storage._save_storage_links({"slot_a": "D:\\Dropbox\\slots"})
        storage._save_storage_links({})
        assert not (storage.memory_dir / "_storage_links.json").exists()

    def test_load_returns_empty_dict_on_corrupt_file(self, tmp_path):
        storage = _make_storage(tmp_path)
        (storage.memory_dir / "_storage_links.json").write_text("not json", encoding="utf-8")
        assert storage._load_storage_links() == {}

    def test_get_custom_storage_path_returns_none_when_unlinked(self, tmp_path):
        storage = _make_storage(tmp_path)
        assert storage.get_custom_storage_path("slot_a") is None

    def test_get_custom_storage_path_returns_linked_value(self, tmp_path):
        storage = _make_storage(tmp_path)
        storage._save_storage_links({"slot_a": "D:\\Dropbox\\slots"})
        assert storage.get_custom_storage_path("slot_a") == "D:\\Dropbox\\slots"
