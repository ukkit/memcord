"""
MCP Prompts for Memcord - Reusable workflow templates for GitHub Copilot.

This module defines preconfigured prompts for common memcord workflows that can be
invoked in GitHub Copilot Chat or other MCP clients using slash commands.
"""

# MCP Prompt Definitions
PROMPTS = {
    "project-memory": {
        "name": "project-memory",
        "description": "Create and initialize a memory slot for the current project",
        "prompt": """Create a new memcord memory slot for this project and save the initial context.

Steps:
1. Identify the project name from the workspace or ask the user
2. Create a memory slot using memcord_name with the project name
3. Save the following initial context:
   - Project name and purpose
   - Technology stack
   - Key files and directories
   - Current development phase

Use memcord_save_progress to automatically summarize and save the context.""",
        "categories": ["setup", "project-management"],
    },
    "code-review-save": {
        "name": "code-review-save",
        "description": "Save code review decisions and feedback",
        "prompt": """Save code review decisions to memcord for future reference.

Steps:
1. Use or create a 'code-reviews' memory slot
2. Extract key information from the current context:
   - PR number or commit hash
   - Files reviewed
   - Key decisions made
   - Action items or follow-ups
   - Reviewers involved
3. Save using memcord_save with structured format
4. Suggest relevant tags (e.g., 'security', 'performance', 'architecture')

Format the saved content for easy retrieval later.""",
        "categories": ["code-review", "documentation"],
    },
    "architecture-decision": {
        "name": "architecture-decision",
        "description": "Document an architecture decision record (ADR)",
        "prompt": """Document an architecture decision in memcord using ADR format.

Use or create an 'architecture-decisions' memory slot and save the following structure:

ADR-[NUMBER]: [DECISION TITLE]

Decision: [What was decided]

Context: [Why this decision was necessary]

Alternatives Considered: [What other options were evaluated]

Rationale: [Why this decision was chosen]

Consequences: [Impact and implications]

Date: [Today's date]

Use memcord_save to store this structured decision for future reference.""",
        "categories": ["architecture", "documentation", "decision-making"],
    },
    "bug-investigation": {
        "name": "bug-investigation",
        "description": "Track bug investigation progress and findings",
        "prompt": """Create or use a 'bug-investigations' memory slot to track this bug investigation.

Document:
1. Bug description and reproduction steps
2. Timeline of investigation activities
3. Hypotheses tested
4. Root cause analysis
5. Solution or workaround
6. Related issues or patterns

Use memcord_save_progress to automatically summarize the investigation as it progresses.""",
        "categories": ["debugging", "troubleshooting"],
    },
    "meeting-notes": {
        "name": "meeting-notes",
        "description": "Save meeting notes and action items",
        "prompt": """Save meeting notes to memcord with structured format.

Create or use a meeting-specific memory slot and save:
- Meeting title and date
- Attendees
- Agenda items discussed
- Key decisions made
- Action items with owners
- Follow-up topics

Use memcord_save_progress to create an AI-generated summary.""",
        "categories": ["meetings", "collaboration"],
    },
    "search-past-decisions": {
        "name": "search-past-decisions",
        "description": "Search for past decisions and discussions",
        "prompt": """Search memcord for relevant past decisions and discussions.

Steps:
1. Identify key search terms from the current context or user query
2. Use memcord_search with Boolean operators if needed for precise results
3. If searching for conceptual information, use memcord_query for natural language search
4. Present findings with timestamps and source memory slots
5. Suggest related searches if relevant

Focus on extracting actionable insights from past conversations.""",
        "categories": ["search", "knowledge-retrieval"],
    },
    "sprint-planning": {
        "name": "sprint-planning",
        "description": "Document sprint planning session",
        "prompt": """Create or use a 'sprint-planning' memory slot to document this sprint.

Save:
- Sprint number and duration
- Sprint goals and objectives
- Selected user stories/tickets
- Story point estimates
- Team capacity and velocity
- Risks and dependencies
- Success criteria

Use memcord_save_progress for automatic summarization.""",
        "categories": ["agile", "planning", "project-management"],
    },
    "tech-debt": {
        "name": "tech-debt",
        "description": "Log technical debt items and decisions",
        "prompt": """Use or create a 'tech-debt' memory slot to track technical debt.

Document:
- Description of the technical debt
- Why it was introduced (context/constraints)
- Impact on development velocity or system quality
- Proposed solution or refactoring approach
- Related ticket numbers
- Priority level

Tag appropriately for easy filtering (e.g., 'performance', 'security', 'maintainability').""",
        "categories": ["tech-debt", "documentation"],
    },
    "onboarding-docs": {
        "name": "onboarding-docs",
        "description": "Create onboarding documentation from project knowledge",
        "prompt": """Generate onboarding documentation by querying memcord for project knowledge.

Steps:
1. Search memcord for:
   - Architecture decisions
   - Development setup instructions
   - Code review guidelines
   - Common troubleshooting issues
   - Team conventions and practices
2. Use memcord_query to extract conceptual information
3. Compile findings into structured onboarding guide
4. Save to a 'team-onboarding' memory slot

Focus on practical, actionable information for new team members.""",
        "categories": ["onboarding", "documentation", "knowledge-management"],
    },
    "incident-postmortem": {
        "name": "incident-postmortem",
        "description": "Document incident postmortem and learnings",
        "prompt": """Create or use an 'incidents' memory slot to document this postmortem.

Structure:
- Incident title and date
- Severity and impact
- Timeline of events
- Root cause analysis
- What went well
- What went wrong
- Action items to prevent recurrence
- Related incidents or patterns

Use memcord_save for permanent record and future reference.""",
        "categories": ["incidents", "postmortem", "learning"],
    },
    "api-design": {
        "name": "api-design",
        "description": "Document API design decisions and specifications",
        "prompt": """Use or create an 'api-design' memory slot to document API decisions.

Save:
- Endpoint URLs and HTTP methods
- Request/response formats
- Authentication/authorization approach
- Versioning strategy
- Rate limiting and error handling
- Design rationale and trade-offs

Use memcord_save_progress to summarize the design discussion.""",
        "categories": ["api", "design", "documentation"],
    },
    "security-review": {
        "name": "security-review",
        "description": "Document security review findings and decisions",
        "prompt": """Create or use a 'security-reviews' memory slot to track security findings.

Document:
- Vulnerability description and severity
- Attack vectors and exploit scenarios
- Affected components or endpoints
- Remediation steps and timeline
- Verification method
- Related security patterns or best practices

Tag with 'security' and specific vulnerability type (e.g., 'xss', 'sql-injection').""",
        "categories": ["security", "review", "compliance"],
    },
    "knowledge-export": {
        "name": "knowledge-export",
        "description": "Export project knowledge for sharing or archival",
        "prompt": """Export relevant memcord knowledge for sharing or archival.

Steps:
1. Identify memory slots to export (architecture, decisions, reviews, etc.)
2. Use memcord_export to generate markdown or JSON files
3. Compile into comprehensive project documentation
4. Suggest organization structure for exported content

Focus on creating shareable, readable documentation.""",
        "categories": ["export", "documentation", "sharing"],
    },
    "retrospective": {
        "name": "retrospective",
        "description": "Document sprint or project retrospective",
        "prompt": """Create or use a 'retrospectives' memory slot to document this retro.

Save:
- Retrospective date and participants
- What went well (positive outcomes)
- What could be improved (challenges)
- Action items for next sprint/project
- Experiments to try
- Appreciation shoutouts

Use memcord_save_progress for automatic summarization.""",
        "categories": ["agile", "retrospective", "team"],
    },
    "merge-related": {
        "name": "merge-related",
        "description": "Merge related conversation memories intelligently",
        "prompt": """Identify and merge related memory slots to consolidate knowledge.

Steps:
1. List available memory slots using memcord_list
2. Identify slots with similar topics or themes
3. Use memcord_merge to combine related slots with duplicate detection
4. Suggest a meaningful name for the merged slot
5. Verify the merge with preview mode first

This helps organize and consolidate project knowledge over time.""",
        "categories": ["organization", "maintenance"],
    },
    "context-resume": {
        "name": "context-resume",
        "description": "Resume work by loading project context from memory",
        "prompt": """Help the user resume work on this project by loading context from memcord.

Steps:
1. Identify the current project or ask which project to resume
2. Use memcord_use to activate the project memory slot
3. Use memcord_select_entry to find recent entries (e.g., "latest" or "today")
4. Present a summary of:
   - What was last discussed
   - Key decisions made recently
   - Open action items or next steps
   - Relevant context for current work

Focus on getting the user quickly up to speed.""",
        "categories": ["workflow", "context-switching"],
    },
}


