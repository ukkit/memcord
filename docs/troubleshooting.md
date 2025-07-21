# Troubleshooting & Support

Common issues, solutions, and debugging guidance for the Chat Memory MCP Server.

## Common Issues

### Installation & Setup Issues

#### 1. "Advanced tool 'X' is not enabled"
**Problem**: Trying to use advanced tools (tags, groups, import, export) when they're disabled.

**Solution**:
```bash
# Add to your MCP configuration environment:
"MEMCORD_ENABLE_ADVANCED": "true"

# Or check current mode by trying memcord_list_tags
# If it returns an error, advanced tools are disabled
```

**Advanced tools requiring this setting**:
- `memcord_tag`, `memcord_list_tags`, `memcord_group`
- `memcord_import`, `memcord_merge`
- `memcord_export`, `memcord_share`

#### 2. "No memory slot selected"
**Problem**: Trying to save or read memory without selecting a slot first.

**Solution**:
```bash
# Always create/select a memory slot first
memcord_name "my_project"
# Then use other memory operations
memcord_save "conversation content"
```

#### 2. "Memory slot not found"
**Problem**: Referencing a memory slot that doesn't exist.

**Solutions**:
- Check available slots: `memcord_list`
- Verify slot name spelling (case-sensitive)
- Create the slot if needed: `memcord_name "slot_name"`

#### 3. Server not starting
**Problem**: MCP server fails to launch.

**Troubleshooting steps**:
1. Check Python version: `python --version` (3.8+ required)
2. Verify installation: `uv run memcord --help`
3. Check file permissions in the project directory
4. Verify PYTHONPATH environment variable

**Common fixes**:
```bash
# Reinstall dependencies
uv pip install -e .

# Check MCP configuration
claude mcp list
claude mcp get chat-memory

# Run with debug output
PYTHONPATH=src python -m chat_memory.server --debug
```

#### 4. "Command not found: uv"
**Problem**: `uv` package manager not installed.

**Solution**:
```bash
# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Or use pip instead
pip install -e .
python -m chat_memory.server
```

### Search & Query Issues

#### 5. "No search results found"
**Problem**: Search queries return no results despite having relevant content.

**Troubleshooting**:
- Check spelling and try different keywords
- Use broader search terms
- Try natural language queries: `memcord_query "question"`
- Verify content exists: `memcord_list`

**Search tips**:
```bash
# Try different approaches
memcord_search "database"          # Single term
memcord_search "database OR db"    # Alternative terms  
memcord_search "data*"            # Partial matching
memcord_query "What about databases?" # Natural language
```

#### 6. "Search is slow"
**Problem**: Search operations take too long.

**Causes & Solutions**:
- **Large memory collection**: Search index builds on startup
- **First query**: Index may need initialization
- **Complex queries**: Use simpler terms or add filters

**Performance improvements**:
```bash
# Use tag/group filters to narrow results
memcord_search "meeting" --include-tags "urgent"
memcord_search "project" --max-results 10

# Restart server to rebuild index
claude mcp restart chat-memory
```

#### 7. "Tags not working"
**Problem**: Tag operations failing or not filtering correctly.

**Troubleshooting**:
- Ensure tags are added: `memcord_tag add "tag1 tag2"`
- Check existing tags: `memcord_list_tags`
- Remember tags are case-insensitive (stored lowercase)
- Verify tag spelling in filter commands

### Configuration Issues

#### 8. "MCP server not found in Claude Code"
**Problem**: Server not appearing in Claude Code.

**Solution**:
```bash
# Verify server is added
claude mcp list

# Add if missing
claude mcp add chat-memory uv --directory /path/to/memcord run memcord -e PYTHONPATH=/path/to/memcord/src

# Check configuration
claude mcp get chat-memory
```

#### 9. "Permission denied" errors
**Problem**: File system permission issues.

**Solutions**:
- Check directory permissions: `ls -la`
- Ensure write access to memory_slots/ directory
- Verify user ownership of project files
- Run with appropriate user permissions

#### 10. "Invalid compression ratio"
**Problem**: Summary compression fails with invalid ratio.

**Solution**:
- Use values between 0.05 and 0.5
- Default is 0.15 (15% compression)
- Examples: `memcord_save_progress "content" 0.1` (10% compression)

## Debug Mode

### Enabling Debug Output

```bash
# Run server with debug logging
PYTHONPATH=src python -m chat_memory.server --debug

# Set log level
export LOG_LEVEL=DEBUG
uv run memcord

# Check specific component
python -c "from src.chat_memory.search import SearchEngine; print('Search OK')"
```

