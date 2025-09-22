"""Workflow templates and automation for common memcord usage patterns.

This module provides predefined templates for common workflows and automation
features to streamline repetitive tasks and improve user productivity.
"""

import json
import asyncio
import aiofiles
from pathlib import Path
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum

from .smart_defaults import WorkflowAutomation, PreferenceLearningEngine


class TemplateCategory(Enum):
    """Categories for workflow templates."""
    PROJECT = "project"
    MEETING = "meeting"
    LEARNING = "learning"
    DEBUGGING = "debugging"
    MAINTENANCE = "maintenance"
    COLLABORATION = "collaboration"


@dataclass
class WorkflowTemplate:
    """Represents a reusable workflow template."""
    name: str
    category: TemplateCategory
    description: str
    steps: List[Dict[str, Any]]
    required_params: List[str]
    optional_params: List[str]
    estimated_duration: int  # minutes
    tags: List[str]
    created_by: str
    created_at: datetime
    usage_count: int = 0
    success_rate: float = 1.0


@dataclass 
class QuickAction:
    """Represents a quick action shortcut."""
    name: str
    description: str
    tool_combination: List[Dict[str, Any]]
    trigger_keywords: List[str]
    context_requirements: Dict[str, Any]
    success_rate: float = 1.0
    usage_count: int = 0


