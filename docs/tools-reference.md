# Tools Reference

Complete reference for all 23 tools available in Memcord.

## Tool Availability

MemCord offers **two modes** with different tool sets:

### 🔧 Basic Mode (Default - 15 Tools)
Available without configuration:
- Core: `memcord_name`, `memcord_use`, `memcord_save`, `memcord_read`, `memcord_save_progress`, `memcord_list`
- Configuration: `memcord_configure`
- Search: `memcord_search`, `memcord_query`
- Privacy: `memcord_zero`
- Selection: `memcord_select_entry`
- Integration: `memcord_merge`
- Project Binding: `memcord_init`, `memcord_unbind`
- Utility: `memcord_ping`

### ⚡ Advanced Mode (All 23 Tools)
Requires `MEMCORD_ENABLE_ADVANCED=true`:
- **All Basic tools** plus:
- Organization: `memcord_tag`, `memcord_list_tags`, `memcord_group`
- Import: `memcord_import`
- Storage: `memcord_compress`
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
- `slot_name` (optional): Target memory slot. If not provided, uses current slot

**Slot resolution priority:** explicit `slot_name` → active slot → `.memcord` binding file in cwd. If the bound slot exists, it is also auto-activated for the rest of the session.

**Examples:**
- "Save this conversation to memory"
- "Store our discussion about the API changes"

### 4. `memcord_read [slot_name]`
Retrieves full content from memory slot.

**Parameters:**
- `slot_name` (optional): Name of slot to read. If not provided, uses current slot

**Slot resolution priority:** explicit `slot_name` → active slot → `.memcord` binding file in cwd.

**Examples:**
- "What did we discuss in the last session?"
- "Read from slot 'project_alpha'"

### 5. `memcord_save_progress <chat_text> [compression_ratio]`
Generates a summary and appends it to memory slot with timestamp.

**Parameters:**
- `chat_text`: Text to summarize
- `slot_name` (optional): Target memory slot. If not provided, uses current slot
- `compression_ratio` (optional): Target compression (0.05-0.5). Defaults to the slot's `default_compression_ratio` config value (0.15)

**Slot resolution priority:** explicit `slot_name` → active slot → `.memcord` binding file in cwd. If the bound slot exists, it is also auto-activated for the rest of the session.

**Summarizer backend:** Uses the backend configured for the slot via `memcord_configure`. New slots default to `sumy` (graph-based, zero model files); existing slots default to `nltk` (unchanged prior behavior). Override globally with `MEMCORD_SUMMARIZER` env var.

**Examples:**
- "Summarize our progress and save it"
- "Save progress with 10% compression"

### 6. `memcord_configure`
Get or set per-slot configuration — summarizer backend, consolidation limits, and custom storage location.

**Parameters:**
- `action`: `get` (show config), `set` (update a key), or `reset` (restore defaults)
- `key` (required for `set`): Config key to update. Valid keys:
  - `summarizer_backend` — `"sumy"` | `"semantic"` | `"transformers"` | `"nltk"`
  - `sumy_algorithm` — `"lexrank"` | `"lsa"` | `"edmundson"`
  - `semantic_model` — sentence-transformers model name (default: `"all-MiniLM-L6-v2"`)
  - `transformers_model` — HuggingFace model name (default: `"philschmid/bart-large-cnn-samsum"`)
  - `hf_device` — `"auto"` | `"cpu"` | `"cuda"` | `"mps"`
  - `default_compression_ratio` — float between 0.05 and 0.5
  - `max_auto_summaries` — int ≥ 0; max combined `auto_summary`/`rolled_summary` entries before consolidation (`0` disables)
  - `custom_storage_path` — absolute directory where this slot's data file lives (e.g. a synced Dropbox/OneDrive folder); empty string or `"none"` reverts to the default location
- `value` (required for `set`): New value for the key
- `slot_name` (optional): Target slot. Uses current slot if not specified

**Slot resolution priority:** explicit `slot_name` → active slot → `.memcord` binding file in cwd.

**Config is per-slot** and stored as a sidecar JSON file (`{slot}_config.json`). Changes take effect on the very next `memcord_save_progress` call — no restart required.

