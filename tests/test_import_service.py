"""Tests for the import service module.

Tests the ImportService business logic extracted from the server handlers
during the optimization (Phase 2).
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from memcord.models import MemoryEntry, MemorySlot
from memcord.services.import_service import ImportResult, ImportService


class MockImportResult:
    """Mock result from ContentImporter."""

    def __init__(
        self,
        success: bool = True,
        content: str = "Imported content here",
        source_type: str = "file",
        source_location: str = "/path/to/file.txt",
        error: str = None,
    ):
        self.success = success
        self.content = content
        self.source_type = source_type
        self.source_location = source_location
        self.error = error
        self.metadata = {
            "imported_at": datetime.now().isoformat(),
            "file_size": len(content) if content else 0,
        }


class MockMemorySlot:
    """Mock MemorySlot for testing."""

    def __init__(self, slot_name: str, tags: list = None, group_path: str = None, description: str = None):
        self.slot_name = slot_name
        self.tags = tags or []
        self.group_path = group_path
        self.description = description
        self.entries = []


class TestImportResult:
    """Tests for ImportResult dataclass."""

    def test_successful_import_result(self):
        """Test creating a successful import result."""
        result = ImportResult(
            success=True,
            slot_name="my_slot",
            source="file.txt",
            source_type="file",
            content_length=1000,
            timestamp=datetime.now(),
        )

        assert result.success is True
        assert result.slot_name == "my_slot"
        assert result.error is None

    def test_failed_import_result(self):
        """Test creating a failed import result."""
        result = ImportResult(
            success=False,
            source="invalid.txt",
            error="File not found",
        )

        assert result.success is False
        assert result.error == "File not found"

    def test_default_values(self):
        """Test default values are set correctly."""
        result = ImportResult(success=True)

        assert result.slot_name == ""
        assert result.source == ""
        assert result.source_type == ""
        assert result.content_length == 0
        assert result.tags_applied == []
        assert result.metadata == {}

    def test_with_tags_and_group(self):
        """Test result with tags and group path."""
        result = ImportResult(
            success=True,
            slot_name="test",
            tags_applied=["tag1", "tag2"],
            group_path="project/docs",
        )

        assert result.tags_applied == ["tag1", "tag2"]
        assert result.group_path == "project/docs"


class TestImportServiceValidation:
    """Tests for ImportService input validation."""

    @pytest.fixture
    def mock_storage(self):
        """Create mock storage manager."""
        storage = MagicMock()
        storage.save_memory = AsyncMock(
            return_value=MemoryEntry(type="manual_save", content="test")
        )
        storage.read_memory = AsyncMock()
        storage._save_slot = AsyncMock()
        return storage

    @pytest.fixture
    def mock_importer(self):
        """Create mock content importer."""
        importer = MagicMock()
        importer.import_content = AsyncMock(return_value=MockImportResult())
        return importer

    @pytest.fixture
    def import_service(self, mock_storage, mock_importer):
        """Create ImportService instance."""
        return ImportService(mock_storage, mock_importer)

    @pytest.mark.asyncio
    async def test_empty_source_returns_error(self, import_service):
        """Test empty source returns error."""
        result = await import_service.import_content("", "slot_name")

        assert result.success is False
        assert "Source cannot be empty" in result.error

    @pytest.mark.asyncio
    async def test_whitespace_source_returns_error(self, import_service):
        """Test whitespace-only source returns error."""
        result = await import_service.import_content("   ", "slot_name")

        assert result.success is False
        assert "Source cannot be empty" in result.error

    @pytest.mark.asyncio
    async def test_no_slot_name_returns_error(self, import_service):
        """Test missing slot name returns error."""
        result = await import_service.import_content("/path/to/file.txt", "")

        assert result.success is False
        assert "No memory slot selected" in result.error

    @pytest.mark.asyncio
    async def test_none_slot_name_returns_error(self, import_service):
        """Test None slot name returns error."""
        result = await import_service.import_content("/path/to/file.txt", None)

        assert result.success is False
        assert "No memory slot selected" in result.error


class TestImportServiceFileImport:
    """Tests for ImportService file import functionality."""

    @pytest.fixture
    def mock_storage(self):
        """Create mock storage manager."""
        storage = MagicMock()
        storage.save_memory = AsyncMock(
            return_value=MemoryEntry(type="manual_save", content="test", timestamp=datetime.now())
        )
        storage.read_memory = AsyncMock(return_value=None)
        storage._save_slot = AsyncMock()
        return storage

    @pytest.fixture
    def mock_importer(self):
        """Create mock content importer."""
        importer = MagicMock()
        importer.import_content = AsyncMock(
            return_value=MockImportResult(
                success=True,
                content="File content here",
                source_type="file",
                source_location="/path/to/file.txt",
            )
        )
        return importer

    @pytest.fixture
    def import_service(self, mock_storage, mock_importer):
        """Create ImportService instance."""
        return ImportService(mock_storage, mock_importer)

    @pytest.mark.asyncio
    async def test_successful_file_import(self, import_service, mock_importer):
        """Test successful file import."""
        result = await import_service.import_content(
            "/path/to/file.txt", "my_slot"
        )

        assert result.success is True
        assert result.slot_name == "my_slot"
        assert result.source_type == "file"
        assert result.content_length > 0
        mock_importer.import_content.assert_called_once_with("/path/to/file.txt")

    @pytest.mark.asyncio
    async def test_import_strips_source_whitespace(self, import_service, mock_importer):
        """Test source path is stripped of whitespace."""
        await import_service.import_content(
            "  /path/to/file.txt  ", "my_slot"
        )

        mock_importer.import_content.assert_called_once_with("/path/to/file.txt")

    @pytest.mark.asyncio
    async def test_import_with_description(self, import_service, mock_storage):
        """Test import with description."""
        result = await import_service.import_content(
            "/path/to/file.txt",
            "my_slot",
            description="Important document",
        )

        assert result.success is True
        # Check that save_memory was called with content containing description
        call_args = mock_storage.save_memory.call_args
        saved_content = call_args[0][1]
        assert "Description: Important document" in saved_content

    @pytest.mark.asyncio
    async def test_import_content_header(self, import_service, mock_storage):
        """Test import adds proper header to content."""
        await import_service.import_content("/path/to/file.txt", "my_slot")

        call_args = mock_storage.save_memory.call_args
        saved_content = call_args[0][1]

        assert "=== IMPORTED CONTENT ===" in saved_content
        assert "Source:" in saved_content
        assert "Type:" in saved_content
        assert "Imported:" in saved_content


class TestImportServiceMetadata:
    """Tests for ImportService metadata handling."""

    @pytest.fixture
    def mock_storage(self):
        """Create mock storage manager."""
        storage = MagicMock()
        storage.save_memory = AsyncMock(
            return_value=MemoryEntry(type="manual_save", content="test", timestamp=datetime.now())
        )
        storage.read_memory = AsyncMock()
        storage._save_slot = AsyncMock()
        return storage

    @pytest.fixture
    def mock_importer(self):
        """Create mock content importer."""
        importer = MagicMock()
        importer.import_content = AsyncMock(return_value=MockImportResult())
        return importer

    @pytest.fixture
    def import_service(self, mock_storage, mock_importer):
        """Create ImportService instance."""
        return ImportService(mock_storage, mock_importer)

    @pytest.mark.asyncio
    async def test_import_with_tags(self, import_service, mock_storage):
        """Test import applies tags to slot."""
        mock_slot = MockMemorySlot("my_slot", tags=[])
        mock_storage.read_memory.return_value = mock_slot

        result = await import_service.import_content(
            "/path/to/file.txt",
            "my_slot",
            tags=["imported", "document"],
        )

        assert result.success is True
        assert result.tags_applied == ["imported", "document"]
        mock_storage._save_slot.assert_called_once()

    @pytest.mark.asyncio
    async def test_import_merges_existing_tags(self, import_service, mock_storage):
        """Test import merges with existing tags."""
        mock_slot = MockMemorySlot("my_slot", tags=["existing"])
        mock_storage.read_memory.return_value = mock_slot

        await import_service.import_content(
            "/path/to/file.txt",
            "my_slot",
            tags=["new_tag"],
        )

        # Slot should have both tags
        assert "existing" in mock_slot.tags
        assert "new_tag" in mock_slot.tags

    @pytest.mark.asyncio
    async def test_import_with_group_path(self, import_service, mock_storage):
        """Test import sets group path."""
        mock_slot = MockMemorySlot("my_slot")
        mock_storage.read_memory.return_value = mock_slot

        result = await import_service.import_content(
            "/path/to/file.txt",
            "my_slot",
            group_path="project/docs",
        )

        assert result.success is True
        assert result.group_path == "project/docs"
        assert mock_slot.group_path == "project/docs"

    @pytest.mark.asyncio
    async def test_import_sets_description_if_empty(self, import_service, mock_storage):
        """Test import sets description on slot if empty.

        Note: Description is only set when metadata (tags/group_path) is provided,
        because the service only reads and updates the slot when applying metadata.
        """
        mock_slot = MockMemorySlot("my_slot", description=None)
        mock_storage.read_memory.return_value = mock_slot

        # Must provide tags or group_path to trigger the metadata update path
        await import_service.import_content(
            "/path/to/file.txt",
            "my_slot",
            description="New description",
            tags=["test"],  # Triggers metadata update
        )

        # Verify _save_slot was called
        mock_storage._save_slot.assert_called_once()
        # The description should be set on the slot object
        assert mock_slot.description == "New description"

    @pytest.mark.asyncio
    async def test_import_preserves_existing_description(self, import_service, mock_storage):
        """Test import does not overwrite existing description."""
        mock_slot = MockMemorySlot("my_slot", description="Original description")
        mock_storage.read_memory.return_value = mock_slot

        await import_service.import_content(
            "/path/to/file.txt",
            "my_slot",
            description="New description",
        )

        assert mock_slot.description == "Original description"


class TestImportServiceErrorHandling:
    """Tests for ImportService error handling."""

    @pytest.fixture
    def mock_storage(self):
        """Create mock storage manager."""
        storage = MagicMock()
        storage.save_memory = AsyncMock()
        storage.read_memory = AsyncMock()
        storage._save_slot = AsyncMock()
        return storage

    @pytest.fixture
    def mock_importer(self):
        """Create mock content importer."""
        return MagicMock()

    @pytest.fixture
    def import_service(self, mock_storage, mock_importer):
        """Create ImportService instance."""
        return ImportService(mock_storage, mock_importer)

    @pytest.mark.asyncio
    async def test_importer_failure(self, import_service, mock_importer):
        """Test handling of importer failure."""
        mock_importer.import_content = AsyncMock(
            return_value=MockImportResult(
                success=False,
                error="File not found",
            )
        )

        result = await import_service.import_content("/invalid/path.txt", "my_slot")

        assert result.success is False
        assert "Import failed" in result.error
        assert "File not found" in result.error

    @pytest.mark.asyncio
    async def test_storage_exception(self, import_service, mock_storage, mock_importer):
        """Test handling of storage exceptions."""
        mock_importer.import_content = AsyncMock(return_value=MockImportResult())
        mock_storage.save_memory.side_effect = IOError("Disk full")

        result = await import_service.import_content("/path/to/file.txt", "my_slot")

        assert result.success is False
        assert "Disk full" in result.error

    @pytest.mark.asyncio
    async def test_importer_exception(self, import_service, mock_importer):
        """Test handling of importer exceptions."""
        mock_importer.import_content = AsyncMock(side_effect=RuntimeError("Network error"))

        result = await import_service.import_content("https://example.com", "my_slot")

        assert result.success is False
        assert "Network error" in result.error


class TestImportServiceSourceTypes:
    """Tests for different source types (file, URL, clipboard)."""

    @pytest.fixture
    def mock_storage(self):
        """Create mock storage manager."""
        storage = MagicMock()
        storage.save_memory = AsyncMock(
            return_value=MemoryEntry(type="manual_save", content="test", timestamp=datetime.now())
        )
        storage.read_memory = AsyncMock(return_value=None)
        storage._save_slot = AsyncMock()
        return storage

    @pytest.fixture
    def mock_importer(self):
        """Create mock content importer."""
        return MagicMock()

    @pytest.fixture
    def import_service(self, mock_storage, mock_importer):
        """Create ImportService instance."""
        return ImportService(mock_storage, mock_importer)

    @pytest.mark.asyncio
    async def test_url_import(self, import_service, mock_importer):
        """Test URL import."""
        mock_importer.import_content = AsyncMock(
            return_value=MockImportResult(
                success=True,
                content="<html>Page content</html>",
                source_type="url",
                source_location="https://example.com",
            )
        )

        result = await import_service.import_content("https://example.com", "my_slot")

        assert result.success is True
        assert result.source_type == "url"

    @pytest.mark.asyncio
    async def test_clipboard_import(self, import_service, mock_importer):
        """Test clipboard import (source = '-')."""
        mock_importer.import_content = AsyncMock(
            return_value=MockImportResult(
                success=True,
                content="Clipboard content",
                source_type="clipboard",
                source_location=None,
            )
        )

        result = await import_service.import_content("-", "my_slot")

        assert result.success is True
        assert result.source_type == "clipboard"
        mock_importer.import_content.assert_called_once_with("-")

    @pytest.mark.asyncio
    async def test_result_includes_metadata(self, import_service, mock_importer):
        """Test result includes import metadata."""
        mock_importer.import_content = AsyncMock(
            return_value=MockImportResult(
                success=True,
                content="Content",
                source_type="file",
            )
        )

        result = await import_service.import_content("/path/file.txt", "my_slot")

        assert result.success is True
        assert "imported_at" in result.metadata
        assert result.file_size is not None
