# Usage Examples & Workflows

Practical examples and common workflows for using the Chat Memory MCP Server effectively.

> **📋 Tool Modes**: 
> - **Basic Tools** (always available): `memcord_name`, `memcord_save`, `memcord_read`, `memcord_save_progress`, `memcord_list`, `memcord_search`, `memcord_query`
> - **Advanced Tools** (require `MEMCORD_ENABLE_ADVANCED=true`): `memcord_tag`, `memcord_group`, `memcord_list_tags`, `memcord_import`, `memcord_merge`, `memcord_export`, `memcord_share`
> 
> Most examples below use advanced tools. For basic-only workflows, focus on the core memory operations.

## Basic Workflows

### 1. Project Meeting Documentation

**Scenario**: Document weekly team meetings for a software project.

```bash
# Step 1: Create organized memory slot
memcord_name "weekly_standup_2024_01_15"
memcord_tag add "meeting weekly standup urgent"
memcord_group set "meetings/weekly"

# Step 2: Save the meeting discussion
memcord_save "
Team Standup - Jan 15, 2024

Attendees: Alice, Bob, Carol
Duration: 30 minutes

Alice:
- Completed API authentication module
- Working on rate limiting implementation  
- Blocker: Need database schema approval

Bob:
- Finished frontend login component
- Started integration testing
- Next: User registration flow

Carol:
- Reviewed security documentation
- Updated deployment scripts
- Action: Schedule security audit

Decisions:
- Use JWT tokens for authentication
- Implement Redis for rate limiting
- Security audit scheduled for next week

Action Items:
- Alice: Get DB schema approval by Wed
- Bob: Complete registration by Friday  
- Carol: Book security audit vendor
"

# Step 3: Generate summary for quick reference
memcord_save_progress "Above meeting content" 0.2

# Step 4: Export for team sharing
memcord_export "weekly_standup_2024_01_15" "md"
```

### 2. Research and Knowledge Management

**Scenario**: Collecting and organizing research on different technologies.

```bash
# Research Session 1: Database Options
memcord_name "database_research"
memcord_tag add "research database technical decision"
memcord_group set "research/technical"

memcord_save "
Database Research Session

PostgreSQL:
- ACID compliance
- Strong consistency
- Complex queries with joins
- JSON support for flexibility
- Cons: Resource intensive

MongoDB:
- Document-based NoSQL
- Horizontal scaling
- Flexible schema
- Good for rapid development
- Cons: Eventual consistency

Redis:
- In-memory data store
- Excellent for caching
- Pub/sub capabilities
- Very fast reads/writes
- Cons: Data persistence concerns
"

# Research Session 2: Add new findings
memcord_name "database_research"
memcord_save_progress "
Additional research on database performance:

Benchmarks show PostgreSQL handling 10k concurrent connections efficiently.
MongoDB cluster setup requires 3+ nodes for production.
Redis persistence can be configured with AOF + RDB for durability.

Decision factors:
- Data consistency requirements
- Expected query complexity  
- Scaling needs
- Team expertise
" 0.15

# Query your research later
memcord_query "What are the pros and cons of PostgreSQL?"
memcord_query "Which database is best for caching?"
memcord_search "performance" --include-tags "research"
```

### 3. Bug Investigation and Resolution

**Scenario**: Tracking a complex bug investigation across multiple sessions.

