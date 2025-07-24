# Installation & Configuration

This guide covers the complete installation and configuration process for the MemCord MCP Server.

## Prerequisites

- Python 3.8 or higher
- `uv` package manager (recommended) or `pip`

## Installation

### Install with uv (Recommended)

```bash
# Clone the repository
git clone <repository-url>
cd memcord

# Install with uv
uv pip install -e .
```

### Install with pip

```bash
# Clone the repository
git clone <repository-url>
cd memcord

# Install dependencies
pip install -e .
```

## Configuration

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

If you prefer manual configuration or need custom settings:

```bash
# Method 1: Project-specific (shared with team)
claude mcp add memcord uv --directory . run memcord --scope project -e PYTHONPATH=./src -e MEMCORD_ENABLE_ADVANCED=true

# Method 2: User-wide (available across all projects)  
claude mcp add memcord uv --directory /path/to/memcord run memcord --scope user -e PYTHONPATH=/path/to/memcord/src -e MEMCORD_ENABLE_ADVANCED=true

# Method 3: Local to current directory
claude mcp add memcord uv --directory . run memcord -e PYTHONPATH=./src -e MEMCORD_ENABLE_ADVANCED=true
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

By default, the `.mcp.json` configuration enables all 18 tools (9 basic + 9 advanced). To use only basic tools, set:

```bash
# Disable advanced tools
claude mcp configure memcord -e MEMCORD_ENABLE_ADVANCED=false
```

### Claude Desktop

MemCord offers two tool modes. Choose the configuration that fits your needs:

**Configuration Files**:
- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

#### Basic Mode (Default - 8 Tools)
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

#### Advanced Mode (All 17 Tools)
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

## Security & Privacy

- **Local Storage Only**: All data stored locally on your machine
- **No Cloud Dependencies**: No external services or API calls
- **File Permissions**: Standard file system permissions apply
- **MCP Sandboxing**: Resources accessed through MCP security model
- **Search Index Privacy**: All indexing and search operations are local
- **No Data Transmission**: Tags, groups, and queries never leave your system