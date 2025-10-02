"""Storage efficiency enhancements for memcord."""

import asyncio
import gzip
import hashlib
import json
import logging
import math
from collections import defaultdict
from collections.abc import AsyncIterator, Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any

import aiofiles
import aiofiles.os

from .models import MemoryEntry, MemorySlot


@dataclass
class IndexChangeLog:
    """Tracks changes to search index for incremental updates."""

    slot_name: str
    operation: str  # 'add', 'update', 'delete'
    timestamp: datetime
    content_hash: str | None = None
    previous_hash: str | None = None


@dataclass
class StorageStats:
    """Storage usage statistics and monitoring."""

    total_slots: int
    total_size_mb: float
    compressed_slots: int
    compression_ratio: float
    fragmentation_ratio: float
    oldest_access: datetime
    newest_access: datetime
    index_size_mb: float
    cache_size_mb: float
    available_space_mb: float = 0.0
    quota_used_percent: float = 0.0


class AlertType(Enum):
    """Types of storage alerts."""

    QUOTA_WARNING = "quota_warning"
    QUOTA_CRITICAL = "quota_critical"
    LOW_SPACE = "low_space"
    HIGH_FRAGMENTATION = "high_fragmentation"
    CLEANUP_NEEDED = "cleanup_needed"
    PERFORMANCE_DEGRADED = "performance_degraded"


@dataclass
class StorageAlert:
    """Storage alert information."""

    alert_type: AlertType
    message: str
    severity: str  # 'info', 'warning', 'critical'
    timestamp: datetime
    threshold_value: float | None = None
    current_value: float | None = None
    suggested_action: str | None = None


@dataclass
class QuotaConfig:
    """Storage quota configuration."""

    max_total_size_mb: float
    max_slots: int
    max_slot_size_mb: float
    warning_threshold_percent: float = 80.0
    critical_threshold_percent: float = 95.0
    auto_cleanup_enabled: bool = True
    cleanup_threshold_days: int = 30


