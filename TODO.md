# Memcord - Claude Code & MCP Compliance TODO

> **Generated**: 2026-01-18
> **Last Updated**: 2026-01-19
> **MCP Spec Version**: 2025-11-25
> **Memcord Version**: 2.3.7
> **Status**: P0 items complete, P2/P3 pending

This document outlines the implementation steps required to make memcord work flawlessly with Claude Code and comply with the latest MCP specification.

---

## Priority Legend

| Priority | Meaning |
|----------|---------|
| **P0** | Critical - Must fix for basic functionality |
| **P1** | High - Important for production readiness |
| **P2** | Medium - Recommended for full compliance |
| **P3** | Low - Nice to have / Future enhancement |

---

## 1. Add Project-Level `.mcp.json` Configuration

**Priority**: P0 (Critical)
**Effort**: Low
**Files to Create**: `.mcp.json`

### Why This Is Needed
Claude Code uses `.mcp.json` for project-scoped MCP server configuration. This allows team members to share MCP server configurations via version control and enables automatic server discovery.

### Implementation Steps

#### Step 1.1: Create the `.mcp.json` file at project root

```json
{
  "mcpServers": {
    "memcord": {
      "type": "stdio",
      "command": "uv",
      "args": [
        "--directory",
        "${workspaceFolder}",
        "run",
        "memcord"
      ],
      "env": {
        "PYTHONPATH": "${workspaceFolder}/src",
        "MEMCORD_ENABLE_ADVANCED": "false"
      }
    },
    "memcord-advanced": {
      "type": "stdio",
      "command": "uv",
      "args": [
        "--directory",
        "${workspaceFolder}",
        "run",
        "memcord"
      ],
      "env": {
        "PYTHONPATH": "${workspaceFolder}/src",
        "MEMCORD_ENABLE_ADVANCED": "true"
      }
    }
  }
}
```

#### Step 1.2: Add Windows-specific configuration variant

Create `.mcp.windows.json` for Windows users:

```json
{
  "mcpServers": {
    "memcord": {
      "type": "stdio",
      "command": "cmd",
      "args": [
        "/c",
        "uv",
        "--directory",
        "${workspaceFolder}",
        "run",
        "memcord"
      ],
      "env": {
        "PYTHONPATH": "${workspaceFolder}/src"
      }
    }
  }
}
```

#### Step 1.3: Update documentation

Add instructions to `README.md` explaining:
- How Claude Code auto-discovers `.mcp.json`
- Difference between local, project, and user scope
- How to approve project-scoped servers on first use

### Verification

```bash
# In Claude Code, run:
claude mcp list
# Should show "memcord" as available

# Or use the /mcp command in Claude Code to verify connection
```

---

## 2. Update MCP SDK Version

**Priority**: P0 (Critical)
**Effort**: Low
**Files to Modify**: `pyproject.toml`

### Why This Is Needed
The MCP specification 2025-11-25 introduced new features including progress tracking, elicitation, and improved error handling. The SDK version must support these features.

### Implementation Steps

#### Step 2.1: Check current SDK version compatibility

```bash
# Check available versions
uv pip index versions mcp

# Check current installed version
uv pip show mcp
```

#### Step 2.2: Update `pyproject.toml`

```toml
# Change from:
dependencies = [
    "mcp>=1.22.0",
    # ...
]

# Change to:
dependencies = [
    "mcp>=1.30.0,<2.0.0",  # Pin to 1.x for stability
    # ...
]
```

#### Step 2.3: Update lock file and test

```bash
# Update dependencies
uv sync

# Run tests to ensure compatibility
uv run pytest tests/ -v

# Test MCP server manually
uv run memcord
```

#### Step 2.4: Review SDK changelog for breaking changes

Check https://github.com/modelcontextprotocol/python-sdk/releases for:
- New required methods
- Deprecated APIs
- Changed signatures

### Verification

```python
# Add version check to server.py
import mcp
print(f"MCP SDK Version: {mcp.__version__}")
```

---

## 3. Add Progress Notification Support

**Priority**: P2 (Medium)
**Effort**: Medium
**Files to Modify**: `src/memcord/server.py`, `src/memcord/merger.py`, `src/memcord/importer.py`

### Why This Is Needed
The 2025-11-25 MCP spec adds progress tracking utilities. Long-running operations (merge, import, search across large datasets) should report progress to clients.

### Implementation Steps

#### Step 3.1: Create progress notification helper

Add to `src/memcord/utils/progress.py`:

```python
"""Progress notification utilities for MCP."""

import secrets
from dataclasses import dataclass
from typing import Optional

@dataclass
class ProgressTracker:
    """Track and report operation progress."""

    operation_id: str
    total: int
    current: int = 0
    message: Optional[str] = None

    @classmethod
    def create(cls, total: int, message: str = None) -> "ProgressTracker":
        return cls(
            operation_id=secrets.token_hex(8),
            total=total,
            message=message
        )

    def update(self, current: int, message: str = None) -> dict:
        """Update progress and return notification payload."""
        self.current = current
        if message:
            self.message = message
        return {
            "progressToken": self.operation_id,
            "progress": self.current,
            "total": self.total,
            "message": self.message
        }

    def increment(self, amount: int = 1) -> dict:
        """Increment progress by amount."""
        return self.update(self.current + amount)

    def complete(self) -> dict:
        """Mark operation as complete."""
        return self.update(self.total, "Complete")
```

