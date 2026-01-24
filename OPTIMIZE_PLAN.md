# Server.py Optimization Plan

## Goal
Refactor `server.py` (2,736 lines, 26 handlers) to ~1,850 lines while improving:
- **Manageability**: Extract business logic to service modules
- **Performance**: Dictionary-based dispatch, preloading, lazy-loading optimization
- **Safety**: Consistent error handling using existing `MemcordError` system
- **Startup Speed**: Strategic preloading for faster first tool invocation

## Summary of Changes

| Change | Impact | Lines Saved | Status |
|--------|--------|-------------|--------|
| Handler registry with dict dispatch | Eliminate routing duplication | ~150 | ✅ COMPLETE |
| Extract 5 service modules | Move business logic out | ~800 | ✅ COMPLETE |
| Standardize error handling | Use MemcordError consistently | ~100 | ✅ COMPLETE |
| Co-locate tool schemas with handlers | Single source of truth for schemas | ~36 | ✅ COMPLETE |
| **Phase 1-4 Total** | | **~443 actual** | ✅ COMPLETE |
| Extend @handle_errors to 20 handlers | Consistent error handling | +20 lines | ✅ COMPLETE |
| Extract large handler sub-actions | Simplify multi-action handlers | -103 | ✅ COMPLETE |
| Consolidate utility patterns | DRY timestamp/slot/response | minimal | ⚠️ SKIPPED - already clean |
| Preloading optimizations | Faster startup & first call | - | ✅ COMPLETE |
| **Phase 5-6 Total** | | **~350** | ⏳ PENDING |
| **Grand Total** | | **~793** | |

---

## Implementation Progress (2026-01-23)

### Completed ✅ Phases 1-4
- **Phase 1**: Handler registry with O(1) dispatch - COMPLETE
- **Phase 2**: Service modules created - COMPLETE
- **Phase 2 Integration**: ALL handlers now delegating to services ✅
- **Phase 3**: `@handle_errors` decorator applied to 6 handlers ✅
- **Phase 4**: Tool schema co-location - COMPLETE ✅

### Pending ⏳ Phases 5-6
- **Phase 5**: Extended handler refactoring - PENDING
- **Phase 6**: Preloading optimizations - PENDING

### Current Metrics
| Metric | Value | Change |
|--------|-------|--------|
| `server.py` | 2,246 lines | **-490 lines** from original 2,736 |
| New modules created | ~1,816 lines | |
| Tests passing | 616/616 | ✅ Re-verified 2026-01-24 |
| New optimization tests | 187 | ✅ Added 2026-01-24 |
| Registered handlers | 26 | 18 basic + 8 advanced |
| Schema locations | 1 | Reduced from 3 (single source of truth) |

### Test Verification (2026-01-24)
Full test suite re-verified with new optimization module tests:
- **Result**: 616/616 tests passing (429 original + 187 new)
- **Duration**: ~6.5 minutes (394.60s)
- **Error handling tests**: All passing (KeyError, ValidationError raised correctly)
- **Security validation**: Path traversal and SQL injection patterns properly blocked

### New Test Files Created (2026-01-24)
| Test File | Tests | Coverage |
|-----------|-------|----------|
| `test_handler_registry.py` | 18 | HandlerRegistry, HandlerInfo, global registry integration |
| `test_response_builder.py` | 25 | ResponseBuilder, @handle_errors, @validate_required_args, @validate_slot_selected |
| `test_merge_service.py` | 29 | MergeService validation, preview, execute, debug info |
| `test_import_service.py` | 24 | ImportService validation, file import, metadata handling |
| `test_compression_service.py` | 27 | CompressionService stats, analyze, compress, decompress |
| `test_archive_service.py` | 27 | ArchiveService archive, restore, list, stats, candidates |
| `test_monitoring_service.py` | 37 | MonitoringService status, metrics, logs, diagnostics |

### Handlers Integrated with Services ✅ ALL COMPLETE
| Handler | Service | Status |
|---------|---------|--------|
| `_handle_mergemem` | MergeService | ✅ |
| `_handle_status` | MonitoringService | ✅ |
| `_handle_metrics` | MonitoringService | ✅ |
| `_handle_logs` | MonitoringService | ✅ |
| `_handle_diagnostics` | MonitoringService | ✅ |
| `_handle_compressmem` | CompressionService | ✅ |
| `_handle_archivemem` | ArchiveService | ✅ |
| `_handle_importmem` | ImportService | ✅ |

