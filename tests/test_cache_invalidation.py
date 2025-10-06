"""
Tests for cache invalidation on external file modifications.

Ensures cache is invalidated when memory slot files are modified externally
(e.g., by backup restoration tools).
"""

import asyncio
import json
import time

import pytest

from memcord.storage import StorageManager


@pytest.mark.asyncio
async def test_cache_invalidated_on_external_file_modification(tmp_path):
    """Test that cache is invalidated when file is modified externally."""
    # Create storage with caching enabled
    storage = StorageManager(
        memory_dir=str(tmp_path),
        enable_caching=True,
        enable_efficiency=False,
        enable_memory_management=False,
    )

    # Save initial slot
    slot_name = "test_cache_invalidation"
    await storage.save_memory(slot_name, "Original content")

    # Read slot (will be cached)
    slot1 = await storage.read_memory(slot_name)
    assert slot1 is not None
    assert len(slot1.entries) == 1
    assert slot1.entries[0].content == "Original content"

    # Modify file EXTERNALLY (simulating memcord-tools or manual edit)
    slot_file = tmp_path / f"{slot_name}.json"

    # Sleep briefly to ensure different mtime
    time.sleep(0.01)

    # Directly modify the JSON file
    with open(slot_file, encoding="utf-8") as f:
        data = json.load(f)

    # Add a new entry externally
    data["entries"].append(
        {
            "type": "manual_save",
            "content": "Added by external tool",
            "timestamp": "2025-09-30T00:00:00.000000",
            "metadata": {},
            "compression_info": {
                "is_compressed": False,
                "algorithm": "none",
                "original_size": None,
                "compressed_size": None,
                "compression_ratio": None,
                "compressed_at": None,
            },
        }
    )

    with open(slot_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

    # Read slot again - should detect file change and reload
    slot2 = await storage.read_memory(slot_name)
    assert slot2 is not None

    # Should see the externally added entry
    assert len(slot2.entries) == 2
    assert slot2.entries[0].content == "Original content"
    assert slot2.entries[1].content == "Added by external tool"


@pytest.mark.asyncio
async def test_cache_used_when_file_unchanged(tmp_path):
    """Test that cache is used when file hasn't changed."""
    storage = StorageManager(
        memory_dir=str(tmp_path),
        enable_caching=True,
        enable_efficiency=False,
        enable_memory_management=False,
    )

    slot_name = "test_cache_reuse"
    await storage.save_memory(slot_name, "Test content")

    # First read - loads from file
    slot1 = await storage.read_memory(slot_name)
    assert slot1 is not None

    # Second read - should use cache (file unchanged)
    slot2 = await storage.read_memory(slot_name)
    assert slot2 is not None

    # Should be same data
    assert len(slot1.entries) == len(slot2.entries)
    assert slot1.entries[0].content == slot2.entries[0].content


@pytest.mark.asyncio
async def test_cache_invalidation_with_memcord_tools_simulation(tmp_path):
    """Simulate memcord-tools restoration workflow to verify cache invalidation."""
    storage = StorageManager(
        memory_dir=str(tmp_path),
        enable_caching=True,
        enable_efficiency=False,
        enable_memory_management=False,
    )

    # Create initial slot (simulates normal memcord usage)
    slot_name = "simulation_slot"
    await storage.save_memory(slot_name, "Current work")

    # Read slot (gets cached)
    slot_before = await storage.read_memory(slot_name)
    assert len(slot_before.entries) == 1

    # Simulate memcord-tools restoring missing entries
    slot_file = tmp_path / f"{slot_name}.json"

    # Wait to ensure different mtime
    await asyncio.sleep(0.1)

    # Load current data
    with open(slot_file, encoding="utf-8") as f:
        data = json.load(f)

    # Add "restored" entries
    data["entries"].insert(
        0,
        {
            "type": "auto_summary",
            "content": "Historical entry restored from backup",
            "timestamp": "2025-09-25T00:00:00.000000",
            "original_length": 500,
            "summary_length": 50,
            "metadata": {},
            "compression_info": {"is_compressed": False, "algorithm": "none"},
        },
    )

    # Sort chronologically (like memcord-tools does)
    data["entries"].sort(key=lambda x: x.get("timestamp", ""))

    # Save merged data
    with open(slot_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

    # Read slot - should see restored entry
    slot_after = await storage.read_memory(slot_name)
    assert len(slot_after.entries) == 2
    assert slot_after.entries[0].content == "Historical entry restored from backup"
    assert slot_after.entries[1].content == "Current work"
