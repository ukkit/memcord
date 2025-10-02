"""Tests for MetricsCollector component.

Tests performance metrics collection and statistical analysis.

Coverage: 75%+
- Metrics recording and retrieval
- Statistical summaries and time-based filtering
- Thread safety for concurrent operations
- Memory limits and eviction

Tests use direct fixture usage for cleaner code.
"""

import time
from datetime import datetime, timedelta
from threading import Thread
from unittest.mock import patch

import pytest

from memcord.status_monitoring import MetricsCollector


def test_metrics_collector_initialization(metrics_collector):
    """Test MetricsCollector initialization with different max_metrics."""
    from .conftest import MetricsCollectorFactory

    assert metrics_collector.max_metrics == 10000
    assert len(metrics_collector.metrics) == 0

    collector_custom = MetricsCollectorFactory.create_with_max_metrics(5000)
    assert collector_custom.max_metrics == 5000


def test_record_single_metric(metrics_collector):
    """Test recording a single performance metric."""
    metrics_collector.record_metric("response_time", 125.5, "ms", {"endpoint": "/api/test"})

    metrics = metrics_collector.get_metrics("response_time")
    assert len(metrics) == 1

    metric = metrics[0]
    assert metric.metric_name == "response_time"
    assert metric.value == 125.5
    assert metric.unit == "ms"
    assert metric.tags == {"endpoint": "/api/test"}
    assert isinstance(metric.timestamp, datetime)


def test_record_multiple_metrics(metrics_collector):
    """Test recording multiple metrics and retrieval."""
    # Record multiple metrics
    for i in range(10):
        metrics_collector.record_metric("cpu_usage", float(i * 10), "percent")
        time.sleep(0.001)  # Small delay to ensure different timestamps

    metrics = metrics_collector.get_metrics("cpu_usage")
    assert len(metrics) == 10

    # Verify values are stored correctly
    values = [m.value for m in metrics]
    assert values == [float(i * 10) for i in range(10)]


def test_get_metrics_with_time_filter(metrics_collector):
    """Test filtering metrics by time."""
    # Record metrics at different times
    base_time = datetime.now()

    with patch("memcord.status_monitoring.datetime") as mock_datetime:
        # Mock datetime.now() for first metric (2 minutes ago)
        mock_datetime.now.return_value = base_time - timedelta(minutes=2)
        mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)
        metrics_collector.record_metric("test_metric", 1.0)

        # Mock datetime.now() for second metric (30 seconds ago)
        mock_datetime.now.return_value = base_time - timedelta(seconds=30)
        metrics_collector.record_metric("test_metric", 2.0)

        # Mock datetime.now() for third metric (now)
        mock_datetime.now.return_value = base_time
        metrics_collector.record_metric("test_metric", 3.0)

    # Get metrics from last minute (should get 2 metrics)
    recent_metrics = metrics_collector.get_metrics("test_metric", since=base_time - timedelta(minutes=1))

    assert len(recent_metrics) == 2
    values = [m.value for m in recent_metrics]
    assert 2.0 in values
    assert 3.0 in values


def test_get_metrics_with_limit(metrics_collector):
    """Test limiting number of returned metrics."""
    # Record 20 metrics
    for i in range(20):
        metrics_collector.record_metric("test_metric", float(i))

    # Get only last 5 metrics
    limited_metrics = metrics_collector.get_metrics("test_metric", limit=5)
    assert len(limited_metrics) == 5

    # Should return last 5 values (15, 16, 17, 18, 19)
    values = [m.value for m in limited_metrics]
    assert values == [15.0, 16.0, 17.0, 18.0, 19.0]


def test_get_metric_summary(metrics_collector):
    """Test statistical summary calculation."""

    # Record metrics with known values
    test_values = [10.0, 20.0, 30.0, 40.0, 50.0]
    for value in test_values:
        metrics_collector.record_metric("test_metric", value, "units")

    summary = metrics_collector.get_metric_summary("test_metric")

    assert summary["count"] == 5
    assert summary["avg"] == 30.0  # (10+20+30+40+50)/5
    assert summary["min"] == 10.0
    assert summary["max"] == 50.0
    assert summary["latest"] == 50.0
    assert summary["unit"] == "units"


