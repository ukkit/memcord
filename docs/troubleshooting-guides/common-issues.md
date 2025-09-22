# Common Memcord Issues and Solutions

This guide covers the most frequently encountered issues when using memcord tools, with step-by-step solutions and prevention strategies.

## Memory Management Issues

### Issue: "No memory slot selected" Error

**Problem:** You try to save content but get an error saying no memory slot is selected.

**Symptoms:**
```
Error: No memory slot selected. Use 'memname' first.
```

**Solution:**
1. **Create or select a memory slot:**
   ```bash
   memcord_name slot_name="your_project_name"
   ```

2. **Verify the slot is active:**
   ```bash
   memcord_list
   ```
   Look for "(current)" marker next to a slot name.

**Prevention:**
- Always start sessions by creating or selecting a memory slot
- Use descriptive names that clearly identify the purpose
- Check `memcord_list` if you're unsure about current status

**Quick Fix:**
```bash
# Emergency temporary slot for immediate saving
memcord_name slot_name="temp_session"
memcord_save chat_text="Your important content here"
```

---

### Issue: Zero Mode Active - Content Not Saved

**Problem:** Your content isn't being saved despite using save commands.

**Symptoms:**
```
⚠️ Zero mode active - content NOT saved.

💡 To save this content:
1. Use 'memcord_name [slot_name]' to select a memory slot
2. Then retry your save command
```

**Solution:**
1. **Exit zero mode by selecting any memory slot:**
   ```bash
   memcord_name slot_name="your_work_session"
   ```

2. **Retry your save command:**
   ```bash
   memcord_save chat_text="Your content here"
   ```

3. **Verify saving is working:**
   ```bash
   memcord_read
   ```

**Understanding Zero Mode:**
- Zero mode prevents all memory saving for privacy
- Activated with `memcord_zero` command
- Stays active until you select a regular memory slot
- Useful for sensitive conversations or testing

**Prevention:**
- Be aware when you've activated zero mode intentionally
- Check `memcord_list` to see current status
- Only use zero mode when privacy is specifically needed

---

### Issue: Memory Slot Not Found

**Problem:** You try to access a memory slot that doesn't exist.

**Symptoms:**
```
Memory slot 'project_name' not found.
Error: Memory slot 'old_project' does not exist. Use 'memcord_name' to create new slots or 'memcord_list' to see available slots.
```

**Solution:**
1. **Check available slots:**
   ```bash
   memcord_list
   ```

2. **Use correct slot name or create new one:**
   ```bash
   # If you found the correct name
   memcord_name slot_name="correct_name"
   
   # Or create a new slot
   memcord_name slot_name="new_project"
   ```

3. **Search for content if you can't find the right slot:**
   ```bash
   memcord_search query="key terms from your content"
   ```

**Common Causes:**
- Typos in slot names (e.g., "projecct" instead of "project")
- Forgotten exact naming (e.g., "web_app" vs "webapp" vs "web-app")
- Slot was archived or deleted
- Confusion between similar slot names

**Prevention:**
- Use consistent naming conventions
- Keep a list of active project slot names
- Use descriptive names that are easy to remember
- Regularly review `memcord_list` to stay oriented

---

## Search and Query Issues

### Issue: No Search Results Found

**Problem:** Search returns no results for terms you know exist in your memory.

**Symptoms:**
```
No results found for: 'database optimization'
```

**Solution:**
1. **Try broader search terms:**
   ```bash
   # Instead of specific terms
   memcord_search query="database"
   # Or try synonyms
   memcord_search query="DB OR database OR MySQL OR PostgreSQL"
   ```

2. **Check for typos and alternative spellings:**
   ```bash
   memcord_search query="optimization OR optimisation"
   ```

3. **Use natural language query instead:**
   ```bash
   memcord_query question="What did I learn about making databases faster?"
   ```

4. **Remove restrictive filters:**
   ```bash
   # Remove tag filters that might be too restrictive
   memcord_search query="database" 
   # Instead of
   memcord_search query="database" include_tags=["very_specific_tag"]
   ```

5. **Check if content might be archived:**
   ```bash
   memcord_archive action="list"
   ```

**Prevention:**
- Include synonyms when saving content
- Use consistent terminology for important concepts
- Add descriptive tags to improve searchability
- Test searchability immediately after saving important content

