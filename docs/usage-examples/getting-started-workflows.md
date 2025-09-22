# Getting Started with Memcord - Complete Workflows

This guide provides step-by-step workflows for common memcord usage patterns, from basic memory management to advanced organization and optimization.

## Quick Start: First Session

### Your First 5 Minutes with Memcord
```bash
# 1. Create your first memory slot
memcord_name slot_name="my_first_project"
# ✅ Result: Memory slot 'my_first_project' is now active

# 2. Save some conversation content  
memcord_save chat_text="Today I learned about database indexing. Key points:
- B-tree indexes are most common
- Composite indexes can cover multiple columns
- Index selectivity affects performance
- Too many indexes can slow down writes"
# ✅ Result: Saved 156 characters to memory slot 'my_first_project'

# 3. Verify the save worked
memcord_read
# ✅ Result: Shows your saved content with timestamp

# 4. Try a search to test functionality
memcord_search query="database indexing"
# ✅ Result: Finds your saved content with relevance score

# 5. Check your memory organization  
memcord_list
# ✅ Result: Shows all memory slots - you should see 'my_first_project'
```

**What you accomplished:**
- Created your first organized memory space
- Saved important information for future reference
- Verified the save and search functionality works
- Learned the basic workflow pattern

## Daily Work Session Workflow

### Starting Your Work Day
```bash
# 1. Review available memory slots
memcord_list
# See: • work_project (15 entries, 4,230 chars, updated 2024-09-04)
#      • client_alpha (8 entries, 2,100 chars, updated 2024-09-03)  
#      • learning_notes (23 entries, 8,445 chars, updated 2024-09-02)

# 2. Activate the project you're working on today
memcord_name slot_name="work_project"
# ✅ Active memory context set

# 3. Review recent progress (optional)
memcord_select_entry relative_time="latest"
# ✅ See your last saved work to get oriented

# 4. Start working and save progress as you go...
# (Continue your conversation with Claude)

# 5. Save important developments
memcord_save_progress chat_text="Made significant progress on the user authentication system. Claude helped me understand JWT implementation details, security considerations, and best practices for token refresh. We also discussed database schema changes needed for user roles and permissions."
# ✅ Progress summarized and saved with compression
```

### Ending Your Work Session
```bash
# 1. Save final session summary
memcord_save_progress chat_text="Session wrap-up: Completed JWT implementation, identified next steps for role-based permissions, noted potential security improvements for production deployment." compression_ratio=0.2

# 2. Check what was accomplished today
memcord_read

# 3. Tag important sessions for future organization
memcord_tag action="add" tags=["authentication", "security", "implementation"]

# 4. Quick overview of all projects
memcord_list
```

## Project Management Workflow

### Setting Up a New Project
```bash
# 1. Create main project memory
memcord_name slot_name="proj_ecommerce_platform"

# 2. Save initial project requirements
memcord_save chat_text="E-commerce Platform Project - Initial Requirements:

SCOPE:
- User authentication and profiles
- Product catalog with search/filtering  
- Shopping cart and checkout process
- Payment integration (Stripe)
- Admin dashboard for inventory management
- Mobile-responsive design

TIMELINE: 12 weeks
TEAM: 3 developers, 1 designer
TECH STACK: React, Node.js, PostgreSQL, Redis

PRIORITIES:
1. Core shopping functionality
2. Payment processing
3. Admin tools
4. Performance optimization"

# 3. Organize with tags and groups
memcord_tag action="add" tags=["project", "ecommerce", "requirements", "planning"]
memcord_group action="set" group_path="projects/ecommerce"

# 4. Create subsystem memory slots  
memcord_name slot_name="proj_ecommerce_frontend"
memcord_tag action="add" tags=["project", "ecommerce", "frontend", "react"]
memcord_group action="set" group_path="projects/ecommerce/frontend"

memcord_name slot_name="proj_ecommerce_backend"  
memcord_tag action="add" tags=["project", "ecommerce", "backend", "nodejs"]
memcord_group action="set" group_path="projects/ecommerce/backend"

memcord_name slot_name="proj_ecommerce_database"
memcord_tag action="add" tags=["project", "ecommerce", "database", "postgresql"]
memcord_group action="set" group_path="projects/ecommerce/database"

# 5. Return to main project slot for ongoing coordination
memcord_name slot_name="proj_ecommerce_platform"
```