```bash
# Initial bug report
memcord_name "auth_bug_investigation"
memcord_tag add "bug critical security authentication"
memcord_group set "bugs/critical"

memcord_save "
Bug Report #1247: Authentication Bypass

Severity: Critical
Reporter: QA Team
Date: 2024-01-15

Description:
Users can access protected routes without valid JWT tokens
Intermittent issue - occurs ~20% of requests

Initial findings:
- Only affects /api/v1/admin/* endpoints
- Token validation middleware seems to fail
- No errors in application logs
- Only happens in production environment

Investigation plan:
1. Review middleware code
2. Check token validation logic
3. Compare prod vs dev configurations
4. Add detailed logging
"

# Investigation session 1
memcord_save_progress "
Investigation Update 1:

Found issue in middleware:
- Race condition in token cache
- Multiple requests clearing cache simultaneously
- Cache miss causes fallback to 'allow' instead of 'deny'

Code review shows:
```javascript
if (!tokenCache.has(token)) {
  // BUG: Default to allow during cache rebuild
  return next(); // Should be 'return res.status(401)'
}
```

Next steps:
- Fix default behavior
- Add proper locking for cache operations
- Increase test coverage for concurrent scenarios
" 0.2

# Resolution session
memcord_save_progress "
Resolution:

1. Fixed middleware default behavior
2. Implemented proper cache locking
3. Added integration tests for concurrent auth
4. Deployed fix to staging - no issues in 48h testing

Code changes:
- middleware/auth.js: Fixed default deny behavior  
- tests/auth.test.js: Added concurrency tests
- monitoring/alerts.js: Added auth failure rate alerts

Status: RESOLVED
Verification: 1000+ production requests with 0% bypass rate
" 0.1

# Later analysis
memcord_query "What was the root cause of the authentication bug?"
memcord_query "What steps were taken to prevent this issue in the future?"
```

## Advanced Workflows

### 4. Cross-Project Knowledge Sharing

**Scenario**: Managing knowledge across multiple related projects.

```bash
# Project Alpha insights
memcord_name "project_alpha_lessons"
memcord_tag add "project alpha lessons architecture"
memcord_group set "projects/alpha/retrospective"

memcord_save "
Project Alpha - Architecture Lessons Learned

Microservices Approach:
✅ Services were well-isolated
✅ Independent deployment worked well
❌ Service discovery was complex
❌ Cross-service debugging difficult

Technology Choices:
✅ Node.js for rapid development
✅ PostgreSQL for complex queries
❌ Should have used TypeScript from start
❌ Redis clustering was overkill

Team Process:
✅ Daily standups kept everyone aligned
✅ Code reviews caught many issues
❌ Should have done more pair programming
❌ Technical debt accumulated quickly
"

# Project Beta planning
memcord_name "project_beta_planning"
memcord_tag add "project beta planning architecture"
memcord_group set "projects/beta/planning"

# Learn from previous project
memcord_query "What lessons were learned about microservices in project alpha?"
memcord_query "What technology choices should we avoid in the new project?"

# Document planning decisions
memcord_save "
Project Beta - Initial Planning

Based on Alpha lessons learned:

Architecture Decisions:
- Start with monolith, extract services later
- Use TypeScript from day 1
- Implement proper service discovery (Consul)
- Plan cross-service debugging strategy

Technology Stack:
- TypeScript + Node.js (proven combo)
- PostgreSQL (continue with what works)
- Simple Redis setup (single instance initially)
- Docker for consistent environments

Process Improvements:
- Implement pair programming sessions
- Weekly technical debt review
- Automated testing before code review
- Architecture decision records (ADRs)
"

# Cross-project search
memcord_search "typescript" --include-tags "project"
memcord_search "postgresql performance" --include-tags "architecture"
```

### 5. Customer Support Knowledge Base

**Scenario**: Building a searchable knowledge base for customer support.

```bash
# Common authentication issues
memcord_name "auth_support_kb"
memcord_tag add "support authentication common customer"
memcord_group set "support/authentication"

memcord_save "
Authentication Support Guide

Common Issues:

1. 'Invalid credentials' error
   Causes: Wrong email/password, account locked, expired session
   Solution: Verify credentials, check account status, clear browser cache
   
2. 'Token expired' message
   Causes: Session timeout (24h default), server restart
   Solution: Re-login, check 'remember me' option
   
3. Social login failures
   Causes: Third-party service down, permissions changed
   Solution: Try email login, check social platform status

Escalation triggers:
- Multiple users affected (service issue)
- Account appears compromised (security)
- Payment-related auth issues (billing team)
"

# Payment support knowledge
memcord_name "payment_support_kb"
memcord_tag add "support payment billing customer"
memcord_group set "support/billing"

memcord_save "
Payment Support Guide

Common Issues:

1. Card declined
   Causes: Insufficient funds, expired card, bank security
   Solution: Try different card, contact bank, verify billing address
   
2. Subscription not updating
   Causes: Payment processing delay, cache issues
   Solution: Wait 15 minutes, clear cache, check bank statement
   
3. Refund requests
   Process: Verify purchase, check refund policy, process via admin panel
   Timeline: 3-5 business days to original payment method
"

# Support agent using the knowledge base
memcord_query "How to handle expired token errors?"
memcord_query "What should I do if a customer's card is declined?"
memcord_search "refund" --include-tags "support"
memcord_search "authentication AND social" --include-tags "customer"
```

