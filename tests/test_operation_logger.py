"""Tests for OperationLogger component.

Tests operation tracking and logging functionality.

Coverage: 75%+
- Operation start/complete tracking
- Log filtering (tool, status, time)
- Statistics calculation
- Thread safety and memory tracking

Tests use direct fixture usage for cleaner code.
"""

import time
from datetime import datetime, timedelta
from threading import Thread
from unittest.mock import patch

import pytest

from memcord.status_monitoring import OperationLogger


def test_operation_logger_initialization(operation_logger):
    """Test OperationLogger initialization."""
    assert operation_logger.operation_logs.maxlen == 50000
    assert len(operation_logger.operation_logs) == 0
    assert len(operation_logger.active_operations) == 0

    logger_custom = OperationLogger(max_logs=10000)
    assert logger_custom.operation_logs.maxlen == 10000


def test_start_operation(operation_logger):
    """Test starting operation tracking."""
    operation_id = "test_op_001"
    tool_name = "test_tool"
    parameters = {"param1": "value1", "param2": 42}

    operation_logger.start_operation(operation_id, tool_name, parameters)

    # Check active operations
    assert operation_id in operation_logger.active_operations
    active_op = operation_logger.active_operations[operation_id]

    assert active_op.operation_id == operation_id
    assert active_op.tool_name == tool_name
    assert active_op.parameters == parameters
    assert active_op.status == "started"
    assert active_op.end_time is None
    assert active_op.duration_ms is None
    assert isinstance(active_op.start_time, datetime)

    # Check operation logs
    assert len(operation_logger.operation_logs) == 1
    logged_op = operation_logger.operation_logs[0]
    assert logged_op.operation_id == operation_id


def test_complete_operation_success(operation_logger):
    """Test completing operation with success status."""
    operation_id = "test_op_002"
    operation_logger.start_operation(operation_id, "test_tool", {})

    # Small delay to ensure duration calculation
    time.sleep(0.01)

    operation_logger.complete_operation(operation_id, status="completed", result_size_bytes=1024)

    # Check operation is removed from active operations
    assert operation_id not in operation_logger.active_operations

    # Check operation log is updated
    completed_op = None
    for op in operation_logger.operation_logs:
        if op.operation_id == operation_id:
            completed_op = op
            break

    assert completed_op is not None
    assert completed_op.status == "completed"
    assert completed_op.end_time is not None
    assert completed_op.duration_ms is not None
    assert completed_op.duration_ms > 0
    assert completed_op.result_size_bytes == 1024


def test_complete_operation_failure(operation_logger):
    """Test completing operation with failure status."""
    operation_id = "test_op_003"
    operation_logger.start_operation(operation_id, "test_tool", {})

    error_message = "Test error occurred"
    operation_logger.complete_operation(operation_id, status="failed", error_message=error_message)

    # Find the completed operation
    failed_op = None
    for op in operation_logger.operation_logs:
        if op.operation_id == operation_id:
            failed_op = op
            break

    assert failed_op is not None
    assert failed_op.status == "failed"
    assert failed_op.error_message == error_message


def test_complete_nonexistent_operation(operation_logger):
    """Test completing an operation that doesn't exist."""
    # This should not raise an exception
    operation_logger.complete_operation("nonexistent_op", status="completed")

    # Should not affect the logs
    assert len(operation_logger.operation_logs) == 0


def test_get_operation_logs_basic(operation_logger):
    """Test basic operation log retrieval."""
    # Start and complete several operations with unique timestamps
    import time

    for i in range(5):
        op_id = f"test_op_{i:03d}"
        operation_logger.start_operation(op_id, f"tool_{i}", {"index": i})
        time.sleep(0.001)  # Ensure unique timestamps on Windows
        operation_logger.complete_operation(op_id, status="completed")

    logs = operation_logger.get_operation_logs()

    assert len(logs) == 5
    # Should be sorted by start time (most recent first)
    assert logs[0].operation_id == "test_op_004"
    assert logs[-1].operation_id == "test_op_000"


def test_get_operation_logs_with_tool_filter(operation_logger):
    """Test filtering operation logs by tool name."""
    # Create operations with different tools
    operation_logger.start_operation("op1", "tool_a", {})
    operation_logger.complete_operation("op1", status="completed")

    operation_logger.start_operation("op2", "tool_b", {})
    operation_logger.complete_operation("op2", status="completed")

    operation_logger.start_operation("op3", "tool_a", {})
    operation_logger.complete_operation("op3", status="completed")

    # Filter by tool_a
    tool_a_logs = operation_logger.get_operation_logs(tool_name="tool_a")
    assert len(tool_a_logs) == 2

    tool_names = [log.tool_name for log in tool_a_logs]
    assert all(name == "tool_a" for name in tool_names)


def test_get_operation_logs_with_status_filter(operation_logger):
    """Test filtering operation logs by status."""
    # Create operations with different statuses
    operation_logger.start_operation("op1", "tool", {})
    operation_logger.complete_operation("op1", status="completed")

    operation_logger.start_operation("op2", "tool", {})
    operation_logger.complete_operation("op2", status="failed", error_message="Error")

    operation_logger.start_operation("op3", "tool", {})
    operation_logger.complete_operation("op3", status="completed")

    # Filter by failed status
    failed_logs = operation_logger.get_operation_logs(status="failed")
    assert len(failed_logs) == 1
    assert failed_logs[0].operation_id == "op2"
    assert failed_logs[0].status == "failed"


