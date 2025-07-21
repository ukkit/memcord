# Claude Code Integration Guide

This guide covers using MemCord with Claude Code CLI for modern development workflows, team collaboration, and project-specific memory management.

## Overview

MemCord integrates seamlessly with Claude Code CLI through a project-level `.mcp.json` configuration file. This enables:

- **Project-specific setup** - Memory configuration tied to your codebase
- **Team collaboration** - Shared configuration via version control
- **Zero-config experience** - One command installation and setup
- **Development workflows** - Custom commands for common operations

## Quick Start

### 1. Install MemCord with Claude Code

```bash
# Clone the repository
git clone https://github.com/ukkit/memcord.git
cd memcord

# Install dependencies
uv sync --dev

# Install MCP server (uses included .mcp.json)
claude mcp install .

# Verify installation
claude mcp list
claude mcp test memcord
```

### 2. Verify Your Setup

```bash
# Check that memcord is listed
claude mcp list

# Get detailed information
claude mcp get memcord

# Test server startup
claude mcp test memcord
```

You should see all 17 tools available (8 basic + 9 advanced).

## Project Configuration

### The .mcp.json File

MemCord includes a comprehensive `.mcp.json` configuration:

```json
{
  "name": "memcord",
  "version": "1.1.0",
  "description": "MCP server for chat memory management with summarization and file sharing",
  "server": {
    "command": "uv",
    "args": ["--directory", ".", "run", "memcord"],
    "env": {
      "PYTHONPATH": "./src",
      "MEMCORD_ENABLE_ADVANCED": "true"
    }
  }
}
```

Key features:
- **Relative paths** - Works from any project location
- **Advanced tools enabled** - All 17 tools available by default
- **Team sharing** - Configuration tracked in version control
- **Environment isolation** - Uses project's virtual environment

### Configuration Options

You can customize the configuration after installation:

```bash
# Disable advanced tools (use only 8 basic tools)
claude mcp configure memcord -e MEMCORD_ENABLE_ADVANCED=false

# Re-enable advanced tools
claude mcp configure memcord -e MEMCORD_ENABLE_ADVANCED=true

# Add custom memory directory
claude mcp configure memcord -e MEMCORD_MEMORY_DIR=/custom/path

# View current configuration
claude mcp get memcord
```

## Team Collaboration

### Sharing Configuration

Since `.mcp.json` is included in the repository, your entire team gets consistent MemCord setup:

```bash
# Team member workflow
git clone your-project-with-memcord
cd your-project
claude mcp install .  # Uses the shared .mcp.json
```

### Project-Specific Memory

Each project can have its own memory configuration:

```bash
# Different projects, different memory locations
cd /project-a
claude mcp install .  # MemCord for project A

cd /project-b  
claude mcp install .  # Separate MemCord for project B
```

### Memory Organization Strategies

**By Project Type:**
```bash
# Development project
memcord_name "dev_discussions"
memcord_tag add "development" "api" "architecture"

# Research project  
memcord_name "research_notes"
memcord_tag add "research" "papers" "analysis"
```

**By Team Role:**
```bash
# Frontend team memories
memcord_group create "frontend"
memcord_name "frontend/ui_decisions"

# Backend team memories
memcord_group create "backend"
memcord_name "backend/api_design"
```

## Custom Commands

Create project-specific slash commands for common memory operations.

### Setup Commands Directory

```bash
# Project-specific commands (recommended for teams)
mkdir -p .claude/commands

# User-wide commands (personal use)
mkdir -p ~/.claude/commands
```

### Essential Memory Commands

Create these files in your `.claude/commands/` directory:

**`.claude/commands/memory-save.md`**
```markdown
---
description: Save current conversation to memory
---

Save the current conversation to memory slot: $ARGUMENTS

First use memcord_name to set the memory slot, then use memcord_save_progress to save our conversation with auto-summarization.
```

**`.claude/commands/memory-search.md`**
```markdown
---
description: Search across all project memories
---

Search for: $ARGUMENTS

Use memcord_search to find information across all memory slots in this project.
```

**`.claude/commands/memory-ask.md`**
```markdown
---
description: Ask questions about project memories
---

Answer this question about project memories: $ARGUMENTS

Use memcord_query to process this natural language question across all project memory slots.
```

**`.claude/commands/memory-import.md`**
```markdown
---
description: Import project documentation into memory
---

Import documentation: $ARGUMENTS

Use memcord_import to bring in README files, API docs, or other project documentation.
```

**`.claude/commands/memory-organize.md`**
```markdown
---
description: Organize memories with tags and groups
---

Organize current memory with: $ARGUMENTS

Use memcord_tag and memcord_group tools to organize the current memory slot.
```

### Advanced Team Commands

**`.claude/commands/memory-sync.md`**
```markdown
---
description: Share memory snapshot with team
---

Create shareable memory export: $ARGUMENTS

Use memcord_export to create shareable memory files for team collaboration.
```

**`.claude/commands/memory-review.md`**
```markdown
---
description: Review recent project decisions
---

Review recent decisions about: $ARGUMENTS

Use memcord_query to find and summarize recent decisions and discussions.
```

### Command Usage

After creating commands, use them in Claude Code:

```bash
# Save current discussion about API changes
/memory-save api_changes

# Search for previous discussions
/memory-search "authentication implementation"

# Ask about project decisions
/memory-ask "What consensus did we reach on the database schema?"

# Import project documentation
/memory-import README.md

# Organize current memory
/memory-organize "add tags: database, schema, decisions"
```

## Development Workflows

### Code Review Memory

