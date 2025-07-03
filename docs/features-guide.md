# MemCord Features Guide

A comprehensive guide to all MemCord features, capabilities, and use cases.

## Overview

MemCord is a powerful Model Context Protocol (MCP) server designed for intelligent chat memory management. It transforms how you store, organize, and retrieve conversation history with AI-enhanced features that make your memories searchable, shareable, and actionable.

## Core Features

### 1. Memory Management

#### Named Memory Slots
Create organized containers for different types of conversations:
- **Project-specific**: `project_alpha`, `team_standup`, `client_meeting`
- **Topic-based**: `api_design`, `security_review`, `budget_planning`
- **Time-based**: `weekly_sync_2024_01`, `q1_retrospective`

**Benefits:**
- Keep conversations organized and contextually grouped
- Easy retrieval of specific discussion topics
- Prevents information overload and context mixing

#### Auto-Summarization
Intelligent content compression that preserves key information:
- **85-95% compression** while maintaining essential details
- **Configurable compression ratios** (0.05-0.5)
- **Preserves decisions, action items, and key insights**
- **Maintains chronological order** of important events

**Use Cases:**
- Long project discussions that need periodic summaries
- Meeting notes that require executive summaries
- Research sessions with key findings extraction

### 2. Intelligent Search & Retrieval

#### Full-Text Search
Advanced search capabilities across all memory slots:
- **TF-IDF scoring** for relevance-ranked results
- **Snippet previews** with highlighted search terms
- **Boolean operators** (AND, OR, NOT) for complex queries
- **Tag-based filtering** to narrow search scope

**Search Examples:**
```
"API AND database NOT deprecated"
"meeting OR standup" with tag:urgent
"authentication" excluding tag:archived
```

#### Natural Language Queries
Ask questions about your memories in plain English:
- **What**: "What decisions were made about the API design?"
- **Who**: "Who was responsible for the database migration?"
- **When**: "When did we discuss the budget changes?"
- **Why**: "Why did we choose React over Vue?"
- **How**: "How did we solve the performance issues?"

**AI-Powered Context:**
- Understands context and relationships between conversations
- Provides relevant excerpts from multiple memory slots
- Synthesizes information from different time periods

### 3. Content Import & Integration

#### Multi-Format Support


Import content from various sources through a modular handler system:

**Text Files** (`.txt`, `.md`, `.markdown`, `.rst`, `.log`)
```python
# Usage example
memcord_import source="/path/to/notes.md" slot_name="research_notes" tags=["notes","draft"]
```
- Uses `aiofiles` for async file reading
- Preserves UTF-8 encoding and formatting
- Extracts file metadata (size, extension, timestamps)

**PDF Documents** (`.pdf`)
```python
# Usage example  
memcord_import source="/path/to/document.pdf" slot_name="research_docs" tags=["pdf","research"]
```
- Uses `pdfplumber` library for robust text extraction
- Processes page-by-page with clear page markers
- Handles complex layouts, tables, and formatting
- Includes page count and extraction method in metadata

**Web URLs** (`http://`, `https://`)
```python
# Usage example
memcord_import source="https://example.com/article" slot_name="web_content" group_path="articles/tech"
```
- Uses `trafilatura` for intelligent content extraction
- Falls back to `BeautifulSoup` for additional coverage
- Removes ads, navigation, comments, and clutter
- Extracts page titles and metadata
- 30-second timeout with proper error handling

**Structured Data** (`.json`, `.csv`, `.tsv`)
```python
# Usage examples
memcord_import source="/data/export.csv" slot_name="analytics_data" description="Sales data Q1 2025"
memcord_import source="/config/settings.json" slot_name="config_backup"
```
- JSON: Pretty-prints with proper indentation and structure detection
- CSV/TSV: Uses `pandas` for robust parsing and data conversion
- Includes schema information (columns, row counts, data types)
- Converts tabular data to human-readable format

#### Import Process Architecture

**Handler System:**
1. `ContentImporter` coordinates specialized handlers
2. Automatic handler selection based on source type
3. Extensible architecture for new content types
4. `ImportResult` model for standardized responses