def test_get_metric_summary_empty(metrics_collector):
    """Test metric summary with no data."""
    summary = metrics_collector.get_metric_summary("nonexistent_metric")

    expected = {"count": 0, "avg": 0, "min": 0, "max": 0, "latest": 0}
    assert summary == expected


def test_get_all_metric_names(metrics_collector):
    """Test getting all metric names."""
    metrics_collector.record_metric("cpu_usage", 50.0)
    metrics_collector.record_metric("memory_usage", 70.0)
    metrics_collector.record_metric("response_time", 120.0)

    metric_names = metrics_collector.get_all_metric_names()

    assert len(metric_names) == 3
    assert "cpu_usage" in metric_names
    assert "memory_usage" in metric_names
    assert "response_time" in metric_names


def test_thread_safety(metrics_collector):
    """Test that MetricsCollector is thread-safe."""

    def record_metrics(thread_id: int):
        """Record metrics from a specific thread."""
        for i in range(100):
            metrics_collector.record_metric(f"thread_{thread_id}_metric", float(i))

    # Create and start multiple threads
    threads = []
    for thread_id in range(5):
        thread = Thread(target=record_metrics, args=(thread_id,))
        threads.append(thread)
        thread.start()

    # Wait for all threads to complete
    for thread in threads:
        thread.join()

    # Verify all metrics were recorded
    all_metrics = []
    for thread_id in range(5):
        metrics = metrics_collector.get_metrics(f"thread_{thread_id}_metric")
        all_metrics.extend(metrics)

    assert len(all_metrics) == 500  # 5 threads * 100 metrics each


def test_max_metrics_limit():
    """Test that metrics collection respects max_metrics limit."""
    # Set a small max_metrics for testing
    collector = MetricsCollector(max_metrics=100)

    # Each metric name gets max_metrics // 10 = 10 slots
    for i in range(20):  # Record more than the limit
        collector.record_metric("test_metric", float(i))

    metrics = collector.get_metrics("test_metric")

    # Should only have last 10 metrics due to deque maxlen
    assert len(metrics) <= 10

    # Should contain the most recent values
    values = [m.value for m in metrics]
    assert max(values) == 19.0  # Last recorded value


def test_metrics_with_tags(metrics_collector):
    """Test metrics recording and retrieval with different tags."""
    metrics_collector.record_metric("api_response", 100.0, "ms", {"endpoint": "/users", "method": "GET"})
    metrics_collector.record_metric("api_response", 150.0, "ms", {"endpoint": "/orders", "method": "POST"})

    metrics = metrics_collector.get_metrics("api_response")
    assert len(metrics) == 2

    # Verify tags are preserved
    tags_list = [m.tags for m in metrics]
    assert {"endpoint": "/users", "method": "GET"} in tags_list
    assert {"endpoint": "/orders", "method": "POST"} in tags_list


def test_metric_summary_time_window(metrics_collector):
    """Test metric summary with different time windows."""

    base_time = datetime.now()

    with patch("memcord.status_monitoring.datetime") as mock_datetime:
        # Record old metric (2 hours ago)
        mock_datetime.now.return_value = base_time - timedelta(hours=2)
        mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)
        metrics_collector.record_metric("test_metric", 10.0)

        # Record recent metric (30 minutes ago)
        mock_datetime.now.return_value = base_time - timedelta(minutes=30)
        metrics_collector.record_metric("test_metric", 20.0)

        # Record current metric
        mock_datetime.now.return_value = base_time
        metrics_collector.record_metric("test_metric", 30.0)

    # Get summary for last hour (should only include 2 recent metrics)
    with patch("memcord.status_monitoring.datetime") as mock_datetime:
        mock_datetime.now.return_value = base_time
        summary = metrics_collector.get_metric_summary("test_metric", window_minutes=60)

    assert summary["count"] == 2
    assert summary["avg"] == 25.0  # (20 + 30) / 2
    assert summary["min"] == 20.0
    assert summary["max"] == 30.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
