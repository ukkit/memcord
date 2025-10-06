"""Batch operations system for executing multiple memcord commands efficiently.

This module provides batch processing capabilities, allowing users to execute
multiple commands in sequence with smart error handling, rollback capabilities,
and progress tracking.
"""

import asyncio
import json
from collections.abc import Callable
from dataclasses import asdict, dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

import aiofiles

from .smart_defaults import PreferenceLearningEngine


class BatchMode(Enum):
    """Execution modes for batch operations."""

    SEQUENTIAL = "sequential"  # Execute one at a time, stop on error
    PARALLEL = "parallel"  # Execute all simultaneously
    FAIL_FAST = "fail_fast"  # Stop on first error
    CONTINUE = "continue"  # Continue despite errors
    ROLLBACK = "rollback"  # Rollback on any failure


class OperationStatus(Enum):
    """Status of individual operations."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    ROLLED_BACK = "rolled_back"


@dataclass
class BatchOperation:
    """Represents a single operation in a batch."""

    id: str
    tool_name: str
    parameters: dict[str, Any]
    description: str
    depends_on: list[str] = None  # Operation IDs this depends on
    retry_count: int = 0
    max_retries: int = 2
    timeout_seconds: float = 30.0
    rollback_operation: dict[str, Any] | None = None

    def __post_init__(self):
        if self.depends_on is None:
            self.depends_on = []


@dataclass
class BatchResult:
    """Result of a batch operation execution."""

    operation_id: str
    status: OperationStatus
    result: Any = None
    error: str = None
    execution_time: float = 0.0
    timestamp: datetime = None
    retry_count: int = 0

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


@dataclass
class BatchExecution:
    """Represents a complete batch execution."""

    batch_id: str
    operations: list[BatchOperation]
    mode: BatchMode
    results: list[BatchResult]
    started_at: datetime
    completed_at: datetime | None = None
    total_operations: int = 0
    successful_operations: int = 0
    failed_operations: int = 0
    execution_time: float = 0.0

    def __post_init__(self):
        self.total_operations = len(self.operations)


class BatchOperationManager:
    """Manages batch execution of memcord operations."""

    def __init__(self, storage_dir: Path, preference_engine: PreferenceLearningEngine):
        self.storage_dir = storage_dir
        self.preference_engine = preference_engine
        self.batch_history_file = storage_dir / "batch_history.json"
        self.active_batches: dict[str, BatchExecution] = {}
        self.batch_history: list[BatchExecution] = []
        self.max_history = 100

        # Tool executors - would be injected in real implementation
        self.tool_executors: dict[str, Callable] = {}

    async def initialize(self):
        """Initialize the batch operation manager."""
        await self._load_batch_history()

    def register_tool_executor(self, tool_name: str, executor: Callable):
        """Register a tool executor function."""
        self.tool_executors[tool_name] = executor

    async def create_batch(
        self, operations: list[dict[str, Any]], mode: BatchMode = BatchMode.SEQUENTIAL, batch_id: str | None = None
    ) -> str:
        """Create a new batch operation."""
        if batch_id is None:
            batch_id = f"batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        # Convert operation dictionaries to BatchOperation objects
        batch_operations = []
        for i, op_dict in enumerate(operations):
            operation = BatchOperation(
                id=op_dict.get("id", f"{batch_id}_op_{i}"),
                tool_name=op_dict["tool"],
                parameters=op_dict.get("params", {}),
                description=op_dict.get("description", f"Execute {op_dict['tool']}"),
                depends_on=op_dict.get("depends_on", []),
                max_retries=op_dict.get("max_retries", 2),
                timeout_seconds=op_dict.get("timeout", 30.0),
                rollback_operation=op_dict.get("rollback"),
            )
            batch_operations.append(operation)

        batch_execution = BatchExecution(
            batch_id=batch_id, operations=batch_operations, mode=mode, results=[], started_at=datetime.now()
        )

        self.active_batches[batch_id] = batch_execution
        return batch_id

    async def execute_batch(self, batch_id: str, context: dict[str, Any]) -> BatchExecution:
        """Execute a batch operation."""
        if batch_id not in self.active_batches:
            raise ValueError(f"Batch {batch_id} not found")

        batch = self.active_batches[batch_id]
        start_time = datetime.now()

        try:
            if batch.mode == BatchMode.PARALLEL:
                await self._execute_parallel(batch, context)
            else:
                await self._execute_sequential(batch, context)

        except Exception as e:
            # Handle batch-level failures
            print(f"Batch execution failed: {e}")

        finally:
            # Finalize batch
            batch.completed_at = datetime.now()
            batch.execution_time = (batch.completed_at - start_time).total_seconds()
            batch.successful_operations = len([r for r in batch.results if r.status == OperationStatus.COMPLETED])
            batch.failed_operations = len([r for r in batch.results if r.status == OperationStatus.FAILED])

            # Move to history
            self.batch_history.append(batch)
            if len(self.batch_history) > self.max_history:
                self.batch_history = self.batch_history[-self.max_history :]

            # Remove from active
            del self.active_batches[batch_id]

            await self._save_batch_history()

        return batch

    async def _execute_sequential(self, batch: BatchExecution, context: dict[str, Any]):
        """Execute operations sequentially."""
        dependency_graph = self._build_dependency_graph(batch.operations)
        execution_order = self._topological_sort(dependency_graph)

        for operation in execution_order:
            # Check if dependencies are satisfied
            if not self._dependencies_satisfied(operation, batch.results):
                result = BatchResult(
                    operation_id=operation.id, status=OperationStatus.SKIPPED, error="Dependencies not satisfied"
                )
                batch.results.append(result)
                continue

            # Execute the operation
            result = await self._execute_single_operation(operation, context)
            batch.results.append(result)

            # Check execution mode behavior
            if result.status == OperationStatus.FAILED:
                if batch.mode == BatchMode.FAIL_FAST:
                    break
                elif batch.mode == BatchMode.ROLLBACK:
                    await self._rollback_batch(batch, context)
                    break

    async def _execute_parallel(self, batch: BatchExecution, context: dict[str, Any]):
        """Execute operations in parallel where possible."""
        # Group operations by dependency level
        dependency_levels = self._group_by_dependency_level(batch.operations)

        for level_operations in dependency_levels:
            # Execute all operations at this level in parallel
            tasks = []
            for operation in level_operations:
                if self._dependencies_satisfied(operation, batch.results):
                    task = self._execute_single_operation(operation, context)
                    tasks.append(task)
                else:
                    # Skip if dependencies not satisfied
                    result = BatchResult(
                        operation_id=operation.id, status=OperationStatus.SKIPPED, error="Dependencies not satisfied"
                    )
                    batch.results.append(result)

            # Wait for all tasks at this level to complete
            if tasks:
                level_results = await asyncio.gather(*tasks, return_exceptions=True)

                for result in level_results:
                    if isinstance(result, Exception):
                        # Handle exceptions
                        error_result = BatchResult(
                            operation_id="unknown", status=OperationStatus.FAILED, error=str(result)
                        )
                        batch.results.append(error_result)
                    else:
                        batch.results.append(result)

    async def _execute_single_operation(self, operation: BatchOperation, context: dict[str, Any]) -> BatchResult:
        """Execute a single operation with retry logic."""
        start_time = datetime.now()

        for attempt in range(operation.max_retries + 1):
            try:
                result = BatchResult(operation_id=operation.id, status=OperationStatus.RUNNING, timestamp=start_time)

                # Apply smart defaults to parameters
                smart_defaults = await self.preference_engine.get_smart_defaults(operation.tool_name, context)
                merged_params = {**smart_defaults, **operation.parameters}

                # Execute with timeout
                executor_result = await asyncio.wait_for(
                    self._call_tool_executor(operation.tool_name, merged_params, context),
                    timeout=operation.timeout_seconds,
                )

                result.status = OperationStatus.COMPLETED
                result.result = executor_result
                result.execution_time = (datetime.now() - start_time).total_seconds()
                result.retry_count = attempt

                # Record successful execution for learning
                await self.preference_engine.record_command(operation.tool_name, merged_params, context, success=True)

                return result

            except asyncio.TimeoutError:
                error_msg = f"Operation timed out after {operation.timeout_seconds} seconds"

            except Exception as e:
                error_msg = str(e)

            # If this wasn't the last attempt, wait before retry
            if attempt < operation.max_retries:
                await asyncio.sleep(2**attempt)  # Exponential backoff

        # All retries failed
        result = BatchResult(
            operation_id=operation.id,
            status=OperationStatus.FAILED,
            error=error_msg,
            execution_time=(datetime.now() - start_time).total_seconds(),
            retry_count=operation.max_retries,
        )

        # Record failed execution for learning
        await self.preference_engine.record_command(operation.tool_name, operation.parameters, context, success=False)

        return result

    async def _call_tool_executor(self, tool_name: str, parameters: dict[str, Any], context: dict[str, Any]) -> Any:
        """Call the appropriate tool executor."""
        if tool_name not in self.tool_executors:
            raise ValueError(f"No executor registered for tool: {tool_name}")

        executor = self.tool_executors[tool_name]
        return await executor(parameters, context)

    def _build_dependency_graph(self, operations: list[BatchOperation]) -> dict[str, list[str]]:
        """Build a dependency graph from operations."""
        graph = {}

        for operation in operations:
            graph[operation.id] = operation.depends_on.copy()

        return graph

    def _topological_sort(self, dependency_graph: dict[str, list[str]]) -> list[BatchOperation]:
        """Sort operations by dependencies using topological sort."""
        # Get the current batch being processed
        current_batch = None
        for batch in self.active_batches.values():
            if batch.results == []:  # This is the batch being executed
                current_batch = batch
                break

        if not current_batch:
            return []

        # Create a mapping from operation ID to operation object
        operations_map = {op.id: op for op in current_batch.operations}

        # Kahn's algorithm for topological sorting
        in_degree = dict.fromkeys(dependency_graph, 0)

        # Calculate in-degrees (reverse dependencies)
        for node in dependency_graph:
            for dependency in dependency_graph[node]:
                if dependency in in_degree:
                    in_degree[node] += 1

        # Initialize queue with nodes that have no dependencies
        queue = [node for node in in_degree if in_degree[node] == 0]
        result = []

        while queue:
            node = queue.pop(0)
            if node in operations_map:
                result.append(operations_map[node])

            # Update in-degrees of dependent nodes
            for dependent in dependency_graph:
                if node in dependency_graph[dependent]:
                    in_degree[dependent] -= 1
                    if in_degree[dependent] == 0:
                        queue.append(dependent)

        return result

    def _group_by_dependency_level(self, operations: list[BatchOperation]) -> list[list[BatchOperation]]:
        """Group operations by dependency level for parallel execution."""
        levels = []
        remaining_operations = operations.copy()
        completed_operations = set()

        while remaining_operations:
            current_level = []

            # Find operations that can run at this level
            for operation in remaining_operations[:]:
                if all(dep in completed_operations for dep in operation.depends_on):
                    current_level.append(operation)
                    remaining_operations.remove(operation)

            if not current_level:
                # Circular dependency or missing dependency
                break

            levels.append(current_level)
            completed_operations.update(op.id for op in current_level)

        return levels

    def _dependencies_satisfied(self, operation: BatchOperation, results: list[BatchResult]) -> bool:
        """Check if an operation's dependencies are satisfied."""
        completed_ops = {r.operation_id for r in results if r.status == OperationStatus.COMPLETED}

        return all(dep in completed_ops for dep in operation.depends_on)

    async def _rollback_batch(self, batch: BatchExecution, context: dict[str, Any]):
        """Rollback completed operations in reverse order."""
        completed_results = [r for r in batch.results if r.status == OperationStatus.COMPLETED]
        completed_results.reverse()  # Rollback in reverse order

        for result in completed_results:
            # Find the original operation
            operation = next((op for op in batch.operations if op.id == result.operation_id), None)

            if operation and operation.rollback_operation:
                try:
                    rollback_params = operation.rollback_operation
                    rollback_tool = rollback_params.get("tool")
                    rollback_args = rollback_params.get("params", {})

                    if rollback_tool in self.tool_executors:
                        await self._call_tool_executor(rollback_tool, rollback_args, context)

                        # Mark as rolled back
                        result.status = OperationStatus.ROLLED_BACK

                except Exception as e:
                    print(f"Rollback failed for operation {result.operation_id}: {e}")

    def get_batch_status(self, batch_id: str) -> dict[str, Any] | None:
        """Get the current status of a batch operation."""
        if batch_id in self.active_batches:
            batch = self.active_batches[batch_id]
            return {
                "batch_id": batch_id,
                "status": "running",
                "total_operations": batch.total_operations,
                "completed_operations": len([r for r in batch.results if r.status == OperationStatus.COMPLETED]),
                "failed_operations": len([r for r in batch.results if r.status == OperationStatus.FAILED]),
                "progress": len(batch.results) / batch.total_operations if batch.total_operations > 0 else 0,
            }

        # Check history
        for batch in self.batch_history:
            if batch.batch_id == batch_id:
                return {
                    "batch_id": batch_id,
                    "status": "completed",
                    "total_operations": batch.total_operations,
                    "successful_operations": batch.successful_operations,
                    "failed_operations": batch.failed_operations,
                    "execution_time": batch.execution_time,
                }

        return None

    def create_macro(self, name: str, operations: list[dict[str, Any]], description: str = "") -> dict[str, Any]:
        """Create a reusable macro from a sequence of operations."""
        macro = {
            "name": name,
            "description": description,
            "operations": operations,
            "created_at": datetime.now().isoformat(),
            "usage_count": 0,
        }

        return macro

    async def execute_macro(
        self, macro: dict[str, Any], context: dict[str, Any], mode: BatchMode = BatchMode.SEQUENTIAL
    ) -> str:
        """Execute a predefined macro."""
        batch_id = await self.create_batch(macro["operations"], mode)

        # Update usage count
        macro["usage_count"] += 1

        await self.execute_batch(batch_id, context)
        return batch_id

    def suggest_batch_optimizations(self, operations: list[dict[str, Any]]) -> list[str]:
        """Suggest optimizations for a batch of operations."""
        suggestions = []

        # Analyze operation patterns
        tool_counts = {}
        for op in operations:
            tool = op.get("tool", "unknown")
            tool_counts[tool] = tool_counts.get(tool, 0) + 1

        # Suggest parallel execution for independent operations
        has_dependencies = any(op.get("depends_on") for op in operations)
        if not has_dependencies and len(operations) > 1:
            suggestions.append("Consider using parallel execution mode for better performance")

        # Suggest grouping similar operations
        if any(count > 1 for count in tool_counts.values()):
            suggestions.append("Group similar operations together to optimize execution")

        # Suggest timeout adjustments
        if any(op.get("timeout", 30) > 60 for op in operations):
            suggestions.append("Some operations have long timeouts - consider breaking them into smaller steps")

        # Suggest rollback operations for destructive changes
        destructive_tools = ["memcord_archive", "memcord_merge", "memcord_compress"]
        has_destructive = any(op.get("tool") in destructive_tools for op in operations)
        if has_destructive:
            suggestions.append("Consider adding rollback operations for destructive changes")

        return suggestions

    async def _load_batch_history(self):
        """Load batch history from disk."""
        try:
            if self.batch_history_file.exists():
                async with aiofiles.open(self.batch_history_file) as f:
                    content = await f.read()
                    history_data = json.loads(content)

                    for batch_dict in history_data:
                        # Reconstruct BatchExecution objects
                        batch_dict["started_at"] = datetime.fromisoformat(batch_dict["started_at"])
                        if batch_dict["completed_at"]:
                            batch_dict["completed_at"] = datetime.fromisoformat(batch_dict["completed_at"])

                        # Reconstruct operations and results
                        operations = []
                        for op_dict in batch_dict["operations"]:
                            operations.append(BatchOperation(**op_dict))
                        batch_dict["operations"] = operations

                        results = []
                        for result_dict in batch_dict["results"]:
                            result_dict["timestamp"] = datetime.fromisoformat(result_dict["timestamp"])
                            result_dict["status"] = OperationStatus(result_dict["status"])
                            results.append(BatchResult(**result_dict))
                        batch_dict["results"] = results

                        batch_dict["mode"] = BatchMode(batch_dict["mode"])
                        self.batch_history.append(BatchExecution(**batch_dict))

        except Exception:
            # If loading fails, start with empty history
            self.batch_history = []

    async def _save_batch_history(self):
        """Save batch history to disk."""
        try:
            history_data = []
            for batch in self.batch_history:
                batch_dict = asdict(batch)

                # Convert enums and datetime to strings
                batch_dict["mode"] = batch.mode.value
                batch_dict["started_at"] = batch.started_at.isoformat()
                if batch.completed_at:
                    batch_dict["completed_at"] = batch.completed_at.isoformat()

                # Convert results
                for result in batch_dict["results"]:
                    result["status"] = result["status"].value
                    result["timestamp"] = result["timestamp"].isoformat()

                history_data.append(batch_dict)

            async with aiofiles.open(self.batch_history_file, "w") as f:
                await f.write(json.dumps(history_data, indent=2, default=str))

        except Exception as e:
            print(f"Failed to save batch history: {e}")


