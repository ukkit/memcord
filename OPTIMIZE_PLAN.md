# Server.py Optimization Plan

## Goal
Refactor `server.py` (2,736 lines, 26 handlers) to ~1,400 lines while improving:
- **Manageability**: Extract business logic to service modules
- **Performance**: Dictionary-based dispatch instead of 43 if/elif branches
- **Safety**: Consistent error handling using existing `MemcordError` system

## Summary of Changes

| Change | Impact | Lines Saved | Status |
|--------|--------|-------------|--------|
| Handler registry with dict dispatch | Eliminate routing duplication | ~150 | ✅ COMPLETE |
| Extract 5 service modules | Move business logic out | ~800 | ⚡ Infrastructure Ready |
| Standardize error handling | Use MemcordError consistently | ~100 | ⚡ Infrastructure Ready |
| Co-locate tool schemas with handlers | Reduce tool definition boilerplate | ~200 | Pending |
| **Total** | | **~1,250** | |

---

## Implementation Progress (2026-01-22)

### Completed
- **Phase 1**: Handler registry with O(1) dispatch - COMPLETE
- **Phase 2**: Service modules created (infrastructure only)
- **Phase 3**: ResponseBuilder and error decorators created (infrastructure only)

### Current Metrics
| Metric | Value |
|--------|-------|
| `server.py` | 2,684 lines |
| New modules created | ~1,816 lines |
| Tests passing | 429/429 |

### Files Created
| File | Lines | Purpose |
|------|-------|---------|
| `handler_registry.py` | 135 | O(1) handler dispatch |
| `response_builder.py` | 190 | Response formatting, error decorators |
| `services/__init__.py` | 58 | Service exports |
| `services/merge_service.py` | 307 | Merge business logic |
| `services/compression_service.py` | 299 | Compression business logic |
| `services/archive_service.py` | 296 | Archive business logic |
| `services/import_service.py` | 159 | Import business logic |
| `services/monitoring_service.py` | 405 | Monitoring business logic |

### Remaining Work
To achieve the full ~1,300 line reduction:
1. Update handlers to delegate to service modules (~800 lines saved)
2. Apply `@handle_errors` decorator to handlers
3. Move tool schemas into handler decorators (~200 lines saved)

---

## Phase 1: Handler Registry (Low Risk) ✅ COMPLETE

### Created `src/memcord/handler_registry.py` (135 lines)
- `HandlerInfo` dataclass with name, handler, category, description, input_schema, requires_advanced
- `HandlerRegistry` class with register decorator, dispatch, get_tools, get_by_category methods

### Updated `server.py`
- Added `_build_handler_map()` - maps all 26 tools to (handler, requires_advanced) tuples
- Added `_dispatch_handler()` - centralized O(1) dispatch with advanced tool checking
- Replaced ~90 line if/elif chain in `call_tool_direct()` with single dispatch call
- Replaced ~40 line if/elif chain in `call_tool()` with single dispatch call

### Verification
- All 429 tests passing

---

## Phase 2: Extract Service Modules (Medium Risk) ⚡ INFRASTRUCTURE READY

### Created `src/memcord/services/` directory with:

**2.1 `merge_service.py`** (307 lines) ✅
- `MergeService` class with `preview_merge()`, `execute_merge()`, `validate_merge_request()`, `load_source_slots()`
- `MergePreviewResult`, `MergeExecuteResult` dataclasses

**2.2 `import_service.py`** (159 lines) ✅
- `ImportService` class with `import_content()`
- `ImportResult` dataclass

**2.3 `compression_service.py`** (299 lines) ✅
- `CompressionService` class with `get_stats()`, `analyze()`, `compress_slot()`, `compress_all_slots()`, `decompress_slot()`
- `CompressionStats`, `CompressionResult`, `BulkCompressionResult`, `DecompressionResult`, `CompressionAnalysis` dataclasses

**2.4 `archive_service.py`** (296 lines) ✅
- `ArchiveService` class with `archive_slot()`, `restore_slot()`, `list_archives()`, `get_stats()`, `find_candidates()`
- `ArchiveResult`, `RestoreResult`, `ArchiveInfo`, `ArchiveListResult`, `ArchiveStats`, `ArchiveCandidate`, `ArchiveCandidatesResult` dataclasses

