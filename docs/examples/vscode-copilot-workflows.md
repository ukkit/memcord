# VSCode and GitHub Copilot Workflows

Real-world examples of using memcord with GitHub Copilot agent mode in VSCode.

## Table of Contents

- [Getting Started](#getting-started)
- [Project Memory Workflows](#project-memory-workflows)
- [Code Review Workflows](#code-review-workflows)
- [Architecture Decision Workflows](#architecture-decision-workflows)
- [Bug Investigation Workflows](#bug-investigation-workflows)
- [Team Knowledge Sharing](#team-knowledge-sharing)
- [Search and Query Patterns](#search-and-query-patterns)
- [Advanced Workflows](#advanced-workflows)

---

## Getting Started

### Basic Copilot Interaction Pattern

All memcord operations in VSCode use GitHub Copilot agent mode. Start your prompts with `@workspace` to activate the agent.

**Example:**
```
User: @workspace Create a memory slot for this project
Copilot: [Uses memcord_name tool to create slot]
```

### Understanding Agent Mode

When you use `@workspace`, Copilot:
1. Analyzes your natural language request
2. Determines which memcord tools to use
3. Executes the tools with appropriate parameters
4. Returns results in conversational format

You don't need to know exact tool names or parameters - just describe what you want in natural language.

---

## Project Memory Workflows

### Workflow 1: Starting a New Project

**Goal:** Create project-specific memory and save initial context.

**Conversation:**
```
User: @workspace I'm starting a new API project called "payment-gateway".
      Create a memcord slot for it and save our initial requirements

Copilot: I'll create a memory slot for your payment-gateway project.

User: The requirements are:
      - REST API for payment processing
      - Support Stripe and PayPal
      - PCI compliance required
      - Node.js + Express backend

Copilot: [Saves content to payment-gateway slot]
         I've saved your initial requirements to the payment-gateway memory slot.
```

**What Happened:**
- `memcord_name "payment-gateway"` - Created new slot
- `memcord_save` - Saved requirements text

---

### Workflow 2: Continuing Previous Work

**Goal:** Resume work on an existing project by loading context.

**Conversation:**
```
User: @workspace I'm back to work on the payment-gateway project.
      What were we working on?

Copilot: [Uses memcord_use and memcord_read]
         Looking at your payment-gateway memories...

         You were working on:
         - REST API design with Stripe and PayPal integration
         - PCI compliance requirements
         - Setting up Node.js + Express backend

         Last discussion was about API endpoint structure.
```

**What Happened:**
- `memcord_use "payment-gateway"` - Activated the slot
- `memcord_read` - Retrieved stored content

---

### Workflow 3: Saving Progress Automatically

**Goal:** Let Copilot auto-summarize and save the conversation.

**Conversation:**
```
User: @workspace We just finished designing the payment webhook endpoints.
      Save our progress with a summary

Copilot: [Uses memcord_save_progress]
         I've summarized and saved our conversation:

         Summary: "Designed webhook endpoints for payment events including
         payment.succeeded, payment.failed, and refund.processed. Decided
         on HMAC-SHA256 signature verification for security."

         Entry added to payment-gateway slot.
```

**What Happened:**
- `memcord_save_progress` - AI-generated summary appended to slot

---

## Code Review Workflows

### Workflow 4: Saving Code Review Decisions

**Goal:** Document decisions made during code reviews.

**Conversation:**
```
User: @workspace Create a code-review-notes slot for our team

Copilot: [Creates slot]

User: @workspace Save this code review decision:
      "PR #123 - Authentication refactor
      Decided to use JWT tokens with 15-minute expiry
      Refresh tokens stored in HttpOnly cookies
      Approved by @john and @sarah"

Copilot: [Saves to code-review-notes]
         Saved code review decision for PR #123.
```

**Later...**
```
User: @workspace What did we decide about authentication tokens?

Copilot: [Uses memcord_query]
         Based on your code review notes:

         You decided to use JWT tokens with 15-minute expiry,
         with refresh tokens stored in HttpOnly cookies.
         This was approved in PR #123 by @john and @sarah.
```

**What Happened:**
- `memcord_name` - Created code-review-notes slot
- `memcord_save` - Saved review decision
- `memcord_query` - Natural language search later

---

### Workflow 5: Tracking Technical Debt

**Goal:** Maintain a running log of technical debt decisions.

**Conversation:**
```
User: @workspace Use the tech-debt slot

Copilot: [Activates tech-debt slot]

User: @workspace Add this item:
      "Payment retry logic needs refactoring. Currently using exponential
      backoff but should implement circuit breaker pattern. Ticket: PAY-456"

Copilot: [Saves entry]

User: @workspace Show me all circuit breaker related tech debt

Copilot: [Uses memcord_search with "circuit breaker"]
         Found 1 item:
         - Payment retry logic needs circuit breaker pattern (PAY-456)
```

**What Happened:**
- `memcord_use "tech-debt"` - Switched to existing slot
- `memcord_save` - Added new entry
- `memcord_search "circuit breaker"` - Filtered search

---

## Architecture Decision Workflows

### Workflow 6: Documenting Architecture Decisions

**Goal:** Create an Architecture Decision Record (ADR) in memcord.

**Conversation:**
```
User: @workspace Create an architecture-decisions slot

Copilot: [Creates slot]

User: @workspace Save this ADR:
      "ADR-001: Database Selection

      Decision: PostgreSQL for transactional data

      Context: Need ACID guarantees for payment transactions

      Considered: MySQL, PostgreSQL, MongoDB

      Rationale: PostgreSQL offers better JSON support, strong consistency,
      and proven track record in financial applications.

      Consequences: Team needs PostgreSQL training, hosting costs $200/month"

Copilot: [Saves ADR]
         ADR-001 saved to architecture-decisions slot.
```

**Retrieving Later:**
```
User: @workspace Why did we choose PostgreSQL over MySQL?

Copilot: [Uses memcord_query]
         According to ADR-001:

         PostgreSQL was chosen for better JSON support, strong ACID consistency,
         and proven track record in financial applications. MySQL was considered
         but PostgreSQL's features were a better fit for payment transactions.
```

**What Happened:**
- `memcord_name` - Created ADR slot
- `memcord_save` - Saved structured decision
- `memcord_query` - Natural language retrieval

---

### Workflow 7: Comparing Past Decisions

**Goal:** Search across multiple architecture decisions.

**Conversation:**
```
User: @workspace Search architecture-decisions for all database-related ADRs

Copilot: [Uses memcord_search]
         Found 3 database-related decisions:

         1. ADR-001: PostgreSQL for transactional data
         2. ADR-005: Redis for caching layer
         3. ADR-012: Elasticsearch for search functionality
```

**What Happened:**
- `memcord_search "database"` - Full-text search with keyword

---

## Bug Investigation Workflows

### Workflow 8: Tracking Bug Investigation

**Goal:** Document debugging process and findings.

**Conversation:**
```
User: @workspace Create a bug-investigations slot

Copilot: [Creates slot]

User: @workspace I'm investigating why payments are failing intermittently.
      Save this timeline:

      10:00 AM - First report of failed payment (order #8374)
      10:15 AM - Found 15 more failures in last hour
      10:30 AM - All failures have same error: "timeout connecting to Stripe"
      10:45 AM - Network logs show DNS resolution issues
      11:00 AM - Root cause: DNS server was rate-limiting us

Copilot: [Uses memcord_save_progress]
         Saved bug investigation with timeline.
         Summary: "Payment failures caused by DNS rate-limiting"
```

**Next Day:**
```
User: @workspace What was the root cause of yesterday's payment failures?

Copilot: [Uses memcord_query]
         Yesterday's payment failures were caused by DNS server rate-limiting,
         which led to timeouts connecting to Stripe.
```

**What Happened:**
- `memcord_name` - Created investigation slot
- `memcord_save_progress` - Auto-summarized timeline
- `memcord_query` - Retrieved cause with natural language

---

### Workflow 9: Linking Related Bugs

**Goal:** Merge related bug investigations.

**Conversation:**
```
User: @workspace Merge bug-investigations and incident-reports into
      all-incidents slot

Copilot: [Uses memcord_merge]
         Analyzing slots for duplicates...

         Merged 2 slots into all-incidents:
         - 12 unique entries
         - 3 duplicates removed
         - Chronological order preserved
```

**What Happened:**
- `memcord_merge ["bug-investigations", "incident-reports"] "all-incidents"` - Intelligent merge with deduplication

---

## Team Knowledge Sharing

### Workflow 10: Sharing Meeting Notes

**Goal:** Export memory for team distribution.

**Conversation:**
```
User: @workspace Export the sprint-planning slot as markdown

Copilot: [Uses memcord_export]
         Exported sprint-planning to: memory_slots/sprint-planning.md

         You can share this file with your team.
```

**What Happened:**
- `memcord_export "sprint-planning" "markdown"` - Exported as shareable file

---

### Workflow 11: Importing Team Knowledge

**Goal:** Import documentation from various sources.

**Conversation:**
```
User: @workspace Import our API documentation from docs/api-guide.pdf
      into the team-knowledge slot

Copilot: [Uses memcord_import]
         Imported API documentation from PDF.
         Added 47 pages to team-knowledge slot.
```

**What Happened:**
- `memcord_import "docs/api-guide.pdf" "team-knowledge"` - PDF content extraction and import

---

## Search and Query Patterns

### Workflow 12: Boolean Search

**Goal:** Complex search with multiple terms.

**Conversation:**
```
User: @workspace Search for conversations about "authentication" AND "security"
      but NOT "OAuth"

Copilot: [Uses memcord_search with Boolean operators]
         Found 8 conversations matching your criteria:

         1. JWT implementation discussion
         2. API key rotation strategy
         3. Session management design
         ...
```

**What Happened:**
- `memcord_search "authentication AND security NOT OAuth"` - Boolean operators

---

### Workflow 13: Temporal Queries

**Goal:** Find information from specific time periods.

**Conversation:**
```
User: @workspace What database decisions did we make last month?

Copilot: [Uses memcord_query with temporal filtering]
         In the past month, you made these database decisions:

         1. Chose PostgreSQL for transactional data (3 weeks ago)
         2. Added Redis caching layer (2 weeks ago)
         3. Implemented connection pooling (1 week ago)
```

**What Happened:**
- `memcord_query` with temporal constraint detection - "last month" parsed automatically

---

### Workflow 14: Tag-Based Filtering

**Goal:** Search within tagged categories.

**Conversation:**
```
User: @workspace Search for security-tagged memories about API design

Copilot: [Uses memcord_search with tag filter]
         Found 5 security-related API design discussions:

         1. Rate limiting strategy
         2. Authentication header format
         3. CORS configuration
         ...
```

**What Happened:**
- `memcord_search` with tag filtering (requires advanced mode)

---

## Advanced Workflows

### Workflow 15: Privacy Mode

**Goal:** Discuss sensitive information without saving.

**Conversation:**
```
User: @workspace Enable zero mode - I need to discuss something confidential

Copilot: [Uses memcord_zero]
         Zero mode activated. Nothing will be saved until you switch slots.

User: [Discusses sensitive salary information]

Copilot: [No saving occurs]

User: @workspace Switch back to the payment-gateway slot

Copilot: [Uses memcord_use "payment-gateway"]
         Switched to payment-gateway. Auto-saving resumed.
```

**What Happened:**
- `memcord_zero` - Activated privacy mode
- `memcord_use` - Deactivated privacy mode by switching slots

---

### Workflow 16: Timeline Navigation

**Goal:** Review specific points in conversation history.

**Conversation:**
```
User: @workspace Show me what we discussed 2 hours ago about API endpoints

Copilot: [Uses memcord_select_entry "2 hours ago"]
         2 hours ago, you were discussing webhook endpoint structure:

         "Designed webhook endpoints for payment events including
         payment.succeeded, payment.failed..."
```

**What Happened:**
- `memcord_select_entry "2 hours ago"` - Relative time navigation

---

### Workflow 17: Storage Optimization

**Goal:** Compress old memories to save space.

**Conversation:**
```
User: @workspace Analyze compression opportunities for old-project slot

Copilot: [Uses memcord_compress analyze]
         Compression analysis for old-project:

         Current size: 2.4 MB
         Compressed size: 0.6 MB (75% reduction)
         Estimated savings: 1.8 MB

User: @workspace Compress it

Copilot: [Uses memcord_compress compress]
         Compressed old-project slot.
         Saved 1.8 MB of disk space.
```

**What Happened:**
- `memcord_compress "old-project" "analyze"` - Preview compression
- `memcord_compress "old-project" "compress"` - Apply compression

---

### Workflow 18: Archiving Inactive Projects

**Goal:** Archive completed projects for long-term storage.

**Conversation:**
```
User: @workspace Archive the completed-mvp slot

Copilot: [Uses memcord_archive]
         Archived completed-mvp slot:

         Moved to: archives/completed-mvp/
         Reason: Project completed
         Can be restored anytime with memcord_archive restore
```

**What Happened:**
- `memcord_archive "completed-mvp" "archive"` - Moved to long-term storage

---

## Best Practices

### 1. Use Descriptive Slot Names

**Good:**
- `payment-api-redesign`
- `security-audit-2026`
- `onboarding-john-smith`

**Avoid:**
- `project1`
- `stuff`
- `temp`

### 2. Save Progress Regularly

Use `memcord_save_progress` after significant discussions:
```
@workspace Save our progress on the authentication design
```

### 3. Create Topical Slots

Separate concerns into dedicated slots:
- `architecture-decisions`
- `code-reviews`
- `bug-investigations`
- `team-meetings`

### 4. Use Natural Language

Copilot understands conversational requests:
- "Create a memory for this project"
- "What did we decide about databases?"
- "Find all security-related discussions"

### 5. Enable Advanced Mode for Teams

Set in `.vscode/mcp.json`:
```json
{
  "env": {
    "MEMCORD_ENABLE_ADVANCED": "true"
  }
}
```

Unlocks:
- Tag management
- Import/export
- Compression
- Archival

---

## Troubleshooting Common Scenarios

### Copilot Can't Find Memcord Tools

**Try:**
```
User: @workspace List available MCP servers

Copilot: [Shows if memcord is configured]
```

If not listed, check `.vscode/mcp.json` configuration.

---

### Tool Calls Timing Out

**Try:**
```
User: @workspace Show me a quick summary from architecture-decisions

Copilot: [Faster than reading full slot]
```

Use queries instead of reading large slots entirely.

---

### Need to See Raw Data

**Open slot file directly:**
```
memory_slots/project-name.json
```

All data is stored as readable JSON.

---

## Next Steps

- **[VSCode Setup Guide](../vscode-setup.md)** - Installation and configuration
- **[Tools Reference](../tools-reference.md)** - Complete tool documentation
- **[Security Guide](../security-vscode.md)** - Security best practices

---

**Tips:**
- Experiment with natural language - Copilot is flexible
- Use `@workspace` prefix for all memcord operations
- Check VSCode logs if tools aren't working: `Developer: Show Logs` → "MCP"

---

**Last Updated:** January 2026
