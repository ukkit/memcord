# Search & Query Features

Advanced search capabilities and AI-powered query processing for intelligent memory retrieval.

## Search Engine Features

### Full-Text Search
- **Multi-field search** across slot names, tags, groups, and content
- **Relevance scoring** using TF-IDF algorithm
- **Snippet preview** showing matched content in context
- **Case-sensitive and case-insensitive** search options
- **Fast indexing** with inverted index for sub-second performance

### Boolean Search Operators
Support for complex search queries using logical operators:

- **AND**: All terms must be present
  - `"API AND database"` - finds content with both terms
- **OR**: Any term can be present  
  - `"meeting OR standup"` - finds content with either term
- **NOT**: Excludes specific terms
  - `"project NOT archived"` - finds projects excluding archived ones

### Search Filtering
- **Tag-based filtering**: Include or exclude specific tags
- **Group-based filtering**: Search within specific organizational groups
- **Result limiting**: Control maximum number of results
- **Relevance threshold**: Filter by minimum relevance score

## Natural Language Queries

### Question Classification
The system understands different types of questions:

- **What**: Content and decision queries
  - "What decisions were made about the API?"
- **Who**: Person/responsibility identification
  - "Who was responsible for the database migration?"
- **When**: Timeline and temporal queries
  - "When did we discuss the budget changes?"
- **Where**: Location and context queries
  - "Where did we document the security requirements?"
- **Why**: Reasoning and explanation queries
  - "Why was the old system deprecated?"
- **How**: Process and method queries
  - "How do we handle authentication?"

### Temporal Constraint Detection
Recognizes time-based qualifiers in queries:

- **Recent**: "recently", "lately", "new"
- **Past periods**: "last week", "last month", "yesterday"
- **Specific dates**: "in January", "Q3", "2024"
- **Relative time**: "before the launch", "after the meeting"

### Key Term Extraction
- **Stop word filtering**: Removes common words for better matching
- **Stem matching**: Handles word variations (run, running, ran)
- **Phrase recognition**: Identifies important multi-word terms
- **Context weighting**: Prioritizes terms based on question type

## Organization System

### Tagging Features
- **Multiple tags per slot** for flexible categorization
- **Hierarchical tags** using dot notation
  - Example: `"project.alpha.backend"`, `"meeting.weekly.standup"`
- **Tag-based filtering** in search and listing
- **Global tag management** with usage tracking
- **Auto-completion** suggestions for existing tags
- **Case-insensitive** storage (normalized to lowercase)

### Group Management
- **Hierarchical folder structure** for memory slots
- **Unlimited nesting** depth for complex organization
- **Path-based navigation** using forward slashes
- **Group metadata** including member count and descriptions
- **Bulk operations** on group members
- **Group-scoped search** for targeted queries

### Example Organization Structure
```
projects/
  ├── alpha/
  │   ├── meetings/     [tags: urgent, weekly]
  │   ├── development/  [tags: backend, api]
  │   └── documentation/ [tags: specs, review]
  ├── beta/
  │   ├── planning/     [tags: roadmap, timeline]
  │   └── testing/      [tags: qa, bugs]
  └── archived/         [tags: completed, old]

personal/
  ├── learning/         [tags: education, notes]
  ├── ideas/           [tags: brainstorm, future]
  └── references/      [tags: links, resources]
```

## Search Examples

### Basic Text Search
```
# Simple keyword search
memcord_search "database migration"

# Multiple keywords (AND logic)
memcord_search "API AND authentication"

# Alternative terms (OR logic) 
memcord_search "meeting OR standup OR discussion"

# Exclude terms (NOT logic)
memcord_search "project NOT archived"
```

### Advanced Filtering
```
# Search with tag inclusion
memcord_search "performance" --include-tags "urgent,critical"

# Search excluding specific tags
memcord_search "documentation" --exclude-tags "outdated,draft"

# Limit results
memcord_search "API changes" --max-results 10

# Case-sensitive search
memcord_search "DatabaseManager" --case-sensitive true
```

### Natural Language Queries
```
# Decision tracking
memcord_query "What decisions were made about the API design?"

# Responsibility identification
memcord_query "Who was assigned to handle the security audit?"

# Timeline queries
memcord_query "When did we last discuss the budget changes?"

# Status inquiries
memcord_query "What was the progress on the mobile app last month?"

# Process documentation
memcord_query "How do we handle user authentication?"

# Problem identification
memcord_query "What issues were identified during code review?"
```

## AI Enhancement Features

### Intelligent Search
- **Semantic understanding** of search queries beyond exact matches
- **Context-aware responses** that understand query intent
- **Relevance scoring** that considers content importance and recency
- **Smart snippet extraction** highlighting the most relevant portions

### Content Analysis
- **Automatic summarization** with configurable compression ratios
- **Key term extraction** for improved searchability and indexing
- **Temporal pattern recognition** in queries and content
- **Content type classification** (meetings, decisions, technical docs, etc.)

### Query Processing Pipeline
1. **Query parsing**: Extract intent, terms, and constraints
2. **Index search**: Fast retrieval of candidate documents
3. **Relevance scoring**: Rank results by importance and match quality
4. **Context extraction**: Generate relevant snippets
5. **Response formatting**: Present results with citations and metadata

## Search Performance

### Indexing Strategy
- **Inverted index** for fast term lookup
- **TF-IDF scoring** for relevance ranking
- **Incremental updates** when memory slots change
- **Memory-efficient** storage and retrieval

### Query Optimization
- **Sub-second response** times for most queries
- **Lazy loading** of large result sets
- **Result caching** for repeated queries
- **Parallel processing** for complex searches

### Scalability
- **Handles thousands** of memory slots efficiently
- **Configurable limits** to prevent resource exhaustion
- **Background indexing** for new content
- **Automatic cleanup** of outdated indexes

## Future AI Integrations

The enhanced architecture supports upcoming AI features:

- **Automatic tagging** based on content analysis
- **Smart group suggestions** for better organization
- **Content recommendations** based on usage patterns
- **Intelligent summarization** with domain-specific formats
- **Cross-memory relationship** detection and suggestions
- **Proactive search suggestions** based on current context