class WorkflowTemplateManager:
    """Manages workflow templates and quick actions."""
    
    def __init__(self, storage_dir: Path):
        self.storage_dir = storage_dir
        self.templates_file = storage_dir / "workflow_templates.json"
        self.quick_actions_file = storage_dir / "quick_actions.json"
        self.templates: Dict[str, WorkflowTemplate] = {}
        self.quick_actions: Dict[str, QuickAction] = {}
        self.custom_templates: Dict[str, WorkflowTemplate] = {}
    
    async def initialize(self):
        """Initialize the template manager."""
        self._create_builtin_templates()
        await self._load_custom_templates()
        await self._load_quick_actions()
    
    def _create_builtin_templates(self):
        """Create built-in workflow templates."""
        
        # Project Setup Templates
        self.templates["new_web_project"] = WorkflowTemplate(
            name="New Web Development Project",
            category=TemplateCategory.PROJECT,
            description="Set up organized memory structure for a web development project",
            steps=[
                {
                    "tool": "memcord_name",
                    "params": {"slot_name": "proj_{project_name}"},
                    "description": "Create main project memory slot"
                },
                {
                    "tool": "memcord_save", 
                    "params": {
                        "chat_text": """# {project_name} - Project Overview

## Project Details
- **Name:** {project_name}
- **Type:** {project_type}
- **Started:** {date}
- **Tech Stack:** {tech_stack}
- **Timeline:** {timeline}

## Goals & Requirements
- {goal_1}
- {goal_2}
- {goal_3}

## Architecture Notes
- Frontend: {frontend_tech}
- Backend: {backend_tech}  
- Database: {database_tech}

## Next Steps
- [ ] Set up development environment
- [ ] Create initial project structure
- [ ] Set up version control
- [ ] Plan first sprint

## Resources
- Repository: {repo_url}
- Documentation: {docs_url}
- Design: {design_url}"""
                    },
                    "description": "Save initial project documentation"
                },
                {
                    "tool": "memcord_tag",
                    "params": {
                        "action": "add", 
                        "tags": ["project", "web-dev", "{project_type}", "active"]
                    },
                    "description": "Add organizational tags"
                },
                {
                    "tool": "memcord_group",
                    "params": {"action": "set", "group_path": "projects/{project_name}"},
                    "description": "Organize into project group"
                },
                {
                    "tool": "memcord_name",
                    "params": {"slot_name": "proj_{project_name}_frontend"},
                    "description": "Create frontend-specific slot"
                },
                {
                    "tool": "memcord_tag",
                    "params": {
                        "action": "add",
                        "tags": ["project", "{project_name}", "frontend", "development"]
                    },
                    "description": "Tag frontend slot"
                },
                {
                    "tool": "memcord_group",
                    "params": {"action": "set", "group_path": "projects/{project_name}/frontend"},
                    "description": "Group frontend slot"
                },
                {
                    "tool": "memcord_name", 
                    "params": {"slot_name": "proj_{project_name}_backend"},
                    "description": "Create backend-specific slot"
                },
                {
                    "tool": "memcord_tag",
                    "params": {
                        "action": "add", 
                        "tags": ["project", "{project_name}", "backend", "development"]
                    },
                    "description": "Tag backend slot"
                },
                {
                    "tool": "memcord_group",
                    "params": {"action": "set", "group_path": "projects/{project_name}/backend"},
                    "description": "Group backend slot"
                }
            ],
            required_params=["project_name"],
            optional_params=["project_type", "tech_stack", "timeline", "goal_1", "goal_2", "goal_3",
                           "frontend_tech", "backend_tech", "database_tech", "repo_url", "docs_url", "design_url"],
            estimated_duration=5,
            tags=["project-setup", "web-development", "organization"],
            created_by="system",
            created_at=datetime.now()
        )
        
        # Meeting Templates
        self.templates["weekly_standup"] = WorkflowTemplate(
            name="Weekly Team Standup",
            category=TemplateCategory.MEETING,
            description="Structure for weekly team standup meetings",
            steps=[
                {
                    "tool": "memcord_name",
                    "params": {"slot_name": "standup_weekly_{date}"},
                    "description": "Create weekly standup slot"
                },
                {
                    "tool": "memcord_save",
                    "params": {
                        "chat_text": """# Weekly Standup - {date}

## Meeting Info
- **Date:** {date}
- **Time:** {time}
- **Attendees:** {attendees}
- **Facilitator:** {facilitator}

## Last Week's Progress
### {team_member_1}
- Completed: 
- Challenges:
- Blockers:

### {team_member_2}
- Completed:
- Challenges: 
- Blockers:

### {team_member_3}
- Completed:
- Challenges:
- Blockers:

## This Week's Goals
- [ ] Priority 1: {priority_1}
- [ ] Priority 2: {priority_2} 
- [ ] Priority 3: {priority_3}

## Action Items
- [ ] {action_1} - Owner: {owner_1} - Due: {due_1}
- [ ] {action_2} - Owner: {owner_2} - Due: {due_2}

## Blockers & Risks
- {blocker_1}
- {risk_1}

## Next Meeting
- Date: {next_meeting_date}
- Focus: {next_focus}"""
                    },
                    "description": "Save meeting template"
                },
                {
                    "tool": "memcord_tag",
                    "params": {
                        "action": "add",
                        "tags": ["meeting", "standup", "weekly", "team"]
                    },
                    "description": "Tag meeting appropriately"
                },
                {
                    "tool": "memcord_group", 
                    "params": {"action": "set", "group_path": "meetings/weekly_standups"},
                    "description": "Organize in meeting group"
                }
            ],
            required_params=["date"],
            optional_params=["time", "attendees", "facilitator", "team_member_1", "team_member_2", 
                           "team_member_3", "priority_1", "priority_2", "priority_3", "action_1", 
                           "owner_1", "due_1", "action_2", "owner_2", "due_2", "blocker_1", "risk_1",
                           "next_meeting_date", "next_focus"],
            estimated_duration=3,
            tags=["meeting", "standup", "team-management"],
            created_by="system",
            created_at=datetime.now()
        )
        
        # Learning Templates
        self.templates["deep_learning_session"] = WorkflowTemplate(
            name="Deep Learning Study Session",
            category=TemplateCategory.LEARNING,
            description="Structured approach to learning complex technical topics",
            steps=[
                {
                    "tool": "memcord_name",
                    "params": {"slot_name": "learn_{topic}_{session_number}"},
                    "description": "Create learning session slot"
                },
                {
                    "tool": "memcord_save",
                    "params": {
                        "chat_text": """# Learning Session: {topic} - Session {session_number}

## Session Overview
- **Topic:** {topic}
- **Date:** {date}
- **Duration Planned:** {duration} minutes
- **Session Type:** {session_type}
- **Difficulty Level:** {difficulty}

## Learning Objectives
- **Primary Goal:** {primary_objective}
- **Secondary Goals:** 
  - {secondary_1}
  - {secondary_2}
  - {secondary_3}

## Prerequisites Completed
- [ ] {prereq_1}
- [ ] {prereq_2}
- [ ] {prereq_3}

## Resources
- **Primary Resource:** {primary_resource}
- **Supplementary Resources:**
  - {resource_1}
  - {resource_2}
  - {resource_3}
- **Practice Materials:** {practice_materials}

## Session Notes
### Key Concepts
[Fill during session]

### Code Examples
[Add code snippets and explanations]

### Insights & Aha Moments
[Document breakthrough understanding]

### Questions & Confusions
[Note areas needing clarification]

## Practice Exercises
- [ ] Exercise 1: {exercise_1}
- [ ] Exercise 2: {exercise_2}
- [ ] Exercise 3: {exercise_3}

## Session Summary
### What I Learned
[Summary of key takeaways]

### What I Struggled With
[Areas for review or further study]

### Next Steps
- [ ] {next_step_1}
- [ ] {next_step_2}
- [ ] Review: {review_topic}

## Connections to Previous Learning
[How this connects to what I already know]

## Applications & Projects
[How I can apply this knowledge]"""
                    },
                    "description": "Create comprehensive learning template"
                },
                {
                    "tool": "memcord_tag",
                    "params": {
                        "action": "add",
                        "tags": ["learning", "{topic}", "education", "session-{session_number}"]
                    },
                    "description": "Tag learning session"
                },
                {
                    "tool": "memcord_group",
                    "params": {"action": "set", "group_path": "learning/{topic}"},
                    "description": "Organize in learning group"
                }
            ],
            required_params=["topic", "session_number", "date"],
            optional_params=["duration", "session_type", "difficulty", "primary_objective",
                           "secondary_1", "secondary_2", "secondary_3", "prereq_1", "prereq_2", 
                           "prereq_3", "primary_resource", "resource_1", "resource_2", "resource_3",
                           "practice_materials", "exercise_1", "exercise_2", "exercise_3",
                           "next_step_1", "next_step_2", "review_topic"],
            estimated_duration=4,
            tags=["learning", "education", "structured-study"],
            created_by="system", 
            created_at=datetime.now()
        )
        
        # Debugging Templates
        self.templates["systematic_debugging"] = WorkflowTemplate(
            name="Systematic Debugging Session", 
            category=TemplateCategory.DEBUGGING,
            description="Structured approach to troubleshooting and debugging",
            steps=[
                {
                    "tool": "memcord_name",
                    "params": {"slot_name": "debug_{issue_name}_{date}"},
                    "description": "Create debugging session slot"
                },
                {
                    "tool": "memcord_save",
                    "params": {
                        "chat_text": """# DEBUGGING SESSION - {issue_name}

## Issue Overview
- **Date:** {date}
- **Severity:** {severity}
- **Impact:** {impact}
- **Reporter:** {reporter}
- **Environment:** {environment}

## Problem Description
### What's Happening
{problem_description}

### Expected vs Actual Behavior
- **Expected:** {expected_behavior}
- **Actual:** {actual_behavior}

### When Did It Start
{when_started}

### Frequency
{frequency}

## Symptoms Observed
- {symptom_1}
- {symptom_2}
- {symptom_3}

## Environment Details
- **System:** {system_details}
- **Version:** {version}
- **Configuration:** {configuration}
- **Recent Changes:** {recent_changes}

## Initial Hypotheses
1. **Hypothesis 1:** {hypothesis_1}
   - **Confidence:** {confidence_1}
   - **How to test:** {test_1}

2. **Hypothesis 2:** {hypothesis_2}
   - **Confidence:** {confidence_2}
   - **How to test:** {test_2}

3. **Hypothesis 3:** {hypothesis_3}
   - **Confidence:** {confidence_3}
   - **How to test:** {test_3}

## Investigation Steps
### Step 1: {step_1}
- **Action:** {action_1}
- **Result:** [To be filled]
- **Conclusion:** [To be filled]

### Step 2: {step_2}
- **Action:** {action_2}
- **Result:** [To be filled]
- **Conclusion:** [To be filled]

### Step 3: {step_3}
- **Action:** {action_3}
- **Result:** [To be filled]
- **Conclusion:** [To be filled]

## Root Cause Analysis
### Root Cause
[To be determined through investigation]

### Why It Happened
[Analysis of underlying causes]

### Why It Wasn't Caught Earlier
[Process improvement insights]

## Solution
### Immediate Fix
[Short-term solution to resolve the issue]

### Long-term Solution
[Permanent fix and prevention measures]

### Verification Steps
- [ ] {verification_1}
- [ ] {verification_2}
- [ ] {verification_3}

## Prevention Measures
- {prevention_1}
- {prevention_2}
- {prevention_3}

## Lessons Learned
### Technical Insights
[Technical knowledge gained]

### Process Improvements
[How to prevent similar issues]

### Tool/Method Effectiveness
[What worked well, what didn't]

## Follow-up Actions
- [ ] {followup_1} - Due: {due_1}
- [ ] {followup_2} - Due: {due_2}
- [ ] {followup_3} - Due: {due_3}"""
                    },
                    "description": "Create systematic debugging template"
                },
                {
                    "tool": "memcord_tag", 
                    "params": {
                        "action": "add",
                        "tags": ["debugging", "troubleshooting", "{severity}", "{environment}"]
                    },
                    "description": "Tag debugging session"
                },
                {
                    "tool": "memcord_group",
                    "params": {"action": "set", "group_path": "troubleshooting/{environment}"},
                    "description": "Organize in troubleshooting group"
                }
            ],
            required_params=["issue_name", "date", "problem_description"],
            optional_params=["severity", "impact", "reporter", "environment", "expected_behavior",
                           "actual_behavior", "when_started", "frequency", "symptom_1", "symptom_2",
                           "symptom_3", "system_details", "version", "configuration", "recent_changes",
                           "hypothesis_1", "confidence_1", "test_1", "hypothesis_2", "confidence_2",
                           "test_2", "hypothesis_3", "confidence_3", "test_3", "step_1", "action_1",
                           "step_2", "action_2", "step_3", "action_3", "verification_1", 
                           "verification_2", "verification_3", "prevention_1", "prevention_2",
                           "prevention_3", "followup_1", "due_1", "followup_2", "due_2", 
                           "followup_3", "due_3"],
            estimated_duration=8,
            tags=["debugging", "troubleshooting", "systematic-approach"],
            created_by="system",
            created_at=datetime.now()
        )
        
        # Maintenance Templates
        self.templates["memory_maintenance"] = WorkflowTemplate(
            name="Memory Organization & Maintenance",
            category=TemplateCategory.MAINTENANCE,
            description="Regular maintenance workflow for memory optimization",
            steps=[
                {
                    "tool": "memcord_list",
                    "params": {},
                    "description": "Review current memory organization"
                },
                {
                    "tool": "memcord_compress",
                    "params": {"action": "analyze"},
                    "description": "Analyze compression opportunities"
                },
                {
                    "tool": "memcord_archive",
                    "params": {"action": "candidates", "days_inactive": 30},
                    "description": "Find archival candidates"
                },
                {
                    "tool": "memcord_compress",
                    "params": {"action": "compress"},
                    "description": "Compress eligible content"
                },
                {
                    "tool": "memcord_name",
                    "params": {"slot_name": "maintenance_log_{date}"},
                    "description": "Create maintenance log"
                },
                {
                    "tool": "memcord_save",
                    "params": {
                        "chat_text": """# Memory Maintenance Log - {date}

## Maintenance Tasks Completed
- [ ] Reviewed memory organization
- [ ] Analyzed compression opportunities  
- [ ] Identified archival candidates
- [ ] Compressed eligible content
- [ ] Cleaned up temporary slots
- [ ] Updated tags and groups
- [ ] Verified search functionality

## Statistics Before Maintenance
- Total Slots: {slots_before}
- Total Size: {size_before}
- Compression Rate: {compression_before}

## Actions Taken
### Compression
- Slots compressed: {compressed_count}
- Space saved: {space_saved}
- Compression ratio achieved: {compression_ratio}

### Archival
- Slots archived: {archived_count}
- Archive reason: {archive_reason}

### Organization
- Tags cleaned up: {tags_cleaned}
- Groups reorganized: {groups_reorganized}

## Statistics After Maintenance
- Total Slots: {slots_after}
- Total Size: {size_after}
- Compression Rate: {compression_after}

## Recommendations for Next Maintenance
- {recommendation_1}
- {recommendation_2}
- {recommendation_3}

## Next Maintenance Date
{next_maintenance_date}"""
                    },
                    "description": "Log maintenance activities"
                },
                {
                    "tool": "memcord_tag",
                    "params": {
                        "action": "add",
                        "tags": ["maintenance", "system", "optimization", "log"]
                    },
                    "description": "Tag maintenance log"
                },
                {
                    "tool": "memcord_group",
                    "params": {"action": "set", "group_path": "system/maintenance"},
                    "description": "Group maintenance log"
                }
            ],
            required_params=["date"],
            optional_params=["slots_before", "size_before", "compression_before", "compressed_count",
                           "space_saved", "compression_ratio", "archived_count", "archive_reason",
                           "tags_cleaned", "groups_reorganized", "slots_after", "size_after", 
                           "compression_after", "recommendation_1", "recommendation_2", 
                           "recommendation_3", "next_maintenance_date"],
            estimated_duration=10,
            tags=["maintenance", "optimization", "housekeeping"],
            created_by="system",
            created_at=datetime.now()
        )
    
    async def get_template(self, template_name: str) -> Optional[WorkflowTemplate]:
        """Get a specific template by name."""
        if template_name in self.templates:
            return self.templates[template_name]
        elif template_name in self.custom_templates:
            return self.custom_templates[template_name]
        return None
    
    async def list_templates(self, category: Optional[TemplateCategory] = None) -> List[WorkflowTemplate]:
        """List available templates, optionally filtered by category."""
        all_templates = list(self.templates.values()) + list(self.custom_templates.values())
        
        if category:
            return [t for t in all_templates if t.category == category]
        
        return all_templates
    
    async def execute_template(self, template_name: str, params: Dict[str, str],
                             automation: WorkflowAutomation, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a workflow template."""
        template = await self.get_template(template_name)
        if not template:
            raise ValueError(f"Template '{template_name}' not found")
        
        # Update usage statistics
        template.usage_count += 1
        
        # Execute the template
        result = await automation.execute_template(template_name, params, context)
        
        # Update success rate
        if result["steps_successful"] == result["steps_executed"]:
            template.success_rate = (template.success_rate * (template.usage_count - 1) + 1.0) / template.usage_count
        else:
            success = result["steps_successful"] / result["steps_executed"]
            template.success_rate = (template.success_rate * (template.usage_count - 1) + success) / template.usage_count
        
        return result
    
    async def create_custom_template(self, name: str, category: TemplateCategory,
                                   description: str, steps: List[Dict[str, Any]], 
                                   required_params: List[str], optional_params: List[str] = None) -> WorkflowTemplate:
        """Create a custom user template."""
        if optional_params is None:
            optional_params = []
        
        template = WorkflowTemplate(
            name=name,
            category=category,
            description=description,
            steps=steps,
            required_params=required_params,
            optional_params=optional_params,
            estimated_duration=len(steps) * 2,  # Rough estimate
            tags=["custom", category.value],
            created_by="user",
            created_at=datetime.now()
        )
        
        self.custom_templates[name] = template
        await self._save_custom_templates()
        
        return template
    
    def get_quick_actions(self, context: Dict[str, Any]) -> List[QuickAction]:
        """Get applicable quick actions for current context."""
        applicable_actions = []
        
        for action in self.quick_actions.values():
            # Check if context requirements are met
            if self._check_context_requirements(action.context_requirements, context):
                applicable_actions.append(action)
        
        # Sort by usage count and success rate
        applicable_actions.sort(key=lambda x: (x.usage_count * x.success_rate), reverse=True)
        
        return applicable_actions[:5]  # Top 5 actions
    
    def _check_context_requirements(self, requirements: Dict[str, Any], context: Dict[str, Any]) -> bool:
        """Check if context meets requirements for a quick action."""
        for req_key, req_value in requirements.items():
            if req_key not in context:
                return False

            if isinstance(req_value, list):
                if context[req_key] not in req_value:
                    return False
            elif isinstance(req_value, str) and req_value.startswith((">", "<", ">=", "<=")):
                # Handle comparison operators
                try:
                    if req_value.startswith(">="):
                        threshold = int(req_value[2:].strip())
                        if not (isinstance(context[req_key], (int, float)) and context[req_key] >= threshold):
                            return False
                    elif req_value.startswith("<="):
                        threshold = int(req_value[2:].strip())
                        if not (isinstance(context[req_key], (int, float)) and context[req_key] <= threshold):
                            return False
                    elif req_value.startswith(">"):
                        threshold = int(req_value[1:].strip())
                        if not (isinstance(context[req_key], (int, float)) and context[req_key] > threshold):
                            return False
                    elif req_value.startswith("<"):
                        threshold = int(req_value[1:].strip())
                        if not (isinstance(context[req_key], (int, float)) and context[req_key] < threshold):
                            return False
                except (ValueError, TypeError):
                    return False
            elif context[req_key] != req_value:
                return False

        return True
    
    async def _load_custom_templates(self):
        """Load custom templates from disk."""
        try:
            if self.templates_file.exists():
                async with aiofiles.open(self.templates_file, 'r') as f:
                    content = await f.read()
                    templates_data = json.loads(content)
                    
                    for name, template_dict in templates_data.items():
                        # Convert string back to enum and datetime
                        template_dict["category"] = TemplateCategory(template_dict["category"])
                        template_dict["created_at"] = datetime.fromisoformat(template_dict["created_at"])
                        self.custom_templates[name] = WorkflowTemplate(**template_dict)
        except Exception:
            # If loading fails, start with empty custom templates
            self.custom_templates = {}
    
    async def _load_quick_actions(self):
        """Load quick actions from disk."""
        try:
            if self.quick_actions_file.exists():
                async with aiofiles.open(self.quick_actions_file, 'r') as f:
                    content = await f.read()
                    actions_data = json.loads(content)

                    for name, action_dict in actions_data.items():
                        self.quick_actions[name] = QuickAction(**action_dict)
            else:
                # No quick actions file exists, create default ones
                self._create_default_quick_actions()
        except Exception:
            # If loading fails, start with default quick actions
            self._create_default_quick_actions()
    
    def _create_default_quick_actions(self):
        """Create default quick actions."""
        self.quick_actions = {
            "quick_save_and_tag": QuickAction(
                name="Quick Save and Tag",
                description="Save content and immediately add tags",
                tool_combination=[
                    {"tool": "memcord_save", "params": {"chat_text": "{content}"}},
                    {"tool": "memcord_tag", "params": {"action": "add", "tags": ["{tag_1}", "{tag_2}"]}}
                ],
                trigger_keywords=["save and tag", "quick save"],
                context_requirements={"has_content": True, "has_active_slot": True}
            ),
            
            "save_compress_read": QuickAction(
                name="Save, Compress, and Verify", 
                description="Save content with summarization and verify",
                tool_combination=[
                    {"tool": "memcord_save_progress", "params": {"chat_text": "{content}", "compression_ratio": 0.15}},
                    {"tool": "memcord_read", "params": {}}
                ],
                trigger_keywords=["save and verify", "save compress"],
                context_requirements={"has_content": True, "content_length": "> 500"}
            ),
            
            "search_and_read": QuickAction(
                name="Search and Read Results",
                description="Search for content and read the top result",
                tool_combination=[
                    {"tool": "memcord_search", "params": {"query": "{query}", "max_results": 3}},
                    {"tool": "memcord_read", "params": {"slot_name": "{result_slot}"}}
                ],
                trigger_keywords=["find and read", "search read"],
                context_requirements={"has_query": True}
            ),
            
            "project_setup_quick": QuickAction(
                name="Quick Project Setup",
                description="Rapidly set up a new project with basic organization",
                tool_combination=[
                    {"tool": "memcord_name", "params": {"slot_name": "proj_{project}"}},
                    {"tool": "memcord_tag", "params": {"action": "add", "tags": ["project", "{project}", "active"]}},
                    {"tool": "memcord_group", "params": {"action": "set", "group_path": "projects/{project}"}}
                ],
                trigger_keywords=["new project", "project setup"],
                context_requirements={"has_project_name": True}
            ),
            
            "meeting_wrap": QuickAction(
                name="Meeting Wrap-up",
                description="Quickly wrap up meeting notes with organization",
                tool_combination=[
                    {"tool": "memcord_save", "params": {"chat_text": "Meeting ended: {time}\n\nAction Items:\n{actions}\n\nNext Meeting: {next_date}"}},
                    {"tool": "memcord_tag", "params": {"action": "add", "tags": ["meeting", "completed", "{meeting_type}"]}},
                    {"tool": "memcord_group", "params": {"action": "set", "group_path": "meetings/{meeting_type}"}}
                ],
                trigger_keywords=["wrap meeting", "end meeting", "meeting done"],
                context_requirements={"current_slot_type": "meeting"}
            )
        }
    
    async def _save_custom_templates(self):
        """Save custom templates to disk."""
        try:
            templates_data = {}
            for name, template in self.custom_templates.items():
                template_dict = asdict(template)
                # Convert enum and datetime to strings for JSON serialization
                template_dict["category"] = template.category.value
                template_dict["created_at"] = template.created_at.isoformat()
                templates_data[name] = template_dict
            
            async with aiofiles.open(self.templates_file, 'w') as f:
                await f.write(json.dumps(templates_data, indent=2))
        except Exception as e:
            print(f"Failed to save custom templates: {e}")
    
    async def save_quick_actions(self):
        """Save quick actions to disk."""
        try:
            actions_data = {}
            for name, action in self.quick_actions.items():
                actions_data[name] = asdict(action)
            
            async with aiofiles.open(self.quick_actions_file, 'w') as f:
                await f.write(json.dumps(actions_data, indent=2))
        except Exception as e:
            print(f"Failed to save quick actions: {e}")


# Integration helper functions
def fill_template_defaults(params: Dict[str, str]) -> Dict[str, str]:
    """Fill common template parameters with default values."""
    filled_params = params.copy()
    
    now = datetime.now()
    
    # Date and time defaults
    if "date" not in filled_params:
        filled_params["date"] = now.strftime("%Y_%m_%d")
    
    if "time" not in filled_params:
        filled_params["time"] = now.strftime("%H:%M")
    
    if "datetime" not in filled_params:
        filled_params["datetime"] = now.strftime("%Y-%m-%d %H:%M:%S")
    
    if "iso_date" not in filled_params:
        filled_params["iso_date"] = now.isoformat()
    
    # Week-related defaults
    if "week_of" not in filled_params:
        filled_params["week_of"] = now.strftime("%Y_W%U")
    
    if "month_year" not in filled_params:
        filled_params["month_year"] = now.strftime("%Y_%m")
    
    # Session numbering (simple default)
    if "session_number" not in filled_params:
        filled_params["session_number"] = "1"
    
    return filled_params


def suggest_template_from_context(context: Dict[str, Any]) -> List[str]:
    """Suggest templates based on current context."""
    suggestions = []
    
    # Time-based suggestions
    now = datetime.now()
    day_of_week = now.weekday()  # 0 = Monday
    hour = now.hour
    
    # Monday morning - suggest weekly planning
    if day_of_week == 0 and 8 <= hour <= 10:
        suggestions.append("weekly_standup")
    
    # End of day - suggest wrap-up templates
    if 17 <= hour <= 19:
        suggestions.append("daily_wrap_up")
    
    # Context-based suggestions
    current_slot = context.get("current_slot", "")
    
    if current_slot.startswith("debug_") or "debug" in current_slot:
        suggestions.append("systematic_debugging")
    
    if current_slot.startswith("learn_") or "learn" in current_slot:
        suggestions.append("deep_learning_session")
    
    if current_slot.startswith("meet_") or "meeting" in current_slot:
        suggestions.append("weekly_standup")
    
    if current_slot.startswith("proj_") or "project" in current_slot:
        suggestions.append("new_web_project")
    
    # Activity-based suggestions
    recent_tools = context.get("recent_tools", [])
    
    if "memcord_compress" in recent_tools or "memcord_archive" in recent_tools:
        suggestions.append("memory_maintenance")
    
    return suggestions[:3]  # Top 3 suggestions