**Auto-creation rules:**
- New slot (no `.json` file yet) → `summarizer_backend = "sumy"` (smarter default)
- Existing slot (`.json` file present) → `summarizer_backend = "nltk"` (preserves prior behavior)

**`custom_storage_path` behavior:**
- Setting it on a slot that already has data **automatically migrates** the slot's `.json` (and `.bak`) file to the new directory — nothing is left behind.
- Setting it on a slot with no data yet just records the redirect; the next save writes straight to the custom location.
- If data already exists at *both* the old and new locations, the call is refused (no overwrite) so you can resolve the conflict manually.
- The redirect itself is **local to this machine** — each device pointing at a shared folder (e.g. Dropbox) needs to run its own `set` once, using whatever path that folder resolves to locally. Derived data (search index, cache, archives) stays local and is rebuilt lazily; only the primary `.json` file is shared.

**Examples:**
- `memcord_configure action="get"` — Show current slot config
- `memcord_configure action="set" key="summarizer_backend" value="transformers"` — Switch to abstractive BART
- `memcord_configure action="set" key="default_compression_ratio" value="0.25"` — Set compression to 25%
- `memcord_configure action="set" key="custom_storage_path" value="D:\Dropbox\shared"` — Move/link this slot to a synced folder
- `memcord_configure action="set" key="custom_storage_path" value=""` — Revert to the default storage location
- `memcord_configure action="reset"` — Restore defaults for current slot

**Env var override:** `MEMCORD_SUMMARIZER=nltk` overrides per-slot config for all slots (useful for Docker/CI).

### 7. `memcord_list`
Lists all available memory slots with metadata.

**Parameters:** None

**Examples:**
- "Show me all my memory slots"
- "List all available memories"

### 8. `memcord_ping`
Lightweight health check for server warm-up. Returns minimal response to confirm server is running.

**Parameters:** None

**Returns:** "pong"

**Use Cases:**
- Warm up the server at session start to avoid cold start delays
- Health check to verify server is responsive
- Configure in Claude Code hooks for automatic warm-up

**Examples:**
- Call `memcord_ping` at the start of a session
- Add to `UserPromptSubmit` hook for automatic warm-up