### 6. Learning and Development Tracking

**Scenario**: Personal learning journey with progress tracking.

```bash
# Learning React
memcord_name "react_learning_journey"
memcord_tag add "learning react frontend javascript personal"
memcord_group set "learning/frontend"

memcord_save "
React Learning Plan

Week 1: Fundamentals
- Components and JSX ✅
- Props and state ✅  
- Event handling ✅
- Conditional rendering 🔄

Week 2: Advanced Concepts
- Hooks (useState, useEffect) 📅
- Context API 📅
- Custom hooks 📅

Week 3: Ecosystem
- React Router 📅
- State management (Redux/Zustand) 📅
- Testing (Jest, React Testing Library) 📅

Resources:
- Official React docs
- React course on Udemy
- Practice projects: Todo app, Weather app
"

# Daily progress updates
memcord_save_progress "
Day 3 Progress:

Completed:
- Built first component with props
- Learned about JSX compilation  
- Created simple counter with useState

Challenges:
- Understanding component lifecycle
- When to use class vs function components
- State immutability concepts

Next: Practice with useEffect for side effects
" 0.3

# Weekly review
memcord_save_progress "
Week 1 Complete:

Achievements:
✅ Built 3 practice components
✅ Understand props vs state
✅ Can handle basic events
✅ Conditional rendering working

Gaps identified:
- Need more practice with complex state
- Don't fully understand useEffect dependencies
- Haven't tried any CSS-in-JS solutions

Plan for week 2:
- Focus on hooks deep dive
- Build a todo app with useEffect
- Explore styled-components
" 0.2

# Later reflection
memcord_query "What challenges did I face when learning React hooks?"
memcord_query "What achievements did I make in week 1?"
memcord_search "useEffect" --include-tags "learning"
```

## Import & Integration Workflows

### 7. Content Import and Organization

**Scenario**: Import research documents from various sources and organize them effectively.

```bash
# Import PDF research paper
memcord_name "research_ai_trends_2024"
memcord_import source="/path/to/ai-trends-2024.pdf" slot_name="research_ai_trends_2024" tags=["research", "ai", "trends", "2024"] group_path="research/papers"

# Import web article about AI developments
memcord_import source="https://techblog.com/ai-breakthroughs-2024" slot_name="ai_web_article" tags=["ai", "web", "article", "2024"] group_path="research/articles"

# Import CSV data from survey results
memcord_import source="/data/ai_adoption_survey.csv" slot_name="survey_data" description="AI adoption survey results Q4 2024" tags=["survey", "data", "ai", "adoption"] group_path="research/data"

# Import markdown notes from previous session
memcord_import source="./meeting_notes.md" slot_name="previous_notes" tags=["notes", "meeting", "draft"] group_path="meetings/drafts"

# Import log file for troubleshooting
memcord_import source="/logs/error_analysis.log" slot_name="error_logs" description="Production errors from last week" tags=["logs", "errors", "production"] group_path="troubleshooting"

# Query imported content
memcord_query "What are the main AI trends identified in the research?"
memcord_search "adoption" --include-tags "survey"
```

### 8. Project Documentation Consolidation

**Scenario**: Merge scattered project documentation into comprehensive guides.

