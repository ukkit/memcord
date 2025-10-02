"""
Enhanced feedback message system for memcord operations.

This module provides detailed success messages, actionable suggestions, impact summaries,
confirmation dialogs, and undo/redo capabilities for better user experience.
"""

from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

from .progress_tracker import OperationResult, OperationType


class MessageType(Enum):
    """Types of feedback messages."""

    SUCCESS = "success"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CONFIRMATION = "confirmation"
    SUGGESTION = "suggestion"


class ActionSeverity(Enum):
    """Severity levels for destructive actions."""

    LOW = "low"  # Non-destructive, easily reversible
    MEDIUM = "medium"  # Modifies data but recoverable
    HIGH = "high"  # Potentially destructive, confirmation needed
    CRITICAL = "critical"  # Irreversible or system-affecting


@dataclass
class ImpactSummary:
    """Summary of operation impact on the system."""

    slots_affected: int = 0
    slots_created: int = 0
    slots_modified: int = 0
    slots_deleted: int = 0
    entries_processed: int = 0
    storage_change: int = 0  # Bytes changed (positive = growth, negative = reduction)
    tags_affected: set[str] = field(default_factory=set)
    groups_affected: set[str] = field(default_factory=set)

    def format_summary(self) -> str:
        """Format impact summary as human-readable text."""
        parts = []

        if self.slots_created > 0:
            parts.append(f"Created {self.slots_created} slot{'s' if self.slots_created != 1 else ''}")

        if self.slots_modified > 0:
            parts.append(f"Modified {self.slots_modified} slot{'s' if self.slots_modified != 1 else ''}")

        if self.slots_deleted > 0:
            parts.append(f"Deleted {self.slots_deleted} slot{'s' if self.slots_deleted != 1 else ''}")

        if self.entries_processed > 0:
            parts.append(f"Processed {self.entries_processed} entries")

        if self.storage_change != 0:
            if self.storage_change > 0:
                parts.append(f"Increased storage by {self._format_bytes(self.storage_change)}")
            else:
                parts.append(f"Reduced storage by {self._format_bytes(abs(self.storage_change))}")

        if self.tags_affected:
            parts.append(f"Affected {len(self.tags_affected)} tag{'s' if len(self.tags_affected) != 1 else ''}")

        if self.groups_affected:
            parts.append(f"Affected {len(self.groups_affected)} group{'s' if len(self.groups_affected) != 1 else ''}")

        return "; ".join(parts) if parts else "No significant changes"

    def _format_bytes(self, bytes_count: int) -> str:
        """Format byte count as human-readable string."""
        if bytes_count < 1024:
            return f"{bytes_count} bytes"
        elif bytes_count < 1024 * 1024:
            return f"{bytes_count / 1024:.1f} KB"
        elif bytes_count < 1024 * 1024 * 1024:
            return f"{bytes_count / (1024 * 1024):.1f} MB"
        else:
            return f"{bytes_count / (1024 * 1024 * 1024):.1f} GB"


@dataclass
class NextStepSuggestion:
    """Actionable suggestion for next steps."""

    action: str
    description: str
    command: str | None = None
    priority: int = 1  # 1 = highest priority
    category: str = "general"

    def format_suggestion(self) -> str:
        """Format suggestion as actionable text."""
        text = f"{self.action}: {self.description}"
        if self.command:
            text += f" (Command: {self.command})"
        return text


@dataclass
class ConfirmationDialog:
    """Configuration for confirmation dialog."""

    title: str
    message: str
    severity: ActionSeverity
    consequences: list[str] = field(default_factory=list)
    alternatives: list[str] = field(default_factory=list)
    confirm_text: str = "Confirm"
    cancel_text: str = "Cancel"
    require_explicit_yes: bool = False

    def format_dialog(self) -> str:
        """Format confirmation dialog as text."""
        lines = [
            f"⚠️  {self.title}",
            "",
            self.message,
        ]

        if self.consequences:
            lines.append("")
            lines.append("📋 Consequences:")
            for consequence in self.consequences:
                lines.append(f"   • {consequence}")

        if self.alternatives:
            lines.append("")
            lines.append("💡 Alternatives:")
            for alternative in self.alternatives:
                lines.append(f"   • {alternative}")

        lines.extend(
            [
                "",
                f"Severity: {self.severity.value.upper()}",
                f"Type '{self.confirm_text}' to proceed or '{self.cancel_text}' to abort",
            ]
        )

        return "\n".join(lines)