class IncrementalSearchIndex:
    """Enhanced search index with incremental update capabilities."""

    def __init__(self, index_dir: Path):
        self.index_dir = Path(index_dir)
        self.index_dir.mkdir(exist_ok=True)

        # Core index data
        self.word_to_slots: dict[str, set[str]] = defaultdict(set)
        self.slot_word_counts: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
        self.slot_total_words: dict[str, int] = defaultdict(int)
        self.slot_content_hashes: dict[str, str] = {}

        # Change tracking
        self.change_log: list[IndexChangeLog] = []
        self.dirty_slots: set[str] = set()

        # Background maintenance
        self._maintenance_task: asyncio.Task | None = None
        self._shutdown_event = asyncio.Event()

    async def initialize(self):
        """Initialize index from persistent storage."""
        await self._load_index_from_disk()
        # Start background maintenance task
        self._maintenance_task = asyncio.create_task(self._background_maintenance())

    async def shutdown(self):
        """Shutdown index and save state."""
        self._shutdown_event.set()
        if self._maintenance_task:
            await self._maintenance_task
        await self._save_index_to_disk()

    def _calculate_content_hash(self, slot: MemorySlot) -> str:
        """Calculate hash for slot content to detect changes."""
        content = slot.get_searchable_content()
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    def _tokenize(self, text: str, case_sensitive: bool = False) -> list[str]:
        """Tokenize text for indexing."""
        import re

        if not case_sensitive:
            text = text.lower()
        # Extract words (alphanumeric sequences)
        words = re.findall(r"\b\w+\b", text)
        return [word for word in words if len(word) > 1]  # Filter single characters

    async def add_or_update_slot(self, slot: MemorySlot) -> bool:
        """Add or update slot in index incrementally. Returns True if updated."""
        content_hash = self._calculate_content_hash(slot)
        slot_name = slot.slot_name

        # Check if content actually changed
        if slot_name in self.slot_content_hashes:
            previous_hash = self.slot_content_hashes[slot_name]
            if previous_hash == content_hash:
                return False  # No changes needed

            # Content changed, remove old version first
            await self._remove_slot_from_index(slot_name)
            operation = "update"
        else:
            operation = "add"
            previous_hash = None

        # Add new content to index
        content = slot.get_searchable_content()
        words = self._tokenize(content)

        # Add new word counts
        word_counts = defaultdict(int)
        for word in words:
            word_counts[word] += 1
            self.word_to_slots[word].add(slot_name)

        self.slot_word_counts[slot_name] = dict(word_counts)
        self.slot_total_words[slot_name] = len(words)
        self.slot_content_hashes[slot_name] = content_hash

        # Log the change
        change = IndexChangeLog(
            slot_name=slot_name,
            operation=operation,
            timestamp=datetime.now(),
            content_hash=content_hash,
            previous_hash=previous_hash,
        )
        self.change_log.append(change)
        self.dirty_slots.add(slot_name)

        return True

    async def _remove_slot_from_index(self, slot_name: str):
        """Remove slot from index."""
        if slot_name not in self.slot_word_counts:
            return

        # Remove slot from word mappings
        for word in self.slot_word_counts[slot_name]:
            self.word_to_slots[word].discard(slot_name)
            if not self.word_to_slots[word]:
                del self.word_to_slots[word]

        # Remove slot data
        del self.slot_word_counts[slot_name]
        del self.slot_total_words[slot_name]
        if slot_name in self.slot_content_hashes:
            del self.slot_content_hashes[slot_name]

    async def remove_slot(self, slot_name: str):
        """Remove slot from index and log change."""
        await self._remove_slot_from_index(slot_name)

        # Log the change
        change = IndexChangeLog(slot_name=slot_name, operation="delete", timestamp=datetime.now())
        self.change_log.append(change)
        self.dirty_slots.discard(slot_name)

    async def _background_maintenance(self):
        """Background task for index maintenance."""
        while not self._shutdown_event.is_set():
            try:
                # Wait for maintenance interval or shutdown
                await asyncio.wait_for(self._shutdown_event.wait(), timeout=300.0)  # 5 minutes
                break
            except asyncio.TimeoutError:
                pass  # Time for maintenance

            # Perform maintenance tasks
            await self._perform_maintenance()

    async def _perform_maintenance(self):
        """Perform index maintenance tasks."""
        # Save incremental changes to disk
        if self.dirty_slots:
            await self._save_incremental_changes()

        # Cleanup old change log entries (keep last 1000)
        if len(self.change_log) > 1000:
            self.change_log = self.change_log[-1000:]

        # Compact index if needed (remove empty word mappings)
        empty_words = [word for word, slots in self.word_to_slots.items() if not slots]
        for word in empty_words:
            del self.word_to_slots[word]

    async def _save_index_to_disk(self):
        """Save complete index to disk."""
        index_data = {
            "word_to_slots": {word: list(slots) for word, slots in self.word_to_slots.items()},
            "slot_word_counts": dict(self.slot_word_counts),
            "slot_total_words": dict(self.slot_total_words),
            "slot_content_hashes": self.slot_content_hashes,
            "change_log": [
                {
                    "slot_name": change.slot_name,
                    "operation": change.operation,
                    "timestamp": change.timestamp.isoformat(),
                    "content_hash": change.content_hash,
                    "previous_hash": change.previous_hash,
                }
                for change in self.change_log
            ],
        }

        index_path = self.index_dir / "search_index.json"
        temp_path = self.index_dir / "search_index.json.tmp"

        async with aiofiles.open(temp_path, "w", encoding="utf-8") as f:
            await f.write(json.dumps(index_data, indent=2))

        # Atomic replace
        await aiofiles.os.rename(str(temp_path), str(index_path))
        self.dirty_slots.clear()

    async def _save_incremental_changes(self):
        """Save only changed slots to disk incrementally."""
        if not self.dirty_slots:
            return

        changes_path = self.index_dir / f"changes_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

        # Prepare incremental data
        incremental_data = {
            "timestamp": datetime.now().isoformat(),
            "dirty_slots": list(self.dirty_slots),
            "word_updates": {},
            "slot_updates": {},
        }

        # Include only data for dirty slots
        for slot_name in self.dirty_slots:
            if slot_name in self.slot_word_counts:
                incremental_data["slot_updates"][slot_name] = {
                    "word_counts": self.slot_word_counts[slot_name],
                    "total_words": self.slot_total_words[slot_name],
                    "content_hash": self.slot_content_hashes.get(slot_name),
                }

        async with aiofiles.open(changes_path, "w", encoding="utf-8") as f:
            await f.write(json.dumps(incremental_data, indent=2))

        self.dirty_slots.clear()

    async def _load_index_from_disk(self):
        """Load index from persistent storage."""
        index_path = self.index_dir / "search_index.json"

        if index_path.exists():
            async with aiofiles.open(index_path, encoding="utf-8") as f:
                data = await f.read()
                index_data = json.loads(data)

            # Restore index data
            self.word_to_slots = defaultdict(set)
            for word, slots in index_data.get("word_to_slots", {}).items():
                self.word_to_slots[word] = set(slots)

            self.slot_word_counts = defaultdict(lambda: defaultdict(int))
            for slot_name, word_counts in index_data.get("slot_word_counts", {}).items():
                self.slot_word_counts[slot_name] = defaultdict(int, word_counts)

            self.slot_total_words = defaultdict(int, index_data.get("slot_total_words", {}))
            self.slot_content_hashes = index_data.get("slot_content_hashes", {})

            # Restore change log
            self.change_log = []
            for change_data in index_data.get("change_log", []):
                change = IndexChangeLog(
                    slot_name=change_data["slot_name"],
                    operation=change_data["operation"],
                    timestamp=datetime.fromisoformat(change_data["timestamp"]),
                    content_hash=change_data.get("content_hash"),
                    previous_hash=change_data.get("previous_hash"),
                )
                self.change_log.append(change)

        # Also load any incremental changes
        await self._load_incremental_changes()

    async def _load_incremental_changes(self):
        """Load and apply incremental changes."""
        changes_files = sorted(self.index_dir.glob("changes_*.json"))

        for changes_file in changes_files:
            try:
                async with aiofiles.open(changes_file, encoding="utf-8") as f:
                    data = await f.read()
                    changes_data = json.loads(data)

                # Apply slot updates
                for slot_name, slot_data in changes_data.get("slot_updates", {}).items():
                    self.slot_word_counts[slot_name] = defaultdict(int, slot_data["word_counts"])
                    self.slot_total_words[slot_name] = slot_data["total_words"]
                    if slot_data.get("content_hash"):
                        self.slot_content_hashes[slot_name] = slot_data["content_hash"]

                # Rebuild word-to-slots mapping for updated slots
                for slot_name in changes_data.get("dirty_slots", []):
                    if slot_name in self.slot_word_counts:
                        for word in self.slot_word_counts[slot_name]:
                            self.word_to_slots[word].add(slot_name)

            except Exception as e:
                print(f"Warning: Could not load incremental changes from {changes_file}: {e}")
                continue

    def search(self, query: str, case_sensitive: bool = False) -> dict[str, float]:
        """Search index with TF-IDF scoring."""
        if not query.strip():
            return {}

        query_words = self._tokenize(query, case_sensitive)
        if not query_words:
            return {}

        # Find candidate slots
        candidate_slots = set()
        for word in query_words:
            candidate_slots.update(self.word_to_slots.get(word, set()))

        if not candidate_slots:
            return {}

        # Calculate TF-IDF scores
        total_slots = len(self.slot_total_words)
        scores = {}

        for slot_name in candidate_slots:
            score = 0.0
            for word in query_words:
                tf = self.slot_word_counts[slot_name].get(word, 0) / max(1, self.slot_total_words[slot_name])
                df = len(self.word_to_slots[word])
                # Use smoothed IDF to avoid log(1) = 0 for single documents
                # Add a small constant to ensure non-zero scores
                idf = math.log(total_slots / df) + 1.0 if df > 0 else 1.0
                score += tf * idf

            scores[slot_name] = score

        return scores


