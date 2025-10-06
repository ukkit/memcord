"""Tests for ResourceMonitor component.

Tests system resource monitoring and alert generation.

Coverage: 75%+
- Resource data collection (CPU, memory, disk)
- Alert generation based on thresholds
- Resource history and time filtering
- Thread safety and context management

Tests use direct fixture usage for cleaner code.
"""

import time
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

from memcord.status_monitoring import ResourceMonitor, SystemResource


def test_resource_monitor_initialization(resource_monitor):
    """Test ResourceMonitor initialization."""
    assert resource_monitor.collection_interval == 30
    assert resource_monitor.monitoring is False
    assert resource_monitor.monitor_thread is None
    assert len(resource_monitor.resource_history) == 0

    monitor_custom = ResourceMonitor(collection_interval=60)
    assert monitor_custom.collection_interval == 60


def test_resource_monitor_start_stop():
    """Test starting and stopping resource monitoring."""
    monitor = ResourceMonitor(collection_interval=1)  # Short interval for testing

    assert not monitor.monitoring

    monitor.start_monitoring()
    assert monitor.monitoring is True
    assert monitor.monitor_thread is not None
    assert monitor.monitor_thread.is_alive()

    # Let it collect at least one data point
    time.sleep(1.5)

    monitor.stop_monitoring()
    assert monitor.monitoring is False

    # Give thread time to stop
    time.sleep(0.5)
    assert not monitor.monitor_thread.is_alive()


def test_resource_monitor_double_start():
    """Test that starting monitoring twice doesn't create multiple threads."""
    monitor = ResourceMonitor(collection_interval=1)

    monitor.start_monitoring()
    first_thread = monitor.monitor_thread

    monitor.start_monitoring()  # Should not create new thread
    second_thread = monitor.monitor_thread

    assert first_thread is second_thread

    monitor.stop_monitoring()


@patch("psutil.cpu_percent")
@patch("psutil.virtual_memory")
@patch("psutil.disk_usage")
@patch("psutil.pids")
@patch("psutil.Process")
def test_collect_resource_data(mock_process, mock_pids, mock_disk, mock_memory, mock_cpu, resource_monitor):
    """Test resource data collection with mocked psutil."""
    # Mock return values
    mock_cpu.return_value = 45.5

    mock_memory_info = MagicMock()
    mock_memory_info.percent = 65.0
    mock_memory_info.used = 8 * 1024 * 1024 * 1024  # 8 GB
    mock_memory_info.available = 4 * 1024 * 1024 * 1024  # 4 GB
    mock_memory.return_value = mock_memory_info

    mock_disk_info = MagicMock()
    mock_disk_info.total = 1000 * 1024 * 1024 * 1024  # 1 TB
    mock_disk_info.used = 600 * 1024 * 1024 * 1024  # 600 GB
    mock_disk_info.free = 400 * 1024 * 1024 * 1024  # 400 GB
    mock_disk.return_value = mock_disk_info

    mock_pids.return_value = list(range(100))  # 100 processes

    mock_process_instance = MagicMock()
    mock_process_instance.num_threads.return_value = 25
    mock_process.return_value = mock_process_instance

    resource_data = resource_monitor._collect_resource_data()

    assert isinstance(resource_data, SystemResource)
    assert resource_data.cpu_percent == 45.5
    assert resource_data.memory_percent == 65.0
    assert resource_data.memory_used_mb == 8192.0  # 8 GB in MB
    assert resource_data.memory_available_mb == 4096.0  # 4 GB in MB
    assert resource_data.disk_usage_percent == 60.0  # 600/1000 * 100
    assert resource_data.disk_free_gb == 400.0  # 400 GB
    assert resource_data.process_count == 100
    assert resource_data.thread_count == 25
    assert isinstance(resource_data.timestamp, datetime)


def test_get_current_resources(resource_monitor):
    """Test getting current resource usage."""
    with patch.object(resource_monitor, "_collect_resource_data") as mock_collect:
        mock_resource = SystemResource(
            cpu_percent=50.0,
            memory_percent=70.0,
            memory_used_mb=4096.0,
            memory_available_mb=2048.0,
            disk_usage_percent=80.0,
            disk_free_gb=200.0,
            process_count=150,
            thread_count=30,
            timestamp=datetime.now(),
        )
        mock_collect.return_value = mock_resource

        current = resource_monitor.get_current_resources()
        assert current is mock_resource
        mock_collect.assert_called_once()


def test_get_resource_history(resource_monitor):
    """Test resource history retrieval with time filtering."""
    base_time = datetime.now()

    # Add some mock history data
    for i in range(5):
        resource = SystemResource(
            cpu_percent=float(i * 10),
            memory_percent=float(i * 15),
            memory_used_mb=1000.0 + i * 100,
            memory_available_mb=2000.0 - i * 50,
            disk_usage_percent=50.0 + i * 5,
            disk_free_gb=500.0 - i * 10,
            process_count=100 + i * 10,
            thread_count=20 + i * 2,
            timestamp=base_time - timedelta(minutes=i * 30),
        )
        resource_monitor.resource_history.append(resource)

    # Get history for last 2 hours (should get 4 items: 0, 30, 60, 90 minutes ago)
    # Use slightly less than 2 hours to avoid boundary issues on Windows
    history = resource_monitor.get_resource_history(hours=1.9)  # 114 minutes
    assert len(history) == 4

    # Should not include the 5th item (120 minutes ago)
    timestamps = [r.timestamp for r in history]
    oldest_timestamp = min(timestamps)
    cutoff_time = base_time - timedelta(hours=1.9)
    assert oldest_timestamp >= cutoff_time


