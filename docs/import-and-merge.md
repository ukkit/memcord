# Import & Merge Guide

Comprehensive guide for Phase 3 features: importing content from various sources and merging memory slots with intelligent duplicate detection.

## Table of Contents

1. [Content Import System](#content-import-system)
2. [Memory Slot Merging](#memory-slot-merging)
3. [Supported File Formats](#supported-file-formats)
4. [Import Strategies](#import-strategies)
5. [Merge Strategies](#merge-strategies)
6. [Best Practices](#best-practices)
7. [Troubleshooting](#troubleshooting)

## Content Import System

### Overview

The `memcord_import` tool enables importing content from various sources into memory slots, expanding beyond manual text entry to support:

- **Text Files**: Markdown, plain text, documentation
- **PDF Documents**: Research papers, reports, manuals
- **Web Content**: Articles, blog posts, documentation pages
- **Structured Data**: CSV datasets, JSON configurations

### Basic Import Syntax

```bash
memcord_import source="<source_path_or_url>" [options]
```

**Required Parameters:**
- `source`: File path, URL, or data source

**Optional Parameters:**
- `slot_name`: Target memory slot (uses current slot if not specified)
- `description`: Descriptive text for the imported content
- `tags`: Array of tags for categorization
- `group_path`: Hierarchical organization path

### Import Examples

#### Text File Import
```bash
# Import markdown documentation
memcord_import source="./project-docs/README.md" slot_name="project_readme" tags=["docs","readme"] group_path="projects/alpha"

# Import meeting notes
memcord_import source="/notes/meeting_2025_01_15.txt" slot_name="meeting_notes" description="Weekly standup notes" tags=["meeting","standup"]
```

#### PDF Document Import
```bash
# Import research paper
memcord_import source="/research/paper.pdf" slot_name="research_lit" tags=["research","pdf","literature"] description="Key research paper on ML"

# Import technical manual
memcord_import source="./manuals/api_guide.pdf" slot_name="api_docs" tags=["manual","api","reference"] group_path="documentation/api"
```

#### Web Content Import
```bash
# Import blog article
memcord_import source="https://example.com/best-practices-guide" slot_name="best_practices" tags=["web","guide"] description="Industry best practices"

# Import documentation page
memcord_import source="https://docs.framework.com/getting-started" slot_name="framework_docs" tags=["docs","web","tutorial"] group_path="learning/frameworks"
```

#### Structured Data Import
```bash
# Import CSV dataset
memcord_import source="/data/sales_q1_2025.csv" slot_name="sales_data" tags=["data","csv","sales"] description="Q1 2025 sales metrics"

# Import JSON configuration
memcord_import source="./config/app_settings.json" slot_name="app_config" tags=["config","json"] group_path="configurations/app"
```

### Import Metadata

Every import automatically includes rich metadata:

```markdown
=== IMPORTED CONTENT ===
Source: /path/to/file.pdf
Type: pdf
Imported: 2025-01-15T10:30:00
Description: Research paper on machine learning
========================

[Original content follows...]
```

## Memory Slot Merging

### Overview

The `memcord_merge` tool consolidates multiple memory slots into a single, organized slot with:

- **Duplicate Detection**: Configurable similarity thresholds
- **Chronological Ordering**: Timeline-based content organization
- **Metadata Consolidation**: Combined tags and groups
- **Preview Mode**: See results before execution

### Basic Merge Syntax

```bash
memcord_merge source_slots=["slot1","slot2"] target_slot="merged_slot" [options]
```

**Required Parameters:**
- `source_slots`: Array of memory slots to merge (minimum 2)
- `target_slot`: Name for the merged result

**Optional Parameters:**
- `action`: `preview` (default) or `merge`
- `similarity_threshold`: 0.0-1.0 (default 0.8)
- `delete_sources`: true/false (default false)

### Merge Workflow

#### 1. Preview Phase
```bash
# Preview merge to see statistics
memcord_merge source_slots=["meeting1","meeting2","meeting3"] target_slot="project_meetings" action="preview"
```

**Preview Output:**
```
=== MERGE PREVIEW: project_meetings ===
Source slots: meeting1, meeting2, meeting3
Total content length: 15,420 characters
Duplicate content to remove: 7 sections
Similarity threshold: 80.0%

Merged tags (8): meeting, project, alpha, weekly, standup, urgent, decisions, action-items
Merged groups (1): meetings/weekly

Chronological order:
  - meeting1: 2025-01-08 09:00:00
  - meeting2: 2025-01-15 09:00:00  
  - meeting3: 2025-01-22 09:00:00

⚠️  WARNING: Target slot 'project_meetings' already exists and will be overwritten!

Content preview:
==========================================
=== MERGED MEMORY SLOT ===
Created: 2025-01-22 14:30:00
Source Slots: meeting1, meeting2, meeting3
Total Sources: 3
=========================

--- From meeting1 (2025-01-08 09:00:00) ---
Team Standup - Jan 8, 2025
[Content follows...]
==========================================

To execute the merge, call memcord_merge again with action='merge'
```

#### 2. Execution Phase
```bash
# Execute the merge
memcord_merge source_slots=["meeting1","meeting2","meeting3"] target_slot="project_meetings" action="merge"
```

**Execution Output:**
```
✅ Successfully merged 3 slots into 'project_meetings'
Final content: 14,150 characters
Duplicates removed: 7 sections
Merged at: 2025-01-22 14:30:15

Source slots: meeting1, meeting2, meeting3
Tags merged: meeting, project, alpha, weekly, standup, urgent, decisions, action-items
Groups merged: meetings/weekly
```

### Advanced Merge Options

#### Custom Similarity Threshold
```bash
# More aggressive duplicate detection (70% similarity)
memcord_merge source_slots=["draft1","draft2"] target_slot="final_doc" action="merge" similarity_threshold=0.7

# More conservative duplicate detection (90% similarity)
memcord_merge source_slots=["notes1","notes2"] target_slot="combined_notes" action="merge" similarity_threshold=0.9
```

#### Source Cleanup
```bash
# Merge and delete source slots
memcord_merge source_slots=["temp1","temp2","temp3"] target_slot="consolidated" action="merge" delete_sources=true
```

## Supported File Formats

### Text Files
- **Extensions**: `.txt`, `.md`, `.markdown`, `.rst`, `.log`
- **Encoding**: UTF-8 (automatic detection)
- **Size Limit**: 50MB per file
- **Features**: Preserves formatting, handles large files

### PDF Documents  
- **Processing**: Page-by-page text extraction
- **Library**: `pdfplumber` for robust extraction
- **Features**: Page number headers, maintains structure
- **Limitations**: Text-based PDFs only (no OCR)

### Web Content
- **Protocols**: HTTP/HTTPS
- **Processing**: Clean article extraction with `trafilatura`
- **Features**: Removes ads/navigation, preserves main content
- **Metadata**: Page title, content type, extraction method

### Structured Data
- **JSON**: Configuration files, API responses, data exports
- **CSV/TSV**: Datasets, reports, tabular data
- **Processing**: `pandas` for robust data handling
- **Features**: Schema detection, row/column statistics

## Import Strategies

### 1. Hierarchical Organization
```bash
# Organize by project and type
memcord_import source="./docs/api.md" slot_name="api_docs" group_path="projects/alpha/documentation"
memcord_import source="./specs/requirements.pdf" slot_name="requirements" group_path="projects/alpha/specifications"
```

### 2. Thematic Tagging
```bash
# Tag by content themes
memcord_import source="article1.pdf" slot_name="research1" tags=["ai","neural-networks","deep-learning"]
memcord_import source="article2.pdf" slot_name="research2" tags=["ai","computer-vision","cnn"]
```

### 3. Batch Import Workflows
```bash
# Import multiple related files
for file in docs/*.md; do
    memcord_import source="$file" slot_name="doc_$(basename $file .md)" tags=["docs","batch"] group_path="documentation/guides"
done
```

### 4. Source Type Specialization
```bash
# Web content with source attribution
memcord_import source="https://tech-blog.com/article" slot_name="tech_trends" tags=["web","trends","external"] description="External tech trends analysis"

# Internal documentation
memcord_import source="./internal/process.md" slot_name="internal_process" tags=["internal","process","confidential"] description="Internal process documentation"
```

## Merge Strategies

### 1. Chronological Consolidation
```bash
# Merge time-series content (meetings, logs, reports)
memcord_merge source_slots=["jan_meetings","feb_meetings","mar_meetings"] target_slot="q1_meetings" action="merge"
```

### 2. Thematic Consolidation
```bash
# Merge by topic or theme
memcord_merge source_slots=["api_docs1","api_docs2","api_reference"] target_slot="complete_api_docs" action="merge"
```

### 3. Progressive Consolidation
```bash
# Multi-stage merging for large datasets
# Stage 1: Merge weekly reports
memcord_merge source_slots=["week1","week2","week3","week4"] target_slot="month1" action="merge"
memcord_merge source_slots=["week5","week6","week7","week8"] target_slot="month2" action="merge"

# Stage 2: Merge monthly summaries
memcord_merge source_slots=["month1","month2","month3"] target_slot="q1_summary" action="merge"
```

### 4. Cleanup and Archival
```bash
# Merge temporary slots and cleanup
memcord_merge source_slots=["temp_notes1","temp_notes2","temp_drafts"] target_slot="archived_content" action="merge" delete_sources=true
```

## Best Practices

### Import Best Practices

1. **Use Descriptive Slot Names**
   ```bash
   # Good
   memcord_import source="report.pdf" slot_name="q1_sales_report_2025"
   
   # Avoid
   memcord_import source="report.pdf" slot_name="report1"
   ```

2. **Apply Consistent Tagging**
   ```bash
   # Consistent taxonomy
   memcord_import source="doc.pdf" tags=["finance","quarterly","report","2025"]
   ```

3. **Organize with Group Paths**
   ```bash
   # Hierarchical organization
   memcord_import source="spec.md" group_path="projects/alpha/specifications"
   ```

4. **Add Context with Descriptions**
   ```bash
   # Descriptive context
   memcord_import source="data.csv" description="Customer survey responses Q1 2025 - 1,500 respondents"
   ```

### Merge Best Practices

1. **Always Preview First**
   ```bash
   # Preview before executing
   memcord_merge source_slots=["a","b"] target_slot="merged" action="preview"
   # Review output, then:
   memcord_merge source_slots=["a","b"] target_slot="merged" action="merge"
   ```

2. **Adjust Similarity Thresholds**
   ```bash
   # For technical docs (conservative)
   memcord_merge ... similarity_threshold=0.9
   
   # For meeting notes (aggressive)
   memcord_merge ... similarity_threshold=0.7
   ```

3. **Use Cleanup Strategically**
   ```bash
   # Only delete sources when confident
   memcord_merge ... delete_sources=true action="merge"
   ```

4. **Meaningful Target Names**
   ```bash
   # Descriptive merge targets
   memcord_merge ... target_slot="project_alpha_complete_documentation"
   ```

### Organization Best Practices

1. **Consistent Naming Conventions**
   - Use descriptive, date-stamped names
   - Follow project/team naming standards
   - Include version numbers for iterations

2. **Strategic Group Hierarchies**
   ```
   projects/
   ├── alpha/
   │   ├── documentation/
   │   ├── meetings/
   │   └── specifications/
   └── beta/
       ├── research/
       └── development/
   ```

3. **Tag Taxonomies**
   ```bash
   # Category tags: [type, priority, status, domain]
   tags=["meeting","high","active","frontend"]
   ```

## Troubleshooting

### Import Issues

#### File Not Found
```
Error: Source cannot be empty
Error: File not found: /path/to/file.pdf
```
**Solution:** Verify file path and permissions

#### Unsupported Format
```
Error: No suitable import handler found for source
```
**Solution:** Check supported formats, convert if necessary

#### Web Content Extraction Failed
```
Import failed: No content could be extracted from URL
```
**Solutions:**
- Check URL accessibility
- Verify content is text-based
- Try different URLs if paywall/login required

#### Large File Handling
```
Import failed: File too large
```
**Solutions:**
- Split large files into smaller sections
- Use compression if applicable
- Consider cloud storage with direct links

### Merge Issues

#### Insufficient Source Slots
```
Error: At least 2 source slots are required for merging
```
**Solution:** Provide minimum 2 valid slot names

#### Missing Source Slots
```
Error: Memory slots not found: slot1, slot3
```
**Solution:** Verify slot names with `memcord_list`

#### Target Slot Conflicts
```
⚠️ WARNING: Target slot 'merged' already exists and will be overwritten!
```
**Solution:** 
- Use different target name, or
- Proceed if overwrite is intentional

#### Memory/Performance Issues
```
Merge operation failed: Memory allocation error
```
**Solutions:**
- Reduce content size
- Use higher similarity threshold
- Merge in smaller batches

### Performance Optimization

#### Large Content Handling
```bash
# Use higher similarity thresholds for faster processing
memcord_merge ... similarity_threshold=0.9

# Process in smaller batches
memcord_merge source_slots=["batch1","batch2"] target_slot="intermediate1"
memcord_merge source_slots=["batch3","batch4"] target_slot="intermediate2"  
memcord_merge source_slots=["intermediate1","intermediate2"] target_slot="final"
```

#### Web Import Optimization
```bash
# Batch web imports to avoid rate limiting
for url in $urls; do
    memcord_import source="$url" ...
    sleep 2  # Rate limiting
done
```

#### Resource Management
```bash
# Cleanup after major operations
memcord_merge ... delete_sources=true  # Remove temporary slots
```

This comprehensive guide covers all aspects of using the Phase 3 import and merge features effectively. For additional help, refer to the [Tools Reference](tools-reference.md) for detailed parameter specifications and the [Examples](examples.md) for practical workflows.