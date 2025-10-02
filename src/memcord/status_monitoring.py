"""System status monitoring and health check functionality for memcord.

This module provides comprehensive monitoring capabilities including:
1. Health check endpoints
2. Performance metrics collection and display
3. System resource monitoring
4. Operation history and logging
5. Diagnostic tools and system analysis
"""

import gc
import sys
import threading
import time
from collections import defaultdict, deque
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from pathlib import Path
from threading import Lock
from typing import Any

import psutil


@dataclass
class HealthStatus:
    """System health status information."""

    service: str
    status: str  # "healthy", "degraded", "unhealthy"
    timestamp: datetime
    response_time: float
    details: dict[str, Any]
    error_message: str | None = None


@dataclass
class PerformanceMetric:
    """Performance metric data point."""

    metric_name: str
    value: float
    timestamp: datetime
    unit: str
    tags: dict[str, str]


@dataclass
class SystemResource:
    """System resource usage information."""

    cpu_percent: float
    memory_percent: float
    memory_used_mb: float
    memory_available_mb: float
    disk_usage_percent: float
    disk_free_gb: float
    process_count: int
    thread_count: int
    timestamp: datetime


@dataclass
class OperationLog:
    """Operation execution log entry."""

    operation_id: str
    tool_name: str
    parameters: dict[str, Any]
    start_time: datetime
    end_time: datetime | None
    duration_ms: float | None
    status: str  # "started", "completed", "failed", "timeout"
    error_message: str | None
    memory_usage_mb: float | None
    result_size_bytes: int | None


