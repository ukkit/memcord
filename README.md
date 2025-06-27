# MemCord MCP Server

A Model Context Protocol (MCP) server for managing chat memory with automatic summarization, intelligent search, and file sharing capabilities. Save, organize, and retrieve conversation history with powerful AI-enhanced search across all your memories.

[![MCP Server](https://img.shields.io/badge/MCP-Server-blue)](https://github.com/modelcontextprotocol)
  [![Claude Desktop](https://img.shields.io/badge/Claude-Desktop-orange)](https://claude.ai/desktop)
  [![Python](https://img.shields.io/badge/Python-3.10+-green)](https://python.org)
  [![License](https://img.shields.io/badge/License-MIT-yellow)](LICENSE)


## Key Features

- **Memory Management**: Create named memory slots, save conversations, generate summaries
- **Content Import**: Import from text files, PDFs, web URLs, and structured data (CSV/JSON)
- **Intelligent Search**: Full-text search with natural language queries and Boolean operators
- **Smart Organization**: Tag-based categorization and hierarchical group management
- **Memory Merging**: Consolidate multiple slots with duplicate detection and chronological ordering
- **Multiple Formats**: Export to Markdown, Text, or JSON with MCP file resource sharing
- **Local & Secure**: All data stored locally with no cloud dependencies
- **AI-Enhanced**: TF-IDF search scoring, automatic summarization, contextual responses

## Quick Start

```bash
# Install
git clone <repository-url>
cd memcord
uv pip install -e .
```

## Add to Claude Desktop

### Basic Mode (Default - 7 Tools)
```json
{
  "mcpServers": {
    "memcord": {
      "command": "uv",
      "args": [
        "--directory",
        "/path/to/memcord",
        "run",
        "memcord"
      ],
      "env": {
        "PYTHONPATH": "/path/to/memcord/src"
      }
    }
  }
}
```

### Advanced Mode (All 14 Tools)
```json
{
  "mcpServers": {
    "memcord": {
      "command": "uv",
      "args": [
        "--directory",
        "/path/to/memcord",
        "run",
        "memcord"
      ],
      "env": {
        "PYTHONPATH": "/path/to/memcord/src",
        "MEMCORD_ENABLE_ADVANCED": "true"
      }
    }
  }
}
```

**📚 [Complete Installation Guide](docs/installation.md)** - Detailed setup for Claude Code, Claude Desktop, and other MCP applications.

## Basic Usage

```bash
# Create a memory slot and save conversation
memcord_name "project_meeting"
memcord_save "Our discussion about the new API design..."

# Search and query your memories
memcord_search "API design decisions"
memcord_query "What did we decide about authentication?"

# Import content from various sources
memcord_import source="/path/to/document.pdf" slot_name="research_docs" tags=["pdf","research"]
memcord_import source="https://example.com/article" slot_name="web_content"

# Organize with tags and groups
memcord_tag add "project urgent architecture"
memcord_group set "meetings/weekly"

# Merge related memory slots
memcord_merge source_slots=["meeting1","meeting2"] target_slot="project_summary" action="preview"

# Export and share
memcord_export "project_meeting" "md"
```

## Available Tools

MemCord offers **two modes** to suit different use cases:

### 🔧 Basic Mode (Default - 7 Tools)
Essential memory management features always available:

**Core Tools**
- `memcord_name` - Create/select memory slots
- `memcord_save` - Save conversations manually
- `memcord_read` - Retrieve stored content
- `memcord_save_progress` - Auto-summarize and append
- `memcord_list` - List all memory slots

**Search & Intelligence**
- `memcord_search` - Full-text search with Boolean operators
- `memcord_query` - Natural language questions about memories

### ⚡ Advanced Mode (All 14 Tools)
Set `MEMCORD_ENABLE_ADVANCED=true` to unlock additional features:

**Organization** (Advanced)
- `memcord_tag` - Add/remove/list tags for categorization
- `memcord_group` - Organize slots into hierarchical groups
- `memcord_list_tags` - View all available tags

**Import & Integration** (Advanced) 🆕
- `memcord_import` - Import content from files, PDFs, web URLs, and structured data
- `memcord_merge` - Merge multiple memory slots with duplicate detection

**Export & Sharing** (Advanced)
- `memcord_export` - Export to Markdown, Text, or JSON
- `memcord_share` - Generate shareable files in multiple formats

**📖 [Complete Tools Reference](docs/tools-reference.md)** - Detailed documentation for all 14 tools with examples and parameters.

## Tool Modes

### When to Use Basic Mode
- **New users** getting started with MemCord
- **Simpler workflows** focused on core memory management
- **Minimal setup** with essential features only
- **Performance-sensitive** environments

### When to Use Advanced Mode
- **Power users** who need full functionality
- **Complex workflows** with organization, import/export needs
- **Team collaboration** requiring advanced features
- **Content management** from multiple sources

**Switching Modes**: You can enable/disable advanced tools anytime by setting the `MEMCORD_ENABLE_ADVANCED` environment variable and restarting the MCP server.

## Documentation

- **📚 [Installation Guide](docs/installation.md)** - Complete setup instructions for all MCP applications
- **📖 [Tools Reference](docs/tools-reference.md)** - Detailed documentation for all 14 tools
- **📥 [Import & Merge Guide](docs/import-and-merge.md)** - Comprehensive guide for Phase 3 features 🆕
- **🔍 [Search & Query Guide](docs/search-and-query.md)** - Advanced search features and natural language queries
- **🗂️ [Usage Examples](docs/examples.md)** - Real-world workflows and practical use cases
- **⚙️ [Data Format Specification](docs/data-format.md)** - Technical details and file formats
- **🛠️ [Troubleshooting](docs/troubleshooting.md)** - Common issues and solutions

## Features in Detail

### Memory Management
- **Named Slots**: Organize conversations by project, topic, or purpose
- **Auto-Summarization**: Compress content by 85-95% while preserving key information
- **Timestamps**: Track when memories were created and last updated
- **Multiple Formats**: Store and export in Markdown, Text, or JSON

### Search & Intelligence
- **TF-IDF Scoring**: Relevance-ranked search results with snippet previews
- **Boolean Search**: Use AND, OR, NOT operators for complex queries
- **Natural Language**: Ask questions like "What decisions were made about the API?"
- **Fast Indexing**: Sub-second search across thousands of memory slots

### Organization & Sharing
- **Tags**: Multi-tag categorization with hierarchical support
- **Groups**: Organize memories into folders and subfolders
- **MCP Resources**: Auto-generated file resources accessible to other MCP apps
- **Export Options**: Share memories in multiple formats simultaneously

## License & Support

**MIT License** - see LICENSE file for details.

**Issues & Feature Requests**: Use the GitHub issue tracker