#### Step 3.2: Update server to support progress notifications

In `src/memcord/server.py`:

```python
from .utils.progress import ProgressTracker

class ChatMemoryServer:
    # ... existing code ...

    async def _send_progress(self, tracker: ProgressTracker):
        """Send progress notification to client."""
        try:
            await self.app.send_notification(
                "notifications/progress",
                tracker.update(tracker.current, tracker.message)
            )
        except Exception:
            # Progress notifications are optional, don't fail operation
            pass
```

#### Step 3.3: Add progress to merge operation

In `_handle_merge()`:

```python
async def _handle_merge(self, arguments: dict) -> Sequence[TextContent]:
    source_slots = arguments.get("source_slots", [])

    # Create progress tracker
    tracker = ProgressTracker.create(
        total=len(source_slots) + 2,  # slots + dedup + save
        message="Starting merge operation"
    )
    await self._send_progress(tracker)

    # Load each slot with progress
    for i, slot_name in enumerate(source_slots):
        slot = await self.storage._load_slot(slot_name)
        tracker.update(i + 1, f"Loaded {slot_name}")
        await self._send_progress(tracker)

    # Deduplicate
    tracker.update(len(source_slots) + 1, "Detecting duplicates")
    await self._send_progress(tracker)

    # ... merge logic ...

    # Complete
    await self._send_progress(tracker.complete())
```

#### Step 3.4: Add progress to import operation

Similar pattern for `_handle_import()` with:
- URL fetch progress
- PDF page processing progress
- Content extraction progress

### Verification

```python
# Test that progress notifications are sent
# Add test in tests/test_progress.py

@pytest.mark.asyncio
async def test_merge_sends_progress():
    server = ChatMemoryServer()
    # Mock notification sending
    notifications = []
    server.app.send_notification = lambda m, d: notifications.append((m, d))

    await server._handle_merge({
        "source_slots": ["slot1", "slot2"],
        "target_slot": "merged",
        "action": "merge"
    })

    assert any(n[0] == "notifications/progress" for n in notifications)
```

---

## 4. Add `list_changed` Notifications

**Priority**: P2 (Medium)
**Effort**: Low
**Files to Modify**: `src/memcord/server.py`, `src/memcord/storage.py`

### Why This Is Needed
Claude Code supports dynamic tool/resource updates. When memory slots are created, deleted, or modified, the client should be notified so it can refresh its resource list without reconnecting.

### Implementation Steps

#### Step 4.1: Create notification helper methods

In `src/memcord/server.py`:

```python
class ChatMemoryServer:
    # ... existing code ...

    async def _notify_resources_changed(self):
        """Notify client that resource list has changed."""
        try:
            await self.app.send_notification(
                "notifications/resources/list_changed",
                {}
            )
        except Exception:
            # Notification failure shouldn't break operations
            pass

    async def _notify_tools_changed(self):
        """Notify client that tool list has changed."""
        try:
            await self.app.send_notification(
                "notifications/tools/list_changed",
                {}
            )
        except Exception:
            pass
```

#### Step 4.2: Call notifications after state changes

Update handlers that modify resources:

```python
async def _handle_memname(self, arguments: dict) -> Sequence[TextContent]:
    # ... existing logic to create/select slot ...

    if created_new_slot:
        await self._notify_resources_changed()

    return result

async def _handle_savemem(self, arguments: dict) -> Sequence[TextContent]:
    # ... existing save logic ...

    # Notify after successful save
    await self._notify_resources_changed()

    return result

async def _handle_merge(self, arguments: dict) -> Sequence[TextContent]:
    # ... merge logic ...

    if action == "merge" and success:
        await self._notify_resources_changed()

    return result
```

#### Step 4.3: Add notification when advanced tools toggle

```python
def toggle_advanced_tools(self, enabled: bool):
    """Toggle advanced tools availability."""
    if self.enable_advanced_tools != enabled:
        self.enable_advanced_tools = enabled
        self._tool_cache = None  # Invalidate cache
        asyncio.create_task(self._notify_tools_changed())
```

### Verification

```bash
# In Claude Code, after adding a memory slot:
# The resource list should update automatically without /mcp refresh
```

---

## 5. Windows Compatibility Fix

**Priority**: P0 (Critical for Windows users)
**Effort**: Low
**Files to Modify**: Documentation, config templates

### Why This Is Needed
Windows requires special handling for stdio-based MCP servers. The `uv` command may need to be wrapped with `cmd /c` for proper process spawning.

### Implementation Steps

#### Step 5.1: Create Windows-specific config template

Create `config-templates/claude_desktop_config.windows.json`:

```json
{
  "mcpServers": {
    "memcord": {
      "command": "cmd",
      "args": [
        "/c",
        "uv",
        "--directory",
        "C:\\path\\to\\memcord",
        "run",
        "memcord"
      ],
      "env": {
        "PYTHONPATH": "C:\\path\\to\\memcord\\src"
      }
    }
  }
}
```

#### Step 5.2: Add platform detection to installation docs