### Daily Project Development
```bash
# Morning: Review yesterday's progress
memcord_search query="TODO OR next steps OR pending" include_tags=["ecommerce"]

# Work on specific subsystem
memcord_name slot_name="proj_ecommerce_frontend"
memcord_save_progress chat_text="Working on user authentication UI. Implemented login form with validation, working on registration flow. Challenge: handling form state efficiently with React hooks. Solution: custom useForm hook with validation schema."

# Document decisions and solutions  
memcord_save chat_text="DECISION: Using React Hook Form for all forms
- Reduces re-renders compared to controlled components  
- Built-in validation with yup schema
- Better performance for complex forms
- Team consensus in today's standup

IMPLEMENTATION NOTES:
- Created reusable form components in /components/forms/
- Validation schemas in /utils/validation/
- Error handling with toast notifications"

# Cross-reference with other subsystems
memcord_save chat_text="INTEGRATION POINTS with backend:
- POST /api/auth/login endpoint (implemented)
- POST /api/auth/register endpoint (in progress)  
- JWT token refresh logic (needs coordination)
- User profile endpoints (backend team working on this)"
```

## Learning and Research Workflow

### Deep Learning Session Setup
```bash
# 1. Create focused learning memory
memcord_name slot_name="learn_machine_learning_fundamentals"

# 2. Set learning context and goals
memcord_save chat_text="Machine Learning Fundamentals - Learning Session 1

GOAL: Understand core ML concepts and algorithms
FOCUS TODAY: Supervised vs Unsupervised Learning
RESOURCES: Stanford CS229 lectures, hands-on examples
TIME ALLOCATED: 2 hours

LEARNING OBJECTIVES:
- Understand bias-variance tradeoff
- Compare different algorithms (linear regression, SVM, neural networks)
- Practice with real datasets
- Document key insights for future reference"

# 3. Organize for future discovery
memcord_tag action="add" tags=["learning", "machine-learning", "fundamentals", "algorithms"]
memcord_group action="set" group_path="learning/machine_learning"
```

### During Learning Session
```bash
# Save key insights as you learn
memcord_save_progress chat_text="Key insight about bias-variance tradeoff: 

High bias models (like linear regression) underfit - they make strong assumptions about data shape and can't capture complex patterns. 

High variance models (like high-degree polynomials) overfit - they memorize training data but don't generalize.

The sweet spot is finding the right model complexity that balances both. Cross-validation helps find this balance by testing on unseen data.

PRACTICAL EXAMPLE: 
- Linear model on housing prices: high bias (assumes linear relationship)
- 15-degree polynomial: high variance (fits noise in training data)  
- Ridge regression: balances both with regularization parameter"

# Document resources and references
memcord_save chat_text="RESOURCES - Machine Learning Fundamentals:

VIDEOS:
- Stanford CS229 Lecture 3: Bias-Variance Tradeoff (timestamp: 15:30-45:20)
- 3Blue1Brown: Neural Networks series (excellent visual explanations)

PAPERS:
- 'The Elements of Statistical Learning' Chapter 2
- 'Pattern Recognition and Machine Learning' Bishop, Chapter 1

PRACTICAL:
- Kaggle Housing Prices dataset (good for regression practice)
- Scikit-learn documentation with examples
- Google Colab notebooks from CS229

NEXT STEPS:
- Practice implementing linear regression from scratch
- Experiment with regularization parameters  
- Move on to classification algorithms next session"
```

### Connecting Learning Across Sessions
```bash
# Search for related previous learning
memcord_search query="regression AND overfitting" include_tags=["learning"]

# Build on previous sessions  
memcord_save_progress chat_text="Building on previous regression learning - now understand that regularization (Ridge, Lasso) is one way to control model complexity and prevent overfitting. This connects to today's bias-variance discussion:

Ridge regression adds L2 penalty → controls variance by shrinking coefficients
Lasso regression adds L1 penalty → controls variance + feature selection  
Elastic Net combines both → balances L1 and L2 benefits

This gives practical tools for the bias-variance tradeoff I learned about conceptually."

# Cross-reference with other topics
memcord_search query="cross-validation" include_tags=["learning", "statistics"]
```

## Team Collaboration Workflow