**Import Flow:**
1. **Source Detection**: Automatic routing based on file extension/URL scheme
2. **Content Extraction**: Handler-specific processing with error handling
3. **Metadata Creation**: Standard metadata plus source-specific information
4. **Content Formatting**: Adds import header with source attribution
5. **Memory Storage**: Saves to specified slot with optional tags/groups

#### Advanced Import Features

**Automatic Detection:**
- File extension-based routing for local files
- URL scheme detection for web content
- MIME type validation where available
- Graceful fallbacks for ambiguous sources

**Rich Metadata Preservation:**
- Import timestamps and source attribution
- File sizes and processing statistics
- Content-specific details (page counts, column names, etc.)
- Extraction method and library information

**Error Handling & Recovery:**
- Comprehensive validation at each step
- Graceful fallbacks (multiple web extraction methods)
- Detailed error messages with troubleshooting hints
- Partial success handling for large imports

**Large File Support:**
- Up to 50MB file size limit
- Streaming processing for memory efficiency
- Progress tracking for long operations
- Timeout handling for web requests

**Integration Features:**
- **Tag Assignment**: Apply tags during import for immediate organization
- **Group Placement**: Set hierarchical groups for imported content
- **Description Support**: Add custom descriptions to imported memories
- **Metadata Preservation**: Maintain all original source information
>>>>>>> 71d9d1e (added tests)

### 4. Memory Slot Merging

#### Intelligent Consolidation
Combine multiple related memory slots:
- **Duplicate detection** with configurable similarity thresholds
- **Chronological ordering** preserves timeline integrity
- **Metadata consolidation** merges tags and groups
- **Preview mode** shows results before execution

**Merge Use Cases:**
- Consolidating meeting notes from a project phase
- Combining research from multiple sources
- Merging temporary slots into permanent documentation
- Creating comprehensive project summaries

#### Advanced Merge Options
- **Similarity threshold** (0.0-1.0) controls duplicate sensitivity
- **Source cleanup** option removes original slots after merge
- **Merge statistics** show content analysis and space savings
- **Rollback capability** if merge results are unsatisfactory

### 5. Storage Optimization

#### Intelligent Compression
Optimize storage space while maintaining functionality:
- **Automatic compression** for content over 1KB
- **30-70% typical space savings** with gzip compression
- **Transparent decompression** when reading content
- **Search functionality** works on compressed content

**Compression Actions:**
- **Analyze**: Preview compression potential without changes
- **Compress**: Apply compression to selected or all slots
- **Decompress**: Restore original content format
- **Stats**: View detailed compression statistics

#### Archival System
Long-term storage for inactive memories:
- **Candidate identification** based on inactivity periods
- **Compressed archival** for maximum space efficiency
- **Metadata preservation** maintains all original information
- **Easy restoration** when archived content is needed

### 6. Organization & Categorization

#### Tag System
Flexible categorization with multiple tags per slot:
- **Hierarchical tags** using dot notation (`project.alpha.backend`)
- **Case-insensitive** storage and matching
- **Auto-completion** suggestions from existing tags
- **Bulk operations** for tag management

**Tag Strategies:**
- **Project tags**: `project.alpha`, `project.beta`
- **Type tags**: `meeting`, `research`, `decision`
- **Status tags**: `active`, `completed`, `archived`
- **Priority tags**: `urgent`, `important`, `routine`

#### Group Management
Hierarchical folder structure for memory organization:
- **Unlimited nesting** depth for complex hierarchies
- **Path-based navigation** (`projects/alpha/meetings`)
- **Bulk operations** on group members
- **Visual organization** in list views

**Group Examples:**
```
projects/
├── alpha/
│   ├── meetings/
│   ├── research/
│   └── decisions/
├── beta/
│   └── planning/
└── internal/
    ├── standup/
    └── retrospectives/
```

### 7. Export & Sharing

#### Multiple Export Formats
Generate shareable content in various formats:

**Markdown (.md)**
- Rich formatting with headers, lists, and emphasis
- Preserves conversation structure
- GitHub-compatible syntax
- Ideal for documentation and wikis

**Plain Text (.txt)**
- Clean, readable format
- Universal compatibility
- Perfect for email and simple sharing
- Maintains chronological order

**JSON (.json)**
- Complete data preservation
- Programmatic access to all metadata
- Ideal for data analysis and backup
- Maintains full search indexing

