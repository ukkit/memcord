---
description: Auto-summarize and save conversation progress
---

Auto-summarize and save current conversation progress.

Use the memcord_save_progress tool to automatically summarize and append the current conversation to the memory slot.

**Auto-detection is built-in:** The server automatically detects the slot in this priority order:
1. Explicit slot_name in arguments
2. Currently active slot (via memcord_use/memcord_name)
3. Project binding (`.memcord` file in current working directory)

Just call `memcord_save_progress` directly - do NOT manually search for `.memcord` files.