```bash
# Start with existing project documentation slots
memcord_list | grep "project_alpha"
# Results: project_alpha_api, project_alpha_database, project_alpha_frontend, project_alpha_deployment

# Preview the merge to see what we're working with
memcord_merge source_slots=["project_alpha_api", "project_alpha_database", "project_alpha_frontend"] target_slot="project_alpha_complete" action="preview"

# Execute merge with moderate duplicate detection
memcord_merge source_slots=["project_alpha_api", "project_alpha_database", "project_alpha_frontend"] target_slot="project_alpha_complete" action="merge" similarity_threshold=0.7

# Add deployment documentation
memcord_merge source_slots=["project_alpha_complete", "project_alpha_deployment"] target_slot="project_alpha_master" action="merge" delete_sources=true

# Organize the consolidated documentation
memcord_name "project_alpha_master"
memcord_tag add "documentation complete master project"
memcord_group set "projects/alpha/documentation"

# Export for team sharing
memcord_export "project_alpha_master" "md"
memcord_share "project_alpha_master" "md,pdf"
```

### 9. Research Literature Review Workflow

**Scenario**: Import multiple research sources and create a comprehensive literature review.

```bash
# Import various research sources
memcord_import source="/papers/machine_learning_2024.pdf" slot_name="ml_paper_2024" tags=["research", "ml", "2024", "paper"] group_path="literature/core"

memcord_import source="https://arxiv.org/abs/2024.12345" slot_name="arxiv_neural_networks" tags=["research", "arxiv", "neural", "networks"] group_path="literature/core"

memcord_import source="/datasets/experiment_results.csv" slot_name="experiment_data" description="Neural network training results" tags=["data", "experiments", "results"] group_path="literature/data"

memcord_import source="./conference_notes.md" slot_name="conference_insights" tags=["conference", "notes", "insights"] group_path="literature/notes"

# Create thematic collections by merging related content
# Preview AI/ML theory merge
memcord_merge source_slots=["ml_paper_2024", "arxiv_neural_networks"] target_slot="theory_collection" action="preview"

# Execute theory merge
memcord_merge source_slots=["ml_paper_2024", "arxiv_neural_networks"] target_slot="theory_collection" action="merge" similarity_threshold=0.8

# Create practical insights collection
memcord_merge source_slots=["experiment_data", "conference_insights"] target_slot="practical_insights" action="merge"

# Create comprehensive literature review
memcord_merge source_slots=["theory_collection", "practical_insights"] target_slot="literature_review_2024" action="merge" delete_sources=true

# Enhance with structured analysis
memcord_name "literature_review_2024"
memcord_save_progress "
Literature Review Analysis Summary:

Key Themes Identified:
1. Neural network architectures evolution
2. Training efficiency improvements  
3. Real-world application performance
4. Ethical considerations in AI deployment

Methodology Trends:
- Increased focus on transfer learning
- Attention mechanisms dominating NLP
- Federated learning for privacy
- AutoML for democratization

Future Research Directions:
- Explainable AI development
- Edge computing optimization
- Quantum-classical hybrid models
- Sustainable AI practices
" 0.2

# Query for specific insights
memcord_query "What are the main challenges in neural network training identified in the literature?"
memcord_query "Which methodologies showed the most promising results?"
memcord_search "efficiency" --include-tags "research"
```

### 10. Customer Support Knowledge Base Development

**Scenario**: Build comprehensive support documentation from various sources.