def test_get_operation_logs_with_time_filter(operation_logger):
    """Test filtering operation logs by time."""
    base_time = datetime.now()

    with patch("memcord.status_monitoring.datetime") as mock_datetime:
        # Old operation (2 hours ago)
        mock_datetime.now.return_value = base_time - timedelta(hours=2)
        mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)
        operation_logger.start_operation("old_op", "tool", {})

        # Recent operation (30 minutes ago)
        mock_datetime.now.return_value = base_time - timedelta(minutes=30)
        operation_logger.start_operation("recent_op", "tool", {})

    # Filter for operations from last hour
    recent_logs = operation_logger.get_operation_logs(since=base_time - timedelta(hours=1))

    assert len(recent_logs) == 1
    assert recent_logs[0].operation_id == "recent_op"


def test_get_operation_logs_with_limit(operation_logger):
    """Test limiting operation log results."""
    # Create 10 operations with unique timestamps
    import time

    for i in range(10):
        op_id = f"op_{i:02d}"
        operation_logger.start_operation(op_id, "tool", {})
        time.sleep(0.001)  # Ensure unique timestamps on Windows
        operation_logger.complete_operation(op_id, status="completed")

    # Get only 3 most recent
    limited_logs = operation_logger.get_operation_logs(limit=3)
    assert len(limited_logs) == 3

    # Should be most recent operations
    operation_ids = [log.operation_id for log in limited_logs]
    assert operation_ids == ["op_09", "op_08", "op_07"]


def test_get_operation_stats(operation_logger):
    """Test operation statistics calculation."""
    base_time = datetime.now()

    with patch.object(operation_logger, "_get_current_memory_usage", return_value=100.0):
        with patch("memcord.status_monitoring.datetime") as mock_datetime:
            # Successful operations with controlled timing
            for i in range(7):
                op_id = f"success_{i}"

                # Set start time
                start_time = base_time + timedelta(seconds=i * 10)
                mock_datetime.now.return_value = start_time
                mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)
                operation_logger.start_operation(op_id, "tool_success", {})

                # Set end time for known duration
                end_time = start_time + timedelta(milliseconds=100 * (i + 1))
                mock_datetime.now.return_value = end_time
                operation_logger.complete_operation(op_id, status="completed")

            # Failed operations
            for i in range(3):
                op_id = f"failure_{i}"
                start_time = base_time + timedelta(seconds=100 + i * 10)
                mock_datetime.now.return_value = start_time
                operation_logger.start_operation(op_id, "tool_failure", {})

                end_time = start_time + timedelta(milliseconds=50)
                mock_datetime.now.return_value = end_time
                operation_logger.complete_operation(op_id, status="failed", error_message="Error")

    stats = operation_logger.get_operation_stats()

    assert stats["total_operations"] == 10
    assert stats["completed_operations"] == 7
    assert stats["failed_operations"] == 3
    assert stats["success_rate"] == 70.0  # 7/10 * 100

    # Check tool distribution
    assert stats["tool_distribution"]["tool_success"] == 7
    assert stats["tool_distribution"]["tool_failure"] == 3

    # Check duration statistics (only for completed operations)
    # Durations should be 100, 200, 300, 400, 500, 600, 700 ms
    assert stats["avg_duration_ms"] == 400.0  # (100+200+...+700)/7
    assert stats["min_duration_ms"] == 100.0
    assert stats["max_duration_ms"] == 700.0

    # Check slowest operations
    assert len(stats["slowest_operations"]) == 5
    assert stats["slowest_operations"][0]["duration_ms"] == 700.0


def test_get_operation_stats_empty(operation_logger):
    """Test operation statistics with no operations."""
    stats = operation_logger.get_operation_stats()

    assert stats["total_operations"] == 0


def test_thread_safety(operation_logger):
    """Test that OperationLogger is thread-safe."""

    def worker_thread(thread_id: int):
        """Worker thread that starts and completes operations."""
        for i in range(10):  # Reduced to avoid hitting deque maxlen
            op_id = f"thread_{thread_id}_op_{i}"
            operation_logger.start_operation(op_id, f"tool_{thread_id}", {"index": i})
            time.sleep(0.001)  # Small delay
            operation_logger.complete_operation(op_id, status="completed")

    # Start multiple threads
    threads = []
    for thread_id in range(3):
        thread = Thread(target=worker_thread, args=(thread_id,))
        threads.append(thread)
        thread.start()

    # Wait for completion
    for thread in threads:
        thread.join()

    # Verify all operations were logged (get_operation_logs has default limit=100)
    logs = operation_logger.get_operation_logs(limit=None)  # Get all logs
    assert len(logs) == 30  # 3 threads * 10 operations each

    # Verify no active operations remain
    assert len(operation_logger.active_operations) == 0

    # Verify thread safety by checking all tool names appear
    tool_names = {log.tool_name for log in logs}
    assert "tool_0" in tool_names
    assert "tool_1" in tool_names
    assert "tool_2" in tool_names


def test_memory_usage_tracking(operation_logger):
    """Test that memory usage is tracked during operations."""
    with patch.object(operation_logger, "_get_current_memory_usage", return_value=256.5):
        operation_logger.start_operation("memory_test", "tool", {})

        # Check that memory usage was recorded
        active_op = operation_logger.active_operations["memory_test"]
        assert active_op.memory_usage_mb == 256.5


def test_max_logs_limit():
    """Test that operation logs respect max_logs limit."""
    logger = OperationLogger(max_logs=100)

    # Create more operations than the limit
    for i in range(150):
        op_id = f"op_{i:03d}"
        logger.start_operation(op_id, "tool", {})
        logger.complete_operation(op_id, status="completed")

    # Should only keep the most recent 100
    logs = logger.get_operation_logs()
    assert len(logs) <= 100

    # Should contain the most recent operations
    operation_ids = [log.operation_id for log in logs]
    assert "op_149" in operation_ids  # Most recent
    assert "op_000" not in operation_ids  # Should be evicted


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
