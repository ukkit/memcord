# Data Format & Technical Specifications

Technical documentation for data structures, file formats, and storage specifications.

## File Structure

```
chat-memory-mcp/
├── memory_slots/          # Internal JSON storage with enhanced metadata
│   ├── project_alpha.json      # With tags, groups, descriptions, compression
│   ├── meeting_notes.json      # Organized, searchable, optimized storage
│   └── ...
├── archives/              # Archived memory slots (compressed)
│   ├── index.json              # Archive index with metadata
│   ├── old_project_archived.json
│   └── ...
├── shared_memories/       # Exported files
│   ├── project_alpha.md
│   ├── project_alpha.txt
│   └── ...
├── docs/                  # Documentation
│   ├── PRD.md            # Product Requirements Document
│   ├── installation.md   # Installation guide
│   ├── tools-reference.md # Complete tools documentation
│   ├── search-and-query.md # Search & AI features
│   ├── data-format.md    # This file
│   ├── troubleshooting.md # Support documentation
│   └── examples.md       # Usage examples
└── src/memcord/           # Source code
    ├── server.py         # Main MCP server with 15 tools
    ├── storage.py        # Enhanced storage with compression/archive support
    ├── models.py         # Enhanced data models with compression metadata
    ├── compression.py    # Content compression utilities
    ├── archival.py       # Archival system for long-term storage
    ├── search.py         # Search engine with TF-IDF scoring
    ├── query.py          # Natural language query processing
    └── summarizer.py     # Text summarization
```

## Memory Slot Data Structure

### Enhanced Memory Slot JSON Schema

```json
{
  "slot_name": "project_alpha",
  "created_at": "2024-01-01T12:00:00Z",
  "updated_at": "2024-01-01T15:30:00Z",
  "tags": ["project", "urgent", "backend"],
  "group_path": "projects/alpha/development",
  "description": "Development discussions for Project Alpha",
  "priority": 1,
  "is_archived": false,
  "archived_at": null,
  "archive_reason": null,
  "metadata": {
    "total_entries": 5,
    "total_characters": 12500,
    "last_summary_at": "2024-01-01T14:00:00Z",
    "search_keywords": ["api", "database", "authentication"],
    "contributors": ["alice", "bob"],
    "project_phase": "development"
  },
  "entries": [
    {
      "id": "entry_001",
      "type": "manual_save",
      "content": "Full conversation text...",
      "timestamp": "2024-01-01T12:00:00Z",
      "metadata": {
        "word_count": 850,
        "participant_count": 3,
        "topics": ["api_design", "authentication"],
        "decisions": ["use_jwt_tokens", "implement_rate_limiting"]
      },
      "compression_info": {
        "is_compressed": false,
        "algorithm": "none",
        "original_size": null,
        "compressed_size": null,
        "compression_ratio": null,
        "compressed_at": null
      }
    },
    {
      "id": "entry_002",
      "type": "auto_summary", 
      "content": "Summary of key points...",
      "timestamp": "2024-01-01T12:30:00Z",
      "original_length": 5000,
      "summary_length": 750,
      "compression_ratio": 0.15,
      "metadata": {
        "summary_type": "progressive",
        "key_points": 5,
        "decisions_count": 2,
        "action_items": 3
      },
      "compression_info": {
        "is_compressed": true,
        "algorithm": "gzip",
        "original_size": 5000,
        "compressed_size": 750,
        "compression_ratio": 0.15,
        "compressed_at": "2024-01-01T12:30:00Z"
      }
    }
  ]
}
```

### Field Specifications

#### Root Level Fields
- **slot_name**: Unique identifier for the memory slot
- **created_at**: ISO 8601 timestamp of creation
- **updated_at**: ISO 8601 timestamp of last modification
- **tags**: Array of lowercase strings for categorization
- **group_path**: Hierarchical path using forward slashes
- **description**: Human-readable description of the slot's purpose
- **priority**: Integer (1-5) indicating importance
- **metadata**: Object containing aggregate information
- **entries**: Array of individual memory entries

