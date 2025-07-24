# Tools Reference

Complete reference for all 18 tools available in the Chat Memory MCP Server.

## Tool Availability

MemCord offers **two modes** with different tool sets:

### 🔧 Basic Mode (Default - 9 Tools)
Available without configuration:
- Core: `memcord_name`, `memcord_use`, `memcord_save`, `memcord_read`, `memcord_save_progress`, `memcord_list`
- Search: `memcord_search`, `memcord_query`
- Privacy: `memcord_zero`

### ⚡ Advanced Mode (All 18 Tools)
Requires `MEMCORD_ENABLE_ADVANCED=true`:
- **All Basic tools** plus:
- Organization: `memcord_tag`, `memcord_list_tags`, `memcord_group`
- Import & Integration: `memcord_import`, `memcord_merge`
- Export & Sharing: `memcord_export`, `memcord_share`
- Archival: `memcord_archive`

---

## Basic Tools (Always Available)

### Core Memory Management

### 1. `memcord_name <slot_name>`
Creates or selects a named memory slot.

**Parameters:**
- `slot_name`: Name of the memory slot to create or select

**Examples:**
- "Set memory slot to 'project_alpha'"
- "Create memory slot called 'meeting_notes'"

### 2. `memcord_use <slot_name>`
Activates an existing memory slot (does not create new slots).

**Parameters:**
- `slot_name`: Name of the existing memory slot to activate

**Examples:**
- "Use memory slot 'project_alpha'"
- "Switch to existing slot 'meeting_notes'"

**Note:** This tool only activates existing slots. If the slot doesn't exist, it returns an error suggesting to use `memcord_name` to create new slots or `memcord_list` to see available slots.

### 3. `memcord_save <chat_text>`
Manually saves exact chat text to current memory slot (overwrites existing content).

**Parameters:**
- `chat_text`: The conversation text to save

**Examples:**
- "Save this conversation to memory"
- "Store our discussion about the API changes"

### 4. `memcord_read [slot_name]`
Retrieves full content from memory slot.

**Parameters:**
- `slot_name` (optional): Name of slot to read. If not provided, uses current slot

**Examples:**
- "What did we discuss in the last session?"
- "Read from slot 'project_alpha'"

### 5. `memcord_save_progress <chat_text> [compression_ratio]`
Generates a summary and appends it to memory slot with timestamp.

**Parameters:**
- `chat_text`: Text to summarize
- `compression_ratio` (optional): Target compression (0.05-0.5, default 0.15)

**Examples:**
- "Summarize our progress and save it"
- "Save progress with 10% compression"

### 6. `memcord_list`
Lists all available memory slots with metadata.

**Parameters:** None

**Examples:**
- "Show me all my memory slots"
- "List all available memories"

### 7. `memcord_search <query> [options]`
Search across all memory slots with advanced filtering.

**Parameters:**
- `query`: Search query string
- `include_tags` (optional): Only include slots with these tags
- `exclude_tags` (optional): Exclude slots with these tags
- `max_results` (optional): Maximum number of results (default: 20)
- `case_sensitive` (optional): Whether search is case sensitive (default: false)

**Examples:**
- "Search for 'API integration'"
- "Search for 'database' excluding tag 'archived'"

### 8. `memcord_query <question>`
Ask natural language questions about your stored memories.

**Parameters:**
- `question`: Natural language question
- `max_results` (optional): Maximum number of results to consider (default: 5)

**Examples:**
- "What decisions were made about the API design?"
- "What issues were discussed in the last meeting?"

### Privacy Control

### 9. `memcord_zero`
Activate zero mode - no memory will be saved until switched to another slot.

**Parameters:**
- None

**Behavior:**
- Activates "zero mode" where all save operations are blocked
- Clear notifications inform user when zero mode is active
- `memcord_list` shows zero mode status prominently
- Mode persists until user switches to another memory slot with `memcord_name`

**Examples:**
- `memcord_zero` - Activate zero mode
- After activation, any `memcord_save` or `memcord_save_progress` will be blocked with helpful guidance

**Use Cases:**
- **Privacy conversations**: Ensure sensitive discussions aren't accidentally saved
- **Testing scenarios**: Prevent test conversations from polluting memory
- **Temporary usage**: Use Claude without building permanent memory
- **Guest access**: Allow others to use your setup without saving their conversations

**Exit Zero Mode:**
- Use `memcord_name [slot_name]` to select any memory slot and resume saving

---

## Advanced Tools (Requires MEMCORD_ENABLE_ADVANCED=true)

### Storage Optimization

