"""Memory slot merging and consolidation system."""

import difflib
import logging
import re
from dataclasses import dataclass
from datetime import datetime

from pydantic import BaseModel, Field

from .models import MemoryEntry, MemorySlot

logger = logging.getLogger(__name__)


@dataclass
class MergePreview:
    """Preview of a merge operation."""

    source_slots: list[str]
    target_slot: str
    total_content_length: int
    duplicate_content_removed: int
    merged_tags: set[str]
    merged_groups: set[str]
    chronological_order: list[tuple[str, datetime]]
    content_preview: str


class MergeResult(BaseModel):
    """Result of a merge operation."""

    success: bool
    merged_slot_name: str
    source_slots: list[str]
    content_length: int
    duplicates_removed: int
    tags_merged: list[str]
    groups_merged: list[str]
    error: str | None = None
    merged_entries: list[MemoryEntry] = Field(default_factory=list)


class ContentSimilarityAnalyzer:
    """Analyzes content similarity for duplicate detection."""

    @staticmethod
    def calculate_similarity(text1: str, text2: str) -> float:
        """Calculate similarity between two text strings (0.0 to 1.0)."""
        if not text1 or not text2:
            return 0.0

        # Normalize text for comparison
        normalized1 = ContentSimilarityAnalyzer._normalize_text(text1)
        normalized2 = ContentSimilarityAnalyzer._normalize_text(text2)

        # Use sequence matcher for similarity
        matcher = difflib.SequenceMatcher(None, normalized1, normalized2)
        return matcher.ratio()

    @staticmethod
    def _normalize_text(text: str) -> str:
        """Normalize text for comparison."""
        # Convert to lowercase
        text = text.lower()

        # Remove extra whitespace
        text = re.sub(r"\s+", " ", text)

        # Remove common punctuation
        text = re.sub(r"[^\w\s]", "", text)

        return text.strip()

    @staticmethod
    def find_duplicate_paragraphs(content_blocks: list[str], similarity_threshold: float = 0.8) -> list[list[int]]:
        """Find groups of similar paragraphs across content blocks."""
        duplicates = []
        processed = set()

        for i, block1 in enumerate(content_blocks):
            if i in processed:
                continue

            similar_group = [i]

            for j, block2 in enumerate(content_blocks[i + 1 :], i + 1):
                if j in processed:
                    continue

                similarity = ContentSimilarityAnalyzer.calculate_similarity(block1, block2)
                if similarity >= similarity_threshold:
                    similar_group.append(j)
                    processed.add(j)

            if len(similar_group) > 1:
                duplicates.append(similar_group)
                processed.update(similar_group)

        return duplicates