See [Server Warm-up](claude-code-guide.md#server-warm-up-avoid-cold-start-delays) for hook configuration.

### 9. `memcord_search <query> [options]`
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

### 10. `memcord_query <question>`
Ask natural language questions about your stored memories.

**Parameters:**
- `question`: Natural language question
- `max_results` (optional): Maximum number of results to consider (default: 5)

**Examples:**
- "What decisions were made about the API design?"
- "What issues were discussed in the last meeting?"

### Privacy Control

### 11. `memcord_zero`
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

### Entry Selection & Timeline Navigation

### 12. `memcord_select_entry`
Select and retrieve a specific memory entry by timestamp, relative time, or index within a memory slot.

**Parameters:**
- `slot_name` (optional): Target memory slot (uses current if not specified)
- `timestamp` (optional): Exact timestamp in ISO format (e.g., '2025-07-21T17:30:00')
- `relative_time` (optional): Human descriptions like 'latest', 'oldest', '2 hours ago', 'yesterday'
- `entry_index` (optional): Direct numeric index (0-based, negative for reverse indexing)
- `entry_type` (optional): Filter by entry type ('manual_save' or 'auto_summary')
- `show_context` (optional): Include timeline position and adjacent entries info (default: true)

**Selection Methods (choose exactly one):**
- **Timestamp Selection**: Exact timestamp matching with 30-minute tolerance
- **Relative Time**: Natural language expressions for temporal navigation
- **Index Selection**: Direct numeric access to entries in chronological order

**Examples:**
- `memcord_select_entry timestamp="2025-07-21T17:30:00"` - Select entry closest to specific time
- `memcord_select_entry relative_time="latest"` - Get the most recent entry
- `memcord_select_entry relative_time="2 hours ago"` - Get entry from approximately 2 hours ago
- `memcord_select_entry entry_index=0` - Get the oldest entry (first in timeline)
- `memcord_select_entry entry_index=-1` - Get the newest entry (last in timeline)
- `memcord_select_entry relative_time="oldest" entry_type="manual_save"` - Get oldest manual save

**Relative Time Expressions:**
- **Simple**: 'latest', 'newest', 'oldest', 'earliest', 'first'
- **Ordinal**: '2nd latest', 'third oldest', 'second newest'
- **Time Deltas**: '2 hours ago', '30 minutes ago', 'yesterday', 'last week'

**Features:**
- **Timeline Context**: Shows position and adjacent entries for navigation
- **Flexible Matching**: Tolerant timestamp matching for approximate selection
- **Type Filtering**: Filter by manual saves vs auto summaries
- **Error Guidance**: Helpful messages with available options when selection fails
- **Index Support**: Both positive (0=oldest) and negative (-1=newest) indexing

**Use Cases:**
- **Timeline Navigation**: Jump to specific points in conversation history
- **Content Retrieval**: Access specific decisions or discussions by time
- **Version Comparison**: Compare different versions of content over time
- **Context Building**: Select relevant entries for current discussion

### Memory Integration

### 13. `memcord_merge <source_slots> <target_slot> [options]`
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

**Use Cases:**
- **Project Consolidation**: Combine related project discussions into single slot
- **Meeting Summaries**: Merge multiple meeting notes into comprehensive overview
- **Research Organization**: Consolidate scattered research into organized collection
- **Content Cleanup**: Remove duplicates while preserving unique information

### Project Binding

### 14. `memcord_init <project_path> [slot_name]`
Initialize memcord for a project directory by binding it to a memory slot. Creates a `.memcord` file in the project root.

**Parameters:**
- `project_path`: Path to the project directory to initialize
- `slot_name` (optional): Memory slot name to bind. If not specified, uses directory name

**Behavior:**
- Creates a `.memcord` file in the project directory containing the slot name
- Auto-generates slot name from directory name if not specified (spaces replaced with underscores)
- Creates the memory slot if it doesn't exist
- If `.memcord` file already exists, reads and uses the existing slot name (unless new slot_name is specified)

**Examples:**
- `memcord_init project_path="/path/to/my-project"` - Initializes with slot named "my-project"
- `memcord_init project_path="/path/to/project" slot_name="custom-slot"` - Initializes with specified slot
- `memcord_init project_path="."` - Initializes current directory

**Use Cases:**
- **Project-specific memory**: Each project automatically uses its own memory slot
- **Team collaboration**: `.memcord` file can be committed to version control
- **Auto-detection**: Claude Code slash commands automatically use the bound slot

### 15. `memcord_unbind <project_path>`
Remove the `.memcord` binding file from a project directory.

**Parameters:**
- `project_path`: Path to the project directory to unbind

**Behavior:**
- Removes the `.memcord` file from the project directory
- Does NOT delete the memory slot itself (data is preserved)
- Returns helpful message if no `.memcord` file exists

**Examples:**
- `memcord_unbind project_path="/path/to/my-project"` - Removes binding
- `memcord_unbind project_path="."` - Unbinds current directory

---

## Advanced Tools (Requires MEMCORD_ENABLE_ADVANCED=true)

### Storage Optimization

### 16. `memcord_compress`
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

### 17. `memcord_tag <action> [tags]`
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

### 18. `memcord_list_tags`
List all tags used across all memory slots.

**Parameters:** None

**Examples:**
- "Show me all available tags"
- "What tags are being used?"

**Output includes:**
- Tag name
- Usage count
- Associated memory slots

### 19. `memcord_group <action> [group_path]`
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

### 20. `memcord_import <source> [options]`
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

### Archival & Long-term Storage

### 21. `memcord_archive <action> [options]`
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

### 22. `memcord_export <slot_name> <format>`
Exports memory slot as an MCP file resource.

**Parameters:**
- `slot_name`: Name of the memory slot to export
- `format`: Export format (`md`, `txt`, `json`)

**Examples:**
- "Export project_alpha as markdown"
- "Export meeting_notes as JSON"

### 23. `memcord_share <slot_name> [formats]`
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
- **"Unknown config key"**: Run `memcord_configure action="get"` to see valid keys
- **"Unknown action"**: Use `get`, `set`, or `reset` for `memcord_configure`
- **"No search results"**: Try broader terms or check spelling
- **"Tag not found"**: Verify with `memcord_list_tags`
- **"Invalid group path"**: Use forward slashes for hierarchy