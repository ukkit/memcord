---
description: Save memory and clear context
---

Before clearing the conversation context:

1. Check if there's an active memory slot (via memcord_status or by checking current state)
2. If a slot is active:
   - Ask the user if they want to save the conversation to memory before clearing
   - If yes, use memcord_save_progress to auto-summarize and save
   - Call memcord_close to deactivate the slot
3. After saving and closing (or if user declines), inform them to run `/clear`

Note: This command prepares for context clearing but does not execute `/clear` itself.