#### MCP File Resources
Automatic resource generation for MCP ecosystem:
- **URI-based access** (`memory://slot_name.md`)
- **Metadata inclusion** (size, timestamps, tags)
- **Cross-application sharing** with other MCP tools
- **Real-time updates** when memory content changes

### 8. Advanced Features

#### Search Engine Integration
Built-in search capabilities:
- **Inverted index** for fast term lookup
- **TF-IDF scoring** for relevance ranking
- **Phrase matching** and proximity search
- **Cache optimization** for frequently accessed content

#### AI Query Processing
Natural language understanding:
- **Intent recognition** for different question types
- **Context synthesis** from multiple sources
- **Relevance scoring** for answer quality
- **Snippet extraction** with highlighted matches

#### Data Validation & Integrity
Robust data handling:
- **Schema validation** for all data structures
- **Automatic backup** creation before operations
- **Atomic operations** prevent data corruption
- **Recovery mechanisms** for failed operations

## Feature Comparison: Basic vs Advanced Mode

### Basic Mode (8 Tools)
**Target Users**: New users, simple workflows, performance-sensitive environments

**Available Features:**
- Core memory management (create, save, read, list)
- Progress summarization with compression
- Full-text search with Boolean operators
- Natural language queries
- Storage compression for space optimization

**Best For:**
- Getting started with MemCord
- Simple conversation storage and retrieval
- Basic search and query needs
- Minimal setup requirements

### Advanced Mode (15 Tools)
**Target Users**: Power users, complex workflows, team collaboration

**Additional Features:**
- Tag-based organization and categorization
- Hierarchical group management
- Content import from files, PDFs, and web URLs
- Memory slot merging with duplicate detection
- Multi-format export (Markdown, Text, JSON)
- File sharing and MCP resource generation
- Archival system for long-term storage

**Best For:**
- Complex project management
- Research and documentation workflows
- Content consolidation from multiple sources
- Team collaboration and sharing
- Long-term memory organization

## Use Case Scenarios

### Software Development Teams

**Project Management**
```
# Create project memory
memcord_name "project_alpha"
memcord_group set "projects/alpha"
memcord_tag add "project development active"

# Save sprint planning
memcord_save "Sprint planning discussion..."
memcord_save_progress "Summary of sprint goals and tasks" 0.2

# Search for decisions
memcord_search "architecture decisions"
memcord_query "What authentication method did we choose?"
```

**Code Review Sessions**
```
# Import review notes
memcord_import source="./code_review_notes.md" slot_name="review_session" tags=["review","code","security"]

# Merge multiple review sessions
memcord_merge source_slots=["review_session1","review_session2"] target_slot="final_review" action="merge"

# Export for team sharing
memcord_export "final_review" "md"
```

### Research & Documentation

**Research Project**
```
# Import research materials
memcord_import source="https://research-paper-url.com" slot_name="research_base" tags=["research","ai","nlp"]
memcord_import source="./research_notes.pdf" slot_name="research_base"

# Organize research
memcord_group set "research/ai_project"
memcord_tag add "research literature review"

# Query research findings
memcord_query "What are the key findings about transformer models?"
```

**Documentation Management**
```
# Create documentation hub
memcord_name "api_documentation"
memcord_group set "documentation/api"

# Compress older documentation
memcord_compress action="analyze"
memcord_compress action="compress" slot_name="api_documentation"

# Archive completed projects
memcord_archive action="candidates" days_inactive=60
memcord_archive action="archive" slot_name="old_project" reason="project_completed"
```

### Business & Meetings

**Meeting Management**
```
# Weekly standup
memcord_name "standup_2024_01_15"
memcord_group set "meetings/standup"
memcord_tag add "standup daily team"

# Save meeting notes
memcord_save "Team standup discussion..."
memcord_save_progress "Action items and decisions" 0.15

# Quarterly review
memcord_merge source_slots=["standup_2024_01_15","standup_2024_01_22"] target_slot="q1_standup_summary" action="merge"
```

**Client Communications**
```
# Client project tracking
memcord_name "client_project_x"
memcord_group set "clients/project_x"
memcord_tag add "client external important"

# Export client reports
memcord_export "client_project_x" "md"
memcord_share "client_project_x" "md,txt"
```

