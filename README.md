# MemCord MCP Server

A Model Context Protocol (MCP) server for managing chat memory with automatic summarization, intelligent search, and file sharing capabilities. Save, organize, and retrieve conversation history with powerful AI-enhanced search across all your memories.

# MemCord Features

## Never Lose Context Again
Transform your Claude conversations into a searchable, organized knowledge base that grows with you

### **Core Benefits**

* **🧠 Infinite Memory** - Claude remembers everything across unlimited conversations with intelligent auto-summarization
* **🔒 Your Data, Your Control** - 100% local storage with zero cloud dependencies or privacy concerns
* **📚 Universal Knowledge Import** - Pull in PDFs, research papers, web articles, and data files instantly
* **⚡ Lightning Search** - Ask questions in plain English: "What did we decide about the API design?"
* **🎯 Effortless Organization** - Smart tags and folders that organize themselves around your workflow
* **🔗 Intelligent Merging** - Automatically combines related conversations while eliminating duplicates
* **🤖 AI-Powered Intelligence** - Advanced search algorithms that understand context, not just keywords
* **⚙️ Set-and-Forget Setup** - Configure once, works invisibly forever

### **The Bottom Line**

Stop losing brilliant ideas in chat history. Turn every Claude conversation into permanent, searchable knowledge that compounds over time.

**Perfect for:** Researchers, consultants, developers, and anyone who has important conversations with Claude that they can't afford to lose.

## Quick Start

```bash
# First time installation
git clone https://github.com/ukkit/memcord.git
cd memcord
uv venv
source .venv/bin/activate
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
        "/path/to/chat-memory-mcp",
        "run",
        "memcord"
      ],
      "env": {
        "PYTHONPATH": "/path/to/chat-memory-mcp/src"
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

# Optimize storage with compression
memcord_compress action="analyze"  # Preview compression potential
memcord_compress action="compress" slot_name="project_meeting"

# Export and share
memcord_export "project_meeting" "md"
```

## Available Tools

MemCord offers **two modes** to suit different use cases:

### 🔧 Basic Mode (Default - 8 Tools)
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

**Storage Optimization**
- `memcord_compress` - Compress memory content to save storage space

### ⚡ Advanced Mode (All 15 Tools)
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

**Archival & Long-term Storage** (Advanced)
- `memcord_archive` - Archive inactive memory slots for long-term storage

**📖 [Complete Tools Reference](docs/tools-reference.md)** - Detailed documentation for all 15 tools with examples and parameters.

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

### Advanced Mode Config (All 14 Tools)

```json
{
  "mcpServers": {
    "memcord": {
      "command": "uv",
      "args": [
        "--directory",
        "/path/to/chat-memory-mcp",
        "run",
        "memcord"
      ],
      "env": {
        "PYTHONPATH": "/path/to/chat-memory-mcp/src",
        "MEMCORD_ENABLE_ADVANCED": "true"
      }
    }
  }
}
```

## Documentation

- **📚 [Installation Guide](docs/installation.md)** - Complete setup instructions for all MCP applications
- **📃 [Feature Guide](docs/features-guide.md)** - Complete list of features
- **📖 [Tools Reference](docs/tools-reference.md)** - Detailed documentation for all 14 tools
- **📥 [Import & Merge Guide](docs/import-and-merge.md)** - Comprehensive guide for Phase 3 features 🆕
- **🔍 [Search & Query Guide](docs/search-and-query.md)** - Advanced search features and natural language queries
- **🗂️ [Usage Examples](docs/examples.md)** - Real-world workflows and practical use cases
- **⚙️ [Data Format Specification](docs/data-format.md)** - Technical details and file formats
- **🛠️ [Troubleshooting](docs/troubleshooting.md)** - Common issues and solutions

## License & Support

**MIT License** - see LICENSE file for details.

**Issues & Feature Requests**: Use the GitHub issue tracker
**Contributing**: Contributions welcome! Please read CONTRIBUTING.md for guidelines