#### Entry Types
- **manual_save**: Exact conversation text saved manually
- **auto_summary**: AI-generated summary with compression
- **import**: Content imported from external sources
- **merge**: Combined content from multiple slots

#### Metadata Schema
```json
{
  "total_entries": "number",
  "total_characters": "number", 
  "last_summary_at": "ISO 8601 timestamp",
  "search_keywords": ["array", "of", "strings"],
  "contributors": ["array", "of", "participants"],
  "project_phase": "string",
  "custom_fields": {
    "arbitrary": "key-value pairs"
  }
}
```

## Export Formats

### Markdown Format (.md)
```markdown
# Memory Slot: project_alpha

**Created:** 2024-01-01T12:00:00Z  
**Updated:** 2024-01-01T15:30:00Z  
**Tags:** project, urgent, backend  
**Group:** projects/alpha/development  

## Description
Development discussions for Project Alpha

## Entries

### Entry 1 - Manual Save (2024-01-01T12:00:00Z)
Full conversation text...

### Entry 2 - Auto Summary (2024-01-01T12:30:00Z)
*Summary (15% compression: 5000 → 750 characters)*

Summary of key points...
```

### Plain Text Format (.txt)
```
MEMORY SLOT: project_alpha
================================

Created: 2024-01-01T12:00:00Z
Updated: 2024-01-01T15:30:00Z
Tags: project, urgent, backend
Group: projects/alpha/development

Description: Development discussions for Project Alpha

ENTRIES
-------

[2024-01-01T12:00:00Z] Manual Save:
Full conversation text...

[2024-01-01T12:30:00Z] Auto Summary (15% compression):
Summary of key points...
```

### JSON Format (.json)
Complete memory slot data structure as shown above, with all metadata preserved.

## Search Index Structure

### Inverted Index Format
```json
{
  "term": "database",
  "documents": [
    {
      "slot_name": "project_alpha",
      "entry_id": "entry_001",
      "tf": 0.05,
      "positions": [45, 123, 289],
      "context": "...database migration plan..."
    }
  ],
  "idf": 2.1,
  "total_frequency": 15
}
```

### Search Result Format
```json
{
  "query": "database migration",
  "total_results": 3,
  "execution_time_ms": 12,
  "results": [
    {
      "slot_name": "project_alpha",
      "entry_id": "entry_001",
      "score": 0.85,
      "snippet": "...discussing the database migration plan...",
      "tags": ["project", "backend"],
      "group_path": "projects/alpha/development",
      "timestamp": "2024-01-01T12:00:00Z",
      "matched_terms": ["database", "migration"],
      "highlights": [
        {"start": 45, "end": 53, "term": "database"},
        {"start": 54, "end": 63, "term": "migration"}
      ]
    }
  ]
}
```

## MCP File Resources

### Resource URI Format
- `memory://slot_name.md` - Markdown export
- `memory://slot_name.txt` - Plain text export  
- `memory://slot_name.json` - Full JSON data

### Resource Metadata
```json
{
  "uri": "memory://project_alpha.md",
  "name": "project_alpha.md",
  "description": "Memory slot: project_alpha (Markdown format)",
  "mimeType": "text/markdown",
  "size": 2048,
  "lastModified": "2024-01-01T15:30:00Z",
  "tags": ["project", "urgent", "backend"],
  "group": "projects/alpha/development"
}
```

## Archive Storage Structure

### Archive Index Format
```json
{
  "created_at": "2024-01-01T12:00:00Z",
  "updated_at": "2024-01-01T15:30:00Z",
  "total_archives": 3,
  "total_original_size": 45000,
  "total_archived_size": 12000,
  "entries": {
    "old_project": {
      "slot_name": "old_project",
      "original_path": "memory_slots/old_project.json",
      "archive_path": "archives/old_project_archived.json",
      "archived_at": "2024-01-01T15:30:00Z",
      "archive_reason": "project_completed",
      "original_size": 15000,
      "archived_size": 4000,
      "compression_ratio": 0.27,
      "last_accessed": "2023-12-01T10:00:00Z",
      "entry_count": 12,
      "tags": ["project", "completed"],
      "group_path": "projects/legacy"
    }
  }
}
```

