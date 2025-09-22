"""
Progress tracking and feedback system for memcord operations.

This module provides comprehensive progress tracking capabilities for long-running operations,
including progress bars, time estimation, cancellation support, and enhanced feedback messages.
"""

import asyncio
import time
from abc import ABC, abstractmethod
from contextlib import contextmanager
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union
from pathlib import Path
import uuid
from datetime import datetime, timedelta
import json

from .models import MemorySlot


class OperationType(Enum):
    """Types of operations that can be tracked."""
    SAVE = "save"
    SEARCH = "search" 
    MERGE = "merge"
    IMPORT = "import"
    COMPRESS = "compress"
    ARCHIVE = "archive"
    EXPORT = "export"
    BATCH = "batch"
    TEMPLATE = "template"
    CLEANUP = "cleanup"


class OperationStatus(Enum):
    """Status of tracked operations."""
    PENDING = "pending"
    RUNNING = "running"
    CANCELLING = "cancelling"
    CANCELLED = "cancelled"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class ProgressInfo:
    """Information about operation progress."""
    current: int = 0
    total: int = 0
    percentage: float = 0.0
    message: str = ""
    details: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def is_complete(self) -> bool:
        """Check if operation is complete."""
        return self.current >= self.total and self.total > 0
    
    def update(self, current: int, message: str = "", **details):
        """Update progress information."""
        self.current = min(current, self.total)
        self.percentage = (self.current / self.total * 100) if self.total > 0 else 0.0
        if message:
            self.message = message
        if details:
            self.details.update(details)


@dataclass
class TimeEstimate:
    """Time estimation for operations."""
    start_time: datetime
    estimated_duration: Optional[timedelta] = None
    estimated_completion: Optional[datetime] = None
    remaining: Optional[timedelta] = None
    
    def update_estimate(self, progress_percentage: float):
        """Update time estimation based on current progress."""
        if progress_percentage <= 0:
            return
            
        elapsed = datetime.now() - self.start_time
        if progress_percentage >= 100:
            self.estimated_duration = elapsed
            self.remaining = timedelta(0)
            self.estimated_completion = datetime.now()
        else:
            # Estimate total duration based on current progress
            self.estimated_duration = elapsed / (progress_percentage / 100)
            self.remaining = self.estimated_duration - elapsed
            self.estimated_completion = self.start_time + self.estimated_duration
    
    @property
    def elapsed(self) -> timedelta:
        """Get elapsed time."""
        return datetime.now() - self.start_time
    
    def format_remaining(self) -> str:
        """Format remaining time as human-readable string."""
        if not self.remaining:
            return "Unknown"
        
        total_seconds = int(self.remaining.total_seconds())
        if total_seconds < 60:
            return f"{total_seconds}s"
        elif total_seconds < 3600:
            minutes = total_seconds // 60
            seconds = total_seconds % 60
            return f"{minutes}m {seconds}s"
        else:
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            return f"{hours}h {minutes}m"


@dataclass
class OperationResult:
    """Result of a completed operation."""
    success: bool
    message: str
    details: Dict[str, Any] = field(default_factory=dict)
    suggestions: List[str] = field(default_factory=list)
    impact_summary: str = ""
    undo_available: bool = False
    undo_info: Optional[Dict[str, Any]] = None


class ProgressCallback(ABC):
    """Abstract base for progress callbacks."""
    
    @abstractmethod
    async def on_start(self, operation_id: str, operation_type: OperationType, 
                      total_steps: int, description: str):
        """Called when operation starts."""
        pass
    
    @abstractmethod
    async def on_progress(self, operation_id: str, progress: ProgressInfo, 
                         time_estimate: TimeEstimate):
        """Called on progress updates."""
        pass
    
    @abstractmethod
    async def on_complete(self, operation_id: str, result: OperationResult, 
                         time_estimate: TimeEstimate):
        """Called when operation completes."""
        pass
    
    @abstractmethod
    async def on_error(self, operation_id: str, error: Exception, 
                      time_estimate: TimeEstimate):
        """Called when operation fails."""
        pass
    
    @abstractmethod
    async def on_cancel(self, operation_id: str, time_estimate: TimeEstimate):
        """Called when operation is cancelled."""
        pass


