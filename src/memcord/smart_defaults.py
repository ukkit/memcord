"""Smart defaults and automation system for memcord.

This module implements intelligent defaults based on user patterns, context-aware suggestions,
and workflow automation to improve user experience and reduce cognitive load.
"""

import json
import asyncio
import aiofiles
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple, Set
from datetime import datetime, timedelta
from collections import defaultdict, Counter
from dataclasses import dataclass, asdict
import re

from .models import MemorySlot, MemoryEntry


@dataclass
class UserPreference:
    """Represents a learned user preference."""
    key: str
    value: Any
    confidence: float
    usage_count: int
    last_used: datetime
    context: Dict[str, Any]


@dataclass
class WorkflowPattern:
    """Represents a detected user workflow pattern."""
    name: str
    commands: List[str]
    frequency: int
    average_duration: float
    success_rate: float
    contexts: List[Dict[str, Any]]
    last_used: datetime


@dataclass
class SmartSuggestion:
    """Represents a contextual suggestion for the user."""
    tool_name: str
    parameters: Dict[str, Any]
    reason: str
    confidence: float
    category: str  # "workflow", "completion", "optimization"


class PreferenceLearningEngine:
    """Learns and applies user preferences for intelligent defaults."""
    
    def __init__(self, storage_dir: Path):
        self.storage_dir = storage_dir
        self.preferences_file = storage_dir / "user_preferences.json"
        self.patterns_file = storage_dir / "workflow_patterns.json"
        self.preferences: Dict[str, UserPreference] = {}
        self.workflow_patterns: Dict[str, WorkflowPattern] = {}
        self.command_history: List[Dict[str, Any]] = []
        self.max_history = 1000
    
    async def initialize(self):
        """Initialize the preference learning engine."""
        await self._load_preferences()
        await self._load_workflow_patterns()
    
    async def record_command(self, tool_name: str, parameters: Dict[str, Any], 
                           context: Dict[str, Any], success: bool = True):
        """Record a command execution for learning."""
        command_record = {
            "tool_name": tool_name,
            "parameters": parameters,
            "context": context,
            "timestamp": datetime.now().isoformat(),
            "success": success
        }
        
        self.command_history.append(command_record)
        
        # Keep history within limits
        if len(self.command_history) > self.max_history:
            self.command_history = self.command_history[-self.max_history:]
        
        # Learn from this command
        self._learn_from_command(command_record)
        
        # Update workflow patterns
        await self._update_workflow_patterns()
    
    async def get_smart_defaults(self, tool_name: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Get intelligent default values for a tool based on learned preferences."""
        defaults = {}
        
        # Get preference-based defaults
        preference_defaults = self._get_preference_defaults(tool_name, context)
        defaults.update(preference_defaults)
        
        # Get context-aware defaults
        context_defaults = self._get_context_defaults(tool_name, context)
        defaults.update(context_defaults)
        
        # Get pattern-based defaults
        pattern_defaults = self._get_pattern_defaults(tool_name, context)
        defaults.update(pattern_defaults)
        
        return defaults
    
    async def get_smart_suggestions(self, current_tool: str, context: Dict[str, Any]) -> List[SmartSuggestion]:
        """Get contextual suggestions for next actions."""
        suggestions = []
        
        # Workflow-based suggestions
        workflow_suggestions = self._get_workflow_suggestions(current_tool, context)
        suggestions.extend(workflow_suggestions)
        
        # Pattern completion suggestions
        completion_suggestions = self._get_completion_suggestions(current_tool, context)
        suggestions.extend(completion_suggestions)
        
        # Optimization suggestions
        optimization_suggestions = self._get_optimization_suggestions(current_tool, context)
        suggestions.extend(optimization_suggestions)
        
        # Sort by confidence and return top suggestions
        suggestions.sort(key=lambda x: x.confidence, reverse=True)
        return suggestions[:5]
    
    async def get_auto_completions(self, tool_name: str, parameter: str, 
                                 partial_value: str, context: Dict[str, Any]) -> List[str]:
        """Get auto-completion suggestions for parameter values."""
        completions = []
        
        if parameter == "slot_name":
            completions.extend(self._get_slot_name_completions(partial_value, context))
        elif parameter == "tags":
            completions.extend(self._get_tag_completions(partial_value, context))
        elif parameter == "query":
            completions.extend(self._get_query_completions(partial_value, context))
        elif parameter == "group_path":
            completions.extend(self._get_group_completions(partial_value, context))
        
        return completions[:10]  # Return top 10 completions
    
    def _learn_from_command(self, command_record: Dict[str, Any]):
        """Learn preferences from a command execution."""
        tool_name = command_record["tool_name"]
        parameters = command_record["parameters"]
        context = command_record["context"]
        
        # Learn parameter preferences
        for param, value in parameters.items():
            preference_key = f"{tool_name}.{param}"
            
            if preference_key in self.preferences:
                pref = self.preferences[preference_key]
                pref.usage_count += 1
                pref.last_used = datetime.now()
                # Update confidence based on consistency
                if pref.value == value:
                    pref.confidence = min(1.0, pref.confidence + 0.1)
                else:
                    pref.confidence = max(0.0, pref.confidence - 0.15)  # More aggressive penalty for inconsistency
                    pref.value = value  # Update to most recent value
            else:
                self.preferences[preference_key] = UserPreference(
                    key=preference_key,
                    value=value,
                    confidence=0.6,  # Starting confidence
                    usage_count=1,
                    last_used=datetime.now(),
                    context=context
                )
        
        # Learn contextual patterns
        self._learn_contextual_patterns(tool_name, parameters, context)
    
    def _learn_contextual_patterns(self, tool_name: str, parameters: Dict[str, Any], context: Dict[str, Any]):
        """Learn patterns based on context."""
        # Learn slot naming patterns
        if tool_name == "memcord_name" and "slot_name" in parameters:
            slot_name = parameters["slot_name"]
            self._learn_naming_pattern(slot_name, context)
        
        # Learn tagging patterns
        if "tags" in parameters:
            tags = parameters["tags"]
            self._learn_tagging_patterns(tags, context)
        
        # Learn compression preferences
        if "compression_ratio" in parameters:
            ratio = parameters["compression_ratio"]
            self._learn_compression_preferences(ratio, context)
    
    def _learn_naming_pattern(self, slot_name: str, context: Dict[str, Any]):
        """Learn user's naming conventions."""
        # Extract naming patterns
        patterns = []
        
        # Check for common prefixes
        prefixes = ["proj_", "meet_", "learn_", "debug_", "temp_", "test_"]
        for prefix in prefixes:
            if slot_name.startswith(prefix):
                patterns.append(f"prefix_{prefix}")
        
        # Check for date patterns
        if re.search(r'\d{4}[-_]\d{2}[-_]\d{2}', slot_name):
            patterns.append("includes_date")
        
        # Check for versioning
        if re.search(r'v\d+|version\d+|_\d+$', slot_name):
            patterns.append("includes_version")
        
        # Store patterns as preferences
        for pattern in patterns:
            key = f"naming_pattern.{pattern}"
            if key in self.preferences:
                self.preferences[key].usage_count += 1
                self.preferences[key].confidence = min(1.0, self.preferences[key].confidence + 0.05)
            else:
                self.preferences[key] = UserPreference(
                    key=key,
                    value=True,
                    confidence=0.4,
                    usage_count=1,
                    last_used=datetime.now(),
                    context=context
                )
    
    def _learn_tagging_patterns(self, tags: List[str], context: Dict[str, Any]):
        """Learn user's tagging preferences."""
        for tag in tags:
            key = f"common_tag.{tag}"
            if key in self.preferences:
                self.preferences[key].usage_count += 1
                self.preferences[key].confidence = min(1.0, self.preferences[key].confidence + 0.02)
            else:
                self.preferences[key] = UserPreference(
                    key=key,
                    value=tag,
                    confidence=0.3,
                    usage_count=1,
                    last_used=datetime.now(),
                    context=context
                )
    
    def _learn_compression_preferences(self, ratio: float, context: Dict[str, Any]):
        """Learn compression ratio preferences by content type."""
        content_type = context.get("content_type", "general")
        key = f"compression_ratio.{content_type}"
        
        if key in self.preferences:
            # Weighted average with new ratio
            current = self.preferences[key]
            current.value = (current.value * current.usage_count + ratio) / (current.usage_count + 1)
            current.usage_count += 1
            current.confidence = min(1.0, current.confidence + 0.05)
        else:
            self.preferences[key] = UserPreference(
                key=key,
                value=ratio,
                confidence=0.5,
                usage_count=1,
                last_used=datetime.now(),
                context=context
            )
    
    def _get_preference_defaults(self, tool_name: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Get defaults based on learned preferences."""
        defaults = {}
        
        # Look for tool-specific preferences
        for key, pref in self.preferences.items():
            if key.startswith(f"{tool_name}.") and pref.confidence > 0.6:
                param_name = key.split(".", 1)[1]
                defaults[param_name] = pref.value
        
        return defaults
    
    def _get_context_defaults(self, tool_name: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Get defaults based on current context."""
        defaults = {}
        
        # Time-based defaults
        current_hour = datetime.now().hour
        if 9 <= current_hour <= 17:  # Work hours
            if tool_name == "memcord_name" and not context.get("current_slot"):
                # Suggest work-related naming during work hours
                date_suffix = datetime.now().strftime("%Y_%m_%d")
                defaults["suggested_prefix"] = f"work_{date_suffix}_"
        
        # Project context defaults
        current_slot = context.get("current_slot")
        if current_slot:
            # Infer project from current slot
            if current_slot.startswith("proj_"):
                project_name = current_slot.split("proj_")[1].split("_")[0]
                if tool_name == "memcord_tag":
                    defaults["suggested_tags"] = [project_name, "project"]
                elif tool_name == "memcord_group":
                    defaults["suggested_group_path"] = f"projects/{project_name}"
        
        # Compression defaults based on content analysis
        if tool_name == "memcord_save_progress":
            content_length = context.get("content_length", 0)
            if content_length > 5000:  # Long content
                defaults["compression_ratio"] = 0.2  # More aggressive
            elif content_length > 1000:  # Medium content
                defaults["compression_ratio"] = 0.3
            else:  # Short content
                defaults["compression_ratio"] = 0.4  # Less aggressive
        
        return defaults
    
    def _get_pattern_defaults(self, tool_name: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Get defaults based on detected patterns."""
        defaults = {}
        
        # Recent command patterns
        recent_commands = self.command_history[-10:]  # Last 10 commands
        
        if tool_name == "memcord_name":
            # Look for naming patterns in recent slot creations
            recent_slots = [cmd["parameters"].get("slot_name") for cmd in recent_commands 
                          if cmd["tool_name"] == "memcord_name" and "slot_name" in cmd["parameters"]]
            
            if recent_slots:
                # Detect common prefixes
                prefix_counts = Counter()
                for slot in recent_slots:
                    parts = slot.split("_")
                    if len(parts) > 1:
                        prefix_counts[parts[0] + "_"] += 1
                
                if prefix_counts:
                    most_common_prefix = prefix_counts.most_common(1)[0][0]
                    defaults["suggested_prefix"] = most_common_prefix
        
        return defaults
    
    def _get_workflow_suggestions(self, current_tool: str, context: Dict[str, Any]) -> List[SmartSuggestion]:
        """Get workflow-based suggestions."""
        suggestions = []
        
        # Common workflow patterns
        workflow_patterns = {
            "memcord_name": [
                ("memcord_save", "Save initial content to new memory slot"),
                ("memcord_tag", "Add organizational tags to new slot"),
                ("memcord_group", "Organize slot into a group")
            ],
            "memcord_save": [
                ("memcord_read", "Verify saved content"),
                ("memcord_tag", "Add tags for organization"),
                ("memcord_search", "Test searchability of saved content")
            ],
            "memcord_search": [
                ("memcord_read", "Read full content from search results"),
                ("memcord_select_entry", "Access specific entries from results"),
                ("memcord_query", "Ask follow-up questions about found content")
            ],
            "memcord_list": [
                ("memcord_compress", "Optimize storage for large slots"),
                ("memcord_archive", "Archive inactive slots"),
                ("memcord_merge", "Consolidate related slots")
            ]
        }
        
        if current_tool in workflow_patterns:
            for next_tool, reason in workflow_patterns[current_tool]:
                # Adjust confidence based on context
                confidence = 0.7
                if next_tool == "memcord_tag" and context.get("has_tags"):
                    confidence = 0.5  # Lower confidence if tags already exist

                suggestions.append(SmartSuggestion(
                    tool_name=next_tool,
                    parameters={},
                    reason=reason,
                    confidence=confidence,
                    category="workflow"
                ))
        
        return suggestions
    
    def _get_completion_suggestions(self, current_tool: str, context: Dict[str, Any]) -> List[SmartSuggestion]:
        """Get pattern completion suggestions."""
        suggestions = []
        
        # Look for incomplete workflows
        recent_commands = [cmd["tool_name"] for cmd in self.command_history[-5:]]
        
        # Detect incomplete save workflow
        if "memcord_save" in recent_commands and "memcord_read" not in recent_commands:
            suggestions.append(SmartSuggestion(
                tool_name="memcord_read",
                parameters={},
                reason="Verify your recent save was successful",
                confidence=0.8,
                category="completion"
            ))
        
        # Detect unorganized content
        if current_tool == "memcord_save" and not context.get("has_tags"):
            suggestions.append(SmartSuggestion(
                tool_name="memcord_tag",
                parameters={"action": "add", "tags": self._suggest_tags_for_content(context)},
                reason="Add tags for better organization and searchability",
                confidence=0.6,
                category="completion"
            ))
        
        return suggestions
    
    def _get_optimization_suggestions(self, current_tool: str, context: Dict[str, Any]) -> List[SmartSuggestion]:
        """Get optimization suggestions."""
        suggestions = []
        
        # Storage optimization
        if context.get("slot_size", 0) > 50000:  # Large slot
            suggestions.append(SmartSuggestion(
                tool_name="memcord_compress",
                parameters={"action": "analyze"},
                reason="Analyze compression potential for large memory slot",
                confidence=0.7,
                category="optimization"
            ))
        
        # Archive suggestions
        inactive_days = context.get("days_since_last_update", 0)
        if inactive_days > 30:
            suggestions.append(SmartSuggestion(
                tool_name="memcord_archive",
                parameters={"action": "candidates"},
                reason="Consider archiving inactive memory slots",
                confidence=0.6,
                category="optimization"
            ))
        
        return suggestions
    
    def _suggest_tags_for_content(self, context: Dict[str, Any]) -> List[str]:
        """Suggest tags based on content analysis."""
        suggested_tags = []
        
        # Use common tags from preferences
        common_tags = [pref.value for key, pref in self.preferences.items() 
                      if key.startswith("common_tag.") and pref.confidence > 0.5]
        suggested_tags.extend(common_tags[:3])  # Top 3 common tags
        
        # Content-based suggestions
        content = context.get("content", "").lower()
        
        # Technical terms
        if any(term in content for term in ["api", "endpoint", "service", "database"]):
            suggested_tags.append("technical")
        
        # Learning content
        if any(term in content for term in ["learn", "tutorial", "documentation", "guide"]):
            suggested_tags.append("learning")
        
        # Project content
        if any(term in content for term in ["project", "implementation", "development"]):
            suggested_tags.append("project")
        
        return suggested_tags[:5]  # Max 5 suggestions
    
    def _get_slot_name_completions(self, partial_value: str, context: Dict[str, Any]) -> List[str]:
        """Get slot name auto-completions."""
        completions = []
        
        # Get existing slot names from recent history
        recent_slots = set()
        for cmd in self.command_history:
            if "slot_name" in cmd["parameters"]:
                slot_name = cmd["parameters"]["slot_name"]
                if slot_name.startswith(partial_value):
                    recent_slots.add(slot_name)
        
        completions.extend(list(recent_slots))
        
        # Suggest patterns based on partial input
        if partial_value:
            # Common prefixes
            if partial_value.startswith("proj"):
                completions.extend([f"proj_{datetime.now().strftime('%Y_%m_%d')}",
                                  f"proj_{partial_value[5:]}_frontend",
                                  f"proj_{partial_value[5:]}_backend"])
            elif partial_value.startswith("meet"):
                completions.extend([f"meet_{datetime.now().strftime('%Y_%m_%d')}",
                                  f"meet_team_{datetime.now().strftime('%m_%d')}",
                                  f"meet_standup_{datetime.now().strftime('%m_%d')}"])
            elif partial_value.startswith("learn"):
                completions.extend([f"learn_{partial_value[6:]}_basics",
                                  f"learn_{partial_value[6:]}_advanced",
                                  f"learn_{partial_value[6:]}_tutorial"])
        
        return list(set(completions))
    
    def _get_tag_completions(self, partial_value: str, context: Dict[str, Any]) -> List[str]:
        """Get tag auto-completions."""
        completions = []
        
        # Get commonly used tags
        common_tags = [pref.value for key, pref in self.preferences.items()
                      if key.startswith("common_tag.") and 
                      str(pref.value).startswith(partial_value)]
        completions.extend(common_tags)
        
        # Standard tag suggestions
        standard_tags = ["project", "learning", "meeting", "technical", "research", 
                        "debugging", "planning", "documentation", "testing", "archived"]
        completions.extend([tag for tag in standard_tags if tag.startswith(partial_value)])
        
        return list(set(completions))
    
    def _get_query_completions(self, partial_value: str, context: Dict[str, Any]) -> List[str]:
        """Get search query auto-completions."""
        completions = []
        
        # Recent search queries
        recent_queries = [cmd["parameters"].get("query", "") for cmd in self.command_history
                         if cmd["tool_name"] == "memcord_search" and "query" in cmd["parameters"]]
        
        matching_queries = [q for q in recent_queries if q.startswith(partial_value)]
        completions.extend(matching_queries)
        
        # Common search patterns
        if len(partial_value) >= 3:
            common_patterns = [
                f"{partial_value} AND error",
                f"{partial_value} OR problem",
                f"{partial_value} NOT deprecated",
                f'"{partial_value}"'  # Exact phrase
            ]
            completions.extend(common_patterns)
        
        return list(set(completions))[:10]
    
    def _get_group_completions(self, partial_value: str, context: Dict[str, Any]) -> List[str]:
        """Get group path auto-completions."""
        completions = []
        
        # Recent group paths
        recent_groups = [cmd["parameters"].get("group_path", "") for cmd in self.command_history
                        if "group_path" in cmd["parameters"]]
        
        # Add matching existing groups
        matching_groups = [g for g in recent_groups if g.startswith(partial_value)]
        completions.extend(matching_groups)
        
        # Suggest hierarchical completions
        if "/" in partial_value:
            base_path = "/".join(partial_value.split("/")[:-1])
            # Suggest common sub-paths
            common_subs = ["frontend", "backend", "database", "testing", "documentation"]
            completions.extend([f"{base_path}/{sub}" for sub in common_subs])
        else:
            # Suggest top-level groups
            common_groups = ["projects", "learning", "meetings", "research", "documentation"]
            completions.extend([g for g in common_groups if g.startswith(partial_value)])
        
        return list(set(completions))
    
    async def _update_workflow_patterns(self):
        """Update workflow patterns based on recent command sequences."""
        if len(self.command_history) < 3:
            return
        
        # Only analyze the most recent sequence to avoid over-counting
        recent_commands = self.command_history[-5:]  # Look at last 5 commands
        
        # Analyze sequences of 3 commands (most common useful pattern)
        if len(recent_commands) >= 3:
            # Take the most recent 3-command sequence
            sequence = recent_commands[-3:]
            if all(cmd["success"] for cmd in sequence):  # Only successful sequences
                pattern_name = "_".join(cmd["tool_name"] for cmd in sequence)
                
                if pattern_name in self.workflow_patterns:
                    pattern = self.workflow_patterns[pattern_name]
                    pattern.frequency += 1
                    pattern.last_used = datetime.now()
                    # Keep only the most recent contexts (limit memory usage)
                    pattern.contexts = pattern.contexts[-3:] + [cmd["context"] for cmd in sequence]
                else:
                    self.workflow_patterns[pattern_name] = WorkflowPattern(
                        name=pattern_name,
                        commands=[cmd["tool_name"] for cmd in sequence],
                        frequency=1,
                        average_duration=0.0,  # Could be calculated if we track timing
                        success_rate=1.0,
                        contexts=[cmd["context"] for cmd in sequence],
                        last_used=datetime.now()
                    )
    
    async def _load_preferences(self):
        """Load preferences from disk."""
        try:
            if self.preferences_file.exists():
                async with aiofiles.open(self.preferences_file, 'r') as f:
                    content = await f.read()
                    prefs_data = json.loads(content)
                    
                    for key, pref_dict in prefs_data.items():
                        # Convert timestamp string back to datetime
                        pref_dict["last_used"] = datetime.fromisoformat(pref_dict["last_used"])
                        self.preferences[key] = UserPreference(**pref_dict)
        except Exception:
            # If loading fails, start with empty preferences
            self.preferences = {}
    
    async def _load_workflow_patterns(self):
        """Load workflow patterns from disk."""
        try:
            if self.patterns_file.exists():
                async with aiofiles.open(self.patterns_file, 'r') as f:
                    content = await f.read()
                    patterns_data = json.loads(content)
                    
                    for name, pattern_dict in patterns_data.items():
                        # Convert timestamp string back to datetime
                        pattern_dict["last_used"] = datetime.fromisoformat(pattern_dict["last_used"])
                        self.workflow_patterns[name] = WorkflowPattern(**pattern_dict)
        except Exception:
            # If loading fails, start with empty patterns
            self.workflow_patterns = {}
    
    async def save_preferences(self):
        """Save preferences to disk."""
        try:
            prefs_data = {}
            for key, pref in self.preferences.items():
                pref_dict = asdict(pref)
                # Convert datetime to string for JSON serialization
                pref_dict["last_used"] = pref.last_used.isoformat()
                prefs_data[key] = pref_dict
            
            async with aiofiles.open(self.preferences_file, 'w') as f:
                await f.write(json.dumps(prefs_data, indent=2))
        except Exception as e:
            # Log error but don't fail the operation
            print(f"Failed to save preferences: {e}")
    
    async def save_workflow_patterns(self):
        """Save workflow patterns to disk."""
        try:
            patterns_data = {}
            for name, pattern in self.workflow_patterns.items():
                pattern_dict = asdict(pattern)
                # Convert datetime to string for JSON serialization  
                pattern_dict["last_used"] = pattern.last_used.isoformat()
                patterns_data[name] = pattern_dict
            
            async with aiofiles.open(self.patterns_file, 'w') as f:
                await f.write(json.dumps(patterns_data, indent=2))
        except Exception as e:
            # Log error but don't fail the operation
            print(f"Failed to save workflow patterns: {e}")


class WorkflowAutomation:
    """Handles workflow automation and batch operations."""
    
    def __init__(self, storage_manager, preference_engine: PreferenceLearningEngine):
        self.storage_manager = storage_manager
        self.preference_engine = preference_engine
        self.templates = self._initialize_templates()
        self.macros: Dict[str, List[Dict[str, Any]]] = {}
        self.tool_executors: Dict[str, Any] = {}  # For testing/mocking
    
    def _initialize_templates(self) -> Dict[str, Dict[str, Any]]:
        """Initialize common workflow templates."""
        return {
            "new_project": {
                "name": "New Project Setup",
                "description": "Set up a new project with organized memory slots",
                "steps": [
                    {"tool": "memcord_name", "params": {"slot_name": "{project_name}"}},
                    {"tool": "memcord_tag", "params": {"action": "add", "tags": ["project", "{project_name}"]}},
                    {"tool": "memcord_group", "params": {"action": "set", "group_path": "projects/{project_name}"}},
                    {"tool": "memcord_save", "params": {"chat_text": "Project: {project_name}\nStarted: {date}\n\nGoals:\n- {goal_1}\n- {goal_2}\n\nNext Steps:\n- {next_step}"}}
                ],
                "required_params": ["project_name"],
                "optional_params": ["goal_1", "goal_2", "next_step"]
            },
            
            "daily_standup": {
                "name": "Daily Standup Meeting",
                "description": "Set up memory slot for daily standup notes",
                "steps": [
                    {"tool": "memcord_name", "params": {"slot_name": "standup_{date}"}},
                    {"tool": "memcord_tag", "params": {"action": "add", "tags": ["meeting", "standup", "daily"]}},
                    {"tool": "memcord_group", "params": {"action": "set", "group_path": "meetings/daily_standups"}},
                    {"tool": "memcord_save", "params": {"chat_text": "Daily Standup - {date}\n\nAttendees: {attendees}\n\nYesterday's Progress:\n- \n\nToday's Plans:\n- \n\nBlockers:\n- \n\nAction Items:\n- "}}
                ],
                "required_params": ["date"],
                "optional_params": ["attendees"]
            },
            
            "learning_session": {
                "name": "Learning Session Setup",
                "description": "Organize a focused learning session",
                "steps": [
                    {"tool": "memcord_name", "params": {"slot_name": "learn_{topic}_{date}"}},
                    {"tool": "memcord_tag", "params": {"action": "add", "tags": ["learning", "{topic}", "education"]}},
                    {"tool": "memcord_group", "params": {"action": "set", "group_path": "learning/{topic}"}},
                    {"tool": "memcord_save", "params": {"chat_text": "Learning Session: {topic}\nDate: {date}\n\nLearning Objectives:\n- {objective_1}\n- {objective_2}\n\nResources:\n- {resource_1}\n\nKey Insights:\n[To be filled during session]\n\nNext Steps:\n[To be determined]"}}
                ],
                "required_params": ["topic", "date"],
                "optional_params": ["objective_1", "objective_2", "resource_1"]
            },
            
            "troubleshooting_session": {
                "name": "Troubleshooting Session",
                "description": "Document a troubleshooting process",
                "steps": [
                    {"tool": "memcord_name", "params": {"slot_name": "debug_{issue}_{date}"}},
                    {"tool": "memcord_tag", "params": {"action": "add", "tags": ["debugging", "troubleshooting", "{category}"]}},
                    {"tool": "memcord_group", "params": {"action": "set", "group_path": "troubleshooting/{category}"}},
                    {"tool": "memcord_save", "params": {"chat_text": "TROUBLESHOOTING SESSION - {issue}\nDate: {date}\n\nPROBLEM DESCRIPTION:\n{problem_description}\n\nSYMPTOMS:\n- {symptom_1}\n\nENVIRONMENT:\n- {environment}\n\nTROUBLESHOOTING STEPS:\n1. \n\nSOLUTION:\n[To be documented]\n\nLESSONS LEARNED:\n[To be filled]"}}
                ],
                "required_params": ["issue", "date", "problem_description"],
                "optional_params": ["category", "symptom_1", "environment"]
            }
        }
    
    async def execute_template(self, template_name: str, params: Dict[str, str], 
                             context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a workflow template with provided parameters."""
        if template_name not in self.templates:
            raise ValueError(f"Template '{template_name}' not found")
        
        template = self.templates[template_name]
        results = []
        
        # Fill in default parameters
        filled_params = self._fill_template_params(params)
        
        # Execute each step
        for step in template["steps"]:
            try:
                # Fill in parameters for this step
                step_params = self._substitute_params(step["params"], filled_params)
                
                # Execute the tool
                result = await self._execute_tool(step["tool"], step_params, context)
                results.append({
                    "tool": step["tool"],
                    "params": step_params,
                    "success": True,
                    "result": result
                })
                
                # Record for learning
                await self.preference_engine.record_command(
                    step["tool"], step_params, context, success=True
                )
                
            except Exception as e:
                results.append({
                    "tool": step["tool"],
                    "params": step.get("params", {}),
                    "success": False,
                    "error": str(e)
                })
                break  # Stop on first failure
        
        return {
            "template_name": template_name,
            "steps_executed": len(results),
            "steps_successful": len([r for r in results if r["success"]]),
            "results": results
        }
    
    async def batch_operation(self, operations: List[Dict[str, Any]], 
                            context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute multiple operations as a batch."""
        results = []
        
        for op in operations:
            try:
                tool_name = op["tool"]
                params = op.get("params", {})
                
                # Apply smart defaults
                defaults = await self.preference_engine.get_smart_defaults(tool_name, context)
                merged_params = {**defaults, **params}  # params override defaults
                
                # Execute the operation
                result = await self._execute_tool(tool_name, merged_params, context)
                results.append({
                    "tool": tool_name,
                    "params": merged_params,
                    "success": True,
                    "result": result
                })
                
                # Record for learning
                await self.preference_engine.record_command(
                    tool_name, merged_params, context, success=True
                )
                
            except Exception as e:
                results.append({
                    "tool": op["tool"],
                    "params": op.get("params", {}),
                    "success": False,
                    "error": str(e)
                })
        
        return {
            "total_operations": len(operations),
            "successful_operations": len([r for r in results if r["success"]]),
            "failed_operations": len([r for r in results if not r["success"]]),
            "results": results
        }
    
    def _fill_template_params(self, params: Dict[str, str]) -> Dict[str, str]:
        """Fill in default values for template parameters."""
        filled = params.copy()
        
        # Add common default values
        if "date" not in filled:
            filled["date"] = datetime.now().strftime("%Y_%m_%d")
        
        if "datetime" not in filled:
            filled["datetime"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        return filled
    
    def _substitute_params(self, template_params: Dict[str, Any], 
                         filled_params: Dict[str, str]) -> Dict[str, Any]:
        """Substitute parameters in template."""
        result = {}
        
        for key, value in template_params.items():
            if isinstance(value, str):
                # Replace template variables
                for param_key, param_value in filled_params.items():
                    value = value.replace(f"{{{param_key}}}", str(param_value))
                result[key] = value
            elif isinstance(value, list):
                # Handle list parameters (like tags)
                result[key] = [
                    self._substitute_string(item, filled_params) if isinstance(item, str) else item
                    for item in value
                ]
            else:
                result[key] = value
        
        return result
    
    def _substitute_string(self, template: str, params: Dict[str, str]) -> str:
        """Substitute parameters in a string template."""
        result = template
        for param_key, param_value in params.items():
            result = result.replace(f"{{{param_key}}}", str(param_value))
        return result
    
    async def _execute_tool(self, tool_name: str, params: Dict[str, Any], 
                          context: Dict[str, Any]) -> Any:
        """Execute a memcord tool with given parameters."""
        # Check for mock executors first (for testing)
        if tool_name in self.tool_executors:
            executor = self.tool_executors[tool_name]
            if callable(executor):
                return await executor(params, context)
            return executor
        
        # Real implementation
        if tool_name == "memcord_name":
            slot_name = params["slot_name"]
            return await self.storage_manager.create_or_get_slot(slot_name)
        elif tool_name == "memcord_save":
            slot_name = context.get("current_slot") or params.get("slot_name")
            content = params["chat_text"]
            return await self.storage_manager.save_memory(slot_name, content)
        # Add other tool implementations as needed
        
        return {"status": "executed", "tool": tool_name, "params": params}