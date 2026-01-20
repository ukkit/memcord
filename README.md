<table>
  <tr>
    <td>
      <img src="assets/image/memcord_1024.png" width="256">
    </td>
    <td>
      <h3>MEMCORD v2.3.7 (mcp server)</h3>
      <p>
        This privacy-first, self-hosted MCP server helps you organize chat history, summarize messages, search across past chats with AI — and keeps everything secure and fully under your control.
      </p>
    </td>
  </tr>
</table>

[![MCP Server](https://img.shields.io/badge/MCP-Server-blue)](https://github.com/modelcontextprotocol)
  [![Claude Code](https://img.shields.io/badge/Claude-Code-purple)](https://docs.anthropic.com/claude/docs/claude-code)
  [![Claude Desktop](https://img.shields.io/badge/Claude-Desktop-orange)](https://claude.ai/desktop)
  [![VSCode](https://img.shields.io/badge/Visual_Studio-Code-orange)](https://code.visualstudio.com/)
  [![Google Antigravity](https://img.shields.io/badge/Google-Antigravity-4285F4)](https://antigravity.google)
  [![Python](https://img.shields.io/badge/Python-3.10+-green)](https://python.org)
  [![License](https://img.shields.io/badge/License-MIT-yellow)](LICENSE)
  [![Buy Me a Coffee](https://img.shields.io/badge/Buy%20Me%20A-Coffee-white)](https://buymeacoffee.com/ukkit)

### Never Lose Context Again

Transform your Claude conversations into a searchable, organized knowledge base that grows with you

## ✨ Core Benefits

* **🧠 Infinite Memory** - Claude remembers everything across unlimited conversations with intelligent auto-summarization
* **🔒 Your Data, Your Control** - 100% local storage with zero cloud dependencies or privacy concerns
* **🎯 Effortless Organization** - Smart tags and folders that organize themselves around your workflow
* **🔗 Intelligent Merging** - Automatically combines related conversations while eliminating duplicates

## What's new in v2.3.7

```text
Cross-Platform Support & MCP Compliance:

  - Windows PowerShell installer (install.ps1) for one-line installation
  - Centralized config-templates/ folder with platform-specific configs
  - Cross-platform config generator (scripts/generate-config.py)
  - Windows cmd /c wrapper support for proper process spawning
  - Updated MCP SDK version constraint to v1.22-2.0 for stability
  - Logging configuration to prevent stdout corruption in STDIO mode
```

<details>
<summary>v2.3.6 - Google Antigravity IDE Support</summary>

```text
  - Added Google Antigravity IDE configuration template
  - Full compatibility with Antigravity's MCP server integration
```
</details>

## 🚀 Quick Start

**macOS / Linux:**
```bash
curl -fsSL https://github.com/ukkit/memcord/raw/main/install.sh | bash
```

**Windows (PowerShell):**
```powershell
irm https://github.com/ukkit/memcord/raw/main/install.ps1 | iex
```

This will:
- Download and setup **memcord**
- Set up Python virtual environment using uv
- Generate platform-specific MCP configuration files
- Configure Claude Desktop, Claude Code, VSCode, and Antigravity IDE

### Configuration Templates

All MCP configuration templates are in `config-templates/`. After installation, run:

```bash
# Regenerate configs (useful after updates or path changes)
uv run python scripts/generate-config.py

# Windows users
uv run python scripts/generate-config.py --platform windows

# Preview changes without writing
uv run python scripts/generate-config.py --dry-run
```

### Claude Desktop

Copy the generated `claude_desktop_config.json` to your Claude Desktop config location:

| Platform | Config Location |
|----------|-----------------|
| macOS | `~/Library/Application Support/Claude/claude_desktop_config.json` |
| Windows | `%APPDATA%\Claude\claude_desktop_config.json` |
| Linux | `~/.config/Claude/claude_desktop_config.json` |

Or use the template from `config-templates/claude-desktop/`:

```json
{
  "mcpServers": {
    "memcord": {
      "command": "uv",
      "args": ["--directory", "/path/to/memcord", "run", "memcord"],
      "env": {
        "PYTHONPATH": "/path/to/memcord/src",
        "MEMCORD_ENABLE_ADVANCED": "false"
      }
    }
  }
}
```

**Windows users:** Use `config-templates/claude-desktop/config.windows.json` which includes the required `cmd /c` wrapper.

### VSCode with GitHub Copilot

**Prerequisites:**
- VSCode 1.102+ (MCP support is GA)
- GitHub Copilot subscription
- Organization/Enterprise MCP policy enabled (if applicable)

**Setup:**

The installer creates `.vscode/mcp.json` automatically. Or copy manually:

```bash
cp config-templates/vscode/mcp.json .vscode/mcp.json
```

The VSCode config uses `${workspaceFolder}` variables, so no path replacement needed:

```json
{
  "servers": {
    "memcord": {
      "command": "uv",
      "args": ["--directory", "${workspaceFolder}", "run", "memcord"],
      "env": {
        "PYTHONPATH": "${workspaceFolder}/src",
        "MEMCORD_ENABLE_ADVANCED": "false"
      }
    }
  }
}
```

**GitHub Copilot Agent Mode:**
Once configured, memcord tools are available in Copilot agent mode. Use natural language:
- "Create a memory slot for this project"
- "Search my memories for API design decisions"
- "Query past conversations about authentication"

**[Complete VSCode Setup Guide](docs/vscode-setup.md)** - Detailed instructions for VSCode and GitHub Copilot integration.

### Google Antigravity IDE

The installer generates `.antigravity/mcp_config.json` automatically. Or configure manually:

```json
{
  "mcpServers": {
    "memcord": {
      "command": "uv",
      "args": ["--directory", "/absolute/path/to/memcord", "run", "memcord"],
      "env": {
        "PYTHONPATH": "/absolute/path/to/memcord/src",
        "MEMCORD_ENABLE_ADVANCED": "false"
      }
    }
  }
}
```

> **Note:** Antigravity requires absolute paths.

<img alt="Anti-Gravity screenshot with memcord" src="assets/image/anti-gravity.png">

### Claude Code CLI

The installer creates `.mcp.json` in the project root. Or add manually:

```bash
claude mcp add-json memcord '{"type":"stdio","command":"uv","args":["--directory","/path/to/memcord","run","memcord"],"env":{"PYTHONPATH":"/path/to/memcord/src"}}'
```

**Windows users:** Use `cmd` wrapper:
```powershell
claude mcp add-json memcord '{"type":"stdio","command":"cmd","args":["/c","uv","--directory","C:\\path\\to\\memcord","run","memcord"],"env":{"PYTHONPATH":"C:\\path\\to\\memcord\\src"}}'
```

Verify installation:

```bash
claude mcp list
claude mcp get memcord
```

Add at top of your CLAUDE.md file:

```bash
memcord_name "NAME_OF_YOUR_PROJECT"
```

### Manual Installation

```bash
git clone https://github.com/ukkit/memcord.git
cd memcord
uv venv
source .venv/bin/activate  # Windows: .venv\Scripts\Activate.ps1
uv pip install -e .

# Generate configuration files
uv run python scripts/generate-config.py
```

### Update Existing Installation

```bash
cd /path/to/memcord
git pull
uv pip install -e .
uv run python scripts/generate-config.py  # Regenerate configs
```

**[Complete Installation Guide](docs/installation.md)** - Detailed setup for Claude Code, Claude Desktop, and other MCP applications.

## 💻 Basic Usage

```bash
# Create a memory slot and save conversation
memcord_name "project_meeting"
memcord_save "Our discussion about the new API design..."
memcord_save_progress

# Use existing memory slot
memcord_use "project_meeting" 🆕

# Navigate timeline - select specific entries
memcord_select_entry "2 hours ago"  # or "latest", index, timestamp 🆕

# Privacy control - activate zero mode (no saving)
memcord_zero  # No memory will be saved until switched to another slot

# Search and query your memories
memcord_search "API design decisions"
memcord_query "What did we decide about authentication?"

# Merge related conversations
memcord_merge ["project_meeting", "api_notes"] "consolidated_project" 🆕

```
Refer to **📖 [Complete Tools Reference](docs/tools-reference.md)** for Advanced Mode and detailed documentation for all 19 tools with examples and parameters.

## 📚 Documentation
<details><summary>⚠️ Documentation updates in progress </summary>

- **📚 [Installation Guide](docs/installation.md)** - Complete setup instructions for all MCP applications
- **📃 [Feature Guide](docs/features-guide.md)** - Complete list of features
- **📖 [Tools Reference](docs/tools-reference.md)** - Detailed documentation for all 19 tools
- **📥 [Import & Merge Guide](docs/import-and-merge.md)** - Comprehensive guide for Phase 3 features 🆕
- **🔍 [Search & Query Guide](docs/search-and-query.md)** - Advanced search features and natural language queries
- **🗂️ [Usage Examples](docs/examples.md)** - Real-world workflows and practical use cases
- **⚙️ [Data Format Specification](docs/data-format.md)** - Technical details and file formats
- **🛠️ [Troubleshooting](docs/troubleshooting.md)** - Common issues and solutions

</details>

---

💎 If you find this project helpful, consider:

 - 🌟 Starring the repository on GitHub
 - 🤝 [Support Development](https://buymeacoffee.com/ukkit)
 - 🐛 Reporting bugs and suggesting features

___

**MIT License** - see LICENSE file for details.

---

## Star History

[![Star History Chart](https://api.star-history.com/svg?repos=ukkit/memcord&type=date&legend=top-left)](https://www.star-history.com/#ukkit/memcord&type=date&legend=top-left)
