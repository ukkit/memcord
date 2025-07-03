"""Data models for chat memory management."""

from datetime import datetime
from typing import List, Optional, Dict, Any, Set
import re
from pydantic import BaseModel, Field


class CompressionInfo(BaseModel):
    """Information about content compression."""
    
    is_compressed: bool = Field(False, description="Whether content is compressed")
    algorithm: str = Field("none", description="Compression algorithm used")
    original_size: Optional[int] = Field(None, description="Original size in bytes")
    compressed_size: Optional[int] = Field(None, description="Compressed size in bytes")
    compression_ratio: Optional[float] = Field(None, description="Compression ratio")
    compressed_at: Optional[datetime] = Field(None, description="When compression was applied")


class MemoryEntry(BaseModel):
    """Single entry in a memory slot."""
    
    type: str = Field(..., description="Type of entry: 'manual_save' or 'auto_summary'")
    content: str = Field(..., description="Content of the entry")
    timestamp: datetime = Field(default_factory=datetime.now, description="When entry was created")
    original_length: Optional[int] = Field(None, description="Length of original text for summaries")
    summary_length: Optional[int] = Field(None, description="Length of summary for summaries")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    compression_info: CompressionInfo = Field(default_factory=CompressionInfo, description="Compression information")


class MemorySlot(BaseModel):
    """Complete memory slot with all entries."""
    
    slot_name: str = Field(..., description="Name of the memory slot")
    created_at: datetime = Field(default_factory=datetime.now, description="When slot was created")
    updated_at: datetime = Field(default_factory=datetime.now, description="When slot was last updated")
    entries: List[MemoryEntry] = Field(default_factory=list, description="All entries in this slot")
    current_slot: bool = Field(False, description="Whether this is the currently active slot")
    tags: Set[str] = Field(default_factory=set, description="Tags associated with this memory slot")
    
    class Config:
        json_encoders = {
            set: list  # Convert sets to lists for JSON serialization
        }
    group_path: Optional[str] = Field(None, description="Group/folder path for organization")
    description: Optional[str] = Field(None, description="Optional description of the memory slot")
    priority: int = Field(0, description="Priority level for organization (0=normal, 1=high, -1=low)")
    is_archived: bool = Field(False, description="Whether this slot is archived")
    archived_at: Optional[datetime] = Field(None, description="When slot was archived")
    archive_reason: Optional[str] = Field(None, description="Reason for archiving")
    
    def add_entry(self, entry: MemoryEntry) -> None:
        """Add a new entry and update timestamp."""
        self.entries.append(entry)
        self.updated_at = datetime.now()
    
    def get_latest_entry(self) -> Optional[MemoryEntry]:
        """Get the most recent entry."""
        return self.entries[-1] if self.entries else None
    
    def get_total_content_length(self) -> int:
        """Get total length of all content."""
        return sum(len(entry.content) for entry in self.entries)
    
    def add_tag(self, tag: str) -> None:
        """Add a tag to this memory slot."""
        self.tags.add(tag.lower().strip())
        self.updated_at = datetime.now()
    
    def remove_tag(self, tag: str) -> bool:
        """Remove a tag from this memory slot. Returns True if tag was removed."""
        tag_lower = tag.lower().strip()
        if tag_lower in self.tags:
            self.tags.remove(tag_lower)
            self.updated_at = datetime.now()
            return True
        return False
    
    def has_tag(self, tag: str) -> bool:
        """Check if slot has a specific tag."""
        return tag.lower().strip() in self.tags
    
    def set_group(self, group_path: Optional[str]) -> None:
        """Set the group path for this memory slot."""
        self.group_path = group_path
        self.updated_at = datetime.now()
    
    def get_searchable_content(self) -> str:
        """Get all searchable content combined."""
        content_parts = [self.slot_name]
        if self.description:
            content_parts.append(self.description)
        content_parts.extend(self.tags)
        if self.group_path:
            content_parts.append(self.group_path)
        content_parts.extend(entry.content for entry in self.entries)
        return ' '.join(content_parts)
    
    def archive(self, reason: str = None) -> None:
        """Mark this memory slot as archived."""
        self.is_archived = True
        self.archived_at = datetime.now()
        self.archive_reason = reason
        self.updated_at = datetime.now()
    
    def unarchive(self) -> None:
        """Remove archive status from this memory slot."""
        self.is_archived = False
        self.archived_at = None
        self.archive_reason = None
        self.updated_at = datetime.now()
    
    def get_compression_stats(self) -> Dict[str, Any]:
        """Get compression statistics for this slot."""
        total_entries = len(self.entries)
        compressed_entries = sum(1 for entry in self.entries if entry.compression_info.is_compressed)
        
        total_original_size = 0
        total_compressed_size = 0
        
        for entry in self.entries:
            if entry.compression_info.is_compressed:
                total_original_size += entry.compression_info.original_size or 0
                total_compressed_size += entry.compression_info.compressed_size or 0
            else:
                content_size = len(entry.content.encode('utf-8'))
                total_original_size += content_size
                total_compressed_size += content_size
        
        compression_ratio = total_compressed_size / total_original_size if total_original_size > 0 else 1.0
        
        return {
            "total_entries": total_entries,
            "compressed_entries": compressed_entries,
            "compression_percentage": (compressed_entries / total_entries * 100) if total_entries > 0 else 0,
            "total_original_size": total_original_size,
            "total_compressed_size": total_compressed_size, 
            "compression_ratio": compression_ratio,
            "space_saved": total_original_size - total_compressed_size,
            "space_saved_percentage": (1 - compression_ratio) * 100
        }


