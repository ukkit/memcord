---
description: Deactivate memory slot and end session
---

Use the memcord_close tool to deactivate the current memory slot.

**Auto-detection is built-in:** The server will deactivate whatever slot is currently active.

Call `memcord_close` to:
1. Deactivate the current memory slot
2. Prevent accidental saves to wrong slots in future sessions

Optionally, use memcord_save_progress first to save the conversation before closing.
