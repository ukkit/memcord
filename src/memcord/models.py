"""Data models for chat memory management."""

from datetime import datetime
from typing import List, Optional, Dict, Any, Set, Tuple
import re
from pydantic import BaseModel, Field, field_validator, model_validator
from pathlib import Path
import os
from urllib.parse import urlparse


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
    
    type: str = Field(..., pattern=r"^(manual_save|auto_summary)$", description="Type of entry: 'manual_save' or 'auto_summary'")
    content: str = Field(
        ..., 
        min_length=1,
        max_length=10_485_760,  # 10MB limit
        description="Content of the entry (1 char to 10MB)"
    )
    timestamp: datetime = Field(default_factory=datetime.now, description="When entry was created")
    original_length: Optional[int] = Field(None, description="Length of original text for summaries")
    summary_length: Optional[int] = Field(None, description="Length of summary for summaries")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    compression_info: CompressionInfo = Field(default_factory=CompressionInfo, description="Compression information")
    
    @field_validator('content')
    @classmethod
    def validate_content_size(cls, v):
        """Validate content size and encoding."""
        if not v:
            raise ValueError("Content cannot be empty")
        
        # Check byte size (UTF-8 encoding)
        byte_size = len(v.encode('utf-8'))
        if byte_size > 10_485_760:  # 10MB
            raise ValueError(f"Content too large: {byte_size} bytes (max 10MB)")
        
        # Check for potentially malicious content
        suspicious_patterns = [
            r'<script[^>]*>',
            r'javascript:',
            r'data:text/html',
            r'vbscript:',
            r'<[^>]*\son\w+\s*='  # HTML event handlers like <div onclick=...>
        ]
        
        for pattern in suspicious_patterns:
            if re.search(pattern, v, re.IGNORECASE):
                raise ValueError("Content contains potentially unsafe script elements")
        
        return v


