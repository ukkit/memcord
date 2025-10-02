"""Archival system for memory slot management."""

import asyncio
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import aiofiles
import aiofiles.os
from pydantic import BaseModel, Field

from .compression import ContentCompressor
from .models import CompressionInfo, MemorySlot


class ArchiveEntry(BaseModel):
    """Entry in the archive index."""

    slot_name: str = Field(..., description="Name of the archived memory slot")
    original_path: str = Field(..., description="Original path before archiving")
    archive_path: str = Field(..., description="Path in archive storage")
    archived_at: datetime = Field(..., description="When slot was archived")
    archive_reason: str = Field("manual", description="Reason for archiving")
    original_size: int = Field(..., description="Original file size in bytes")
    archived_size: int = Field(..., description="Archived file size in bytes")
    compression_ratio: float = Field(1.0, description="Compression ratio")
    last_accessed: datetime = Field(..., description="Last time slot was accessed")
    entry_count: int = Field(0, description="Number of entries in the slot")
    tags: list[str] = Field(default_factory=list, description="Tags from the original slot")
    group_path: str | None = Field(None, description="Group path from original slot")


class ArchiveIndex(BaseModel):
    """Index of all archived memory slots."""

    created_at: datetime = Field(default_factory=datetime.now, description="When index was created")
    updated_at: datetime = Field(default_factory=datetime.now, description="Last update time")
    total_archives: int = Field(0, description="Total number of archived slots")
    total_original_size: int = Field(0, description="Total original size of archived content")
    total_archived_size: int = Field(0, description="Total archived size")
    entries: dict[str, ArchiveEntry] = Field(default_factory=dict, description="Archive entries by slot name")

    def add_entry(self, entry: ArchiveEntry) -> None:
        """Add an archive entry to the index."""
        self.entries[entry.slot_name] = entry
        self.total_archives = len(self.entries)
        self.total_original_size = sum(e.original_size for e in self.entries.values())
        self.total_archived_size = sum(e.archived_size for e in self.entries.values())
        self.updated_at = datetime.now()

    def remove_entry(self, slot_name: str) -> bool:
        """Remove an archive entry from the index."""
        if slot_name in self.entries:
            del self.entries[slot_name]
            self.total_archives = len(self.entries)
            self.total_original_size = sum(e.original_size for e in self.entries.values())
            self.total_archived_size = sum(e.archived_size for e in self.entries.values())
            self.updated_at = datetime.now()
            return True
        return False

    def get_stats(self) -> dict[str, Any]:
        """Get archive statistics."""
        total_savings = self.total_original_size - self.total_archived_size
        savings_percent = (total_savings / self.total_original_size * 100) if self.total_original_size > 0 else 0

        return {
            "total_archives": self.total_archives,
            "total_original_size": self.total_original_size,
            "total_archived_size": self.total_archived_size,
            "total_savings": total_savings,
            "savings_percentage": savings_percent,
            "average_compression_ratio": self.total_archived_size / self.total_original_size
            if self.total_original_size > 0
            else 1.0,
        }