### 10. `memcord_compress`
Compress memory slot content to save storage space with intelligent gzip compression.

**Parameters:**
- `action`: Action to perform (`analyze`, `compress`, `decompress`, `stats`)
- `slot_name` (optional): Memory slot name to compress. Processes all slots if not specified
- `force` (optional): Force compression even for already compressed content (default: false)

**Actions:**
- **`analyze`**: Preview compression potential without making changes
- **`compress`**: Apply compression to memory slot content 
- **`decompress`**: Restore compressed content to original form
- **`stats`**: View detailed compression statistics

**Examples:**
- `memcord_compress action="analyze"` - Preview compression for all slots
- `memcord_compress action="compress" slot_name="project_alpha"` - Compress specific slot
- `memcord_compress action="stats"` - View overall compression statistics
- `memcord_compress action="decompress" slot_name="project_alpha"` - Restore original content

**Features:**
- Automatic compression threshold (1KB minimum)
- 30-70% typical storage reduction
- Maintains search functionality on compressed content
- Transparent decompression when reading content

### Organization Tools

### 11. `memcord_tag <action> [tags]`
Manage tags for memory slots.

**Parameters:**
- `action`: Action to perform (`add`, `remove`, `list`)
- `tags` (optional): Space-separated list of tags (required for add/remove)

**Examples:**
- "Add tags 'project', 'meeting' to current slot"
- "Remove tag 'draft' from current slot"
- "List all tags for current slot"

**Tag Features:**
- Multiple tags per slot
- Case-insensitive (stored in lowercase)
- Hierarchical tags using dot notation (e.g., "project.alpha.backend")
- Auto-completion suggestions

### 12. `memcord_list_tags`
List all tags used across all memory slots.

**Parameters:** None

**Examples:**
- "Show me all available tags"
- "What tags are being used?"

**Output includes:**
- Tag name
- Usage count
- Associated memory slots

### 13. `memcord_group <action> [group_path]`
Manage memory slot groups and folders.

**Parameters:**
- `action`: Action to perform (`set`, `remove`, `list`)
- `group_path` (optional): Hierarchical path (required for set)

**Examples:**
- "Set group 'projects/alpha' for current slot"
- "Remove group assignment from current slot"
- "List all memory groups"

**Group Features:**
- Hierarchical folder structure
- Unlimited nesting depth
- Path-based navigation
- Bulk operations on group members

### Import & Integration

### 14. `memcord_import <source> [options]`
Import content from various sources including files, PDFs, web URLs, and structured data.

**Parameters:**
- `source`: Source to import from (file path, URL, etc.)
- `slot_name` (optional): Target memory slot name. Uses current slot if not specified
- `description` (optional): Description for the imported content
- `tags` (optional): Array of tags to apply to the imported content
- `group_path` (optional): Group path for organization

**Supported Sources:**
- **Text Files**: `.txt`, `.md`, `.markdown`, `.rst`, `.log`
- **PDF Documents**: Extracts text content page by page
- **Web URLs**: Extracts clean article content from web pages
- **Structured Data**: `.json`, `.csv`, `.tsv` files

**Examples:**
- "Import PDF document: `memcord_import source='/path/to/document.pdf' slot_name='research_docs' tags=['pdf','research']`"
- "Import web article: `memcord_import source='https://example.com/article' slot_name='web_content' group_path='articles/tech'`"
- "Import CSV data: `memcord_import source='/data/export.csv' slot_name='analytics_data' description='Sales data Q1 2025'`"
- "Import markdown file: `memcord_import source='./notes.md' tags=['notes','draft']`"

**Features:**
- Automatic source type detection
- Import metadata preservation
- Rich content headers with source information
- Support for large files (up to 50MB)
- Comprehensive error handling

### 15. `memcord_merge <source_slots> <target_slot> [options]`
Merge multiple memory slots into one with intelligent duplicate detection.

**Parameters:**
- `source_slots`: Array of memory slot names to merge (minimum 2)
- `target_slot`: Name for the merged memory slot
- `action` (optional): `preview` (default) or `merge`
- `similarity_threshold` (optional): Duplicate detection threshold 0.0-1.0 (default 0.8)
- `delete_sources` (optional): Delete source slots after successful merge (default false)

**Actions:**
- **Preview**: Shows merge statistics and content preview without executing
- **Merge**: Executes the merge operation with duplicate removal

