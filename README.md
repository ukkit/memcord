<table>
  <tr>
    <td>
      <img src="assets/image/memcord_1024.png" width="256">
    </td>
    <td>
      <h3>MEMCORD v2.4.0 (mcp server)</h3>
      <p>
        This privacy-first, self-hosted MCP server helps you organize chat history, summarize messages, search across past chats with AI — and keeps everything secure and fully under your control.
      </p>
    </td>
  </tr>
</table>

<p align="center">
  <a href="https://github.com/modelcontextprotocol"><img src="https://img.shields.io/badge/MCP-Server-blue" alt="MCP Server"></a>
  <a href="https://docs.anthropic.com/claude/docs/claude-code"><img src="https://img.shields.io/badge/Claude-Code-purple" alt="Claude Code"></a>
  <a href="https://claude.ai/desktop"><img src="https://img.shields.io/badge/Claude-Desktop-orange" alt="Claude Desktop"></a>
  <a href="https://code.visualstudio.com/"><img src="https://img.shields.io/badge/Visual_Studio-Code-orange" alt="VSCode"></a>
  <a href="https://antigravity.google"><img src="https://img.shields.io/badge/Google-Antigravity-4285F4" alt="Google Antigravity"></a>
  <a href="https://python.org"><img src="https://img.shields.io/badge/Python-3.10+-green" alt="Python"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-yellow" alt="License"></a>
  <a href="https://github.com/ukkit/memcord/actions/workflows/ci.yml"><img src="https://github.com/ukkit/memcord/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="https://buymeacoffee.com/ukkit"><img src="https://img.shields.io/badge/Buy%20Me%20A-Coffee-white" alt="Buy Me a Coffee"></a>
</p>

<h2 align="center">Never Lose Context Again</h2>
<p align="center"><em>Transform your Claude conversations into a searchable, organized knowledge base that grows with you</em></p>

## Core Benefits

* **Infinite Memory** - Claude remembers everything across unlimited conversations with intelligent auto-summarization
* **Your Data, Your Control** - 100% local storage with zero cloud dependencies or privacy concerns
* **Effortless Organization** - Smart tags and folders that organize themselves around your workflow
* **Intelligent Merging** - Automatically combines related conversations while eliminating duplicates

**[What's new in v2.4.0](docs/versions.md#v240---project-memory-binding--auto-detection)** — Project memory binding & auto-detection for Claude Code. See [Project Setup Workflow](#project-setup-workflow) for details.

## Prerequisites

- **Python 3.10+** — [python.org](https://python.org)
- **uv** (Python package manager) — install with:

  **macOS / Linux:**
  ```bash
  curl -LsSf https://astral.sh/uv/install.sh | sh
  ```
  **Windows (PowerShell):**
  ```powershell
  powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
  ```

## Quick Start

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

## IDE Configuration

The installer auto-configures all supported IDEs. For manual setup or troubleshooting, see the detailed guides:

| IDE / Client | Guide |
|---|---|
| Claude Code CLI | [Installation Guide — Claude Code](docs/installation.md#claude-code-cli-recommended-) |
| Claude Desktop | [Installation Guide — Claude Desktop](docs/installation.md#claude-desktop) |
| VSCode + GitHub Copilot | [VSCode Setup Guide](docs/vscode-setup.md) |
| Google Antigravity | [Installation Guide — Other MCP Apps](docs/installation.md#other-mcp-applications) |
| Configuration templates | [`config-templates/`](config-templates/) ([README](config-templates/README.md)) |

### Manual Installation

```bash
git clone https://github.com/ukkit/memcord.git
cd memcord
uv venv && uv pip install -e .
uv run python scripts/generate-config.py
```

See the **[Complete Installation Guide](docs/installation.md)** for updating, advanced options, and custom commands.

<a id="project-setup-workflow"></a>

## Project Setup Workflow

### First-Time Setup (New Project)

```bash
# 1. Once you are in claude code, initialize the project with a memory slot (one-time setup)
memcord_init "." "my-project-name"
OR
memcord_init "my_project_name"
# Creates .memcord file containing "my-project-name"

# 2. Start saving your conversations
/memcord-save-progress  # Auto-detects slot from .memcord file
```

### Subsequent Sessions (Returning to Project)

```bash
# Just use slash commands - no slot name needed!
/memcord-read           # Reads from bound slot automatically

/memcord-save           # Saves to bound slot automatically
/memcord-save-progress  # Summarizes and saves automatically
```

### How Auto-Detection Works

1. When you run `/memcord-read` (or save/save-progress) without arguments
2. Claude checks for `.memcord` file in the current working directory
3. If found, reads the slot name and uses it automatically
4. No need to remember or type slot names!

## Basic Usage

```bash
# Create a memory slot and save conversation
memcord_name "project_meeting"
memcord_save "Our discussion about the new API design..."
memcord_save_progress

# Use existing memory slot
memcord_use "project_meeting"

# Navigate timeline - select specific entries
memcord_select_entry "2 hours ago"  # or "latest", index, timestamp

# Privacy control - activate zero mode (no saving)
memcord_zero  # No memory will be saved until switched to another slot

# Search and query your memories
memcord_search "API design decisions"
memcord_query "What did we decide about authentication?"

# Merge related conversations
memcord_merge ["project_meeting", "api_notes"] "consolidated_project"

# Initialize project directory with memory slot (auto-detection for slash commands)
memcord_init "." "my-project"  # Creates .memcord file
memcord_unbind "."             # Removes binding

```
Refer to **[Complete Tools Reference](docs/tools-reference.md)** for Advanced Mode and detailed documentation for all 21 tools with examples and parameters.

## Documentation

- **[Installation Guide](docs/installation.md)** - Complete setup instructions for all MCP applications
- **[Feature Guide](docs/features-guide.md)** - Complete list of features
- **[Tools Reference](docs/tools-reference.md)** - Detailed documentation for all 21 tools
- **[Import & Merge Guide](docs/import-and-merge.md)** - Comprehensive guide for Phase 3 features
- **[Search & Query Guide](docs/search-and-query.md)** - Advanced search features and natural language queries
- **[Usage Examples](docs/examples.md)** - Real-world workflows and practical use cases
- **[Data Format Specification](docs/data-format.md)** - Technical details and file formats
- **[Troubleshooting](docs/troubleshooting.md)** - Common issues and solutions
- **[Version History](docs/versions.md)** - Changelog for all releases

---

If you find this project helpful, consider:

 - ⭐ Starring the repository on GitHub
 - 💸 [Support Development](https://buymeacoffee.com/ukkit)
 - 🐛 Reporting bugs and suggesting features

___

**MIT License** - see LICENSE file for details.

---

## Star History

[![Star History Chart](https://api.star-history.com/svg?repos=ukkit/memcord&type=date&legend=top-left)](https://www.star-history.com/#ukkit/memcord&type=date&legend=top-left)