## Performance & Scalability

### Storage Efficiency
- **Compression ratios**: 30-70% space savings
- **Selective compression**: Only content over 1KB threshold
- **Archive compression**: Additional optimization for long-term storage
- **Incremental updates**: Only modified content is rewritten

### Search Performance
- **Sub-second queries** for most search operations
- **Index optimization**: ~10% of total content size
- **Bounded memory usage** with configurable limits
- **Concurrent access** support for multiple operations

### Scalability Limits
- **Memory slots**: Tested with 10,000+ slots
- **Content size**: Individual entries up to 50MB
- **Search index**: Handles millions of terms efficiently
- **Concurrent users**: Thread-safe operations

## Security & Privacy

### Data Protection
- **Local storage only**: All data remains on your machine
- **No cloud dependencies**: Complete offline operation
- **File system security**: Inherits OS-level permissions
- **Backup creation**: Automatic data protection

### Content Sanitization
- **HTML stripping**: Removes potentially harmful content
- **Encoding validation**: Ensures UTF-8 compliance
- **Size limits**: Prevents memory exhaustion
- **Type checking**: Validates all input data

## Migration & Compatibility

### Version Compatibility
- **Automatic migration** between MemCord versions
- **Backward compatibility** with older data formats
- **Schema versioning** for future-proof storage
- **Data integrity** validation during upgrades

### Export/Import Workflow
- **Full data portability** via JSON export
- **Selective migration** of specific memory slots
- **Metadata preservation** in all export formats
- **Bulk operations** for large dataset handling

## Getting the Most from MemCord

### Best Practices

**Memory Organization**
1. Use consistent naming conventions for slots
2. Apply tags early and consistently
3. Create logical group hierarchies
4. Regular cleanup of unused slots

**Search Optimization**
1. Use specific terms rather than generic ones
2. Combine Boolean operators for precise results
3. Leverage tags for filtering large result sets
4. Use natural language queries for complex questions

**Content Management**
1. Save progress regularly with summaries
2. Compress large or old content to save space
3. Archive completed projects to reduce clutter
4. Merge related slots for better organization

### Advanced Workflows

**Research Pipeline**
1. Import content from multiple sources
2. Tag and categorize all materials
3. Use queries to identify patterns and insights
4. Merge findings into comprehensive reports
5. Export final documentation for sharing

**Project Management**
1. Create project-specific memory slots
2. Save all meeting notes and decisions
3. Use progress summaries for status updates
4. Search for past decisions and context
5. Archive completed projects for reference

**Knowledge Base Building**
1. Import documentation from various sources
2. Create hierarchical organization structure
3. Use tags for cross-cutting concerns
4. Build searchable knowledge repository
5. Export subsets for team distribution

## Troubleshooting & Support

### Common Issues
- **Memory slot not found**: Check spelling with `memcord_list`
- **Search returns no results**: Try broader terms or check filters
- **Import fails**: Verify file permissions and format
- **Compression errors**: Check available disk space

### Performance Optimization
- **Regular cleanup**: Archive or delete unused slots
- **Index rebuilding**: Automatic optimization during idle time
- **Compression usage**: Balance between space and access speed
- **Memory monitoring**: Track usage with built-in statistics

### Getting Help
- **Documentation**: Complete guides in the `docs/` directory
- **Examples**: Real-world usage patterns and workflows
- **Issue tracking**: GitHub repository for bug reports
- **Community**: Discussion forums and user groups

## Future Enhancements

### Planned Features
- **Collaborative editing**: Multi-user access to shared memories
- **Version control**: Track changes and maintain history
- **Plugin system**: Custom extensions and integrations
- **Advanced analytics**: Usage patterns and content insights

### Integration Possibilities
- **MCP ecosystem**: Enhanced compatibility with other MCP tools
- **External APIs**: Integration with project management tools
- **Automation**: Scheduled operations and batch processing
- **AI enhancements**: Improved summarization and query processing

MemCord continues to evolve based on user feedback and emerging needs in the MCP ecosystem. Regular updates bring new features, performance improvements, and enhanced compatibility with the broader AI tooling landscape.