"""Tests for automatic summary entry consolidation (auto-pruning).

Covers:
- SlotConfig.max_auto_summaries field validation
- MemoryEntry rolled_summary type acceptance
- StorageManager._consolidate_old_summaries unit behaviour
- Integration via add_summary_entry end-to-end
"""

from datetime import datetime, timedelta
from pathlib import Path

import pytest
from pydantic import ValidationError

from memcord.models import MemoryEntry, MemorySlot, SlotConfig
from memcord.storage import StorageManager


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_storage(tmp_path: Path) -> StorageManager:
    return StorageManager(
        memory_dir=str(tmp_path / "slots"),
        shared_dir=str(tmp_path / "shared"),
        enable_caching=False,
        enable_efficiency=False,
        enable_memory_management=False,
    )


def _make_slot(n: int, entry_type: str = "auto_summary") -> MemorySlot:
    """Return a slot with *n* entries of the given type, each 1 minute apart."""
    slot = MemorySlot(slot_name="test")
    base = datetime(2026, 1, 1, 12, 0, 0)
    for i in range(n):
        slot.add_entry(
            MemoryEntry(
                type=entry_type,
                content=f"summary content {i}",
                timestamp=base + timedelta(minutes=i),
            )
        )
    return slot


# ---------------------------------------------------------------------------
# SlotConfig model
# ---------------------------------------------------------------------------


class TestSlotConfigMaxAutoSummaries:
    def test_default_is_five(self):
        config = SlotConfig()
        assert config.max_auto_summaries == 5

    def test_zero_is_valid(self):
        config = SlotConfig(max_auto_summaries=0)
        assert config.max_auto_summaries == 0

    def test_large_value_accepted(self):
        config = SlotConfig(max_auto_summaries=100)
        assert config.max_auto_summaries == 100

    def test_negative_rejected(self):
        with pytest.raises(ValidationError):
            SlotConfig(max_auto_summaries=-1)


# ---------------------------------------------------------------------------
# MemoryEntry type pattern
# ---------------------------------------------------------------------------


class TestMemoryEntryRolledSummaryType:
    def test_rolled_summary_accepted(self):
        entry = MemoryEntry(type="rolled_summary", content="consolidated text")
        assert entry.type == "rolled_summary"

    def test_manual_save_still_accepted(self):
        entry = MemoryEntry(type="manual_save", content="x")
        assert entry.type == "manual_save"

    def test_auto_summary_still_accepted(self):
        entry = MemoryEntry(type="auto_summary", content="x")
        assert entry.type == "auto_summary"

    def test_unknown_type_rejected(self):
        with pytest.raises(ValidationError):
            MemoryEntry(type="unknown_type", content="x")


# ---------------------------------------------------------------------------
# _consolidate_old_summaries unit tests
# ---------------------------------------------------------------------------


class TestConsolidateOldSummaries:
    @pytest.fixture
    def storage(self, tmp_path):
        return _make_storage(tmp_path)

    def test_no_consolidation_exactly_at_max(self, storage):
        slot = _make_slot(5)
        storage._consolidate_old_summaries(slot, max_entries=5)
        assert len(slot.entries) == 5
        assert all(e.type == "auto_summary" for e in slot.entries)

    def test_no_consolidation_below_max(self, storage):
        slot = _make_slot(3)
        storage._consolidate_old_summaries(slot, max_entries=5)
        assert len(slot.entries) == 3

    def test_consolidation_triggered_one_over_max(self, storage):
        slot = _make_slot(6)
        storage._consolidate_old_summaries(slot, max_entries=5)
        assert len(slot.entries) == 5

    def test_first_entry_becomes_rolled_summary(self, storage):
        slot = _make_slot(6)
        storage._consolidate_old_summaries(slot, max_entries=5)
        assert slot.entries[0].type == "rolled_summary"

    def test_consolidated_from_count_is_correct(self, storage):
        # 6 entries, max=5 → oldest 2 merged into 1 rolled
        slot = _make_slot(6)
        storage._consolidate_old_summaries(slot, max_entries=5)
        assert slot.entries[0].metadata["consolidated_from"] == 2

    def test_recent_entries_preserved_intact(self, storage):
        slot = _make_slot(6)
        recent_contents = [e.content for e in slot.entries[2:]]  # last 4
        storage._consolidate_old_summaries(slot, max_entries=5)
        assert [e.content for e in slot.entries[1:]] == recent_contents

    def test_rolled_content_contains_merged_originals(self, storage):
        slot = _make_slot(6)
        old_0_content = slot.entries[0].content
        old_1_content = slot.entries[1].content
        storage._consolidate_old_summaries(slot, max_entries=5)
        rolled_content = slot.entries[0].content
        assert old_0_content in rolled_content
        assert old_1_content in rolled_content

    def test_rolled_metadata_timestamps_present(self, storage):
        slot = _make_slot(6)
        storage._consolidate_old_summaries(slot, max_entries=5)
        meta = slot.entries[0].metadata
        assert "oldest_timestamp" in meta
        assert "newest_timestamp" in meta

    def test_rolled_metadata_oldest_is_earliest(self, storage):
        slot = _make_slot(6)
        first_ts = slot.entries[0].timestamp.isoformat()
        storage._consolidate_old_summaries(slot, max_entries=5)
        assert slot.entries[0].metadata["oldest_timestamp"] == first_ts

    def test_rolled_entries_count_toward_cap(self, storage):
        # Slot with 1 rolled_summary + 4 auto_summary = 5 total (at cap)
        slot = MemorySlot(slot_name="test")
        base = datetime(2026, 1, 1, 12, 0, 0)
        slot.add_entry(MemoryEntry(type="rolled_summary", content="old roll", timestamp=base))
        for i in range(5):
            slot.add_entry(
                MemoryEntry(
                    type="auto_summary",
                    content=f"summary {i}",
                    timestamp=base + timedelta(minutes=i + 1),
                )
            )
        # 6 total (1 rolled + 5 auto), max=5 → should consolidate
        storage._consolidate_old_summaries(slot, max_entries=5)
        assert len(slot.entries) == 5
        assert slot.entries[0].type == "rolled_summary"

    def test_large_batch_reduces_to_max(self, storage):
        slot = _make_slot(20)
        storage._consolidate_old_summaries(slot, max_entries=5)
        assert len(slot.entries) == 5
        assert slot.entries[0].type == "rolled_summary"
        assert slot.entries[0].metadata["consolidated_from"] == 16

    def test_manual_save_entries_not_counted_or_consolidated(self, storage):
        # manual_save entries should be ignored by the consolidation
        slot = MemorySlot(slot_name="test")
        base = datetime(2026, 1, 1)
        slot.add_entry(MemoryEntry(type="manual_save", content="important save", timestamp=base))
        for i in range(6):
            slot.add_entry(
                MemoryEntry(
                    type="auto_summary",
                    content=f"sum {i}",
                    timestamp=base + timedelta(minutes=i + 1),
                )
            )
        # 1 manual_save + 6 auto_summary; max=5 → consolidate 2 auto → 5 summary + 1 manual = 6 total
        storage._consolidate_old_summaries(slot, max_entries=5)
        manual_entries = [e for e in slot.entries if e.type == "manual_save"]
        assert len(manual_entries) == 1
        assert manual_entries[0].content == "important save"


