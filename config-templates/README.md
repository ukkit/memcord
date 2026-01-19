# Memcord MCP Configuration Templates

This directory contains MCP (Model Context Protocol) configuration templates for various IDEs and platforms.

## Quick Setup

### Automatic Configuration (Recommended)

Run the configuration generator script:

```bash
# Unix/macOS/Linux
uv run python scripts/generate-config.py

# Windows PowerShell
uv run python scripts/generate-config.py --platform windows

# Preview changes without writing files
uv run python scripts/generate-config.py --dry-run
```

### Manual Configuration

If you prefer manual setup, copy the appropriate template and replace `{{MEMCORD_PATH}}` with your actual installation path.

## Directory Structure

```
config-templates/
├── claude-desktop/          # Claude Desktop App
│   ├── config.json          # Unix/macOS/Linux template
│   └── config.windows.json  # Windows template (uses cmd /c wrapper)
├── claude-code/             # Claude Code CLI
│   ├── mcp.json             # Unix/macOS/Linux template
│   └── mcp.windows.json     # Windows template
├── vscode/                  # VSCode/GitHub Copilot
│   └── mcp.json             # Uses ${workspaceFolder} variable
└── antigravity/             # Google Antigravity IDE
    └── mcp_config.json      # Requires absolute paths
```

## Platform-Specific Instructions

### Claude Desktop

**macOS/Linux:**
1. Copy `claude-desktop/config.json` to:
   - macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
   - Linux: `~/.config/Claude/claude_desktop_config.json`
2. Replace `{{MEMCORD_PATH}}` with your memcord installation path

**Windows:**
1. Copy `claude-desktop/config.windows.json` to:
   - `%APPDATA%\Claude\claude_desktop_config.json`
2. Replace `{{MEMCORD_PATH}}` with your memcord path (use `\\` for path separators)

### Claude Code CLI

Claude Code looks for `.mcp.json` in:
1. Current project directory (project-scoped)
2. User home directory (user-scoped)

**Setup:**
```bash
# Project-scoped (recommended)
cp config-templates/claude-code/mcp.json .mcp.json

# Verify
claude mcp list
```

**Windows:**
Use `config-templates/claude-code/mcp.windows.json` instead.

### VSCode / GitHub Copilot

1. Copy `config-templates/vscode/mcp.json` to `.vscode/mcp.json`
2. No path replacement needed - uses `${workspaceFolder}` variable
3. Requires VSCode 1.102+ and GitHub Copilot extension

### Google Antigravity IDE

1. Copy `config-templates/antigravity/mcp_config.json` to `.antigravity/mcp_config.json`
2. Replace `{{MEMCORD_PATH}}` with **absolute path** (relative paths not supported)
3. Use Unix-style paths even on Windows when running in cloud

## Configuration Options

### Basic vs Advanced Mode

Each template includes two server configurations:

| Server | Tools | Use Case |
|--------|-------|----------|
| `memcord` | 11 core tools | Standard usage |
| `memcord-advanced` | 19+ tools | Power users |

Set via environment variable:
```json
"env": {
  "MEMCORD_ENABLE_ADVANCED": "true"
}
```

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `MEMCORD_ENABLE_ADVANCED` | `false` | Enable advanced tools |
| `MEMCORD_LOG_LEVEL` | `WARNING` | Logging level (DEBUG, INFO, WARNING, ERROR) |
| `PYTHONPATH` | - | Should point to `{memcord}/src` |

## Windows-Specific Notes

Windows requires wrapping the `uv` command with `cmd /c` for proper process spawning:

```json
{
  "command": "cmd",
  "args": ["/c", "uv", "--directory", "C:\\path\\to\\memcord", "run", "memcord"]
}
```

**Path separators:**
- Use `\\` (double backslash) in JSON strings
- Example: `"C:\\Users\\name\\memcord\\src"`

## Troubleshooting

### Server not appearing in client

1. Verify the path is correct and absolute
2. Check that `uv` is installed and in PATH
3. Restart the client application
4. Check logs: `MEMCORD_LOG_LEVEL=DEBUG uv run memcord 2>debug.log`

### JSON-RPC errors

If you see JSON parsing errors, check:
1. No print statements are writing to stdout
2. Logging is configured to use stderr
3. Run: `uv run memcord 2>&1 | head -5` to see initial output

### Windows-specific issues

1. Ensure `cmd /c` wrapper is used
2. Use double backslashes in paths
3. Try running in PowerShell as Administrator

## Verification

After configuration, verify the connection:

```bash
# Claude Code
claude mcp list

# Should show:
# memcord (stdio) - connected
```

## Need Help?

- [Installation Guide](../docs/installation.md)
- [Enterprise Setup](../docs/enterprise-setup.md)
- [GitHub Issues](https://github.com/ukkit/memcord/issues)