### Service Properties Added to ChatMemoryServer
- `merge_service` - MergeService(storage, merger)
- `monitoring_service` - MonitoringService(status_monitor)
- `compression_service` - CompressionService(storage)
- `archive_service` - ArchiveService(storage)
- `import_service` - ImportService(storage, importer)

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

### Handlers with @handle_errors Decorator ✅ ALL 26 COMPLETE
All 26 handlers now have `@handle_errors` decorator for consistent error handling.

**Priority 1 (Large handlers - added 2026-01-24):**
| Handler | Default Error Message |
|---------|----------------------|
| `_handle_importmem` | "Import failed" |
| `_handle_mergemem` | "Merge operation failed" |
| `_handle_compressmem` | "Compression operation failed" |
| `_handle_archivemem` | "Archive operation failed" |
| `_handle_metrics` | "Metrics retrieval failed" |
| `_handle_diagnostics` | "Diagnostics failed" |

**Priority 2 (Medium handlers - added 2026-01-24):**
| Handler | Default Error Message |
|---------|----------------------|
| `_handle_memname` | "Naming operation failed" |
| `_handle_memuse` | "Use operation failed" |
| `_handle_savemem` | "Save failed" |
| `_handle_readmem` | "Read failed" |
| `_handle_saveprogress` | "Save progress failed" |
| `_handle_listmems` | "List operation failed" |
| `_handle_zeromem` | "Zero mode operation failed" |
| `_handle_exportmem` | "Export failed" |
| `_handle_sharemem` | "Share operation failed" |
| `_handle_status` | "Status check failed" |
| `_handle_logs` | "Log retrieval failed" |
| `_handle_bind` | "Bind operation failed" |

**Priority 3 (Small handlers - added 2026-01-24):**
| Handler | Default Error Message |
|---------|----------------------|
| `_handle_ping` | "Ping failed" |
| `_handle_unbind` | "Unbind failed" |

**Previously completed (Phase 3):**
| Handler | Default Error Message |
|---------|----------------------|
| `_handle_searchmem` | "Search failed" |
| `_handle_tagmem` | "Tag operation failed" |
| `_handle_listtags` | "Failed to list tags" |
| `_handle_groupmem` | "Group operation failed" |
| `_handle_querymem` | "Query failed" |
| `_handle_select_entry` | "Error selecting entry" |

### Remaining Work
Phases 1-4 complete. Phases 5-6 pending for additional optimization.

1. ~~Update compression handler to delegate to CompressionService~~ ✅
2. ~~Update archive handler to delegate to ArchiveService~~ ✅
3. ~~Update import handler to delegate to ImportService~~ ✅
4. ~~Apply `@handle_errors` decorator to 6 handlers~~ ✅
5. ~~Move tool schemas into handler decorators~~ ✅
6. ~~Apply `@handle_errors` to remaining 20 handlers~~ ✅ (2026-01-24)
7. ~~Extract large handler sub-actions~~ ✅ (2026-01-24) - SelectEntryService created
8. ~~Consolidate utility patterns~~ ⚠️ SKIPPED - analysis showed minimal impact
9. ~~Implement preloading optimizations~~ ✅ (2026-01-24) - Tool cache + TextSummarizer pre-loaded

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
- All 429 tests passing (re-verified 2026-01-23)

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

## Phase 4: Tool Schema Co-location (Low Risk) ✅ COMPLETE

### Changes Made (2026-01-23)

**1. Added import to server.py:**
```python
from .handler_registry import handler_registry
```

**2. Added decorators to all 26 handlers:**
```python
@handler_registry.register(
    "memcord_save",
    category="basic",
    description="Save chat text to memory slot (overwrites existing content)",
    input_schema={
        "type": "object",
        "properties": {
            "chat_text": {"type": "string", "description": "Chat text to save"},
            "slot_name": {"type": "string", "description": "Memory slot name (optional)"},
        },
        "required": ["chat_text"],
    },
)
async def _handle_savemem(self, arguments):
    ...
```

