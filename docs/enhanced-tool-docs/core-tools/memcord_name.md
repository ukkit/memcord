# memcord_name - Create or Select Memory Slots

## Overview
**Category:** Core  
**Purpose:** Create a new memory slot or activate an existing one  
**Prerequisites:** None - this is typically your first command

## Detailed Description
Creates a new memory slot or activates an existing one. This is the primary way to organize your conversations into named memory spaces. Each slot acts as an independent memory container with its own history, tags, and metadata.

Memory slots are automatically created if they don't exist, making this the most convenient way to start working with a new topic or project.

## Usage Examples

### Example 1: Create a New Project Memory
**Scenario:** Starting a new coding project  
**Command:**
```bash
memcord_name slot_name="web_app_project"
```
**Expected Result:** Memory slot 'web_app_project' created and activated with timestamp
**Follow-up:** Start saving project-related conversations with `memcord_save` or `memcord_save_progress`

### Example 2: Switch to Existing Memory
**Scenario:** Continue working on an existing project  
**Command:**
```bash
memcord_name slot_name="meeting_notes"
```
**Expected Result:** Memory slot 'meeting_notes' activated, showing creation date and entry count
**Follow-up:** Use `memcord_read` to review existing content before adding new information

### Example 3: Create Topic-Specific Memory
**Scenario:** Start a research session on a specific topic  
**Command:**
```bash
memcord_name slot_name="database_optimization_research"
```
**Expected Result:** New slot created with descriptive name for easy future identification
**Follow-up:** Use `memcord_save_progress` to save research findings with summarization

## Common Use Cases
- **Project Management:** Create slots for different projects or clients
- **Learning Sessions:** Separate slots for different topics or courses
- **Meeting Notes:** Individual slots for recurring meetings or teams
- **Research Sessions:** Topic-specific slots for deep-dive investigations
- **Troubleshooting:** Separate slots for different technical issues
- **Creative Work:** Different slots for various creative projects or ideas

## Parameters
- **slot_name** (required): Name of the memory slot
  - Spaces are automatically converted to underscores
  - Use descriptive names for easy identification
  - Consider naming conventions like `proj_`, `meet_`, `learn_` prefixes

## Best Practices

### Naming Conventions
- **Projects:** `proj_website_redesign`, `proj_mobile_app`
- **Meetings:** `meet_team_standup`, `meet_client_alpha`
- **Learning:** `learn_python_basics`, `learn_machine_learning`
- **Research:** `research_database_performance`, `research_ui_frameworks`

### Organization Tips
- Use consistent prefixes for related slots
- Include version numbers for iterative work: `proj_v2_website`
- Add dates for time-sensitive content: `meet_2024_01_planning`
- Keep names descriptive but concise (under 50 characters)

## Troubleshooting

### Problem: Slot name contains spaces or special characters
**Solution:** Spaces are automatically converted to underscores. Avoid special characters like `/`, `\`, `:`, etc.
**Prevention:** Use underscore_case or camelCase naming conventions
**Example:** `"my project notes"` becomes `my_project_notes`

### Problem: Can't remember existing slot names
**Solution:** Use `memcord_list` to see all available memory slots with metadata
**Prevention:** Use descriptive names and maintain a consistent naming pattern
**Follow-up:** Consider using `memcord_search` to find slots by content if needed

### Problem: Accidentally created duplicate slots with similar names
**Solution:** Use `memcord_merge` to consolidate related slots, then delete duplicates
**Prevention:** Check `memcord_list` before creating new slots with similar purposes
**Workflow:** Always review existing slots before starting new topics

## Tips & Tricks

💡 **Quick Start:** Always begin new sessions by creating or selecting a memory slot - this ensures your conversation is properly saved and organized

💡 **Descriptive Naming:** Use names that will make sense to you months later. Include context like project phase, client name, or topic focus

💡 **Automatic Creation:** Don't worry about whether a slot exists - if it doesn't, it will be created automatically

💡 **Context Switching:** Use this command to quickly switch between different conversation contexts without losing your place

💡 **Batch Organization:** Create multiple related slots at once for complex projects, e.g., `proj_frontend`, `proj_backend`, `proj_database`

## Related Tools
- **memcord_use** - Activate existing slots only (safer for avoiding typos)
- **memcord_list** - See all available memory slots before creating new ones
- **memcord_save** - Save content to the newly created/selected slot
- **memcord_read** - Review existing content in the slot
- **memcord_merge** - Combine related slots later if needed

## Workflow Integration

### Starting a New Session
1. **memcord_name** - Create/select memory slot
2. **memcord_list** - Confirm slot selection (optional)
3. **memcord_read** - Review existing content (if continuing previous work)
4. Start conversation and use **memcord_save** or **memcord_save_progress**

### Context Switching
1. **memcord_name** - Switch to different topic/project slot
2. **memcord_read** - Get oriented with previous context
3. Continue conversation in new context
4. **memcord_save** - Preserve new discussion

### Project Organization
1. Create main project slot: **memcord_name** `proj_main`
2. Create subsystem slots: **memcord_name** `proj_frontend`, `proj_backend`
3. Use **memcord_merge** later to consolidate related discussions
4. Apply **memcord_tag** and **memcord_group** for advanced organization