"""Tests for the archive service module.

Tests the ArchiveService business logic extracted from the server handlers
during the optimization (Phase 2).
"""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from memcord.services.archive_service import (
    ArchiveCandidate,
    ArchiveCandidatesResult,
    ArchiveInfo,
    ArchiveListResult,
    ArchiveResult,
    ArchiveService,
    ArchiveStats,
    RestoreResult,
)


class TestArchiveResult:
    """Tests for ArchiveResult dataclass."""

    def test_successful_archive_result(self):
        """Test creating a successful archive result."""
        result = ArchiveResult(
            success=True,
            slot_name="my_slot",
            archived_at="2026-01-24T10:00:00",
            archive_reason="manual",
            original_size=10000,
            archived_size=6000,
            space_saved=4000,
            compression_ratio=0.6,
        )

        assert result.success is True
        assert result.slot_name == "my_slot"
        assert result.space_saved == 4000

    def test_failed_archive_result(self):
        """Test creating a failed archive result."""
        result = ArchiveResult(
            success=False,
            slot_name="my_slot",
            error="Slot not found",
        )

        assert result.success is False
        assert result.error == "Slot not found"

    def test_default_values(self):
        """Test default values are set correctly."""
        result = ArchiveResult(success=True)

        assert result.slot_name == ""
        assert result.archived_at == ""
        assert result.compression_ratio == 1.0


class TestRestoreResult:
    """Tests for RestoreResult dataclass."""

    def test_successful_restore_result(self):
        """Test creating a successful restore result."""
        result = RestoreResult(
            success=True,
            slot_name="my_slot",
            restored_at="2026-01-24T10:00:00",
            entry_count=5,
            total_size=10000,
        )

        assert result.success is True
        assert result.entry_count == 5

    def test_failed_restore_result(self):
        """Test creating a failed restore result."""
        result = RestoreResult(
            success=False,
            slot_name="my_slot",
            error="Archive corrupted",
        )

        assert result.success is False


class TestArchiveInfo:
    """Tests for ArchiveInfo dataclass."""

    def test_archive_info_creation(self):
        """Test creating archive info."""
        info = ArchiveInfo(
            slot_name="archived_slot",
            archived_at="2026-01-20T10:00:00",
            days_ago=4,
            archive_reason="inactivity",
            entry_count=10,
            original_size=10000,
            archived_size=6000,
            space_saved=4000,
            tags=["project", "important"],
            group_path="work/project",
        )

        assert info.slot_name == "archived_slot"
        assert info.days_ago == 4
        assert info.tags == ["project", "important"]


class TestArchiveStats:
    """Tests for ArchiveStats dataclass."""

    def test_archive_stats_creation(self):
        """Test creating archive stats."""
        stats = ArchiveStats(
            total_archives=10,
            total_original_size=100000,
            total_archived_size=60000,
            total_savings=40000,
            savings_percentage=40.0,
            average_compression_ratio=0.6,
        )

        assert stats.total_archives == 10
        assert stats.savings_percentage == 40.0

    def test_default_values(self):
        """Test default values."""
        stats = ArchiveStats()

        assert stats.total_archives == 0
        assert stats.average_compression_ratio == 1.0


class TestArchiveCandidate:
    """Tests for ArchiveCandidate dataclass."""

    def test_candidate_creation(self):
        """Test creating an archive candidate."""
        candidate = ArchiveCandidate(
            slot_name="old_slot",
            last_updated="2025-12-01",
            days_inactive=54,
            entry_count=5,
            current_size=5000,
            tags=["old"],
            group_path="archive/candidates",
        )

        assert candidate.slot_name == "old_slot"
        assert candidate.days_inactive == 54


class TestArchiveCandidatesResult:
    """Tests for ArchiveCandidatesResult dataclass."""

    def test_candidates_result_with_entries(self):
        """Test result with archive candidates."""
        result = ArchiveCandidatesResult(
            success=True,
            candidates=[
                ArchiveCandidate(
                    slot_name="slot1",
                    last_updated="2025-12-01",
                    days_inactive=54,
                    entry_count=5,
                    current_size=5000,
                ),
            ],
            days_inactive_threshold=30,
        )

        assert result.success is True
        assert len(result.candidates) == 1

    def test_empty_candidates_result(self):
        """Test result with no candidates."""
        result = ArchiveCandidatesResult(
            success=True,
            candidates=[],
            days_inactive_threshold=30,
        )

        assert result.success is True
        assert len(result.candidates) == 0


