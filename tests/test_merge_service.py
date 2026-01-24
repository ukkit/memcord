"""Tests for the merge service module.

Tests the MergeService business logic extracted from the server handlers
during the optimization (Phase 2).
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from memcord.models import MemoryEntry, MemorySlot
from memcord.services.merge_service import (
    MergeExecuteResult,
    MergePreviewResult,
    MergeService,
)


class MockMemorySlot:
    """Mock MemorySlot for testing."""

    def __init__(self, slot_name: str, content: str = "test content", tags: set = None, group_path: str = None):
        self.slot_name = slot_name
        self.name = slot_name  # Alias
        self.content = content
        self.tags = tags or set()
        self.group_path = group_path
        self.entries = [
            MemoryEntry(type="manual_save", content=content, timestamp=datetime.now())
        ]
        self.created_at = datetime.now()
        self.updated_at = datetime.now()


class MockMergePreview:
    """Mock merge preview for testing."""

    def __init__(
        self,
        source_slots: list = None,
        total_content_length: int = 1000,
        duplicate_content_removed: int = 100,
    ):
        self.source_slots = source_slots or ["slot1", "slot2"]
        self.total_content_length = total_content_length
        self.duplicate_content_removed = duplicate_content_removed
        self.merged_tags = {"tag1", "tag2"}
        self.merged_groups = {"group/path"}
        self.chronological_order = [
            ("slot1", datetime.now()),
            ("slot2", datetime.now()),
        ]
        self.content_preview = "Preview content..."


class MockMergeResult:
    """Mock merge result for testing."""

    def __init__(self, success: bool = True, error: str = None):
        self.success = success
        self.error = error
        self.content_length = 900
        self.duplicates_removed = 50
        self.tags_merged = {"merged_tag"}
        self.groups_merged = ["group/path"]


class TestMergePreviewResult:
    """Tests for MergePreviewResult dataclass."""

    def test_successful_preview_result(self):
        """Test creating a successful preview result."""
        result = MergePreviewResult(
            success=True,
            source_slots=["slot1", "slot2"],
            target_slot="merged",
            total_content_length=1000,
            duplicate_content_removed=100,
        )

        assert result.success is True
        assert len(result.source_slots) == 2
        assert result.target_slot == "merged"
        assert result.error is None

    def test_failed_preview_result(self):
        """Test creating a failed preview result."""
        result = MergePreviewResult(
            success=False,
            error="At least 2 source slots are required",
        )

        assert result.success is False
        assert result.error is not None

    def test_default_values(self):
        """Test default values are set correctly."""
        result = MergePreviewResult(success=True)

        assert result.source_slots == []
        assert result.target_slot == ""
        assert result.total_content_length == 0
        assert result.similarity_threshold == 0.8
        assert result.merged_tags == set()
        assert result.merged_groups == set()


class TestMergeExecuteResult:
    """Tests for MergeExecuteResult dataclass."""

    def test_successful_execute_result(self):
        """Test creating a successful execution result."""
        result = MergeExecuteResult(
            success=True,
            target_slot="merged",
            source_slots=["slot1", "slot2"],
            content_length=1000,
            duplicates_removed=50,
            merged_at=datetime.now(),
        )

        assert result.success is True
        assert result.target_slot == "merged"
        assert result.merged_at is not None

    def test_failed_execute_result(self):
        """Test creating a failed execution result."""
        result = MergeExecuteResult(
            success=False,
            error="Merge operation failed: internal error",
        )

        assert result.success is False
        assert "internal error" in result.error

    def test_deleted_sources_tracking(self):
        """Test tracking of deleted source slots."""
        result = MergeExecuteResult(
            success=True,
            target_slot="merged",
            deleted_sources=["slot1", "slot2"],
        )

        assert result.deleted_sources == ["slot1", "slot2"]


class TestMergeServiceValidation:
    """Tests for MergeService validation methods."""

    @pytest.fixture
    def mock_storage(self):
        """Create mock storage manager."""
        storage = MagicMock()
        storage.read_memory = AsyncMock()
        storage.save_memory = AsyncMock()
        storage.delete_slot = AsyncMock()
        storage._save_slot = AsyncMock()
        return storage

    @pytest.fixture
    def mock_merger(self):
        """Create mock merger."""
        merger = MagicMock()
        merger.create_merge_preview = MagicMock(return_value=MockMergePreview())
        merger.merge_slots = MagicMock(return_value=MockMergeResult())
        merger._merge_content = MagicMock(return_value="Merged content")
        return merger

    @pytest.fixture
    def merge_service(self, mock_storage, mock_merger):
        """Create MergeService instance."""
        return MergeService(mock_storage, mock_merger)

    @pytest.mark.asyncio
    async def test_validate_empty_source_slots(self, merge_service):
        """Test validation fails with empty source slots."""
        is_valid, error, sources, target = await merge_service.validate_merge_request(
            [], "target"
        )

        assert is_valid is False
        assert "At least 2 source slots" in error
        assert sources == []

    @pytest.mark.asyncio
    async def test_validate_single_source_slot(self, merge_service):
        """Test validation fails with single source slot."""
        is_valid, error, sources, target = await merge_service.validate_merge_request(
            ["only_one"], "target"
        )

        assert is_valid is False
        assert "At least 2 source slots" in error

    @pytest.mark.asyncio
    async def test_validate_empty_target(self, merge_service):
        """Test validation fails with empty target."""
        is_valid, error, sources, target = await merge_service.validate_merge_request(
            ["slot1", "slot2"], ""
        )

        assert is_valid is False
        assert "Target slot name cannot be empty" in error

    @pytest.mark.asyncio
    async def test_validate_whitespace_target(self, merge_service):
        """Test validation fails with whitespace-only target."""
        is_valid, error, sources, target = await merge_service.validate_merge_request(
            ["slot1", "slot2"], "   "
        )

        assert is_valid is False
        assert "Target slot name cannot be empty" in error

    @pytest.mark.asyncio
    async def test_validate_cleans_slot_names(self, merge_service):
        """Test validation cleans slot names."""
        is_valid, error, sources, target = await merge_service.validate_merge_request(
            ["  slot1  ", "slot2  ", ""], "target name"
        )

        assert is_valid is True
        assert sources == ["slot1", "slot2"]
        assert target == "target_name"  # spaces replaced with underscores

    @pytest.mark.asyncio
    async def test_validate_valid_request(self, merge_service):
        """Test validation passes with valid request."""
        is_valid, error, sources, target = await merge_service.validate_merge_request(
            ["slot1", "slot2", "slot3"], "merged"
        )

        assert is_valid is True
        assert error is None
        assert sources == ["slot1", "slot2", "slot3"]
        assert target == "merged"


class TestMergeServiceLoadSlots:
    """Tests for MergeService slot loading."""

    @pytest.fixture
    def mock_storage(self):
        """Create mock storage manager."""
        storage = MagicMock()
        storage.read_memory = AsyncMock()
        return storage

    @pytest.fixture
    def mock_merger(self):
        """Create mock merger."""
        return MagicMock()

    @pytest.fixture
    def merge_service(self, mock_storage, mock_merger):
        """Create MergeService instance."""
        return MergeService(mock_storage, mock_merger)

    @pytest.mark.asyncio
    async def test_load_all_slots_found(self, merge_service, mock_storage):
        """Test loading slots when all exist."""
        mock_storage.read_memory.side_effect = [
            MockMemorySlot("slot1"),
            MockMemorySlot("slot2"),
        ]

        slots, missing = await merge_service.load_source_slots(["slot1", "slot2"])

        assert len(slots) == 2
        assert len(missing) == 0

    @pytest.mark.asyncio
    async def test_load_some_slots_missing(self, merge_service, mock_storage):
        """Test loading slots when some are missing."""
        mock_storage.read_memory.side_effect = [
            MockMemorySlot("slot1"),
            None,  # slot2 not found
        ]

        slots, missing = await merge_service.load_source_slots(["slot1", "slot2"])

        assert len(slots) == 1
        assert missing == ["slot2"]

    @pytest.mark.asyncio
    async def test_load_all_slots_missing(self, merge_service, mock_storage):
        """Test loading slots when all are missing."""
        mock_storage.read_memory.return_value = None

        slots, missing = await merge_service.load_source_slots(["slot1", "slot2"])

        assert len(slots) == 0
        assert missing == ["slot1", "slot2"]


class TestMergeServicePreview:
    """Tests for MergeService preview operation."""

    @pytest.fixture
    def mock_storage(self):
        """Create mock storage manager."""
        storage = MagicMock()
        storage.read_memory = AsyncMock()
        return storage

    @pytest.fixture
    def mock_merger(self):
        """Create mock merger."""
        merger = MagicMock()
        merger.create_merge_preview = MagicMock(return_value=MockMergePreview())
        return merger

    @pytest.fixture
    def merge_service(self, mock_storage, mock_merger):
        """Create MergeService instance."""
        return MergeService(mock_storage, mock_merger)

    @pytest.mark.asyncio
    async def test_preview_validation_fails(self, merge_service):
        """Test preview returns error on validation failure."""
        result = await merge_service.preview_merge(["slot1"], "target", 0.8)

        assert result.success is False
        assert "At least 2 source slots" in result.error

    @pytest.mark.asyncio
    async def test_preview_missing_slots(self, merge_service, mock_storage):
        """Test preview returns error when slots missing."""
        mock_storage.read_memory.side_effect = [
            MockMemorySlot("slot1"),
            None,  # slot2 not found
        ]

        result = await merge_service.preview_merge(["slot1", "slot2"], "target", 0.8)

        assert result.success is False
        assert "not found" in result.error
        assert "slot2" in result.error

    @pytest.mark.asyncio
    async def test_preview_success(self, merge_service, mock_storage, mock_merger):
        """Test successful preview generation."""
        mock_storage.read_memory.side_effect = [
            MockMemorySlot("slot1", content="Content 1"),
            MockMemorySlot("slot2", content="Content 2"),
            None,  # target doesn't exist
        ]

        result = await merge_service.preview_merge(["slot1", "slot2"], "merged", 0.8)

        assert result.success is True
        assert result.target_slot == "merged"
        assert result.target_exists is False
        mock_merger.create_merge_preview.assert_called_once()

    @pytest.mark.asyncio
    async def test_preview_target_exists(self, merge_service, mock_storage, mock_merger):
        """Test preview shows target exists."""
        mock_storage.read_memory.side_effect = [
            MockMemorySlot("slot1"),
            MockMemorySlot("slot2"),
            MockMemorySlot("merged"),  # target exists
        ]

        result = await merge_service.preview_merge(["slot1", "slot2"], "merged", 0.8)

        assert result.success is True
        assert result.target_exists is True

    @pytest.mark.asyncio
    async def test_preview_merger_error(self, merge_service, mock_storage, mock_merger):
        """Test preview handles merger errors."""
        mock_storage.read_memory.side_effect = [
            MockMemorySlot("slot1"),
            MockMemorySlot("slot2"),
            None,
        ]
        mock_merger.create_merge_preview.side_effect = ValueError("Merger error")

        result = await merge_service.preview_merge(["slot1", "slot2"], "merged", 0.8)

        assert result.success is False
        assert "Merge preview failed" in result.error
        assert result.debug_info is not None


class TestMergeServiceExecute:
    """Tests for MergeService execution operation."""

    @pytest.fixture
    def mock_storage(self):
        """Create mock storage manager."""
        storage = MagicMock()
        storage.read_memory = AsyncMock()
        storage.save_memory = AsyncMock(
            return_value=MemoryEntry(type="manual_save", content="merged")
        )
        storage.delete_slot = AsyncMock(return_value=True)
        storage._save_slot = AsyncMock()
        return storage

    @pytest.fixture
    def mock_merger(self):
        """Create mock merger."""
        merger = MagicMock()
        merger.merge_slots = MagicMock(return_value=MockMergeResult())
        merger._merge_content = MagicMock(return_value="Merged content here")
        return merger

    @pytest.fixture
    def merge_service(self, mock_storage, mock_merger):
        """Create MergeService instance."""
        return MergeService(mock_storage, mock_merger)

    @pytest.mark.asyncio
    async def test_execute_validation_fails(self, merge_service):
        """Test execute returns error on validation failure."""
        result = await merge_service.execute_merge(["slot1"], "target")

        assert result.success is False
        assert "At least 2 source slots" in result.error

    @pytest.mark.asyncio
    async def test_execute_missing_slots(self, merge_service, mock_storage):
        """Test execute returns error when slots missing."""
        mock_storage.read_memory.side_effect = [
            MockMemorySlot("slot1"),
            None,
        ]

        result = await merge_service.execute_merge(["slot1", "slot2"], "target")

        assert result.success is False
        assert "not found" in result.error

    @pytest.mark.asyncio
    async def test_execute_success(self, merge_service, mock_storage, mock_merger):
        """Test successful merge execution."""
        slot1 = MockMemorySlot("slot1", tags={"tag1"})
        slot2 = MockMemorySlot("slot2", tags={"tag2"})

        mock_storage.read_memory.side_effect = [
            slot1,
            slot2,
            MockMemorySlot("merged"),  # After save
        ]

        result = await merge_service.execute_merge(["slot1", "slot2"], "merged")

        assert result.success is True
        assert result.target_slot == "merged"
        assert result.content_length == 900
        assert result.duplicates_removed == 50
        mock_storage.save_memory.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_with_delete_sources(self, merge_service, mock_storage, mock_merger):
        """Test merge execution with source deletion."""
        mock_storage.read_memory.side_effect = [
            MockMemorySlot("slot1"),
            MockMemorySlot("slot2"),
            MockMemorySlot("merged"),
        ]

        result = await merge_service.execute_merge(
            ["slot1", "slot2"], "merged", delete_sources=True
        )

        assert result.success is True
        assert "slot1" in result.deleted_sources
        assert "slot2" in result.deleted_sources
        assert mock_storage.delete_slot.call_count == 2

    @pytest.mark.asyncio
    async def test_execute_delete_partial_failure(self, merge_service, mock_storage, mock_merger):
        """Test merge handles partial deletion failures."""
        mock_storage.read_memory.side_effect = [
            MockMemorySlot("slot1"),
            MockMemorySlot("slot2"),
            MockMemorySlot("merged"),
        ]
        # First delete succeeds, second fails
        mock_storage.delete_slot.side_effect = [True, Exception("Delete failed")]

        result = await merge_service.execute_merge(
            ["slot1", "slot2"], "merged", delete_sources=True
        )

        assert result.success is True
        assert "slot1" in result.deleted_sources
        assert "slot2" not in result.deleted_sources

    @pytest.mark.asyncio
    async def test_execute_merger_failure(self, merge_service, mock_storage, mock_merger):
        """Test execute handles merger failure."""
        mock_storage.read_memory.side_effect = [
            MockMemorySlot("slot1"),
            MockMemorySlot("slot2"),
        ]
        mock_merger.merge_slots.return_value = MockMergeResult(
            success=False, error="Merge conflict"
        )

        result = await merge_service.execute_merge(["slot1", "slot2"], "merged")

        assert result.success is False
        assert "Merge conflict" in result.error

    @pytest.mark.asyncio
    async def test_execute_custom_similarity_threshold(self, merge_service, mock_storage, mock_merger):
        """Test execute uses custom similarity threshold."""
        mock_storage.read_memory.side_effect = [
            MockMemorySlot("slot1"),
            MockMemorySlot("slot2"),
            MockMemorySlot("merged"),
        ]

        await merge_service.execute_merge(
            ["slot1", "slot2"], "merged", similarity_threshold=0.5
        )

        # Verify merger was called with custom threshold
        call_args = mock_merger.merge_slots.call_args
        assert call_args[0][2] == 0.5  # Third positional argument is threshold


class TestMergeServiceDebugInfo:
    """Tests for MergeService debug info building."""

    @pytest.fixture
    def merge_service(self):
        """Create MergeService instance."""
        return MergeService(MagicMock(), MagicMock())

    def test_build_debug_info_includes_traceback(self, merge_service):
        """Test debug info includes traceback."""
        slots = [MockMemorySlot("test_slot")]
        error = ValueError("Test error")

        debug_info = merge_service._build_debug_info(slots, error)

        assert "traceback" in debug_info.lower() or "Traceback" in debug_info
        assert "Debug info" in debug_info

    def test_build_debug_info_includes_slot_info(self, merge_service):
        """Test debug info includes slot information."""
        slots = [
            MockMemorySlot("slot1", content="Content 1"),
            MockMemorySlot("slot2", content="Content 2"),
        ]
        error = ValueError("Test error")

        debug_info = merge_service._build_debug_info(slots, error)

        assert "slot1" in debug_info
        assert "slot2" in debug_info
        assert "entries_count" in debug_info
