---
description: Read from memory slot
---

Read from memory slot: $ARGUMENTS

Use the memcord_read tool to retrieve content from the specified memory slot.

**Auto-detection is built-in:** The server automatically detects the slot in this priority order:
1. Explicit slot_name in arguments
2. Currently active slot (via memcord_use/memcord_name)
3. Project binding (`.memcord` file in current working directory)

Just call `memcord_read` directly - do NOT manually search for `.memcord` files.