**Examples:**
- "Preview merge: `memcord_merge source_slots=['meeting1','meeting2','meeting3'] target_slot='project_meetings' action='preview'`"
- "Execute merge: `memcord_merge source_slots=['draft1','draft2'] target_slot='final_document' action='merge' similarity_threshold=0.7`"
- "Merge with cleanup: `memcord_merge source_slots=['temp1','temp2'] target_slot='consolidated' action='merge' delete_sources=true`"

**Features:**
- **Duplicate Detection**: Configurable similarity threshold for content deduplication
- **Chronological Ordering**: Maintains timeline of merged content
- **Metadata Consolidation**: Merges tags and groups from all source slots
- **Preview Mode**: See merge results before execution
- **Source Cleanup**: Optional deletion of source slots after successful merge
- **Merge Statistics**: Detailed information about content and duplicates removed

### Archival & Long-term Storage

### 16. `memcord_archive <action> [options]`
Archive or restore memory slots for long-term storage with automatic compression.

**Parameters:**
- `action`: Action to perform (`archive`, `restore`, `list`, `stats`, `candidates`)
- `slot_name` (optional): Memory slot name to archive/restore (required for `archive` and `restore`)
- `reason` (optional): Reason for archiving (default: "manual")
- `days_inactive` (optional): Days of inactivity for finding candidates (default: 30)

**Actions:**
- **`archive`**: Move a memory slot to compressed archive storage
- **`restore`**: Restore an archived slot back to active memory
- **`list`**: Browse all archived memory slots with metadata
- **`stats`**: View archive storage statistics and space savings
- **`candidates`**: Find slots suitable for archiving based on inactivity

**Examples:**
- `memcord_archive action="candidates" days_inactive=30` - Find slots inactive for 30+ days
- `memcord_archive action="archive" slot_name="old_project" reason="project_completed"` - Archive specific slot
- `memcord_archive action="list"` - View all archived slots
- `memcord_archive action="restore" slot_name="old_project"` - Restore from archive
- `memcord_archive action="stats"` - View archive statistics

**Features:**
- **Automatic Compression**: Archives are compressed for maximum space savings
- **Preserved Metadata**: All tags, groups, and timestamps maintained
- **Search Integration**: Archived content remains searchable (future enhancement)
- **Safe Operations**: Archives preserve original data with restoration capability
- **Usage Analytics**: Identifies inactive slots for archival recommendations

### Export & Sharing

### 17. `memcord_export <slot_name> <format>`
Exports memory slot as an MCP file resource.

**Parameters:**
- `slot_name`: Name of the memory slot to export
- `format`: Export format (`md`, `txt`, `json`)

**Examples:**
- "Export project_alpha as markdown"
- "Export meeting_notes as JSON"

### 18. `memcord_share <slot_name> [formats]`
Generates shareable files in multiple formats.

**Parameters:**
- `slot_name`: Name of the memory slot to share
- `formats` (optional): Comma-separated list of formats (default: all)

**Examples:**
- "Share project_alpha in markdown and text formats"
- "Share meeting_notes in all formats"

## Advanced Usage Patterns

### Combining Tools
```
1. Create and organize:
   memcord_name "api_review" → memcord_tag add "technical review urgent" → memcord_group set "projects/backend"

2. Search and analyze:
   memcord_search "database performance" → memcord_query "What performance issues were identified?"

3. Export and share:
   memcord_export "api_review" "md" → memcord_share "api_review" "md,txt"
```

### Workflow Integration
```
1. Daily standup workflow:
   memcord_name "standup_2024_01_15" → memcord_save [conversation] → memcord_tag add "standup daily" → memcord_group set "meetings/daily"

2. Project documentation:
   memcord_name "project_specs" → memcord_save_progress [content] 0.1 → memcord_tag add "specs documentation" → memcord_export "project_specs" "md"

3. Research and analysis:
   memcord_search "security audit" → memcord_query "What security recommendations were made?" → memcord_name "security_summary" → memcord_save [findings]
```

## Tool Chaining

Many tools can be chained together for complex operations:

```
# Complete project setup
memcord_name → memcord_tag add → memcord_group set → memcord_save → memcord_export

# Research workflow  
memcord_search → memcord_query → memcord_name → memcord_save_progress

# Organization review
memcord_list → memcord_list_tags → memcord_group list → memcord_search [tag filter]
```

## Error Handling

Common error messages and solutions:

- **"No memory slot selected"**: Use `memcord_name` first
- **"Memory slot not found"**: Check spelling with `memcord_list`
- **"Invalid compression ratio"**: Use value between 0.05 and 0.5
- **"No search results"**: Try broader terms or check spelling
- **"Tag not found"**: Verify with `memcord_list_tags`
- **"Invalid group path"**: Use forward slashes for hierarchy