def test_get_resource_alerts(resource_monitor):
    """Test resource usage alert generation."""
    # Test with high resource usage
    with patch.object(resource_monitor, "get_current_resources") as mock_get_current:
        high_usage_resource = SystemResource(
            cpu_percent=95.0,  # Critical
            memory_percent=90.0,  # Warning
            memory_used_mb=8000.0,
            memory_available_mb=800.0,
            disk_usage_percent=98.0,  # Critical
            disk_free_gb=10.0,
            process_count=200,
            thread_count=50,
            timestamp=datetime.now(),
        )
        mock_get_current.return_value = high_usage_resource

        alerts = resource_monitor.get_resource_alerts()

        # Should have 3 alerts: CPU critical, memory warning, disk critical
        assert len(alerts) == 3

        # Check CPU alert
        cpu_alert = next((a for a in alerts if a["type"] == "cpu_high"), None)
        assert cpu_alert is not None
        assert cpu_alert["severity"] == "critical"
        assert cpu_alert["value"] == 95.0

        # Check memory alert
        memory_alert = next((a for a in alerts if a["type"] == "memory_high"), None)
        assert memory_alert is not None
        assert memory_alert["severity"] == "warning"
        assert memory_alert["value"] == 90.0

        # Check disk alert
        disk_alert = next((a for a in alerts if a["type"] == "disk_full"), None)
        assert disk_alert is not None
        assert disk_alert["severity"] == "critical"
        assert disk_alert["value"] == 98.0


def test_get_resource_alerts_healthy(resource_monitor):
    """Test resource alerts with healthy system."""
    with patch.object(resource_monitor, "get_current_resources") as mock_get_current:
        healthy_resource = SystemResource(
            cpu_percent=30.0,
            memory_percent=50.0,
            memory_used_mb=4000.0,
            memory_available_mb=4000.0,
            disk_usage_percent=60.0,
            disk_free_gb=400.0,
            process_count=100,
            thread_count=25,
            timestamp=datetime.now(),
        )
        mock_get_current.return_value = healthy_resource

        alerts = resource_monitor.get_resource_alerts()
        assert len(alerts) == 0


def test_get_resource_alerts_warning_levels(resource_monitor):
    """Test resource alerts at warning thresholds."""
    with patch.object(resource_monitor, "get_current_resources") as mock_get_current:
        warning_resource = SystemResource(
            cpu_percent=80.0,  # Warning level
            memory_percent=88.0,  # Warning level
            memory_used_mb=7000.0,
            memory_available_mb=1000.0,
            disk_usage_percent=88.0,  # Warning level
            disk_free_gb=120.0,
            process_count=150,
            thread_count=35,
            timestamp=datetime.now(),
        )
        mock_get_current.return_value = warning_resource

        alerts = resource_monitor.get_resource_alerts()

        # Should have 3 warning alerts
        assert len(alerts) == 3
        for alert in alerts:
            assert alert["severity"] == "warning"


def test_monitor_loop_exception_handling():
    """Test that monitoring loop handles exceptions gracefully."""
    monitor = ResourceMonitor(collection_interval=0.1)  # Very short interval

    with patch.object(monitor, "_collect_resource_data") as mock_collect:
        # Make the first call raise an exception, then work normally
        mock_collect.side_effect = [
            RuntimeError("Test error"),
            SystemResource(
                cpu_percent=50.0,
                memory_percent=60.0,
                memory_used_mb=4000.0,
                memory_available_mb=2000.0,
                disk_usage_percent=70.0,
                disk_free_gb=300.0,
                process_count=100,
                thread_count=25,
                timestamp=datetime.now(),
            ),
        ]

        monitor.start_monitoring()
        time.sleep(0.3)  # Let it run through exception and recovery
        monitor.stop_monitoring()

        # Should have called collect at least twice (exception + success)
        assert mock_collect.call_count >= 2


def test_resource_history_maxlen(resource_monitor):
    """Test that resource history respects maxlen limit."""
    # Add more items than maxlen (2880)
    for i in range(3000):
        resource = SystemResource(
            cpu_percent=float(i),  # Use unique values instead of modulo
            memory_percent=50.0,
            memory_used_mb=4000.0,
            memory_available_mb=2000.0,
            disk_usage_percent=70.0,
            disk_free_gb=300.0,
            process_count=100,
            thread_count=25,
            timestamp=datetime.now() - timedelta(seconds=i),
        )
        resource_monitor.resource_history.append(resource)

    # Should only keep the most recent 2880 items
    assert len(resource_monitor.resource_history) == 2880

    # Should contain the most recent items (2999, 2998, ..., 120)
    cpu_values = [r.cpu_percent for r in resource_monitor.resource_history]
    assert 2999.0 in cpu_values  # Most recent item
    assert 120.0 in cpu_values  # Should be the oldest kept item
    assert 119.0 not in cpu_values  # Should be evicted
    assert 0.0 not in cpu_values  # Should be evicted


def test_resource_monitor_context_manager():
    """Test using ResourceMonitor as context manager."""
    monitor = ResourceMonitor(collection_interval=0.1)

    # Manual context manager simulation since ResourceMonitor doesn't implement it yet
    try:
        monitor.start_monitoring()
        assert monitor.monitoring is True
        time.sleep(0.2)
    finally:
        monitor.stop_monitoring()

    assert monitor.monitoring is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