**3. Updated dispatch to use registry:**
```python
async def _dispatch_handler(self, name: str, arguments: dict[str, Any]):
    handler_info = handler_registry.dispatch(name)
    if handler_info is None:
        return [TextContent(type="text", text=f"Error: Unknown tool: {name}")]
    if handler_info.requires_advanced and not self.enable_advanced_tools:
        return [TextContent(type="text", text=f"Error: Advanced tool '{name}' is not enabled...")]
    return await handler_info.handler(self, arguments)
```

**4. Updated list_tools to use registry:**
```python
self._tool_cache = handler_registry.get_tools(include_advanced=self.enable_advanced_tools)
```

**5. Removed deprecated methods:**
- `_build_handler_map()` (~38 lines)
- `_get_basic_tools()` (~333 lines)
- `_get_advanced_tools()` (~181 lines)
- `self._handler_map` attribute

### Results
| Metric | Before | After |
|--------|--------|-------|
| server.py lines | 2,329 | 2,293 |
| Schema locations | 3 | 1 |
| Registered handlers | - | 26 |

### Key Benefit
Single source of truth - tool schemas are now co-located directly with their handler implementations, eliminating the scattered 3-location problem.

---

## Phase 5: Extended Handler Refactoring (Medium Risk) ⏳ PENDING

### 5.1 Apply @handle_errors to Remaining 20 Handlers ✅ COMPLETE (2026-01-24)

All 26 handlers now have the `@handle_errors` decorator:

**Priority 1 - Large handlers (>100 lines):**
| Handler | Lines | Range | Error Message |
|---------|-------|-------|---------------|
| `_handle_archivemem` | 154 | 1713-1867 | "Archive operation failed" |
| `_handle_compressmem` | 139 | 1574-1713 | "Compression operation failed" |
| `_handle_mergemem` | 128 | 1446-1574 | "Merge operation failed" |
| `_handle_diagnostics` | 115 | 2098-2213 | "Diagnostics failed" |
| `_handle_metrics` | 90 | 1942-2032 | "Metrics retrieval failed" |
| `_handle_importmem` | 82 | 1364-1446 | "Import failed" |

**Priority 2 - Medium handlers (40-80 lines):**
| Handler | Lines | Error Message |
|---------|-------|---------------|
| `_handle_status` | 75 | "Status check failed" |
| `_handle_logs` | 66 | "Log retrieval failed" |
| `_handle_sharemem` | 64 | "Share operation failed" |
| `_handle_readmem` | 62 | "Read failed" |
| `_handle_memname` | 57 | "Naming operation failed" |
| `_handle_zeromem` | 53 | "Zero mode operation failed" |
| `_handle_memuse` | 50 | "Use operation failed" |
| `_handle_bind` | 48 | "Bind operation failed" |
| `_handle_listmems` | 43 | "List operation failed" |
| `_handle_exportmem` | 42 | "Export failed" |
| `_handle_savemem` | 41 | "Save failed" |
| `_handle_saveprogress` | 40 | "Save progress failed" |

**Priority 3 - Small handlers (<20 lines):**
| Handler | Lines | Error Message |
|---------|-------|---------------|
| `_handle_unbind` | 11 | "Unbind failed" |
| `_handle_ping` | 10 | "Ping failed" |

**Estimated savings:** ~100 lines (error handling boilerplate removal)

### 5.2 Extract Large Handler Sub-Actions ✅ COMPLETE (2026-01-24)

Analysis showed most handlers were already well-refactored:
- `_handle_mergemem` (~20 lines) - Already delegates to MergeService
- `_handle_compressmem` (~24 lines) - Already delegates to CompressionService
- `_handle_archivemem` (~24 lines) - Already delegates to ArchiveService
- `_handle_diagnostics` (~5 lines) - Already delegates to MonitoringService

**Extracted: `_handle_select_entry` (170 lines) → SelectEntryService**
- Created `services/select_entry_service.py` (~200 lines)
- Handler reduced from 170 → 55 lines (handler + formatter)
- **Net savings: 103 lines in server.py**

### 5.3 Consolidate Utility Patterns

**5.3.1 Timestamp Formatting (11 occurrences)**
```python
# Current: Scattered across handlers
.strftime("%Y-%m-%d %H:%M:%S")

# Proposed: Add to response_builder.py
def format_timestamp(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%d %H:%M:%S")
```
Locations: lines 466, 479, 515, 568, 605, 677, 1133, 1388, 1497, 1529, 1747, 1765

