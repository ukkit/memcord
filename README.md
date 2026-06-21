<div align="center">
  <img src="assets/image/memcord_1024.png" width="256">
  <h3>MEMCORD v4.1.0 (mcp server)</h3>
  <p>This privacy-first, self-hosted MCP server helps you organize chat history, summarize messages, search across past chats with AI — and keeps everything secure and fully under your control.</p>
</div>

<p align="center">
  <a href="https://github.com/modelcontextprotocol"><img src="https://img.shields.io/badge/MCP-Server-blue" alt="MCP Server"></a>
  <a href="https://docs.anthropic.com/claude/docs/claude-code"><img src="https://img.shields.io/badge/Claude-Code-purple" alt="Claude Code"></a>
  <a href="https://claude.ai/desktop"><img src="https://img.shields.io/badge/Claude-Desktop-orange" alt="Claude Desktop"></a>
  <a href="https://code.visualstudio.com/"><img src="https://img.shields.io/badge/Visual_Studio-Code-orange" alt="VSCode"></a>
  <a href="https://antigravity.google"><img src="https://img.shields.io/badge/Google-Antigravity-4285F4" alt="Google Antigravity"></a>
  <a href="https://python.org"><img src="https://img.shields.io/badge/Python-3.10+-green" alt="Python"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-yellow" alt="License"></a>
  <a href="https://buymeacoffee.com/ukkit"><img src="https://img.shields.io/badge/Buy%20Me%20A-Coffee-white" alt="Buy Me a Coffee"></a>
</p>

<h2 align="center">Never Lose Context Again</h2>
<p align="center"><em>Transform your Claude conversations into a searchable, organized knowledge base that grows with you</em></p>