class MemorySlotMerger:
    """Handles merging and consolidation of memory slots."""

    def __init__(self):
        self.similarity_analyzer = ContentSimilarityAnalyzer()

    def create_merge_preview(
        self, slots: list[MemorySlot], target_name: str, similarity_threshold: float = 0.8
    ) -> MergePreview:
        """Create a preview of the merge operation."""
        if not slots:
            raise ValueError("No slots provided for merge preview")

        # Collect merged entries for accurate stats
        merged_entries = self._collect_entries(slots, similarity_threshold)

        # Count duplicates
        total_entry_count = sum(len(slot.entries) for slot in slots)
        duplicates_count = total_entry_count - len(merged_entries)

        # Total content length across all merged entries
        total_content_length = sum(len(e.content) for e in merged_entries)

        # Tags and groups
        all_tags: set[str] = set()
        all_groups: set[str] = set()
        for slot in slots:
            all_tags.update(slot.tags or [])
            if slot.group_path:
                all_groups.add(slot.group_path)

        # Chronological order by slot updated_at
        chronological_entries = sorted(
            [(slot.slot_name, slot.updated_at) for slot in slots],
            key=lambda x: x[1],
        )

        # Content preview from first merged entry
        content_preview = ""
        if merged_entries:
            first_content = merged_entries[0].content
            content_preview = first_content[:500] + "..." if len(first_content) > 500 else first_content

        return MergePreview(
            source_slots=[slot.slot_name for slot in slots],
            target_slot=target_name,
            total_content_length=total_content_length,
            duplicate_content_removed=duplicates_count,
            merged_tags=all_tags,
            merged_groups=all_groups,
            chronological_order=chronological_entries,
            content_preview=content_preview,
        )

    def merge_slots(self, slots: list[MemorySlot], target_name: str, similarity_threshold: float = 0.8) -> MergeResult:
        """Merge multiple memory slots into one."""
        try:
            if not slots:
                return MergeResult(
                    success=False,
                    merged_slot_name=target_name,
                    source_slots=[],
                    content_length=0,
                    duplicates_removed=0,
                    tags_merged=[],
                    groups_merged=[],
                    error="No slots provided for merging",
                )

            # Collect and deduplicate entries, preserving individual MemoryEntry objects
            merged_entries = self._collect_entries(slots, similarity_threshold)

            # Count duplicates removed
            total_entry_count = sum(len(slot.entries) for slot in slots)
            duplicates_removed = total_entry_count - len(merged_entries)

            # Total content length
            content_length = sum(len(e.content) for e in merged_entries)

            # Merge metadata
            merged_tags = list(set().union(*(set(slot.tags or []) for slot in slots)))
            merged_groups = list({slot.group_path for slot in slots if slot.group_path})

            return MergeResult(
                success=True,
                merged_slot_name=target_name,
                source_slots=[slot.slot_name for slot in slots],
                content_length=content_length,
                duplicates_removed=duplicates_removed,
                tags_merged=merged_tags,
                groups_merged=merged_groups,
                merged_entries=merged_entries,
            )

        except Exception as e:
            logger.error(f"Error merging slots: {e}")
            return MergeResult(
                success=False,
                merged_slot_name=target_name,
                source_slots=[slot.slot_name for slot in slots],
                content_length=0,
                duplicates_removed=0,
                tags_merged=[],
                groups_merged=[],
                error=str(e),
            )

    def _collect_entries(self, slots: list[MemorySlot], similarity_threshold: float = 0.8) -> list[MemoryEntry]:
        """Collect all entries from slots, deduplicate by content similarity, and sort by timestamp."""
        if not slots:
            return []

        # Gather all entries from all source slots
        all_entries: list[MemoryEntry] = []
        for slot in slots:
            all_entries.extend(slot.entries)

        # Sort by timestamp ascending so the oldest entry is always encountered first
        all_entries.sort(key=lambda e: e.timestamp)

        # Deduplicate: since entries are sorted oldest-first, the already-accepted entry
        # is always the older one — we simply skip any later candidate that is too similar.
        deduplicated: list[MemoryEntry] = []
        for candidate in all_entries:
            is_duplicate = any(
                self.similarity_analyzer.calculate_similarity(candidate.content, existing.content)
                >= similarity_threshold
                for existing in deduplicated
            )
            if not is_duplicate:
                deduplicated.append(candidate)

        return deduplicated

    def suggest_merge_candidates(self, slots: list[MemorySlot], similarity_threshold: float = 0.7) -> list[list[str]]:
        """Suggest groups of slots that might be good candidates for merging."""
        if len(slots) < 2:
            return []

        merge_candidates = []
        processed_slots = set()

        for i, slot1 in enumerate(slots):
            name1 = slot1.slot_name
            if name1 in processed_slots:
                continue

            similar_slots = [name1]

            for _j, slot2 in enumerate(slots[i + 1 :], i + 1):
                name2 = slot2.slot_name
                if name2 in processed_slots:
                    continue

                # Check content similarity
                content1 = "\n\n".join(entry.content for entry in slot1.entries)
                content2 = "\n\n".join(entry.content for entry in slot2.entries)

                content_similarity = self.similarity_analyzer.calculate_similarity(content1, content2)

                # Check tag overlap
                tags1 = set(slot1.tags or [])
                tags2 = set(slot2.tags or [])
                tag_overlap = len(tags1 & tags2) / max(len(tags1 | tags2), 1)

                # Check group similarity
                group_match = (slot1.group_path == slot2.group_path) if slot1.group_path and slot2.group_path else False

                # Combined similarity score
                combined_score = content_similarity * 0.6 + tag_overlap * 0.3 + (0.1 if group_match else 0)

                if combined_score >= similarity_threshold:
                    similar_slots.append(name2)
                    processed_slots.add(name2)

            if len(similar_slots) > 1:
                merge_candidates.append(similar_slots)
                processed_slots.update(similar_slots)

        return merge_candidates