def get_prompt(name: str) -> dict:
    """Get a specific prompt by name.

    Args:
        name: The prompt name (e.g., 'project-memory')

    Returns:
        The prompt definition dictionary

    Raises:
        KeyError: If prompt name not found
    """
    return PROMPTS[name]


def list_prompts() -> list[str]:
    """List all available prompt names.

    Returns:
        List of prompt names
    """
    return list(PROMPTS.keys())


def get_prompts_by_category(category: str) -> list[dict]:
    """Get all prompts in a specific category.

    Args:
        category: The category to filter by (e.g., 'documentation')

    Returns:
        List of prompt definitions matching the category
    """
    return [prompt for prompt in PROMPTS.values() if category in prompt.get("categories", [])]


def list_categories() -> list[str]:
    """List all unique categories across prompts.

    Returns:
        Sorted list of unique category names
    """
    categories: set[str] = set()
    for prompt in PROMPTS.values():
        categories.update(prompt.get("categories", []))
    return sorted(categories)


def format_prompt_list() -> str:
    """Format all prompts as a readable list.

    Returns:
        Formatted string with all prompts and descriptions
    """
    lines = ["Available Memcord Prompts:\n"]
    for name, prompt in PROMPTS.items():
        lines.append(f"/{name}")
        lines.append(f"  {prompt['description']}")
        lines.append(f"  Categories: {', '.join(prompt['categories'])}\n")
    return "\n".join(lines)


# Prompt aliases for convenience
ALIASES = {
    "project": "project-memory",
    "review": "code-review-save",
    "adr": "architecture-decision",
    "bug": "bug-investigation",
    "meeting": "meeting-notes",
    "search": "search-past-decisions",
    "sprint": "sprint-planning",
    "debt": "tech-debt",
    "onboard": "onboarding-docs",
    "postmortem": "incident-postmortem",
    "api": "api-design",
    "security": "security-review",
    "export": "knowledge-export",
    "retro": "retrospective",
    "merge": "merge-related",
    "resume": "context-resume",
}


def resolve_alias(name: str) -> str:
    """Resolve a prompt alias to its full name.

    Args:
        name: Prompt name or alias

    Returns:
        Full prompt name
    """
    return ALIASES.get(name, name)