class MemorySlot(BaseModel):
    """Complete memory slot with all entries."""
    
    slot_name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Name of the memory slot (1-100 chars, supports Unicode)"
    )
    created_at: datetime = Field(default_factory=datetime.now, description="When slot was created")
    updated_at: datetime = Field(default_factory=datetime.now, description="When slot was last updated")
    entries: List[MemoryEntry] = Field(default_factory=list, description="All entries in this slot")
    current_slot: bool = Field(False, description="Whether this is the currently active slot")
    tags: Set[str] = Field(default_factory=set, description="Tags associated with this memory slot")
    
    class Config:
        json_encoders = {
            set: list  # Convert sets to lists for JSON serialization
        }
    group_path: Optional[str] = Field(
        None,
        max_length=500,
        pattern=r"^[a-zA-Z0-9_\-/\.\s]*$",
        description="Group/folder path for organization (max 500 chars, safe path chars only)"
    )
    description: Optional[str] = Field(
        None, 
        max_length=1000,
        description="Optional description of the memory slot (max 1000 chars)"
    )
    priority: int = Field(0, description="Priority level for organization (0=normal, 1=high, -1=low)")
    is_archived: bool = Field(False, description="Whether this slot is archived")
    archived_at: Optional[datetime] = Field(None, description="When slot was archived")
    archive_reason: Optional[str] = Field(
        None,
        max_length=500,
        description="Reason for archiving (max 500 chars)"
    )
    
    @field_validator('slot_name')
    @classmethod
    def validate_slot_name(cls, v):
        """Validate slot name for security and usability."""
        if not v or not v.strip():
            raise ValueError("Slot name cannot be empty")

        # Remove dangerous characters (but allow currency symbols and Unicode)
        cleaned = v.strip()
        dangerous_chars = ['<', '>', '"', "'", '&', '|', ';', '`', '$']
        if any(char in cleaned for char in dangerous_chars):
            raise ValueError("Slot name contains unsafe characters")

        # Remove null bytes and dangerous control characters
        cleaned = ''.join(char for char in cleaned if char != '\x00')
        cleaned = ''.join(char for char in cleaned if ord(char) >= 32 or char in '\r\n\t')

        # Check for SQL injection patterns and reject them
        sql_patterns = ['DROP', 'UNION', 'SELECT', 'DELETE', 'INSERT', 'UPDATE', 'CREATE', 'ALTER', '--', '/*', '*/', ';']
        for pattern in sql_patterns:
            if pattern in cleaned.upper():
                raise ValueError(f"Slot name contains SQL keyword or pattern: {pattern}")

        # Prevent path traversal
        if '../' in cleaned or '..\\' in cleaned:
            raise ValueError("Slot name cannot contain path traversal sequences")

        # Reserved names
        reserved = {'__ZERO__', 'CON', 'PRN', 'AUX', 'NUL', 'COM1', 'COM2', 'COM3', 'COM4', 'LPT1', 'LPT2'}
        if cleaned.upper() in reserved:
            raise ValueError(f"Slot name '{cleaned}' is reserved")

        return cleaned
    
    @field_validator('group_path')
    @classmethod
    def validate_group_path(cls, v):
        """Validate group path for security."""
        if v is None:
            return v
            
        # Prevent path traversal
        if '../' in v or '..\\' in v:
            raise ValueError("Group path cannot contain path traversal sequences")

        # Prevent dangerous absolute paths (path injection)
        dangerous_paths = [
            '/etc/', '/proc/', '/dev/', '/sys/', '/boot/', '/root/',
            'c:\\windows\\', 'c:\\program', '\\\\.\\pipe\\',
            '/var/log/', '/tmp/', '/usr/bin/', '/bin/'
        ]

        v_lower = v.lower()
        for dangerous in dangerous_paths:
            if v_lower.startswith(dangerous.lower()):
                raise ValueError(f"Group path cannot access system directories: {dangerous}")

        # Normalize path separators
        normalized = v.replace('\\', '/').strip('/')

        # Check individual components
        if normalized:
            components = normalized.split('/')
            for component in components:
                if not component.strip():
                    raise ValueError("Group path cannot have empty components")
                if component.strip() in ['.', '..']:
                    raise ValueError("Group path cannot contain . or .. components")

        return normalized if normalized else None
    
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
        """Get all searchable content combined, decompressing when necessary."""
        content_parts = [self.slot_name]
        if self.description:
            content_parts.append(self.description)
        content_parts.extend(self.tags)
        if self.group_path:
            content_parts.append(self.group_path)
        
        # Add entry content, decompressing if necessary
        for entry in self.entries:
            if entry.compression_info.is_compressed:
                try:
                    # Import here to avoid circular imports
                    from .compression import ContentCompressor
                    compressor = ContentCompressor()
                    decompressed = compressor.decompress_json_content(entry.content, entry.compression_info)
                    content_parts.append(decompressed)
                except Exception as e:
                    # If decompression fails, skip this entry's content for search
                    # but don't break the entire search
                    print(f"Warning: Failed to decompress content for search: {e}")
                    continue
            else:
                content_parts.append(entry.content)
        
        return ' '.join(content_parts)
    
    @property
    def content(self) -> str:
        """Get combined content from all entries for compatibility with merger."""
        return '\n\n'.join(entry.content for entry in self.entries)
    
    @property  
    def name(self) -> str:
        """Get slot name for compatibility with merger."""
        return self.slot_name
    
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
    
    def get_entry_by_timestamp(self, target_time: datetime, tolerance_minutes: int = 30) -> Optional[Tuple[int, MemoryEntry]]:
        """Get entry closest to target timestamp within tolerance."""
        from .temporal_parser import TemporalParser
        return TemporalParser.find_closest_entry_by_time(self.entries, target_time, tolerance_minutes)
    
    def get_entry_by_relative_time(self, relative_desc: str) -> Optional[Tuple[int, MemoryEntry]]:
        """Get entry by relative time description."""
        from .temporal_parser import TemporalParser
        
        parsed = TemporalParser.parse_relative_time(relative_desc)
        if not parsed:
            return None
        
        mode, ordinal, target_time = parsed
        
        if target_time:  # Absolute time from relative expression
            return self.get_entry_by_timestamp(target_time)
        elif ordinal:  # Ordinal expression (2nd latest, etc.)
            return TemporalParser.get_entry_by_ordinal(self.entries, mode, ordinal)
        else:  # Simple latest/oldest
            if mode == 'latest':
                if self.entries:
                    return (len(self.entries) - 1, self.entries[-1])
            elif mode == 'oldest':
                if self.entries:
                    return (0, self.entries[0])
        
        return None
    
    def get_entry_by_index(self, index: int, reverse: bool = False) -> Optional[Tuple[int, MemoryEntry]]:
        """Get entry by index (supports negative indexing)."""
        if not self.entries:
            return None
        
        try:
            if reverse:
                # Reverse indexing: -1 is latest, -2 is second latest, etc.
                actual_index = len(self.entries) + index if index < 0 else len(self.entries) - 1 - index
            else:
                # Normal indexing: 0 is oldest, -1 is latest
                actual_index = index if index >= 0 else len(self.entries) + index
            
            if 0 <= actual_index < len(self.entries):
                return (actual_index, self.entries[actual_index])
        except IndexError:
            pass
        
        return None
    
    def get_timeline_context(self, selected_index: int) -> Dict[str, Any]:
        """Get timeline context around a selected entry."""
        if not self.entries or selected_index < 0 or selected_index >= len(self.entries):
            return {}
        
        from .temporal_parser import TemporalParser
        
        selected_entry = self.entries[selected_index]
        total_entries = len(self.entries)
        
        context = {
            "position": f"{selected_index + 1} of {total_entries} entries",
            "selected_timestamp": selected_entry.timestamp.isoformat(),
            "selected_type": selected_entry.type,
            "total_entries": total_entries
        }
        
        # Add previous entry info
        if selected_index > 0:
            prev_entry = self.entries[selected_index - 1]
            context["previous_entry"] = {
                "timestamp": prev_entry.timestamp.isoformat(),
                "type": prev_entry.type,
                "time_description": TemporalParser.format_time_description(prev_entry.timestamp),
                "content_preview": prev_entry.content[:100] + "..." if len(prev_entry.content) > 100 else prev_entry.content
            }
        
        # Add next entry info
        if selected_index < total_entries - 1:
            next_entry = self.entries[selected_index + 1]
            context["next_entry"] = {
                "timestamp": next_entry.timestamp.isoformat(),
                "type": next_entry.type,
                "time_description": TemporalParser.format_time_description(next_entry.timestamp),
                "content_preview": next_entry.content[:100] + "..." if len(next_entry.content) > 100 else next_entry.content
            }
        
        return context
    
    def get_available_timestamps(self) -> List[str]:
        """Get list of all available timestamps for user reference."""
        return [entry.timestamp.isoformat() for entry in self.entries]


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
    
    slot_name: str = Field(..., min_length=1, description="Name of the memory slot")
    entry_index: Optional[int] = Field(None, description="Index of matching entry, None for slot-level match")
    relevance_score: float = Field(..., ge=0.0, le=1.0, description="Relevance score (0.0 to 1.0)")
    snippet: str = Field(..., description="Preview snippet of matching content")
    match_type: str = Field(..., pattern="^(slot|entry|tag|group)$", description="Type of match: 'slot', 'entry', 'tag', 'group'")
    timestamp: datetime = Field(..., description="Timestamp of the matched content")
    tags: List[str] = Field(default_factory=list, description="Tags of the memory slot")
    group_path: Optional[str] = Field(None, description="Group path of the memory slot")


