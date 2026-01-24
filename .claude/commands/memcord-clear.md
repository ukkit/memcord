---
description: Save memory and clear context
---

Before clearing the conversation context:

1. Check if the current working directory has a `.memcord` file (indicating a project binding)
2. If a binding exists:
   - Read the slot name from the `.memcord` file
   - Ask the user if they want to save the conversation to memory before clearing
   - If yes, use memcord_save_progress to auto-summarize and save the conversation
3. After saving (or if user declines), inform them to run `/clear` to clear the context

Note: This command prepares for context clearing but does not execute `/clear` itself - the user must run that separately.
