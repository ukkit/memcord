# Version History

## v2.4.2 - Project Detection & Code Quality Fixes

```text
  - Fixed .memcord detection to use MCP client roots instead of server cwd
  - Proper file URI parsing with percent-decoding (spaces, special chars in paths)
  - Cross-platform URI-to-path conversion using urllib.parse (Windows & POSIX)
  - Slot name validation on .memcord files (rejects path traversal, injection chars)
  - Multiline .memcord files now read only the first line
  - Space-to-underscore normalization consistent across all detection paths
  - Removed debug logging left in _handle_memname handler
  - Replaced asyncio.iscoroutine with inspect.iscoroutinefunction for robust async detection
  - Added 25 new tests for URI parsing, roots detection, and edge cases
```

## v2.4.1 - Summarizer Enhancement & CI Improvements

```text
  - Enhanced TextSummarizer with better scoring, MMR selection, and chat-aware summarization
  - Added memcord_close tool to deactivate memory slots and end sessions
  - Fixed memcord_use to auto-detect slot name from .memcord binding file
  - Fixed slot state issues with separate read/write resolution
  - Moved release exclusion patterns to .releaseexclude for easier maintenance
  - Added CLAUDE.md project development guide
  - Added GitHub Actions CI workflows (manual trigger, matrix testing across Python 3.10-3.12 and 3 OSes)
  - CI runs disabled by default to reduce costs (workflow_dispatch only)
```

## v2.4.0 - Project Memory Binding & Auto-Detection

```text
  - New memcord_init tool: Initialize project directories with memory slots via .memcord file
  - New memcord_unbind tool: Remove project bindings (preserves memory data)
  - Auto-detection: Slash commands automatically use bound slot from .memcord file
  - Zero-config workflow: Once bound, no need to specify slot names
  - Updated tool count: 21 tools (13 basic + 8 advanced)
  - Enhanced documentation for project binding workflows
```

## v2.3.7 - Cross-Platform Support

```text
  - Windows PowerShell installer (install.ps1) for one-line installation
  - Centralized config-templates/ folder with platform-specific configs
  - Cross-platform config generator (scripts/generate-config.py)
  - Windows cmd /c wrapper support for proper process spawning
  - Updated MCP SDK version constraint to v1.22-2.0 for stability
  - Logging configuration to prevent stdout corruption in STDIO mode
```

## v2.3.6 - Google Antigravity IDE Support

```text
  - Added Google Antigravity IDE configuration template
  - Full compatibility with Antigravity's MCP server integration
```

## v2.3.5 - Enhanced VSCode and GitHub Copilot Integration

```text
  - Added comprehensive VSCode configuration templates (.vscode/mcp.json.example)
  - Implemented 16 reusable prompt templates for GitHub Copilot workflows
  - Created automated verification script for VSCode setup validation
  - Added MCP registry metadata (package.json) for marketplace discovery
  - Full integration test suite for VSCode/Copilot compatibility
  - Complete documentation for enterprise deployment, security, and workflows
```

## v2.3.4 - Updated MCP SDK & MCP Protocol to latest

```text
  - MCP SDK: 1.22.0 (released November 20, 2025)
  - MCP Protocol: 2025-11-25 (released November 25, 2025)
```

## v2.3.3 - Optimizations to improve speed, reduce startup time, and improve code maintainability

```text
  - Tool definition caching to eliminate redundant list_tools() calls
  - Lazy loading for heavy dependencies (TextSummarizer, SimpleQueryProcessor, ContentImporter, MemorySlotMerger) via u/property decorators for faster startup
  - Error message constants to eliminate 30+ duplicate string literals and improve maintainability
  - LRU cache (@functools.lru_cache) to _get_mime_type() for faster repeated lookups
```

## v2.3.0 - Enhanced Security

```text
  - Built-in protection that checks inputs, limits misuse, strengthens defenses, and handles errors safely
  - High Speed: Uses 42% fewer tokens, loads slots 20x faster, and makes searches 7x quicker thanks to smart caching that hits 80% of the time—keeping response times under a millisecond.
  - Better Documentation: Clearer documentation, intelligent default settings that adapt to your preferences.
```

### v2.2.0 - What's new

```text
  - Timeline Navigation - memcord_select_entry
  - Simplified Slot Activation - memcord_use
  - Memory Integration Promoted - memcord_merge
```
