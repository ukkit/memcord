# memcord_search - Advanced Memory Search

## Overview
**Category:** Search  
**Purpose:** Full-text search across memory slots with advanced filtering  
**Prerequisites:** Memory slots with saved content

## Detailed Description
Performs comprehensive full-text search across all your memory slots with support for Boolean operators (AND, OR, NOT), tag filtering, case sensitivity options, and result ranking by relevance. This is your primary tool for finding specific information across all your saved conversations and knowledge.

The search engine indexes all saved content and provides ranked results with relevance scores, making it easy to find the most pertinent information quickly.

## Usage Examples

### Example 1: Simple Keyword Search
**Scenario:** Find all references to database optimization  
**Command:**
```bash
memcord_search query="database optimization"
```
**Expected Result:** Ranked list of memory slots containing "database optimization" with relevance scores and context snippets
**Follow-up:** Use `memcord_read slot_name="result_slot"` to review full content

### Example 2: Boolean Search with Multiple Terms
**Scenario:** Find discussions about APIs but exclude deprecated information  
**Command:**
```bash
memcord_search query="API AND authentication NOT deprecated" max_results=10
```
**Expected Result:** 10 most relevant results about API authentication, excluding any content mentioning "deprecated"
**Follow-up:** Use `memcord_select_entry` to access specific entries from results

### Example 3: Tag-Filtered Search
**Scenario:** Find technical content excluding meetings  
**Command:**
```bash
memcord_search query="performance optimization" include_tags=["technical", "research"] exclude_tags=["meetings", "archived"] case_sensitive=false
```
**Expected Result:** Performance optimization discussions from technical and research content, excluding meetings and archived material
**Follow-up:** Apply similar tags to new related content for better organization

### Example 4: Targeted Project Search
**Scenario:** Find specific error solutions within project-related content  
**Command:**
```bash
memcord_search query="error handling AND async" include_tags=["project_alpha"] max_results=5
```
**Expected Result:** Top 5 results about error handling and async programming specific to project_alpha
**Follow-up:** Use `memcord_merge` to consolidate related error handling discussions

## Common Use Cases
- **Solution Retrieval:** Find previously discussed solutions to similar problems
- **Knowledge Discovery:** Locate related information across different conversation contexts
- **Research Analysis:** Find patterns and connections in saved research
- **Project History:** Track decisions and discussions within specific projects
- **Learning Review:** Revisit topics you've learned about in the past
- **Client Information:** Find specific details from client communications
- **Technical Reference:** Quickly locate technical specifications or configurations

## Parameters
- **query** (required): Search terms and Boolean operators
  - Supports AND, OR, NOT operators
  - Use quotes for exact phrases: `"exact phrase"`
  - Case-insensitive by default
- **include_tags** (optional): Only search slots with these tags
  - Array of tag names
  - Must match at least one tag to be included
- **exclude_tags** (optional): Exclude slots with these tags
  - Array of tag names  
  - Excludes slots that have any of these tags
- **max_results** (optional): Maximum number of results (default: 20, max: 100)
- **case_sensitive** (optional): Enable case-sensitive search (default: false)

## Search Operators & Syntax

### Boolean Operators
- **AND:** Both terms must be present
  - `API AND authentication`
- **OR:** Either term can be present  
  - `React OR Vue OR Angular`
- **NOT:** Exclude terms containing this word
  - `database NOT MySQL`

### Phrase Search
- **Exact Phrases:** Use quotes for exact matching
  - `"machine learning algorithm"`
  - `"error message: connection timeout"`

### Complex Queries
- **Grouping:** Combine operators logically
  - `(React OR Vue) AND (state management)`
  - `database AND (optimization OR performance) NOT deprecated`

## Search Result Interpretation

### Relevance Scoring
- **1.0:** Perfect match (contains all search terms prominently)
- **0.8-0.9:** High relevance (most search terms present)
- **0.6-0.7:** Moderate relevance (some search terms present)
- **0.3-0.5:** Low relevance (few search terms or less prominent)
- **< 0.3:** Minimal relevance (tangential matches)

