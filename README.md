<table>
  <tr>
    <td>
      <img src="assets/image/memcord_1024.png" width="256">
    </td>
    <td>
      <h3>MEMCORD v2 (mcp server)</h3>
      <p>
        This privacy-first, self-hosted MCP server helps you organize chat history, summarize messages, search across past chats with AI — and keeps everything secure and fully under your control.
      </p>
    </td>
  </tr>
</table>

[![MCP Server](https://img.shields.io/badge/MCP-Server-blue)](https://github.com/modelcontextprotocol)
  [![Claude Code](https://img.shields.io/badge/Claude-Code-purple)](https://docs.anthropic.com/claude/docs/claude-code)
  [![Claude Desktop](https://img.shields.io/badge/Claude-Desktop-orange)](https://claude.ai/desktop)
  [![Python](https://img.shields.io/badge/Python-3.10+-green)](https://python.org)
  [![License](https://img.shields.io/badge/License-MIT-yellow)](LICENSE)
  [![Buy Me a Coffee](https://img.shields.io/badge/Buy%20Me%20A-Coffee-white)](https://buymeacoffee.com/ukkit)

# Features

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
curl -fsSL https://github.com/ukkit/memcord/raw/main/install.sh | bash
```

This will:
- Download and setup **memcord**
- Set Up Python Virtual Environment using uv
- Update claude_desktop_config.json & README.md with Installation Path

### Claude Desktop Configuration

```json
{
  "mcpServers": {
    "memcord": {
      "command": "uv",
      "args": [
        "--directory",
        "</path/to/memcord>",
        "run",
        "memcord"
      ],
      "env": {
        "PYTHONPATH": "</path/to/memcord/>/src"
      }
    }
  }
}
```

### ✨  Claude Code MCP

```bash
# Add MCP server for your project
claude mcp add-json memcord '{"type":"stdio","command":"uv","args":["--directory","</path/to/memcord>","run","memcord"],"env":{"PYTHONPATH":"</path/to/memcord>/src"}}'

# Verify installation
claude mcp list
claude mcp get memcord

# Add at top of your CLAUDE.md file
memcord_name "NAME_OF_YOUR_PROJECT"
```

### Manual Installaion

```bash
# Traditional installation method
git clone https://github.com/ukkit/memcord.git
cd memcord
uv venv
source .venv/bin/activate
uv pip install -e .

# Replace </path/to/memcord/> in claude_desktop_config.json to the path where you installed it manually
```

**📚 [Complete Installation Guide](docs/installation.md)** - Detailed setup for Claude Code, Claude Desktop, and other MCP applications.

## Basic Usage

```bash
# Create a memory slot and save conversation
memcord_name "project_meeting"
memcord_save "Our discussion about the new API design..."
memcord_save_progress

# Use existing memory slot
memcord_use "project_meeting" 🆕

# Privacy control - activate zero mode (no saving)
memcord_zero  # No memory will be saved until switched to another slot

# Search and query your memories
memcord_search "API design decisions"
memcord_query "What did we decide about authentication?"

```

### 🔧 Basic Mode (Default)

**Core Tools**

- `memcord_name` - Create/select memory slots
- `memcord_save` - Save conversations manually
- `memcord_read` - Retrieve stored content
- `memcord_save_progress` - Auto-summarize and append
- `memcord_list` - List all memory slots
- `memcord_use` - Use existing memory slot

**Privacy Control**

- `memcord_zero` - Activate zero mode - no memory will be saved

**Search & Intelligence**

- `memcord_search` - Full-text search with Boolean operators
- `memcord_query` - Natural language questions about memories

Refer to **📖 [Complete Tools Reference](docs/tools-reference.md)** for Advanced Mode and detailed documentation for all 17 tools with examples and parameters.

## Documentation

- **📚 [Installation Guide](docs/installation.md)** - Complete setup instructions for all MCP applications
- **📃 [Feature Guide](docs/features-guide.md)** - Complete list of features
- **📖 [Tools Reference](docs/tools-reference.md)** - Detailed documentation for all 17 tools
- **📥 [Import & Merge Guide](docs/import-and-merge.md)** - Comprehensive guide for Phase 3 features 🆕
- **🔍 [Search & Query Guide](docs/search-and-query.md)** - Advanced search features and natural language queries
- **🗂️ [Usage Examples](docs/examples.md)** - Real-world workflows and practical use cases
- **⚙️ [Data Format Specification](docs/data-format.md)** - Technical details and file formats
- **🛠️ [Troubleshooting](docs/troubleshooting.md)** - Common issues and solutions

___

**MIT License** - see LICENSE file for details.

**Issues & Feature Requests**: Use the GitHub issue tracker

___

**Found this helpful? [Buy me a coffee ☕](https://buymeacoffee.com/ukkit)**