### Debug Information

Debug mode provides:
- Detailed error messages
- Search query analysis
- Index statistics
- Performance metrics
- File operation logs

### Log File Locations

```bash
# Check system logs
tail -f ~/.local/share/claude/logs/mcp.log

# Application-specific logs (if configured)
tail -f ./logs/chat_memory.log
```

## Performance Troubleshooting

### Memory Usage Issues

**Symptoms**: High memory usage, slow operations

**Solutions**:
1. **Limit result sets**:
   ```bash
   memcord_search "query" --max-results 20
   ```

2. **Clean up large memory slots**:
   ```bash
   # Export and archive old content
   memcord_export "old_slot" "json"
   # Then delete or summarize
   ```

3. **Optimize search index**:
   ```bash
   # Restart server to rebuild index
   claude mcp restart chat-memory
   ```

### Disk Space Issues

**Symptoms**: "No space left on device" errors

**Solutions**:
1. **Check disk usage**:
   ```bash
   du -sh memory_slots/
   du -sh shared_memories/
   ```

2. **Clean up exports**:
   ```bash
   rm shared_memories/*.txt
   rm shared_memories/*.md
   # Keep JSON exports for data integrity
   ```

3. **Archive old memories**:
   ```bash
   # Move old slots to archive directory
   mkdir archive/
   mv memory_slots/old_* archive/
   ```

## Data Recovery

### Corrupted Memory Slots

**Symptoms**: JSON parsing errors, missing data

**Recovery steps**:
1. **Check for backup files**:
   ```bash
   ls memory_slots/*.backup
   ls memory_slots/*.bak
   ```

2. **Validate JSON structure**:
   ```bash
   python -m json.tool memory_slots/slot_name.json
   ```

3. **Restore from export**:
   ```bash
   # If JSON export exists
   cp shared_memories/slot_name.json memory_slots/
   ```

### Lost Search Index

**Symptoms**: No search results, index errors

**Recovery**:
```bash
# Delete index cache
rm -rf .cache/search_index.json
rm -rf .cache/term_frequencies.json

# Restart server to rebuild
claude mcp restart chat-memory
```

## Network & Connectivity

### MCP Connection Issues

**Symptoms**: Tools not available, connection timeouts

**Troubleshooting**:
1. **Check MCP server status**:
   ```bash
   claude mcp status chat-memory
   ```

2. **Restart MCP server**:
   ```bash
   claude mcp restart chat-memory
   ```

3. **Verify configuration**:
   ```bash
   claude mcp get chat-memory
   cat ~/.mcp.json  # Check project config
   ```

## Validation & Testing

### Test Server Functionality

```bash
# Test search functionality
python -c "
from src.chat_memory.search import SearchEngine
engine = SearchEngine()
print('Search engine: OK')
"

# Test query processing  
python -c "
from src.chat_memory.query import SimpleQueryProcessor
processor = SimpleQueryProcessor()
print('Query processor: OK')
"

# Validate data models
python -c "
from src.chat_memory.models import MemorySlot, SearchQuery
print('Data models: OK')
"
```

### Run Tests (if available)

```bash
# Install dev dependencies
uv pip install -e ".[dev]"

# Run test suite
pytest

# Run specific tests
pytest tests/test_search.py
pytest tests/test_storage.py
```

## Getting Help

### Before Reporting Issues

1. **Check this troubleshooting guide**
2. **Verify your setup** matches installation requirements
3. **Try debug mode** to get detailed error information
4. **Check recent changes** to your configuration

### Reporting Issues

When reporting problems, include:

1. **System information**:
   - Operating system and version
   - Python version (`python --version`)
   - uv version (`uv --version`)

2. **Error details**:
   - Complete error message
   - Debug output (if available)
   - Steps to reproduce

3. **Configuration**:
   - MCP server configuration
   - Environment variables
   - Project structure

### Support Channels

- **GitHub Issues**: For bug reports and feature requests
- **Documentation**: Check docs/ directory for detailed guides
- **Debug Output**: Use debug mode for detailed diagnostics

### Emergency Recovery

If all else fails:

1. **Backup current data**:
   ```bash
   cp -r memory_slots/ backup_$(date +%Y%m%d)/
   ```

2. **Reinstall fresh**:
   ```bash
   uv pip uninstall memcord
   uv pip install -e .
   ```

3. **Restore data**:
   ```bash
   cp backup_*/memory_slots/* memory_slots/
   ```

4. **Rebuild index**:
   ```bash
   rm -rf .cache/
   claude mcp restart chat-memory
   ```