**5.3.2 Slot Validation Pattern (8+ occurrences)**
```python
# Current: Repeated in handlers
slot_name = self._resolve_slot(arguments)
if not slot_name:
    return [TextContent(type="text", text=self.ERROR_NO_SLOT_SELECTED)]

# Proposed: Use existing @validate_slot_selected decorator
@validate_slot_selected()
async def _handle_savemem(self, arguments):
    ...
```

**5.3.3 Zero Mode Check (3 occurrences)**
```python
# Current: Repeated check
if self.storage._state.is_zero_mode():
    return [TextContent(type="text", text=self.WARNING_ZERO_MODE)]

# Proposed: Add decorator
@check_zero_mode()
async def _handle_savemem(self, arguments):
    ...
```

**5.3.4 Response Building Pattern**
```python
# Current: Manual list building
lines = []
lines.append(...)
return [TextContent(type="text", text="\n".join(lines))]

# Proposed: Use ResponseBuilder
return ResponseBuilder.from_lines(lines)
```

**Estimated savings:** ~50 lines

### 5.4 Underutilized Formatting Methods

17 formatting methods exist but aren't consistently used. Handlers should delegate:

| Handler | Should Use | Current State |
|---------|-----------|---------------|
| `_handle_readmem` | `_format_readmem_entries()` | Inline (lines 601-623) |
| `_handle_listmems` | `_format_slot_list()` | Inline (lines 695-724) |
| `_handle_select_entry` | `_format_select_entry_response()` | Inline (lines 926-965) |
| `_handle_searchmem` | `_format_search_results()` | Inline (lines 1118-1137) |

---

## Phase 6: Preloading Optimizations (Low Risk) ✅ COMPLETE (2026-01-24)

### 6.1 Current Initialization Analysis

| Component | Current | Load Time | Recommendation |
|-----------|---------|-----------|----------------|
| **StorageManager** | Eager | 50-100ms | Keep eager (required) |
| **StatusMonitoringSystem** | Eager | 30-50ms | **LAZY LOAD** |
| **TextSummarizer** | Lazy | 5-10ms | **EAGERLY LOAD** |
| **Tool Cache** | First use | 10-20ms | **PRE-POPULATE** |
| **MemorySlotMerger** | Lazy | 50-100ms | Keep lazy |
| **ContentImporter** | Lazy | 30-50ms | Keep lazy |
| **SimpleQueryProcessor** | Lazy | 40-60ms | Keep lazy |
| **Services (5x)** | Lazy | 20-50ms ea | Keep lazy |

### 6.2 Pre-load TextSummarizer ✅ COMPLETE

**Reason:** `memcord_save_progress` is a common first operation
**Implementation:** Changed from lazy-load to eager-load in `__init__`
**Impact:** Eliminates 5-10ms delay on first summary

### 6.3 Pre-populate Tool Cache ✅ COMPLETE

**Reason:** `list_tools()` is called on every MCP connection
**Implementation:** Pre-populated in `__init__` with `_get_basic_tools()` + optional advanced tools
**Impact:** Eliminates 10-20ms delay on first list_tools()

### 6.4 Lazy-load StatusMonitoringSystem (Medium)

**Reason:** Not all users need monitoring on every startup
**Current:** Fully initialized in `__init__` (spawns background threads)
**Impact:** Saves 30-50ms startup time for non-monitoring use cases

```python
# Convert from eager to lazy property
def __init__(self, memory_dir: str | Path = DEFAULT_MEMORY_DIR, ...):
    # ... existing initialization ...

    # CHANGE: Initialize to None
    self._status_monitor = None

@property
def status_monitor(self):
    """Lazy-loaded StatusMonitoringSystem instance."""
    if self._status_monitor is None:
        from .status_monitoring import StatusMonitoringSystem
        self._status_monitor = StatusMonitoringSystem(
            storage_manager=self.storage,
            data_dir=self.storage.memory_dir
        )
    return self._status_monitor
```

**Note:** Update all `self.status_monitor` references to use property accessor.

### 6.5 Optional Async Warmup Hook (Advanced)

For applications that want optimal first-call performance:

```python
async def warmup(self) -> None:
    """Optional async initialization for pre-warming caches.

    Call after server creation for optimal first-call performance:
        server = ChatMemoryServer()
        await server.warmup()
    """
    # Pre-load common slots metadata
    await self.storage.list_memory_slots()

    # Pre-initialize query processor if search is expected
    _ = self.query_processor

    # Warm the tool cache (if not already done)
    if self._tool_cache is None:
        self._tool_cache = handler_registry.get_tools(
            include_advanced=self.enable_advanced_tools
        )
```

