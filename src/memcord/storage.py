"""Storage management for memory slots."""

import asyncio
import json
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Any

import aiofiles
import aiofiles.os

from .archival import ArchivalManager
from .cache import (
    CacheLevel,
    CacheManager,
    generate_search_cache_key,
    generate_slot_cache_key,
)
from .compression import ContentCompressor
from .memory_manager import MemoryAlert, MemoryManager
from .models import (
    CompressionInfo,
    GroupInfo,
    MemoryEntry,
    MemorySlot,
    SearchQuery,
    SearchResult,
    ServerState,
)
from .search import SearchEngine
from .storage_efficiency import (
    DeltaCompressor,
    IncrementalSearchIndex,
    StorageMonitor,
    StorageStats,
    StreamingOperations,
)


class StorageManager:
    """Manages file-based storage for memory slots."""

    def __init__(
        self,
        memory_dir: str = "memory_slots",
        shared_dir: str = "shared_memories",
        enable_caching: bool = True,
        enable_efficiency: bool = True,
        enable_memory_management: bool = True,
    ):
        # Convert to absolute paths to prevent working directory issues
        # Use .absolute() instead of .resolve() to avoid requiring path to exist
        self.memory_dir = Path(memory_dir).expanduser().absolute()
        self.shared_dir = Path(shared_dir).expanduser().absolute()
        self._lock = asyncio.Lock()
        self._state = ServerState()
        self._search_engine = SearchEngine()
        self._compressor = ContentCompressor()
        self._archival_manager = ArchivalManager(str(self.memory_dir), str(self.memory_dir.parent / "archives"))

        # Initialize caching system
        self.enable_caching = enable_caching
        self._cache_manager: CacheManager | None = None
        if enable_caching:
            self._cache_manager = CacheManager(
                memory_cache_size=1000,
                memory_cache_memory_mb=50,
                disk_cache_dir=str(self.memory_dir / "cache"),
                disk_cache_max_files=5000,
                enable_predictive_loading=True,
            )

        # Initialize storage efficiency enhancements
        self.enable_efficiency = enable_efficiency
        self._incremental_index: IncrementalSearchIndex | None = None
        self._delta_compressor: DeltaCompressor | None = None
        self._storage_monitor: StorageMonitor | None = None

        if enable_efficiency:
            self._incremental_index = IncrementalSearchIndex(self.memory_dir / "index")
            self._delta_compressor = DeltaCompressor(self.memory_dir)
            self._storage_monitor = StorageMonitor(self.memory_dir)

        # Initialize memory management
        self.enable_memory_management = enable_memory_management
        self._memory_manager: MemoryManager | None = None
        if enable_memory_management:
            # Configure reasonable defaults (500MB limit, monitoring enabled)
            self._memory_manager = MemoryManager(
                enable_tracemalloc=True,
                memory_limit_mb=500.0,  # 500MB default limit
                warning_threshold=0.8,
                critical_threshold=0.9,
            )

        # Ensure directories exist
        self.memory_dir.mkdir(exist_ok=True)
        self.shared_dir.mkdir(exist_ok=True)

        # Flag to track if subsystems are initialized
        self._search_initialized = False
        self._cache_initialized = False
        self._efficiency_initialized = False
        self._memory_management_initialized = False

    async def _ensure_cache_initialized(self):
        """Initialize cache manager if not already initialized."""
        if self.enable_caching and self._cache_manager and not self._cache_initialized:
            await self._cache_manager.initialize()
            self._cache_initialized = True

    async def _ensure_efficiency_initialized(self):
        """Initialize efficiency enhancements if not already initialized."""
        if self.enable_efficiency and not self._efficiency_initialized:
            if self._incremental_index:
                await self._incremental_index.initialize()
            self._efficiency_initialized = True

    async def _ensure_memory_management_initialized(self):
        """Initialize memory management if not already initialized."""
        if self.enable_memory_management and self._memory_manager and not self._memory_management_initialized:
            await self._memory_manager.start_monitoring(interval=30.0)
            self._memory_management_initialized = True

    async def shutdown(self):
        """Shutdown storage manager and all subsystems."""
        if self._cache_manager:
            await self._cache_manager.shutdown()
        if self._incremental_index:
            await self._incremental_index.shutdown()
        if self._memory_manager:
            await self._memory_manager.stop_monitoring()

    async def _get_slot_path(self, slot_name: str) -> Path:
        """Get the file path for a memory slot."""
        return self.memory_dir / f"{slot_name}.json"

    async def _load_slot(self, slot_name: str) -> MemorySlot | None:
        """Load memory slot from file with cache invalidation on file changes."""
        await self._ensure_cache_initialized()

        slot_path = await self._get_slot_path(slot_name)
        if not slot_path.exists():
            return None

        # Get file modification time for cache invalidation
        file_mtime = slot_path.stat().st_mtime

        # Try cache first if enabled
        if self._cache_manager:
            cache_key = generate_slot_cache_key(slot_name)
            cached_data, hit = await self._cache_manager.get(cache_key, CacheLevel.MEMORY)

            if hit:
                try:
                    # Check if file was modified since cache
                    cache_mtime = cached_data.get("_file_mtime")

                    if cache_mtime and file_mtime <= cache_mtime:
                        # File unchanged, use cache
                        cached_data_clean = {k: v for k, v in cached_data.items() if not k.startswith("_")}
                        return MemorySlot(**cached_data_clean)
                    else:
                        # File changed externally, invalidate cache
                        await self._cache_manager.remove(cache_key)
                except Exception:
                    # Cache corruption, fall back to disk
                    await self._cache_manager.remove(cache_key)

        # Load from file (cache miss or invalidated)
        try:
            async with aiofiles.open(slot_path, encoding="utf-8") as f:
                data = await f.read()
                slot_data = json.loads(data)
                slot = MemorySlot(**slot_data)

                # Cache with file mtime for invalidation
                if self._cache_manager:
                    cache_key = generate_slot_cache_key(slot_name)
                    cache_data = slot.model_dump()
                    cache_data["_file_mtime"] = file_mtime  # Store mtime for future checks

                    await self._cache_manager.put(
                        cache_key,
                        cache_data,
                        CacheLevel.MEMORY,
                        ttl_seconds=3600,  # Cache for 1 hour
                    )

                return slot
        except (json.JSONDecodeError, ValueError) as e:
            raise ValueError(f"Error loading slot '{slot_name}': {e}") from e

    async def _save_slot(self, slot: MemorySlot) -> None:
        """Save memory slot to file with efficiency enhancements."""
        await self._ensure_cache_initialized()
        await self._ensure_efficiency_initialized()

        slot_path = await self._get_slot_path(slot.slot_name)
        old_slot = None

        # Load existing slot for delta compression
        if slot_path.exists() and self._delta_compressor:
            try:
                old_slot = await self._load_slot(slot.slot_name)
            except Exception:
                pass  # Continue with full save

        # Create delta if we have old version and compression enabled
        if old_slot and self._delta_compressor:
            try:
                await self._delta_compressor.create_delta(slot.slot_name, old_slot, slot)
            except Exception as e:
                print(f"Warning: Could not create delta for {slot.slot_name}: {e}")

        # Create a backup if file exists
        if slot_path.exists():
            backup_path = slot_path.with_suffix(".json.bak")
            await aiofiles.os.rename(str(slot_path), str(backup_path))

        try:
            # Use streaming operations for large slots
            content_size = sum(len(entry.content) for entry in slot.entries)
            if content_size > 1024 * 1024:  # 1MB threshold
                await StreamingOperations.write_slot_streaming(slot, slot_path)
            else:
                # Standard write for smaller slots
                slot_dict = slot.model_dump()
                slot_dict = self._serialize_datetime(slot_dict)

                async with aiofiles.open(slot_path, "w", encoding="utf-8") as f:
                    await f.write(json.dumps(slot_dict, indent=2, ensure_ascii=False))

            # Remove backup on successful save
            backup_path = slot_path.with_suffix(".json.bak")
            if backup_path.exists():
                await aiofiles.os.remove(str(backup_path))

            # Update cache with new slot data
            if self._cache_manager:
                cache_key = generate_slot_cache_key(slot.slot_name)
                await self._cache_manager.put(cache_key, slot.model_dump(), CacheLevel.MEMORY, ttl_seconds=3600)

                await self._invalidate_search_caches(slot.slot_name)

            # Update global tags
            for tag in slot.tags:
                self._state.add_tag_to_global_set(tag)

            # Update group information
            if slot.group_path:
                from .models import GroupInfo

                if slot.group_path not in self._state.groups:
                    group_info = GroupInfo(
                        path=slot.group_path,
                        name=slot.group_path.split("/")[-1],
                        parent_path="/".join(slot.group_path.split("/")[:-1]) if "/" in slot.group_path else None,
                    )
                    self._state.add_group(group_info)

                self._state.groups[slot.group_path].updated_at = datetime.now()

            # Update search indexes (both old and new)
            self._search_engine.add_slot(slot)

            # Update incremental index if enabled
            if self._incremental_index:
                try:
                    updated = await self._incremental_index.add_or_update_slot(slot)
                    if updated:
                        print(f"Incremental index updated for slot: {slot.slot_name}")
                except Exception as e:
                    print(f"Warning: Could not update incremental index: {e}")

        except Exception as e:
            # Restore backup if save failed
            backup_path = slot_path.with_suffix(".json.bak")
            if backup_path.exists():
                await aiofiles.os.rename(str(backup_path), str(slot_path))
            raise ValueError(f"Error saving slot '{slot.slot_name}': {e}") from e

    async def _invalidate_search_caches(self, slot_name: str):
        """Invalidate search caches that might be affected by slot changes."""
        if not self._cache_manager:
            return

        # This is a simplified invalidation strategy
        # In production, you might want to be more selective about which caches to invalidate
        # For now, we'll clear all search-related cache entries
        # A more sophisticated approach would track which searches return specific slots

        # Note: This is a placeholder implementation
        # The actual cache doesn't provide a way to iterate through keys,
        # so we'll rely on TTL expiration for search cache invalidation
        pass

    def _serialize_datetime(self, obj: Any) -> Any:
        """Convert datetime objects and sets to JSON-serializable format."""
        if isinstance(obj, datetime):
            return obj.isoformat()
        elif isinstance(obj, set):
            return sorted(obj)  # Convert sets to sorted lists
        elif isinstance(obj, dict):
            return {k: self._serialize_datetime(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._serialize_datetime(item) for item in obj]
        return obj

    async def create_or_get_slot(self, slot_name: str) -> MemorySlot:
        """Create a new slot or get existing one."""
        # Validate slot name
        if not slot_name or not slot_name.strip():
            raise ValueError("Slot name cannot be empty")

        async with self._lock:
            slot = await self._load_slot(slot_name)

            if slot is None:
                slot = MemorySlot(slot_name=slot_name)
                await self._save_slot(slot)
                self._search_engine.add_slot(slot)
            else:
                # Only update search index if slot content changed
                if (
                    slot_name not in self._search_engine.slots_cache
                    or self._search_engine.slots_cache[slot_name].updated_at != slot.updated_at
                ):
                    self._search_engine.add_slot(slot)

            self._state.set_current_slot(slot_name)
            return slot

    async def save_memory(self, slot_name: str, content: str, entry_type: str = "manual_save") -> MemoryEntry:
        """Save content to memory slot."""
        # Validate content
        if not content or not content.strip():
            raise ValueError("Content cannot be empty")

        async with self._lock:
            slot = await self._load_slot(slot_name)

            if slot is None:
                slot = MemorySlot(slot_name=slot_name)

            entry = MemoryEntry(type=entry_type, content=content, timestamp=datetime.now())

            if entry_type == "manual_save":
                # For manual saves, replace all content
                slot.entries = [entry]
            else:
                # For other types, append
                slot.add_entry(entry)

            await self._save_slot(slot)
            self._search_engine.add_slot(slot)  # Update search index
            return entry

    async def read_memory(self, slot_name: str) -> MemorySlot | None:
        """Read memory slot content."""
        return await self._load_slot(slot_name)

    async def list_memory_slots(self) -> list[dict[str, Any]]:
        """List all available memory slots with metadata."""
        slots_info = []

        for slot_file in self.memory_dir.glob("*.json"):
            slot_name = slot_file.stem
            try:
                slot = await self._load_slot(slot_name)
                if slot:
                    slots_info.append(
                        {
                            "name": slot_name,
                            "created_at": slot.created_at.isoformat(),
                            "updated_at": slot.updated_at.isoformat(),
                            "entry_count": len(slot.entries),
                            "total_length": slot.get_total_content_length(),
                            "is_current": slot_name == self._state.current_slot,
                        }
                    )
            except Exception:
                # Skip corrupted slots
                continue

        return sorted(slots_info, key=lambda x: x["updated_at"], reverse=True)

    async def add_summary_entry(self, slot_name: str, original_content: str, summary: str) -> MemoryEntry:
        """Add a summary entry to a memory slot."""
        async with self._lock:
            slot = await self._load_slot(slot_name)

            if slot is None:
                slot = MemorySlot(slot_name=slot_name)

            entry = MemoryEntry(
                type="auto_summary",
                content=summary,
                timestamp=datetime.now(),
                original_length=len(original_content),
                summary_length=len(summary),
            )

            slot.add_entry(entry)
            await self._save_slot(slot)
            self._search_engine.add_slot(slot)  # Update search index
            return entry

    def get_current_slot(self) -> str | None:
        """Get the currently active slot name."""
        return self._state.current_slot

    async def export_slot_to_file(self, slot_name: str, format: str, output_path: str | None = None) -> str:
        """Export memory slot to a file in the specified format."""
        slot = await self._load_slot(slot_name)
        if not slot:
            raise ValueError(f"Memory slot '{slot_name}' not found")

        if output_path is None:
            output_path = str(self.shared_dir / f"{slot_name}.{format}")

        if format == "md":
            content = self._format_as_markdown(slot)
        elif format == "txt":
            content = self._format_as_text(slot)
        elif format == "json":
            content = self._format_as_json(slot)
        else:
            raise ValueError(f"Unsupported format: {format}")

        async with aiofiles.open(output_path, "w", encoding="utf-8") as f:
            await f.write(content)

        return output_path

    def _format_as_markdown(self, slot: MemorySlot) -> str:
        """Format memory slot as Markdown."""
        lines = [f"# Memory Slot: {slot.slot_name}", ""]

        # Add metadata
        lines.extend(
            [
                f"**Created:** {slot.created_at.strftime('%Y-%m-%d %H:%M:%S')}",
                f"**Updated:** {slot.updated_at.strftime('%Y-%m-%d %H:%M:%S')}",
                f"**Entries:** {len(slot.entries)}",
            ]
        )

        # Add tags if present
        if slot.tags:
            lines.append(f"**Tags:** {', '.join(sorted(slot.tags))}")

        # Add group if present
        if slot.group_path:
            lines.append(f"**Group:** {slot.group_path}")

        # Add description if present
        if slot.description:
            lines.append(f"**Description:** {slot.description}")

        lines.append("")

        for i, entry in enumerate(slot.entries):
            entry_type = "Manual Save" if entry.type == "manual_save" else "Auto Summary"
            lines.extend([f"## {entry_type} - {entry.timestamp.strftime('%Y-%m-%d %H:%M:%S')}", ""])

            if entry.type == "auto_summary" and entry.original_length and entry.summary_length:
                compression = (entry.summary_length / entry.original_length) * 100
                lines.extend(
                    [
                        (
                            f"**Summary Length:** {entry.summary_length}/{entry.original_length} "
                            f"characters ({compression:.1f}%)"
                        ),
                        "",
                    ]
                )

            lines.extend([entry.content, ""])

            if i < len(slot.entries) - 1:
                lines.append("---")
                lines.append("")

        lines.extend(["---", "*Exported via Chat Memory MCP Server*"])

        return "\n".join(lines)

    def _format_as_text(self, slot: MemorySlot) -> str:
        """Format memory slot as plain text."""
        lines = [
            f"MEMORY SLOT: {slot.slot_name}",
            f"Created: {slot.created_at.strftime('%Y-%m-%d %H:%M:%S')}",
            f"Updated: {slot.updated_at.strftime('%Y-%m-%d %H:%M:%S')}",
            f"Entries: {len(slot.entries)}",
        ]

        # Add tags if present
        if slot.tags:
            lines.append(f"Tags: {', '.join(sorted(slot.tags))}")

        # Add group if present
        if slot.group_path:
            lines.append(f"Group: {slot.group_path}")

        # Add description if present
        if slot.description:
            lines.append(f"Description: {slot.description}")

        lines.append("")

        for entry in slot.entries:
            entry_type = "MANUAL SAVE" if entry.type == "manual_save" else "AUTO SUMMARY"
            lines.extend([f"=== {entry_type} ({entry.timestamp.strftime('%Y-%m-%d %H:%M:%S')}) ===", entry.content, ""])

        lines.append("--- Exported via Chat Memory MCP Server ---")
        return "\n".join(lines)

    def _format_as_json(self, slot: MemorySlot) -> str:
        """Format memory slot as JSON."""
        export_data = {
            "slot_name": slot.slot_name,
            "name": slot.slot_name,  # Backward compatibility
            "exported_at": datetime.now().isoformat(),
            "created_at": slot.created_at.isoformat(),
            "updated_at": slot.updated_at.isoformat(),
            "entry_count": len(slot.entries),
            "tags": sorted(slot.tags) if slot.tags else [],
            "group_path": slot.group_path,
            "description": slot.description,
            "priority": slot.priority,
            "entries": [
                {
                    "type": entry.type,
                    "content": entry.content,
                    "timestamp": entry.timestamp.isoformat(),
                    "original_length": entry.original_length,
                    "summary_length": entry.summary_length,
                    "metadata": entry.metadata,
                }
                for entry in slot.entries
            ],
            "export_format": "mcp_memory_v1",
        }

        return json.dumps(export_data, indent=2, ensure_ascii=False)

    async def _initialize_search_index(self) -> None:
        """Initialize search index with existing memory slots."""
        try:
            for slot_file in self.memory_dir.glob("*.json"):
                slot_name = slot_file.stem
                slot = await self._load_slot(slot_name)
                if slot:
                    self._search_engine.add_slot(slot)
                    # Update global tags
                    for tag in slot.tags:
                        self._state.add_tag_to_global_set(tag)
        except Exception as e:
            print(f"Warning: Error initializing search index: {e}")
        finally:
            self._search_initialized = True

    async def search_memory(self, query: SearchQuery) -> list[SearchResult]:
        """Search across all memory slots with caching support."""
        await self._ensure_cache_initialized()

        # Try cache first if enabled
        if self._cache_manager:
            cache_key = generate_search_cache_key(query)
            cached_results, hit = await self._cache_manager.get(cache_key, CacheLevel.DISK)
            if hit:
                try:
                    # Convert cached data back to SearchResult objects
                    return [SearchResult(**result_data) for result_data in cached_results]
                except Exception:
                    # Cache corruption, fall back to fresh search
                    await self._cache_manager.remove(cache_key)

        # Initialize search index if needed
        if not self._search_initialized:
            await self._initialize_search_index()
            self._search_initialized = True

        # Perform search
        results = self._search_engine.search(query)

        # Cache the search results if caching is enabled
        if self._cache_manager and results:
            cache_key = generate_search_cache_key(query)
            # Convert SearchResult objects to dicts for caching
            cached_data = [result.model_dump() for result in results]
            await self._cache_manager.put(
                cache_key,
                cached_data,
                CacheLevel.DISK,
                ttl_seconds=1800,  # Cache search results for 30 minutes
            )

        return results

    async def add_tag_to_slot(self, slot_name: str, tag: str) -> bool:
        """Add a tag to a memory slot."""
        async with self._lock:
            slot = await self._load_slot(slot_name)
            if not slot:
                return False

            slot.add_tag(tag)
            await self._save_slot(slot)
            self._search_engine.add_slot(slot)  # Update search index
            self._state.add_tag_to_global_set(tag)
            return True

    async def remove_tag_from_slot(self, slot_name: str, tag: str) -> bool:
        """Remove a tag from a memory slot."""
        async with self._lock:
            slot = await self._load_slot(slot_name)
            if not slot:
                return False

            removed = slot.remove_tag(tag)
            if removed:
                await self._save_slot(slot)
                self._search_engine.add_slot(slot)  # Update search index

                # Check if tag is still used by other slots
                tag_still_used = False
                for slot_file in self.memory_dir.glob("*.json"):
                    if slot_file.stem != slot_name:
                        other_slot = await self._load_slot(slot_file.stem)
                        if other_slot and other_slot.has_tag(tag):
                            tag_still_used = True
                            break

                if not tag_still_used:
                    self._state.remove_tag_from_global_set(tag)

            return removed

    async def list_all_tags(self) -> list[str]:
        """List all tags used across memory slots."""
        return sorted(self._state.all_tags)

    async def set_slot_group(self, slot_name: str, group_path: str | None) -> bool:
        """Set the group path for a memory slot."""
        async with self._lock:
            slot = await self._load_slot(slot_name)
            if not slot:
                return False

            old_group = slot.group_path
            slot.set_group(group_path)
            await self._save_slot(slot)
            self._search_engine.add_slot(slot)  # Update search index

            # Update group information
            if old_group and old_group in self._state.groups:
                self._state.groups[old_group].member_count -= 1

            if group_path:
                if group_path not in self._state.groups:
                    # Create new group
                    group_info = GroupInfo(
                        path=group_path,
                        name=group_path.split("/")[-1],
                        parent_path="/".join(group_path.split("/")[:-1]) if "/" in group_path else None,
                    )
                    self._state.add_group(group_info)

                self._state.groups[group_path].member_count += 1
                self._state.groups[group_path].updated_at = datetime.now()

            return True

    async def list_groups(self) -> list[GroupInfo]:
        """List all memory groups."""
        # Dynamically update member counts
        group_counts = {}
        for slot_file in self.memory_dir.glob("*.json"):
            slot_name = slot_file.stem
            try:
                slot = await self._load_slot(slot_name)
                if slot and slot.group_path:
                    group_counts[slot.group_path] = group_counts.get(slot.group_path, 0) + 1
            except Exception:
                continue

        # Update member counts in groups
        for group_path, count in group_counts.items():
            if group_path in self._state.groups:
                self._state.groups[group_path].member_count = count

        return list(self._state.groups.values())

    async def _delete_slot_internal(self, slot_name: str) -> bool:
        """Internal delete slot method - assumes lock is already held."""
        slot_path = await self._get_slot_path(slot_name)
        if not slot_path.exists():
            return False

        # Remove from search index
        self._search_engine.remove_slot(slot_name)

        # Remove from current slot if it's current
        if self._state.current_slot == slot_name:
            self._state.current_slot = None

        # Remove from available slots
        if slot_name in self._state.available_slots:
            self._state.available_slots.remove(slot_name)

        # Invalidate cache
        await self.invalidate_slot_cache(slot_name)

        # Delete file
        await aiofiles.os.remove(str(slot_path))
        return True

    async def delete_slot(self, slot_name: str) -> bool:
        """Delete a memory slot."""
        async with self._lock:
            return await self._delete_slot_internal(slot_name)

    async def get_search_stats(self) -> dict[str, Any]:
        """Get search engine statistics."""
        return self._search_engine.get_stats()

    def get_server_state(self) -> ServerState:
        """Get the current server state."""
        return self._state

    async def compress_slot(self, slot_name: str, force: bool = False) -> dict[str, Any]:
        """Compress content in a memory slot."""
        async with self._lock:
            slot = await self._load_slot(slot_name)
            if not slot:
                raise ValueError(f"Memory slot '{slot_name}' not found")

            compression_stats = {
                "slot_name": slot_name,
                "entries_processed": 0,
                "entries_compressed": 0,
                "original_size": 0,
                "compressed_size": 0,
                "space_saved": 0,
                "compression_ratio": 1.0,
            }

            entries_modified = False

            for entry in slot.entries:
                original_size = len(entry.content.encode("utf-8"))
                compression_stats["original_size"] += original_size
                compression_stats["entries_processed"] += 1

                # Skip if already compressed and not forcing
                if entry.compression_info.is_compressed and not force:
                    compression_stats["compressed_size"] += entry.compression_info.compressed_size or original_size
                    continue

                # Check if content should be compressed
                if self._compressor.should_compress(entry.content) or force:
                    try:
                        compressed_content, metadata = self._compressor.compress_json_content(entry.content)

                        # Update entry with compressed content
                        entry.content = compressed_content
                        entry.compression_info = CompressionInfo(
                            is_compressed=True,
                            algorithm=metadata.algorithm,
                            original_size=metadata.original_size,
                            compressed_size=metadata.compressed_size,
                            compression_ratio=metadata.compression_ratio,
                            compressed_at=metadata.compressed_at,
                        )

                        compression_stats["entries_compressed"] += 1
                        compression_stats["compressed_size"] += metadata.compressed_size
                        entries_modified = True

                    except Exception as e:
                        print(f"Warning: Failed to compress entry in slot {slot_name}: {e}")
                        compression_stats["compressed_size"] += original_size
                else:
                    compression_stats["compressed_size"] += original_size

            # Save slot if any entries were modified
            if entries_modified:
                await self._save_slot(slot)
                self._search_engine.add_slot(slot)  # Update search index

            # Calculate final statistics
            compression_stats["space_saved"] = compression_stats["original_size"] - compression_stats["compressed_size"]
            compression_stats["compression_ratio"] = (
                compression_stats["compressed_size"] / compression_stats["original_size"]
                if compression_stats["original_size"] > 0
                else 1.0
            )

            return compression_stats

    async def decompress_slot(self, slot_name: str) -> dict[str, Any]:
        """Decompress content in a memory slot."""
        async with self._lock:
            slot = await self._load_slot(slot_name)
            if not slot:
                raise ValueError(f"Memory slot '{slot_name}' not found")

            decompression_stats = {
                "slot_name": slot_name,
                "entries_processed": 0,
                "entries_decompressed": 0,
                "decompressed_successfully": True,
            }

            entries_modified = False

            for entry in slot.entries:
                decompression_stats["entries_processed"] += 1

                if entry.compression_info.is_compressed:
                    try:
                        # Decompress content
                        from .compression import CompressionMetadata

                        metadata = CompressionMetadata(
                            algorithm=entry.compression_info.algorithm,
                            original_size=entry.compression_info.original_size or 0,
                            compressed_size=entry.compression_info.compressed_size or 0,
                            compression_ratio=entry.compression_info.compression_ratio or 1.0,
                            compressed_at=entry.compression_info.compressed_at or datetime.now(),
                        )

                        decompressed_content = self._compressor.decompress_json_content(entry.content, metadata)

                        # Update entry with decompressed content
                        entry.content = decompressed_content
                        entry.compression_info = CompressionInfo()  # Reset compression info

                        decompression_stats["entries_decompressed"] += 1
                        entries_modified = True

                    except Exception as e:
                        print(f"Warning: Failed to decompress entry in slot {slot_name}: {e}")
                        decompression_stats["decompressed_successfully"] = False

            # Save slot if any entries were modified
            if entries_modified:
                await self._save_slot(slot)
                self._search_engine.add_slot(slot)  # Update search index

            return decompression_stats

    async def get_compression_stats(self, slot_name: str | None = None) -> dict[str, Any]:
        """Get compression statistics for a slot or all slots."""
        if slot_name:
            slot = await self._load_slot(slot_name)
            if not slot:
                raise ValueError(f"Memory slot '{slot_name}' not found")
            return slot.get_compression_stats()
        else:
            # Get stats for all slots
            all_stats = {
                "total_slots": 0,
                "total_entries": 0,
                "compressed_entries": 0,
                "total_original_size": 0,
                "total_compressed_size": 0,
                "slot_stats": {},
            }

            for slot_file in self.memory_dir.glob("*.json"):
                slot_name = slot_file.stem
                try:
                    slot = await self._load_slot(slot_name)
                    if slot:
                        stats = slot.get_compression_stats()
                        all_stats["total_slots"] += 1
                        all_stats["total_entries"] += stats["total_entries"]
                        all_stats["compressed_entries"] += stats["compressed_entries"]
                        all_stats["total_original_size"] += stats["total_original_size"]
                        all_stats["total_compressed_size"] += stats["total_compressed_size"]
                        all_stats["slot_stats"][slot_name] = stats
                except Exception:
                    continue

            # Calculate overall compression ratio
            all_stats["compression_ratio"] = (
                all_stats["total_compressed_size"] / all_stats["total_original_size"]
                if all_stats["total_original_size"] > 0
                else 1.0
            )
            all_stats["space_saved"] = all_stats["total_original_size"] - all_stats["total_compressed_size"]
            all_stats["space_saved_percentage"] = (1 - all_stats["compression_ratio"]) * 100

            return all_stats

    async def archive_slot(self, slot_name: str, reason: str = "manual") -> dict[str, Any]:
        """Archive a memory slot."""
        async with self._lock:
            slot = await self._load_slot(slot_name)
            if not slot:
                raise ValueError(f"Memory slot '{slot_name}' not found")

            # Archive the slot
            archive_entry = await self._archival_manager.archive_slot(slot, reason)

            # Remove from active storage
            await self._delete_slot_internal(slot_name)

            return {
                "slot_name": slot_name,
                "archived_at": archive_entry.archived_at.isoformat(),
                "archive_reason": reason,
                "original_size": archive_entry.original_size,
                "archived_size": archive_entry.archived_size,
                "compression_ratio": archive_entry.compression_ratio,
                "space_saved": archive_entry.original_size - archive_entry.archived_size,
            }

    async def restore_from_archive(self, slot_name: str) -> dict[str, Any]:
        """Restore a memory slot from archive."""
        async with self._lock:
            # Check if slot already exists in active storage
            if await self._load_slot(slot_name):
                raise ValueError(f"Memory slot '{slot_name}' already exists in active storage")

            # Restore from archive
            slot = await self._archival_manager.restore_slot(slot_name)

            # Save to active storage
            await self._save_slot(slot)
            self._search_engine.add_slot(slot)

            # Remove from archive (optional - could keep for backup)
            # await self._archival_manager.delete_archive(slot_name)

            return {
                "slot_name": slot_name,
                "restored_at": datetime.now().isoformat(),
                "entry_count": len(slot.entries),
                "total_size": slot.get_total_content_length(),
            }

    async def list_archives(self, include_stats: bool = False) -> list[dict[str, Any]]:
        """List all archived memory slots."""
        return await self._archival_manager.list_archives(include_stats)

    async def get_archive_stats(self) -> dict[str, Any]:
        """Get archive statistics."""
        return await self._archival_manager.get_archive_stats()

    async def find_archival_candidates(self, days_inactive: int = 30) -> list[tuple[str, dict[str, Any]]]:
        """Find memory slots that could be archived."""
        return await self._archival_manager.find_candidates_for_archival(days_inactive)

    async def get_cache_stats(self) -> dict[str, Any] | None:
        """Get comprehensive cache statistics."""
        if not self._cache_manager:
            return None

        return await self._cache_manager.get_stats()

    async def clear_cache(self) -> bool:
        """Clear all cache data."""
        if not self._cache_manager:
            return False

        await self._cache_manager.clear()
        return True

    async def warm_cache_for_slots(self, slot_names: list[str]) -> int:
        """Pre-warm cache for specified slots."""
        if not self._cache_manager:
            return 0

        warmed_count = 0
        for slot_name in slot_names:
            try:
                # Load slot into cache
                slot = await self._load_slot(slot_name)
                if slot:
                    warmed_count += 1
            except Exception as e:
                print(f"Warning: Failed to warm cache for slot {slot_name}: {e}")

        return warmed_count

    async def invalidate_slot_cache(self, slot_name: str) -> bool:
        """Invalidate cache for a specific slot."""
        if not self._cache_manager:
            return False

        cache_key = generate_slot_cache_key(slot_name)
        await self._cache_manager.remove(cache_key)
        return True

    # Storage Efficiency Methods

    async def get_storage_stats(self) -> StorageStats:
        """Get comprehensive storage statistics."""
        await self._ensure_efficiency_initialized()

        if not self._storage_monitor:
            # Fallback basic stats
            return StorageStats(
                total_slots=len(self._state.available_slots),
                total_size_mb=0.0,
                compressed_slots=0,
                compression_ratio=0.0,
                fragmentation_ratio=0.0,
                oldest_access=datetime.now(),
                newest_access=datetime.now(),
                index_size_mb=0.0,
                cache_size_mb=0.0,
            )

        return await self._storage_monitor.get_storage_stats()

    async def cleanup_storage(self, days_old: int = 30) -> dict[str, Any]:
        """Clean up old temporary files and identify cleanup candidates."""
        await self._ensure_efficiency_initialized()

        cleanup_stats = {"temp_files_cleaned": 0, "cleanup_candidates": [], "space_freed_mb": 0.0}

        if self._storage_monitor:
            # Clean temporary files
            temp_cleaned = await self._storage_monitor.cleanup_temporary_files()
            cleanup_stats["temp_files_cleaned"] = temp_cleaned

            # Identify cleanup candidates
            candidates = await self._storage_monitor.identify_cleanup_candidates(days_old)
            cleanup_stats["cleanup_candidates"] = candidates

        return cleanup_stats

    async def compress_old_slots(self, days_old: int = 30) -> dict[str, Any]:
        """Automatically compress slots that haven't been accessed recently."""
        await self._ensure_efficiency_initialized()

        compression_stats = {"slots_processed": 0, "slots_compressed": 0, "space_saved_mb": 0.0, "errors": []}

        if not self._storage_monitor:
            return compression_stats

        # Get candidates for compression
        candidates = await self._storage_monitor.identify_cleanup_candidates(days_old)

        for slot_name in candidates:
            try:
                compression_stats["slots_processed"] += 1

                # Compress the slot
                result = await self.compress_slot(slot_name, force=False)

                if result.get("entries_compressed", 0) > 0:
                    compression_stats["slots_compressed"] += 1
                    compression_stats["space_saved_mb"] += result.get("space_saved", 0) / (1024 * 1024)

            except Exception as e:
                compression_stats["errors"].append(f"Failed to compress {slot_name}: {str(e)}")

        return compression_stats

    async def optimize_indexes(self) -> dict[str, Any]:
        """Optimize search indexes for better performance."""
        await self._ensure_efficiency_initialized()

        optimization_stats = {
            "traditional_index_optimized": False,
            "incremental_index_optimized": False,
            "maintenance_performed": False,
            "errors": [],
        }

        try:
            # Optimize traditional search index
            if hasattr(self._search_engine, "optimize"):
                await self._search_engine.optimize()
                optimization_stats["traditional_index_optimized"] = True
        except Exception as e:
            optimization_stats["errors"].append(f"Traditional index optimization failed: {str(e)}")

        try:
            # Trigger incremental index maintenance
            if self._incremental_index:
                await self._incremental_index._perform_maintenance()
                optimization_stats["incremental_index_optimized"] = True
                optimization_stats["maintenance_performed"] = True
        except Exception as e:
            optimization_stats["errors"].append(f"Incremental index optimization failed: {str(e)}")

        return optimization_stats

    async def get_index_stats(self) -> dict[str, Any]:
        """Get statistics about search indexes."""
        await self._ensure_efficiency_initialized()

        stats = {
            "traditional_index": {
                "total_words": len(getattr(self._search_engine.index, "word_to_slots", {})),
                "total_slots": getattr(self._search_engine.index, "total_slots", 0),
                "dirty": getattr(self._search_engine.index, "dirty", False),
            },
            "incremental_index": {
                "available": self._incremental_index is not None,
                "total_words": 0,
                "total_slots": 0,
                "dirty_slots": 0,
                "change_log_entries": 0,
            },
        }

        if self._incremental_index:
            stats["incremental_index"].update(
                {
                    "total_words": len(self._incremental_index.word_to_slots),
                    "total_slots": len(self._incremental_index.slot_total_words),
                    "dirty_slots": len(self._incremental_index.dirty_slots),
                    "change_log_entries": len(self._incremental_index.change_log),
                }
            )

        return stats

    async def rebuild_indexes(self, force: bool = False) -> dict[str, Any]:
        """Rebuild search indexes from scratch."""
        rebuild_stats = {
            "traditional_index_rebuilt": False,
            "incremental_index_rebuilt": False,
            "slots_processed": 0,
            "errors": [],
        }

        try:
            # Rebuild traditional index
            self._search_initialized = False
            await self._initialize_search_index()
            rebuild_stats["traditional_index_rebuilt"] = True
        except Exception as e:
            rebuild_stats["errors"].append(f"Traditional index rebuild failed: {str(e)}")

        try:
            # Rebuild incremental index
            if self._incremental_index:
                # Shutdown existing index
                await self._incremental_index.shutdown()

                # Create new index
                self._incremental_index = IncrementalSearchIndex(self.memory_dir / "index")
                await self._incremental_index.initialize()

                # Re-index all slots
                for slot_file in self.memory_dir.glob("*.json"):
                    slot_name = slot_file.stem
                    slot = await self._load_slot(slot_name)
                    if slot:
                        await self._incremental_index.add_or_update_slot(slot)
                        rebuild_stats["slots_processed"] += 1

                rebuild_stats["incremental_index_rebuilt"] = True
        except Exception as e:
            rebuild_stats["errors"].append(f"Incremental index rebuild failed: {str(e)}")

        return rebuild_stats

    # Memory Management API
    async def get_memory_stats(self) -> dict[str, Any] | None:
        """Get comprehensive memory statistics."""
        if not self._memory_manager:
            return None

        await self._ensure_memory_management_initialized()
        return await self._memory_manager.get_memory_report()

    async def get_memory_trend(self, minutes: int = 30) -> dict[str, float] | None:
        """Get memory usage trend over specified time period."""
        if not self._memory_manager:
            return None

        return self._memory_manager.get_memory_trend(minutes)

    async def configure_memory_limits(
        self, memory_limit_mb: float, warning_threshold: float = 0.8, critical_threshold: float = 0.9
    ) -> bool:
        """Configure memory limits and thresholds."""
        if not self._memory_manager:
            return False

        self._memory_manager.configure_limits(memory_limit_mb, warning_threshold, critical_threshold)
        return True

    async def force_memory_cleanup(self) -> dict[str, int]:
        """Force memory cleanup and garbage collection."""
        if not self._memory_manager:
            return {"objects_freed": 0}

        return await self._memory_manager.force_garbage_collection()

    def track_memory_object(self, obj: Any, obj_type: str):
        """Track an object for memory monitoring."""
        if self._memory_manager:
            self._memory_manager.track_object(obj, obj_type)

    def add_memory_alert_callback(self, callback: Callable[[MemoryAlert], None]):
        """Add callback for memory alerts."""
        if self._memory_manager:
            self._memory_manager.add_alert_callback(callback)