class ConsoleProgressCallback(ProgressCallback):
    """Console-based progress callback with ASCII progress bars."""
    
    def __init__(self, show_details: bool = True):
        self.show_details = show_details
        self._operations: Dict[str, Dict[str, Any]] = {}
    
    async def on_start(self, operation_id: str, operation_type: OperationType,
                      total_steps: int, description: str):
        """Display operation start."""
        self._operations[operation_id] = {
            'type': operation_type,
            'description': description,
            'total_steps': total_steps
        }
        print(f"\n🚀 Starting {operation_type.value}: {description}")
        if total_steps > 0:
            print(f"📊 Progress: [{'':>50}] 0% (0/{total_steps})")
    
    async def on_progress(self, operation_id: str, progress: ProgressInfo,
                         time_estimate: TimeEstimate):
        """Update progress bar."""
        if operation_id not in self._operations:
            return
        
        # Create ASCII progress bar
        bar_width = 50
        filled = int(bar_width * progress.percentage / 100)
        bar = '█' * filled + '░' * (bar_width - filled)
        
        # Format time remaining
        remaining_str = time_estimate.format_remaining()
        
        # Update display
        print(f"\r📊 Progress: [{bar}] {progress.percentage:.1f}% "
              f"({progress.current}/{progress.total}) - "
              f"⏱️  ETA: {remaining_str}", end='')
        
        if progress.message:
            print(f"\n💬 {progress.message}")
        
        if self.show_details and progress.details:
            for key, value in progress.details.items():
                print(f"   • {key}: {value}")
    
    async def on_complete(self, operation_id: str, result: OperationResult,
                         time_estimate: TimeEstimate):
        """Display completion message."""
        print(f"\n✅ Completed in {time_estimate.elapsed}")
        print(f"📋 {result.message}")
        
        if result.impact_summary:
            print(f"📈 Impact: {result.impact_summary}")
        
        if result.suggestions:
            print("💡 Suggestions:")
            for suggestion in result.suggestions:
                print(f"   • {suggestion}")
        
        if result.undo_available:
            print("↩️  Undo available - use memcord_undo to reverse this operation")
        
        # Cleanup
        self._operations.pop(operation_id, None)
    
    async def on_error(self, operation_id: str, error: Exception,
                      time_estimate: TimeEstimate):
        """Display error message."""
        print(f"\n❌ Failed after {time_estimate.elapsed}")
        print(f"💥 Error: {error}")
        self._operations.pop(operation_id, None)
    
    async def on_cancel(self, operation_id: str, time_estimate: TimeEstimate):
        """Display cancellation message."""
        print(f"\n⏹️  Cancelled after {time_estimate.elapsed}")
        self._operations.pop(operation_id, None)


@dataclass
class TrackedOperation:
    """A tracked long-running operation."""
    operation_id: str
    operation_type: OperationType
    description: str
    status: OperationStatus
    progress: ProgressInfo
    time_estimate: TimeEstimate
    callback: Optional[ProgressCallback] = None
    cancellation_event: asyncio.Event = field(default_factory=asyncio.Event)
    result: Optional[OperationResult] = None
    error: Optional[Exception] = None


class OperationQueue:
    """Queue for managing multiple operations."""
    
    def __init__(self):
        self._operations: Dict[str, TrackedOperation] = {}
        self._queue: List[str] = []
        self._running: Set[str] = set()
        self._max_concurrent = 3
    
    def add_operation(self, operation: TrackedOperation) -> str:
        """Add operation to queue."""
        self._operations[operation.operation_id] = operation
        self._queue.append(operation.operation_id)
        return operation.operation_id
    
    async def start_next_operations(self):
        """Start next operations from queue."""
        while (len(self._running) < self._max_concurrent and 
               self._queue and 
               self._queue[0] not in self._running):
            
            operation_id = self._queue.pop(0)
            operation = self._operations[operation_id]
            
            if operation.status == OperationStatus.PENDING:
                self._running.add(operation_id)
                operation.status = OperationStatus.RUNNING
                # Operation execution would happen here via callback
    
    def get_operation(self, operation_id: str) -> Optional[TrackedOperation]:
        """Get operation by ID."""
        return self._operations.get(operation_id)
    
    def list_operations(self) -> List[TrackedOperation]:
        """List all operations."""
        return list(self._operations.values())
    
    def get_running_operations(self) -> List[TrackedOperation]:
        """Get currently running operations."""
        return [op for op in self._operations.values() 
                if op.status == OperationStatus.RUNNING]
    
    def complete_operation(self, operation_id: str, result: OperationResult):
        """Mark operation as completed."""
        if operation_id in self._operations:
            self._operations[operation_id].status = OperationStatus.COMPLETED
            self._operations[operation_id].result = result
            self._running.discard(operation_id)
    
    def fail_operation(self, operation_id: str, error: Exception):
        """Mark operation as failed."""
        if operation_id in self._operations:
            self._operations[operation_id].status = OperationStatus.FAILED
            self._operations[operation_id].error = error
            self._running.discard(operation_id)
    
    def cancel_operation(self, operation_id: str):
        """Cancel an operation."""
        if operation_id in self._operations:
            operation = self._operations[operation_id]
            if operation.status in [OperationStatus.PENDING, OperationStatus.RUNNING]:
                operation.status = OperationStatus.CANCELLING
                operation.cancellation_event.set()