# Helper functions for common batch patterns
def create_project_setup_batch(project_name: str, project_type: str = "web") -> list[dict[str, Any]]:
    """Create a batch for setting up a new project."""
    return [
        {
            "id": f"create_main_{project_name}",
            "tool": "memcord_name",
            "params": {"slot_name": f"proj_{project_name}"},
            "description": f"Create main slot for {project_name}",
        },
        {
            "id": f"tag_main_{project_name}",
            "tool": "memcord_tag",
            "params": {"action": "add", "tags": ["project", project_type, project_name]},
            "depends_on": [f"create_main_{project_name}"],
            "description": "Tag main project slot",
        },
        {
            "id": f"group_main_{project_name}",
            "tool": "memcord_group",
            "params": {"action": "set", "group_path": f"projects/{project_name}"},
            "depends_on": [f"create_main_{project_name}"],
            "description": "Group main project slot",
        },
        {
            "id": f"create_frontend_{project_name}",
            "tool": "memcord_name",
            "params": {"slot_name": f"proj_{project_name}_frontend"},
            "depends_on": [f"tag_main_{project_name}", f"group_main_{project_name}"],
            "description": f"Create frontend slot for {project_name}",
        },
        {
            "id": f"create_backend_{project_name}",
            "tool": "memcord_name",
            "params": {"slot_name": f"proj_{project_name}_backend"},
            "depends_on": [f"tag_main_{project_name}", f"group_main_{project_name}"],
            "description": f"Create backend slot for {project_name}",
        },
    ]


def create_maintenance_batch() -> list[dict[str, Any]]:
    """Create a batch for routine memory maintenance."""
    return [
        {
            "id": "analyze_compression",
            "tool": "memcord_compress",
            "params": {"action": "analyze"},
            "description": "Analyze compression opportunities",
        },
        {
            "id": "find_archive_candidates",
            "tool": "memcord_archive",
            "params": {"action": "candidates", "days_inactive": 30},
            "description": "Find archival candidates",
        },
        {
            "id": "compress_content",
            "tool": "memcord_compress",
            "params": {"action": "compress"},
            "depends_on": ["analyze_compression"],
            "description": "Compress eligible content",
        },
        {
            "id": "create_maintenance_log",
            "tool": "memcord_name",
            "params": {"slot_name": f"maintenance_{datetime.now().strftime('%Y_%m_%d')}"},
            "depends_on": ["compress_content", "find_archive_candidates"],
            "description": "Create maintenance log",
        },
    ]
