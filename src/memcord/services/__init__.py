"""Service modules for memcord business logic.

These modules contain extracted business logic from the server handlers,
providing cleaner separation of concerns and improved testability.
"""

from .archive_service import (
    ArchiveCandidate,
    ArchiveCandidatesResult,
    ArchiveInfo,
    ArchiveListResult,
    ArchiveResult,
    ArchiveService,
    ArchiveStats,
    RestoreResult,
)
from .compression_service import (
    BulkCompressionResult,
    CompressionAnalysis,
    CompressionResult,
    CompressionService,
    CompressionStats,
    DecompressionResult,
)
from .import_service import ImportResult, ImportService
from .merge_service import MergeExecuteResult, MergePreviewResult, MergeService
from .monitoring_service import (
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
from .select_entry_service import SelectedEntry, SelectEntryService, SelectionRequest

__all__ = [
    # Archive
    "ArchiveService",
    "ArchiveResult",
    "RestoreResult",
    "ArchiveInfo",
    "ArchiveListResult",
    "ArchiveStats",
    "ArchiveCandidate",
    "ArchiveCandidatesResult",
    # Compression
    "CompressionService",
    "CompressionResult",
    "CompressionStats",
    "BulkCompressionResult",
    "DecompressionResult",
    "CompressionAnalysis",
    # Import
    "ImportService",
    "ImportResult",
    # Merge
    "MergeService",
    "MergePreviewResult",
    "MergeExecuteResult",
    # Monitoring
    "MonitoringService",
    "StatusReport",
    "MetricsReport",
    "LogsReport",
    "DiagnosticsReport",
    "HealthCheck",
    "MetricSummary",
    "LogEntry",
    "PerformanceIssue",
    # Select Entry
    "SelectEntryService",
    "SelectedEntry",
    "SelectionRequest",
]