# ---------------------------------------------------------------------------
# Integration: add_summary_entry triggers consolidation
# ---------------------------------------------------------------------------


class TestAutoConsolidationIntegration:
    @pytest.mark.asyncio
    async def test_consolidation_triggers_when_cap_exceeded(self, tmp_path):
        storage = _make_storage(tmp_path)
        await storage.save_slot_config("s", SlotConfig(max_auto_summaries=3))
        for i in range(4):
            await storage.add_summary_entry("s", f"original {i}", f"summary {i}")
        slot = await storage.read_memory("s")
        summary_entries = [e for e in slot.entries if e.type in {"auto_summary", "rolled_summary"}]
        assert len(summary_entries) == 3

    @pytest.mark.asyncio
    async def test_no_consolidation_when_disabled(self, tmp_path):
        storage = _make_storage(tmp_path)
        await storage.save_slot_config("s", SlotConfig(max_auto_summaries=0))
        for i in range(8):
            await storage.add_summary_entry("s", f"original {i}", f"summary {i}")
        slot = await storage.read_memory("s")
        assert len(slot.entries) == 8

    @pytest.mark.asyncio
    async def test_rolled_summary_appears_after_consolidation(self, tmp_path):
        storage = _make_storage(tmp_path)
        await storage.save_slot_config("s", SlotConfig(max_auto_summaries=3))
        for i in range(4):
            await storage.add_summary_entry("s", f"original {i}", f"summary {i}")
        slot = await storage.read_memory("s")
        assert slot.entries[0].type == "rolled_summary"

    @pytest.mark.asyncio
    async def test_consolidation_persists_to_disk(self, tmp_path):
        storage = _make_storage(tmp_path)
        await storage.save_slot_config("s", SlotConfig(max_auto_summaries=3))
        for i in range(4):
            await storage.add_summary_entry("s", f"original {i}", f"summary {i}")

        # Re-load with a fresh StorageManager instance
        storage2 = _make_storage(tmp_path)
        slot = await storage2.read_memory("s")
        assert slot is not None
        summary_entries = [e for e in slot.entries if e.type in {"auto_summary", "rolled_summary"}]
        assert len(summary_entries) == 3
        assert slot.entries[0].type == "rolled_summary"

    @pytest.mark.asyncio
    async def test_default_cap_of_five_applied(self, tmp_path):
        storage = _make_storage(tmp_path)
        # No explicit config → default max_auto_summaries=5
        for i in range(7):
            await storage.add_summary_entry("s", f"original {i}", f"summary {i}")
        slot = await storage.read_memory("s")
        summary_entries = [e for e in slot.entries if e.type in {"auto_summary", "rolled_summary"}]
        assert len(summary_entries) == 5

    @pytest.mark.asyncio
    async def test_continued_saves_stay_bounded(self, tmp_path):
        storage = _make_storage(tmp_path)
        await storage.save_slot_config("s", SlotConfig(max_auto_summaries=3))
        for i in range(20):
            await storage.add_summary_entry("s", f"original {i}", f"summary {i}")
        slot = await storage.read_memory("s")
        summary_entries = [e for e in slot.entries if e.type in {"auto_summary", "rolled_summary"}]
        assert len(summary_entries) == 3
