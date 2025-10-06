"""
Integration layer for progress tracking with memcord operations.

This module integrates the progress tracking and feedback systems with existing
memcord tools to provide enhanced user experience with progress indicators.
"""

import asyncio
import inspect
from collections.abc import Callable
from functools import wraps
from pathlib import Path
from typing import Any

from .feedback_messages import ConfirmationManager, FeedbackMessageGenerator
from .progress_tracker import (
    ConsoleProgressCallback,
    OperationType,
    ProgressCallback,
    ProgressTracker,
)


class MemcordProgressIntegration:
    """Main integration class for progress tracking in memcord."""

    def __init__(self, storage_dir: Path):
        self.storage_dir = storage_dir
        self.progress_tracker = ProgressTracker(storage_dir)
        self.feedback_generator = FeedbackMessageGenerator(storage_dir)
        self.confirmation_manager = ConfirmationManager()

        # Default callback for console output
        self.default_callback = ConsoleProgressCallback(show_details=True)

    def track_operation(self, operation_type: OperationType, description: str = ""):
        """Decorator to add progress tracking to operations."""

        def decorator(func: Callable) -> Callable:
            @wraps(func)
            async def wrapper(*args, **kwargs):
                # Extract context from function arguments
                context = self._extract_context(func, args, kwargs)

                # Check if confirmation is needed
                confirmation_type = self._get_confirmation_type(operation_type, context)
                if confirmation_type:
                    confirmation_text = self.feedback_generator.create_confirmation_dialog(confirmation_type, context)
                    if confirmation_text:
                        print(confirmation_text)
                        # In real implementation, would wait for user confirmation
                        # For now, we'll assume confirmation

                # Estimate total steps
                total_steps = self._estimate_steps(operation_type, context)

                # Start tracking
                operation_desc = description or f"{operation_type.value} operation"
                with self.progress_tracker.track_operation(
                    operation_type, operation_desc, total_steps, self.default_callback
                ) as progress_context:
                    try:
                        # Execute the original function
                        if inspect.iscoroutinefunction(func):
                            result = await func(*args, progress_context=progress_context, **kwargs)
                        else:
                            result = func(*args, progress_context=progress_context, **kwargs)

                        # Generate enhanced feedback
                        if isinstance(result, dict):
                            enhanced_result = self.feedback_generator.generate_success_message(
                                operation_type, result, context
                            )

                            # Complete operation with enhanced result
                            self.progress_tracker.complete_operation(progress_context.operation_id, enhanced_result)

                        return result

                    except Exception:
                        # Let the progress tracker handle the error
                        raise

            return wrapper

        return decorator

    def _extract_context(self, func: Callable, args: tuple, kwargs: dict) -> dict[str, Any]:
        """Extract context information from function call."""
        context = {}

        # Get function signature
        sig = inspect.signature(func)
        bound_args = sig.bind(*args, **kwargs)
        bound_args.apply_defaults()

        # Extract common context variables
        for param_name, value in bound_args.arguments.items():
            if param_name in [
                "slot_name",
                "slot_names",
                "query",
                "file_path",
                "source_slots",
                "target_slot",
                "compression_ratio",
                "content",
            ]:
                context[param_name] = value

        # Add function-specific context
        context["function_name"] = func.__name__
        context["timestamp"] = asyncio.get_event_loop().time()

        return context

    def _get_confirmation_type(self, operation_type: OperationType, context: dict[str, Any]) -> str | None:
        """Determine if operation needs confirmation."""
        if operation_type == OperationType.MERGE and context.get("source_slots"):
            return "merge_slots"

        if operation_type == OperationType.ARCHIVE and context.get("slot_names"):
            slot_count = len(context["slot_names"]) if isinstance(context["slot_names"], list) else 1
            if slot_count > 5:
                return "archive_slots"

        if operation_type == OperationType.COMPRESS and context.get("compression_ratio", 1.0) < 0.3:
            return "compress_slots"

        if operation_type == OperationType.BATCH:
            return "batch_operations"

        return None

    def _estimate_steps(self, operation_type: OperationType, context: dict[str, Any]) -> int:
        """Estimate total steps for progress tracking."""
        if operation_type == OperationType.SAVE:
            # Estimate based on content length
            content = context.get("content", "")
            return max(1, len(content) // 1000)  # 1 step per 1000 characters

        elif operation_type == OperationType.SEARCH:
            return 3  # Parse query, search index, format results

        elif operation_type == OperationType.MERGE:
            source_slots = context.get("source_slots", [])
            if isinstance(source_slots, list):
                return len(source_slots) * 2 + 3  # Read each slot, analyze, merge, save
            return 5  # Default estimate

        elif operation_type == OperationType.IMPORT:
            return 4  # Read file, parse content, create slot, save

        elif operation_type == OperationType.COMPRESS:
            return 5  # Analyze, backup, compress, validate, save

        elif operation_type == OperationType.ARCHIVE:
            slot_names = context.get("slot_names", [])
            if isinstance(slot_names, list):
                return len(slot_names)
            return 1

        elif operation_type == OperationType.EXPORT:
            return 3  # Read, format, write

        elif operation_type == OperationType.BATCH:
            operations = context.get("operations", [])
            if isinstance(operations, list):
                return len(operations)
            return context.get("operation_count", 5)

        return 1  # Default single step


# Decorator functions for common operations


def track_save_operation(integration: MemcordProgressIntegration):
    """Decorator for save operations."""
    return integration.track_operation(OperationType.SAVE, "Saving content to memory slot")


def track_search_operation(integration: MemcordProgressIntegration):
    """Decorator for search operations."""
    return integration.track_operation(OperationType.SEARCH, "Searching memory content")


def track_merge_operation(integration: MemcordProgressIntegration):
    """Decorator for merge operations."""
    return integration.track_operation(OperationType.MERGE, "Merging memory slots")


def track_import_operation(integration: MemcordProgressIntegration):
    """Decorator for import operations."""
    return integration.track_operation(OperationType.IMPORT, "Importing external content")


def track_compress_operation(integration: MemcordProgressIntegration):
    """Decorator for compression operations."""
    return integration.track_operation(OperationType.COMPRESS, "Compressing memory content")


def track_archive_operation(integration: MemcordProgressIntegration):
    """Decorator for archive operations."""
    return integration.track_operation(OperationType.ARCHIVE, "Archiving memory slots")


def track_export_operation(integration: MemcordProgressIntegration):
    """Decorator for export operations."""
    return integration.track_operation(OperationType.EXPORT, "Exporting memory content")


def track_batch_operation(integration: MemcordProgressIntegration):
    """Decorator for batch operations."""
    return integration.track_operation(OperationType.BATCH, "Executing batch operations")


class ProgressAwareMixin:
    """Mixin class to add progress tracking to existing classes."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if hasattr(self, "storage_dir"):
            self.progress_integration = MemcordProgressIntegration(self.storage_dir)
        else:
            # Fallback to current directory if storage_dir not available
            self.progress_integration = MemcordProgressIntegration(Path.cwd())

    def _track_progress_if_available(self, progress_context, step: int, message: str = "", **details):
        """Helper method to update progress if context is available."""
        if hasattr(progress_context, "update"):
            asyncio.create_task(progress_context.update(step, message, **details))
        elif progress_context:  # Fallback for simple progress tracking
            print(f"Progress: Step {step} - {message}")


# Utility functions for manual progress tracking


async def track_long_operation(
    storage_dir: Path,
    operation_type: OperationType,
    description: str,
    operation_func: Callable,
    callback: ProgressCallback | None = None,
) -> Any:
    """Utility function to manually track a long operation."""
    tracker = ProgressTracker(storage_dir)

    with tracker.track_operation(operation_type, description, 0, callback) as progress_context:
        return await operation_func(progress_context)


def create_progress_callback(show_console: bool = True, show_details: bool = True) -> ProgressCallback:
    """Create a progress callback with specified options."""
    if show_console:
        return ConsoleProgressCallback(show_details=show_details)
    else:
        # Could return other callback types (e.g., silent, file-based, etc.)
        return ConsoleProgressCallback(show_details=False)


# Context managers for manual progress tracking


class ProgressContext:
    """Context manager for manual progress tracking."""

    def __init__(
        self,
        storage_dir: Path,
        operation_type: OperationType,
        description: str,
        total_steps: int = 0,
        callback: ProgressCallback | None = None,
    ):
        self.tracker = ProgressTracker(storage_dir)
        self.operation_type = operation_type
        self.description = description
        self.total_steps = total_steps
        self.callback = callback or ConsoleProgressCallback()
        self.progress_context = None

    def __enter__(self):
        self.progress_context = self.tracker.track_operation(
            self.operation_type, self.description, self.total_steps, self.callback
        ).__enter__()
        return self.progress_context

    def __exit__(self, exc_type, exc_val, exc_tb):
        if hasattr(self.progress_context, "__exit__"):
            self.progress_context.__exit__(exc_type, exc_val, exc_tb)
        # OperationProgressContext doesn't have __exit__, context manager handles cleanup


# Global integration instance for backwards compatibility
_global_integration: MemcordProgressIntegration | None = None


def initialize_progress_integration(storage_dir: Path):
    """Initialize global progress integration instance."""
    global _global_integration
    _global_integration = MemcordProgressIntegration(storage_dir)


def get_progress_integration() -> MemcordProgressIntegration | None:
    """Get global progress integration instance."""
    return _global_integration
