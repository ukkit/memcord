"""Memory slot merging and consolidation system."""

import difflib
import logging
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from pydantic import BaseModel

from .models import MemorySlot

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

        # Collect all content
        all_content = []
        all_tags = set()
        all_groups = set()
        chronological_entries = []

        for slot in slots:
            # Direct MemorySlot access instead of using compatibility properties
            content = "\n\n".join(entry.content for entry in slot.entries)
            all_content.append(content)
            all_tags.update(slot.tags or [])
            if slot.group_path:
                all_groups.add(slot.group_path)

            # Use slot_name directly
            chronological_entries.append((slot.slot_name, slot.updated_at))

        # Sort chronologically
        chronological_entries.sort(key=lambda x: x[1])

        # Analyze duplicates
        content_blocks = []
        for content in all_content:
            # Split content into paragraphs for analysis
            paragraphs = [p.strip() for p in content.split("\n\n") if p.strip()]
            content_blocks.extend(paragraphs)

        duplicate_groups = self.similarity_analyzer.find_duplicate_paragraphs(content_blocks, similarity_threshold)

        # Calculate duplicate content to be removed
        duplicates_count = sum(len(group) - 1 for group in duplicate_groups)

        # Create preview content (first 500 chars)
        merged_content = self._merge_content(slots, similarity_threshold)
        content_preview = merged_content[:500] + "..." if len(merged_content) > 500 else merged_content

        return MergePreview(
            source_slots=[slot.slot_name for slot in slots],
            target_slot=target_name,
            total_content_length=len(merged_content),
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

            # Create preview to get merge statistics
            preview = self.create_merge_preview(slots, target_name, similarity_threshold)

            # Merge content
            merged_content = self._merge_content(slots, similarity_threshold)

            # Merge metadata
            merged_tags = list(preview.merged_tags)
            merged_groups = list(preview.merged_groups)

            # Create merged slot (return the content and metadata)
            # The actual slot creation will be handled by the storage manager

            return MergeResult(
                success=True,
                merged_slot_name=target_name,
                source_slots=[slot.slot_name for slot in slots],
                content_length=len(merged_content),
                duplicates_removed=preview.duplicate_content_removed,
                tags_merged=merged_tags,
                groups_merged=merged_groups,
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

    def _merge_content(self, slots: list[MemorySlot], similarity_threshold: float = 0.8) -> str:
        """Merge content from multiple slots, removing duplicates."""
        if not slots:
            return ""

        # Sort slots chronologically
        sorted_slots = sorted(slots, key=lambda x: x.updated_at)

        # Collect content sections with metadata
        content_sections = []

        for slot in sorted_slots:
            timestamp = slot.updated_at.strftime("%Y-%m-%d %H:%M:%S")
            content = "\n\n".join(entry.content for entry in slot.entries)

            header = f"\n--- From {slot.slot_name} ({timestamp}) ---\n"

            content_sections.append(
                {"header": header, "content": content, "slot_name": slot.slot_name, "timestamp": slot.updated_at}
            )

        # Remove duplicate content sections
        deduplicated_sections = self._remove_duplicate_sections(content_sections, similarity_threshold)

        # Combine into final content
        merged_parts = []

        # Add merge header
        merge_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        source_names = [slot.slot_name for slot in sorted_slots]

        merge_header = (
            f"=== MERGED MEMORY SLOT ===\n"
            f"Created: {merge_timestamp}\n"
            f"Source Slots: {', '.join(source_names)}\n"
            f"Total Sources: {len(source_names)}\n"
            f"=========================\n\n"
        )

        merged_parts.append(merge_header)

        # Add deduplicated content
        for section in deduplicated_sections:
            merged_parts.append(section["header"])
            merged_parts.append(section["content"])
            merged_parts.append("\n")

        return "".join(merged_parts)

    def _remove_duplicate_sections(
        self, sections: list[dict[str, Any]], similarity_threshold: float
    ) -> list[dict[str, Any]]:
        """Remove duplicate content sections."""
        if not sections:
            return []

        deduplicated = []

        for current_section in sections:
            is_duplicate = False

            # Check against already added sections
            for existing_section in deduplicated:
                similarity = self.similarity_analyzer.calculate_similarity(
                    current_section["content"], existing_section["content"]
                )

                if similarity >= similarity_threshold:
                    is_duplicate = True
                    # Keep the older section (chronologically first)
                    if current_section["timestamp"] < existing_section["timestamp"]:
                        # Replace with older section
                        deduplicated.remove(existing_section)
                        deduplicated.append(current_section)
                    break

            if not is_duplicate:
                deduplicated.append(current_section)

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