class TestArchiveServiceArchive:
    """Tests for ArchiveService archive method."""

    @pytest.fixture
    def mock_storage(self):
        """Create mock storage manager."""
        storage = MagicMock()
        storage.archive_slot = AsyncMock()
        storage.restore_from_archive = AsyncMock()
        storage.list_archives = AsyncMock()
        storage.get_archive_stats = AsyncMock()
        storage.find_archival_candidates = AsyncMock()
        return storage

    @pytest.fixture
    def archive_service(self, mock_storage):
        """Create ArchiveService instance."""
        return ArchiveService(mock_storage)

    @pytest.mark.asyncio
    async def test_archive_success(self, archive_service, mock_storage):
        """Test successful slot archival."""
        mock_storage.archive_slot.return_value = {
            "archived_at": "2026-01-24T10:00:00",
            "archive_reason": "manual",
            "original_size": 10000,
            "archived_size": 6000,
            "space_saved": 4000,
            "compression_ratio": 0.6,
        }

        result = await archive_service.archive_slot("my_slot", "cleanup")

        assert result.success is True
        assert result.slot_name == "my_slot"
        assert result.space_saved == 4000
        mock_storage.archive_slot.assert_called_once_with("my_slot", "cleanup")

    @pytest.mark.asyncio
    async def test_archive_empty_slot_name(self, archive_service):
        """Test archive with empty slot name."""
        result = await archive_service.archive_slot("", "reason")

        assert result.success is False
        assert "slot_name is required" in result.error

    @pytest.mark.asyncio
    async def test_archive_default_reason(self, archive_service, mock_storage):
        """Test archive uses default reason."""
        mock_storage.archive_slot.return_value = {
            "archived_at": "2026-01-24T10:00:00",
            "archive_reason": "manual",
        }

        await archive_service.archive_slot("my_slot")

        mock_storage.archive_slot.assert_called_once_with("my_slot", "manual")

    @pytest.mark.asyncio
    async def test_archive_error_handling(self, archive_service, mock_storage):
        """Test archive error handling."""
        mock_storage.archive_slot.side_effect = ValueError("Slot not found")

        result = await archive_service.archive_slot("nonexistent")

        assert result.success is False
        assert "Slot not found" in result.error


class TestArchiveServiceRestore:
    """Tests for ArchiveService restore method."""

    @pytest.fixture
    def mock_storage(self):
        """Create mock storage manager."""
        storage = MagicMock()
        storage.restore_from_archive = AsyncMock()
        return storage

    @pytest.fixture
    def archive_service(self, mock_storage):
        """Create ArchiveService instance."""
        return ArchiveService(mock_storage)

    @pytest.mark.asyncio
    async def test_restore_success(self, archive_service, mock_storage):
        """Test successful restoration."""
        mock_storage.restore_from_archive.return_value = {
            "restored_at": "2026-01-24T10:00:00",
            "entry_count": 5,
            "total_size": 10000,
        }

        result = await archive_service.restore_slot("my_slot")

        assert result.success is True
        assert result.slot_name == "my_slot"
        assert result.entry_count == 5

    @pytest.mark.asyncio
    async def test_restore_empty_slot_name(self, archive_service):
        """Test restore with empty slot name."""
        result = await archive_service.restore_slot("")

        assert result.success is False
        assert "slot_name is required" in result.error

    @pytest.mark.asyncio
    async def test_restore_error_handling(self, archive_service, mock_storage):
        """Test restore error handling."""
        mock_storage.restore_from_archive.side_effect = ValueError("Archive not found")

        result = await archive_service.restore_slot("nonexistent")

        assert result.success is False
        assert "Archive not found" in result.error


class TestArchiveServiceListArchives:
    """Tests for ArchiveService list_archives method."""

    @pytest.fixture
    def mock_storage(self):
        """Create mock storage manager."""
        storage = MagicMock()
        storage.list_archives = AsyncMock()
        return storage

    @pytest.fixture
    def archive_service(self, mock_storage):
        """Create ArchiveService instance."""
        return ArchiveService(mock_storage)

    @pytest.mark.asyncio
    async def test_list_archives_empty(self, archive_service, mock_storage):
        """Test listing when no archives exist."""
        mock_storage.list_archives.return_value = []

        result = await archive_service.list_archives()

        assert result.success is True
        assert len(result.archives) == 0

    @pytest.mark.asyncio
    async def test_list_archives_with_entries(self, archive_service, mock_storage):
        """Test listing archives with entries."""
        mock_storage.list_archives.return_value = [
            {
                "slot_name": "archived_1",
                "archived_at": datetime.now().isoformat(),
                "archive_reason": "cleanup",
                "entry_count": 5,
                "original_size": 10000,
                "archived_size": 6000,
                "space_saved": 4000,
                "tags": ["project"],
                "group_path": "work",
            },
            {
                "slot_name": "archived_2",
                "archived_at": (datetime.now() - timedelta(days=7)).isoformat(),
                "archive_reason": "manual",
                "entry_count": 3,
                "original_size": 5000,
                "archived_size": 3000,
                "space_saved": 2000,
                "tags": [],
                "group_path": None,
            },
        ]

        result = await archive_service.list_archives()

        assert result.success is True
        assert len(result.archives) == 2
        assert result.archives[0].slot_name == "archived_1"
        assert result.archives[1].days_ago >= 7

    @pytest.mark.asyncio
    async def test_list_archives_calculates_days_ago(self, archive_service, mock_storage):
        """Test that days_ago is calculated correctly."""
        archived_at = (datetime.now() - timedelta(days=10)).isoformat()
        mock_storage.list_archives.return_value = [
            {
                "slot_name": "old_archive",
                "archived_at": archived_at,
                "archive_reason": "old",
                "entry_count": 1,
                "original_size": 1000,
                "archived_size": 500,
                "space_saved": 500,
            },
        ]

        result = await archive_service.list_archives()

        assert result.archives[0].days_ago >= 10

    @pytest.mark.asyncio
    async def test_list_archives_error_handling(self, archive_service, mock_storage):
        """Test list archives error handling."""
        mock_storage.list_archives.side_effect = IOError("Storage error")

        result = await archive_service.list_archives()

        assert result.success is False
        assert "Storage error" in result.error


