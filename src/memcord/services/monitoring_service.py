"""Monitoring service for system health and performance.

Extracts business logic from the monitoring handlers for better testability
and separation of concerns.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ..status_monitoring import StatusMonitoringSystem


@dataclass
class HealthCheck:
    """Result of a health check."""

    service: str
    status: str  # "healthy", "degraded", "unhealthy", "unknown"
    response_time: float
    error_message: str | None = None
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class StatusReport:
    """System status report."""

    success: bool
    overall_status: str = ""
    uptime_seconds: float = 0.0
    uptime_hours: float = 0.0
    active_operations: int = 0
    total_operations: int = 0
    success_rate: float = 0.0
    avg_duration_ms: float = 0.0
    healthy_checks: int = 0
    total_checks: int = 0
    health_checks: list[HealthCheck] = field(default_factory=list)
    cpu_percent: float = 0.0
    memory_percent: float = 0.0
    disk_usage_percent: float = 0.0
    error: str | None = None


@dataclass
class MetricSummary:
    """Summary of a single metric."""

    name: str
    count: int = 0
    avg: float = 0.0
    min: float = 0.0
    max: float = 0.0
    latest: float = 0.0
    unit: str = ""


@dataclass
class MetricsReport:
    """Performance metrics report."""

    success: bool
    metric_name: str | None = None
    hours: int = 1
    data_points: int = 0
    summary: MetricSummary | None = None
    available_metrics: list[str] = field(default_factory=list)
    summaries: dict[str, MetricSummary] = field(default_factory=dict)
    error: str | None = None


@dataclass
class LogEntry:
    """A single operation log entry."""

    tool_name: str
    status: str  # "completed", "failed", "started", "timeout"
    start_time: datetime
    duration_ms: float | None = None
    error_message: str | None = None


@dataclass
class LogsReport:
    """Operation logs report."""

    success: bool
    hours: int = 1
    tool_filter: str | None = None
    status_filter: str | None = None
    total_count: int = 0
    shown_count: int = 0
    logs: list[LogEntry] = field(default_factory=list)
    total_operations: int = 0
    success_rate: float = 0.0
    failed_operations: int = 0
    avg_duration_ms: float = 0.0
    error: str | None = None


@dataclass
class PerformanceIssue:
    """A detected performance issue."""

    severity: str  # "critical", "warning", "info"
    description: str


@dataclass
class DiagnosticsReport:
    """System diagnostics report."""

    success: bool
    check_type: str = "health"  # "health", "performance", "full_report"
    timestamp: str = ""
    health_checks: list[HealthCheck] = field(default_factory=list)
    issues: list[PerformanceIssue] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    full_report_data: dict[str, Any] = field(default_factory=dict)
    error: str | None = None


class MonitoringService:
    """Service for system monitoring operations."""

    def __init__(self, status_monitor: "StatusMonitoringSystem"):
        """Initialize monitoring service.

        Args:
            status_monitor: StatusMonitoringSystem instance
        """
        self.status_monitor = status_monitor

    async def get_status(self, include_details: bool = False) -> StatusReport:
        """Get system status.

        Args:
            include_details: Include detailed health check results

        Returns:
            StatusReport with system status
        """
        try:
            status = await self.status_monitor.get_system_status()

            # Parse health checks
            health_checks = []
            for check in status.get("health_checks", []):
                health_checks.append(
                    HealthCheck(
                        service=check.get("service", ""),
                        status=check.get("status", "unknown"),
                        response_time=check.get("response_time", 0.0),
                        error_message=check.get("error_message"),
                        details=check.get("details", {}),
                    )
                )

            # Parse operation stats
            op_stats = status.get("recent_operation_stats", {})

            # Parse resource usage
            resources = status.get("resource_usage", {})

            healthy = sum(1 for c in health_checks if c.status == "healthy")

            return StatusReport(
                success=True,
                overall_status=status.get("overall_status", "unknown"),
                uptime_seconds=status.get("uptime_seconds", 0.0),
                uptime_hours=status.get("uptime_seconds", 0.0) / 3600,
                active_operations=status.get("active_operations", 0),
                total_operations=op_stats.get("total_operations", 0),
                success_rate=op_stats.get("success_rate", 0.0),
                avg_duration_ms=op_stats.get("avg_duration_ms", 0.0),
                healthy_checks=healthy,
                total_checks=len(health_checks),
                health_checks=health_checks if include_details else [],
                cpu_percent=resources.get("cpu_percent", 0.0),
                memory_percent=resources.get("memory_percent", 0.0),
                disk_usage_percent=resources.get("disk_usage_percent", 0.0),
            )

        except Exception as e:
            return StatusReport(success=False, error=str(e))

    def get_metrics(self, metric_name: str | None = None, hours: int = 1) -> MetricsReport:
        """Get performance metrics.

        Args:
            metric_name: Optional specific metric name
            hours: Time window in hours

        Returns:
            MetricsReport with metrics data
        """
        try:
            if metric_name:
                # Get specific metric
                metrics_data = self.status_monitor.get_performance_metrics(metric_name, hours)
                summary_data = metrics_data.get("summary", {})

                summary = None
                if summary_data.get("count", 0) > 0:
                    summary = MetricSummary(
                        name=metric_name,
                        count=summary_data.get("count", 0),
                        avg=summary_data.get("avg", 0.0),
                        min=summary_data.get("min", 0.0),
                        max=summary_data.get("max", 0.0),
                        latest=summary_data.get("latest", 0.0),
                        unit=summary_data.get("unit", ""),
                    )

                return MetricsReport(
                    success=True,
                    metric_name=metric_name,
                    hours=hours,
                    data_points=metrics_data.get("data_points", 0),
                    summary=summary,
                )

            else:
                # Get all metrics summary
                metrics_data = self.status_monitor.get_performance_metrics(hours=hours)
                available_metrics = metrics_data.get("available_metrics", [])
                summaries_data = metrics_data.get("summaries", {})

                summaries = {}
                for name, summary_data in summaries_data.items():
                    if summary_data.get("count", 0) > 0:
                        summaries[name] = MetricSummary(
                            name=name,
                            count=summary_data.get("count", 0),
                            avg=summary_data.get("avg", 0.0),
                            min=summary_data.get("min", 0.0),
                            max=summary_data.get("max", 0.0),
                            latest=summary_data.get("latest", 0.0),
                            unit=summary_data.get("unit", ""),
                        )

                return MetricsReport(
                    success=True,
                    hours=hours,
                    available_metrics=available_metrics,
                    summaries=summaries,
                )

        except Exception as e:
            return MetricsReport(success=False, error=str(e))

    def get_logs(
        self,
        tool_name: str | None = None,
        status: str | None = None,
        hours: int = 1,
        limit: int = 100,
    ) -> LogsReport:
        """Get operation logs.

        Args:
            tool_name: Optional filter by tool name
            status: Optional filter by status
            hours: Time window in hours
            limit: Maximum number of logs

        Returns:
            LogsReport with log entries
        """
        try:
            since = datetime.now() - timedelta(hours=hours)

            filters = {"since": since, "limit": limit}
            if tool_name:
                filters["tool_name"] = tool_name
            if status:
                filters["status"] = status

            logs_data = self.status_monitor.get_operation_logs(**filters)
            logs_raw = logs_data.get("logs", [])
            stats = logs_data.get("stats", {})

            # Parse logs
            logs = []
            for log in logs_raw[:20]:  # Limit to 20 for display
                start_time = log.get("start_time")
                if isinstance(start_time, str):
                    start_time = datetime.fromisoformat(start_time.replace("Z", "+00:00"))

                logs.append(
                    LogEntry(
                        tool_name=log.get("tool_name", ""),
                        status=log.get("status", ""),
                        start_time=start_time,
                        duration_ms=log.get("duration_ms"),
                        error_message=log.get("error_message"),
                    )
                )

            return LogsReport(
                success=True,
                hours=hours,
                tool_filter=tool_name,
                status_filter=status,
                total_count=logs_data.get("total_count", 0),
                shown_count=len(logs),
                logs=logs,
                total_operations=stats.get("total_operations", 0),
                success_rate=stats.get("success_rate", 0.0),
                failed_operations=stats.get("failed_operations", 0),
                avg_duration_ms=stats.get("avg_duration_ms", 0.0),
            )

        except Exception as e:
            return LogsReport(success=False, error=str(e))

    async def run_diagnostics(self, check_type: str = "health") -> DiagnosticsReport:
        """Run system diagnostics.

        Args:
            check_type: Type of check ("health", "performance", "full_report")

        Returns:
            DiagnosticsReport with diagnostics results
        """
        try:
            timestamp = datetime.now().isoformat()

            if check_type == "health":
                # Run health checks
                health_checks_raw = await self.status_monitor.diagnostic_tool.run_health_checks()

                health_checks = []
                for check in health_checks_raw:
                    health_checks.append(
                        HealthCheck(
                            service=check.service,
                            status=check.status,
                            response_time=check.response_time,
                            error_message=check.error_message,
                            details=check.details or {},
                        )
                    )

                return DiagnosticsReport(
                    success=True,
                    check_type=check_type,
                    timestamp=timestamp,
                    health_checks=health_checks,
                )

            elif check_type == "performance":
                # Performance analysis
                analysis = self.status_monitor.diagnostic_tool.analyze_performance_issues(
                    self.status_monitor.metrics_collector,
                    self.status_monitor.operation_logger,
                )

                issues = []
                for issue in analysis.get("issues", []):
                    issues.append(
                        PerformanceIssue(
                            severity=issue.get("severity", "info"),
                            description=issue.get("description", ""),
                        )
                    )

                return DiagnosticsReport(
                    success=True,
                    check_type=check_type,
                    timestamp=analysis.get("timestamp", timestamp),
                    issues=issues,
                    recommendations=analysis.get("recommendations", []),
                )

            elif check_type == "full_report":
                # Generate comprehensive report
                report = await self.status_monitor.generate_full_report()

                return DiagnosticsReport(
                    success=True,
                    check_type=check_type,
                    timestamp=report.get("timestamp", timestamp),
                    full_report_data=report,
                )

            else:
                return DiagnosticsReport(
                    success=False,
                    check_type=check_type,
                    error=f"Unknown check type: {check_type}",
                )

        except Exception as e:
            return DiagnosticsReport(success=False, check_type=check_type, error=str(e))