class MetricsCollector:
    """Collects and manages performance metrics."""

    def __init__(self, max_metrics: int = 10000):
        self.metrics: dict[str, deque] = defaultdict(lambda: deque(maxlen=max_metrics // 10))
        self.max_metrics = max_metrics
        self._lock = Lock()

    def record_metric(self, name: str, value: float, unit: str = "", tags: dict[str, str] = None):
        """Record a performance metric."""
        with self._lock:
            metric = PerformanceMetric(
                metric_name=name, value=value, timestamp=datetime.now(), unit=unit, tags=tags or {}
            )
            self.metrics[name].append(metric)

    def get_metrics(self, name: str, since: datetime = None, limit: int = 100) -> list[PerformanceMetric]:
        """Get metrics for a specific metric name."""
        with self._lock:
            metrics = list(self.metrics[name])

            if since:
                metrics = [m for m in metrics if m.timestamp >= since]

            return metrics[-limit:] if limit else metrics

    def get_metric_summary(self, name: str, window_minutes: int = 60) -> dict[str, Any]:
        """Get statistical summary of a metric over a time window."""
        since = datetime.now() - timedelta(minutes=window_minutes)
        metrics = self.get_metrics(name, since)

        if not metrics:
            return {"count": 0, "avg": 0, "min": 0, "max": 0, "latest": 0}

        values = [m.value for m in metrics]
        return {
            "count": len(values),
            "avg": sum(values) / len(values),
            "min": min(values),
            "max": max(values),
            "latest": values[-1],
            "unit": metrics[0].unit if metrics else "",
        }

    def get_all_metric_names(self) -> list[str]:
        """Get all available metric names."""
        with self._lock:
            return list(self.metrics.keys())


class ResourceMonitor:
    """Monitors system resource usage."""

    def __init__(self, collection_interval: int = 30):
        self.collection_interval = collection_interval
        self.resource_history: deque = deque(maxlen=2880)  # 24 hours at 30s intervals
        self.monitoring = False
        self.monitor_thread = None
        self._lock = Lock()

    def start_monitoring(self):
        """Start continuous resource monitoring."""
        if self.monitoring:
            return

        self.monitoring = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()

    def stop_monitoring(self):
        """Stop continuous resource monitoring."""
        self.monitoring = False
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=5)

    def _monitor_loop(self):
        """Main monitoring loop."""
        while self.monitoring:
            try:
                resource_data = self._collect_resource_data()
                with self._lock:
                    self.resource_history.append(resource_data)
                time.sleep(self.collection_interval)
            except Exception as e:
                print(f"Resource monitoring error: {e}")
                time.sleep(self.collection_interval)

    def _collect_resource_data(self) -> SystemResource:
        """Collect current system resource data."""
        # CPU usage
        cpu_percent = psutil.cpu_percent(interval=1)

        # Memory usage
        memory = psutil.virtual_memory()

        # Disk usage (for current working directory)
        disk = psutil.disk_usage(".")

        # Process information
        try:
            process = psutil.Process()
            process_threads = process.num_threads()
        except (psutil.NoSuchProcess, psutil.AccessDenied, OSError):
            process_threads = threading.active_count()

        return SystemResource(
            cpu_percent=cpu_percent,
            memory_percent=memory.percent,
            memory_used_mb=memory.used / (1024 * 1024),
            memory_available_mb=memory.available / (1024 * 1024),
            disk_usage_percent=(disk.used / disk.total) * 100,
            disk_free_gb=disk.free / (1024 * 1024 * 1024),
            process_count=len(psutil.pids()),
            thread_count=process_threads,
            timestamp=datetime.now(),
        )

    def get_current_resources(self) -> SystemResource:
        """Get current resource usage."""
        return self._collect_resource_data()

    def get_resource_history(self, hours: int = 1) -> list[SystemResource]:
        """Get resource history for specified hours."""
        cutoff = datetime.now() - timedelta(hours=hours)
        with self._lock:
            return [r for r in self.resource_history if r.timestamp >= cutoff]

    def get_resource_alerts(self) -> list[dict[str, Any]]:
        """Check for resource usage alerts."""
        current = self.get_current_resources()
        alerts = []

        # CPU usage alerts
        if current.cpu_percent > 90:
            alerts.append(
                {
                    "type": "cpu_high",
                    "severity": "critical",
                    "message": f"CPU usage is very high: {current.cpu_percent:.1f}%",
                    "value": current.cpu_percent,
                    "threshold": 90,
                }
            )
        elif current.cpu_percent > 75:
            alerts.append(
                {
                    "type": "cpu_high",
                    "severity": "warning",
                    "message": f"CPU usage is high: {current.cpu_percent:.1f}%",
                    "value": current.cpu_percent,
                    "threshold": 75,
                }
            )

        # Memory usage alerts
        if current.memory_percent > 95:
            alerts.append(
                {
                    "type": "memory_high",
                    "severity": "critical",
                    "message": f"Memory usage is very high: {current.memory_percent:.1f}%",
                    "value": current.memory_percent,
                    "threshold": 95,
                }
            )
        elif current.memory_percent > 85:
            alerts.append(
                {
                    "type": "memory_high",
                    "severity": "warning",
                    "message": f"Memory usage is high: {current.memory_percent:.1f}%",
                    "value": current.memory_percent,
                    "threshold": 85,
                }
            )

        # Disk usage alerts
        if current.disk_usage_percent > 95:
            alerts.append(
                {
                    "type": "disk_full",
                    "severity": "critical",
                    "message": f"Disk usage is very high: {current.disk_usage_percent:.1f}%",
                    "value": current.disk_usage_percent,
                    "threshold": 95,
                }
            )
        elif current.disk_usage_percent > 85:
            alerts.append(
                {
                    "type": "disk_full",
                    "severity": "warning",
                    "message": f"Disk usage is high: {current.disk_usage_percent:.1f}%",
                    "value": current.disk_usage_percent,
                    "threshold": 85,
                }
            )

        return alerts


class OperationLogger:
    """Logs and tracks operation execution."""

    def __init__(self, max_logs: int = 50000):
        self.operation_logs: deque = deque(maxlen=max_logs)
        self.active_operations: dict[str, OperationLog] = {}
        self._lock = Lock()

    def start_operation(self, operation_id: str, tool_name: str, parameters: dict[str, Any]) -> None:
        """Log the start of an operation."""
        with self._lock:
            log_entry = OperationLog(
                operation_id=operation_id,
                tool_name=tool_name,
                parameters=parameters,
                start_time=datetime.now(),
                end_time=None,
                duration_ms=None,
                status="started",
                error_message=None,
                memory_usage_mb=self._get_current_memory_usage(),
                result_size_bytes=None,
            )
            self.active_operations[operation_id] = log_entry
            self.operation_logs.append(log_entry)

    def complete_operation(
        self, operation_id: str, status: str = "completed", error_message: str = None, result_size_bytes: int = None
    ) -> None:
        """Log the completion of an operation."""
        with self._lock:
            if operation_id in self.active_operations:
                log_entry = self.active_operations[operation_id]
                log_entry.end_time = datetime.now()
                log_entry.duration_ms = (log_entry.end_time - log_entry.start_time).total_seconds() * 1000
                log_entry.status = status
                log_entry.error_message = error_message
                log_entry.result_size_bytes = result_size_bytes

                # Update in the deque as well
                for i, entry in enumerate(self.operation_logs):
                    if entry.operation_id == operation_id:
                        self.operation_logs[i] = log_entry
                        break

                # Remove from active operations
                del self.active_operations[operation_id]

    def get_operation_logs(
        self, tool_name: str = None, status: str = None, since: datetime = None, limit: int = 100
    ) -> list[OperationLog]:
        """Get operation logs with optional filtering."""
        with self._lock:
            logs = list(self.operation_logs)

        # Apply filters
        if tool_name:
            logs = [log for log in logs if log.tool_name == tool_name]

        if status:
            logs = [log for log in logs if log.status == status]

        if since:
            logs = [log for log in logs if log.start_time >= since]

        # Sort by start time (most recent first) and limit
        logs.sort(key=lambda x: x.start_time, reverse=True)
        return logs[:limit] if limit else logs

    def get_operation_stats(self, window_hours: int = 24) -> dict[str, Any]:
        """Get operation statistics over a time window."""
        since = datetime.now() - timedelta(hours=window_hours)
        logs = self.get_operation_logs(since=since)

        if not logs:
            return {"total_operations": 0}

        # Calculate statistics
        completed_logs = [log for log in logs if log.status == "completed" and log.duration_ms is not None]
        failed_logs = [log for log in logs if log.status == "failed"]

        stats = {
            "total_operations": len(logs),
            "completed_operations": len(completed_logs),
            "failed_operations": len(failed_logs),
            "success_rate": len(completed_logs) / len(logs) * 100 if logs else 0,
            "tool_distribution": {},
            "avg_duration_ms": 0,
            "slowest_operations": [],
        }

        # Tool distribution
        tool_counts = defaultdict(int)
        for log in logs:
            tool_counts[log.tool_name] += 1
        stats["tool_distribution"] = dict(tool_counts)

        # Duration statistics
        if completed_logs:
            durations = [log.duration_ms for log in completed_logs]
            stats["avg_duration_ms"] = sum(durations) / len(durations)
            stats["min_duration_ms"] = min(durations)
            stats["max_duration_ms"] = max(durations)

            # Slowest operations
            slowest = sorted(completed_logs, key=lambda x: x.duration_ms, reverse=True)[:5]
            stats["slowest_operations"] = [
                {
                    "operation_id": op.operation_id,
                    "tool_name": op.tool_name,
                    "duration_ms": op.duration_ms,
                    "start_time": op.start_time.isoformat(),
                }
                for op in slowest
            ]

        return stats

    def _get_current_memory_usage(self) -> float:
        """Get current process memory usage in MB."""
        try:
            process = psutil.Process()
            return process.memory_info().rss / (1024 * 1024)
        except (psutil.NoSuchProcess, psutil.AccessDenied, OSError):
            return 0.0


class DiagnosticTool:
    """Provides diagnostic capabilities and system analysis."""

    def __init__(self, storage_manager=None):
        self.storage_manager = storage_manager

    async def run_health_checks(self) -> list[HealthStatus]:
        """Run comprehensive health checks."""
        checks = []

        # Storage system health
        checks.append(await self._check_storage_health())

        # Memory system health
        checks.append(self._check_memory_health())

        # File system health
        checks.append(self._check_filesystem_health())

        # Python environment health
        checks.append(self._check_python_environment())

        return checks

    async def _check_storage_health(self) -> HealthStatus:
        """Check storage system health."""
        start_time = time.time()

        try:
            if self.storage_manager:
                # Try to list memory slots (await the async function)
                slots = await self.storage_manager.list_memory_slots()
                response_time = (time.time() - start_time) * 1000

                return HealthStatus(
                    service="storage",
                    status="healthy",
                    timestamp=datetime.now(),
                    response_time=response_time,
                    details={"slot_count": len(slots), "storage_responsive": True},
                )
            else:
                return HealthStatus(
                    service="storage",
                    status="unknown",
                    timestamp=datetime.now(),
                    response_time=0,
                    details={"message": "Storage manager not available"},
                    error_message="Storage manager not initialized",
                )

        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            return HealthStatus(
                service="storage",
                status="unhealthy",
                timestamp=datetime.now(),
                response_time=response_time,
                details={"error_type": type(e).__name__},
                error_message=str(e),
            )

    def _check_memory_health(self) -> HealthStatus:
        """Check memory system health."""
        start_time = time.time()

        try:
            # Get memory statistics
            process = psutil.Process()
            memory_info = process.memory_info()
            system_memory = psutil.virtual_memory()

            response_time = (time.time() - start_time) * 1000

            # Determine health status
            memory_usage_pct = (memory_info.rss / system_memory.total) * 100

            if memory_usage_pct > 50:
                status = "degraded"
            elif memory_usage_pct > 80:
                status = "unhealthy"
            else:
                status = "healthy"

            return HealthStatus(
                service="memory",
                status=status,
                timestamp=datetime.now(),
                response_time=response_time,
                details={
                    "process_memory_mb": memory_info.rss / (1024 * 1024),
                    "process_memory_percent": memory_usage_pct,
                    "system_memory_percent": system_memory.percent,
                    "gc_stats": {"collections": gc.get_stats(), "count": gc.get_count()},
                },
            )

        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            return HealthStatus(
                service="memory",
                status="unhealthy",
                timestamp=datetime.now(),
                response_time=response_time,
                details={"error_type": type(e).__name__},
                error_message=str(e),
            )

    def _check_filesystem_health(self) -> HealthStatus:
        """Check file system health."""
        start_time = time.time()

        try:
            # Check disk space
            disk_usage = psutil.disk_usage(".")
            free_space_pct = (disk_usage.free / disk_usage.total) * 100

            # Test write capability
            test_file = Path("health_check_test.tmp")
            test_file.write_text("health check")
            test_file.unlink()

            response_time = (time.time() - start_time) * 1000

            # Determine status
            if free_space_pct < 5:
                status = "unhealthy"
            elif free_space_pct < 15:
                status = "degraded"
            else:
                status = "healthy"

            return HealthStatus(
                service="filesystem",
                status=status,
                timestamp=datetime.now(),
                response_time=response_time,
                details={
                    "disk_free_percent": free_space_pct,
                    "disk_free_gb": disk_usage.free / (1024**3),
                    "disk_total_gb": disk_usage.total / (1024**3),
                    "write_test": "passed",
                },
            )

        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            return HealthStatus(
                service="filesystem",
                status="unhealthy",
                timestamp=datetime.now(),
                response_time=response_time,
                details={"error_type": type(e).__name__},
                error_message=str(e),
            )

    def _check_python_environment(self) -> HealthStatus:
        """Check Python environment health."""
        start_time = time.time()

        try:
            details = {
                "python_version": sys.version,
                "platform": sys.platform,
                "thread_count": threading.active_count(),
                "modules_loaded": len(sys.modules),
                "path_length": len(sys.path),
            }

            response_time = (time.time() - start_time) * 1000

            return HealthStatus(
                service="python_environment",
                status="healthy",
                timestamp=datetime.now(),
                response_time=response_time,
                details=details,
            )

        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            return HealthStatus(
                service="python_environment",
                status="unhealthy",
                timestamp=datetime.now(),
                response_time=response_time,
                details={"error_type": type(e).__name__},
                error_message=str(e),
            )

    def analyze_performance_issues(
        self, metrics_collector: MetricsCollector, operation_logger: OperationLogger
    ) -> dict[str, Any]:
        """Analyze system for performance issues."""
        analysis = {"timestamp": datetime.now().isoformat(), "issues": [], "recommendations": []}

        # Check operation performance
        stats = operation_logger.get_operation_stats(window_hours=1)

        if stats["total_operations"] > 0:
            # High failure rate
            if stats["success_rate"] < 90:
                analysis["issues"].append(
                    {
                        "type": "high_failure_rate",
                        "severity": "warning",
                        "description": f"Operation success rate is {stats['success_rate']:.1f}% (last hour)",
                        "data": stats,
                    }
                )
                analysis["recommendations"].append("Review failed operations and check error patterns")

            # Slow operations
            if stats.get("avg_duration_ms", 0) > 5000:  # 5 seconds
                analysis["issues"].append(
                    {
                        "type": "slow_operations",
                        "severity": "warning",
                        "description": f"Average operation duration is {stats['avg_duration_ms']:.0f}ms",
                        "data": {"avg_duration": stats["avg_duration_ms"]},
                    }
                )
                analysis["recommendations"].append("Consider optimizing slow operations or adding caching")

        # Check resource metrics
        try:
            resource_monitor = ResourceMonitor()
            current_resources = resource_monitor.get_current_resources()

            # High resource usage
            if current_resources.memory_percent > 85:
                analysis["issues"].append(
                    {
                        "type": "high_memory_usage",
                        "severity": "critical" if current_resources.memory_percent > 95 else "warning",
                        "description": f"Memory usage is {current_resources.memory_percent:.1f}%",
                        "data": {"memory_percent": current_resources.memory_percent},
                    }
                )
                analysis["recommendations"].append("Monitor memory usage and consider garbage collection")

            if current_resources.cpu_percent > 85:
                analysis["issues"].append(
                    {
                        "type": "high_cpu_usage",
                        "severity": "critical" if current_resources.cpu_percent > 95 else "warning",
                        "description": f"CPU usage is {current_resources.cpu_percent:.1f}%",
                        "data": {"cpu_percent": current_resources.cpu_percent},
                    }
                )
                analysis["recommendations"].append("Review CPU-intensive operations and optimize")

        except Exception as e:
            analysis["issues"].append(
                {
                    "type": "monitoring_error",
                    "severity": "warning",
                    "description": f"Unable to collect resource metrics: {str(e)}",
                }
            )

        return analysis

    async def generate_system_report(
        self, metrics_collector: MetricsCollector, operation_logger: OperationLogger, resource_monitor: ResourceMonitor
    ) -> dict[str, Any]:
        """Generate comprehensive system status report."""
        report = {
            "timestamp": datetime.now().isoformat(),
            "health_checks": [asdict(check) for check in await self.run_health_checks()],
            "performance_analysis": self.analyze_performance_issues(metrics_collector, operation_logger),
            "operation_stats": operation_logger.get_operation_stats(),
            "resource_usage": asdict(resource_monitor.get_current_resources()),
            "resource_alerts": resource_monitor.get_resource_alerts(),
            "metrics_summary": {},
        }

        # Add metrics summary for key metrics
        for metric_name in ["operation_duration", "memory_usage", "response_time"]:
            try:
                summary = metrics_collector.get_metric_summary(metric_name)
                if summary["count"] > 0:
                    report["metrics_summary"][metric_name] = summary
            except (KeyError, AttributeError):
                pass  # Metric might not exist yet

        return report


class StatusMonitoringSystem:
    """Main system status monitoring coordinator."""

    def __init__(self, storage_manager=None, data_dir: str = "memory_slots"):
        self.storage_manager = storage_manager
        self.data_dir = Path(data_dir)
        self._start_time = time.time()

        # Initialize components
        self.metrics_collector = MetricsCollector()
        self.resource_monitor = ResourceMonitor()
        self.operation_logger = OperationLogger()
        self.diagnostic_tool = DiagnosticTool(storage_manager)

        # Start monitoring
        self.resource_monitor.start_monitoring()

    def shutdown(self):
        """Shutdown monitoring system."""
        self.resource_monitor.stop_monitoring()

    async def get_system_status(self) -> dict[str, Any]:
        """Get current system status overview."""
        health_checks = await self.diagnostic_tool.run_health_checks()

        # Overall system health
        health_statuses = [check.status for check in health_checks]
        if "unhealthy" in health_statuses:
            overall_status = "unhealthy"
        elif "degraded" in health_statuses:
            overall_status = "degraded"
        else:
            overall_status = "healthy"

        return {
            "overall_status": overall_status,
            "timestamp": datetime.now().isoformat(),
            "uptime_seconds": time.time() - self._start_time,
            "health_checks": [asdict(check) for check in health_checks],
            "resource_usage": asdict(self.resource_monitor.get_current_resources()),
            "active_operations": len(self.operation_logger.active_operations),
            "recent_operation_stats": self.operation_logger.get_operation_stats(window_hours=1),
        }

    def get_performance_metrics(self, metric_name: str = None, hours: int = 1) -> dict[str, Any]:
        """Get performance metrics."""
        if metric_name:
            since = datetime.now() - timedelta(hours=hours)
            metrics = self.metrics_collector.get_metrics(metric_name, since)
            return {
                "metric_name": metric_name,
                "data_points": len(metrics),
                "metrics": [asdict(m) for m in metrics],
                "summary": self.metrics_collector.get_metric_summary(metric_name, hours * 60),
            }
        else:
            # Return summary for all metrics
            metric_names = self.metrics_collector.get_all_metric_names()
            summaries = {}
            for name in metric_names:
                summaries[name] = self.metrics_collector.get_metric_summary(name, hours * 60)
            return {"available_metrics": metric_names, "summaries": summaries}

    def get_operation_logs(self, **filters) -> dict[str, Any]:
        """Get operation execution logs."""
        logs = self.operation_logger.get_operation_logs(**filters)
        return {
            "logs": [asdict(log) for log in logs],
            "total_count": len(logs),
            "stats": self.operation_logger.get_operation_stats(),
        }

    def get_resource_history(self, hours: int = 1) -> list[dict[str, Any]]:
        """Get system resource usage history."""
        history = self.resource_monitor.get_resource_history(hours)
        return [asdict(resource) for resource in history]

    def generate_full_report(self) -> dict[str, Any]:
        """Generate comprehensive system report."""
        return self.diagnostic_tool.generate_system_report(
            self.metrics_collector, self.operation_logger, self.resource_monitor
        )

    # Operation tracking methods for integration
    def start_operation_tracking(self, operation_id: str, tool_name: str, parameters: dict[str, Any]):
        """Start tracking an operation."""
        self.operation_logger.start_operation(operation_id, tool_name, parameters)
        self.metrics_collector.record_metric("operations_started", 1, "count")

    def complete_operation_tracking(
        self, operation_id: str, status: str = "completed", error_message: str = None, result_size_bytes: int = None
    ):
        """Complete operation tracking."""
        self.operation_logger.complete_operation(operation_id, status, error_message, result_size_bytes)
        self.metrics_collector.record_metric(f"operations_{status}", 1, "count")

    def record_performance_metric(self, name: str, value: float, unit: str = "", tags: dict[str, str] = None):
        """Record a performance metric."""
        self.metrics_collector.record_metric(name, value, unit, tags)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.shutdown()