```bash
# Import existing support documents
memcord_import source="/support/faq_old.md" slot_name="legacy_faq" tags=["support", "faq", "legacy"] group_path="support/legacy"

memcord_import source="/support/troubleshooting_guide.pdf" slot_name="troubleshooting_pdf" tags=["support", "troubleshooting", "guide"] group_path="support/guides"

memcord_import source="https://help.company.com/api-docs" slot_name="api_help_web" tags=["support", "api", "web"] group_path="support/api"

# Import structured data from support tickets
memcord_import source="/data/support_tickets_q4.csv" slot_name="support_analytics" description="Support ticket analysis Q4 2024" tags=["support", "data", "analytics"] group_path="support/data"

# Import recent meeting notes about support improvements
memcord_import source="./support_team_meeting.md" slot_name="support_meeting_notes" tags=["support", "meeting", "improvements"] group_path="support/meetings"

# Preview merge of core support content
memcord_merge source_slots=["legacy_faq", "troubleshooting_pdf", "api_help_web"] target_slot="support_knowledge_base" action="preview" similarity_threshold=0.6

# Execute merge with lower threshold to catch similar but not identical issues
memcord_merge source_slots=["legacy_faq", "troubleshooting_pdf", "api_help_web"] target_slot="support_knowledge_base" action="merge" similarity_threshold=0.6

# Add analytics insights
memcord_merge source_slots=["support_knowledge_base", "support_analytics"] target_slot="enhanced_support_kb" action="merge"

# Incorporate recent improvements
memcord_merge source_slots=["enhanced_support_kb", "support_meeting_notes"] target_slot="complete_support_kb" action="merge" delete_sources=true

# Structure the final knowledge base
memcord_name "complete_support_kb"
memcord_tag add "support knowledge-base complete master"
memcord_group set "support/master"

# Generate different views for different audiences
memcord_export "complete_support_kb" "md"  # For internal team
memcord_export "complete_support_kb" "json"  # For integration with help desk system

# Query capabilities for support agents
memcord_query "How do we handle authentication timeout errors?"
memcord_query "What are the most common API integration issues?"
memcord_search "billing" --include-tags "support"
```

### 11. Multi-Source Competitive Analysis

**Scenario**: Import competitor information from various sources and create analysis.

```bash
# Import competitor reports
memcord_import source="/reports/competitor_a_analysis.pdf" slot_name="competitor_a" tags=["competitor", "analysis", "report"] group_path="competitive/reports"

memcord_import source="/reports/competitor_b_analysis.pdf" slot_name="competitor_b" tags=["competitor", "analysis", "report"] group_path="competitive/reports"

# Import web research on competitors
memcord_import source="https://techcrunch.com/competitor-a-funding" slot_name="competitor_a_news" tags=["competitor", "news", "funding"] group_path="competitive/news"

memcord_import source="https://industry-report.com/market-analysis" slot_name="market_analysis" tags=["market", "analysis", "industry"] group_path="competitive/market"

# Import structured pricing data
memcord_import source="/data/competitor_pricing.csv" slot_name="pricing_data" description="Competitor pricing comparison Q4 2024" tags=["pricing", "data", "comparison"] group_path="competitive/data"

# Create competitor-specific collections
memcord_merge source_slots=["competitor_a", "competitor_a_news"] target_slot="competitor_a_complete" action="merge"

# Create market overview
memcord_merge source_slots=["competitor_b", "market_analysis", "pricing_data"] target_slot="market_overview" action="merge"

# Preview comprehensive analysis merge
memcord_merge source_slots=["competitor_a_complete", "market_overview"] target_slot="competitive_analysis_2024" action="preview"

# Execute final merge
memcord_merge source_slots=["competitor_a_complete", "market_overview"] target_slot="competitive_analysis_2024" action="merge" delete_sources=true similarity_threshold=0.7

# Add strategic insights
memcord_name "competitive_analysis_2024"
memcord_save_progress "
Competitive Analysis Executive Summary:

Market Position:
- Competitor A: Strong in enterprise, weak in SMB
- Competitor B: Aggressive pricing, limited features
- Market trend: Moving toward integrated solutions

Key Opportunities:
1. Feature gap in mobile experience
2. Pricing advantage in mid-market segment
3. Superior customer support reputation

Strategic Recommendations:
1. Accelerate mobile development
2. Bundle services for enterprise clients
3. Enhance SMB onboarding experience
" 0.15

# Analysis queries
memcord_query "What are Competitor A's main strengths and weaknesses?"
memcord_query "What pricing strategies are competitors using?"
memcord_search "mobile AND features" --include-tags "competitor"
```

