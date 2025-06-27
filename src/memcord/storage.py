"""Storage management for memory slots."""

import json
import asyncio
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime
import aiofiles
import aiofiles.os

from .models import MemorySlot, MemoryEntry, ServerState, SearchQuery, SearchResult, GroupInfo
from .search import SearchEngine


class StorageManager:
    """Manages file-based storage for memory slots."""
    
    def __init__(self, memory_dir: str = "memory_slots", shared_dir: str = "shared_memories"):
        self.memory_dir = Path(memory_dir)
        self.shared_dir = Path(shared_dir)
        self._lock = asyncio.Lock()
        self._state = ServerState()
        self._search_engine = SearchEngine()
        
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