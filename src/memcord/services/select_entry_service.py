"""Select entry service for temporal memory entry selection.

Provides business logic for selecting specific memory entries
by timestamp, relative time, or index.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from ..storage import StorageManager
from ..temporal_parser import TemporalParser


@dataclass
class SelectedEntry:
    """Result of entry selection."""

    success: bool
    slot_name: str = ""
    error: str | None = None

    # Entry data (when found)
    timestamp: datetime | None = None
    entry_type: str = ""
    content: str = ""
    index: int = -1

    # Selection metadata
    selection_method: str = ""
    selection_query: str = ""
    tolerance_applied: bool = False

    # Context data (optional)
    context: dict[str, Any] = field(default_factory=dict)

    # Available entries for error messages
    available_entries: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class SelectionRequest:
    """Parameters for entry selection."""

    slot_name: str
    timestamp: str | None = None
    relative_time: str | None = None
    entry_index: int | None = None
    entry_type: str | None = None
    show_context: bool = True


class SelectEntryService:
    """Service for selecting memory entries by various criteria."""

    def __init__(self, storage: StorageManager):
        """Initialize the service.

        Args:
            storage: StorageManager instance for reading memory slots
        """
        self.storage = storage

    async def select_entry(self, request: SelectionRequest) -> SelectedEntry:
        """Select a memory entry based on the request criteria.

        Args:
            request: SelectionRequest with slot name and selection criteria

        Returns:
            SelectedEntry with the found entry or error information
        """
        slot_name = request.slot_name

        # Load the memory slot
        slot = await self.storage.read_memory(slot_name)
        if not slot:
            return SelectedEntry(
                success=False,
                slot_name=slot_name,
                error=f"Memory slot '{slot_name}' not found. Use 'memcord_list' to see available slots.",
            )

        # Check if slot has entries
        if not slot.entries:
            return SelectedEntry(
                success=False,
                slot_name=slot_name,
                error=f"Memory slot '{slot_name}' is empty. No entries to select.",
            )

        # Validate selection input
        is_valid, error_msg = TemporalParser.validate_selection_input(
            request.timestamp, request.relative_time, request.entry_index
        )
        if not is_valid:
            return SelectedEntry(
                success=False,
                slot_name=slot_name,
                error=error_msg,
            )

        # Find the entry
        selected_entry = None
        selected_index = -1
        selection_method = ""
        selection_query = ""
        tolerance_applied = False

        if request.timestamp:
            result = self._find_by_timestamp(slot, request.timestamp)
            if result["found"]:
                selected_index = result["index"]
                selected_entry = result["entry"]
                selection_method = "timestamp"
                selection_query = request.timestamp
                tolerance_applied = result.get("tolerance_applied", False)
            elif result.get("error"):
                return SelectedEntry(
                    success=False,
                    slot_name=slot_name,
                    error=result["error"],
                )

        elif request.relative_time:
            time_result = slot.get_entry_by_relative_time(request.relative_time)
            if time_result:
                selected_index, selected_entry = time_result
                selection_method = "relative_time"
                selection_query = request.relative_time

        elif request.entry_index is not None:
            index_result = slot.get_entry_by_index(request.entry_index)
            if index_result:
                selected_index, selected_entry = index_result
                selection_method = "index"
                selection_query = str(request.entry_index)

        # Filter by entry type if specified
        if selected_entry and request.entry_type and selected_entry.type != request.entry_type:
            selected_entry = None
            selected_index = -1

        # Handle no match found
        if not selected_entry:
            available_entries = self._get_available_entries(slot)
            return SelectedEntry(
                success=False,
                slot_name=slot_name,
                error=f"No matching entry found for {selection_method.replace('_', ' ')}: '{selection_query}'",
                available_entries=available_entries,
            )

        # Build context if requested
        context = {}
        if request.show_context:
            context = slot.get_timeline_context(selected_index) or {}

        return SelectedEntry(
            success=True,
            slot_name=slot_name,
            timestamp=selected_entry.timestamp,
            entry_type=selected_entry.type,
            content=selected_entry.content,
            index=selected_index,
            selection_method=selection_method,
            selection_query=selection_query,
            tolerance_applied=tolerance_applied,
            context=context,
        )

    def _find_by_timestamp(self, slot, timestamp_str: str) -> dict[str, Any]:
        """Find entry by timestamp string.

        Args:
            slot: Memory slot to search
            timestamp_str: Timestamp string to parse and match

        Returns:
            Dict with 'found', 'index', 'entry', 'tolerance_applied', or 'error'
        """
        parsed_time = TemporalParser.parse_timestamp(timestamp_str)
        if not parsed_time:
            return {
                "found": False,
                "error": (
                    f"Invalid timestamp format: '{timestamp_str}'\n\n"
                    "Expected formats:\n"
                    "- ISO format: '2025-07-21T17:30:00'\n"
                    "- Date only: '2025-07-21'\n"
                    "- With timezone: '2025-07-21T17:30:00Z'"
                ),
            }

        result = slot.get_entry_by_timestamp(parsed_time)
        if result:
            index, entry = result
            tolerance_applied = abs(entry.timestamp - parsed_time).total_seconds() > 60
            return {
                "found": True,
                "index": index,
                "entry": entry,
                "tolerance_applied": tolerance_applied,
            }

        return {"found": False}

    def _get_available_entries(self, slot) -> list[dict[str, Any]]:
        """Get list of available entries for error messages.

        Args:
            slot: Memory slot to list entries from

        Returns:
            List of entry info dicts with timestamp, type, and time_description
        """
        entries = []
        available_timestamps = slot.get_available_timestamps()
        for i, ts in enumerate(available_timestamps):
            entry = slot.entries[i]
            time_desc = TemporalParser.format_time_description(entry.timestamp)
            entries.append(
                {
                    "index": i,
                    "timestamp": ts,
                    "type": entry.type,
                    "time_description": time_desc,
                }
            )
        return entries