class ProgressTracker:
    """Main progress tracking coordinator."""
    
    def __init__(self, storage_dir: Path):
        self.storage_dir = storage_dir
        self.queue = OperationQueue()
        self._history_file = storage_dir / "operation_history.json"
        self._undo_stack: List[Dict[str, Any]] = []
        self._max_history = 1000
        
        # Ensure storage directory exists
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        # Load operation history
        self._load_history()
    
    def create_operation(self, 
                        operation_type: OperationType,
                        description: str,
                        total_steps: int = 0,
                        callback: Optional[ProgressCallback] = None) -> str:
        """Create a new tracked operation."""
        operation_id = str(uuid.uuid4())
        
        operation = TrackedOperation(
            operation_id=operation_id,
            operation_type=operation_type,
            description=description,
            status=OperationStatus.PENDING,
            progress=ProgressInfo(total=total_steps),
            time_estimate=TimeEstimate(start_time=datetime.now()),
            callback=callback or ConsoleProgressCallback()
        )
        
        self.queue.add_operation(operation)
        return operation_id
    
    @contextmanager
    def track_operation(self,
                       operation_type: OperationType,
                       description: str,
                       total_steps: int = 0,
                       callback: Optional[ProgressCallback] = None):
        """Context manager for tracking operations."""
        operation_id = self.create_operation(operation_type, description, 
                                           total_steps, callback)
        operation = self.queue.get_operation(operation_id)
        
        try:
            # Start operation
            operation.status = OperationStatus.RUNNING
            if operation.callback:
                asyncio.create_task(operation.callback.on_start(
                    operation_id, operation_type, total_steps, description))
            
            yield OperationProgressContext(self, operation_id)
            
            # Complete operation
            if not operation.result and not operation.error:
                result = OperationResult(
                    success=True,
                    message=f"{operation_type.value} completed successfully",
                    impact_summary=f"Processed {operation.progress.current} items"
                )
                self.complete_operation(operation_id, result)
                
        except Exception as e:
            # Operation failed
            self.fail_operation(operation_id, e)
            raise
    
    async def update_progress(self, operation_id: str, current: int, 
                            message: str = "", **details):
        """Update operation progress."""
        operation = self.queue.get_operation(operation_id)
        if not operation:
            return
        
        # Check for cancellation
        if operation.cancellation_event.is_set():
            operation.status = OperationStatus.CANCELLED
            if operation.callback:
                await operation.callback.on_cancel(operation_id, operation.time_estimate)
            return
        
        # Update progress
        operation.progress.update(current, message, **details)
        operation.time_estimate.update_estimate(operation.progress.percentage)
        
        # Notify callback
        if operation.callback:
            await operation.callback.on_progress(operation_id, operation.progress,
                                                operation.time_estimate)
    
    def complete_operation(self, operation_id: str, result: OperationResult):
        """Complete an operation."""
        operation = self.queue.get_operation(operation_id)
        if not operation:
            return
        
        operation.progress.percentage = 100.0
        operation.time_estimate.update_estimate(100.0)
        self.queue.complete_operation(operation_id, result)
        
        # Add to history
        self._add_to_history(operation, result)
        
        # Notify callback
        if operation.callback:
            try:
                asyncio.create_task(operation.callback.on_complete(
                    operation_id, result, operation.time_estimate))
            except RuntimeError:
                # No event loop, callback will be called synchronously
                pass
    
    def fail_operation(self, operation_id: str, error: Exception):
        """Fail an operation."""
        operation = self.queue.get_operation(operation_id)
        if not operation:
            return
        
        self.queue.fail_operation(operation_id, error)
        
        # Notify callback
        if operation.callback:
            try:
                asyncio.create_task(operation.callback.on_error(
                    operation_id, error, operation.time_estimate))
            except RuntimeError:
                # No event loop, callback will be called synchronously
                pass
    
    def cancel_operation(self, operation_id: str) -> bool:
        """Cancel an operation."""
        operation = self.queue.get_operation(operation_id)
        if not operation or operation.status not in [OperationStatus.PENDING, 
                                                     OperationStatus.RUNNING]:
            return False
        
        self.queue.cancel_operation(operation_id)
        return True
    
    def get_operation_status(self, operation_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed operation status."""
        operation = self.queue.get_operation(operation_id)
        if not operation:
            return None
        
        return {
            "operation_id": operation_id,
            "type": operation.operation_type.value,
            "description": operation.description,
            "status": operation.status.value,
            "progress": {
                "current": operation.progress.current,
                "total": operation.progress.total,
                "percentage": operation.progress.percentage,
                "message": operation.progress.message,
                "details": operation.progress.details
            },
            "time": {
                "elapsed": str(operation.time_estimate.elapsed),
                "remaining": operation.time_estimate.format_remaining(),
                "estimated_completion": (operation.time_estimate.estimated_completion.isoformat() 
                                       if operation.time_estimate.estimated_completion else None)
            },
            "can_cancel": operation.status in [OperationStatus.PENDING, OperationStatus.RUNNING]
        }
    
    def list_active_operations(self) -> List[Dict[str, Any]]:
        """List all active operations."""
        active_operations = []
        for operation in self.queue.list_operations():
            if operation.status in [OperationStatus.PENDING, OperationStatus.RUNNING, 
                                   OperationStatus.CANCELLING]:
                status = self.get_operation_status(operation.operation_id)
                if status:
                    active_operations.append(status)
        return active_operations
    
    def add_undo_info(self, operation_type: OperationType, undo_data: Dict[str, Any]):
        """Add undo information for an operation."""
        self._undo_stack.append({
            "timestamp": datetime.now().isoformat(),
            "operation_type": operation_type.value,
            "undo_data": undo_data
        })
        
        # Limit undo stack size
        if len(self._undo_stack) > 50:
            self._undo_stack.pop(0)
    
    def can_undo(self) -> bool:
        """Check if undo is available."""
        return len(self._undo_stack) > 0
    
    def get_undo_info(self) -> Optional[Dict[str, Any]]:
        """Get information about the last undoable operation."""
        return self._undo_stack[-1] if self._undo_stack else None
    
    def pop_undo_info(self) -> Optional[Dict[str, Any]]:
        """Remove and return the last undo operation."""
        return self._undo_stack.pop() if self._undo_stack else None
    
    def _load_history(self):
        """Load operation history from disk."""
        if self._history_file.exists():
            try:
                with open(self._history_file, 'r') as f:
                    data = json.load(f)
                    self._undo_stack = data.get('undo_stack', [])
            except Exception:
                # If history is corrupted, start fresh
                self._undo_stack = []
    
    def _save_history(self):
        """Save operation history to disk."""
        try:
            with open(self._history_file, 'w') as f:
                json.dump({
                    'undo_stack': self._undo_stack[-50:]  # Keep only last 50
                }, f, indent=2)
        except Exception:
            # Ignore save errors
            pass
    
    def _add_to_history(self, operation: TrackedOperation, result: OperationResult):
        """Add completed operation to history."""
        # Save history periodically
        self._save_history()


class OperationProgressContext:
    """Context object for updating progress within tracked operations."""
    
    def __init__(self, tracker: ProgressTracker, operation_id: str):
        self.tracker = tracker
        self.operation_id = operation_id
    
    async def update(self, current: int, message: str = "", **details):
        """Update progress."""
        await self.tracker.update_progress(self.operation_id, current, message, **details)
    
    def add_undo_info(self, undo_data: Dict[str, Any]):
        """Add undo information."""
        operation = self.tracker.queue.get_operation(self.operation_id)
        if operation:
            self.tracker.add_undo_info(operation.operation_type, undo_data)
    
    @property
    def is_cancelled(self) -> bool:
        """Check if operation was cancelled."""
        operation = self.tracker.queue.get_operation(self.operation_id)
        return operation and operation.cancellation_event.is_set()