Update `docs/installation.md`:

```markdown
## Platform-Specific Configuration

### Windows

On Windows, wrap the `uv` command with `cmd /c`:

\`\`\`json
{
  "mcpServers": {
    "memcord": {
      "command": "cmd",
      "args": ["/c", "uv", "--directory", "C:\\path\\to\\memcord", "run", "memcord"]
    }
  }
}
\`\`\`

### macOS / Linux

\`\`\`json
{
  "mcpServers": {
    "memcord": {
      "command": "uv",
      "args": ["--directory", "/path/to/memcord", "run", "memcord"]
    }
  }
}
\`\`\`
```

#### Step 5.3: Add auto-detection script

Create `scripts/generate-config.py`:

```python
#!/usr/bin/env python3
"""Generate platform-appropriate MCP configuration."""

import json
import os
import sys
from pathlib import Path

def generate_config():
    memcord_path = Path(__file__).parent.parent.resolve()

    if sys.platform == "win32":
        config = {
            "mcpServers": {
                "memcord": {
                    "command": "cmd",
                    "args": [
                        "/c", "uv",
                        "--directory", str(memcord_path),
                        "run", "memcord"
                    ],
                    "env": {
                        "PYTHONPATH": str(memcord_path / "src")
                    }
                }
            }
        }
    else:
        config = {
            "mcpServers": {
                "memcord": {
                    "command": "uv",
                    "args": [
                        "--directory", str(memcord_path),
                        "run", "memcord"
                    ],
                    "env": {
                        "PYTHONPATH": str(memcord_path / "src")
                    }
                }
            }
        }

    print(json.dumps(config, indent=2))
    return config

if __name__ == "__main__":
    generate_config()
```

#### Step 5.4: Test on Windows

```powershell
# Test the configuration
cmd /c uv --directory C:\path\to\memcord run memcord

# Verify JSON-RPC communication works
# The server should start without errors
```

### Verification

```powershell
# On Windows, in Claude Code:
claude mcp list
# Should show memcord as connected

# Test a tool call
# Use /mcp to verify server status
```

---

## 6. Implement HTTP Transport Option

**Priority**: P2 (Medium)
**Effort**: High
**Files to Create**: `src/memcord/http_server.py`
**Files to Modify**: `pyproject.toml`, `src/memcord/__init__.py`

### Why This Is Needed
HTTP is the recommended transport for remote/cloud deployments. This enables:
- Running memcord as a shared service
- Cloud deployment scenarios
- Better debugging with standard HTTP tools

### Implementation Steps

#### Step 6.1: Add HTTP dependencies

In `pyproject.toml`:

```toml
dependencies = [
    # ... existing deps ...
    "starlette>=0.35.0",
    "uvicorn>=0.27.0",
    "httpx>=0.26.0",  # For testing
]

[project.optional-dependencies]
http = [
    "starlette>=0.35.0",
    "uvicorn>=0.27.0",
]
```

#### Step 6.2: Create HTTP server module

Create `src/memcord/http_server.py`:

```python
"""HTTP transport for memcord MCP server."""

import asyncio
import json
import logging
from typing import Any

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse, StreamingResponse
from starlette.routing import Route
from starlette.middleware.cors import CORSMiddleware

from .server import ChatMemoryServer

logger = logging.getLogger(__name__)


class HTTPMemcordServer:
    """HTTP wrapper for ChatMemoryServer."""

    def __init__(
        self,
        memory_dir: str = "memory_slots",
        shared_dir: str = "shared_memories",
        enable_advanced_tools: bool = None,
        cors_origins: list[str] = None
    ):
        self.mcp_server = ChatMemoryServer(
            memory_dir=memory_dir,
            shared_dir=shared_dir,
            enable_advanced_tools=enable_advanced_tools
        )
        self.cors_origins = cors_origins or ["*"]
        self.app = self._create_app()

    def _create_app(self) -> Starlette:
        """Create Starlette application with routes."""
        routes = [
            Route("/", self.health_check, methods=["GET"]),
            Route("/mcp", self.handle_mcp, methods=["POST"]),
            Route("/mcp/sse", self.handle_sse, methods=["GET"]),
        ]

        app = Starlette(routes=routes)

        # Add CORS middleware
        app.add_middleware(
            CORSMiddleware,
            allow_origins=self.cors_origins,
            allow_methods=["GET", "POST"],
            allow_headers=["*"],
        )

        return app

    async def health_check(self, request: Request) -> JSONResponse:
        """Health check endpoint."""
        return JSONResponse({
            "status": "healthy",
            "server": "memcord",
            "version": "2.3.6",
            "transport": "http"
        })

    async def handle_mcp(self, request: Request) -> JSONResponse:
        """Handle MCP JSON-RPC requests."""
        try:
            body = await request.json()

            # Route based on method
            method = body.get("method")
            params = body.get("params", {})
            request_id = body.get("id")

            if method == "initialize":
                result = await self._handle_initialize(params)
            elif method == "tools/list":
                result = await self._handle_list_tools()
            elif method == "tools/call":
                result = await self._handle_call_tool(params)
            elif method == "resources/list":
                result = await self._handle_list_resources()
            elif method == "resources/read":
                result = await self._handle_read_resource(params)
            else:
                return JSONResponse({
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {
                        "code": -32601,
                        "message": f"Method not found: {method}"
                    }
                })

            return JSONResponse({
                "jsonrpc": "2.0",
                "id": request_id,
                "result": result
            })

        except Exception as e:
            logger.exception("Error handling MCP request")
            return JSONResponse({
                "jsonrpc": "2.0",
                "id": body.get("id") if "body" in dir() else None,
                "error": {
                    "code": -32603,
                    "message": str(e)
                }
            }, status_code=500)

    async def handle_sse(self, request: Request) -> StreamingResponse:
        """Handle Server-Sent Events for notifications."""
        async def event_generator():
            # Send initial connection event
            yield f"data: {json.dumps({'type': 'connected'})}\n\n"

            # Keep connection alive
            while True:
                await asyncio.sleep(30)
                yield f"data: {json.dumps({'type': 'ping'})}\n\n"

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
            }
        )

    async def _handle_initialize(self, params: dict) -> dict:
        """Handle initialize request."""
        return {
            "protocolVersion": "2025-11-25",
            "serverInfo": {
                "name": "memcord",
                "version": "2.3.6"
            },
            "capabilities": {
                "tools": {"listChanged": True},
                "resources": {"listChanged": True},
            }
        }

    async def _handle_list_tools(self) -> dict:
        """Handle tools/list request."""
        tools = await self.mcp_server.list_tools_direct()
        return {
            "tools": [
                {
                    "name": t.name,
                    "description": t.description,
                    "inputSchema": t.inputSchema
                }
                for t in tools
            ]
        }

    async def _handle_call_tool(self, params: dict) -> dict:
        """Handle tools/call request."""
        name = params.get("name")
        arguments = params.get("arguments", {})

        result = await self.mcp_server.call_tool_direct(name, arguments)

        return {
            "content": [
                {"type": "text", "text": r.text}
                for r in result
            ]
        }

    async def _handle_list_resources(self) -> dict:
        """Handle resources/list request."""
        resources = await self.mcp_server.list_resources_direct()
        return {
            "resources": [
                {
                    "uri": r.uri,
                    "name": r.name,
                    "mimeType": r.mimeType
                }
                for r in resources
            ]
        }

    async def _handle_read_resource(self, params: dict) -> dict:
        """Handle resources/read request."""
        uri = params.get("uri")
        content = await self.mcp_server.read_resource_direct(uri)
        return {
            "contents": [
                {"uri": uri, "text": content}
            ]
        }


def run_http_server(
    host: str = "0.0.0.0",
    port: int = 8080,
    **kwargs
):
    """Run the HTTP server."""
    import uvicorn

    server = HTTPMemcordServer(**kwargs)
    uvicorn.run(server.app, host=host, port=port)


if __name__ == "__main__":
    run_http_server()
```

#### Step 6.3: Add entry point for HTTP mode

In `pyproject.toml`:

```toml
[project.scripts]
memcord = "memcord.server:main"
memcord-http = "memcord.http_server:run_http_server"
```

#### Step 6.4: Add HTTP configuration template

Create `config-templates/claude_code_http.json`:

```json
{
  "mcpServers": {
    "memcord": {
      "type": "http",
      "url": "http://localhost:8080/mcp",
      "headers": {
        "Authorization": "Bearer ${MEMCORD_API_KEY}"
      }
    }
  }
}
```

#### Step 6.5: Add authentication middleware (optional)

```python
from starlette.middleware.authentication import AuthenticationMiddleware

class BearerAuthBackend:
    async def authenticate(self, request):
        auth = request.headers.get("Authorization")
        if not auth or not auth.startswith("Bearer "):
            return None
        token = auth.replace("Bearer ", "")
        # Validate token
        if token == os.getenv("MEMCORD_API_KEY"):
            return AuthCredentials(["authenticated"]), SimpleUser("api")
        return None
```

### Verification

```bash
# Start HTTP server
uv run memcord-http --port 8080

# Test health endpoint
curl http://localhost:8080/

# Test tool listing
curl -X POST http://localhost:8080/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}'

# Configure Claude Code to use HTTP
claude mcp add --transport http memcord-http http://localhost:8080/mcp
```

---

## 7. Add MCP Tool Search Optimization

**Priority**: P3 (Low)
**Effort**: Low
**Files to Modify**: `src/memcord/server.py`

### Why This Is Needed
Claude Code enables "tool search" when MCP tools exceed 10% of context window. With 11-30 tools, memcord may trigger this feature. Optimizing tool descriptions improves search accuracy.

### Implementation Steps

#### Step 7.1: Enhance tool descriptions with keywords

Update tool definitions in `server.py`:

```python
Tool(
    name="memcord_save",
    description=(
        "Save chat text to memory slot (overwrites existing content). "
        "Keywords: store, write, persist, record, capture conversation"
    ),
    inputSchema={...}
),

Tool(
    name="memcord_search",
    description=(
        "Search across all memory slots with advanced filtering. "
        "Supports Boolean operators (AND, OR, NOT), tags, and regex. "
        "Keywords: find, lookup, query, filter, grep memories"
    ),
    inputSchema={...}
),
```

