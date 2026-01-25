"""Compression service for memory slot storage optimization.

Extracts business logic from the compress handler for better testability
and separation of concerns.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..storage import StorageManager


@dataclass
class CompressionStats:
    """Statistics about compression state."""

    slot_name: str | None = None
    total_entries: int = 0
    compressed_entries: int = 0
    compression_percentage: float = 0.0
    total_original_size: int = 0
    total_compressed_size: int = 0
    space_saved: int = 0
    space_saved_percentage: float = 0.0
    compression_ratio: float = 1.0
    total_slots: int = 0  # For global stats


@dataclass
class CompressionResult:
    """Result of a compression operation."""

    success: bool
    slot_name: str | None = None
    entries_processed: int = 0
    entries_compressed: int = 0
    original_size: int = 0
    compressed_size: int = 0
    space_saved: int = 0
    compression_ratio: float = 1.0
    error: str | None = None


@dataclass
class BulkCompressionResult:
    """Result of bulk compression across all slots."""

    success: bool
    slots_processed: int = 0
    total_entries_processed: int = 0
    total_entries_compressed: int = 0
    total_original_size: int = 0
    total_compressed_size: int = 0
    total_space_saved: int = 0
    overall_compression_ratio: float = 1.0
    error: str | None = None


@dataclass
class DecompressionResult:
    """Result of a decompression operation."""

    success: bool
    slot_name: str = ""
    entries_processed: int = 0
    entries_decompressed: int = 0
    decompressed_successfully: bool = True
    error: str | None = None


@dataclass
class CompressionAnalysis:
    """Analysis of compression potential."""

    success: bool
    report: str = ""
    error: str | None = None


class CompressionService:
    """Service for memory slot compression operations."""

    def __init__(self, storage: "StorageManager"):
        """Initialize compression service.

        Args:
            storage: Storage manager for slot operations
        """
        self.storage = storage

    async def get_stats(self, slot_name: str | None = None) -> CompressionStats:
        """Get compression statistics.

        Args:
            slot_name: Optional slot name for single-slot stats, None for global

        Returns:
            CompressionStats with statistics
        """
        stats = await self.storage.get_compression_stats(slot_name)

        if slot_name:
            return CompressionStats(
                slot_name=slot_name,
                total_entries=stats.get("total_entries", 0),
                compressed_entries=stats.get("compressed_entries", 0),
                compression_percentage=stats.get("compression_percentage", 0.0),
                total_original_size=stats.get("total_original_size", 0),
                total_compressed_size=stats.get("total_compressed_size", 0),
                space_saved=stats.get("space_saved", 0),
                space_saved_percentage=stats.get("space_saved_percentage", 0.0),
                compression_ratio=stats.get("compression_ratio", 1.0),
            )
        else:
            return CompressionStats(
                total_slots=stats.get("total_slots", 0),
                total_entries=stats.get("total_entries", 0),
                compressed_entries=stats.get("compressed_entries", 0),
                total_original_size=stats.get("total_original_size", 0),
                total_compressed_size=stats.get("total_compressed_size", 0),
                space_saved=stats.get("space_saved", 0),
                space_saved_percentage=stats.get("space_saved_percentage", 0.0),
                compression_ratio=stats.get("compression_ratio", 1.0),
            )

    async def analyze(self, slot_name: str | None = None) -> CompressionAnalysis:
        """Analyze compression potential.

        Args:
            slot_name: Optional slot name, None for all slots

        Returns:
            CompressionAnalysis with report
        """
        try:
            from ..compression import ContentCompressor, format_compression_report

            compressor = ContentCompressor()

            if slot_name:
                # Analyze single slot
                slot = await self.storage.read_memory(slot_name)
                if not slot:
                    return CompressionAnalysis(
                        success=False,
                        error=f"Memory slot '{slot_name}' not found",
                    )

                slot_data = [slot.model_dump()]
            else:
                # Analyze all slots
                slots_info = await self.storage.list_memory_slots()
                slot_data = []

                for slot_info in slots_info:
                    slot = await self.storage.read_memory(slot_info["name"])
                    if slot:
                        slot_data.append(slot.model_dump())

            stats = compressor.get_compression_stats(slot_data)
            report = format_compression_report(stats)

            return CompressionAnalysis(success=True, report=report)

        except Exception as e:
            return CompressionAnalysis(success=False, error=str(e))

    async def compress_slot(self, slot_name: str, force: bool = False) -> CompressionResult:
        """Compress a single memory slot.

        Args:
            slot_name: Name of slot to compress
            force: Force compression even for already compressed content

        Returns:
            CompressionResult with operation results
        """
        try:
            compression_stats = await self.storage.compress_slot(slot_name, force)

            return CompressionResult(
                success=True,
                slot_name=slot_name,
                entries_processed=compression_stats.get("entries_processed", 0),
                entries_compressed=compression_stats.get("entries_compressed", 0),
                original_size=compression_stats.get("original_size", 0),
                compressed_size=compression_stats.get("compressed_size", 0),
                space_saved=compression_stats.get("space_saved", 0),
                compression_ratio=compression_stats.get("compression_ratio", 1.0),
            )

        except Exception as e:
            return CompressionResult(
                success=False,
                slot_name=slot_name,
                error=str(e),
            )

    async def compress_all_slots(self, force: bool = False) -> BulkCompressionResult:
        """Compress all memory slots.

        Args:
            force: Force compression even for already compressed content

        Returns:
            BulkCompressionResult with aggregate results
        """
        try:
            slots_info = await self.storage.list_memory_slots()
            total_stats = {
                "slots_processed": 0,
                "total_entries_processed": 0,
                "total_entries_compressed": 0,
                "total_original_size": 0,
                "total_compressed_size": 0,
                "total_space_saved": 0,
            }

            for slot_info in slots_info:
                try:
                    compression_stats = await self.storage.compress_slot(slot_info["name"], force)
                    total_stats["slots_processed"] += 1
                    total_stats["total_entries_processed"] += compression_stats.get("entries_processed", 0)
                    total_stats["total_entries_compressed"] += compression_stats.get("entries_compressed", 0)
                    total_stats["total_original_size"] += compression_stats.get("original_size", 0)
                    total_stats["total_compressed_size"] += compression_stats.get("compressed_size", 0)
                    total_stats["total_space_saved"] += compression_stats.get("space_saved", 0)
                except Exception:
                    continue

            overall_ratio = (
                total_stats["total_compressed_size"] / total_stats["total_original_size"]
                if total_stats["total_original_size"] > 0
                else 1.0
            )

            return BulkCompressionResult(
                success=True,
                slots_processed=total_stats["slots_processed"],
                total_entries_processed=total_stats["total_entries_processed"],
                total_entries_compressed=total_stats["total_entries_compressed"],
                total_original_size=total_stats["total_original_size"],
                total_compressed_size=total_stats["total_compressed_size"],
                total_space_saved=total_stats["total_space_saved"],
                overall_compression_ratio=overall_ratio,
            )

        except Exception as e:
            return BulkCompressionResult(success=False, error=str(e))

    async def decompress_slot(self, slot_name: str) -> DecompressionResult:
        """Decompress a memory slot.

        Args:
            slot_name: Name of slot to decompress

        Returns:
            DecompressionResult with operation results
        """
        if not slot_name:
            return DecompressionResult(
                success=False,
                error="slot_name is required for decompress action",
            )

        try:
            decompression_stats = await self.storage.decompress_slot(slot_name)

            return DecompressionResult(
                success=True,
                slot_name=slot_name,
                entries_processed=decompression_stats.get("entries_processed", 0),
                entries_decompressed=decompression_stats.get("entries_decompressed", 0),
                decompressed_successfully=decompression_stats.get("decompressed_successfully", True),
            )

        except Exception as e:
            return DecompressionResult(
                success=False,
                slot_name=slot_name,
                error=str(e),
            )
