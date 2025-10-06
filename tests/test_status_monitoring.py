"""Tests for status monitoring system.

Tests system health checks and monitoring functionality.

Coverage: 86%
- Async health check operations (validates async/await bug fix)
- Storage health monitoring
- System diagnostics and reporting
- Component integration

Tests focus on the async/await patterns that were fixed.
"""

import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from memcord.status_monitoring import (
    DiagnosticTool,
    HealthStatus,
    MetricsCollector,
    OperationLogger,
    ResourceMonitor,
    StatusMonitoringSystem,
)


class MockStorageManager:
    """Mock storage manager for testing async operations."""

    def __init__(self, slot_count: int = 5, should_fail: bool = False):
        self.slot_count = slot_count
        self.should_fail = should_fail

    async def list_memory_slots(self) -> list[dict]:
        """Mock async method that returns memory slots matching real storage format."""
        if self.should_fail:
            raise RuntimeError("Storage manager failure")

        # Simulate some async work
        await asyncio.sleep(0.01)

        return [
            {
                "name": f"slot_{i}",
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
                "entry_count": 5 + i,
                "total_length": 1000 + i * 100,
                "is_current": i == 0,
            }
            for i in range(self.slot_count)
        ]


@pytest.mark.asyncio
async def test_check_storage_health_with_valid_storage():
    """Test storage health check with a working storage manager."""
    storage_manager = MockStorageManager(slot_count=3)
    diagnostic_tool = DiagnosticTool(storage_manager=storage_manager)

    # This should work without coroutine errors
    health_status = await diagnostic_tool._check_storage_health()

    assert health_status.service == "storage"
    assert health_status.status == "healthy"
    assert health_status.details["slot_count"] == 3
    assert health_status.details["storage_responsive"] is True
    assert health_status.error_message is None
    assert health_status.response_time >= 0  # Windows may have 0.0 due to precision


@pytest.mark.asyncio
async def test_check_storage_health_with_failing_storage():
    """Test storage health check when storage manager fails."""
    storage_manager = MockStorageManager(should_fail=True)
    diagnostic_tool = DiagnosticTool(storage_manager=storage_manager)

    health_status = await diagnostic_tool._check_storage_health()

    assert health_status.service == "storage"
    assert health_status.status == "unhealthy"
    assert health_status.details["error_type"] == "RuntimeError"
    assert health_status.error_message == "Storage manager failure"
    assert health_status.response_time >= 0  # Windows may have 0.0 due to precision


@pytest.mark.asyncio
async def test_check_storage_health_without_storage_manager():
    """Test storage health check when no storage manager is provided."""
    diagnostic_tool = DiagnosticTool(storage_manager=None)

    health_status = await diagnostic_tool._check_storage_health()

    assert health_status.service == "storage"
    assert health_status.status == "unknown"
    assert health_status.details["message"] == "Storage manager not available"
    assert health_status.error_message == "Storage manager not initialized"
    assert health_status.response_time == 0


@pytest.mark.asyncio
async def test_run_health_checks_async_integration():
    """Test that run_health_checks properly awaits async storage health check."""
    storage_manager = MockStorageManager(slot_count=7)
    diagnostic_tool = DiagnosticTool(storage_manager=storage_manager)

    # This was the original bug - run_health_checks wasn't awaiting _check_storage_health
    health_checks = await diagnostic_tool.run_health_checks()

    assert len(health_checks) == 4  # storage, memory, filesystem, python_environment

    # Find the storage health check
    storage_check = next((check for check in health_checks if check.service == "storage"), None)

    assert storage_check is not None
    assert storage_check.status == "healthy"
    assert storage_check.details["slot_count"] == 7


@pytest.mark.asyncio
async def test_run_health_checks_handles_storage_exceptions():
    """Test that run_health_checks properly handles storage exceptions."""
    storage_manager = MockStorageManager(should_fail=True)
    diagnostic_tool = DiagnosticTool(storage_manager=storage_manager)

    health_checks = await diagnostic_tool.run_health_checks()

    # Should not raise an exception, should return unhealthy status
    storage_check = next((check for check in health_checks if check.service == "storage"), None)

    assert storage_check is not None
    assert storage_check.status == "unhealthy"
    assert "RuntimeError" in storage_check.details["error_type"]