---

### Issue: Too Many Irrelevant Search Results

**Problem:** Search returns many results but most aren't relevant to what you're looking for.

**Symptoms:**
- High number of results with low relevance scores (< 0.5)
- Results contain your search terms but in wrong context
- Mixed content from unrelated projects or topics

**Solution:**
1. **Use more specific search terms:**
   ```bash
   # Instead of broad terms
   memcord_search query="React authentication error handling"
   # Instead of just
   memcord_search query="error"
   ```

2. **Add Boolean operators to narrow results:**
   ```bash
   memcord_search query="database AND performance NOT tutorial"
   ```

3. **Use tag filters to focus on relevant content:**
   ```bash
   memcord_search query="authentication" include_tags=["current_project", "backend"]
   ```

4. **Use exact phrases for specific information:**
   ```bash
   memcord_search query='"connection timeout error"'
   ```

5. **Reduce max_results to focus on most relevant:**
   ```bash
   memcord_search query="your terms" max_results=5
   ```

**Prevention:**
- Use consistent tagging for related content
- Save content with clear context and specific terminology
- Organize related content in appropriate memory slots
- Use groups and tags to separate different types of content

---

## Content Management Issues

### Issue: Can't Find Previously Saved Content

**Problem:** You know you saved something important but can't locate it.

**Symptoms:**
- Search returns no results for terms you remember using
- Content doesn't appear in expected memory slot
- Uncertainty about which slot contains the information

**Solution:**
1. **Search across all memory with broad terms:**
   ```bash
   memcord_search query="key terms you remember" max_results=20
   ```

2. **Try different search approaches:**
   ```bash
   # Try synonyms and related terms
   memcord_search query="API OR endpoint OR service OR backend"
   
   # Use natural language query
   memcord_query question="Where did I save information about API security?"
   ```

3. **Check recent activity across all slots:**
   ```bash
   memcord_list
   # Look for slots updated around the time you remember saving
   ```

4. **Browse potentially relevant slots manually:**
   ```bash
   memcord_read slot_name="suspected_slot_name"
   ```

5. **Check archived content:**
   ```bash
   memcord_archive action="list"
   ```

**Investigation Checklist:**
- [ ] Tried multiple search terms and synonyms
- [ ] Used both `memcord_search` and `memcord_query`
- [ ] Checked `memcord_list` for recently updated slots
- [ ] Manually browsed most likely memory slots
- [ ] Searched archived content if applicable
- [ ] Considered if content might be in zero mode (not saved)

**Prevention:**
- Save important content immediately when discussed
- Use descriptive context when saving
- Test searchability right after saving
- Use consistent terminology for important concepts
- Tag content with searchable labels

---

### Issue: Memory Slots Getting Too Large and Unwieldy

**Problem:** Memory slots have grown very large, making them hard to navigate and slow to load.

**Symptoms:**
- `memcord_read` returns overwhelming amounts of content
- Long load times for memory operations
- Difficulty finding specific information within slots
- High character counts in `memcord_list` (>10,000 characters)

**Solution:**
1. **Use entry selection to navigate large slots:**
   ```bash
   # Get recent entries only
   memcord_select_entry relative_time="latest"
   
   # Get specific time periods
   memcord_select_entry relative_time="2 hours ago"
   ```

2. **Search within specific slots:**
   ```bash
   # This searches only within specific slots if you include tags
   memcord_search query="specific topic" include_tags=["large_slot_tag"]
   ```

3. **Compress old content:**
   ```bash
   # Analyze compression potential
   memcord_compress slot_name="large_slot" action="analyze"
   
   # Compress if beneficial
   memcord_compress slot_name="large_slot" action="compress"
   ```

4. **Split large slots by topic or time:**
   ```bash
   # Create new focused slots
   memcord_name slot_name="proj_main_frontend"
   memcord_name slot_name="proj_main_backend"
   
   # Manually move relevant content to new slots
   # (Copy specific entries from large slot to new slots)
   ```

5. **Archive old sections if no longer actively needed:**
   ```bash
   memcord_archive slot_name="old_project_phase" action="archive"
   ```

**Prevention:**
- Create separate slots for different aspects of large projects
- Use `memcord_save_progress` with summarization for regular updates
- Regularly review and organize growing slots
- Archive completed phases or old versions

