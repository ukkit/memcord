# Installation & Configuration

This guide covers the complete installation and configuration process for the MemCord MCP Server.

## Prerequisites

- Python 3.10 or higher
- `uv` package manager (recommended) or `pip`

## Installation

### Install with uv (Recommended)

```bash
# Clone the repository
git clone https://github.com/ukkit/memcord.git
cd memcord

# Install with uv (core deps including sumy)
uv pip install -e .
```

### Install with pip

```bash
# Clone the repository
git clone https://github.com/ukkit/memcord.git
cd memcord

# Install dependencies
pip install -e .
```

### Optional Summarizer Backends

The default summarizer is `sumy` (graph-based, zero model files, included in core deps). Two heavier backends are available as optional extras:

```bash
# Semantic backend — sentence-transformers + MMR (~80MB one-time download)
uv pip install -e ".[semantic]"
pip install -e ".[semantic]"

# Transformers backend — HuggingFace BART abstractive summarizer (~400MB one-time download)
uv pip install -e ".[transformers]"
pip install -e ".[transformers]"
```

After installing, configure a slot to use the new backend:
```
memcord_configure action="set" key="summarizer_backend" value="semantic"
memcord_configure action="set" key="summarizer_backend" value="transformers"
```

## Configuration

### OpenClaw

**Step 1 — Install the skill from ClawHub:**

```bash
openclaw skills install memcord --force
```

**Step 2 — Add the MCP server config manually** to `~/.openclaw/openclaw.json`:

```json
{
  "mcp": {
    "servers": {
      "memcord": {
        "command": "uvx",
        "args": ["memcord"],
        "toolFilter": {
          "include": ["memcord_auto_save", "memcord_read"]
        }
      }
    }
  }
}
```

To use a named slot instead of the default `"default"` slot, add an `"env"` field:

```json
{
  "mcp": {
    "servers": {
      "memcord": {
        "command": "uvx",
        "args": ["memcord"],
        "env": { "MEMCORD_DEFAULT_SLOT": "main" },
        "toolFilter": {
          "include": ["memcord_auto_save", "memcord_read"]
        }
      }
    }
  }
}
```

**Step 3 — Verify:**

```bash
openclaw mcp list
```

Memcord exposes two tools in OpenClaw: `memcord_auto_save` (write) and `memcord_read` (read). The `uvx memcord` command downloads memcord from PyPI on first run — no separate installation required.

### Claude Code CLI (Recommended) ⭐

MemCord includes a `.mcp.json` configuration file for seamless Claude Code integration. This enables project-level configuration and team sharing via version control.

#### Project-Level Installation (Team Sharing)

```bash
# Navigate to the memcord project directory
cd /path/to/memcord

# Install the MCP server for this project
claude mcp install ./

# Or install from the current directory
claude mcp install .
```

#### Manual Claude Code Configuration

If you prefer manual configuration or need custom settings, run these from any directory — replace `/path/to/memcord` with the absolute path to your memcord installation:

**macOS / Linux:**
```bash
# Project-specific (shared with team via version control)
claude mcp add memcord uv --directory /path/to/memcord run memcord --scope project -e PYTHONPATH=/path/to/memcord/src -e MEMCORD_ENABLE_ADVANCED=false

# User-wide (available across all projects)
claude mcp add memcord uv --directory /path/to/memcord run memcord --scope user -e PYTHONPATH=/path/to/memcord/src -e MEMCORD_ENABLE_ADVANCED=false
```

**Windows (PowerShell):**

Windows requires `cmd /c` wrapper and `add-json` to avoid argument parsing issues:
```powershell
# Project-specific (shared with team via version control)
claude mcp add-json memcord '{"type":"stdio","command":"cmd","args":["/c","uv","--directory","C:\\path\\to\\memcord","run","memcord"],"env":{"PYTHONPATH":"C:\\path\\to\\memcord\\src","MEMCORD_ENABLE_ADVANCED":"false"}}' --scope project

# User-wide (available across all projects)
claude mcp add-json memcord '{"type":"stdio","command":"cmd","args":["/c","uv","--directory","C:\\path\\to\\memcord","run","memcord"],"env":{"PYTHONPATH":"C:\\path\\to\\memcord\\src","MEMCORD_ENABLE_ADVANCED":"false"}}' --scope user
```

#### Verification

Verify the server is configured correctly:
```bash
# List all configured MCP servers
claude mcp list

# Get detailed information about memcord
claude mcp get memcord

# Test the server startup
claude mcp test memcord
```

#### Advanced Tools

By default, the `.mcp.json` configuration enables all 23 tools (15 basic + 8 advanced). To use only basic tools, set:

```bash
# Disable advanced tools
claude mcp configure memcord -e MEMCORD_ENABLE_ADVANCED=false
```

