---
name: memcord
description: Privacy-first, self-hosted chat memory for OpenClaw — save and recall conversation history across sessions without any cloud dependency.
version: 4.0.0
metadata:
  openclaw:
    requires:
      bins: [uv]
    install:
      - kind: uv
        package: memcord
        bins: [memcord]
---

# Memcord — Persistent Chat Memory

Memcord is a self-hosted MCP server that gives you persistent, searchable memory across conversations. All data is stored as plain JSON files on your own machine — nothing leaves your device.

## Adding Memcord to Your OpenClaw Gateway

Add the following block to your gateway configuration under `mcp.servers`. Only two tools are exposed by default: `memcord_auto_save` (write) and `memcord_read` (read).

```json5
mcp: {
  servers: {
    memcord: {
      command: "memcord",
      toolFilter: {
        include: ["memcord_auto_save", "memcord_read"]
      }
    }
  }
}
```

To use a custom slot name instead of the default `"default"` slot, set the environment variable:

```json5
mcp: {
  servers: {
    memcord: {
      command: "memcord",
      env: { "MEMCORD_DEFAULT_SLOT": "main" },
      toolFilter: {
        include: ["memcord_auto_save", "memcord_read"]
      }
    }
  }
}
```

## How to Use This Skill

When activated, this skill gives you two tools:

**`memcord_auto_save`** — Save the current conversation to persistent memory. Call this at the end of meaningful conversations or whenever the user asks you to remember something. No slot setup required.

**`memcord_read`** — Recall everything stored in memory. Call this at the start of a new conversation to resume context, or when the user asks "what do you remember?" or "what did we discuss before?".

### When to auto-save
- User says "remember this", "save this", "keep this in mind"
- End of a session with important decisions or conclusions
- After completing a task the user may reference again

### When to read
- User says "what do you remember?", "remind me", "what did we discuss?"
- Start of a new session when continuity is expected
- Before answering questions that likely depend on past context