```bash
# Before code review
memcord_name "code_review_$(date +%Y%m%d)"
memcord_save "Starting code review for PR #123: Authentication refactor"

# During review - save important findings
memcord_save_progress  # Auto-saves discussion

# After review
memcord_tag add "code-review" "authentication" "security"
```

### Architecture Decision Records

```bash
# Create ADR memory slot
memcord_name "adr_microservices_migration"
memcord_import "docs/adr/001-microservices.md"
memcord_tag add "adr" "architecture" "microservices"

# Reference in future discussions
memcord_query "What were the main concerns about microservices migration?"
```

### Research and Learning

```bash
# Technical research session
memcord_name "research_$(date +%Y%m%d)"
memcord_import "https://example.com/technical-article"
memcord_save "Key insights from today's research session..."

# Organize research
memcord_group create "research"
memcord_group move research_20241203 "research/"
```

### Bug Investigation

```bash
# Start bug investigation
memcord_name "bug_auth_timeout"
memcord_save "Bug report: Authentication timeouts in production..."

# Track investigation progress
memcord_save_progress  # Saves current findings

# When resolved
memcord_tag add "bug" "resolved" "authentication"
memcord_save "Resolution: Updated timeout configuration to 30s"
```

## Advanced Features

### Memory Compression

```bash
# Analyze memory usage
claude mcp call memcord memcord_compress '{"action": "analyze", "slot_name": "large_discussion"}'

# Compress old memories
claude mcp call memcord memcord_compress '{"action": "compress", "slot_name": "old_project"}'
```

### Archive Management

```bash
# Archive completed project memories
claude mcp call memcord memcord_archive '{"action": "archive", "slot_name": "completed_project"}'

# List archived memories
claude mcp call memcord memcord_archive '{"action": "list"}'
```

### Bulk Operations

```bash
# Export all project memories
claude mcp call memcord memcord_export '{"format": "json", "include_metadata": true}'

# Import team's shared memories
claude mcp call memcord memcord_import '{"source": "team_memories.json", "merge_strategy": "append"}'
```

## Troubleshooting

### Common Issues

**MemCord not starting:**
```bash
# Check server status
claude mcp test memcord

# View logs
claude mcp logs memcord

# Restart server
claude mcp restart memcord
```

**Tools not available:**
```bash
# Verify advanced tools are enabled
claude mcp get memcord | grep MEMCORD_ENABLE_ADVANCED

# Enable advanced tools
claude mcp configure memcord -e MEMCORD_ENABLE_ADVANCED=true
```

**Memory not saving:**
```bash
# Check if in zero mode
claude mcp call memcord memcord_list '{}'

# Exit zero mode
claude mcp call memcord memcord_name '{"slot_name": "normal_memory"}'
```

### Performance Optimization

**Large memory slots:**
```bash
# Compress large memories
claude mcp call memcord memcord_compress '{"action": "compress", "slot_name": "large_slot"}'

# Archive old memories
claude mcp call memcord memcord_archive '{"action": "archive", "slot_name": "old_slot"}'
```

**Search performance:**
```bash
# Use specific tags for faster search
memcord_search "query" --tags "specific-tag"

# Use Boolean operators for precise search
memcord_search "term1 AND term2 NOT term3"
```

## Best Practices

### Memory Organization

1. **Use descriptive slot names**: `project_kickoff_2024` instead of `meeting1`
2. **Tag consistently**: Establish team tagging conventions
3. **Group by purpose**: Separate technical discussions from project management
4. **Archive regularly**: Keep active memories focused and fast

### Team Collaboration

1. **Share .mcp.json**: Include in version control for consistent setup
2. **Document conventions**: Create team guidelines for memory organization
3. **Export important decisions**: Use `memcord_export` for critical information
4. **Regular cleanup**: Archive completed project memories

### Security and Privacy

1. **Use zero mode**: For sensitive discussions that shouldn't be saved
2. **Local storage**: All data remains on your local machine
3. **Selective sharing**: Only export specific memories when needed
4. **Access control**: Standard file system permissions apply

## Integration Examples

### CI/CD Integration

```yaml
# .github/workflows/memcord-validation.yml
name: Validate MemCord Configuration
on: [push, pull_request]

jobs:
  validate-memcord:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Setup uv
        uses: astral-sh/setup-uv@v1
      - name: Install dependencies
        run: uv sync --dev
      - name: Test MemCord startup
        run: timeout 10s uv run memcord || [ $? -eq 124 ]
```

### Project Templates

```bash
# Create project template with MemCord
mkdir new-project-template
cd new-project-template

# Copy MemCord configuration
cp /path/to/memcord/.mcp.json .
cp -r /path/to/memcord/.claude .

# Customize for template
sed -i 's/memcord/project-memory/g' .mcp.json
```

### IDE Integration

Many IDEs can run Claude Code commands directly:

```json
// VS Code tasks.json
{
  "version": "2.0.0",
  "tasks": [
    {
      "label": "Save to Memory",
      "type": "shell",
      "command": "claude",
      "args": ["chat", "/memory-save", "${input:memorySlot}"],
      "group": "test"
    }
  ]
}
```

## Next Steps

- **Explore Advanced Tools**: Try `memcord_import`, `memcord_merge`, and `memcord_compress`
- **Create Custom Commands**: Build project-specific workflows
- **Setup Team Guidelines**: Establish memory organization conventions
- **Integrate with CI/CD**: Add MemCord validation to your build process

For more information, see:
- [Installation Guide](installation.md) - Complete setup instructions
- [Tools Reference](tools-reference.md) - Detailed documentation for all 17 tools
- [Usage Examples](examples.md) - Real-world workflows and use cases