#### Summarizer Backend (Optional)

Set `MEMCORD_SUMMARIZER` to override the per-slot summarizer config for all slots. Useful for Docker/CI where you want a fixed backend regardless of individual slot settings:

```bash
# Force sumy for all slots (default for new slots anyway)
claude mcp configure memcord -e MEMCORD_SUMMARIZER=sumy

# Force NLTK for all slots (backward-compatible, no extra deps)
claude mcp configure memcord -e MEMCORD_SUMMARIZER=nltk

# Force semantic backend (requires: pip install memcord[semantic])
claude mcp configure memcord -e MEMCORD_SUMMARIZER=semantic

# Force transformers backend (requires: pip install memcord[transformers])
claude mcp configure memcord -e MEMCORD_SUMMARIZER=transformers
```

When not set, each slot uses its own backend as configured via `memcord_configure`.

#### Auto-Save Hooks (Optional)

Memcord can automatically save conversation progress when Claude Code compacts context:

```bash
uv run python scripts/generate-config.py --install-hooks
```

This installs agent hooks into `.claude/settings.json`:
- **PreCompact** — saves a summary before context compaction

> **Note:** `SessionEnd` with `type: "agent"` is not supported by Claude Code. Re-running `--install-hooks` will automatically remove any stale `SessionEnd` hook from a previous install.

**Verify installation:** Check `.claude/settings.json` for a `hooks.PreCompact` entry with a `"memcord:"` description.

**Remove hooks:** Edit `.claude/settings.json` and delete the memcord hook entry from the `PreCompact` array.

### Claude Desktop

MemCord offers two tool modes. Choose the configuration that fits your needs:

**Configuration Files**:
- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

#### Basic Mode (Default - 15 Tools)
Essential memory management features:

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

#### Advanced Mode (All 23 Tools)
Includes organization, import/export, and advanced features:

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

**Note**: You can switch between modes anytime by changing the environment variable and restarting Claude Desktop.

### Other MCP Applications

The server can be started directly:

```bash
# Run the server
uv run memcord

# Or with Python
python -m memcord.server
```

## Custom Claude Code Commands

You can create custom slash commands for common memory operations.

### Setup Custom Commands

```bash
# Create commands directory (project-specific)
mkdir -p .claude/commands

# Or create user-wide commands
mkdir -p ~/.claude/commands
```

### Example Commands

Create these files in your `.claude/commands/` directory:

**`.claude/commands/memory-save.md`**
```markdown
---
description: Save current conversation to memory
---

Save the current conversation to memory slot: $ARGUMENTS

Use the memcord_name tool to set the memory slot, then use memcord_save to save our conversation.
```

**`.claude/commands/memory-read.md`**
```markdown
---
description: Read from memory slot
---

Read from memory slot: $ARGUMENTS

Use the memcord_read tool to retrieve the content from the specified memory slot.
```

**`.claude/commands/memory-list.md`**
```markdown
---
description: List all memory slots
---

List all available memory slots.

Use the memcord_list tool to show all memory slots with their metadata.
```

**`.claude/commands/memory-search.md`**
```markdown
---
description: Search across all memory slots
---

Search for: $ARGUMENTS

Use the memcord_search tool to find information across all memory slots.
```

**`.claude/commands/memory-ask.md`**
```markdown
---
description: Ask questions about your memories
---

Answer this question about my memories: $ARGUMENTS

Use the memcord_query tool to process this natural language question.
```

**`.claude/commands/memory-organize.md`**
```markdown
---
description: Add tags to current memory slot
---

Add tags to current memory slot: $ARGUMENTS

Use the memcord_tag tool with action 'add' to organize the current memory slot.
```

### Usage

After creating the commands, use them in Claude Code:

```
/project:memory-save project_discussion
/project:memory-read project_discussion
/project:memory-list
/project:search-memory API changes
/project:query-memory "What decisions were made last week?"
```

## MCP File Resources

Memory slots are automatically available as MCP file resources:

- `memory://slot_name.md` - Markdown format
- `memory://slot_name.txt` - Plain text format
- `memory://slot_name.json` - JSON format

These resources update automatically when memory slots change and can be accessed by other MCP applications.

## Update Existing Installation

```bash
cd /path/to/memcord
git pull
uv pip install -e .
uv run python scripts/generate-config.py  # Regenerate configs

# Optional: Enable auto-save hooks
uv run python scripts/generate-config.py --install-hooks
```

## Security & Privacy

- **Local Storage Only**: All data stored locally on your machine
- **No Cloud Dependencies**: No external services or API calls
- **File Permissions**: Standard file system permissions apply
- **MCP Sandboxing**: Resources accessed through MCP security model
- **Search Index Privacy**: All indexing and search operations are local
- **No Data Transmission**: Tags, groups, and queries never leave your system