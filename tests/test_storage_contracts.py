"""Tests for storage.py core operations.

Tests basic storage contracts and critical bug fixes.

- Storage initialization with absolute paths (validates path resolution fix)
- Basic save/load operations
- Delete operations
- Data persistence contracts
"""

import pytest

from memcord.models import MemorySlot


class TestStorageManagerContracts:
    """Test StorageManager core contracts."""

    @pytest.mark.asyncio
    async def test_storage_initialization_contract(self, clean_storage_manager):
        """Test StorageManager initialization contract."""
        storage = clean_storage_manager

        # Contract: Directories should be created automatically
        assert storage.memory_dir.exists()
        assert storage.shared_dir.exists()

        # Contract: Paths should be absolute (our bug fix)
        assert storage.memory_dir.is_absolute()
        assert storage.shared_dir.is_absolute()

    @pytest.mark.asyncio
    async def test_save_memory_contract(self, clean_storage_manager):
        """Test save_memory core contract."""
        from .conftest import assert_valid_memory_entry

        storage = clean_storage_manager

        # Contract: Should create new slot if doesn't exist
        entry = await storage.save_memory("new_slot", "Initial content")

        assert_valid_memory_entry(entry, "manual_save")
        assert entry.content == "Initial content"

        # Contract: manual_save should REPLACE content (correct behavior)
        _ = await storage.save_memory("new_slot", "Updated content")

        # Read and verify content was replaced (not appended)
        slot = await storage.read_memory("new_slot")
        assert slot is not None
        assert len(slot.entries) == 1  # Only latest entry (replaced)
        assert slot.entries[0].content == "Updated content"

    @pytest.mark.asyncio
    async def test_read_memory_contract(self, clean_storage_manager):
        """Test read_memory core contract."""
        storage = clean_storage_manager

        # Contract: Loading non-existent slot returns None
        result = await storage.read_memory("nonexistent")
        assert result is None

        # Contract: Loading existing slot returns MemorySlot
        await storage.save_memory("existing", "Test content")
        loaded = await storage.read_memory("existing")

        assert loaded is not None
        assert isinstance(loaded, MemorySlot)
        assert loaded.slot_name == "existing"
        assert len(loaded.entries) == 1

    @pytest.mark.asyncio
    async def test_delete_slot_contract(self, clean_storage_manager):
        """Test delete_slot core contract."""
        storage = clean_storage_manager

        # Contract: Deleting non-existent slot returns False
        result = await storage.delete_slot("nonexistent")
        assert result is False

        # Contract: Deleting existing slot returns True and removes it
        await storage.save_memory("test_removal", "Content")

        # Verify it exists
        slot = await storage.read_memory("test_removal")
        assert slot is not None

        # Delete it
        result = await storage.delete_slot("test_removal")
        assert result is True

        # Verify it's gone
        slot_after = await storage.read_memory("test_removal")
        assert slot_after is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
