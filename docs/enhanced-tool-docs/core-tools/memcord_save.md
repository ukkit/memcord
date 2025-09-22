# memcord_save - Save Chat Content to Memory

## Overview
**Category:** Core  
**Purpose:** Save chat text to memory slot (creates new entry)  
**Prerequisites:** Active memory slot (use `memcord_name` first)

## Detailed Description
Saves chat text to the current or specified memory slot as a manual save entry. This creates a new timestamped entry in your memory slot, preserving the exact content you provide. Unlike summarization tools, this saves content verbatim, making it perfect for preserving important conversations, decisions, or detailed technical discussions.

Each save creates a new entry rather than overwriting existing content, so you can build up a comprehensive history over time.

## Usage Examples

### Example 1: Save Important Conversation
**Scenario:** Preserve a critical technical discussion  
**Command:**
```bash
memcord_save chat_text="Claude: Here's my analysis of the database optimization issue. The main bottleneck appears to be in the query execution plan...

User: That's very helpful. What about indexing strategies for this specific case?

Claude: For your use case, I recommend composite indexing on the user_id and timestamp columns, which should improve query performance by 70-80%..."
```
**Expected Result:** Saved 245 characters to memory slot 'current_slot' with timestamp
**Follow-up:** Use `memcord_read` to verify the content was saved correctly

### Example 2: Save to Specific Slot
**Scenario:** Save meeting notes to a dedicated slot while working in another  
**Command:**
```bash
memcord_save chat_text="Meeting Summary: Decided to proceed with Plan B for the API migration. Timeline: 3 weeks. Assigned to John and Sarah." slot_name="team_meetings"
```
**Expected Result:** Saved 95 characters to memory slot 'team_meetings'
**Follow-up:** Switch to that slot with `memcord_name team_meetings` to continue meeting-related discussions

### Example 3: Save Research Findings
**Scenario:** Preserve detailed research or learning content  
**Command:**
```bash
memcord_save chat_text="Key insights from today's machine learning research:

1. Transformer architectures excel at sequence modeling
2. Attention mechanisms allow parallel processing
3. BERT vs GPT: bidirectional vs autoregressive training
4. Fine-tuning requires careful learning rate selection

References: Attention Is All You Need (Vaswani et al.), BERT paper (Devlin et al.)"
```
**Expected Result:** Research findings saved with full detail for future reference

## Common Use Cases
- **Decision Records:** Preserve important decisions and their reasoning
- **Technical Solutions:** Save working solutions to complex problems
- **Meeting Minutes:** Record key points and action items from meetings
- **Research Notes:** Preserve detailed findings from learning sessions
- **Code Reviews:** Save feedback and discussion about code changes
- **Troubleshooting Sessions:** Document problem-solving processes
- **Client Communications:** Record important client requirements or feedback

## Parameters
- **chat_text** (required): The text content to save
  - Can include multiple lines and formatting
  - Preserves exact formatting and content
  - No character limit (within reason)
- **slot_name** (optional): Target memory slot
  - If not specified, uses currently active slot
  - Useful for cross-slot saving without switching context

## Best Practices

### Content Organization
- **Include Context:** Add enough context so the saved content makes sense later
- **Use Clear Titles:** Start with descriptive headers when saving multiple topics
- **Preserve Structure:** Maintain formatting, bullet points, and numbering
- **Add Timestamps:** Include dates/times for time-sensitive information

### When to Use vs. memcord_save_progress
- **Use memcord_save for:**
  - Exact quotes or conversations
  - Technical specifications that must be precise
  - Meeting minutes with specific wording
  - Code snippets or configurations
  - Legal or compliance-related content

- **Use memcord_save_progress for:**
  - Long conversations that need summarization
  - Regular progress updates
  - Content where compression is beneficial
  - Ongoing research that builds up over time

## Troubleshooting

### Problem: Zero mode active - content not saved
**Solution:** Exit zero mode by using `memcord_name [slot_name]` to activate a memory slot
**Prevention:** Check memory status with `memcord_list` before saving
**Context:** Zero mode is a privacy feature that prevents all saving

### Problem: No memory slot selected
**Solution:** Use `memcord_name slot_name` to create or select a memory slot first
**Prevention:** Always start sessions by selecting a memory slot
**Quick Fix:** Use `memcord_name temp` for quick temporary storage

### Problem: Content seems to disappear after saving
**Solution:** Use `memcord_read` to verify content was saved - it creates new entries rather than replacing
**Check:** Content is added as a new timestamped entry, not overwriting existing content
**Verification:** Look for the entry timestamp in the read output

### Problem: Accidentally saved to wrong slot
**Solution:** 
1. Use `memcord_read slot_name="correct_slot"` to verify correct content
2. Copy content from the wrong slot using `memcord_read slot_name="wrong_slot"`  
3. Save to correct slot with `memcord_save chat_text="..." slot_name="correct_slot"`
4. Consider using `memcord_merge` if multiple corrections needed

## Tips & Tricks

💡 **Include Context:** Always add enough context so your saved content makes sense weeks or months later

💡 **Use Descriptive Headers:** Start saved content with clear titles like "Database Optimization Discussion - 2024-01-15"

💡 **Save Early, Save Often:** Don't wait until conversations are complete - save important insights as they develop

💡 **Cross-Slot Saving:** Use the slot_name parameter to save related content to different slots without losing your current context

💡 **Preserve Formatting:** The tool maintains line breaks, spacing, and structure - use this for readable saved content

💡 **Combine with Search:** After saving, test searchability with `memcord_search` using key terms from your saved content

## Related Tools
- **memcord_save_progress** - Auto-summarize and save (better for long content)
- **memcord_read** - Verify saved content and review existing entries
- **memcord_name** - Ensure you're saving to the correct memory slot
- **memcord_search** - Find saved content later using keywords
- **memcord_select_entry** - Access specific saved entries by time or index

## Workflow Integration

### Quick Save Workflow
1. Continue conversation until important point reached
2. **memcord_save** with relevant content
3. **memcord_read** to verify (optional)
4. Continue conversation

### Multi-Slot Documentation
1. **memcord_name** `main_project` - Work in main slot
2. **memcord_save** `slot_name="meeting_notes"` - Save meeting info to separate slot
3. **memcord_save** `slot_name="technical_specs"` - Save technical details to specs slot
4. Continue in main project slot without context switching

### Research Documentation
1. **memcord_name** `research_topic`
2. Save key insights: **memcord_save** with structured content
3. Save references: **memcord_save** with source citations
4. Use **memcord_search** to find related insights later
5. Eventually **memcord_merge** related research slots

## Error Recovery

### If Save Appears to Fail
1. **Check Zero Mode:** Use `memcord_list` to verify memory saving is active
2. **Verify Slot:** Confirm you have an active memory slot
3. **Check Content:** Use `memcord_read` to see if save actually succeeded
4. **Retry:** If needed, try saving again with simplified content

### Content Quality Assurance
1. **Immediate Verification:** Use `memcord_read` after important saves
2. **Search Test:** Try `memcord_search` with key terms to ensure findability
3. **Regular Review:** Periodically review saved content with `memcord_list`