---

## Tool-Specific Issues

### Issue: memcord_merge Preview Shows Unexpected Results

**Problem:** Merge preview doesn't match your expectations for content combination.

**Symptoms:**
- More or fewer duplicates detected than expected
- Content ordering doesn't match your preferences  
- Tags or groups not merged as anticipated

**Solution:**
1. **Adjust similarity threshold:**
   ```bash
   # More aggressive duplicate detection
   memcord_merge source_slots=["slot1", "slot2"] target_slot="merged" action="preview" similarity_threshold=0.9
   
   # Less aggressive duplicate detection
   memcord_merge source_slots=["slot1", "slot2"] target_slot="merged" action="preview" similarity_threshold=0.6
   ```

2. **Review source slots before merging:**
   ```bash
   memcord_read slot_name="slot1"
   memcord_read slot_name="slot2"
   ```

3. **Test merge with subset first:**
   ```bash
   # Try merging just two slots first to understand behavior
   memcord_merge source_slots=["slot1", "slot2"] target_slot="test_merge" action="preview"
   ```

**Understanding Merge Behavior:**
- Content is ordered chronologically across all source slots
- Similarity threshold of 0.8 works well for most content
- Higher thresholds (0.9) are more selective about duplicates
- Lower thresholds (0.6-0.7) catch more subtle duplicates
- Always use preview mode first to understand results

---

### Issue: memcord_import Fails or Returns Errors

**Problem:** Content import from external sources fails or produces unexpected results.

**Common Import Errors:**
```
Import failed: Unable to access file path
Import failed: Unsupported file format
Import failed: Content too large to process
```

**Solution:**
1. **Verify file path and permissions:**
   ```bash
   # Use absolute path
   memcord_import source="/full/path/to/file.txt" slot_name="imported_content"
   
   # Check file exists and is readable
   ls -la /path/to/file.txt
   ```

2. **Check supported formats:**
   - Text files (.txt)
   - PDF files (.pdf)  
   - JSON files (.json)
   - CSV files (.csv)
   - Web URLs (http/https)

3. **Handle large files:**
   ```bash
   # Break large files into smaller sections
   # Or compress before importing
   ```

4. **Import with specific source type:**
   ```bash
   memcord_import source="file.pdf" slot_name="docs" source_type="pdf"
   ```

**Prevention:**
- Use absolute file paths
- Verify file formats are supported
- Test import with small files first
- Ensure proper file permissions

---

## Performance and Storage Issues

### Issue: Slow Tool Response Times

**Problem:** Memcord tools are responding slowly or timing out.

**Symptoms:**
- Long delays before tool responses
- Timeout errors during operations
- Overall sluggish performance

**Solution:**
1. **Check memory usage and storage:**
   ```bash
   memcord_list
   # Look for very large slots (>50,000 characters)
   ```

2. **Compress large memory slots:**
   ```bash
   memcord_compress action="analyze"
   memcord_compress slot_name="large_slot" action="compress"
   ```

3. **Archive inactive content:**
   ```bash
   memcord_archive action="candidates" days_inactive=30
   # Archive old content that's no longer actively used
   ```

4. **Limit search result sizes:**
   ```bash
   memcord_search query="terms" max_results=10
   # Instead of default 20 results
   ```

**Performance Optimization:**
- Keep individual memory slots focused and reasonably sized
- Archive old projects that aren't actively used
- Use compression for historical content
- Regularly clean up test or temporary slots

---

## Quick Diagnostic Commands

When troubleshooting any issue, these commands provide useful diagnostic information:

```bash
# Check overall memory status
memcord_list

# Verify current slot and zero mode status  
memcord_list | head -5

# Test basic functionality
memcord_search query="test" max_results=3

# Check for archived content
memcord_archive action="stats"

# Review recent activity
memcord_select_entry relative_time="latest"

# Storage usage analysis
memcord_compress action="analyze"
```

## Getting Help

If these solutions don't resolve your issue:

1. **Check the specific tool documentation** in `/docs/enhanced-tool-docs/`
2. **Try the troubleshooting workflows** in `/docs/troubleshooting-guides/`
3. **Review usage examples** in `/docs/usage-examples/`
4. **Test with minimal examples** to isolate the problem
5. **Document the issue** for future reference once resolved