@pytest.mark.asyncio
async def test_status_monitoring_system_integration():
    """Test full status monitoring system with async storage manager."""
    storage_manager = MockStorageManager(slot_count=10)

    monitoring_system = StatusMonitoringSystem(storage_manager=storage_manager)

    try:
        # This tests the full async integration
        system_status = await monitoring_system.get_system_status()

        assert "overall_status" in system_status
        assert "health_checks" in system_status
        assert len(system_status["health_checks"]) == 4

        # Verify storage health is properly included
        storage_health = next(
            (check for check in system_status["health_checks"] if check["service"] == "storage"),
            None,
        )

        assert storage_health is not None
        assert storage_health["status"] == "healthy"
        assert storage_health["details"]["slot_count"] == 10

    finally:
        monitoring_system.shutdown()


@pytest.mark.asyncio
async def test_diagnostic_tool_generate_system_report():
    """Test that diagnostic tool can generate comprehensive reports with async components."""
    storage_manager = MockStorageManager(slot_count=5)
    diagnostic_tool = DiagnosticTool(storage_manager=storage_manager)

    # Create mock components
    metrics_collector = MetricsCollector()
    operation_logger = OperationLogger()
    resource_monitor = ResourceMonitor()

    # Generate system report (this calls run_health_checks internally)
    report = await diagnostic_tool.generate_system_report(
        metrics_collector=metrics_collector,
        operation_logger=operation_logger,
        resource_monitor=resource_monitor,
    )

    assert "timestamp" in report
    assert "health_checks" in report
    assert len(report["health_checks"]) == 4

    # Verify async storage health check is included
    storage_health = next(
        (check for check in report["health_checks"] if check["service"] == "storage"),
        None,
    )

    assert storage_health is not None
    assert storage_health["status"] == "healthy"


def test_memory_health_check_sync():
    """Test that memory health check works synchronously."""
    diagnostic_tool = DiagnosticTool()

    health_status = diagnostic_tool._check_memory_health()

    assert health_status.service == "memory"
    assert health_status.status in ["healthy", "degraded", "unhealthy"]
    assert "process_memory_mb" in health_status.details
    assert "process_memory_percent" in health_status.details
    assert health_status.response_time >= 0  # Windows may have 0.0 due to precision


def test_filesystem_health_check_sync():
    """Test that filesystem health check works synchronously."""
    diagnostic_tool = DiagnosticTool()

    health_status = diagnostic_tool._check_filesystem_health()

    assert health_status.service == "filesystem"
    assert health_status.status in ["healthy", "degraded", "unhealthy"]
    assert "disk_free_percent" in health_status.details
    assert "write_test" in health_status.details
    assert health_status.response_time >= 0  # Windows may have 0.0 due to precision


def test_python_environment_health_check_sync():
    """Test that Python environment health check works synchronously."""
    diagnostic_tool = DiagnosticTool()

    health_status = diagnostic_tool._check_python_environment()

    assert health_status.service == "python_environment"
    assert health_status.status == "healthy"
    assert "python_version" in health_status.details
    assert "platform" in health_status.details
    assert health_status.response_time >= 0  # Windows may have 0.0 due to precision


@pytest.mark.asyncio
async def test_async_await_pattern_fix():
    """Specific test for the async/await bug that was fixed.

    This test ensures that:
    1. _check_storage_health is properly declared as async
    2. run_health_checks properly awaits _check_storage_health
    3. list_memory_slots is properly awaited
    """
    storage_manager = MockStorageManager(slot_count=3)
    diagnostic_tool = DiagnosticTool(storage_manager=storage_manager)

    # Test that _check_storage_health is async and can be awaited
    health_status = await diagnostic_tool._check_storage_health()
    assert isinstance(health_status, HealthStatus)

    # Test that run_health_checks properly awaits the async method
    health_checks = await diagnostic_tool.run_health_checks()
    assert len(health_checks) == 4

    # Verify no coroutine objects are returned (the original bug)
    for check in health_checks:
        assert isinstance(check, HealthStatus)
        assert not asyncio.iscoroutine(check)


@pytest.mark.asyncio
async def test_storage_manager_list_memory_slots_properly_awaited():
    """Test that storage_manager.list_memory_slots() is properly awaited."""

    # Create a mock that tracks if it was awaited
    storage_manager = MagicMock()
    storage_manager.list_memory_slots = AsyncMock(
        return_value=[{"name": "test_slot", "created": "2025-01-01T00:00:00"}]
    )

    diagnostic_tool = DiagnosticTool(storage_manager=storage_manager)

    health_status = await diagnostic_tool._check_storage_health()

    # Verify the async method was called
    storage_manager.list_memory_slots.assert_awaited_once()

    # Verify the results are processed correctly
    assert health_status.status == "healthy"
    assert health_status.details["slot_count"] == 1
    assert health_status.details["storage_responsive"] is True


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v"])
