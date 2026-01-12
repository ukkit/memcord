# VSCode and GitHub Copilot Setup Guide

This guide provides detailed instructions for integrating memcord with VSCode and GitHub Copilot agent mode.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Installation Methods](#installation-methods)
- [Configuration Options](#configuration-options)
- [GitHub Copilot Agent Mode](#github-copilot-agent-mode)
- [Enterprise Setup](#enterprise-setup)
- [Verification](#verification)
- [Troubleshooting](#troubleshooting)
- [Advanced Configuration](#advanced-configuration)

---

## Prerequisites

### Required

- **VSCode**: Version 1.102 or higher (MCP support is generally available)
- **Python**: 3.10 or higher
- **uv**: Python package manager ([installation guide](https://github.com/astral-sh/uv))
- **Memcord**: Installed and configured (see main [installation guide](installation.md))

### Optional but Recommended

- **GitHub Copilot**: Subscription required for Copilot agent mode
  - Individual, Business, or Enterprise subscription
  - GitHub Copilot Chat extension installed in VSCode

### Enterprise Requirements

- **MCP Policy**: Must be enabled by organization/enterprise administrator
  - Policy name: "MCP servers in Copilot"
  - Default: Disabled for security
  - Contact your IT administrator to enable

---

## Installation Methods

### Method 1: Workspace Configuration (Recommended)

Best for project-specific memory slots and team collaboration.

**Step 1: Copy Example Configuration**

```bash
# From your project directory
mkdir -p .vscode
cp /path/to/memcord/.vscode/mcp.json.example .vscode/mcp.json
```

**Step 2: Update Paths**

Edit `.vscode/mcp.json` and replace paths if memcord is not in your workspace:

```json
{
  "servers": {
    "memcord": {
      "command": "uv",
      "args": [
        "--directory",
        "/absolute/path/to/memcord",
        "run",
        "memcord"
      ],
      "env": {
        "PYTHONPATH": "/absolute/path/to/memcord/src"
      }
    }
  }
}
```

**Step 3: Reload VSCode**

- Open Command Palette: `Ctrl+Shift+P` (Windows/Linux) or `Cmd+Shift+P` (macOS)
- Run: `Developer: Reload Window`

**Benefits:**
- Configuration is scoped to the project
- Can be version controlled (recommended)
- Portable across team members
- Uses `${workspaceFolder}` variable when memcord is in the workspace

---

### Method 2: Root-Level Configuration

Alternative for source-controlled configuration.

**Step 1: Copy Example**

```bash
cp /path/to/memcord/.mcp.json.example .mcp.json
```

**Step 2: Edit Configuration**

Update `.mcp.json` with absolute paths:

```json
{
  "servers": {
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
        "MEMCORD_ENABLE_ADVANCED": "false"
      }
    }
  }
}
```

**Step 3: Reload VSCode**

---

### Method 3: Global User Configuration

Best for using memcord across all projects.

**Step 1: Open User Configuration**

1. Open Command Palette: `Ctrl+Shift+P` / `Cmd+Shift+P`
2. Run: `MCP: Open User Configuration`
3. VSCode opens `mcp.json` in your user profile

**Step 2: Add Memcord Server**

```json
{
  "servers": {
    "memcord": {
      "command": "uv",
      "args": [
        "--directory",
        "/absolute/path/to/memcord",
        "run",
        "memcord"
      ],
      "env": {
        "PYTHONPATH": "/absolute/path/to/memcord/src"
      }
    }
  }
}
```

**Step 3: Save and Reload**

---

### Method 4: Extensions View (Future)

When memcord is published to the MCP registry:

1. Open Extensions view: `Ctrl+Shift+X` / `Cmd+Shift+X`
2. Search: `@mcp memcord`
3. Install directly from the registry

**Note:** This method is not yet available but is planned for future releases.

---

## Configuration Options

### Environment Variables

You can customize memcord behavior using environment variables:

```json
{
  "servers": {
    "memcord": {
      "command": "uv",
      "args": ["--directory", "/path/to/memcord", "run", "memcord"],
      "env": {
        "PYTHONPATH": "/path/to/memcord/src",
        "MEMCORD_ENABLE_ADVANCED": "true",
        "MEMCORD_MEMORY_DIR": "./custom_memory_slots",
        "MEMCORD_SHARED_DIR": "./custom_shared_memories"
      }
    }
  }
}
```

**Available Variables:**

| Variable | Description | Default |
|----------|-------------|---------|
| `PYTHONPATH` | Path to memcord source | Required |
| `MEMCORD_ENABLE_ADVANCED` | Enable advanced tools (19 total) | `false` (11 basic tools) |
| `MEMCORD_MEMORY_DIR` | Custom memory slots directory | `memory_slots/` |
| `MEMCORD_SHARED_DIR` | Custom shared memories directory | `shared_memories/` |

### Using VSCode Variables

For workspace-relative paths:

```json
{
  "servers": {
    "memcord": {
      "command": "uv",
      "args": [
        "--directory",
        "${workspaceFolder}/memcord",
        "run",
        "memcord"
      ],
      "env": {
        "PYTHONPATH": "${workspaceFolder}/memcord/src"
      }
    }
  }
}
```

**Supported Variables:**
- `${workspaceFolder}` - Root of the opened workspace
- `${workspaceFolderBasename}` - Name of workspace folder
- `${userHome}` - User's home directory

---

## GitHub Copilot Agent Mode

### Overview

When memcord is configured, all tools become available in GitHub Copilot agent mode. Copilot can invoke memcord tools using natural language commands.

### Activating Agent Mode

1. Open GitHub Copilot Chat panel
2. Start your prompt with `@workspace` to activate agent mode
3. Ask Copilot to use memcord tools

### Example Interactions

**Creating and Saving Memory:**

```
User: @workspace Create a memory slot called "api-redesign" and save our discussion about REST vs GraphQL

Copilot: [Uses memcord_name and memcord_save tools]
```

**Searching Past Conversations:**

```
User: @workspace Search my memcord memories for decisions about authentication

Copilot: [Uses memcord_search tool]
```

**Natural Language Queries:**

```
User: @workspace What did we decide about the database schema last week?

Copilot: [Uses memcord_query tool with temporal filtering]
```

**Merging Related Discussions:**

```
User: @workspace Merge my "sprint-planning" and "backlog-review" memory slots

Copilot: [Uses memcord_merge tool]
```

### Available Tools in Agent Mode

**Basic Mode (11 tools):**
- `memcord_name` - Create/select memory slots
- `memcord_use` - Switch to existing slot
- `memcord_save` - Save content directly
- `memcord_save_progress` - Auto-summarize and save
- `memcord_read` - Read slot contents
- `memcord_list` - List all slots
- `memcord_search` - Full-text search
- `memcord_query` - Natural language queries
- `memcord_zero` - Privacy mode (no saving)
- `memcord_select_entry` - Timeline navigation
- `memcord_merge` - Merge slots

**Advanced Mode (8 additional tools):**

Enable with `MEMCORD_ENABLE_ADVANCED=true` in configuration:

- `memcord_tag` - Tag management
- `memcord_import` - Import content (PDF, URL, etc.)
- `memcord_compress` - Storage optimization
- `memcord_archive` - Long-term archival
- `memcord_export` - Export as resources
- `memcord_share` - Generate shareable files
- Plus monitoring and diagnostics tools

---

## Enterprise Setup

### Administrator Configuration

For organization or enterprise GitHub Copilot deployments:

**Step 1: Enable MCP Policy**

1. Go to GitHub organization settings
2. Navigate to: Copilot → Policies
3. Enable: "MCP servers in Copilot"
4. Set allowed MCP servers (optional: whitelist memcord)

**Step 2: Deploy Configuration**

Option A: Central configuration repository
```bash
# Add .vscode/mcp.json to team template repository
# Team members clone and use automatically
```

Option B: Custom Copilot agents
```json
{
  "agents": {
    "memcord-agent": {
      "mcpServers": {
        "memcord": {
          "command": "uv",
          "args": ["--directory", "/shared/path/memcord", "run", "memcord"],
          "env": {
            "PYTHONPATH": "/shared/path/memcord/src"
          }
        }
      }
    }
  }
}
```

### Security Considerations

**Trust and Safety:**
- MCP servers execute arbitrary code on developer machines
- Only install memcord from official sources:
  - GitHub: https://github.com/ukkit/memcord
  - Official releases only
- Review server configuration before enabling

**Data Privacy:**
- Memcord stores all data locally (100% private)
- No cloud dependencies or external API calls
- Memory slots stored in configurable local directories
- Suitable for confidential enterprise data

**Access Control:**
- Control which teams can use memcord via MCP policy
- Use workspace configurations for project-specific access
- Audit tool usage via VSCode logs

**Network Isolation:**
- Memcord operates entirely offline
- No telemetry or external connections
- Safe for air-gapped environments

---

## Verification

### Verify Installation

**Step 1: Check MCP Server Status**

1. Open Command Palette: `Ctrl+Shift+P` / `Cmd+Shift+P`
2. Run: `MCP: List Servers`
3. Verify "memcord" appears in the list

**Step 2: Test Tool Availability**

In GitHub Copilot Chat:

```
@workspace List available memcord tools
```

Copilot should show memcord tools are available.

**Step 3: Run Verification Script**

From memcord directory:

```bash
python utilities/verify_vscode_setup.py
```

Expected output:
```
✓ VSCode version 1.102+ detected
✓ MCP configuration found (.vscode/mcp.json)
✓ Memcord server configured
✓ Python 3.10+ available
✓ uv package manager installed
✓ All dependencies satisfied
```

### Test Basic Functionality

**Create Test Memory:**

```
@workspace Use memcord to create a memory slot called "vscode-test"
```

**Save Content:**

```
@workspace Save "VSCode integration working!" to memcord
```

**Read Back:**

```
@workspace Read the vscode-test memory slot
```

---

## Troubleshooting

### Common Issues

#### 1. Memcord Not Appearing in MCP Servers

**Symptoms:**
- `MCP: List Servers` doesn't show memcord
- Copilot says memcord tools are unavailable

**Solutions:**

A. Check configuration file location:
```bash
# Should exist in one of these locations:
ls .vscode/mcp.json
ls .mcp.json
ls ~/Library/Application\ Support/Code/User/mcp.json  # macOS
ls %APPDATA%\Code\User\mcp.json  # Windows
```

B. Validate JSON syntax:
```bash
# Use a JSON validator
python -m json.tool .vscode/mcp.json
```

C. Reload VSCode:
- Command Palette → `Developer: Reload Window`

---

#### 2. MCP Server Fails to Start

**Symptoms:**
- Error message: "Failed to start MCP server 'memcord'"
- Server appears but shows error state

**Solutions:**

A. Check Python version:
```bash
python --version  # Should be 3.10+
```

B. Verify uv installation:
```bash
uv --version
```

C. Test manual startup:
```bash
cd /path/to/memcord
uv run memcord
```

D. Check PYTHONPATH:
```json
{
  "env": {
    "PYTHONPATH": "/absolute/path/to/memcord/src"  // Must be absolute
  }
}
```

---

#### 3. Tools Available But Not Working

**Symptoms:**
- Copilot sees memcord tools
- Tool calls fail or timeout

**Solutions:**

A. Check logs:
- Command Palette → `Developer: Show Logs`
- Select "MCP" from dropdown
- Look for memcord errors

B. Increase timeout (if needed):
```json
{
  "servers": {
    "memcord": {
      "timeout": 30000  // 30 seconds
    }
  }
}
```

C. Test direct tool call:
```bash
# From memcord directory
uv run python -c "from memcord.server import ChatMemoryServer; import asyncio; s = ChatMemoryServer(); print('OK')"
```

---

#### 4. Enterprise Policy Blocked

**Symptoms:**
- Error: "MCP servers are disabled by your organization"

**Solutions:**

A. Contact administrator to enable MCP policy

B. Request memcord to be whitelisted:
```json
{
  "mcpServers": {
    "allowList": ["memcord"]
  }
}
```

---

#### 5. Workspace Variable Not Resolving

**Symptoms:**
- Error: "${workspaceFolder} not found"

**Solutions:**

A. Use absolute paths instead:
```json
{
  "args": ["--directory", "/absolute/path/to/memcord", "run", "memcord"]
}
```

B. Ensure you've opened a folder (not just files):
- File → Open Folder

---

### Debug Mode

Enable detailed logging:

```json
{
  "servers": {
    "memcord": {
      "command": "uv",
      "args": ["--directory", "/path/to/memcord", "run", "memcord"],
      "env": {
        "PYTHONPATH": "/path/to/memcord/src",
        "MEMCORD_DEBUG": "true"
      }
    }
  }
}
```

Check logs:
- Command Palette → `Developer: Show Logs` → "MCP"

---

## Advanced Configuration

### Multiple Memcord Instances

Run separate instances for different projects:

```json
{
  "servers": {
    "memcord-project-a": {
      "command": "uv",
      "args": ["--directory", "/path/to/memcord", "run", "memcord"],
      "env": {
        "PYTHONPATH": "/path/to/memcord/src",
        "MEMCORD_MEMORY_DIR": "./project-a-memories"
      }
    },
    "memcord-project-b": {
      "command": "uv",
      "args": ["--directory", "/path/to/memcord", "run", "memcord"],
      "env": {
        "PYTHONPATH": "/path/to/memcord/src",
        "MEMCORD_MEMORY_DIR": "./project-b-memories"
      }
    }
  }
}
```

### Team Shared Memories

Configure shared memory directory:

```json
{
  "env": {
    "MEMCORD_SHARED_DIR": "/shared/network/path/team-memories"
  }
}
```

**Note:** Ensure proper file permissions for all team members.

### Custom Storage Locations

Separate storage by project:

```json
{
  "env": {
    "MEMCORD_MEMORY_DIR": "${workspaceFolder}/.memcord/slots",
    "MEMCORD_SHARED_DIR": "${workspaceFolder}/.memcord/shared"
  }
}
```

Add to `.gitignore`:
```gitignore
.memcord/
```

---

## Next Steps

- **[Usage Examples](vscode-copilot-workflows.md)** - Real-world workflows with GitHub Copilot
- **[Tools Reference](tools-reference.md)** - Complete documentation of all 19 tools
- **[Security Guide](security-vscode.md)** - Security best practices for VSCode integration
- **[Troubleshooting Guide](troubleshooting.md)** - General troubleshooting

---

## Support

- **Issues**: https://github.com/ukkit/memcord/issues
- **Documentation**: https://github.com/ukkit/memcord/docs
- **Discussions**: https://github.com/ukkit/memcord/discussions

---

**Last Updated:** January 2026
**Memcord Version:** 2.3.5
**VSCode Compatibility:** 1.102+