class SuggestionEngine:
    """Engine for generating contextual suggestions."""

    def __init__(self):
        self._suggestion_rules: dict[str, list[Callable]] = {
            OperationType.SAVE.value: [
                self._suggest_save_follow_ups,
                self._suggest_organization,
                self._suggest_related_actions,
            ],
            OperationType.SEARCH.value: [self._suggest_search_refinements, self._suggest_result_actions],
            OperationType.MERGE.value: [self._suggest_post_merge_actions, self._suggest_cleanup],
            OperationType.IMPORT.value: [self._suggest_import_organization, self._suggest_validation],
            OperationType.COMPRESS.value: [self._suggest_compression_follow_up],
            OperationType.ARCHIVE.value: [self._suggest_archive_maintenance],
        }

    def generate_suggestions(
        self, operation_type: OperationType, result: OperationResult, context: dict[str, Any]
    ) -> list[NextStepSuggestion]:
        """Generate contextual suggestions based on operation and result."""
        suggestions = []

        # Get operation-specific suggestions
        rules = self._suggestion_rules.get(operation_type.value, [])
        for rule in rules:
            try:
                rule_suggestions = rule(result, context)
                if rule_suggestions:
                    suggestions.extend(rule_suggestions)
            except Exception:
                # Ignore errors in suggestion generation
                continue

        # Add general suggestions
        suggestions.extend(self._generate_general_suggestions(result, context))

        # Sort by priority and remove duplicates
        seen_actions = set()
        unique_suggestions = []
        for suggestion in sorted(suggestions, key=lambda s: s.priority):
            if suggestion.action not in seen_actions:
                unique_suggestions.append(suggestion)
                seen_actions.add(suggestion.action)

        return unique_suggestions[:5]  # Limit to top 5 suggestions

    def _suggest_save_follow_ups(self, result: OperationResult, context: dict[str, Any]) -> list[NextStepSuggestion]:
        """Generate suggestions after save operations."""
        suggestions = []

        slot_name = context.get("slot_name") or result.details.get("slot_name")
        if slot_name:
            suggestions.extend(
                [
                    NextStepSuggestion(
                        action="Add tags",
                        description=f"Organize '{slot_name}' with relevant tags",
                        command=f"memcord_tag add {slot_name} <tag1> <tag2>",
                        priority=2,
                        category="organization",
                    ),
                    NextStepSuggestion(
                        action="Search related",
                        description="Find related content in other slots",
                        command="memcord_search --query 'similar topics'",
                        priority=3,
                        category="discovery",
                    ),
                ]
            )

        return suggestions

    def _suggest_organization(self, result: OperationResult, context: dict[str, Any]) -> list[NextStepSuggestion]:
        """Suggest organization improvements."""
        suggestions = []

        if context.get("entries_count", 0) > 10:
            suggestions.append(
                NextStepSuggestion(
                    action="Consider compression",
                    description="Large slot might benefit from compression",
                    command="memcord_compress analyze",
                    priority=4,
                    category="optimization",
                )
            )

        return suggestions

    def _suggest_related_actions(self, result: OperationResult, context: dict[str, Any]) -> list[NextStepSuggestion]:
        """Suggest related actions based on context."""
        suggestions = []

        # If this is first save in a while, suggest maintenance
        if context.get("days_since_last_save", 0) > 7:
            suggestions.append(
                NextStepSuggestion(
                    action="Run maintenance",
                    description="Consider running system maintenance",
                    command="memcord_compress stats",
                    priority=5,
                    category="maintenance",
                )
            )

        return suggestions

    def _suggest_search_refinements(self, result: OperationResult, context: dict[str, Any]) -> list[NextStepSuggestion]:
        """Suggest search refinements."""
        suggestions = []

        result_count = context.get("result_count", 0)

        if result_count == 0:
            suggestions.extend(
                [
                    NextStepSuggestion(
                        action="Broaden search",
                        description="Try more general search terms",
                        priority=1,
                        category="search",
                    ),
                    NextStepSuggestion(
                        action="Check spelling",
                        description="Verify search terms are spelled correctly",
                        priority=2,
                        category="search",
                    ),
                ]
            )
        elif result_count > 50:
            suggestions.append(
                NextStepSuggestion(
                    action="Narrow search",
                    description="Add more specific terms to reduce results",
                    priority=1,
                    category="search",
                )
            )

        return suggestions

    def _suggest_result_actions(self, result: OperationResult, context: dict[str, Any]) -> list[NextStepSuggestion]:
        """Suggest actions based on search results."""
        suggestions = []

        if context.get("result_count", 0) > 0:
            suggestions.extend(
                [
                    NextStepSuggestion(
                        action="Read results",
                        description="Review the content of interesting results",
                        command="memcord_read <slot_name>",
                        priority=1,
                        category="discovery",
                    ),
                    NextStepSuggestion(
                        action="Save search",
                        description="Save search results for future reference",
                        priority=3,
                        category="organization",
                    ),
                ]
            )

        return suggestions

    def _suggest_post_merge_actions(self, result: OperationResult, context: dict[str, Any]) -> list[NextStepSuggestion]:
        """Suggest actions after merge operations."""
        suggestions = []

        merged_slot = context.get("merged_slot_name") or result.details.get("merged_slot_name")
        if merged_slot:
            suggestions.extend(
                [
                    NextStepSuggestion(
                        action="Review merged content",
                        description="Verify the merged content meets your needs",
                        command=f"memcord_read {merged_slot}",
                        priority=1,
                        category="validation",
                    ),
                    NextStepSuggestion(
                        action="Update tags",
                        description="Update tags to reflect merged content",
                        command=f"memcord_tag add {merged_slot} <new-tags>",
                        priority=2,
                        category="organization",
                    ),
                ]
            )

        return suggestions

    def _suggest_cleanup(self, result: OperationResult, context: dict[str, Any]) -> list[NextStepSuggestion]:
        """Suggest cleanup actions."""
        suggestions = []

        if context.get("source_slots_deleted", False):
            suggestions.append(
                NextStepSuggestion(
                    action="Clean empty groups",
                    description="Remove any empty groups left after merge",
                    command="memcord_group list",
                    priority=4,
                    category="maintenance",
                )
            )

        return suggestions

    def _suggest_import_organization(
        self, result: OperationResult, context: dict[str, Any]
    ) -> list[NextStepSuggestion]:
        """Suggest organization after import."""
        suggestions = []

        imported_slot = context.get("imported_slot_name")
        if imported_slot:
            suggestions.extend(
                [
                    NextStepSuggestion(
                        action="Add descriptive tags",
                        description="Tag imported content for easy discovery",
                        command=f"memcord_tag add {imported_slot} imported <content-type>",
                        priority=1,
                        category="organization",
                    ),
                    NextStepSuggestion(
                        action="Set group",
                        description="Organize imported content into appropriate group",
                        command=f"memcord_group set {imported_slot} imports/<category>",
                        priority=2,
                        category="organization",
                    ),
                ]
            )

        return suggestions

    def _suggest_validation(self, result: OperationResult, context: dict[str, Any]) -> list[NextStepSuggestion]:
        """Suggest validation actions."""
        suggestions = []

        if context.get("import_warnings", 0) > 0:
            suggestions.append(
                NextStepSuggestion(
                    action="Review warnings",
                    description="Check import warnings to ensure data integrity",
                    priority=1,
                    category="validation",
                )
            )

        return suggestions

    def _suggest_compression_follow_up(
        self, result: OperationResult, context: dict[str, Any]
    ) -> list[NextStepSuggestion]:
        """Suggest follow-up actions after compression."""
        suggestions = []

        if context.get("compression_savings", 0) > 0:
            suggestions.append(
                NextStepSuggestion(
                    action="Review compressed content",
                    description="Verify compressed content maintains important information",
                    priority=2,
                    category="validation",
                )
            )

        return suggestions

    def _suggest_archive_maintenance(
        self, result: OperationResult, context: dict[str, Any]
    ) -> list[NextStepSuggestion]:
        """Suggest maintenance after archive operations."""
        suggestions = []

        archived_count = (
            context.get("archived_count", 0)
            or result.details.get("slots_deleted", 0)
            or result.details.get("archived_count", 0)
            or result.details.get("slots_processed", 0)
        )

        if archived_count > 0:
            suggestions.append(
                NextStepSuggestion(
                    action="Update documentation",
                    description="Document archived slots for future reference",
                    priority=3,
                    category="documentation",
                )
            )

        return suggestions

    def _generate_general_suggestions(
        self, result: OperationResult, context: dict[str, Any]
    ) -> list[NextStepSuggestion]:
        """Generate general suggestions applicable to any operation."""
        suggestions = []

        # Suggest backup if significant changes
        if context.get("storage_change_significant", False):
            suggestions.append(
                NextStepSuggestion(
                    action="Create backup",
                    description="Consider exporting important slots as backup",
                    command="memcord_export <slot_name> md",
                    priority=5,
                    category="safety",
                )
            )

        return suggestions


