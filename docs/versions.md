# Version History

## v3.4.0 - MCP Protocol Compliance (spec 2025-03-26 / 2025-11-25)

```text
  - SDK bump: mcp>=1.27.0 for spec 2025-11-25 compliance
  - Tool annotations on all 28 tools: readOnlyHint, destructiveHint, idempotentHint,
    and openWorldHint — enables MCP clients to make smarter tool-use decisions
  - Centralized _TOOL_ANNOTATIONS map + _annotate_tools() post-processor using
    model_dump round-trip — zero per-tool boilerplate, forward-safe for SDK updates
  - Anthropic extension anthropic/maxResultSizeChars: 500K on memcord_read and
    memcord_query — raises Anthropic Claude's per-tool result truncation cap from 25K
  - Resource metadata enrichment: description (slot name + entry count + char count)
    and size fields on every Resource object in list_resources
  - ResourceTemplate registration for memory://{slot_name}.{md,txt,json} — enables
    slot-name argument autocompletion in supporting clients
  - Completions handler (_handle_completion): returns live slot-name suggestions
    filtered by prefix when clients send completion/complete requests
  - Progress notifications with message field: _emit_progress() helper emits
    ProgressNotification with human-readable status in _handle_saveprogress,
    _handle_importmem, and _handle_mergemem — requires client to provide progressToken
  - 23 new tests in tests/test_mcp_protocol_compliance.py covering all new features
  - All 1064 tests pass
```

## v3.3.0 - Zero Memory Leaks and Minimum Memory Footprint

```text
  - Bounded OperationQueue: completed/failed/cancelled ops evicted automatically
    when count exceeds 200; no unbounded accumulation on long-running servers
  - Tracked asyncio tasks: fire-and-forget create_task() calls in ProgressTracker
    and ProgressAwareMixin now store references in a set with add_done_callback
    cleanup — prevents silent GC destruction of in-flight callbacks
  - O(1) LRU cache eviction: interned_strings, json_parse_cache, json_serialize_cache
    switched from plain dict (full list copy on trim) to OrderedDict with
    popitem(last=False) / move_to_end() — no more O(n) memory spikes at capacity
  - Bounded access history: UsagePatternAnalyzer._access_history changed from list
    with slice copy to deque(maxlen=history_size); per-key access_times capped at
    deque(maxlen=1000) — zero-copy auto-eviction
  - RateLimiter memory pruning: empty client/operation entries deleted after request
    expiry — bounds growth from servers with many unique clients
  - Undo stack as deque: _undo_stack changed from list with O(n) pop(0) to
    deque(maxlen=50) — O(1) eviction, serialization uses list()
  - URL session cleanup: requests.Session() in WebURLHandler now uses context manager
    — connection pools always released, including on exception paths
  - change_log hard cap: IncrementalSearchIndex caps change_log at 5000 entries
    (trimmed to 1000) on every write, not just during 5-minute maintenance cycles
  - All 1041 tests pass
```

## v3.2.0 - Fix Event Loop Blocking in Async Summarizers

```text
  - SemanticSummarizer and TransformersSummarizer offload model loading and
    inference to asyncio.to_thread — event loop stays responsive during heavy
    CPU/IO work; MCP requests no longer queue behind model downloads
  - Merge now preserves individual slot entries instead of flattening to a
    single blob, retaining per-entry timestamps and metadata
  - Ruff formatting applied across codebase
  - Release-sync workflow extended with X/Twitter announcement step
```

## v3.1.0 - Write Operations Honor .memcord Binding

```text
  - Write operations now honor .memcord binding as a fallback slot source
  - _resolve_slot_for_write() follows the same priority as reads:
    explicit argument → active slot → .memcord binding in cwd
  - When the bound slot exists, it is auto-activated for the session so
    subsequent calls skip re-detection (no memcord_use required after restart)
  - Affected tools: memcord_save, memcord_save_progress, memcord_configure
  - Updated docs: README.md, tools-reference.md, troubleshooting.md,
    claude-code-guide.md to reflect unified slot resolution behavior
```

## v3.0.2 - Remove Unsupported SessionEnd Hook

```text
  - Dropped SessionEnd from hooks.json template — Claude Code does not support type:agent
    for stop/session-end hooks ("Agent stop hooks are not yet supported outside REPL")
  - merge_hooks() now runs a cleanup pass: re-running --install-hooks removes stale memcord
    hooks from events no longer in the template, fixing existing installs automatically
  - Fixed test_hooks_template_entries_have_required_fields to walk the nested hooks format
  - Added test covering stale hook removal behaviour
  - Updated docs: installation.md and config-templates/README.md
  - Existing users: run `uv run python scripts/generate-config.py --install-hooks` to remove
    the stale SessionEnd hook from .claude/settings.json
```

## v3.0.1 - Claude Code Hooks Format Compatibility

```text
  - Updated hooks template to new Claude Code hooks schema (hooks array nested inside each entry)
  - merge_hooks() now detects and deduplicates memcord entries in both old and new format
    — re-running --install-hooks on existing installs migrates cleanly without duplicates
  - Updated UserPromptSubmit warm-up example in docs/claude-code-guide.md to new format
  - Existing users: run `uv run python scripts/generate-config.py --install-hooks` to migrate
```

## v3.0.0 - Pluggable Summarizer Backends & Per-Slot Config

```text
  - New default summarizer for fresh slots: sumy (graph-based LexRank, zero model downloads)
  - Existing slots auto-assigned nltk config on first access — no behavior change for current users
  - Per-slot sidecar config: {slot_name}_config.json stores backend, algorithm, model, compression ratio
  - New memcord_configure MCP tool: get/set/reset per-slot summarizer config without restarting
  - MEMCORD_SUMMARIZER env var overrides per-slot config for deployment-level control (Docker, CI)
  - Optional semantic backend: sentence-transformers + MMR sentence selection (~80MB, install with [semantic])
  - Optional transformers backend: HuggingFace BART dialogue-trained abstractive summarizer (~400MB, install with [transformers])
  - Summarizer built per-call so config changes take effect immediately on the next save_progress
  - SummaryMetadata Pydantic model for typed LLM-enriched entry metadata
  - SlotConfig Pydantic model for validated per-slot configuration
  - add_summary_entry now stores which backend produced the summary in entry.metadata
  - sumy added to core dependencies; sentence-transformers and transformers remain optional extras
  - 59 new tests covering backends, factory, filesystem sidecar auto-creation, and configure tool
```

## v2.5.0 - Auto-Save Hooks for Claude Code

```text
  - Opt-in Claude Code agent hooks for automatic progress saving
  - PreCompact hook: saves conversation summary before context compaction
  - SessionEnd hook: saves summary and closes the active memory slot
  - New --install-hooks flag for generate-config.py (idempotent, safe to run multiple times)
  - Hooks template at config-templates/claude-code/hooks.json
  - merge_hooks() logic preserves existing hooks and deduplicates memcord entries
  - Added memcord_close to default permissions whitelist
  - Install scripts (install.sh, install.ps1) now mention hooks availability
  - Tests for hook merge logic and template validation
```

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

## v2.2.0 - What's New

```text
  - Timeline Navigation - memcord_select_entry
  - Simplified Slot Activation - memcord_use
  - Memory Integration Promoted - memcord_merge
```