class TestArchiveServiceGetStats:
    """Tests for ArchiveService get_stats method."""

    @pytest.fixture
    def mock_storage(self):
        """Create mock storage manager."""
        storage = MagicMock()
        storage.get_archive_stats = AsyncMock()
        return storage

    @pytest.fixture
    def archive_service(self, mock_storage):
        """Create ArchiveService instance."""
        return ArchiveService(mock_storage)

    @pytest.mark.asyncio
    async def test_get_stats_success(self, archive_service, mock_storage):
        """Test successful stats retrieval."""
        mock_storage.get_archive_stats.return_value = {
            "total_archives": 10,
            "total_original_size": 100000,
            "total_archived_size": 60000,
            "total_savings": 40000,
            "savings_percentage": 40.0,
            "average_compression_ratio": 0.6,
        }

        stats = await archive_service.get_stats()

        assert stats.total_archives == 10
        assert stats.savings_percentage == 40.0

    @pytest.mark.asyncio
    async def test_get_stats_error_returns_empty(self, archive_service, mock_storage):
        """Test stats returns empty on error."""
        mock_storage.get_archive_stats.side_effect = IOError("Error")

        stats = await archive_service.get_stats()

        assert stats.total_archives == 0
        assert stats.average_compression_ratio == 1.0


class TestArchiveServiceFindCandidates:
    """Tests for ArchiveService find_candidates method."""

    @pytest.fixture
    def mock_storage(self):
        """Create mock storage manager."""
        storage = MagicMock()
        storage.find_archival_candidates = AsyncMock()
        return storage

    @pytest.fixture
    def archive_service(self, mock_storage):
        """Create ArchiveService instance."""
        return ArchiveService(mock_storage)

    @pytest.mark.asyncio
    async def test_find_candidates_empty(self, archive_service, mock_storage):
        """Test finding candidates when none exist."""
        mock_storage.find_archival_candidates.return_value = []

        result = await archive_service.find_candidates(30)

        assert result.success is True
        assert len(result.candidates) == 0
        assert result.days_inactive_threshold == 30

    @pytest.mark.asyncio
    async def test_find_candidates_with_results(self, archive_service, mock_storage):
        """Test finding candidates with results."""
        mock_storage.find_archival_candidates.return_value = [
            (
                "old_slot",
                {
                    "last_updated": "2025-12-01T10:00:00",
                    "days_inactive": 54,
                    "entry_count": 5,
                    "current_size": 5000,
                    "tags": ["old", "inactive"],
                    "group_path": "archive",
                },
            ),
        ]

        result = await archive_service.find_candidates(30)

        assert result.success is True
        assert len(result.candidates) == 1
        assert result.candidates[0].slot_name == "old_slot"
        assert result.candidates[0].days_inactive == 54

    @pytest.mark.asyncio
    async def test_find_candidates_custom_threshold(self, archive_service, mock_storage):
        """Test finding candidates with custom threshold."""
        mock_storage.find_archival_candidates.return_value = []

        result = await archive_service.find_candidates(days_inactive=60)

        assert result.days_inactive_threshold == 60
        mock_storage.find_archival_candidates.assert_called_once_with(60)

    @pytest.mark.asyncio
    async def test_find_candidates_error_handling(self, archive_service, mock_storage):
        """Test find candidates error handling."""
        mock_storage.find_archival_candidates.side_effect = IOError("Storage error")

        result = await archive_service.find_candidates(30)

        assert result.success is False
        assert "Storage error" in result.error
        assert result.days_inactive_threshold == 30

    @pytest.mark.asyncio
    async def test_find_candidates_truncates_last_updated(self, archive_service, mock_storage):
        """Test that last_updated is truncated to date only."""
        mock_storage.find_archival_candidates.return_value = [
            (
                "slot",
                {
                    "last_updated": "2025-12-01T10:30:45.123456",
                    "days_inactive": 54,
                    "entry_count": 1,
                    "current_size": 1000,
                },
            ),
        ]

        result = await archive_service.find_candidates(30)

        # Should be truncated to first 10 chars (date only)
        assert result.candidates[0].last_updated == "2025-12-01"