class DeltaCompressor:
    """Handles delta compression for storage updates."""

    def __init__(self, storage_dir: Path):
        self.storage_dir = Path(storage_dir)
        self.deltas_dir = self.storage_dir / "deltas"
        self.deltas_dir.mkdir(exist_ok=True)

    async def create_delta(self, slot_name: str, old_slot: MemorySlot, new_slot: MemorySlot) -> Path:
        """Create delta between old and new slot versions."""
        delta_data = {"slot_name": slot_name, "timestamp": datetime.now().isoformat(), "operations": []}

        # Compare entries
        old_entries = {entry.timestamp.isoformat(): entry for entry in old_slot.entries}
        new_entries = {entry.timestamp.isoformat(): entry for entry in new_slot.entries}

        # Find additions
        for timestamp, entry in new_entries.items():
            if timestamp not in old_entries:
                delta_data["operations"].append(
                    {"type": "add_entry", "timestamp": timestamp, "entry": entry.model_dump()}
                )

        # Find modifications (simplified - compare content)
        for timestamp, new_entry in new_entries.items():
            if timestamp in old_entries:
                old_entry = old_entries[timestamp]
                if old_entry.content != new_entry.content:
                    delta_data["operations"].append(
                        {
                            "type": "modify_entry",
                            "timestamp": timestamp,
                            "old_content": old_entry.content,
                            "new_content": new_entry.content,
                        }
                    )

        # Find deletions
        for timestamp in old_entries:
            if timestamp not in new_entries:
                delta_data["operations"].append({"type": "delete_entry", "timestamp": timestamp})

        # Compare metadata
        if old_slot.tags != new_slot.tags:
            delta_data["operations"].append(
                {"type": "update_tags", "old_tags": list(old_slot.tags), "new_tags": list(new_slot.tags)}
            )

        if old_slot.group_path != new_slot.group_path:
            delta_data["operations"].append(
                {"type": "update_group", "old_group": old_slot.group_path, "new_group": new_slot.group_path}
            )

        # Save delta
        delta_filename = f"{slot_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.delta"
        delta_path = self.deltas_dir / delta_filename

        # Serialize datetime objects before compressing
        def serialize_datetime(obj):
            if isinstance(obj, datetime):
                return obj.isoformat()
            elif isinstance(obj, dict):
                return {k: serialize_datetime(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [serialize_datetime(item) for item in obj]
            elif isinstance(obj, set):
                return sorted(obj)
            return obj

        serialized_delta = serialize_datetime(delta_data)

        # Compress delta data
        compressed_data = gzip.compress(json.dumps(serialized_delta).encode("utf-8"))

        async with aiofiles.open(delta_path, "wb") as f:
            await f.write(compressed_data)

        return delta_path

    async def apply_delta(self, base_slot: MemorySlot, delta_path: Path) -> MemorySlot:
        """Apply delta to base slot to get updated version."""
        # Read and decompress delta
        async with aiofiles.open(delta_path, "rb") as f:
            compressed_data = await f.read()

        delta_data = json.loads(gzip.decompress(compressed_data).decode("utf-8"))

        # Apply operations
        updated_slot = base_slot.model_copy(deep=True)

        for operation in delta_data["operations"]:
            op_type = operation["type"]

            if op_type == "add_entry":
                entry = MemoryEntry(**operation["entry"])
                updated_slot.entries.append(entry)

            elif op_type == "modify_entry":
                timestamp_str = operation["timestamp"]
                for entry in updated_slot.entries:
                    if entry.timestamp.isoformat() == timestamp_str:
                        entry.content = operation["new_content"]
                        break

            elif op_type == "delete_entry":
                timestamp_str = operation["timestamp"]
                updated_slot.entries = [
                    entry for entry in updated_slot.entries if entry.timestamp.isoformat() != timestamp_str
                ]

            elif op_type == "update_tags":
                updated_slot.tags = set(operation["new_tags"])

            elif op_type == "update_group":
                updated_slot.group_path = operation["new_group"]

        return updated_slot


class StreamingOperations:
    """Handles streaming operations for large files."""

    @staticmethod
    async def stream_large_slot(slot_path: Path, chunk_size: int = 8192) -> AsyncIterator[dict[str, Any]]:
        """Stream large slot file in chunks."""
        async with aiofiles.open(slot_path, encoding="utf-8") as f:
            buffer = ""
            depth = 0
            in_string = False
            escape_next = False

            async for chunk in f:
                buffer += chunk

                # Simple JSON streaming parser
                i = 0
                while i < len(buffer):
                    char = buffer[i]

                    if escape_next:
                        escape_next = False
                        i += 1
                        continue

                    if char == "\\":
                        escape_next = True
                    elif char == '"' and not escape_next:
                        in_string = not in_string
                    elif not in_string:
                        if char == "{":
                            depth += 1
                        elif char == "}":
                            depth -= 1
                            if depth == 1:  # Completed an entry
                                # Found complete JSON object, yield it
                                try:
                                    json_str = buffer[: i + 1]
                                    obj = json.loads(json_str)
                                    yield obj
                                    buffer = buffer[i + 1 :]
                                    i = 0
                                    continue
                                except json.JSONDecodeError:
                                    pass  # Continue accumulating
                    i += 1

    @staticmethod
    async def write_slot_streaming(slot: MemorySlot, slot_path: Path, chunk_size: int = 8192):
        """Write slot to file using streaming to handle large content."""
        # Create temporary file for atomic write
        temp_path = slot_path.with_suffix(".tmp")

        async with aiofiles.open(temp_path, "w", encoding="utf-8") as f:
            # Write slot header
            slot_dict = slot.model_dump()

            # Convert datetime objects and sets
            def serialize_datetime(obj):
                if isinstance(obj, dict):
                    return {k: serialize_datetime(v) for k, v in obj.items()}
                elif isinstance(obj, list):
                    return [serialize_datetime(item) for item in obj]
                elif isinstance(obj, datetime):
                    return obj.isoformat()
                elif isinstance(obj, set):
                    return sorted(obj)
                return obj

            slot_dict = serialize_datetime(slot_dict)

            # Write JSON in streaming fashion for large entries
            await f.write("{\n")

            # Write metadata
            for key, value in slot_dict.items():
                if key == "entries":
                    continue
                await f.write(f'  "{key}": {json.dumps(value)},\n')

            # Write entries in chunks
            await f.write('  "entries": [\n')

            for i, entry in enumerate(slot_dict["entries"]):
                if i > 0:
                    await f.write(",\n")
                await f.write("    ")

                # Write entry in chunks if content is large
                entry_json = json.dumps(entry, ensure_ascii=False)
                if len(entry_json) > chunk_size:
                    # Write in chunks
                    for j in range(0, len(entry_json), chunk_size):
                        chunk = entry_json[j : j + chunk_size]
                        await f.write(chunk)
                else:
                    await f.write(entry_json)

            await f.write("\n  ]\n}")

        # Atomic replace
        await aiofiles.os.rename(str(temp_path), str(slot_path))


class StorageMonitor:
    """Monitors storage usage and provides statistics."""

    def __init__(self, storage_dir: Path):
        self.storage_dir = Path(storage_dir)

    async def get_storage_stats(self) -> StorageStats:
        """Get comprehensive storage statistics."""
        total_slots = 0
        total_size = 0
        compressed_slots = 0
        compression_sizes = []
        oldest_access = datetime.now()
        newest_access = datetime.min

        # Analyze slot files
        for slot_file in self.storage_dir.glob("*.json"):
            total_slots += 1
            stat = await aiofiles.os.stat(slot_file)
            total_size += stat.st_size

            # Check access times
            access_time = datetime.fromtimestamp(stat.st_atime)
            if access_time < oldest_access:
                oldest_access = access_time
            if access_time > newest_access:
                newest_access = access_time

            # Check if compressed (simple heuristic)
            if slot_file.suffix == ".gz":
                compressed_slots += 1
                # Estimate compression ratio
                async with aiofiles.open(slot_file, "rb") as f:
                    compressed_data = await f.read()
                    compression_sizes.append(len(compressed_data))

        # Calculate metrics
        total_size_mb = total_size / (1024 * 1024)
        compression_ratio = sum(compression_sizes) / max(1, total_size) if compression_sizes else 0

        # Estimate fragmentation (simplified)
        fragmentation_ratio = 0.1  # Placeholder - would need more sophisticated analysis

        # Get index size
        index_size = 0
        index_dir = self.storage_dir / "index"
        if index_dir.exists():
            for index_file in index_dir.glob("*"):
                stat = await aiofiles.os.stat(index_file)
                index_size += stat.st_size

        index_size_mb = index_size / (1024 * 1024)

        # Get cache size
        cache_size = 0
        cache_dir = self.storage_dir / "cache"
        if cache_dir.exists():
            for cache_file in cache_dir.rglob("*"):
                if cache_file.is_file():
                    stat = await aiofiles.os.stat(cache_file)
                    cache_size += stat.st_size

        cache_size_mb = cache_size / (1024 * 1024)

        return StorageStats(
            total_slots=total_slots,
            total_size_mb=total_size_mb,
            compressed_slots=compressed_slots,
            compression_ratio=compression_ratio,
            fragmentation_ratio=fragmentation_ratio,
            oldest_access=oldest_access,
            newest_access=newest_access,
            index_size_mb=index_size_mb,
            cache_size_mb=cache_size_mb,
        )

    async def identify_cleanup_candidates(self, days_old: int = 30) -> list[str]:
        """Identify slots that haven't been accessed recently."""
        cutoff_date = datetime.now() - timedelta(days=days_old)
        candidates = []

        for slot_file in self.storage_dir.glob("*.json"):
            stat = await aiofiles.os.stat(slot_file)
            access_time = datetime.fromtimestamp(stat.st_atime)

            if access_time < cutoff_date:
                candidates.append(slot_file.stem)

        return candidates

    async def cleanup_temporary_files(self) -> int:
        """Clean up temporary files and return count cleaned."""
        cleaned = 0

        # Clean backup files
        for backup_file in self.storage_dir.glob("*.bak"):
            await aiofiles.os.remove(backup_file)
            cleaned += 1

        # Clean temp files
        for temp_file in self.storage_dir.glob("*.tmp"):
            await aiofiles.os.remove(temp_file)
            cleaned += 1

        return cleaned


class StorageDefragmenter:
    """Handles storage file defragmentation and optimization."""

    def __init__(self, storage_dir: Path):
        self.storage_dir = Path(storage_dir)
        self.logger = logging.getLogger(__name__)

    async def analyze_fragmentation(self) -> dict[str, float]:
        """Analyze storage fragmentation and return metrics."""
        fragmentation_metrics = {
            "file_fragmentation": 0.0,
            "space_fragmentation": 0.0,
            "index_fragmentation": 0.0,
            "overall_fragmentation": 0.0,
        }

        try:
            # Analyze file fragmentation (gaps in slot numbering/naming)
            slot_files = list(self.storage_dir.glob("*.json"))
            if slot_files:
                sorted([f.stem for f in slot_files])

                # Simple heuristic: measure gaps in file creation times
                timestamps = []
                for slot_file in slot_files:
                    stat = await aiofiles.os.stat(slot_file)
                    timestamps.append(stat.st_ctime)

                timestamps.sort()
                if len(timestamps) > 1:
                    gaps = [timestamps[i + 1] - timestamps[i] for i in range(len(timestamps) - 1)]
                    avg_gap = sum(gaps) / len(gaps)
                    max_gap = max(gaps)
                    file_fragmentation = min(1.0, max_gap / (avg_gap * 10)) if avg_gap > 0 else 0.0
                    fragmentation_metrics["file_fragmentation"] = file_fragmentation

            # Analyze space fragmentation (unused space in files)
            total_file_size = 0
            total_content_size = 0

            for slot_file in slot_files:
                stat = await aiofiles.os.stat(slot_file)
                total_file_size += stat.st_size

                # Estimate actual content size vs file size
                try:
                    async with aiofiles.open(slot_file, encoding="utf-8") as f:
                        content = await f.read()
                        # Remove formatting whitespace for content size estimate
                        compact_content = json.dumps(json.loads(content), separators=(",", ":"))
                        total_content_size += len(compact_content.encode("utf-8"))
                except Exception:
                    # Fallback to file size if can't parse
                    total_content_size += stat.st_size

            if total_file_size > 0:
                space_fragmentation = 1.0 - (total_content_size / total_file_size)
                fragmentation_metrics["space_fragmentation"] = max(0.0, space_fragmentation)

            # Analyze index fragmentation
            index_dir = self.storage_dir / "index"
            if index_dir.exists():
                index_files = list(index_dir.glob("*"))
                # Count incremental change files vs main index
                change_files = len([f for f in index_files if f.name.startswith("changes_")])
                total_files = len(index_files)

                if total_files > 0:
                    index_fragmentation = change_files / total_files
                    fragmentation_metrics["index_fragmentation"] = index_fragmentation

            # Calculate overall fragmentation
            overall = (
                fragmentation_metrics["file_fragmentation"] * 0.3
                + fragmentation_metrics["space_fragmentation"] * 0.5
                + fragmentation_metrics["index_fragmentation"] * 0.2
            )
            fragmentation_metrics["overall_fragmentation"] = overall

        except Exception as e:
            self.logger.error(f"Error analyzing fragmentation: {e}")

        return fragmentation_metrics

    async def defragment_storage(self, dry_run: bool = False) -> dict[str, Any]:
        """Defragment storage files and optimize layout."""
        results = {
            "operations_performed": [],
            "space_saved_mb": 0.0,
            "files_optimized": 0,
            "fragmentation_improvement": 0.0,
            "errors": [],
        }

        try:
            # Analyze current state
            initial_fragmentation = await self.analyze_fragmentation()

            # 1. Compact JSON files (remove unnecessary whitespace)
            slot_files = list(self.storage_dir.glob("*.json"))
            for slot_file in slot_files:
                try:
                    if not dry_run:
                        space_saved = await self._compact_json_file(slot_file)
                        results["space_saved_mb"] += space_saved / (1024 * 1024)
                    results["files_optimized"] += 1
                    results["operations_performed"].append(f"Compacted {slot_file.name}")
                except Exception as e:
                    results["errors"].append(f"Failed to compact {slot_file.name}: {e}")

            # 2. Consolidate index files
            if not dry_run:
                await self._consolidate_index_files()
                results["operations_performed"].append("Consolidated index files")

            # 3. Remove empty directories
            if not dry_run:
                removed_dirs = await self._cleanup_empty_directories()
                if removed_dirs:
                    results["operations_performed"].extend([f"Removed empty directory: {d}" for d in removed_dirs])

            # 4. Reorganize files by access patterns (optional optimization)
            if not dry_run:
                await self._reorganize_by_access_patterns()
                results["operations_performed"].append("Reorganized files by access patterns")

            # Calculate improvements
            if not dry_run:
                final_fragmentation = await self.analyze_fragmentation()
                improvement = (
                    initial_fragmentation["overall_fragmentation"] - final_fragmentation["overall_fragmentation"]
                )
                results["fragmentation_improvement"] = max(0.0, improvement)

        except Exception as e:
            results["errors"].append(f"Defragmentation error: {e}")
            self.logger.error(f"Defragmentation failed: {e}")

        return results

    async def _compact_json_file(self, file_path: Path) -> int:
        """Compact a JSON file by removing unnecessary whitespace."""
        original_size = (await aiofiles.os.stat(file_path)).st_size

        # Read and parse JSON
        async with aiofiles.open(file_path, encoding="utf-8") as f:
            data = json.loads(await f.read())

        # Write compacted version
        temp_path = file_path.with_suffix(".compact.tmp")
        async with aiofiles.open(temp_path, "w", encoding="utf-8") as f:
            await f.write(json.dumps(data, separators=(",", ":"), ensure_ascii=False))

        # Replace original with compacted version
        await aiofiles.os.rename(str(temp_path), str(file_path))

        new_size = (await aiofiles.os.stat(file_path)).st_size
        return original_size - new_size

    async def _consolidate_index_files(self):
        """Consolidate fragmented index files."""
        index_dir = self.storage_dir / "index"
        if not index_dir.exists():
            return

        # Load main index
        main_index_path = index_dir / "search_index.json"
        if not main_index_path.exists():
            return

        # Find and consolidate change files
        change_files = sorted(index_dir.glob("changes_*.json"))
        if not change_files:
            return

        # Load main index data
        async with aiofiles.open(main_index_path, encoding="utf-8") as f:
            main_data = json.loads(await f.read())

        # Apply all changes to main index
        for change_file in change_files:
            try:
                async with aiofiles.open(change_file, encoding="utf-8") as f:
                    change_data = json.loads(await f.read())

                # Apply changes (simplified merge)
                if "slot_updates" in change_data:
                    for slot_name, slot_data in change_data["slot_updates"].items():
                        if "word_counts" in slot_data:
                            main_data.setdefault("slot_word_counts", {})[slot_name] = slot_data["word_counts"]
                        if "total_words" in slot_data:
                            main_data.setdefault("slot_total_words", {})[slot_name] = slot_data["total_words"]
                        if "content_hash" in slot_data:
                            main_data.setdefault("slot_content_hashes", {})[slot_name] = slot_data["content_hash"]

            except Exception as e:
                self.logger.error(f"Failed to consolidate change file {change_file}: {e}")

        # Write consolidated index
        temp_path = main_index_path.with_suffix(".consolidated.tmp")
        async with aiofiles.open(temp_path, "w", encoding="utf-8") as f:
            await f.write(json.dumps(main_data, indent=2))

        await aiofiles.os.rename(str(temp_path), str(main_index_path))

        # Remove consolidated change files
        for change_file in change_files:
            await aiofiles.os.remove(change_file)

    async def _cleanup_empty_directories(self) -> list[str]:
        """Remove empty directories."""
        removed = []

        for item in self.storage_dir.rglob("*"):
            if item.is_dir() and item != self.storage_dir:
                try:
                    # Check if directory is empty
                    contents = list(item.iterdir())
                    if not contents:
                        await aiofiles.os.rmdir(item)
                        removed.append(str(item.relative_to(self.storage_dir)))
                except Exception:
                    pass  # Directory not empty or other error

        return removed

    async def _reorganize_by_access_patterns(self):
        """Reorganize files based on access patterns (placeholder for future optimization)."""
        # This would implement more sophisticated file organization
        # based on access frequency, size, etc.
        # For now, it's a placeholder that could sort files by access time
        pass


class QuotaManager:
    """Manages storage quotas and enforcement."""

    def __init__(self, storage_dir: Path, config: QuotaConfig):
        self.storage_dir = Path(storage_dir)
        self.config = config
        self.logger = logging.getLogger(__name__)

    async def check_quota_compliance(self) -> tuple[bool, list[str]]:
        """Check if current storage is within quota limits."""
        violations = []

        # Check total size
        stats = await StorageMonitor(self.storage_dir).get_storage_stats()

        if stats.total_size_mb > self.config.max_total_size_mb:
            violations.append(
                f"Total storage size ({stats.total_size_mb:.1f} MB) "
                f"exceeds limit ({self.config.max_total_size_mb:.1f} MB)"
            )

        # Check slot count
        if stats.total_slots > self.config.max_slots:
            violations.append(f"Number of slots ({stats.total_slots}) exceeds limit ({self.config.max_slots})")

        # Check individual slot sizes
        slot_files = list(self.storage_dir.glob("*.json"))
        for slot_file in slot_files:
            stat = await aiofiles.os.stat(slot_file)
            size_mb = stat.st_size / (1024 * 1024)
            if size_mb > self.config.max_slot_size_mb:
                violations.append(
                    f"Slot {slot_file.stem} ({size_mb:.1f} MB) exceeds limit ({self.config.max_slot_size_mb:.1f} MB)"
                )

        return len(violations) == 0, violations

    async def get_quota_usage(self) -> dict[str, float]:
        """Get current quota usage percentages."""
        stats = await StorageMonitor(self.storage_dir).get_storage_stats()

        return {
            "size_usage_percent": (stats.total_size_mb / self.config.max_total_size_mb) * 100,
            "slot_usage_percent": (stats.total_slots / self.config.max_slots) * 100,
        }

    async def enforce_quota(self, slot_name: str, new_slot_size_mb: float) -> tuple[bool, str]:
        """Enforce quota before allowing new slot creation/update."""
        # Check if new slot would exceed individual limit
        if new_slot_size_mb > self.config.max_slot_size_mb:
            return False, f"Slot size ({new_slot_size_mb:.1f} MB) exceeds limit ({self.config.max_slot_size_mb:.1f} MB)"

        # Check total limits
        stats = await StorageMonitor(self.storage_dir).get_storage_stats()

        # Account for existing slot if updating
        existing_slot_path = self.storage_dir / f"{slot_name}.json"
        existing_size_mb = 0.0
        if existing_slot_path.exists():
            stat = await aiofiles.os.stat(existing_slot_path)
            existing_size_mb = stat.st_size / (1024 * 1024)

        projected_total_size = stats.total_size_mb - existing_size_mb + new_slot_size_mb
        projected_slot_count = stats.total_slots + (1 if not existing_slot_path.exists() else 0)

        if projected_total_size > self.config.max_total_size_mb:
            return (
                False,
                (
                    f"Operation would exceed total size limit "
                    f"({projected_total_size:.1f}/{self.config.max_total_size_mb:.1f} MB)"
                ),
            )

        if projected_slot_count > self.config.max_slots:
            return False, f"Operation would exceed slot count limit ({projected_slot_count}/{self.config.max_slots})"

        return True, "Quota check passed"

    async def suggest_cleanup_actions(self) -> list[str]:
        """Suggest actions to reduce storage usage."""
        suggestions = []

        if not self.config.auto_cleanup_enabled:
            return suggestions

        # Find cleanup candidates
        monitor = StorageMonitor(self.storage_dir)
        candidates = await monitor.identify_cleanup_candidates(self.config.cleanup_threshold_days)

        if candidates:
            suggestions.append(
                f"Archive {len(candidates)} old slots (not accessed in {self.config.cleanup_threshold_days} days)"
            )

        # Check for compressed slots
        stats = await monitor.get_storage_stats()
        uncompressed_slots = stats.total_slots - stats.compressed_slots
        if uncompressed_slots > 0:
            suggestions.append(f"Compress {uncompressed_slots} uncompressed slots")

        # Check fragmentation
        defragmenter = StorageDefragmenter(self.storage_dir)
        fragmentation = await defragmenter.analyze_fragmentation()
        if fragmentation["overall_fragmentation"] > 0.3:
            suggestions.append("Run storage defragmentation to optimize space usage")

        return suggestions


class AlertManager:
    """Manages storage alerts and notifications."""

    def __init__(self, storage_dir: Path, quota_config: QuotaConfig | None = None):
        self.storage_dir = Path(storage_dir)
        self.quota_config = quota_config
        self.logger = logging.getLogger(__name__)
        self.alert_handlers: list[Callable[[StorageAlert], None]] = []

    def add_alert_handler(self, handler: Callable[[StorageAlert], None]):
        """Add alert handler function."""
        self.alert_handlers.append(handler)

    async def check_and_generate_alerts(self) -> list[StorageAlert]:
        """Check storage conditions and generate alerts."""
        alerts = []

        try:
            monitor = StorageMonitor(self.storage_dir)
            stats = await monitor.get_storage_stats()

            # Check quota alerts
            if self.quota_config:
                quota_manager = QuotaManager(self.storage_dir, self.quota_config)
                usage = await quota_manager.get_quota_usage()

                # Size quota alerts
                if usage["size_usage_percent"] >= self.quota_config.critical_threshold_percent:
                    alerts.append(
                        StorageAlert(
                            alert_type=AlertType.QUOTA_CRITICAL,
                            message=f"Storage usage critical: {usage['size_usage_percent']:.1f}% of quota used",
                            severity="critical",
                            timestamp=datetime.now(),
                            threshold_value=self.quota_config.critical_threshold_percent,
                            current_value=usage["size_usage_percent"],
                            suggested_action="Immediate cleanup required to prevent storage failures",
                        )
                    )
                elif usage["size_usage_percent"] >= self.quota_config.warning_threshold_percent:
                    alerts.append(
                        StorageAlert(
                            alert_type=AlertType.QUOTA_WARNING,
                            message=f"Storage usage warning: {usage['size_usage_percent']:.1f}% of quota used",
                            severity="warning",
                            timestamp=datetime.now(),
                            threshold_value=self.quota_config.warning_threshold_percent,
                            current_value=usage["size_usage_percent"],
                            suggested_action="Consider archiving old memory slots",
                        )
                    )

            # Check fragmentation
            defragmenter = StorageDefragmenter(self.storage_dir)
            fragmentation = await defragmenter.analyze_fragmentation()

            if fragmentation["overall_fragmentation"] > 0.5:
                alerts.append(
                    StorageAlert(
                        alert_type=AlertType.HIGH_FRAGMENTATION,
                        message=f"High storage fragmentation detected: {fragmentation['overall_fragmentation']:.1%}",
                        severity="warning",
                        timestamp=datetime.now(),
                        current_value=fragmentation["overall_fragmentation"] * 100,
                        threshold_value=50.0,
                        suggested_action="Run defragmentation to optimize storage layout",
                    )
                )

            # Check cleanup needs
            cleanup_candidates = await monitor.identify_cleanup_candidates(30)
            if len(cleanup_candidates) > 10:
                alerts.append(
                    StorageAlert(
                        alert_type=AlertType.CLEANUP_NEEDED,
                        message=f"{len(cleanup_candidates)} memory slots haven't been accessed in 30+ days",
                        severity="info",
                        timestamp=datetime.now(),
                        current_value=len(cleanup_candidates),
                        suggested_action="Consider archiving unused memory slots",
                    )
                )

            # Check performance indicators
            if stats.index_size_mb > 100:  # 100MB index suggests performance issues
                alerts.append(
                    StorageAlert(
                        alert_type=AlertType.PERFORMANCE_DEGRADED,
                        message=f"Large search index may impact performance: {stats.index_size_mb:.1f} MB",
                        severity="warning",
                        timestamp=datetime.now(),
                        current_value=stats.index_size_mb,
                        threshold_value=100.0,
                        suggested_action="Consider index optimization or archiving old content",
                    )
                )

        except Exception as e:
            self.logger.error(f"Error generating alerts: {e}")

        # Notify handlers
        for alert in alerts:
            for handler in self.alert_handlers:
                try:
                    handler(alert)
                except Exception as e:
                    self.logger.error(f"Alert handler error: {e}")

        return alerts

    def default_alert_handler(self, alert: StorageAlert):
        """Default alert handler that logs alerts."""
        level = logging.INFO
        if alert.severity == "warning":
            level = logging.WARNING
        elif alert.severity == "critical":
            level = logging.CRITICAL

        self.logger.log(level, f"[{alert.alert_type.value}] {alert.message}")
        if alert.suggested_action:
            self.logger.log(level, f"Suggested action: {alert.suggested_action}")


class AutomaticOptimizer:
    """Coordinates automatic storage optimizations."""

    def __init__(self, storage_dir: Path, quota_config: QuotaConfig | None = None):
        self.storage_dir = Path(storage_dir)
        self.quota_config = quota_config
        self.logger = logging.getLogger(__name__)

    async def run_optimization_cycle(self) -> dict[str, Any]:
        """Run a complete optimization cycle."""
        results = {
            "timestamp": datetime.now().isoformat(),
            "operations": [],
            "alerts_generated": 0,
            "space_saved_mb": 0.0,
            "errors": [],
        }

        try:
            # 1. Generate and handle alerts
            alert_manager = AlertManager(self.storage_dir, self.quota_config)
            alert_manager.add_alert_handler(alert_manager.default_alert_handler)
            alerts = await alert_manager.check_and_generate_alerts()
            results["alerts_generated"] = len(alerts)

            # 2. Auto-cleanup if quota config allows
            if self.quota_config and self.quota_config.auto_cleanup_enabled:
                monitor = StorageMonitor(self.storage_dir)
                cleanup_candidates = await monitor.identify_cleanup_candidates(self.quota_config.cleanup_threshold_days)

                # Only cleanup if we have quota pressure
                usage = await QuotaManager(self.storage_dir, self.quota_config).get_quota_usage()
                if usage["size_usage_percent"] > self.quota_config.warning_threshold_percent:
                    # Would integrate with archival system here
                    results["operations"].append(f"Identified {len(cleanup_candidates)} cleanup candidates")

            # 3. Auto-defragmentation if fragmentation is high
            defragmenter = StorageDefragmenter(self.storage_dir)
            fragmentation = await defragmenter.analyze_fragmentation()

            if fragmentation["overall_fragmentation"] > 0.3:
                defrag_results = await defragmenter.defragment_storage(dry_run=False)
                results["operations"].extend(defrag_results["operations_performed"])
                results["space_saved_mb"] += defrag_results.get("space_saved_mb", 0.0)
                results["errors"].extend(defrag_results.get("errors", []))

            # 4. Cleanup temporary files
            temp_cleaned = await monitor.cleanup_temporary_files()
            if temp_cleaned > 0:
                results["operations"].append(f"Cleaned {temp_cleaned} temporary files")

        except Exception as e:
            results["errors"].append(f"Optimization cycle error: {e}")
            self.logger.error(f"Optimization cycle failed: {e}")

        return results