class ConfirmationManager:
    """Manager for handling confirmation dialogs."""

    def __init__(self):
        self._confirmation_rules: dict[str, Callable] = {
            "delete_slots": self._create_delete_confirmation,
            "merge_slots": self._create_merge_confirmation,
            "archive_slots": self._create_archive_confirmation,
            "compress_slots": self._create_compress_confirmation,
            "batch_operations": self._create_batch_confirmation,
        }

    def should_confirm(self, operation_type: str, context: dict[str, Any]) -> bool:
        """Determine if operation requires confirmation."""
        severity = self._assess_severity(operation_type, context)
        return severity in [ActionSeverity.MEDIUM, ActionSeverity.HIGH, ActionSeverity.CRITICAL]

    def create_confirmation(self, operation_type: str, context: dict[str, Any]) -> ConfirmationDialog | None:
        """Create confirmation dialog for operation."""
        rule = self._confirmation_rules.get(operation_type)
        if rule:
            return rule(context)
        return None

    def _assess_severity(self, operation_type: str, context: dict[str, Any]) -> ActionSeverity:
        """Assess operation severity."""
        if operation_type in ["delete_slots", "archive_slots"]:
            slot_count = context.get("slot_count", 0)
            if slot_count > 10:
                return ActionSeverity.CRITICAL
            elif slot_count > 1:
                return ActionSeverity.HIGH
            else:
                return ActionSeverity.MEDIUM

        if operation_type == "merge_slots":
            source_count = context.get("source_slot_count", 0)
            if source_count > 5:
                return ActionSeverity.HIGH
            else:
                return ActionSeverity.MEDIUM

        if operation_type == "batch_operations":
            operation_count = context.get("operation_count", 0)
            if operation_count > 20:
                return ActionSeverity.HIGH
            elif operation_count > 10:
                return ActionSeverity.MEDIUM
            else:
                return ActionSeverity.LOW

        return ActionSeverity.LOW

    def _create_delete_confirmation(self, context: dict[str, Any]) -> ConfirmationDialog:
        """Create confirmation for delete operations."""
        slot_count = context.get("slot_count", 0)

        return ConfirmationDialog(
            title="Confirm Deletion",
            message=f"You are about to permanently delete {slot_count} memory slot{'s' if slot_count != 1 else ''}.",
            severity=ActionSeverity.HIGH if slot_count > 1 else ActionSeverity.MEDIUM,
            consequences=[
                "All content in these slots will be permanently lost",
                "Associated tags and group memberships will be removed",
                "Search index entries will be deleted",
                "This action cannot be undone",
            ],
            alternatives=[
                "Archive slots instead to preserve content while hiding them",
                "Export slots as backup before deletion",
                "Move slots to a 'trash' group for later review",
            ],
            require_explicit_yes=True,
        )

    def _create_merge_confirmation(self, context: dict[str, Any]) -> ConfirmationDialog:
        """Create confirmation for merge operations."""
        source_count = context.get("source_slot_count", 0)
        target_slot = context.get("target_slot_name", "unknown")

        return ConfirmationDialog(
            title="Confirm Merge",
            message=f"Merge {source_count} slots into '{target_slot}'?",
            severity=ActionSeverity.MEDIUM,
            consequences=[
                f"Content from {source_count} slots will be combined",
                "Duplicate content will be removed based on similarity",
                "Source slots will be deleted after successful merge",
                "Original slot structure will be lost",
            ],
            alternatives=[
                "Preview the merge first to see the result",
                "Export source slots as backup before merging",
                "Create a new slot instead of merging into existing one",
            ],
        )

    def _create_archive_confirmation(self, context: dict[str, Any]) -> ConfirmationDialog:
        """Create confirmation for archive operations."""
        slot_count = context.get("slot_count", 0)

        return ConfirmationDialog(
            title="Confirm Archive",
            message=f"Archive {slot_count} memory slot{'s' if slot_count != 1 else ''}?",
            severity=ActionSeverity.MEDIUM,
            consequences=[
                "Slots will be moved to archive storage",
                "Archived slots won't appear in normal listings",
                "Content will be preserved but not easily accessible",
                "Search performance may improve",
            ],
            alternatives=[
                "Tag slots as 'inactive' instead of archiving",
                "Move slots to a specific group for organization",
                "Export slots for external backup",
            ],
        )

    def _create_compress_confirmation(self, context: dict[str, Any]) -> ConfirmationDialog:
        """Create confirmation for compression operations."""
        slot_count = context.get("slot_count", 0)
        compression_ratio = context.get("compression_ratio", 0.5)

        return ConfirmationDialog(
            title="Confirm Compression",
            message=f"Compress {slot_count} slots with {compression_ratio:.0%} target ratio?",
            severity=ActionSeverity.LOW,
            consequences=[
                f"Content will be summarized to ~{compression_ratio:.0%} of original size",
                "Some detail may be lost in the compression process",
                "Original content will be backed up",
                "Operation can be reversed if needed",
            ],
            alternatives=[
                "Start with a higher compression ratio (less aggressive)",
                "Test compression on a single slot first",
                "Create manual summaries instead",
            ],
        )

    def _create_batch_confirmation(self, context: dict[str, Any]) -> ConfirmationDialog:
        """Create confirmation for batch operations."""
        operation_count = context.get("operation_count", 0)
        estimated_time = context.get("estimated_time", "unknown")

        return ConfirmationDialog(
            title="Confirm Batch Operation",
            message=f"Execute {operation_count} operations in batch?",
            severity=ActionSeverity.MEDIUM if operation_count > 10 else ActionSeverity.LOW,
            consequences=[
                f"Will execute {operation_count} operations sequentially",
                f"Estimated completion time: {estimated_time}",
                "Some operations may modify or delete content",
                "Batch can be cancelled while running",
            ],
            alternatives=[
                "Execute operations individually for more control",
                "Review the operation list before proceeding",
                "Start with a smaller batch to test",
            ],
        )