### 6.6 Expected Performance Improvements

| Optimization | Startup Impact | First Call Impact |
|--------------|---------------|-------------------|
| Pre-load TextSummarizer | +5-10ms | -5-10ms on save_progress |
| Pre-populate tool cache | +10-20ms | -10-20ms on list_tools |
| Lazy-load StatusMonitoringSystem | -30-50ms | +30-50ms on first monitoring |
| **Net effect (typical use)** | **-15-20ms** | **-15-30ms** |

For users who don't use monitoring tools, startup is 30-50ms faster.
For users who do use monitoring, first monitoring call has a one-time 30-50ms delay.

---

## Files Created/Modified

### Source Files
| File | Lines | Status |
|------|-------|--------|
| `src/memcord/server.py` | 2,293 | ✅ Phase 4 complete - schemas co-located |
| `src/memcord/handler_registry.py` | 135 | ✅ Created |
| `src/memcord/response_builder.py` | 190 | ✅ Created |
| `src/memcord/services/__init__.py` | 58 | ✅ Created |
| `src/memcord/services/merge_service.py` | 307 | ✅ Created |
| `src/memcord/services/import_service.py` | 159 | ✅ Created |
| `src/memcord/services/compression_service.py` | 299 | ✅ Created |
| `src/memcord/services/archive_service.py` | 296 | ✅ Created |
| `src/memcord/services/monitoring_service.py` | 405 | ✅ Created |
| `src/memcord/services/select_entry_service.py` | 200 | ✅ Created (2026-01-24) |

### Test Files (Added 2026-01-24)
| File | Lines | Status |
|------|-------|--------|
| `tests/test_handler_registry.py` | ~350 | ✅ Created - 18 tests |
| `tests/test_response_builder.py` | ~320 | ✅ Created - 25 tests |
| `tests/test_merge_service.py` | ~400 | ✅ Created - 29 tests |
| `tests/test_import_service.py` | ~350 | ✅ Created - 24 tests |
| `tests/test_compression_service.py` | ~350 | ✅ Created - 27 tests |
| `tests/test_archive_service.py` | ~350 | ✅ Created - 27 tests |
| `tests/test_monitoring_service.py` | ~450 | ✅ Created - 37 tests |

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
- **Phase 5**: Decorators and extractions are additive; can revert individual handlers
- **Phase 6**: Preloading changes are isolated; can toggle eager/lazy independently

---

## Order of Implementation

### Completed ✅
1. **Phase 1** ✅ Handler registry with O(1) dispatch
2. **Phase 2** ✅ Service modules (merge, compression, archive, import, monitoring)
3. **Phase 3** ✅ Error handling decorators applied (6 handlers)
4. **Phase 4** ✅ Tool schema co-location

### Pending ⏳
5. **Phase 5** ⏳ Extended handler refactoring
   - 5.1: Apply `@handle_errors` to remaining 20 handlers
   - 5.2: Extract large handler sub-actions (select_entry, archive, compress, merge, diagnostics)
   - 5.3: Consolidate utility patterns (timestamp, slot validation, zero mode)
   - 5.4: Use existing formatting methods consistently

6. **Phase 6** ⏳ Preloading optimizations
   - 6.2: Pre-load TextSummarizer (quick win)
   - 6.3: Pre-populate tool cache (quick win)
   - 6.4: Lazy-load StatusMonitoringSystem
   - 6.5: Optional async warmup hook

### Results After Phase 1-4
- **server.py**: 2,736 → 2,293 lines (**-443 lines**, 16% reduction)
- **Architecture**: Clean separation of concerns with services
- **Dispatch**: O(1) lookup via handler registry
- **Schemas**: Single source of truth, co-located with handlers
- **Tests**: 429/429 passing ✅ (verified 2026-01-23)

### Expected Results After Phase 5-6
- **server.py**: 2,293 → ~1,850 lines (**~-443 more lines**, 32% total reduction)
- **@handle_errors coverage**: 6/26 → 26/26 handlers (100%)
- **Startup time**: ~50-80ms faster for typical use
- **First tool call**: ~15-30ms faster