**2.5 `monitoring_service.py`** (405 lines) ✅
- `MonitoringService` class with `get_status()`, `get_metrics()`, `get_logs()`, `run_diagnostics()`
- `StatusReport`, `MetricsReport`, `LogsReport`, `DiagnosticsReport`, `HealthCheck`, `MetricSummary`, `LogEntry`, `PerformanceIssue` dataclasses

### Next Step: Handler Integration
Update handlers to delegate to services. Example pattern:
```python
async def _handle_mergemem(self, arguments):
    action = arguments.get("action", "preview")
    if action == "preview":
        result = await self.merge_service.preview_merge(...)
        return self._format_merge_preview(result)
    else:
        result = await self.merge_service.execute_merge(...)
        return self._format_merge_result(result)
```

---

## Phase 3: Standardize Error Handling (Medium Risk) ⚡ INFRASTRUCTURE READY

### Created `src/memcord/response_builder.py` (190 lines) ✅

**ResponseBuilder class:**
- `success(message)` - Create success response
- `error(error: MemcordError)` - Create error response from MemcordError
- `error_message(message)` - Create simple error response
- `from_lines(lines)` - Create response from list of lines

**Decorators:**
- `@handle_errors(error_handler, default_error_message)` - Standardized exception handling
- `@validate_required_args(*args)` - Validate required arguments
- `@validate_slot_selected(slot_arg, error_message)` - Validate slot is selected

### Next Step: Apply to Handlers
```python
@handle_errors()
@validate_slot_selected()
async def _handle_savemem(self, arguments):
    # Handler code - exceptions automatically converted to proper responses
    ...
```

---

## Phase 4: Tool Schema Co-location (Low Risk) - PENDING

Move tool schemas from `_get_basic_tools()` / `_get_advanced_tools()` into handler decorators:

```python
@HandlerRegistry.register(
    "memcord_save",
    category="basic",
    description="Save chat text to memory slot",
    input_schema={
        "type": "object",
        "properties": {
            "chat_text": {"type": "string"},
            "slot_name": {"type": "string"},
        },
        "required": ["chat_text"],
    }
)
async def _handle_savemem(self, arguments):
    ...
```

Update `list_tools()` to generate Tool objects from registry using `handler_registry.get_tools()`.

---

## Files Created/Modified

| File | Lines | Status |
|------|-------|--------|
| `src/memcord/server.py` | 2,684 | ✅ Dispatch updated |
| `src/memcord/handler_registry.py` | 135 | ✅ Created |
| `src/memcord/response_builder.py` | 190 | ✅ Created |
| `src/memcord/services/__init__.py` | 58 | ✅ Created |
| `src/memcord/services/merge_service.py` | 307 | ✅ Created |
| `src/memcord/services/import_service.py` | 159 | ✅ Created |
| `src/memcord/services/compression_service.py` | 299 | ✅ Created |
| `src/memcord/services/archive_service.py` | 296 | ✅ Created |
| `src/memcord/services/monitoring_service.py` | 405 | ✅ Created |

---

## Verification

### After Each Phase
1. Run existing test suite: `pytest tests/`
2. Verify all 26 tools still work via MCP

### End-to-End Testing
```bash
# Run full test suite
pytest tests/ -v

# Test specific handler functionality
pytest tests/test_server_mcp_interface.py -v

# Test service modules
pytest tests/test_merge_service.py tests/test_import_service.py -v
```

### Manual MCP Verification
1. Start server: `uv run memcord`
2. Test basic tools: `memcord_name`, `memcord_save`, `memcord_read`
3. Test advanced tools: `memcord_merge`, `memcord_import`
4. Verify error handling returns proper messages

---

## Rollback Strategy

Each phase is independent and revertible:
- **Phase 1**: Registry can coexist with if/elif during migration
- **Phase 2**: Services added one at a time; handlers can call service OR inline code
- **Phase 3**: Error decorator is optional per handler
- **Phase 4**: Tool definitions can stay in-place if needed

---

## Order of Implementation

1. **Phase 1** first - establishes foundation, lowest risk
2. **Phase 2** largest handlers first (merge_service, then compression, archive, import, monitoring)
3. **Phase 3** after services are stable
4. **Phase 4** final cleanup
