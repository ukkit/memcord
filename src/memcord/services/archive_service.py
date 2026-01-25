"""Archive service for memory slot long-term storage.

Extracts business logic from the archive handler for better testability
and separation of concerns.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..storage import StorageManager


@dataclass
class ArchiveResult:
    """Result of an archive operation."""

    success: bool
    slot_name: str = ""
    archived_at: str = ""
    archive_reason: str = ""
    original_size: int = 0
    archived_size: int = 0
    space_saved: int = 0
    compression_ratio: float = 1.0
    error: str | None = None


@dataclass
class RestoreResult:
    """Result of a restore operation."""

    success: bool
    slot_name: str = ""
    restored_at: str = ""
    entry_count: int = 0
    total_size: int = 0
    error: str | None = None


@dataclass
class ArchiveInfo:
    """Information about an archived slot."""

    slot_name: str
    archived_at: str
    days_ago: int
    archive_reason: str
    entry_count: int
    original_size: int
    archived_size: int
    space_saved: int
    tags: list[str] = field(default_factory=list)
    group_path: str | None = None


@dataclass
class ArchiveListResult:
    """Result of listing archives."""

    success: bool
    archives: list[ArchiveInfo] = field(default_factory=list)
    error: str | None = None


@dataclass
class ArchiveStats:
    """Statistics about archive storage."""

    total_archives: int = 0
    total_original_size: int = 0
    total_archived_size: int = 0
    total_savings: int = 0
    savings_percentage: float = 0.0
    average_compression_ratio: float = 1.0


@dataclass
class ArchiveCandidate:
    """A memory slot that is a candidate for archival."""

    slot_name: str
    last_updated: str
    days_inactive: int
    entry_count: int
    current_size: int
    tags: list[str] = field(default_factory=list)
    group_path: str | None = None


@dataclass
class ArchiveCandidatesResult:
    """Result of finding archive candidates."""

    success: bool
    candidates: list[ArchiveCandidate] = field(default_factory=list)
    days_inactive_threshold: int = 30
    error: str | None = None


class ArchiveService:
    """Service for archive operations."""

    def __init__(self, storage: "StorageManager"):
        """Initialize archive service.

        Args:
            storage: Storage manager for slot operations
        """
        self.storage = storage

    async def archive_slot(self, slot_name: str, reason: str = "manual") -> ArchiveResult:
        """Archive a memory slot.

        Args:
            slot_name: Name of slot to archive
            reason: Reason for archiving

        Returns:
            ArchiveResult with operation results
        """
        if not slot_name:
            return ArchiveResult(
                success=False,
                error="slot_name is required for archive action",
            )

        try:
            archive_result = await self.storage.archive_slot(slot_name, reason)

            return ArchiveResult(
                success=True,
                slot_name=slot_name,
                archived_at=archive_result.get("archived_at", ""),
                archive_reason=archive_result.get("archive_reason", reason),
                original_size=archive_result.get("original_size", 0),
                archived_size=archive_result.get("archived_size", 0),
                space_saved=archive_result.get("space_saved", 0),
                compression_ratio=archive_result.get("compression_ratio", 1.0),
            )

        except Exception as e:
            return ArchiveResult(
                success=False,
                slot_name=slot_name,
                error=str(e),
            )

    async def restore_slot(self, slot_name: str) -> RestoreResult:
        """Restore a slot from archive.

        Args:
            slot_name: Name of slot to restore

        Returns:
            RestoreResult with operation results
        """
        if not slot_name:
            return RestoreResult(
                success=False,
                error="slot_name is required for restore action",
            )

        try:
            restore_result = await self.storage.restore_from_archive(slot_name)

            return RestoreResult(
                success=True,
                slot_name=slot_name,
                restored_at=restore_result.get("restored_at", ""),
                entry_count=restore_result.get("entry_count", 0),
                total_size=restore_result.get("total_size", 0),
            )

        except Exception as e:
            return RestoreResult(
                success=False,
                slot_name=slot_name,
                error=str(e),
            )

    async def list_archives(self) -> ArchiveListResult:
        """List all archived slots.

        Returns:
            ArchiveListResult with archive information
        """
        try:
            archives = await self.storage.list_archives(include_stats=True)

            if not archives:
                return ArchiveListResult(success=True, archives=[])

            archive_infos = []
            for archive in archives:
                archived_at = archive.get("archived_at", "")
                days_ago = 0
                if archived_at:
                    try:
                        days_ago = (datetime.now() - datetime.fromisoformat(archived_at)).days
                    except (ValueError, TypeError):
                        pass

                archive_infos.append(
                    ArchiveInfo(
                        slot_name=archive.get("slot_name", ""),
                        archived_at=archived_at,
                        days_ago=days_ago,
                        archive_reason=archive.get("archive_reason", ""),
                        entry_count=archive.get("entry_count", 0),
                        original_size=archive.get("original_size", 0),
                        archived_size=archive.get("archived_size", 0),
                        space_saved=archive.get("space_saved", 0),
                        tags=archive.get("tags", []) or [],
                        group_path=archive.get("group_path"),
                    )
                )

            return ArchiveListResult(success=True, archives=archive_infos)

        except Exception as e:
            return ArchiveListResult(success=False, error=str(e))

    async def get_stats(self) -> ArchiveStats:
        """Get archive statistics.

        Returns:
            ArchiveStats with aggregate statistics
        """
        try:
            stats = await self.storage.get_archive_stats()

            return ArchiveStats(
                total_archives=stats.get("total_archives", 0),
                total_original_size=stats.get("total_original_size", 0),
                total_archived_size=stats.get("total_archived_size", 0),
                total_savings=stats.get("total_savings", 0),
                savings_percentage=stats.get("savings_percentage", 0.0),
                average_compression_ratio=stats.get("average_compression_ratio", 1.0),
            )

        except Exception:
            return ArchiveStats()

    async def find_candidates(self, days_inactive: int = 30) -> ArchiveCandidatesResult:
        """Find memory slots that are candidates for archival.

        Args:
            days_inactive: Minimum days of inactivity

        Returns:
            ArchiveCandidatesResult with candidate information
        """
        try:
            candidates = await self.storage.find_archival_candidates(days_inactive)

            if not candidates:
                return ArchiveCandidatesResult(
                    success=True,
                    candidates=[],
                    days_inactive_threshold=days_inactive,
                )

            candidate_infos = []
            for slot_name, info in candidates:
                candidate_infos.append(
                    ArchiveCandidate(
                        slot_name=slot_name,
                        last_updated=info.get("last_updated", "")[:10],
                        days_inactive=info.get("days_inactive", 0),
                        entry_count=info.get("entry_count", 0),
                        current_size=info.get("current_size", 0),
                        tags=info.get("tags", []) or [],
                        group_path=info.get("group_path"),
                    )
                )

            return ArchiveCandidatesResult(
                success=True,
                candidates=candidate_infos,
                days_inactive_threshold=days_inactive,
            )

        except Exception as e:
            return ArchiveCandidatesResult(
                success=False,
                days_inactive_threshold=days_inactive,
                error=str(e),
            )