### Archived Memory Slot Format
```json
{
  "slot_name": "old_project",
  "created_at": "2023-01-01T12:00:00Z",
  "updated_at": "2023-12-01T10:00:00Z",
  "is_archived": true,
  "archived_at": "2024-01-01T15:30:00Z",
  "archive_reason": "project_completed",
  "tags": ["project", "completed"],
  "group_path": "projects/legacy",
  "entries": [
    {
      "type": "manual_save",
      "content": "H4sIAAAAAAACA+y9B3QUVRY...==",  // Base64-encoded gzip-compressed content
      "timestamp": "2023-01-01T12:00:00Z",
      "compression_info": {
        "is_compressed": true,
        "algorithm": "gzip",
        "original_size": 5000,
        "compressed_size": 1200,
        "compression_ratio": 0.24,
        "compressed_at": "2024-01-01T15:30:00Z"
      }
    }
  ]
}
```

## Storage Implementation

### File System Layout
```
memory_slots/
├── index.json                 # Global index of all slots
├── tags.json                 # Tag usage tracking
├── groups.json               # Group hierarchy
├── project_alpha.json        # Individual slot files
├── meeting_notes.json
└── ...

archives/
├── index.json                 # Archive index with metadata
├── old_project_archived.json # Compressed archived slots
├── legacy_data_archived.json
└── ...

shared_memories/
├── project_alpha.md          # Exported markdown
├── project_alpha.txt         # Exported text
├── project_alpha.json        # Exported JSON
└── ...

.cache/
├── search_index.json         # Search index cache
├── term_frequencies.json     # TF-IDF data
└── query_cache/              # Cached query results
    ├── query_hash_1.json
    └── ...
```

### Atomic Operations
- **File writes**: Use temporary files with atomic rename
- **Index updates**: Batch operations with rollback capability
- **Cache invalidation**: Automatic cleanup on data changes
- **Backup creation**: Automatic versioning of critical files

## Data Validation

### Schema Validation Rules
- **slot_name**: Required, alphanumeric + underscore/hyphen
- **timestamps**: Must be valid ISO 8601 format
- **tags**: Array of strings, lowercase, no spaces
- **group_path**: Forward slash separated, no leading/trailing slashes
- **compression_ratio**: Float between 0.05 and 0.5
- **priority**: Integer between 1 and 5

### Content Sanitization
- **HTML stripping**: Remove potentially harmful HTML tags
- **Encoding validation**: Ensure UTF-8 compliance
- **Size limits**: Configurable maximum entry sizes
- **Type checking**: Validate entry types against allowed values

## Performance Characteristics

### Storage Efficiency
- **Content compression**: Gzip compression for entries over 1KB threshold
- **Archive compression**: Additional compression for long-term storage
- **Incremental updates**: Only modified fields are rewritten
- **Index optimization**: Periodic cleanup and rebuilding
- **Memory usage**: Lazy loading of large memory slots
- **Space savings**: 30-70% reduction with intelligent compression

### Search Performance
- **Index size**: ~10% of total content size
- **Query time**: Sub-second for most queries
- **Memory usage**: Bounded by configurable limits
- **Concurrent access**: Thread-safe read operations

## Migration & Compatibility

### Version Compatibility
- **Schema versioning**: Automatic migration between versions
- **Backward compatibility**: Support for older formats
- **Forward compatibility**: Graceful handling of newer fields
- **Data integrity**: Validation during migration

### Export/Import
- **Standard formats**: JSON, Markdown, Plain text
- **Metadata preservation**: Full fidelity in JSON exports
- **Bulk operations**: Efficient handling of large datasets
- **Error handling**: Robust recovery from partial failures