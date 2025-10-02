"""Enhanced error handling system for memcord."""

import functools
from enum import Enum
from typing import Any


class ErrorCode(Enum):
    """Standard error codes for memcord operations."""

    # Input Validation Errors (1000-1099)
    INVALID_INPUT = 1000
    INVALID_SLOT_NAME = 1001
    INVALID_CONTENT_SIZE = 1002
    INVALID_PATH = 1003
    INVALID_URL = 1004
    INVALID_COMPRESSION_RATIO = 1005
    INVALID_SEARCH_QUERY = 1006

    # Authentication & Authorization Errors (1100-1199)
    AUTHENTICATION_FAILED = 1100
    INSUFFICIENT_PERMISSIONS = 1101
    SESSION_EXPIRED = 1102
    INVALID_API_KEY = 1103

    # Rate Limiting Errors (1200-1299)
    RATE_LIMIT_EXCEEDED = 1200
    GLOBAL_RATE_LIMIT = 1201
    OPERATION_RATE_LIMIT = 1202

    # Storage Errors (1300-1399)
    STORAGE_ERROR = 1300
    SLOT_NOT_FOUND = 1301
    SLOT_ALREADY_EXISTS = 1302
    STORAGE_QUOTA_EXCEEDED = 1303
    STORAGE_CORRUPTED = 1304

    # Operation Errors (1400-1499)
    OPERATION_TIMEOUT = 1400
    OPERATION_CANCELLED = 1401
    OPERATION_FAILED = 1402
    UNSUPPORTED_OPERATION = 1403

    # Import/Export Errors (1500-1599)
    IMPORT_FAILED = 1500
    EXPORT_FAILED = 1501
    UNSUPPORTED_FORMAT = 1502
    FILE_NOT_FOUND = 1503
    NETWORK_ERROR = 1504

    # Search Errors (1600-1699)
    SEARCH_FAILED = 1600
    QUERY_TOO_COMPLEX = 1601
    INDEX_CORRUPTED = 1602

    # System Errors (1700-1799)
    INTERNAL_ERROR = 1700
    CONFIGURATION_ERROR = 1701
    DEPENDENCY_ERROR = 1702
    RESOURCE_EXHAUSTED = 1703