### Meeting Notes Management
```bash
# Before meeting: Create dedicated meeting memory
memcord_name slot_name="meet_team_standup_2024_09_05"
memcord_tag action="add" tags=["meeting", "standup", "team", "daily"]
memcord_group action="set" group_path="meetings/daily_standups"

# During meeting: Capture key points
memcord_save chat_text="Daily Standup - September 5, 2024

ATTENDEES: Sarah (PM), John (Backend), Alex (Frontend), Maya (Design)

YESTERDAY'S PROGRESS:
- John: Completed user authentication API endpoints
- Alex: Finished login UI components, starting on dashboard
- Maya: Delivered wireframes for checkout flow
- Sarah: Stakeholder review, updated project timeline  

TODAY'S PLANS:
- John: Start payment integration research  
- Alex: Connect frontend auth to backend APIs
- Maya: High-fidelity mockups for checkout
- Sarah: Vendor calls for payment processing

BLOCKERS:
- Alex: Need API documentation for new endpoints (John to provide)
- John: Waiting on payment provider API keys (Sarah following up)
- Maya: Need feedback on wireframes (stakeholders reviewing today)

ACTION ITEMS:
- John: Share API docs with Alex by noon
- Sarah: Follow up on API keys, share wireframe feedback
- Alex: Demo authentication flow in tomorrow's standup
- Maya: Present checkout mockups Friday"

# After meeting: Connect to project context
memcord_search query="authentication API" include_tags=["project", "backend"]
memcord_save chat_text="MEETING CONNECTION: Today's standup aligns with backend authentication work discussed in proj_ecommerce_backend. John's API completion unblocks Alex's frontend integration work."
```

### Cross-Project Knowledge Sharing
```bash
# Find solutions from other projects
memcord_search query="payment integration" exclude_tags=["archived", "deprecated"]

# Share insights across project teams  
memcord_save chat_text="KNOWLEDGE TRANSFER from proj_marketplace_v1:

Payment integration lessons learned:
1. Stripe webhook reliability: implement idempotency keys
2. Error handling: distinguish between user errors vs system failures
3. Testing: use Stripe test mode extensively, automate webhook testing
4. Security: never store payment details, use tokenization
5. UX: provide clear feedback during payment processing

APPLICABLE TO CURRENT PROJECT:
- Same Stripe integration approach
- Reuse webhook handling patterns  
- Apply same security practices
- Consider similar UX patterns

REUSABLE CODE:
- Payment service abstraction layer
- Webhook verification utilities
- Error handling middleware
- Test data generation scripts"

# Tag for future discoverability
memcord_tag action="add" tags=["knowledge-transfer", "payments", "reusable-patterns"]
```

## Troubleshooting and Problem-Solving Workflow