class ArchivalManager:
    """Manages archival operations for memory slots."""

    def __init__(self, memory_dir: str = "memory_slots", archive_dir: str = "archives"):
        # Convert to absolute paths to prevent working directory issues
        # Use .absolute() instead of .resolve() to avoid requiring path to exist
        self.memory_dir = Path(memory_dir).expanduser().absolute()
        self.archive_dir = Path(archive_dir).expanduser().absolute()
        self.index_file = self.archive_dir / "index.json"
        self._lock = asyncio.Lock()
        self._compressor = ContentCompressor()

        # Ensure directories exist
        self.memory_dir.mkdir(exist_ok=True)
        self.archive_dir.mkdir(exist_ok=True)

        # Initialize archive index
        self._index: ArchiveIndex | None = None

    async def _load_index(self) -> ArchiveIndex:
        """Load the archive index from file."""
        if not self.index_file.exists():
            return ArchiveIndex()

        try:
            async with aiofiles.open(self.index_file, encoding="utf-8") as f:
                data = await f.read()
                index_data = json.loads(data)
                return ArchiveIndex(**index_data)
        except Exception as e:
            print(f"Warning: Error loading archive index, creating new one: {e}")
            return ArchiveIndex()

    async def _save_index(self, index: ArchiveIndex) -> None:
        """Save the archive index to file."""
        try:
            # Create backup if file exists
            if self.index_file.exists():
                backup_path = self.index_file.with_suffix(".json.bak")
                await aiofiles.os.rename(str(self.index_file), str(backup_path))

            # Serialize datetime objects
            index_dict = index.model_dump()
            index_dict = self._serialize_datetime(index_dict)

            async with aiofiles.open(self.index_file, "w", encoding="utf-8") as f:
                await f.write(json.dumps(index_dict, indent=2, ensure_ascii=False))

            # Remove backup on successful save
            backup_path = self.index_file.with_suffix(".json.bak")
            if backup_path.exists():
                await aiofiles.os.remove(str(backup_path))

        except Exception as e:
            # Restore backup if save failed
            backup_path = self.index_file.with_suffix(".json.bak")
            if backup_path.exists():
                await aiofiles.os.rename(str(backup_path), str(self.index_file))
            raise ValueError(f"Error saving archive index: {e}") from e

    def _serialize_datetime(self, obj: Any, _seen=None) -> Any:
        """Convert datetime objects and sets to JSON-serializable format."""
        if _seen is None:
            _seen = set()

        # Prevent infinite recursion
        if id(obj) in _seen:
            return str(obj)  # fallback for circular references

        if isinstance(obj, datetime):
            return obj.isoformat()
        elif isinstance(obj, set):
            return list(obj)
        elif isinstance(obj, dict):
            _seen.add(id(obj))
            result = {k: self._serialize_datetime(v, _seen) for k, v in obj.items()}
            _seen.remove(id(obj))
            return result
        elif isinstance(obj, list):
            _seen.add(id(obj))
            result = [self._serialize_datetime(item, _seen) for item in obj]
            _seen.remove(id(obj))
            return result
        return obj

    async def get_index(self) -> ArchiveIndex:
        """Get the current archive index."""
        if self._index is None:
            self._index = await self._load_index()
        return self._index

    async def archive_slot(self, slot: MemorySlot, reason: str = "manual") -> ArchiveEntry:
        """Archive a memory slot."""
        async with self._lock:
            index = await self.get_index()

            # Calculate original size
            original_content = json.dumps(slot.model_dump(), ensure_ascii=False, default=str)
            original_size = len(original_content.encode("utf-8"))

            # Compress content for archival
            compressed_slot = await self._compress_slot_for_archive(slot)
            # Serialize properly to handle sets and datetime objects
            serialized_slot = self._serialize_datetime(compressed_slot)
            archived_content = json.dumps(serialized_slot, ensure_ascii=False)
            archived_size = len(archived_content.encode("utf-8"))

            # Create archive path
            archive_path = self.archive_dir / f"{slot.slot_name}_archived.json"

            # Save archived content
            async with aiofiles.open(archive_path, "w", encoding="utf-8") as f:
                await f.write(archived_content)

            # Create archive entry
            archive_entry = ArchiveEntry(
                slot_name=slot.slot_name,
                original_path=str(self.memory_dir / f"{slot.slot_name}.json"),
                archive_path=str(archive_path),
                archived_at=datetime.now(),
                archive_reason=reason,
                original_size=original_size,
                archived_size=archived_size,
                compression_ratio=archived_size / original_size if original_size > 0 else 1.0,
                last_accessed=slot.updated_at,
                entry_count=len(slot.entries),
                tags=list(slot.tags),
                group_path=slot.group_path,
            )

            # Add to index
            index.add_entry(archive_entry)
            await self._save_index(index)
            self._index = index

            return archive_entry

    async def _compress_slot_for_archive(self, slot: MemorySlot) -> dict[str, Any]:
        """Compress a memory slot for archival storage."""
        slot_dict = slot.model_dump()

        # Compress entry content if not already compressed
        for entry_dict in slot_dict.get("entries", []):
            if not entry_dict.get("compression_info", {}).get("is_compressed", False):
                content = entry_dict.get("content", "")
                if self._compressor.should_compress(content):
                    compressed_content, metadata = self._compressor.compress_json_content(content)
                    entry_dict["content"] = compressed_content
                    entry_dict["compression_info"] = metadata.model_dump()

        # Mark slot as archived
        slot_dict["is_archived"] = True
        slot_dict["archived_at"] = datetime.now().isoformat()
        slot_dict["archive_reason"] = "archived"

        return slot_dict

    async def restore_slot(self, slot_name: str) -> MemorySlot:
        """Restore an archived memory slot."""
        async with self._lock:
            index = await self.get_index()

            if slot_name not in index.entries:
                raise ValueError(f"Archived slot '{slot_name}' not found")

            archive_entry = index.entries[slot_name]
            archive_path = Path(archive_entry.archive_path)

            if not archive_path.exists():
                raise ValueError(f"Archive file not found: {archive_path}")

            # Load archived content
            async with aiofiles.open(archive_path, encoding="utf-8") as f:
                archived_content = await f.read()
                slot_dict = json.loads(archived_content)

            # Decompress content
            decompressed_slot = await self._decompress_slot_from_archive(slot_dict)

            # Create memory slot object
            slot = MemorySlot(**decompressed_slot)

            # Mark as unarchived
            slot.unarchive()

            return slot

    async def _decompress_slot_from_archive(self, slot_dict: dict[str, Any]) -> dict[str, Any]:
        """Decompress an archived memory slot."""
        # Decompress entry content
        for entry_dict in slot_dict.get("entries", []):
            compression_info = entry_dict.get("compression_info", {})
            if compression_info.get("is_compressed", False):
                from .compression import CompressionMetadata

                metadata = CompressionMetadata(**compression_info)
                content = entry_dict.get("content", "")
                decompressed_content = self._compressor.decompress_json_content(content, metadata)
                entry_dict["content"] = decompressed_content
                # Reset compression info
                entry_dict["compression_info"] = CompressionInfo().model_dump()

        # Convert lists back to sets where appropriate (for MemorySlot model compatibility)
        if "tags" in slot_dict and isinstance(slot_dict["tags"], list):
            slot_dict["tags"] = set(slot_dict["tags"])

        return slot_dict

    async def delete_archive(self, slot_name: str) -> bool:
        """Permanently delete an archived memory slot."""
        async with self._lock:
            index = await self.get_index()

            if slot_name not in index.entries:
                return False

            archive_entry = index.entries[slot_name]
            archive_path = Path(archive_entry.archive_path)

            # Remove archive file
            if archive_path.exists():
                await aiofiles.os.remove(str(archive_path))

            # Remove from index
            index.remove_entry(slot_name)
            await self._save_index(index)
            self._index = index

            return True

    async def list_archives(self, include_stats: bool = False) -> list[dict[str, Any]]:
        """List all archived memory slots."""
        index = await self.get_index()

        archives = []
        for entry in index.entries.values():
            archive_info = {
                "slot_name": entry.slot_name,
                "archived_at": entry.archived_at.isoformat(),
                "archive_reason": entry.archive_reason,
                "entry_count": entry.entry_count,
                "tags": entry.tags,
                "group_path": entry.group_path,
                "last_accessed": entry.last_accessed.isoformat(),
            }

            if include_stats:
                archive_info.update(
                    {
                        "original_size": entry.original_size,
                        "archived_size": entry.archived_size,
                        "compression_ratio": entry.compression_ratio,
                        "space_saved": entry.original_size - entry.archived_size,
                    }
                )

            archives.append(archive_info)

        return sorted(archives, key=lambda x: x["archived_at"], reverse=True)

    async def get_archive_stats(self) -> dict[str, Any]:
        """Get overall archive statistics."""
        index = await self.get_index()
        return index.get_stats()

    async def find_candidates_for_archival(
        self, days_inactive: int = 30, min_entries: int = 1
    ) -> list[tuple[str, dict[str, Any]]]:
        """Find memory slots that are candidates for archival."""
        candidates = []
        cutoff_date = datetime.now() - timedelta(days=days_inactive)

        # Scan memory slots directory
        for slot_file in self.memory_dir.glob("*.json"):
            slot_name = slot_file.stem

            try:
                async with aiofiles.open(slot_file, encoding="utf-8") as f:
                    data = await f.read()
                    slot_data = json.loads(data)

                # Check if slot qualifies for archival
                updated_at = datetime.fromisoformat(slot_data.get("updated_at", ""))
                entry_count = len(slot_data.get("entries", []))

                if updated_at < cutoff_date and entry_count >= min_entries:
                    # Calculate estimated savings
                    slot_size = len(data.encode("utf-8"))

                    candidate_info = {
                        "last_updated": updated_at.isoformat(),
                        "days_inactive": (datetime.now() - updated_at).days,
                        "entry_count": entry_count,
                        "current_size": slot_size,
                        "tags": slot_data.get("tags", []),
                        "group_path": slot_data.get("group_path"),
                    }

                    candidates.append((slot_name, candidate_info))

            except Exception as e:
                print(f"Warning: Error analyzing slot {slot_name} for archival: {e}")
                continue

        return sorted(candidates, key=lambda x: x[1]["days_inactive"], reverse=True)


def format_archive_report(stats: dict[str, Any], archives: list[dict[str, Any]]) -> str:
    """Format archive statistics into a readable report."""
    from .compression import format_size

    if stats["total_archives"] == 0:
        return "No archived memory slots found."

    report = [
        "# Archive Storage Report",
        "",
        f"**Total Archives:** {stats['total_archives']}",
        f"**Original Size:** {format_size(stats['total_original_size'])}",
        f"**Archived Size:** {format_size(stats['total_archived_size'])}",
        f"**Space Saved:** {format_size(stats['total_savings'])} ({stats['savings_percentage']:.1f}%)",
        f"**Average Compression:** {stats['average_compression_ratio']:.3f}",
        "",
        "## Archived Memory Slots",
    ]

    for archive in archives[:10]:  # Show first 10
        days_ago = (datetime.now() - datetime.fromisoformat(archive["archived_at"])).days
        report.append(f"- **{archive['slot_name']}** - {archive['entry_count']} entries, archived {days_ago} days ago")

    if len(archives) > 10:
        report.append(f"- ... and {len(archives) - 10} more archived slots")

    report.extend(["", "---", "*Generated by MemCord Archive Manager*"])

    return "\n".join(report)
