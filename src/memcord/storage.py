"""Storage management for memory slots."""

import json
import asyncio
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime
import aiofiles
import aiofiles.os

from .models import MemorySlot, MemoryEntry, ServerState, SearchQuery, SearchResult, GroupInfo, CompressionInfo
from .search import SearchEngine
from .compression import ContentCompressor
from .archival import ArchivalManager


class StorageManager:
    """Manages file-based storage for memory slots."""
    
    def __init__(self, memory_dir: str = "memory_slots", shared_dir: str = "shared_memories"):
        self.memory_dir = Path(memory_dir)
        self.shared_dir = Path(shared_dir)
        self._lock = asyncio.Lock()
        self._state = ServerState()
        self._search_engine = SearchEngine()
        self._compressor = ContentCompressor()
        self._archival_manager = ArchivalManager(memory_dir, "archives")
        
        # Ensure directories exist
        self.memory_dir.mkdir(exist_ok=True)
        self.shared_dir.mkdir(exist_ok=True)
        
        # Flag to track if search index is initialized
        self._search_initialized = False
    
    async def _get_slot_path(self, slot_name: str) -> Path:
        """Get the file path for a memory slot."""
        return self.memory_dir / f"{slot_name}.json"
    
    async def _load_slot(self, slot_name: str) -> Optional[MemorySlot]:
        """Load memory slot from file."""
        slot_path = await self._get_slot_path(slot_name)
        
        if not slot_path.exists():
            return None
        
        try:
            async with aiofiles.open(slot_path, 'r', encoding='utf-8') as f:
                data = await f.read()
                slot_data = json.loads(data)
                return MemorySlot(**slot_data)
        except (json.JSONDecodeError, ValueError) as e:
            raise ValueError(f"Error loading slot '{slot_name}': {e}")
    
    async def _save_slot(self, slot: MemorySlot) -> None:
        """Save memory slot to file."""
        slot_path = await self._get_slot_path(slot.slot_name)
        
        # Create a backup if file exists
        if slot_path.exists():
            backup_path = slot_path.with_suffix('.json.bak')
            await aiofiles.os.rename(str(slot_path), str(backup_path))
        
        try:
            slot_dict = slot.model_dump()
            # Convert datetime objects to ISO strings for JSON serialization
            slot_dict = self._serialize_datetime(slot_dict)
            
            async with aiofiles.open(slot_path, 'w', encoding='utf-8') as f:
                await f.write(json.dumps(slot_dict, indent=2, ensure_ascii=False))
                
            # Remove backup on successful save
            backup_path = slot_path.with_suffix('.json.bak')
            if backup_path.exists():
                await aiofiles.os.remove(str(backup_path))
            
            # Update global tags
            for tag in slot.tags:
                self._state.add_tag_to_global_set(tag)
            
            # Update group information
            if slot.group_path:
                from .models import GroupInfo
                if slot.group_path not in self._state.groups:
                    # Create new group
                    group_info = GroupInfo(
                        path=slot.group_path,
                        name=slot.group_path.split('/')[-1],
                        parent_path='/'.join(slot.group_path.split('/')[:-1]) if '/' in slot.group_path else None
                    )
                    self._state.add_group(group_info)
                
                self._state.groups[slot.group_path].updated_at = datetime.now()
            
            # Update search index
            self._search_engine.add_slot(slot)
                
        except Exception as e:
            # Restore backup if save failed
            backup_path = slot_path.with_suffix('.json.bak')
            if backup_path.exists():
                await aiofiles.os.rename(str(backup_path), str(slot_path))
            raise ValueError(f"Error saving slot '{slot.slot_name}': {e}")
    
    def _serialize_datetime(self, obj: Any) -> Any:
        """Convert datetime objects and sets to JSON-serializable format."""
        if isinstance(obj, datetime):
            return obj.isoformat()
        elif isinstance(obj, set):
            return sorted(list(obj))  # Convert sets to sorted lists
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
                if slot_name not in self._search_engine.slots_cache or self._search_engine.slots_cache[slot_name].updated_at != slot.updated_at:
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
            
            entry = MemoryEntry(
                type=entry_type,
                content=content,
                timestamp=datetime.now()
            )
            
            if entry_type == "manual_save":
                # For manual saves, replace all content
                slot.entries = [entry]
            else:
                # For other types, append
                slot.add_entry(entry)
            
            await self._save_slot(slot)
            self._search_engine.add_slot(slot)  # Update search index
            return entry
    
    async def read_memory(self, slot_name: str) -> Optional[MemorySlot]:
        """Read memory slot content."""
        return await self._load_slot(slot_name)
    
    async def list_memory_slots(self) -> List[Dict[str, Any]]:
        """List all available memory slots with metadata."""
        slots_info = []
        
        for slot_file in self.memory_dir.glob("*.json"):
            slot_name = slot_file.stem
            try:
                slot = await self._load_slot(slot_name)
                if slot:
                    slots_info.append({
                        "name": slot_name,
                        "created_at": slot.created_at.isoformat(),
                        "updated_at": slot.updated_at.isoformat(),
                        "entry_count": len(slot.entries),
                        "total_length": slot.get_total_content_length(),
                        "is_current": slot_name == self._state.current_slot
                    })
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
                summary_length=len(summary)
            )
            
            slot.add_entry(entry)
            await self._save_slot(slot)
            self._search_engine.add_slot(slot)  # Update search index
            return entry
    
    def get_current_slot(self) -> Optional[str]:
        """Get the currently active slot name."""
        return self._state.current_slot
    
    async def export_slot_to_file(self, slot_name: str, format: str, output_path: Optional[str] = None) -> str:
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
        
        async with aiofiles.open(output_path, 'w', encoding='utf-8') as f:
            await f.write(content)
        
        return output_path
    
    def _format_as_markdown(self, slot: MemorySlot) -> str:
        """Format memory slot as Markdown."""
        lines = [
            f"# Memory Slot: {slot.slot_name}",
            ""
        ]
        
        # Add metadata
        lines.extend([
            f"**Created:** {slot.created_at.strftime('%Y-%m-%d %H:%M:%S')}",
            f"**Updated:** {slot.updated_at.strftime('%Y-%m-%d %H:%M:%S')}",
            f"**Entries:** {len(slot.entries)}"
        ])
        
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
            lines.extend([
                f"## {entry_type} - {entry.timestamp.strftime('%Y-%m-%d %H:%M:%S')}",
                ""
            ])
            
            if entry.type == "auto_summary" and entry.original_length and entry.summary_length:
                compression = (entry.summary_length / entry.original_length) * 100
                lines.extend([
                    f"**Summary Length:** {entry.summary_length}/{entry.original_length} characters ({compression:.1f}%)",
                    ""
                ])
            
            lines.extend([
                entry.content,
                ""
            ])
            
            if i < len(slot.entries) - 1:
                lines.append("---")
                lines.append("")
        
        lines.extend([
            "---",
            "*Exported via Chat Memory MCP Server*"
        ])
        
        return "\n".join(lines)
    
    def _format_as_text(self, slot: MemorySlot) -> str:
        """Format memory slot as plain text."""
        lines = [
            f"MEMORY SLOT: {slot.slot_name}",
            f"Created: {slot.created_at.strftime('%Y-%m-%d %H:%M:%S')}",
            f"Updated: {slot.updated_at.strftime('%Y-%m-%d %H:%M:%S')}",
            f"Entries: {len(slot.entries)}"
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
            lines.extend([
                f"=== {entry_type} ({entry.timestamp.strftime('%Y-%m-%d %H:%M:%S')}) ===",
                entry.content,
                ""
            ])
        
        lines.append("--- Exported via Chat Memory MCP Server ---")
        return "\n".join(lines)
    
    def _format_as_json(self, slot: MemorySlot) -> str:
        """Format memory slot as JSON."""
        export_data = {
            "slot_name": slot.slot_name,
            "exported_at": datetime.now().isoformat(),
            "created_at": slot.created_at.isoformat(),
            "updated_at": slot.updated_at.isoformat(),
            "entry_count": len(slot.entries),
            "tags": sorted(list(slot.tags)) if slot.tags else [],
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
                    "metadata": entry.metadata
                }
                for entry in slot.entries
            ],
            "export_format": "mcp_memory_v1"
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
    
    async def search_memory(self, query: SearchQuery) -> List[SearchResult]:
        """Search across all memory slots."""
        if not self._search_initialized:
            await self._initialize_search_index()
            self._search_initialized = True
        return self._search_engine.search(query)
    
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
    
    async def list_all_tags(self) -> List[str]:
        """List all tags used across memory slots."""
        return sorted(list(self._state.all_tags))
    
    async def set_slot_group(self, slot_name: str, group_path: Optional[str]) -> bool:
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
                        name=group_path.split('/')[-1],
                        parent_path='/'.join(group_path.split('/')[:-1]) if '/' in group_path else None
                    )
                    self._state.add_group(group_info)
                
                self._state.groups[group_path].member_count += 1
                self._state.groups[group_path].updated_at = datetime.now()
            
            return True
    
    async def list_groups(self) -> List[GroupInfo]:
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
    
    async def delete_slot(self, slot_name: str) -> bool:
        """Delete a memory slot."""
        async with self._lock:
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
            
            # Delete file
            await aiofiles.os.remove(str(slot_path))
            return True
    
    async def get_search_stats(self) -> Dict[str, Any]:
        """Get search engine statistics."""
        return self._search_engine.get_stats()
    
    def get_server_state(self) -> ServerState:
        """Get the current server state."""
        return self._state
    
    async def compress_slot(self, slot_name: str, force: bool = False) -> Dict[str, Any]:
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
                "compression_ratio": 1.0
            }
            
            entries_modified = False
            
            for entry in slot.entries:
                original_size = len(entry.content.encode('utf-8'))
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
                            compressed_at=metadata.compressed_at
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
                if compression_stats["original_size"] > 0 else 1.0
            )
            
            return compression_stats
    
    async def decompress_slot(self, slot_name: str) -> Dict[str, Any]:
        """Decompress content in a memory slot."""
        async with self._lock:
            slot = await self._load_slot(slot_name)
            if not slot:
                raise ValueError(f"Memory slot '{slot_name}' not found")
            
            decompression_stats = {
                "slot_name": slot_name,
                "entries_processed": 0,
                "entries_decompressed": 0,
                "decompressed_successfully": True
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
                            compressed_at=entry.compression_info.compressed_at or datetime.now()
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
    
    async def get_compression_stats(self, slot_name: Optional[str] = None) -> Dict[str, Any]:
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
                "slot_stats": {}
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
                if all_stats["total_original_size"] > 0 else 1.0
            )
            all_stats["space_saved"] = all_stats["total_original_size"] - all_stats["total_compressed_size"]
            all_stats["space_saved_percentage"] = (1 - all_stats["compression_ratio"]) * 100
            
            return all_stats
    
    async def archive_slot(self, slot_name: str, reason: str = "manual") -> Dict[str, Any]:
        """Archive a memory slot."""
        async with self._lock:
            slot = await self._load_slot(slot_name)
            if not slot:
                raise ValueError(f"Memory slot '{slot_name}' not found")
            
            # Archive the slot
            archive_entry = await self._archival_manager.archive_slot(slot, reason)
            
            # Remove from active storage
            await self.delete_slot(slot_name)
            
            return {
                "slot_name": slot_name,
                "archived_at": archive_entry.archived_at.isoformat(),
                "archive_reason": reason,
                "original_size": archive_entry.original_size,
                "archived_size": archive_entry.archived_size,
                "compression_ratio": archive_entry.compression_ratio,
                "space_saved": archive_entry.original_size - archive_entry.archived_size
            }
    
    async def restore_from_archive(self, slot_name: str) -> Dict[str, Any]:
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
                "total_size": slot.get_total_content_length()
            }
    
    async def list_archives(self, include_stats: bool = False) -> List[Dict[str, Any]]:
        """List all archived memory slots."""
        return await self._archival_manager.list_archives(include_stats)
    
    async def get_archive_stats(self) -> Dict[str, Any]:
        """Get archive statistics."""
        return await self._archival_manager.get_archive_stats()
    
    async def find_archival_candidates(self, days_inactive: int = 30) -> List[Tuple[str, Dict[str, Any]]]:
        """Find memory slots that could be archived."""
        return await self._archival_manager.find_candidates_for_archival(days_inactive)