class ExportConfig(BaseModel):
    """Configuration for exporting memory slots."""
    
    format: str = Field(..., description="Export format: 'md', 'txt', or 'json'")
    include_metadata: bool = Field(True, description="Whether to include metadata")
    include_timestamps: bool = Field(True, description="Whether to include timestamps")
    include_tags: bool = Field(True, description="Whether to include tags in export")
    include_groups: bool = Field(True, description="Whether to include group information")
    pretty_format: bool = Field(True, description="Whether to format output for readability")


class SearchResult(BaseModel):
    """Result from a search query."""
    
    slot_name: str = Field(..., description="Name of the memory slot")
    entry_index: Optional[int] = Field(None, description="Index of matching entry, None for slot-level match")
    relevance_score: float = Field(..., description="Relevance score (0.0 to 1.0)")
    snippet: str = Field(..., description="Preview snippet of matching content")
    match_type: str = Field(..., description="Type of match: 'slot', 'entry', 'tag', 'group'")
    timestamp: datetime = Field(..., description="Timestamp of the matched content")
    tags: List[str] = Field(default_factory=list, description="Tags of the memory slot")
    group_path: Optional[str] = Field(None, description="Group path of the memory slot")


class SearchQuery(BaseModel):
    """Search query configuration."""
    
    query: str = Field(..., description="Search query string")
    include_tags: List[str] = Field(default_factory=list, description="Tags to include in search")
    exclude_tags: List[str] = Field(default_factory=list, description="Tags to exclude from search")
    include_groups: List[str] = Field(default_factory=list, description="Groups to include in search")
    exclude_groups: List[str] = Field(default_factory=list, description="Groups to exclude from search")
    date_from: Optional[datetime] = Field(None, description="Search from this date")
    date_to: Optional[datetime] = Field(None, description="Search until this date")
    content_types: List[str] = Field(default_factory=lambda: ['manual_save', 'auto_summary'], description="Content types to search")
    max_results: int = Field(20, description="Maximum number of results to return")
    case_sensitive: bool = Field(False, description="Whether search should be case sensitive")
    use_regex: bool = Field(False, description="Whether to treat query as regex pattern")


class GroupInfo(BaseModel):
    """Information about a memory group."""
    
    path: str = Field(..., description="Full path of the group")
    name: str = Field(..., description="Display name of the group")
    description: Optional[str] = Field(None, description="Description of the group")
    created_at: datetime = Field(default_factory=datetime.now, description="When group was created")
    updated_at: datetime = Field(default_factory=datetime.now, description="When group was last updated")
    member_count: int = Field(0, description="Number of memory slots in this group")
    total_size: int = Field(0, description="Total content size in this group")
    parent_path: Optional[str] = Field(None, description="Path of parent group")
    subgroups: List[str] = Field(default_factory=list, description="Names of subgroups")


class ServerState(BaseModel):
    """Global server state."""
    
    current_slot: Optional[str] = Field(None, description="Currently active memory slot")
    available_slots: List[str] = Field(default_factory=list, description="List of available slot names")
    all_tags: Set[str] = Field(default_factory=set, description="All tags used across memory slots")
    
    class Config:
        json_encoders = {
            set: list  # Convert sets to lists for JSON serialization
        }
    groups: Dict[str, GroupInfo] = Field(default_factory=dict, description="All memory groups")
    search_index_dirty: bool = Field(True, description="Whether search index needs rebuilding")
    
    def set_current_slot(self, slot_name: str) -> None:
        """Set the current active slot."""
        self.current_slot = slot_name
        if slot_name not in self.available_slots:
            self.available_slots.append(slot_name)
    
    def add_tag_to_global_set(self, tag: str) -> None:
        """Add a tag to the global tag set."""
        self.all_tags.add(tag.lower().strip())
    
    def remove_tag_from_global_set(self, tag: str) -> None:
        """Remove a tag from the global tag set if no slots use it."""
        self.all_tags.discard(tag.lower().strip())
    
    def add_group(self, group_info: GroupInfo) -> None:
        """Add a group to the groups dictionary."""
        self.groups[group_info.path] = group_info
    
    def remove_group(self, group_path: str) -> bool:
        """Remove a group. Returns True if group was removed."""
        if group_path in self.groups:
            del self.groups[group_path]
            return True
        return False
    
    def get_group_hierarchy(self) -> Dict[str, List[str]]:
        """Get group hierarchy as parent -> children mapping."""
        hierarchy = {}
        for group_path, group_info in self.groups.items():
            parent = group_info.parent_path or "root"
            if parent not in hierarchy:
                hierarchy[parent] = []
            hierarchy[parent].append(group_path)
        return hierarchy
    
    def is_zero_mode(self) -> bool:
        """Check if currently in zero mode."""
        return self.current_slot == "__ZERO__"
    
    def activate_zero_mode(self) -> None:
        """Activate zero mode - no memory will be saved."""
        self.current_slot = "__ZERO__"