### When You Encounter a Complex Problem
```bash
# 1. Create problem-focused memory slot
memcord_name slot_name="debug_database_performance_issue"
memcord_tag action="add" tags=["debugging", "database", "performance", "production"]

# 2. Document the problem clearly
memcord_save chat_text="DATABASE PERFORMANCE ISSUE - September 5, 2024

PROBLEM DESCRIPTION:
Query response times increased from 100ms to 3+ seconds over the past week
Affects user dashboard loading, causing timeouts and poor UX

SYMPTOMS:
- Slow queries on user_activities table (2M+ records)
- High CPU usage on database server (80-90% sustained)
- Connection pool exhaustion during peak hours
- Users reporting 'loading forever' on dashboard

ENVIRONMENT:
- PostgreSQL 13.4 on AWS RDS (db.r5.large)  
- Peak concurrent users: ~500
- Main query: complex JOIN across 4 tables with date filtering

IMPACT:
- 40% of users experiencing slow dashboard loads
- Customer complaints increasing
- Potential revenue impact if not resolved soon"

# 3. Search for similar past issues
memcord_search query="database performance AND slow query" include_tags=["debugging", "production"]
memcord_search query="PostgreSQL AND optimization" 

# 4. Work through troubleshooting with Claude
memcord_save_progress chat_text="Troubleshooting session with Claude:

DIAGNOSIS APPROACH:
1. Analyzed EXPLAIN PLAN for slow queries → Found missing index on date column
2. Checked query patterns → N+1 query problem in application code  
3. Reviewed database metrics → Connection pool too small for current load
4. Examined data growth → user_activities table grew 300% in past month

ROOT CAUSES IDENTIFIED:
- Missing composite index on (user_id, created_at) 
- Inefficient ORM queries causing N+1 problem
- Connection pool sized for pre-growth usage
- No query optimization for larger dataset

IMMEDIATE FIXES:
- Add composite index: CREATE INDEX idx_user_activities_user_date ON user_activities(user_id, created_at)
- Optimize ORM queries to use eager loading
- Increase connection pool size from 10 to 25
- Add query timeout limits

MONITORING PLAN:
- Set up alerts for query times > 500ms
- Monitor connection pool utilization  
- Track slow query log for new issues"

# 5. Document the solution and results
memcord_save chat_text="SOLUTION IMPLEMENTED - Database Performance Fix

CHANGES MADE:
1. ✅ Added composite index on user_activities table
2. ✅ Fixed N+1 queries in user dashboard API  
3. ✅ Increased RDS connection pool configuration
4. ✅ Added query monitoring and alerts

RESULTS:
- Query response time: 3000ms → 120ms (96% improvement)
- Database CPU usage: 90% → 45% (50% reduction)  
- User dashboard load time: 8s → 1.2s (85% improvement)
- Zero timeout errors since implementation

LESSONS LEARNED:
- Monitor database performance metrics continuously
- Plan for data growth when designing queries and indexes
- Regular performance testing with realistic data volumes
- ORM query optimization is critical at scale

REUSABLE PATTERNS:
- Composite indexing strategy for date-filtered user data
- Connection pool sizing calculations
- Performance monitoring dashboard setup
- N+1 query detection and prevention techniques"

# 6. Tag for future reference and knowledge sharing
memcord_tag action="add" tags=["solved", "database-optimization", "performance-tuning", "production-fixes"]
```

### Building a Troubleshooting Knowledge Base
```bash
# Search for patterns across different debugging sessions
memcord_search query="root cause AND solution" include_tags=["debugging", "solved"]

# Create consolidated troubleshooting guide
memcord_name slot_name="troubleshooting_patterns_database"
memcord_merge source_slots=["debug_database_performance_issue", "debug_connection_timeout", "debug_query_optimization"] target_slot="troubleshooting_patterns_database" action="preview"

# After review, execute the merge
memcord_merge source_slots=["debug_database_performance_issue", "debug_connection_timeout", "debug_query_optimization"] target_slot="troubleshooting_patterns_database" action="merge"

# Tag the consolidated knowledge
memcord_tag action="add" tags=["knowledge-base", "troubleshooting", "database", "patterns", "reference"]
```

## Memory Organization and Maintenance

### Weekly Memory Maintenance
```bash
# 1. Review memory usage and organization
memcord_list

# 2. Identify slots that might need compression
memcord_compress action="analyze"  

# 3. Compress large slots to save space  
memcord_compress slot_name="proj_ecommerce_platform" action="compress"

# 4. Archive inactive projects
memcord_archive action="candidates" days_inactive=30

# 5. Archive old projects no longer active
memcord_archive slot_name="old_prototype_project" action="archive" reason="project_completed"

# 6. Merge related learning sessions if beneficial
memcord_search query="machine learning" include_tags=["learning"]
# Based on results, consider merging related slots
```

### Memory Organization Best Practices
```bash
# Use consistent tagging across related content
memcord_tag action="add" tags=["project", "ecommerce", "backend"] slot_name="proj_ecommerce_backend"  
memcord_tag action="add" tags=["project", "ecommerce", "frontend"] slot_name="proj_ecommerce_frontend"
memcord_tag action="add" tags=["project", "ecommerce", "database"] slot_name="proj_ecommerce_database"

# Group related memories hierarchically  
memcord_group action="set" group_path="projects/ecommerce" slot_name="proj_ecommerce_platform"
memcord_group action="set" group_path="projects/ecommerce/frontend" slot_name="proj_ecommerce_frontend"  
memcord_group action="set" group_path="projects/ecommerce/backend" slot_name="proj_ecommerce_backend"

# Regularly review and optimize organization
memcord_list_tags
memcord_group action="list"
```

These workflows provide templates you can adapt to your specific needs. Start with the basic patterns and gradually incorporate more advanced organization and optimization techniques as your memory collection grows.