## Organizational Workflows

### 12. Team Onboarding

**Scenario**: Creating structured onboarding materials for new team members.

```bash
# Day 1 onboarding
memcord_name "onboarding_day1_checklist"
memcord_tag add "onboarding checklist day1 admin"
memcord_group set "onboarding/checklists"

memcord_save "
New Developer - Day 1 Checklist

Administrative:
□ HR paperwork completed
□ IT equipment assigned (laptop, monitor, peripherals)
□ Email account created
□ Slack workspace added
□ GitHub organization access granted
□ VPN credentials provided

Development Setup:
□ Install required software (IDE, Git, Node.js, Docker)
□ Clone main repositories
□ Environment setup documentation reviewed
□ Local development environment working
□ First commit pushed to test repository

Introductions:
□ Meet direct manager
□ Meet team members (15min each)
□ Meet key stakeholders
□ Assign mentor/buddy
□ Schedule first 1:1 meeting

Resources:
□ Company handbook shared
□ Technical documentation access
□ Architecture overview session scheduled
□ Coding standards reviewed
"

# Week 1 technical deep dive
memcord_name "onboarding_week1_technical"
memcord_tag add "onboarding technical week1 architecture"
memcord_group set "onboarding/technical"

memcord_save "
Week 1 Technical Onboarding

Architecture Overview:
- System design presentation (Day 2)
- Database schema walkthrough (Day 3)
- API design patterns (Day 4)
- Deployment process (Day 5)

Hands-on Activities:
- Fix first 'good first issue' bug
- Add unit test to existing feature
- Review 3 recent pull requests
- Pair programming session with senior dev

Learning Objectives:
- Understand overall system architecture
- Know where to find documentation
- Comfortable with development workflow
- Can navigate codebase independently
"

# Track onboarding progress
memcord_query "What should a new developer complete on day 1?"
memcord_query "What technical activities are planned for week 1?"
memcord_search "checklist" --include-tags "onboarding"
```

### 13. Decision Documentation

**Scenario**: Recording architectural decisions and their rationale.

```bash
# API versioning decision
memcord_name "adr_001_api_versioning"
memcord_tag add "adr decision architecture api versioning"
memcord_group set "decisions/architecture"

memcord_save "
Architecture Decision Record #001: API Versioning Strategy

Status: Accepted
Date: 2024-01-15
Deciders: Engineering Team, Product Team

Context:
We need to establish a consistent API versioning strategy as we add new features and make breaking changes. Current API has no versioning, causing issues when we need to update endpoints.

Decision:
Implement URL path versioning (e.g., /api/v1/, /api/v2/) rather than header or query parameter versioning.

Rationale:
- Clear and explicit version in URL
- Easy to test and document
- Supports browser-based testing
- Widely adopted industry pattern
- Simpler than content negotiation

Alternatives Considered:
1. Header versioning (Accept: application/vnd.api+json;version=1)
   - Rejected: Complex for frontend teams
2. Query parameter (?version=1)
   - Rejected: Easy to omit accidentally
3. Subdomain versioning (v1.api.example.com)
   - Rejected: DNS and SSL complexity

Implementation:
- New endpoints: Start with /api/v1/
- Existing endpoints: Gradually migrate to /api/v1/
- Deprecation: 6-month notice before removing old versions
- Documentation: Version-specific API docs

Consequences:
+ Clear versioning strategy
+ Easier API evolution
+ Better backward compatibility
- Slight URL complexity
- Need migration plan for existing endpoints
"

# Database migration decision
memcord_name "adr_002_database_migration"
memcord_tag add "adr decision database migration tool"
memcord_group set "decisions/database"

memcord_save "
Architecture Decision Record #002: Database Migration Tool

Status: Accepted  
Date: 2024-01-20
Deciders: Backend Team, DevOps Team

Context:
Current database changes are applied manually, leading to inconsistencies between environments and deployment issues.

Decision:
Use Flyway for database migration management.

Rationale:
- Version-based migration files
- Automatic tracking of applied migrations
- Support for rollback scenarios
- CI/CD integration capabilities
- Wide PostgreSQL support

Alternatives Considered:
1. Liquibase
   - Rejected: XML configuration complexity
2. Custom migration scripts
   - Rejected: No automatic tracking
3. Prisma Migrate
   - Rejected: Too tightly coupled to ORM

Implementation Plan:
- Baseline current production schema
- Convert existing scripts to Flyway format
- Integrate with CI/CD pipeline
- Team training on migration best practices
"

# Query decisions later
memcord_query "Why did we choose URL path versioning for APIs?"
memcord_query "What database migration tool did we select and why?"
memcord_search "flyway" --include-tags "decision"
memcord_search "api versioning alternatives" --include-tags "adr"
```