#### Step 7.2: Group related tools with consistent naming

Ensure naming follows patterns:
- `memcord_save*` - All save operations
- `memcord_read*` - All read operations
- `memcord_search*` / `memcord_query*` - All search operations
- `memcord_list*` - All listing operations

#### Step 7.3: Add tool categories as annotations

```python
Tool(
    name="memcord_merge",
    description="Merge multiple memory slots into one with duplicate detection",
    inputSchema={...},
    # Note: annotations may need SDK support
    # annotations={"category": "organization", "complexity": "advanced"}
),
```

#### Step 7.4: Document tool search behavior

Add to `docs/claude-code-integration.md`:

```markdown
## Tool Search Optimization

When memcord is used with Claude Code, the tool search feature may activate
if tool definitions exceed 10% of the context window.

### Configuring Tool Search Threshold

\`\`\`bash
# Set custom threshold (default: auto:10)
ENABLE_TOOL_SEARCH=auto:5 claude

# Disable tool search
ENABLE_TOOL_SEARCH=false claude
\`\`\`

### Best Practices

1. Use specific keywords when asking for memory operations
2. Mention the tool name if you know it (e.g., "use memcord_search")
3. For complex operations, be descriptive about what you want
```

### Verification

```bash
# Check if tool search is activating
ENABLE_TOOL_SEARCH=auto:5 claude --mcp-debug

# Verify tool descriptions are searchable
# Ask Claude Code: "find memories about Python"
# Should trigger memcord_search or memcord_query
```

---

## 8. Audit and Fix stdout Usage in STDIO Mode

**Priority**: P0 (Critical)
**Effort**: Medium
**Files to Audit**: All Python files in `src/memcord/`

### Why This Is Needed
In STDIO mode, any output to stdout corrupts JSON-RPC messages and breaks communication. All debug output must go to stderr via logging.

### Implementation Steps

#### Step 8.1: Search for print statements

```bash
# Find all print statements
grep -rn "print(" src/memcord/

# Find all sys.stdout usage
grep -rn "sys.stdout" src/memcord/
grep -rn "stdout" src/memcord/
```

#### Step 8.2: Configure logging to use stderr

Create/update `src/memcord/logging_config.py`:

```python
"""Logging configuration for memcord."""

import logging
import sys


def configure_logging(level: str = "INFO"):
    """Configure logging to use stderr only."""

    # Create stderr handler
    handler = logging.StreamHandler(sys.stderr)
    handler.setLevel(getattr(logging, level.upper()))

    # Create formatter
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    handler.setFormatter(formatter)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper()))
    root_logger.addHandler(handler)

    # Specifically configure memcord logger
    memcord_logger = logging.getLogger("memcord")
    memcord_logger.setLevel(getattr(logging, level.upper()))

    return memcord_logger


# Convenience function
def get_logger(name: str) -> logging.Logger:
    """Get a logger for the specified module."""
    return logging.getLogger(f"memcord.{name}")
```

#### Step 8.3: Replace print statements with logging

Example replacements:

```python
# Before
print(f"Loading slot: {slot_name}")
print(f"Error: {e}")

# After
from .logging_config import get_logger
logger = get_logger(__name__)

logger.debug(f"Loading slot: {slot_name}")
logger.error(f"Error: {e}")
```

#### Step 8.4: Add logging initialization to server startup

In `src/memcord/server.py`:

```python
import os
from .logging_config import configure_logging

def main():
    """Main entry point."""
    # Configure logging before anything else
    log_level = os.getenv("MEMCORD_LOG_LEVEL", "WARNING")
    configure_logging(log_level)

    server = ChatMemoryServer()
    asyncio.run(server.run())
```

#### Step 8.5: Add CI check for print statements

Create `.github/workflows/lint.yml` addition:

```yaml
- name: Check for print statements
  run: |
    if grep -rn "print(" src/memcord/ --include="*.py" | grep -v "# noqa: print"; then
      echo "Found print statements that may break STDIO mode"
      exit 1
    fi
```

### Verification

```bash
# Test STDIO mode with debug logging
MEMCORD_LOG_LEVEL=DEBUG uv run memcord 2>debug.log

# Verify no output to stdout
# stdout should only have JSON-RPC messages
# stderr (debug.log) should have all debug output

# Test with Claude Code
claude --mcp-debug
# Should connect without JSON parse errors
```

---

## 9. Add Elicitation Support (2025 Feature)

**Priority**: P3 (Low)
**Effort**: High
**Files to Create**: `src/memcord/elicitation.py`
**Files to Modify**: `src/memcord/server.py`

### Why This Is Needed
The 2025-11-25 MCP spec adds elicitation - allowing servers to request information from users during operations. This enhances UX for ambiguous queries.

### Implementation Steps

#### Step 9.1: Check SDK support for elicitation

```python
# Verify SDK supports elicitation
from mcp.types import ElicitationRequest, ElicitationResponse  # May not exist yet
```

#### Step 9.2: Create elicitation helper module

Create `src/memcord/elicitation.py`:

```python
"""Elicitation support for interactive user queries."""

from dataclasses import dataclass
from typing import Any, Optional
from enum import Enum


class ElicitationType(Enum):
    """Types of elicitation requests."""
    CHOICE = "choice"  # Select from options
    TEXT = "text"      # Free text input
    CONFIRM = "confirm"  # Yes/No confirmation


@dataclass
class ElicitationRequest:
    """Request for user input."""

    type: ElicitationType
    message: str
    options: Optional[list[str]] = None
    default: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        result = {
            "type": self.type.value,
            "message": self.message,
        }
        if self.options:
            result["options"] = self.options
        if self.default:
            result["default"] = self.default
        return result


class ElicitationHelper:
    """Helper for server-initiated user queries."""

    def __init__(self, app):
        self.app = app
        self.supported = self._check_support()

    def _check_support(self) -> bool:
        """Check if client supports elicitation."""
        # Check client capabilities from initialization
        return getattr(self.app, "_client_capabilities", {}).get("elicitation", False)

    async def request_choice(
        self,
        message: str,
        options: list[str],
        default: Optional[str] = None
    ) -> Optional[str]:
        """Request user to choose from options."""
        if not self.supported:
            return default

        try:
            response = await self.app.request_elicitation({
                "type": "choice",
                "message": message,
                "options": options,
                "default": default
            })
            return response.get("value")
        except Exception:
            return default

    async def request_confirmation(
        self,
        message: str,
        default: bool = False
    ) -> bool:
        """Request user confirmation."""
        if not self.supported:
            return default

        try:
            response = await self.app.request_elicitation({
                "type": "confirm",
                "message": message,
                "default": default
            })
            return response.get("value", default)
        except Exception:
            return default

    async def request_text(
        self,
        message: str,
        default: Optional[str] = None
    ) -> Optional[str]:
        """Request free text input."""
        if not self.supported:
            return default

        try:
            response = await self.app.request_elicitation({
                "type": "text",
                "message": message,
                "default": default
            })
            return response.get("value")
        except Exception:
            return default
```

#### Step 9.3: Integrate elicitation into query handler

In `src/memcord/server.py`:

```python
from .elicitation import ElicitationHelper

class ChatMemoryServer:
    def __init__(self, ...):
        # ... existing init ...
        self.elicitation = ElicitationHelper(self.app)

    async def _handle_querymem(self, arguments: dict) -> Sequence[TextContent]:
        question = arguments.get("question", "")

        # If query is ambiguous, ask for clarification
        if self._is_ambiguous_query(question):
            slots = await self.storage.list_slots()

            if self.elicitation.supported:
                selected = await self.elicitation.request_choice(
                    message=f"Which memory slot should I search for '{question}'?",
                    options=["All slots"] + [s.name for s in slots],
                    default="All slots"
                )

                if selected and selected != "All slots":
                    arguments["slot_name"] = selected

        # Continue with query...
        return await self._execute_query(arguments)
```

#### Step 9.4: Add elicitation for merge confirmation

```python
async def _handle_merge(self, arguments: dict) -> Sequence[TextContent]:
    action = arguments.get("action", "preview")

    if action == "merge":
        # Confirm before destructive merge
        if self.elicitation.supported:
            confirmed = await self.elicitation.request_confirmation(
                message=(
                    f"Merge {len(arguments['source_slots'])} slots into "
                    f"'{arguments['target_slot']}'? This cannot be undone."
                ),
                default=False
            )
            if not confirmed:
                return [TextContent(type="text", text="Merge cancelled by user.")]

    # Continue with merge...
```

### Verification

```python
# Test elicitation (requires client support)
@pytest.mark.asyncio
async def test_elicitation_choice():
    server = ChatMemoryServer()

    # Mock elicitation support
    server.elicitation.supported = True
    server.app.request_elicitation = AsyncMock(return_value={"value": "slot1"})

    result = await server.elicitation.request_choice(
        "Which slot?",
        ["slot1", "slot2"]
    )

    assert result == "slot1"
```

---

## 10. Add Authorization/Consent Handling

**Priority**: P2 (Medium)
**Effort**: Medium
**Files to Create**: `src/memcord/consent.py`
**Files to Modify**: `src/memcord/server.py`, `src/memcord/security.py`

### Why This Is Needed
The 2025-11-25 MCP spec emphasizes explicit user consent for data access and operations. Implementing consent flows improves security and user trust.

### Implementation Steps

#### Step 10.1: Create consent management module

Create `src/memcord/consent.py`:

```python
"""User consent management for memcord operations."""

import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Optional


class ConsentScope(Enum):
    """Scopes requiring user consent."""
    READ_MEMORY = "read_memory"
    WRITE_MEMORY = "write_memory"
    DELETE_MEMORY = "delete_memory"
    EXPORT_DATA = "export_data"
    SHARE_MEMORY = "share_memory"
    IMPORT_EXTERNAL = "import_external"


class ConsentDuration(Enum):
    """Duration of consent grant."""
    ONCE = "once"           # Single operation
    SESSION = "session"     # Current session only
    PERMANENT = "permanent" # Until revoked


@dataclass
class ConsentGrant:
    """A recorded consent grant."""
    scope: ConsentScope
    duration: ConsentDuration
    granted_at: datetime
    expires_at: Optional[datetime] = None
    resource: Optional[str] = None  # Specific resource, or None for all

    def is_valid(self) -> bool:
        """Check if consent is still valid."""
        if self.duration == ConsentDuration.ONCE:
            return False  # One-time grants are consumed immediately
        if self.expires_at and datetime.now() > self.expires_at:
            return False
        return True


@dataclass
class ConsentStore:
    """Store for user consent grants."""

    grants: dict[str, list[ConsentGrant]] = field(default_factory=dict)
    storage_path: Optional[Path] = None

    def __post_init__(self):
        if self.storage_path:
            self._load()

    def _load(self):
        """Load grants from storage."""
        if self.storage_path and self.storage_path.exists():
            try:
                data = json.loads(self.storage_path.read_text())
                # Deserialize grants...
            except Exception:
                pass

    def _save(self):
        """Save grants to storage."""
        if self.storage_path:
            # Serialize and save...
            pass

    def grant(
        self,
        scope: ConsentScope,
        duration: ConsentDuration = ConsentDuration.SESSION,
        resource: Optional[str] = None
    ) -> ConsentGrant:
        """Record a consent grant."""
        grant = ConsentGrant(
            scope=scope,
            duration=duration,
            granted_at=datetime.now(),
            expires_at=self._calculate_expiry(duration),
            resource=resource
        )

        key = f"{scope.value}:{resource or '*'}"
        if key not in self.grants:
            self.grants[key] = []
        self.grants[key].append(grant)

        self._save()
        return grant

    def has_consent(
        self,
        scope: ConsentScope,
        resource: Optional[str] = None
    ) -> bool:
        """Check if consent exists for scope/resource."""
        # Check specific resource
        key = f"{scope.value}:{resource or '*'}"
        if key in self.grants:
            for grant in self.grants[key]:
                if grant.is_valid():
                    return True

        # Check wildcard consent
        wildcard_key = f"{scope.value}:*"
        if wildcard_key in self.grants:
            for grant in self.grants[wildcard_key]:
                if grant.is_valid():
                    return True

        return False

    def revoke(self, scope: ConsentScope, resource: Optional[str] = None):
        """Revoke consent for scope/resource."""
        key = f"{scope.value}:{resource or '*'}"
        if key in self.grants:
            del self.grants[key]
            self._save()

    def revoke_all(self):
        """Revoke all consents."""
        self.grants.clear()
        self._save()

    def _calculate_expiry(self, duration: ConsentDuration) -> Optional[datetime]:
        """Calculate expiry time based on duration."""
        if duration == ConsentDuration.ONCE:
            return datetime.now()  # Expires immediately after use
        elif duration == ConsentDuration.SESSION:
            return datetime.now() + timedelta(hours=24)
        return None  # Permanent has no expiry


class ConsentManager:
    """Manager for consent operations with server integration."""

    def __init__(self, app, store: Optional[ConsentStore] = None):
        self.app = app
        self.store = store or ConsentStore()
        self.enabled = os.getenv("MEMCORD_REQUIRE_CONSENT", "false").lower() == "true"

    async def require_consent(
        self,
        scope: ConsentScope,
        resource: Optional[str] = None,
        message: Optional[str] = None
    ) -> bool:
        """Require consent before operation, requesting if needed."""
        if not self.enabled:
            return True

        # Check existing consent
        if self.store.has_consent(scope, resource):
            return True

        # Request consent from user (via elicitation if supported)
        granted = await self._request_consent(scope, resource, message)

        if granted:
            self.store.grant(scope, ConsentDuration.SESSION, resource)

        return granted

    async def _request_consent(
        self,
        scope: ConsentScope,
        resource: Optional[str],
        message: Optional[str]
    ) -> bool:
        """Request consent from user."""
        default_messages = {
            ConsentScope.READ_MEMORY: f"Allow reading memory slot '{resource}'?",
            ConsentScope.WRITE_MEMORY: f"Allow writing to memory slot '{resource}'?",
            ConsentScope.DELETE_MEMORY: f"Allow deleting memory slot '{resource}'?",
            ConsentScope.EXPORT_DATA: "Allow exporting memory data?",
            ConsentScope.SHARE_MEMORY: f"Allow sharing memory slot '{resource}'?",
            ConsentScope.IMPORT_EXTERNAL: "Allow importing external content?",
        }

        prompt = message or default_messages.get(scope, f"Allow {scope.value}?")

        # Try elicitation first
        try:
            response = await self.app.request_elicitation({
                "type": "confirm",
                "message": prompt,
                "default": False
            })
            return response.get("value", False)
        except Exception:
            # Elicitation not supported, assume consent in non-strict mode
            return not self.enabled
```

#### Step 10.2: Integrate consent into server operations

In `src/memcord/server.py`:

```python
from .consent import ConsentManager, ConsentScope

class ChatMemoryServer:
    def __init__(self, ...):
        # ... existing init ...
        self.consent = ConsentManager(self.app)

    async def _handle_readmem(self, arguments: dict) -> Sequence[TextContent]:
        slot_name = arguments.get("slot_name") or self.storage._current_slot

        # Require consent for reading
        if not await self.consent.require_consent(
            ConsentScope.READ_MEMORY,
            resource=slot_name
        ):
            return [TextContent(
                type="text",
                text=f"Access denied: consent required to read '{slot_name}'"
            )]

        # Continue with read operation...
        return await self._execute_read(arguments)

    async def _handle_import(self, arguments: dict) -> Sequence[TextContent]:
        source = arguments.get("source", "")

        # Require consent for external imports
        if not await self.consent.require_consent(
            ConsentScope.IMPORT_EXTERNAL,
            message=f"Allow importing content from '{source}'?"
        ):
            return [TextContent(
                type="text",
                text="Import cancelled: user consent required"
            )]

        # Continue with import...
```

#### Step 10.3: Add consent configuration

Add environment variables:

```bash
# Enable consent requirement (default: false)
MEMCORD_REQUIRE_CONSENT=true

# Consent storage location
MEMCORD_CONSENT_FILE=~/.memcord/consents.json
```

#### Step 10.4: Add consent management tools

```python
Tool(
    name="memcord_consent_status",
    description="View current consent grants",
    inputSchema={"type": "object", "properties": {}},
),

Tool(
    name="memcord_consent_revoke",
    description="Revoke a consent grant",
    inputSchema={
        "type": "object",
        "properties": {
            "scope": {
                "type": "string",
                "enum": ["read_memory", "write_memory", "delete_memory",
                        "export_data", "share_memory", "import_external"],
                "description": "Consent scope to revoke"
            },
            "resource": {
                "type": "string",
                "description": "Specific resource, or omit for all"
            }
        },
        "required": ["scope"]
    },
),
```

### Verification

```python
# Test consent flow
@pytest.mark.asyncio
async def test_consent_required_for_read():
    server = ChatMemoryServer()
    server.consent.enabled = True

    # Mock consent denial
    server.app.request_elicitation = AsyncMock(return_value={"value": False})

    result = await server._handle_readmem({"slot_name": "secret"})

    assert "consent required" in result[0].text.lower()

@pytest.mark.asyncio
async def test_consent_granted():
    server = ChatMemoryServer()
    server.consent.enabled = True
    server.consent.store.grant(ConsentScope.READ_MEMORY, resource="public")

    result = await server._handle_readmem({"slot_name": "public"})

    assert "consent required" not in result[0].text.lower()
```

---

## Summary Checklist

| # | Task | Priority | Status | Notes |
|---|------|----------|--------|-------|
| 1 | Add `.mcp.json` configuration | P0 | [x] | v2.3.7: Created `config-templates/` with all platform configs |
| 2 | Update MCP SDK version | P0 | [x] | v2.3.7: Updated to `>=1.22.0,<2.0.0` in pyproject.toml (latest: 1.25.0) |
| 3 | Add progress notifications | P2 | [ ] | |
| 4 | Add `list_changed` notifications | P2 | [ ] | |
| 5 | Windows compatibility fix | P0 | [x] | v2.3.7: Added `install.ps1`, Windows configs with `cmd /c` wrapper |
| 6 | Implement HTTP transport | P2 | [ ] | |
| 7 | Tool search optimization | P3 | [ ] | |
| 8 | Audit stdout usage | P0 | [x] | v2.3.7: Created `logging_config.py`, configured in `server.py:main()` |
| 9 | Add elicitation support | P3 | [ ] | |
| 10 | Add consent handling | P2 | [ ] | |

### v2.3.7 Implementation Summary (P0 Complete)

**Files Created:**
- `config-templates/` - Centralized MCP configuration templates
  - `claude-desktop/config.json` and `config.windows.json`
  - `claude-code/mcp.json` and `mcp.windows.json`
  - `vscode/mcp.json`
  - `antigravity/mcp_config.json`
  - `README.md` - Setup instructions
- `scripts/generate-config.py` - Cross-platform config generator
- `install.ps1` - Windows PowerShell installer
- `src/memcord/logging_config.py` - Logging to stderr for STDIO mode

**Files Modified:**
- `install.sh` - Now calls generate-config.py
- `pyproject.toml` - MCP SDK version updated
- `src/memcord/server.py` - Logging configuration in main()
- `.gitignore` - Ignore generated config files
- `README.md` - Updated installation instructions

**Files Removed:**
- `.mcp.json.example` (redundant, use config-templates/)
- `claude_desktop_config.json` (now generated)
- `.vscode/mcp.json.example` (redundant)
- `.antigravity/mcp_config.json` (now generated from template)

---

## Testing Strategy

After implementing changes:

1. **Unit Tests**: Run `uv run pytest tests/ -v`
2. **MCP Protocol Tests**: Run `uv run pytest tests/ -m mcp -v`
3. **Integration Tests**:
   ```bash
   # Test with Claude Code
   claude mcp add --scope local memcord-test -- uv --directory . run memcord
   claude /mcp  # Verify connection
   ```
4. **Windows Testing**: Test on Windows with `cmd /c` wrapper
5. **HTTP Testing**: Test HTTP transport with curl/httpx

---

## References

- [MCP Specification 2025-11-25](https://modelcontextprotocol.io/specification/2025-11-25)
- [Claude Code MCP Documentation](https://code.claude.com/docs/en/mcp)
- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk)
- [Build an MCP Server](https://modelcontextprotocol.io/docs/develop/build-server)