### Result Information
- **Slot Name:** Memory slot containing the match
- **Relevance Score:** How well the content matches your query
- **Match Type:** Where the match was found (content, title, tags, etc.)
- **Timestamp:** When the content was saved
- **Snippet:** Preview of the matching content with context
- **Tags:** Associated tags for context
- **Group Path:** Organizational hierarchy if applicable

## Troubleshooting

### Problem: No results found for common terms
**Solution:** 
- Try broader search terms or synonyms
- Check spelling of search terms
- Remove restrictive tag filters
- Use OR operator to expand search: `database OR DB`
**Prevention:** Include synonyms and related terms when saving content

### Problem: Too many irrelevant results
**Solution:**
- Use AND operator to narrow search: `database AND optimization`
- Add exclude terms with NOT: `database NOT tutorial`
- Use tag filters to focus on relevant content types
- Use exact phrases with quotes: `"specific error message"`
**Prevention:** Use consistent terminology and good tagging practices

### Problem: Can't find content you know exists
**Solution:**
- Try different search terms or synonyms
- Check if content is in archived slots
- Use `memcord_list` to verify slot names and recent updates
- Try `memcord_query` for conceptual searches
**Verification:** Use `memcord_read` on suspected slots to manually verify

### Problem: Search results don't show full context
**Solution:**
- Use `memcord_read slot_name="result_slot"` to see full content
- Use `memcord_select_entry` to access specific entries with context
- Lower max_results to focus on most relevant matches
**Context:** Search shows snippets; full content requires separate read commands

## Tips & Tricks

💡 **Start Broad, Then Narrow:** Begin with simple terms, then add AND operators and filters to narrow results

💡 **Use Synonyms:** Include alternative terms - search for both "bug" and "error", "UI" and "interface"

💡 **Test Search Terms:** When saving content, include searchable keywords you might use later

💡 **Leverage Tags:** Use include_tags and exclude_tags to focus searches on relevant content categories

💡 **Check Relevance Scores:** Focus on results with scores > 0.7 for most accurate matches

💡 **Combine with Query:** Use `memcord_search` for specific terms, `memcord_query` for conceptual questions

## Advanced Search Strategies

### Project-Specific Research
```bash
# Find all error handling in current project
memcord_search query="error OR exception OR catch" include_tags=["current_project"]

# Find performance issues excluding resolved ones
memcord_search query="performance AND (slow OR lag OR bottleneck)" exclude_tags=["resolved"]
```

### Cross-Topic Discovery
```bash
# Find connections between different technologies
memcord_search query="React AND (database OR API OR backend)"

# Research pattern discovery
memcord_search query="design pattern" include_tags=["architecture", "planning"]
```

### Historical Analysis
```bash
# Find decisions made in the past
memcord_search query="decided OR decision OR chose" include_tags=["meetings", "planning"]

# Track evolution of ideas
memcord_search query="version OR update OR change" case_sensitive=false
```

## Related Tools
- **memcord_query** - Natural language questions about your memories
- **memcord_read** - Get full content from search results  
- **memcord_select_entry** - Access specific entries from search results
- **memcord_tag** - Improve searchability by adding relevant tags
- **memcord_list** - Overview of available content to search

## Workflow Integration

### Research Workflow
1. **memcord_search** with broad terms to discover relevant content
2. **memcord_read** to review full context of promising results
3. **memcord_save** new insights that build on found information
4. **memcord_tag** to improve organization and future searchability

### Problem-Solving Workflow
1. **memcord_search** for similar problems or error messages
2. **memcord_select_entry** to get specific solutions with context
3. Apply and adapt solutions to current problem
4. **memcord_save** the successful solution for future reference

### Knowledge Building Workflow  
1. **memcord_search** to find related existing knowledge
2. **memcord_query** to ask conceptual questions about the topic
3. **memcord_save_progress** to add new learning in context
4. **memcord_merge** related learning sessions if beneficial

## Performance Optimization

### Search Efficiency
- Use specific terms when possible rather than very broad searches
- Limit max_results for faster response when you need just a few matches
- Use tag filters to reduce the search space
- Cache frequently used search queries mentally for quick access

### Content Organization for Better Search
- Use consistent terminology across related content
- Add descriptive tags that reflect searchable concepts
- Include key terms in saved content naturally
- Create cross-references between related topics