## Tool Chaining Examples

### 14. Complex Research Workflow

```bash
# Research multiple related topics
memcord_search "microservices" --include-tags "architecture" | 
  head -3 | 
  while read slot; do
    memcord_query "What were the main challenges with microservices in $slot?"
  done

# Consolidate findings
memcord_name "microservices_research_summary"
memcord_tag add "research summary microservices architecture"
memcord_save_progress "Consolidated research from multiple projects..." 0.15
```

### 15. Automated Reporting

```bash
# Weekly progress report
memcord_list | grep "$(date +%Y_%m)" | while read slot; do
  echo "## $slot"
  memcord_query "What progress was made in $slot this week?"
  echo ""
done > weekly_report.md

# Tag analysis
memcord_list_tags | while read tag; do
  count=$(memcord_search "tag:$tag" --max-results 1000 | wc -l)
  echo "$tag: $count items"
done | sort -nr > tag_usage_report.txt
```

### 16. Import and Merge Chaining

```bash
# Complex multi-source import and consolidation workflow
# Step 1: Import from multiple sources
memcord_import source="/docs/api_v1.md" slot_name="api_v1_docs" tags=["api", "v1", "docs"] group_path="api/versions" &&
memcord_import source="/docs/api_v2.md" slot_name="api_v2_docs" tags=["api", "v2", "docs"] group_path="api/versions" &&
memcord_import source="https://blog.company.com/api-migration" slot_name="migration_guide" tags=["api", "migration", "blog"] group_path="api/migration"

# Step 2: Preview consolidation options
memcord_merge source_slots=["api_v1_docs", "api_v2_docs"] target_slot="api_consolidated" action="preview" &&
memcord_merge source_slots=["api_consolidated", "migration_guide"] target_slot="complete_api_guide" action="preview"

# Step 3: Execute merge chain with progressive consolidation
memcord_merge source_slots=["api_v1_docs", "api_v2_docs"] target_slot="api_consolidated" action="merge" similarity_threshold=0.6 &&
memcord_merge source_slots=["api_consolidated", "migration_guide"] target_slot="complete_api_guide" action="merge" delete_sources=true

# Step 4: Organize and analyze results
memcord_name "complete_api_guide" &&
memcord_tag add "api complete consolidated master" &&
memcord_group set "api/master" &&
memcord_query "What are the key differences between API v1 and v2?" &&
memcord_export "complete_api_guide" "md"

# Advanced chaining: Batch import with immediate organization
for file in /reports/*.pdf; do
  filename=$(basename "$file" .pdf)
  memcord_import source="$file" slot_name="report_$filename" tags=["report", "pdf", "imported"] group_path="reports/batch"
done

# Merge all imported reports
report_slots=($(memcord_list | grep "report_" | head -10))
memcord_merge source_slots=$report_slots target_slot="consolidated_reports" action="merge" similarity_threshold=0.8 delete_sources=true
```

These examples demonstrate the flexibility and power of the Chat Memory MCP Server across different use cases and workflows. The import and merge capabilities in Phase 3 add significant value for content consolidation, knowledge management, and workflow automation. The key is to establish consistent naming conventions, tagging strategies, and organizational patterns that work for your specific needs.