class ErrorSeverity(Enum):
    """Error severity levels."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class MemcordError(Exception):
    """Base exception class for memcord with enhanced error information."""

    def __init__(
        self,
        message: str,
        error_code: ErrorCode = ErrorCode.INTERNAL_ERROR,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        context: dict[str, Any] | None = None,
        recovery_suggestions: list[str] | None = None,
        documentation_link: str | None = None,
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.severity = severity
        self.context = context or {}
        self.recovery_suggestions = recovery_suggestions or []
        self.documentation_link = documentation_link
        self.timestamp = None

        # Auto-generate timestamp
        from datetime import datetime

        self.timestamp = datetime.now()

    def to_dict(self) -> dict[str, Any]:
        """Convert error to dictionary format."""
        return {
            "error_code": self.error_code.value,
            "error_name": self.error_code.name,
            "message": self.message,
            "severity": self.severity.value,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "context": self.context,
            "recovery_suggestions": self.recovery_suggestions,
            "documentation_link": self.documentation_link,
        }

    def get_user_message(self) -> str:
        """Get formatted user-friendly error message."""
        msg = f"❌ {self.message}"

        if self.recovery_suggestions:
            msg += "\n\n💡 **How to fix this:**"
            for i, suggestion in enumerate(self.recovery_suggestions, 1):
                msg += f"\n{i}. {suggestion}"

        if self.documentation_link:
            msg += f"\n\n📖 **Learn more:** {self.documentation_link}"

        if self.context:
            relevant_context = {
                k: v for k, v in self.context.items() if k in ["operation", "slot_name", "file_path", "query"]
            }
            if relevant_context:
                msg += f"\n\n🔍 **Context:** {', '.join(f'{k}={v}' for k, v in relevant_context.items())}"

        return msg


class ValidationError(MemcordError):
    """Input validation errors."""

    def __init__(self, message: str, field: str = None, value: Any = None, **kwargs):
        context = kwargs.get("context", {})
        if field:
            context["field"] = field
        if value is not None:
            context["invalid_value"] = str(value)[:100]  # Truncate for safety

        kwargs["context"] = context
        kwargs.setdefault("error_code", ErrorCode.INVALID_INPUT)
        kwargs.setdefault("severity", ErrorSeverity.LOW)

        super().__init__(message, **kwargs)


class RateLimitError(MemcordError):
    """Rate limiting errors."""

    def __init__(self, message: str, operation: str = None, limit: int = None, **kwargs):
        context = kwargs.get("context", {})
        if operation:
            context["operation"] = operation
        if limit:
            context["rate_limit"] = limit

        kwargs["context"] = context
        kwargs.setdefault("error_code", ErrorCode.RATE_LIMIT_EXCEEDED)
        kwargs.setdefault("severity", ErrorSeverity.MEDIUM)
        kwargs.setdefault(
            "recovery_suggestions",
            [
                "Wait a minute before making more requests",
                "Reduce the frequency of operations",
                "Consider using batch operations where available",
            ],
        )

        super().__init__(message, **kwargs)


class StorageError(MemcordError):
    """Storage-related errors."""

    def __init__(self, message: str, slot_name: str = None, **kwargs):
        context = kwargs.get("context", {})
        if slot_name:
            context["slot_name"] = slot_name

        kwargs["context"] = context
        kwargs.setdefault("error_code", ErrorCode.STORAGE_ERROR)
        kwargs.setdefault("severity", ErrorSeverity.HIGH)

        super().__init__(message, **kwargs)


class OperationTimeoutError(MemcordError):
    """Operation timeout errors."""

    def __init__(self, message: str, operation: str = None, timeout_seconds: int = None, **kwargs):
        context = kwargs.get("context", {})
        if operation:
            context["operation"] = operation
        if timeout_seconds:
            context["timeout_seconds"] = timeout_seconds

        kwargs["context"] = context
        kwargs.setdefault("error_code", ErrorCode.OPERATION_TIMEOUT)
        kwargs.setdefault("severity", ErrorSeverity.MEDIUM)
        kwargs.setdefault(
            "recovery_suggestions",
            [
                "Try breaking large operations into smaller chunks",
                "Check system resources and network connectivity",
                "Consider using async operations for long-running tasks",
            ],
        )

        super().__init__(message, **kwargs)


class ImportError(MemcordError):
    """Import operation errors."""

    def __init__(self, message: str, source: str = None, **kwargs):
        context = kwargs.get("context", {})
        if source:
            context["source"] = source

        kwargs["context"] = context
        kwargs.setdefault("error_code", ErrorCode.IMPORT_FAILED)
        kwargs.setdefault("severity", ErrorSeverity.MEDIUM)
        kwargs.setdefault(
            "recovery_suggestions",
            [
                "Verify the source file or URL exists and is accessible",
                "Check file format is supported (txt, md, json, csv, pdf)",
                "Ensure network connectivity for URL imports",
            ],
        )

        super().__init__(message, **kwargs)


class ErrorHandler:
    """Central error handling and reporting system."""

    def __init__(self):
        self.error_stats = {"total_errors": 0, "errors_by_code": {}, "errors_by_severity": {}, "recent_errors": []}

        # Documentation links for common errors
        self.doc_links = {
            ErrorCode.INVALID_SLOT_NAME: "https://docs.memcord.dev/slot-naming",
            ErrorCode.RATE_LIMIT_EXCEEDED: "https://docs.memcord.dev/rate-limits",
            ErrorCode.STORAGE_ERROR: "https://docs.memcord.dev/troubleshooting/storage",
            ErrorCode.IMPORT_FAILED: "https://docs.memcord.dev/importing-content",
        }

    def handle_error(self, error: Exception, operation: str = None, context: dict[str, Any] = None) -> MemcordError:
        """Convert any exception to a MemcordError with proper context."""
        if isinstance(error, MemcordError):
            memcord_error = error
        else:
            # Convert standard exceptions to MemcordError
            memcord_error = self._convert_exception(error, operation, context)

        # Add documentation link if available
        if memcord_error.error_code in self.doc_links:
            memcord_error.documentation_link = self.doc_links[memcord_error.error_code]

        # Track error statistics
        self._track_error(memcord_error)

        return memcord_error

    def _convert_exception(
        self, error: Exception, operation: str = None, context: dict[str, Any] = None
    ) -> MemcordError:
        """Convert standard Python exceptions to MemcordError."""
        context = context or {}
        if operation:
            context["operation"] = operation

        if isinstance(error, ValueError):
            return ValidationError(
                str(error), context=context, recovery_suggestions=["Check your input values and try again"]
            )
        elif isinstance(error, FileNotFoundError):
            return StorageError(
                f"File not found: {str(error)}",
                error_code=ErrorCode.FILE_NOT_FOUND,
                context=context,
                recovery_suggestions=["Verify the file path exists", "Check file permissions"],
            )
        elif isinstance(error, PermissionError):
            return StorageError(
                f"Permission denied: {str(error)}",
                error_code=ErrorCode.INSUFFICIENT_PERMISSIONS,
                context=context,
                recovery_suggestions=["Check file/directory permissions", "Run with appropriate privileges"],
            )
        elif isinstance(error, TimeoutError):
            return OperationTimeoutError(f"Operation timed out: {str(error)}", operation=operation, context=context)
        else:
            return MemcordError(
                f"Unexpected error: {str(error)}",
                error_code=ErrorCode.INTERNAL_ERROR,
                severity=ErrorSeverity.HIGH,
                context={**context, "exception_type": type(error).__name__},
                recovery_suggestions=["Try the operation again", "Contact support if the problem persists"],
            )

    def _track_error(self, error: MemcordError):
        """Track error statistics."""
        self.error_stats["total_errors"] += 1

        # Track by error code
        code_name = error.error_code.name
        self.error_stats["errors_by_code"][code_name] = self.error_stats["errors_by_code"].get(code_name, 0) + 1

        # Track by severity
        severity = error.severity.value
        self.error_stats["errors_by_severity"][severity] = self.error_stats["errors_by_severity"].get(severity, 0) + 1

        # Keep recent errors (last 100)
        self.error_stats["recent_errors"].append(error.to_dict())
        if len(self.error_stats["recent_errors"]) > 100:
            self.error_stats["recent_errors"].pop(0)

    def get_error_stats(self) -> dict[str, Any]:
        """Get error statistics."""
        return self.error_stats.copy()

    def create_validation_error(self, message: str, field: str = None, value: Any = None) -> ValidationError:
        """Helper to create validation errors."""
        return ValidationError(message, field=field, value=value)

    def create_rate_limit_error(self, operation: str, limit: int) -> RateLimitError:
        """Helper to create rate limit errors."""
        return RateLimitError(
            f"Rate limit exceeded for {operation} ({limit} requests/minute)", operation=operation, limit=limit
        )

    def create_storage_error(self, message: str, slot_name: str = None) -> StorageError:
        """Helper to create storage errors."""
        return StorageError(message, slot_name=slot_name)

    def create_timeout_error(self, operation: str, timeout_seconds: int) -> OperationTimeoutError:
        """Helper to create timeout errors."""
        return OperationTimeoutError(
            f"Operation {operation} timed out after {timeout_seconds} seconds",
            operation=operation,
            timeout_seconds=timeout_seconds,
        )


# Global error handler instance
error_handler = ErrorHandler()


def handle_errors(func):
    """Decorator to automatically handle errors in tool functions."""

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            # Extract operation name from function name
            operation = getattr(func, "__name__", "unknown_operation")
            handled_error = error_handler.handle_error(e, operation)
            raise handled_error from e

    return wrapper


def handle_async_errors(func):
    """Decorator to automatically handle errors in async tool functions."""

    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            # Extract operation name from function name
            operation = getattr(func, "__name__", "unknown_operation")
            handled_error = error_handler.handle_error(e, operation)
            raise handled_error from e

    return wrapper