class FeedbackMessageGenerator:
    """Main generator for enhanced feedback messages."""

    def __init__(self, storage_dir: Path):
        self.storage_dir = storage_dir
        self.suggestion_engine = SuggestionEngine()
        self.confirmation_manager = ConfirmationManager()

    def generate_success_message(
        self, operation_type: OperationType, result_data: dict[str, Any], context: dict[str, Any]
    ) -> OperationResult:
        """Generate comprehensive success message."""

        # Calculate impact summary
        impact = self._calculate_impact(operation_type, result_data, context)

        # Generate suggestions
        suggestions = self.suggestion_engine.generate_suggestions(
            operation_type,
            OperationResult(success=True, message="", impact_summary=impact.format_summary(), details=result_data),
            context,
        )

        # Check if undo is available
        undo_available = self._has_undo_capability(operation_type, result_data)
        undo_info = result_data.get("undo_info") if undo_available else None

        # Create detailed message
        message = self._create_detailed_message(operation_type, result_data, impact)

        return OperationResult(
            success=True,
            message=message,
            details=result_data,
            suggestions=[s.format_suggestion() for s in suggestions],
            impact_summary=impact.format_summary(),
            undo_available=undo_available,
            undo_info=undo_info,
        )

    def create_confirmation_dialog(self, operation_type: str, context: dict[str, Any]) -> str | None:
        """Create confirmation dialog text."""
        if not self.confirmation_manager.should_confirm(operation_type, context):
            return None

        dialog = self.confirmation_manager.create_confirmation(operation_type, context)
        return dialog.format_dialog() if dialog else None

    def _calculate_impact(
        self, operation_type: OperationType, result_data: dict[str, Any], context: dict[str, Any]
    ) -> ImpactSummary:
        """Calculate the impact of an operation."""
        impact = ImpactSummary()

        # Update based on operation type and results
        if operation_type == OperationType.SAVE:
            if context.get("new_slot", False):
                impact.slots_created = 1
            else:
                impact.slots_modified = 1
            impact.entries_processed = 1
            impact.storage_change = len(result_data.get("content", ""))

        elif operation_type == OperationType.MERGE:
            impact.slots_created = 1  # New merged slot
            impact.slots_deleted = result_data.get("source_slots_count", 0)
            impact.entries_processed = result_data.get("total_entries", 0)
            impact.storage_change = result_data.get("storage_change", 0)

        elif operation_type == OperationType.IMPORT:
            impact.slots_created = result_data.get("slots_created", 0)
            impact.entries_processed = result_data.get("entries_imported", 0)
            impact.storage_change = result_data.get("content_size", 0)

        elif operation_type == OperationType.COMPRESS:
            impact.slots_modified = result_data.get("slots_compressed", 0)
            impact.storage_change = -result_data.get("space_saved", 0)  # Negative = space saved

        elif operation_type == OperationType.ARCHIVE:
            impact.slots_modified = result_data.get("slots_archived", 0)
            if not impact.slots_modified:
                # Check alternative field names
                impact.slots_modified = result_data.get("slots_deleted", 0)

        # Add affected tags and groups
        impact.tags_affected = set(result_data.get("tags_affected", []))
        impact.groups_affected = set(result_data.get("groups_affected", []))

        return impact

    def _create_detailed_message(
        self, operation_type: OperationType, result_data: dict[str, Any], impact: ImpactSummary
    ) -> str:
        """Create detailed success message."""
        base_messages = {
            OperationType.SAVE: "Content saved successfully",
            OperationType.SEARCH: "Search completed",
            OperationType.MERGE: "Memory slots merged successfully",
            OperationType.IMPORT: "Content imported successfully",
            OperationType.COMPRESS: "Compression completed",
            OperationType.ARCHIVE: "Slots archived successfully",
            OperationType.EXPORT: "Export completed successfully",
            OperationType.BATCH: "Batch operations completed",
            OperationType.TEMPLATE: "Template executed successfully",
            OperationType.CLEANUP: "Cleanup completed",
        }

        message = base_messages.get(operation_type, "Operation completed successfully")

        # Add specific details based on operation type
        details = []

        if operation_type == OperationType.SAVE:
            slot_name = result_data.get("slot_name")
            if slot_name:
                details.append(f"Slot: {slot_name}")

            entry_count = result_data.get("entry_count", 0)
            if entry_count > 1:
                details.append(f"{entry_count} entries total")

        elif operation_type == OperationType.SEARCH:
            result_count = result_data.get("result_count", 0)
            details.append(f"Found {result_count} result{'s' if result_count != 1 else ''}")

            if result_count > 0:
                top_relevance = result_data.get("top_relevance", 0)
                details.append(f"Top relevance: {top_relevance:.1%}")

        elif operation_type == OperationType.MERGE:
            merged_slot = result_data.get("merged_slot_name")
            source_count = result_data.get("source_slots_count", 0)
            if merged_slot:
                details.append(f"Result: {merged_slot}")
            details.append(f"Merged {source_count} source slots")

        # Add details to message
        if details:
            message += " - " + "; ".join(details)

        return message

    def _has_undo_capability(self, operation_type: OperationType, result_data: dict[str, Any]) -> bool:
        """Check if operation supports undo."""
        # Operations that support undo
        undoable_operations = {OperationType.SAVE, OperationType.MERGE, OperationType.COMPRESS, OperationType.ARCHIVE}

        return operation_type in undoable_operations and "undo_info" in result_data
