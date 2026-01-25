"""Tests for the compression service module.

Tests the CompressionService business logic extracted from the server handlers
during the optimization (Phase 2).
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from memcord.services.compression_service import (
    BulkCompressionResult,
    CompressionAnalysis,
    CompressionResult,
    CompressionService,
    CompressionStats,
    DecompressionResult,
)


class MockMemorySlot:
    """Mock MemorySlot for testing."""

    def __init__(self, slot_name: str, content: str = "test content"):
        self.slot_name = slot_name
        self.content = content
        self.entries = []

    def model_dump(self):
        return {
            "slot_name": self.slot_name,
            "content": self.content,
            "entries": [],
        }


class TestCompressionStats:
    """Tests for CompressionStats dataclass."""

    def test_slot_specific_stats(self):
        """Test creating slot-specific compression stats."""
        stats = CompressionStats(
            slot_name="my_slot",
            total_entries=10,
            compressed_entries=8,
            compression_percentage=80.0,
            total_original_size=10000,
            total_compressed_size=6000,
            space_saved=4000,
            space_saved_percentage=40.0,
            compression_ratio=0.6,
        )

        assert stats.slot_name == "my_slot"
        assert stats.total_entries == 10
        assert stats.compressed_entries == 8
        assert stats.space_saved == 4000

    def test_global_stats(self):
        """Test creating global compression stats."""
        stats = CompressionStats(
            total_slots=5,
            total_entries=50,
            compressed_entries=40,
            total_original_size=50000,
            total_compressed_size=30000,
            space_saved=20000,
        )

        assert stats.slot_name is None
        assert stats.total_slots == 5
        assert stats.total_entries == 50

    def test_default_values(self):
        """Test default values are set correctly."""
        stats = CompressionStats()

        assert stats.slot_name is None
        assert stats.total_entries == 0
        assert stats.compression_ratio == 1.0
        assert stats.total_slots == 0


class TestCompressionResult:
    """Tests for CompressionResult dataclass."""

    def test_successful_result(self):
        """Test creating a successful compression result."""
        result = CompressionResult(
            success=True,
            slot_name="my_slot",
            entries_processed=10,
            entries_compressed=8,
            original_size=10000,
            compressed_size=6000,
            space_saved=4000,
            compression_ratio=0.6,
        )

        assert result.success is True
        assert result.slot_name == "my_slot"
        assert result.error is None

    def test_failed_result(self):
        """Test creating a failed compression result."""
        result = CompressionResult(
            success=False,
            slot_name="my_slot",
            error="Compression algorithm failed",
        )

        assert result.success is False
        assert result.error is not None


class TestBulkCompressionResult:
    """Tests for BulkCompressionResult dataclass."""

    def test_successful_bulk_result(self):
        """Test creating a successful bulk compression result."""
        result = BulkCompressionResult(
            success=True,
            slots_processed=5,
            total_entries_processed=50,
            total_entries_compressed=40,
            total_original_size=50000,
            total_compressed_size=30000,
            total_space_saved=20000,
            overall_compression_ratio=0.6,
        )

        assert result.success is True
        assert result.slots_processed == 5
        assert result.total_space_saved == 20000

    def test_default_values(self):
        """Test default values for bulk result."""
        result = BulkCompressionResult(success=True)

        assert result.slots_processed == 0
        assert result.overall_compression_ratio == 1.0


class TestDecompressionResult:
    """Tests for DecompressionResult dataclass."""

    def test_successful_decompression(self):
        """Test creating a successful decompression result."""
        result = DecompressionResult(
            success=True,
            slot_name="my_slot",
            entries_processed=10,
            entries_decompressed=10,
        )

        assert result.success is True
        assert result.decompressed_successfully is True

    def test_failed_decompression(self):
        """Test creating a failed decompression result."""
        result = DecompressionResult(
            success=False,
            slot_name="my_slot",
            error="Corrupted data",
        )

        assert result.success is False
        assert result.error == "Corrupted data"


class TestCompressionAnalysis:
    """Tests for CompressionAnalysis dataclass."""

    def test_successful_analysis(self):
        """Test creating a successful analysis result."""
        result = CompressionAnalysis(
            success=True,
            report="Compression analysis report...",
        )

        assert result.success is True
        assert "analysis" in result.report.lower()

    def test_failed_analysis(self):
        """Test creating a failed analysis result."""
        result = CompressionAnalysis(
            success=False,
            error="Analysis failed",
        )

        assert result.success is False


class TestCompressionServiceStats:
    """Tests for CompressionService statistics methods."""

    @pytest.fixture
    def mock_storage(self):
        """Create mock storage manager."""
        storage = MagicMock()
        storage.get_compression_stats = AsyncMock()
        storage.read_memory = AsyncMock()
        storage.list_memory_slots = AsyncMock()
        storage.compress_slot = AsyncMock()
        storage.decompress_slot = AsyncMock()
        return storage

    @pytest.fixture
    def compression_service(self, mock_storage):
        """Create CompressionService instance."""
        return CompressionService(mock_storage)

    @pytest.mark.asyncio
    async def test_get_stats_single_slot(self, compression_service, mock_storage):
        """Test getting stats for a single slot."""
        mock_storage.get_compression_stats.return_value = {
            "total_entries": 10,
            "compressed_entries": 8,
            "compression_percentage": 80.0,
            "total_original_size": 10000,
            "total_compressed_size": 6000,
            "space_saved": 4000,
            "space_saved_percentage": 40.0,
            "compression_ratio": 0.6,
        }

        stats = await compression_service.get_stats("my_slot")

        assert stats.slot_name == "my_slot"
        assert stats.total_entries == 10
        assert stats.compressed_entries == 8
        mock_storage.get_compression_stats.assert_called_once_with("my_slot")

    @pytest.mark.asyncio
    async def test_get_stats_global(self, compression_service, mock_storage):
        """Test getting global compression stats."""
        mock_storage.get_compression_stats.return_value = {
            "total_slots": 5,
            "total_entries": 50,
            "compressed_entries": 40,
            "total_original_size": 50000,
            "total_compressed_size": 30000,
            "space_saved": 20000,
            "space_saved_percentage": 40.0,
            "compression_ratio": 0.6,
        }

        stats = await compression_service.get_stats(None)

        assert stats.slot_name is None
        assert stats.total_slots == 5
        assert stats.total_entries == 50
        mock_storage.get_compression_stats.assert_called_once_with(None)


class TestCompressionServiceAnalyze:
    """Tests for CompressionService analyze method."""

    @pytest.fixture
    def mock_storage(self):
        """Create mock storage manager."""
        storage = MagicMock()
        storage.read_memory = AsyncMock()
        storage.list_memory_slots = AsyncMock()
        return storage

    @pytest.fixture
    def compression_service(self, mock_storage):
        """Create CompressionService instance."""
        return CompressionService(mock_storage)

    @pytest.mark.asyncio
    async def test_analyze_single_slot(self, compression_service, mock_storage):
        """Test analyzing a single slot."""
        mock_slot = MockMemorySlot("my_slot", content="Test content")
        mock_storage.read_memory.return_value = mock_slot

        # Patch at the import location (inside the analyze method)
        with patch("memcord.compression.ContentCompressor") as MockCompressor:
            with patch("memcord.compression.format_compression_report") as mock_format:
                mock_compressor = MockCompressor.return_value
                mock_compressor.get_compression_stats.return_value = {"some": "stats"}
                mock_format.return_value = "Compression report for my_slot"

                result = await compression_service.analyze("my_slot")

        assert result.success is True
        assert "my_slot" in result.report

    @pytest.mark.asyncio
    async def test_analyze_slot_not_found(self, compression_service, mock_storage):
        """Test analyzing a non-existent slot."""
        mock_storage.read_memory.return_value = None

        result = await compression_service.analyze("nonexistent")

        assert result.success is False
        assert "not found" in result.error

    @pytest.mark.asyncio
    async def test_analyze_all_slots(self, compression_service, mock_storage):
        """Test analyzing all slots."""
        mock_storage.list_memory_slots.return_value = [
            {"name": "slot1"},
            {"name": "slot2"},
        ]
        mock_storage.read_memory.side_effect = [
            MockMemorySlot("slot1"),
            MockMemorySlot("slot2"),
        ]

        # Patch at the import location (inside the analyze method)
        with patch("memcord.compression.ContentCompressor") as MockCompressor:
            with patch("memcord.compression.format_compression_report") as mock_format:
                mock_compressor = MockCompressor.return_value
                mock_compressor.get_compression_stats.return_value = {"some": "stats"}
                mock_format.return_value = "Global compression report"

                result = await compression_service.analyze(None)

        assert result.success is True
        assert mock_storage.list_memory_slots.called

    @pytest.mark.asyncio
    async def test_analyze_exception_handling(self, compression_service, mock_storage):
        """Test analyze handles exceptions."""
        mock_storage.read_memory.side_effect = OSError("Read error")

        result = await compression_service.analyze("my_slot")

        assert result.success is False
        assert "Read error" in result.error


class TestCompressionServiceCompress:
    """Tests for CompressionService compress methods."""

    @pytest.fixture
    def mock_storage(self):
        """Create mock storage manager."""
        storage = MagicMock()
        storage.compress_slot = AsyncMock()
        storage.list_memory_slots = AsyncMock()
        return storage

    @pytest.fixture
    def compression_service(self, mock_storage):
        """Create CompressionService instance."""
        return CompressionService(mock_storage)

    @pytest.mark.asyncio
    async def test_compress_slot_success(self, compression_service, mock_storage):
        """Test successful single slot compression."""
        mock_storage.compress_slot.return_value = {
            "entries_processed": 10,
            "entries_compressed": 8,
            "original_size": 10000,
            "compressed_size": 6000,
            "space_saved": 4000,
            "compression_ratio": 0.6,
        }

        result = await compression_service.compress_slot("my_slot")

        assert result.success is True
        assert result.slot_name == "my_slot"
        assert result.entries_compressed == 8
        assert result.space_saved == 4000
        mock_storage.compress_slot.assert_called_once_with("my_slot", False)

    @pytest.mark.asyncio
    async def test_compress_slot_with_force(self, compression_service, mock_storage):
        """Test compression with force flag."""
        mock_storage.compress_slot.return_value = {
            "entries_processed": 10,
            "entries_compressed": 10,
        }

        await compression_service.compress_slot("my_slot", force=True)

        mock_storage.compress_slot.assert_called_once_with("my_slot", True)

    @pytest.mark.asyncio
    async def test_compress_slot_error(self, compression_service, mock_storage):
        """Test compression error handling."""
        mock_storage.compress_slot.side_effect = ValueError("Compression failed")

        result = await compression_service.compress_slot("my_slot")

        assert result.success is False
        assert "Compression failed" in result.error

    @pytest.mark.asyncio
    async def test_compress_all_slots(self, compression_service, mock_storage):
        """Test compressing all slots."""
        mock_storage.list_memory_slots.return_value = [
            {"name": "slot1"},
            {"name": "slot2"},
            {"name": "slot3"},
        ]
        mock_storage.compress_slot.return_value = {
            "entries_processed": 10,
            "entries_compressed": 8,
            "original_size": 5000,
            "compressed_size": 3000,
            "space_saved": 2000,
        }

        result = await compression_service.compress_all_slots()

        assert result.success is True
        assert result.slots_processed == 3
        assert result.total_space_saved == 6000  # 2000 * 3
        assert mock_storage.compress_slot.call_count == 3

    @pytest.mark.asyncio
    async def test_compress_all_slots_partial_failure(self, compression_service, mock_storage):
        """Test bulk compression handles partial failures."""
        mock_storage.list_memory_slots.return_value = [
            {"name": "slot1"},
            {"name": "slot2"},
        ]
        mock_storage.compress_slot.side_effect = [
            {
                "entries_processed": 10,
                "entries_compressed": 8,
                "original_size": 5000,
                "compressed_size": 3000,
                "space_saved": 2000,
            },
            Exception("Failed"),
        ]

        result = await compression_service.compress_all_slots()

        assert result.success is True
        assert result.slots_processed == 1  # Only one succeeded

    @pytest.mark.asyncio
    async def test_compress_all_slots_overall_ratio(self, compression_service, mock_storage):
        """Test overall compression ratio calculation."""
        mock_storage.list_memory_slots.return_value = [{"name": "slot1"}]
        mock_storage.compress_slot.return_value = {
            "entries_processed": 10,
            "entries_compressed": 10,
            "original_size": 10000,
            "compressed_size": 4000,
            "space_saved": 6000,
        }

        result = await compression_service.compress_all_slots()

        assert result.overall_compression_ratio == 0.4  # 4000 / 10000


class TestCompressionServiceDecompress:
    """Tests for CompressionService decompress method."""

    @pytest.fixture
    def mock_storage(self):
        """Create mock storage manager."""
        storage = MagicMock()
        storage.decompress_slot = AsyncMock()
        return storage

    @pytest.fixture
    def compression_service(self, mock_storage):
        """Create CompressionService instance."""
        return CompressionService(mock_storage)

    @pytest.mark.asyncio
    async def test_decompress_slot_success(self, compression_service, mock_storage):
        """Test successful decompression."""
        mock_storage.decompress_slot.return_value = {
            "entries_processed": 10,
            "entries_decompressed": 10,
            "decompressed_successfully": True,
        }

        result = await compression_service.decompress_slot("my_slot")

        assert result.success is True
        assert result.slot_name == "my_slot"
        assert result.entries_decompressed == 10

    @pytest.mark.asyncio
    async def test_decompress_empty_slot_name(self, compression_service):
        """Test decompression with empty slot name."""
        result = await compression_service.decompress_slot("")

        assert result.success is False
        assert "slot_name is required" in result.error

    @pytest.mark.asyncio
    async def test_decompress_slot_error(self, compression_service, mock_storage):
        """Test decompression error handling."""
        mock_storage.decompress_slot.side_effect = ValueError("Corrupted data")

        result = await compression_service.decompress_slot("my_slot")

        assert result.success is False
        assert "Corrupted data" in result.error
