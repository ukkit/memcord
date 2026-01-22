---
description: Save current conversation to memory
---

Save current conversation to memory: $ARGUMENTS

Use the memcord_save tool to manually save chat content to the current memory slot.

**Auto-detection is built-in:** The server automatically detects the slot in this priority order:
1. Explicit slot_name in arguments
2. Currently active slot (via memcord_use/memcord_name)
3. Project binding (`.memcord` file in current working directory)

Just call `memcord_save` directly - do NOT manually search for `.memcord` files.