> **[What's new in v4.1.0](docs/versions.md#v410---custom-storage-path)** — Share a memory slot across devices: point any slot at a custom directory (e.g. a synced Dropbox/OneDrive folder) via `memcord_configure`, with automatic migration of existing data.

## Table of Contents

- [Core Benefits](#core-benefits)
- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Keeping Memcord Updated](#keeping-memcord-updated)
- [Using Memcord](#using-memcord)
- [Custom Storage Path](#custom-storage-path)
- [Summarizer Backends](#summarizer-backends)
- [IDE Configuration](#ide-configuration)
- [Documentation](#documentation)

## Core Benefits

* **Infinite Memory** - Claude remembers everything across unlimited conversations with intelligent auto-summarization
* **Your Data, Your Control** - 100% local storage with zero cloud dependencies or privacy concerns
* **Effortless Organization** - Per-project memory slots with timeline navigation and smart tagging
* **Intelligent Merging** - Automatically combines related conversations while eliminating duplicates

## Prerequisites

<details>
<summary>Python 3.10+ and uv are required. The installer handles both — click to expand manual instructions.</summary>

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

</details>

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
- ✅ Download and setup **memcord**
- ✅ Set up Python virtual environment using uv
- ✅ Generate platform-specific MCP configuration files
- ✅ Configure Claude Desktop, Claude Code, VSCode, and Antigravity IDE

## Keeping Memcord Updated

```bash
cd /path/to/memcord
git pull
uv pip install -e .
uv run python scripts/generate-config.py  # Regenerate configs

# Optional: Enable auto-save hooks (new in v2.5.0)
uv run python scripts/generate-config.py --install-hooks
```

The `--install-hooks` flag is idempotent — it merges into existing `.claude/settings.json` without overwriting other settings or hooks.

## Using Memcord

### First-Time Setup (New Project)

```bash
# 1. Once you are in claude code, initialize the project with a memory slot (one-time setup)
memcord_init "." "my-project-name"
# OR
memcord_init "my_project_name"
# Creates .memcord file containing "my-project-name"

# 2. Start saving your conversations
/memcord-save-progress  # Auto-detects slot from .memcord file
```

### Subsequent Sessions (Returning to Project)

```bash
# Just use slash commands - no slot name needed!
/memcord-read           # Reads from bound slot
/memcord-save           # Saves to bound slot
/memcord-save-progress  # Summarizes and saves
```

### Saving, Searching & Querying (Direct Tool Calls)

```bash
memcord_name "project_meeting"          # Create or select a slot (outside a bound project)
memcord_save "Our discussion about..."  # Save exact text
memcord_save_progress                   # Save a compressed summary
memcord_read                            # Read the slot

memcord_select_entry "2 hours ago"    # Jump to a point in the timeline
memcord_list                          # List all slots
memcord_search "API design"           # Full-text search
memcord_query "What did we decide?"   # Natural language query

memcord_zero                          # Privacy mode — nothing gets saved
```

See **[Complete Tools Reference](docs/tools-reference.md)** for all 23 tools with full parameters and examples.

### Enable Auto-Save (Optional)

```bash
uv run python scripts/generate-config.py --install-hooks
```

Automatically saves conversation progress before context compaction and on session end. See [config-templates/README.md](config-templates/README.md#auto-save-hooks-optional) for details.

### How Auto-Detection Works

All read **and write** operations follow the same slot resolution priority:

1. Explicit `slot_name` argument (always wins)
2. Currently active slot (set by `memcord_use` or `memcord_name`)
3. `.memcord` binding file in the current working directory

When the `.memcord` binding is used and the slot already exists, it is also **auto-activated** for the rest of the session — so subsequent operations skip re-detection automatically.

This means after `memcord_init`, a fresh session (no `memcord_use` call needed) will correctly route `memcord_save`, `memcord_save_progress`, `memcord_configure`, and `memcord_read` to the bound slot.

## Custom Storage Path

Point a slot's data file at any directory — e.g. a Dropbox/OneDrive folder — to share it across devices, via `memcord_configure`.

**New memory in an external path:**
```bash
memcord_name "shared_slot"
memcord_configure action="set" key="custom_storage_path" value="D:\Dropbox\shared"
memcord_save "..."   # writes directly to the external path
```

**Migrate an existing memory:**
```bash
memcord_configure action="set" key="custom_storage_path" value="D:\Dropbox\shared"
# Existing data is moved automatically — memcord_read/memcord_list keep working
```

Each device needs to run the `set` command once with its own local path to the shared folder. See **[Tools Reference — memcord_configure](docs/tools-reference.md#6-memcord_configure)** for migration/collision details.

## Summarizer Backends

Memcord supports four pluggable summarizer backends (`nltk`, `sumy`, `semantic`, `transformers`), switchable per slot via `memcord_configure action="set" key="summarizer_backend" value="..."` — no restart required. New slots default to **sumy** (no downloads); existing slots keep **nltk** for backward compatibility.

See **[Tools Reference — memcord_configure](docs/tools-reference.md#6-memcord_configure)** and **[Features Guide](docs/features-guide.md#auto-summarization)** for the full backend comparison, install instructions, and the `MEMCORD_SUMMARIZER` env var override.

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

## Documentation

| Guide | Description |
|---|---|
| **[Installation Guide](docs/installation.md)** | Complete setup instructions for all MCP applications |
| **[Feature Guide](docs/features-guide.md)** | Complete list of features |
| **[Tools Reference](docs/tools-reference.md)** | Detailed documentation for all 23 tools |
| **[Import & Merge Guide](docs/import-and-merge.md)** | Comprehensive guide for Phase 3 features |
| **[Search & Query Guide](docs/search-and-query.md)** | Advanced search features and natural language queries |
| **[Usage Examples](docs/examples.md)** | Real-world workflows and practical use cases |
| **[Data Format Specification](docs/data-format.md)** | Technical details and file formats |
| **[Troubleshooting](docs/troubleshooting.md)** | Common issues and solutions |
| **[Version History](docs/versions.md)** | Changelog for all releases |

---

If you find this project helpful, consider:

 - ⭐ Starring the repository on GitHub
 - ☕ [Support Development](https://buymeacoffee.com/ukkit)
 - 🐛 Reporting bugs and suggesting features

---

**MIT License** - see LICENSE file for details.

---

## Star History

[![Star History Chart](https://api.star-history.com/svg?repos=ukkit/memcord&type=date&legend=top-left)](https://www.star-history.com/#ukkit/memcord&type=date&legend=top-left)
