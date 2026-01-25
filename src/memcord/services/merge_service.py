"""Merge service for memory slot operations.

Extracts business logic from the merge handler for better testability
and separation of concerns.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..models import MemorySlot
    from ..storage import StorageManager


@dataclass
class MergePreviewResult:
    """Result of a merge preview operation."""

    success: bool
    source_slots: list[str] = field(default_factory=list)
    target_slot: str = ""
    total_content_length: int = 0
    duplicate_content_removed: int = 0
    similarity_threshold: float = 0.8
    merged_tags: set[str] = field(default_factory=set)
    merged_groups: set[str] = field(default_factory=set)
    chronological_order: list[tuple[str, datetime]] = field(default_factory=list)
    content_preview: str = ""
    target_exists: bool = False
    error: str | None = None
    debug_info: str | None = None


@dataclass
class MergeExecuteResult:
    """Result of a merge execution operation."""

    success: bool
    target_slot: str = ""
    source_slots: list[str] = field(default_factory=list)
    content_length: int = 0
    duplicates_removed: int = 0
    merged_at: datetime | None = None
    tags_merged: list[str] = field(default_factory=list)
    groups_merged: list[str] = field(default_factory=list)
    deleted_sources: list[str] = field(default_factory=list)
    error: str | None = None


class MergeService:
    """Service for merging memory slots."""

    def __init__(self, storage: "StorageManager", merger):
        """Initialize merge service.

        Args:
            storage: Storage manager for slot operations
            merger: MemorySlotMerger instance
        """
        self.storage = storage
        self.merger = merger

    async def validate_merge_request(
        self,
        source_slots: list[str],
        target_slot: str,
    ) -> tuple[bool, str | None, list[str], str]:
        """Validate merge request parameters.

        Returns:
            Tuple of (is_valid, error_message, cleaned_source_slots, cleaned_target_slot)
        """
        if not source_slots or len(source_slots) < 2:
            return False, "At least 2 source slots are required for merging", [], ""

        if not target_slot or not target_slot.strip():
            return False, "Target slot name cannot be empty", [], ""

        # Clean slot names
        cleaned_sources = [name.strip() for name in source_slots if name.strip()]
        cleaned_target = target_slot.strip().replace(" ", "_")

        if len(cleaned_sources) < 2:
            return False, "At least 2 valid source slots are required", [], ""

        return True, None, cleaned_sources, cleaned_target

    async def load_source_slots(self, source_slot_names: list[str]) -> tuple[list["MemorySlot"], list[str]]:
        """Load source slots from storage.

        Returns:
            Tuple of (loaded_slots, missing_slot_names)
        """
        slots = []
        missing_slots = []

        for slot_name in source_slot_names:
            slot = await self.storage.read_memory(slot_name)
            if slot:
                slots.append(slot)
            else:
                missing_slots.append(slot_name)

        return slots, missing_slots

    async def preview_merge(
        self,
        source_slots: list[str],
        target_slot: str,
        similarity_threshold: float = 0.8,
    ) -> MergePreviewResult:
        """Generate a preview of the merge operation.

        Args:
            source_slots: List of source slot names
            target_slot: Target slot name
            similarity_threshold: Threshold for duplicate detection

        Returns:
            MergePreviewResult with preview data or error
        """
        # Validate request
        is_valid, error, cleaned_sources, cleaned_target = await self.validate_merge_request(source_slots, target_slot)
        if not is_valid:
            return MergePreviewResult(success=False, error=error)

        # Load source slots
        slots, missing_slots = await self.load_source_slots(cleaned_sources)

        if missing_slots:
            return MergePreviewResult(
                success=False,
                error=f"Memory slots not found: {', '.join(missing_slots)}",
            )

        if len(slots) < 2:
            return MergePreviewResult(
                success=False,
                error="Not enough valid slots found for merging",
            )

        # Check if target exists
        existing_target = await self.storage.read_memory(cleaned_target)

        # Create preview
        try:
            preview = self.merger.create_merge_preview(slots, cleaned_target, similarity_threshold)

            return MergePreviewResult(
                success=True,
                source_slots=list(preview.source_slots),
                target_slot=cleaned_target,
                total_content_length=preview.total_content_length,
                duplicate_content_removed=preview.duplicate_content_removed,
                similarity_threshold=similarity_threshold,
                merged_tags=preview.merged_tags,
                merged_groups=preview.merged_groups,
                chronological_order=list(preview.chronological_order),
                content_preview=preview.content_preview,
                target_exists=existing_target is not None,
            )

        except Exception as e:
            # Build debug info
            debug_info = self._build_debug_info(slots, e)
            return MergePreviewResult(
                success=False,
                error=f"Merge preview failed: {e}",
                debug_info=debug_info,
            )

    async def execute_merge(
        self,
        source_slots: list[str],
        target_slot: str,
        similarity_threshold: float = 0.8,
        delete_sources: bool = False,
    ) -> MergeExecuteResult:
        """Execute the merge operation.

        Args:
            source_slots: List of source slot names
            target_slot: Target slot name
            similarity_threshold: Threshold for duplicate detection
            delete_sources: Whether to delete source slots after merge

        Returns:
            MergeExecuteResult with operation results
        """
        # Validate request
        is_valid, error, cleaned_sources, cleaned_target = await self.validate_merge_request(source_slots, target_slot)
        if not is_valid:
            return MergeExecuteResult(success=False, error=error)

        # Load source slots
        slots, missing_slots = await self.load_source_slots(cleaned_sources)

        if missing_slots:
            return MergeExecuteResult(
                success=False,
                error=f"Memory slots not found: {', '.join(missing_slots)}",
            )

        if len(slots) < 2:
            return MergeExecuteResult(
                success=False,
                error="Not enough valid slots found for merging",
            )

        try:
            # Execute the merge
            merge_result = self.merger.merge_slots(slots, cleaned_target, similarity_threshold)

            if not merge_result.success:
                return MergeExecuteResult(
                    success=False,
                    error=f"Merge failed: {merge_result.error}",
                )

            # Get merged content
            merged_content = self.merger._merge_content(slots, similarity_threshold)

            # Create or update the target slot
            entry = await self.storage.save_memory(cleaned_target, merged_content)

            # Apply merged metadata
            target_memory_slot = await self.storage.read_memory(cleaned_target)
            if target_memory_slot and (merge_result.tags_merged or merge_result.groups_merged):
                if merge_result.tags_merged:
                    target_memory_slot.tags = merge_result.tags_merged

                if merge_result.groups_merged:
                    target_memory_slot.group_path = (
                        merge_result.groups_merged[0] if merge_result.groups_merged else None
                    )

                await self.storage._save_slot(target_memory_slot)

            # Delete source slots if requested
            deleted_sources = []
            if delete_sources:
                for source_slot in cleaned_sources:
                    try:
                        success = await self.storage.delete_slot(source_slot)
                        if success:
                            deleted_sources.append(source_slot)
                    except Exception:
                        # Continue with other deletions even if one fails
                        pass

            return MergeExecuteResult(
                success=True,
                target_slot=cleaned_target,
                source_slots=cleaned_sources,
                content_length=merge_result.content_length,
                duplicates_removed=merge_result.duplicates_removed,
                merged_at=entry.timestamp,
                tags_merged=list(merge_result.tags_merged) if merge_result.tags_merged else [],
                groups_merged=list(merge_result.groups_merged) if merge_result.groups_merged else [],
                deleted_sources=deleted_sources,
            )

        except Exception as e:
            import traceback

            return MergeExecuteResult(
                success=False,
                error=f"Merge operation failed: {e}\n{traceback.format_exc()}",
            )

    def _build_debug_info(self, slots: list["MemorySlot"], error: Exception) -> str:
        """Build debug information for merge errors."""
        import traceback

        debug_lines = [f"Full traceback:\n{traceback.format_exc()}", "", "Debug info:"]

        for i, slot in enumerate(slots):
            debug_lines.append(f"Slot {i} ({slot.slot_name}):")
            debug_lines.append(f"  - type: {type(slot)}")
            debug_lines.append(f"  - has_content: {hasattr(slot, 'content')}")
            debug_lines.append(f"  - has_name: {hasattr(slot, 'name')}")
            debug_lines.append(f"  - has_entries: {hasattr(slot, 'entries')}")
            debug_lines.append(f"  - entries_count: {len(slot.entries) if hasattr(slot, 'entries') else 'N/A'}")

            try:
                content = slot.content
                debug_lines.append(f"  - content_access: SUCCESS (length: {len(content)})")
            except Exception as content_error:
                debug_lines.append(f"  - content_access: FAILED ({content_error})")

            try:
                name = slot.name
                debug_lines.append(f"  - name_access: SUCCESS ({name})")
            except Exception as name_error:
                debug_lines.append(f"  - name_access: FAILED ({name_error})")

        return "\n".join(debug_lines)
