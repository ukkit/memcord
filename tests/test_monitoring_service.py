"""Tests for the monitoring service module.

Tests the MonitoringService business logic extracted from the server handlers
during the optimization (Phase 2).
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from memcord.services.monitoring_service import (
    DiagnosticsReport,
    HealthCheck,
    LogEntry,
    LogsReport,
    MetricsReport,
    MetricSummary,
    MonitoringService,
    PerformanceIssue,
    StatusReport,
)


class MockHealthCheckResult:
    """Mock health check result for testing."""

    def __init__(
        self,
        service: str = "storage",
        status: str = "healthy",
        response_time: float = 10.0,
        error_message: str = None,
        details: dict = None,
    ):
        self.service = service
        self.status = status
        self.response_time = response_time
        self.error_message = error_message
        self.details = details


class TestHealthCheck:
    """Tests for HealthCheck dataclass."""

    def test_healthy_check(self):
        """Test creating a healthy check."""
        check = HealthCheck(
            service="storage",
            status="healthy",
            response_time=10.5,
        )

        assert check.service == "storage"
        assert check.status == "healthy"
        assert check.error_message is None

    def test_unhealthy_check(self):
        """Test creating an unhealthy check."""
        check = HealthCheck(
            service="database",
            status="unhealthy",
            response_time=5000.0,
            error_message="Connection timeout",
        )

        assert check.status == "unhealthy"
        assert check.error_message == "Connection timeout"


class TestStatusReport:
    """Tests for StatusReport dataclass."""

    def test_successful_status_report(self):
        """Test creating a successful status report."""
        report = StatusReport(
            success=True,
            overall_status="healthy",
            uptime_seconds=3600.0,
            uptime_hours=1.0,
            active_operations=5,
            total_operations=100,
            success_rate=95.0,
            avg_duration_ms=50.0,
            healthy_checks=3,
            total_checks=3,
            cpu_percent=25.0,
            memory_percent=45.0,
            disk_usage_percent=60.0,
        )

        assert report.success is True
        assert report.overall_status == "healthy"
        assert report.uptime_hours == 1.0

    def test_failed_status_report(self):
        """Test creating a failed status report."""
        report = StatusReport(
            success=False,
            error="Unable to retrieve status",
        )

        assert report.success is False
        assert report.error is not None


class TestMetricSummary:
    """Tests for MetricSummary dataclass."""

    def test_metric_summary_creation(self):
        """Test creating a metric summary."""
        summary = MetricSummary(
            name="response_time",
            count=100,
            avg=45.5,
            min=10.0,
            max=200.0,
            latest=50.0,
            unit="ms",
        )

        assert summary.name == "response_time"
        assert summary.avg == 45.5
        assert summary.unit == "ms"


class TestMetricsReport:
    """Tests for MetricsReport dataclass."""

    def test_single_metric_report(self):
        """Test report for single metric."""
        report = MetricsReport(
            success=True,
            metric_name="cpu_usage",
            hours=1,
            data_points=60,
            summary=MetricSummary(
                name="cpu_usage",
                count=60,
                avg=35.0,
                min=10.0,
                max=80.0,
                latest=40.0,
                unit="percent",
            ),
        )

        assert report.metric_name == "cpu_usage"
        assert report.summary is not None

    def test_all_metrics_report(self):
        """Test report for all metrics."""
        report = MetricsReport(
            success=True,
            hours=1,
            available_metrics=["cpu", "memory", "disk"],
            summaries={
                "cpu": MetricSummary(name="cpu", count=10, avg=30.0, min=10.0, max=50.0, latest=35.0),
                "memory": MetricSummary(name="memory", count=10, avg=50.0, min=40.0, max=60.0, latest=55.0),
            },
        )

        assert len(report.available_metrics) == 3
        assert len(report.summaries) == 2


class TestLogEntry:
    """Tests for LogEntry dataclass."""

    def test_successful_log_entry(self):
        """Test creating a successful log entry."""
        entry = LogEntry(
            tool_name="memcord_save",
            status="completed",
            start_time=datetime.now(),
            duration_ms=45.5,
        )

        assert entry.tool_name == "memcord_save"
        assert entry.status == "completed"
        assert entry.error_message is None

    def test_failed_log_entry(self):
        """Test creating a failed log entry."""
        entry = LogEntry(
            tool_name="memcord_read",
            status="failed",
            start_time=datetime.now(),
            duration_ms=100.0,
            error_message="Slot not found",
        )

        assert entry.status == "failed"
        assert entry.error_message == "Slot not found"


class TestLogsReport:
    """Tests for LogsReport dataclass."""

    def test_logs_report_with_entries(self):
        """Test logs report with entries."""
        report = LogsReport(
            success=True,
            hours=1,
            total_count=100,
            shown_count=20,
            logs=[
                LogEntry(tool_name="tool1", status="completed", start_time=datetime.now()),
                LogEntry(tool_name="tool2", status="failed", start_time=datetime.now(), error_message="Error"),
            ],
            total_operations=100,
            success_rate=95.0,
            failed_operations=5,
            avg_duration_ms=50.0,
        )

        assert report.success is True
        assert len(report.logs) == 2
        assert report.success_rate == 95.0


class TestPerformanceIssue:
    """Tests for PerformanceIssue dataclass."""

    def test_critical_issue(self):
        """Test creating a critical issue."""
        issue = PerformanceIssue(
            severity="critical",
            description="Memory usage above 90%",
        )

        assert issue.severity == "critical"
        assert "Memory" in issue.description


class TestDiagnosticsReport:
    """Tests for DiagnosticsReport dataclass."""

    def test_health_diagnostics(self):
        """Test health diagnostics report."""
        report = DiagnosticsReport(
            success=True,
            check_type="health",
            timestamp=datetime.now().isoformat(),
            health_checks=[
                HealthCheck(service="storage", status="healthy", response_time=10.0),
            ],
        )

        assert report.success is True
        assert report.check_type == "health"
        assert len(report.health_checks) == 1

    def test_performance_diagnostics(self):
        """Test performance diagnostics report."""
        report = DiagnosticsReport(
            success=True,
            check_type="performance",
            timestamp=datetime.now().isoformat(),
            issues=[
                PerformanceIssue(severity="warning", description="High CPU usage"),
            ],
            recommendations=["Consider upgrading hardware"],
        )

        assert report.check_type == "performance"
        assert len(report.issues) == 1
        assert len(report.recommendations) == 1


class TestMonitoringServiceStatus:
    """Tests for MonitoringService get_status method."""

    @pytest.fixture
    def mock_status_monitor(self):
        """Create mock status monitoring system."""
        monitor = MagicMock()
        monitor.get_system_status = AsyncMock()
        monitor.get_performance_metrics = MagicMock()
        monitor.get_operation_logs = MagicMock()
        monitor.diagnostic_tool = MagicMock()
        monitor.metrics_collector = MagicMock()
        monitor.operation_logger = MagicMock()
        monitor.generate_full_report = MagicMock()
        return monitor

    @pytest.fixture
    def monitoring_service(self, mock_status_monitor):
        """Create MonitoringService instance."""
        return MonitoringService(mock_status_monitor)

    @pytest.mark.asyncio
    async def test_get_status_success(self, monitoring_service, mock_status_monitor):
        """Test successful status retrieval."""
        mock_status_monitor.get_system_status.return_value = {
            "overall_status": "healthy",
            "uptime_seconds": 3600.0,
            "active_operations": 5,
            "health_checks": [
                {"service": "storage", "status": "healthy", "response_time": 10.0},
            ],
            "recent_operation_stats": {
                "total_operations": 100,
                "success_rate": 95.0,
                "avg_duration_ms": 50.0,
            },
            "resource_usage": {
                "cpu_percent": 25.0,
                "memory_percent": 45.0,
                "disk_usage_percent": 60.0,
            },
        }

        report = await monitoring_service.get_status()

        assert report.success is True
        assert report.overall_status == "healthy"
        assert report.uptime_hours == 1.0
        assert report.healthy_checks == 1

    @pytest.mark.asyncio
    async def test_get_status_with_details(self, monitoring_service, mock_status_monitor):
        """Test status retrieval with details included."""
        mock_status_monitor.get_system_status.return_value = {
            "overall_status": "healthy",
            "uptime_seconds": 3600.0,
            "active_operations": 0,
            "health_checks": [
                {"service": "storage", "status": "healthy", "response_time": 10.0},
                {"service": "memory", "status": "healthy", "response_time": 5.0},
            ],
            "recent_operation_stats": {},
            "resource_usage": {},
        }

        report = await monitoring_service.get_status(include_details=True)

        assert len(report.health_checks) == 2

    @pytest.mark.asyncio
    async def test_get_status_without_details(self, monitoring_service, mock_status_monitor):
        """Test status retrieval without details."""
        mock_status_monitor.get_system_status.return_value = {
            "overall_status": "healthy",
            "uptime_seconds": 3600.0,
            "active_operations": 0,
            "health_checks": [
                {"service": "storage", "status": "healthy", "response_time": 10.0},
            ],
            "recent_operation_stats": {},
            "resource_usage": {},
        }

        report = await monitoring_service.get_status(include_details=False)

        assert len(report.health_checks) == 0  # Not included when details=False

    @pytest.mark.asyncio
    async def test_get_status_error(self, monitoring_service, mock_status_monitor):
        """Test status retrieval error handling."""
        mock_status_monitor.get_system_status.side_effect = RuntimeError("Connection failed")

        report = await monitoring_service.get_status()

        assert report.success is False
        assert "Connection failed" in report.error


class TestMonitoringServiceMetrics:
    """Tests for MonitoringService get_metrics method."""

    @pytest.fixture
    def mock_status_monitor(self):
        """Create mock status monitoring system."""
        monitor = MagicMock()
        monitor.get_performance_metrics = MagicMock()
        return monitor

    @pytest.fixture
    def monitoring_service(self, mock_status_monitor):
        """Create MonitoringService instance."""
        return MonitoringService(mock_status_monitor)

    def test_get_specific_metric(self, monitoring_service, mock_status_monitor):
        """Test getting a specific metric."""
        mock_status_monitor.get_performance_metrics.return_value = {
            "data_points": 60,
            "summary": {
                "count": 60,
                "avg": 35.0,
                "min": 10.0,
                "max": 80.0,
                "latest": 40.0,
                "unit": "percent",
            },
        }

        report = monitoring_service.get_metrics(metric_name="cpu_usage", hours=1)

        assert report.success is True
        assert report.metric_name == "cpu_usage"
        assert report.summary is not None
        assert report.summary.avg == 35.0

    def test_get_all_metrics(self, monitoring_service, mock_status_monitor):
        """Test getting all metrics."""
        mock_status_monitor.get_performance_metrics.return_value = {
            "available_metrics": ["cpu", "memory", "disk"],
            "summaries": {
                "cpu": {"count": 10, "avg": 30.0, "min": 10.0, "max": 50.0, "latest": 35.0, "unit": "percent"},
                "memory": {"count": 10, "avg": 50.0, "min": 40.0, "max": 60.0, "latest": 55.0, "unit": "percent"},
            },
        }

        report = monitoring_service.get_metrics(hours=1)

        assert report.success is True
        assert report.metric_name is None
        assert len(report.available_metrics) == 3
        assert len(report.summaries) == 2

    def test_get_metrics_empty_data(self, monitoring_service, mock_status_monitor):
        """Test getting metrics with no data."""
        mock_status_monitor.get_performance_metrics.return_value = {
            "data_points": 0,
            "summary": {"count": 0},
        }

        report = monitoring_service.get_metrics(metric_name="cpu", hours=1)

        assert report.success is True
        assert report.summary is None  # No summary when count is 0

    def test_get_metrics_error(self, monitoring_service, mock_status_monitor):
        """Test metrics retrieval error handling."""
        mock_status_monitor.get_performance_metrics.side_effect = RuntimeError("Error")

        report = monitoring_service.get_metrics()

        assert report.success is False
        assert "Error" in report.error


class TestMonitoringServiceLogs:
    """Tests for MonitoringService get_logs method."""

    @pytest.fixture
    def mock_status_monitor(self):
        """Create mock status monitoring system."""
        monitor = MagicMock()
        monitor.get_operation_logs = MagicMock()
        return monitor

    @pytest.fixture
    def monitoring_service(self, mock_status_monitor):
        """Create MonitoringService instance."""
        return MonitoringService(mock_status_monitor)

    def test_get_logs_success(self, monitoring_service, mock_status_monitor):
        """Test successful log retrieval."""
        mock_status_monitor.get_operation_logs.return_value = {
            "logs": [
                {
                    "tool_name": "memcord_save",
                    "status": "completed",
                    "start_time": datetime.now().isoformat(),
                    "duration_ms": 45.0,
                },
                {
                    "tool_name": "memcord_read",
                    "status": "completed",
                    "start_time": datetime.now().isoformat(),
                    "duration_ms": 20.0,
                },
            ],
            "total_count": 2,
            "stats": {
                "total_operations": 100,
                "success_rate": 95.0,
                "failed_operations": 5,
                "avg_duration_ms": 50.0,
            },
        }

        report = monitoring_service.get_logs(hours=1)

        assert report.success is True
        assert len(report.logs) == 2
        assert report.success_rate == 95.0

    def test_get_logs_with_tool_filter(self, monitoring_service, mock_status_monitor):
        """Test log retrieval with tool filter."""
        mock_status_monitor.get_operation_logs.return_value = {
            "logs": [
                {"tool_name": "memcord_save", "status": "completed", "start_time": datetime.now().isoformat()},
            ],
            "total_count": 1,
            "stats": {},
        }

        report = monitoring_service.get_logs(tool_name="memcord_save", hours=1)

        assert report.success is True
        assert report.tool_filter == "memcord_save"

    def test_get_logs_with_status_filter(self, monitoring_service, mock_status_monitor):
        """Test log retrieval with status filter."""
        mock_status_monitor.get_operation_logs.return_value = {
            "logs": [
                {
                    "tool_name": "memcord_read",
                    "status": "failed",
                    "start_time": datetime.now().isoformat(),
                    "error_message": "Not found",
                },
            ],
            "total_count": 1,
            "stats": {},
        }

        report = monitoring_service.get_logs(status="failed", hours=1)

        assert report.success is True
        assert report.status_filter == "failed"
        assert report.logs[0].error_message == "Not found"

    def test_get_logs_limits_display(self, monitoring_service, mock_status_monitor):
        """Test that logs are limited to 20 for display."""
        # Return more than 20 logs
        mock_status_monitor.get_operation_logs.return_value = {
            "logs": [
                {"tool_name": f"tool_{i}", "status": "completed", "start_time": datetime.now().isoformat()}
                for i in range(50)
            ],
            "total_count": 50,
            "stats": {},
        }

        report = monitoring_service.get_logs(hours=1, limit=50)

        assert report.total_count == 50
        assert report.shown_count == 20  # Limited to 20

    def test_get_logs_error(self, monitoring_service, mock_status_monitor):
        """Test log retrieval error handling."""
        mock_status_monitor.get_operation_logs.side_effect = RuntimeError("Error")

        report = monitoring_service.get_logs()

        assert report.success is False
        assert "Error" in report.error


class TestMonitoringServiceDiagnostics:
    """Tests for MonitoringService run_diagnostics method."""

    @pytest.fixture
    def mock_status_monitor(self):
        """Create mock status monitoring system."""
        monitor = MagicMock()
        monitor.diagnostic_tool = MagicMock()
        monitor.diagnostic_tool.run_health_checks = AsyncMock()
        monitor.diagnostic_tool.analyze_performance_issues = MagicMock()
        monitor.metrics_collector = MagicMock()
        monitor.operation_logger = MagicMock()
        monitor.generate_full_report = AsyncMock()
        return monitor

    @pytest.fixture
    def monitoring_service(self, mock_status_monitor):
        """Create MonitoringService instance."""
        return MonitoringService(mock_status_monitor)

    @pytest.mark.asyncio
    async def test_health_diagnostics(self, monitoring_service, mock_status_monitor):
        """Test health diagnostics."""
        mock_status_monitor.diagnostic_tool.run_health_checks.return_value = [
            MockHealthCheckResult(service="storage", status="healthy", response_time=10.0),
            MockHealthCheckResult(service="memory", status="healthy", response_time=5.0),
        ]

        report = await monitoring_service.run_diagnostics(check_type="health")

        assert report.success is True
        assert report.check_type == "health"
        assert len(report.health_checks) == 2

    @pytest.mark.asyncio
    async def test_performance_diagnostics(self, monitoring_service, mock_status_monitor):
        """Test performance diagnostics."""
        mock_status_monitor.diagnostic_tool.analyze_performance_issues.return_value = {
            "timestamp": datetime.now().isoformat(),
            "issues": [
                {"severity": "warning", "description": "High memory usage"},
            ],
            "recommendations": ["Consider adding more RAM"],
        }

        report = await monitoring_service.run_diagnostics(check_type="performance")

        assert report.success is True
        assert report.check_type == "performance"
        assert len(report.issues) == 1
        assert len(report.recommendations) == 1

    @pytest.mark.asyncio
    async def test_full_report_diagnostics(self, monitoring_service, mock_status_monitor):
        """Test full report diagnostics."""
        mock_status_monitor.generate_full_report.return_value = {
            "timestamp": datetime.now().isoformat(),
            "status": "healthy",
            "metrics": {},
            "logs": [],
        }

        report = await monitoring_service.run_diagnostics(check_type="full_report")

        assert report.success is True
        assert report.check_type == "full_report"
        assert "status" in report.full_report_data

    @pytest.mark.asyncio
    async def test_unknown_check_type(self, monitoring_service):
        """Test unknown check type returns error."""
        report = await monitoring_service.run_diagnostics(check_type="invalid")

        assert report.success is False
        assert "Unknown check type" in report.error

    @pytest.mark.asyncio
    async def test_diagnostics_error_handling(self, monitoring_service, mock_status_monitor):
        """Test diagnostics error handling."""
        mock_status_monitor.diagnostic_tool.run_health_checks.side_effect = RuntimeError("Check failed")

        report = await monitoring_service.run_diagnostics(check_type="health")

        assert report.success is False
        assert "Check failed" in report.error