class SearchQuery(BaseModel):
    """Search query configuration."""
    
    query: str = Field(
        ..., 
        min_length=1, 
        max_length=1000,
        description="Search query string (1-1000 chars)"
    )
    
    @field_validator('query')
    @classmethod
    def validate_search_query(cls, v):
        """Validate search query for security and performance."""
        if not v or not v.strip():
            raise ValueError("Search query cannot be empty")
        
        # Prevent regex injection attacks
        dangerous_regex_chars = ['(?', '(*', '(?=', '(?!', '(?<=', '(?<!']
        for pattern in dangerous_regex_chars:
            if pattern in v:
                raise ValueError(f"Search query contains potentially dangerous regex pattern: {pattern}")
        
        # Limit wildcards to prevent performance issues
        wildcard_count = v.count('*') + v.count('?') + v.count('.')
        if wildcard_count > 10:
            raise ValueError("Search query contains too many wildcards (max 10)")
        
        return v.strip()
    include_tags: List[str] = Field(default_factory=list, description="Tags to include in search")
    exclude_tags: List[str] = Field(default_factory=list, description="Tags to exclude from search")
    include_groups: List[str] = Field(default_factory=list, description="Groups to include in search")
    exclude_groups: List[str] = Field(default_factory=list, description="Groups to exclude from search")
    date_from: Optional[datetime] = Field(None, description="Search from this date")
    date_to: Optional[datetime] = Field(None, description="Search until this date")
    content_types: List[str] = Field(default_factory=lambda: ['manual_save', 'auto_summary'], description="Content types to search")
    max_results: int = Field(
        20, 
        gt=0, 
        le=100, 
        description="Maximum number of results to return (1-100)"
    )
    
    @field_validator('include_tags', 'exclude_tags')
    @classmethod
    def validate_tag_lists(cls, v):
        """Validate tag lists for reasonable limits."""
        if len(v) > 50:
            raise ValueError("Too many tags in filter (max 50)")
        
        for tag in v:
            if not isinstance(tag, str) or len(tag.strip()) == 0:
                raise ValueError("All tags must be non-empty strings")
            if len(tag) > 100:
                raise ValueError("Tag too long (max 100 chars)")
        
        return [tag.strip().lower() for tag in v]
    
    @field_validator('include_groups', 'exclude_groups')
    @classmethod
    def validate_group_lists(cls, v):
        """Validate group lists for reasonable limits."""
        if len(v) > 20:
            raise ValueError("Too many groups in filter (max 20)")
        
        for group in v:
            if not isinstance(group, str) or len(group.strip()) == 0:
                raise ValueError("All groups must be non-empty strings")
            if len(group) > 500:
                raise ValueError("Group path too long (max 500 chars)")
        
        return v
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