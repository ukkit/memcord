"""Shared test fixtures and utilities for memcord testing.

This module provides reusable test fixtures, helpers, and utilities
that make tests cleaner, more maintainable, and easier to write.
"""

import asyncio
import tempfile
from collections.abc import AsyncGenerator, Generator
from pathlib import Path

import pytest

from memcord.models import MemoryEntry, MemorySlot
from memcord.storage import StorageManager


@pytest.fixture
def anyio_backend():
    """Configure async backend for anyio/pytest compatibility."""
    return "asyncio"


@pytest.fixture
def temp_storage_dir() -> Generator[str, None, None]:
    """Provide a temporary directory for storage testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield temp_dir


@pytest.fixture
async def clean_storage_manager(
    temp_storage_dir: str,
) -> AsyncGenerator[StorageManager, None]:
    """Provide a clean StorageManager instance with isolated storage."""
    storage = StorageManager(
        memory_dir=temp_storage_dir,
        shared_dir=str(Path(temp_storage_dir) / "shared"),
        enable_caching=False,  # Disable for predictable testing
        enable_efficiency=False,  # Disable for simpler testing
        enable_memory_management=False,  # Disable for cleaner testing
    )

    try:
        yield storage
    finally:
        # Cleanup any background tasks
        if hasattr(storage, "_cache_manager") and storage._cache_manager:
            await storage._cache_manager.shutdown()


@pytest.fixture
async def populated_storage_manager(
    clean_storage_manager: StorageManager,
) -> StorageManager:
    """Provide a StorageManager with sample test data."""
    storage = clean_storage_manager

    # Create sample slots
    await storage.save_memory("test_slot_1", "First test content")
    await storage.save_memory("test_slot_2", "Second test content")
    await storage.save_memory("python_project", "Python programming tutorial")

    return storage


@pytest.fixture
def sample_memory_entry() -> MemoryEntry:
    """Provide a sample MemoryEntry for testing."""
    return MemoryEntry(
        type="manual_save",
        content="Sample test content for validation",
        metadata={"test": True, "source": "pytest"},
    )


@pytest.fixture
def sample_memory_slot() -> MemorySlot:
    """Provide a sample MemorySlot for testing."""
    return MemorySlot(
        slot_name="test_slot",
        entries=[
            MemoryEntry(type="manual_save", content="First entry"),
            MemoryEntry(
                type="auto_summary",
                content="Summary entry",
                original_length=100,
                summary_length=50,
            ),
        ],
        tags={"test", "sample"},
        group_path="test/group",
        description="Test slot for validation",
        priority=1,
    )


class MockStorageManager:
    """Mock storage manager for testing components that depend on storage."""

    def __init__(self, slot_count: int = 5, should_fail: bool = False):
        self.slot_count = slot_count
        self.should_fail = should_fail
        self.slots = {}

    async def list_memory_slots(self) -> list:
        """Mock async method that returns memory slots matching real storage format."""
        if self.should_fail:
            raise RuntimeError("Storage manager failure")

        # Simulate some async work
        await asyncio.sleep(0.01)

        from datetime import datetime

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

    async def save_memory(self, slot_name: str, content: str) -> MemoryEntry:
        """Mock save_memory for testing."""
        if self.should_fail:
            raise RuntimeError("Storage save failure")

        entry = MemoryEntry(type="manual_save", content=content)
        self.slots[slot_name] = entry
        return entry

    async def read_memory(self, slot_name: str) -> MemorySlot:
        """Mock read_memory for testing."""
        if slot_name in self.slots:
            return MemorySlot(slot_name=slot_name, entries=[self.slots[slot_name]])
        return None


@pytest.fixture
def mock_storage_manager():
    """Provide a mock storage manager for testing."""
    return MockStorageManager()


@pytest.fixture
def failing_mock_storage_manager():
    """Provide a mock storage manager that fails operations."""
    return MockStorageManager(should_fail=True)


# Test helper functions
def assert_valid_memory_entry(entry: MemoryEntry, expected_type: str = "manual_save"):
    """Assert that a MemoryEntry has valid structure and data."""
    assert isinstance(entry, MemoryEntry)
    assert entry.type == expected_type
    assert entry.content is not None
    assert len(entry.content) > 0
    assert entry.timestamp is not None


def assert_valid_memory_slot(slot: MemorySlot):
    """Assert that a MemorySlot has valid structure and data."""
    assert isinstance(slot, MemorySlot)
    assert slot.slot_name is not None
    assert len(slot.slot_name) > 0
    assert slot.created_at is not None
    assert slot.updated_at is not None
    assert isinstance(slot.entries, list)


def create_test_content(size_mb: float = 0.001) -> str:
    """Create test content of specified size for testing."""
    char_count = int(size_mb * 1024 * 1024)
    return "x" * char_count


def create_malicious_content_samples() -> list:
    """Create samples of malicious content for security testing."""
    return [
        "<script>alert('xss')</script>",
        "javascript:alert('xss')",
        "data:text/html,<script>alert('xss')</script>",
        "vbscript:msgbox('xss')",
        "<div onclick='alert()'>Click me</div>",
        "<img src='x' onerror='alert()'>",
        "'; DROP TABLE users; --",
        "test/../../../etc/passwd",
    ]


def create_valid_slot_names() -> list:
    """Create samples of valid slot names for testing."""
    return [
        "project_alpha",
        "meeting-notes",
        "2025_goals",
        "café_notes",  # Unicode
        "project.backup",
        "team_collaboration",
        "research_notes",
    ]


# Factory classes for test data generation
class MemoryEntryFactory:
    """Factory for creating MemoryEntry test objects."""

    @staticmethod
    def create_manual_save(content: str = "Test content", **kwargs) -> MemoryEntry:
        """Create a manual_save MemoryEntry."""
        defaults = {
            "type": "manual_save",
            "content": content,
            "metadata": {"test": True},
        }
        defaults.update(kwargs)
        return MemoryEntry(**defaults)

    @staticmethod
    def create_auto_summary(content: str = "Summary content", original_length: int = 1000, **kwargs) -> MemoryEntry:
        """Create an auto_summary MemoryEntry."""
        defaults = {
            "type": "auto_summary",
            "content": content,
            "original_length": original_length,
            "summary_length": len(content),
            "metadata": {"summary": True},
        }
        defaults.update(kwargs)
        return MemoryEntry(**defaults)

    @staticmethod
    def create_large_content(size_mb: float = 1.0) -> MemoryEntry:
        """Create MemoryEntry with large content for testing."""
        content = "x" * int(size_mb * 1024 * 1024)
        return MemoryEntry(type="manual_save", content=content)


class MemorySlotFactory:
    """Factory for creating MemorySlot test objects."""

    @staticmethod
    def create_basic(slot_name: str = "test_slot", **kwargs) -> MemorySlot:
        """Create a basic MemorySlot."""
        defaults = {
            "slot_name": slot_name,
            "entries": [MemoryEntryFactory.create_manual_save()],
            "tags": set(),
            "priority": 0,
        }
        defaults.update(kwargs)
        return MemorySlot(**defaults)

    @staticmethod
    def create_with_tags(slot_name: str = "tagged_slot", tags: set = None, **kwargs) -> MemorySlot:
        """Create MemorySlot with tags."""
        if tags is None:
            tags = {"test", "sample", "automated"}

        return MemorySlotFactory.create_basic(slot_name=slot_name, tags=tags, **kwargs)

    @staticmethod
    def create_archived(slot_name: str = "archived_slot", reason: str = "test_archival", **kwargs) -> MemorySlot:
        """Create an archived MemorySlot."""
        from datetime import datetime

        defaults = {
            "is_archived": True,
            "archived_at": datetime.now(),
            "archive_reason": reason,
        }
        defaults.update(kwargs)
        return MemorySlotFactory.create_basic(slot_name=slot_name, **defaults)

    @staticmethod
    def create_complex(slot_name: str = "complex_slot") -> MemorySlot:
        """Create a complex MemorySlot with multiple entries and metadata."""
        return MemorySlot(
            slot_name=slot_name,
            entries=[
                MemoryEntryFactory.create_manual_save("Initial content"),
                MemoryEntryFactory.create_auto_summary("Summary of content", 500),
                MemoryEntryFactory.create_manual_save("Updated content"),
            ],
            tags={"complex", "test", "multi-entry"},
            group_path="test/complex",
            description="Complex test slot with multiple entries",
            priority=1,
        )


class TestDataHelper:
    """Helper class for common test data operations."""

    @staticmethod
    def get_malicious_content_samples() -> list:
        """Get samples of malicious content for security testing."""
        return [
            "<script>alert('xss')</script>",
            "javascript:alert('xss')",
            "data:text/html,<script>alert('xss')</script>",
            "vbscript:msgbox('xss')",
            "<div onclick='alert()'>Click me</div>",
            "<img src='x' onerror='alert()'>",
        ]

    @staticmethod
    def get_sql_injection_samples() -> list:
        """Get SQL injection attempt samples."""
        return [
            "test'; DROP TABLE slots; --",
            "test UNION SELECT * FROM users",
            "test; DELETE FROM slots",
            "test/* comment */",
            "test-- comment",
        ]

    @staticmethod
    def get_path_traversal_samples() -> list:
        """Get path traversal attempt samples."""
        return [
            "test/../../../etc/passwd",
            "test..\\windows\\system32",
            "../../../root",
            "test/../../config",
        ]

    @staticmethod
    def get_valid_slot_names() -> list:
        """Get valid slot name samples."""
        return [
            "project_alpha",
            "meeting-notes",
            "2025_goals",
            "café_notes",  # Unicode
            "project.backup",
            "team_collaboration",
        ]


# Storage test helpers
class StorageTestHelper:
    """Helper class for storage testing operations."""

    @staticmethod
    async def create_test_slots(storage: StorageManager, count: int = 3) -> list:
        """Create multiple test slots for testing."""
        slot_names = []
        for i in range(count):
            slot_name = f"test_slot_{i}"
            await storage.save_memory(slot_name, f"Test content {i}")
            slot_names.append(slot_name)
        return slot_names

    @staticmethod
    async def verify_slot_exists(storage: StorageManager, slot_name: str) -> bool:
        """Verify a slot exists and is readable."""
        try:
            slot = await storage.read_memory(slot_name)
            return slot is not None
        except Exception:
            return False

    @staticmethod
    async def cleanup_test_slots(storage: StorageManager, slot_names: list):
        """Clean up test slots after testing."""
        for slot_name in slot_names:
            try:
                await storage.delete_slot(slot_name)
            except Exception:
                pass  # Ignore cleanup errors


# Component-specific fixtures
@pytest.fixture
def metrics_collector():
    """Provide a clean MetricsCollector for testing."""
    from memcord.status_monitoring import MetricsCollector

    return MetricsCollector()


@pytest.fixture
def operation_logger():
    """Provide a clean OperationLogger for testing."""
    from memcord.status_monitoring import OperationLogger

    return OperationLogger()


@pytest.fixture
def resource_monitor():
    """Provide a clean ResourceMonitor for testing."""
    from memcord.status_monitoring import ResourceMonitor

    monitor = ResourceMonitor()
    yield monitor
    # Cleanup
    if monitor.monitoring:
        monitor.stop_monitoring()


# Component-specific factories
class MetricsCollectorFactory:
    """Factory for creating MetricsCollector test objects."""

    @staticmethod
    def create_with_max_metrics(max_metrics: int = 1000):
        """Create MetricsCollector with specific max_metrics."""
        from memcord.status_monitoring import MetricsCollector

        return MetricsCollector(max_metrics=max_metrics)

    @staticmethod
    def create_with_sample_data():
        """Create MetricsCollector with sample performance data."""
        from memcord.status_monitoring import MetricsCollector

        collector = MetricsCollector()

        # Add sample metrics
        collector.record_metric("response_time", 125.5, "ms")
        collector.record_metric("cpu_usage", 45.0, "percent")
        collector.record_metric("memory_usage", 67.2, "percent")

        return collector


class OperationLoggerFactory:
    """Factory for creating OperationLogger test objects."""

    @staticmethod
    def create_with_max_logs(max_logs: int = 1000):
        """Create OperationLogger with specific max_logs."""
        from memcord.status_monitoring import OperationLogger

        return OperationLogger(max_logs=max_logs)

    @staticmethod
    def create_with_sample_operations():
        """Create OperationLogger with sample operations."""
        from memcord.status_monitoring import OperationLogger

        logger = OperationLogger()

        # Add sample operations
        logger.start_operation("op1", "test_tool", {"param": "value"})
        logger.complete_operation("op1", status="completed")

        logger.start_operation("op2", "another_tool", {"data": 123})
        logger.complete_operation("op2", status="failed", error_message="Test error")

        return logger


class ResourceMonitorFactory:
    """Factory for creating ResourceMonitor test objects."""

    @staticmethod
    def create_with_interval(interval: int = 30):
        """Create ResourceMonitor with specific collection interval."""
        from memcord.status_monitoring import ResourceMonitor

        return ResourceMonitor(collection_interval=interval)

    @staticmethod
    def create_sample_system_resource():
        """Create a sample SystemResource for testing."""
        from datetime import datetime

        from memcord.status_monitoring import SystemResource

        return SystemResource(
            cpu_percent=50.0,
            memory_percent=65.0,
            memory_used_mb=4096.0,
            memory_available_mb=2048.0,
            disk_usage_percent=75.0,
            disk_free_gb=250.0,
            process_count=120,
            thread_count=25,
            timestamp=datetime.now(),
        )

    @staticmethod
    def create_high_usage_system_resource():
        """Create SystemResource with high usage for alert testing."""
        from datetime import datetime

        from memcord.status_monitoring import SystemResource

        return SystemResource(
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


# Async test helpers
async def create_sample_slots(storage: StorageManager, count: int = 3) -> list:
    """Create sample memory slots for testing."""
    slot_names = []
    for i in range(count):
        slot_name = f"sample_slot_{i}"
        await storage.save_memory(slot_name, f"Sample content {i}")
        slot_names.append(slot_name)
    return slot_names


async def verify_storage_integrity(storage: StorageManager) -> bool:
    """Verify storage system integrity."""
    try:
        # Test basic operations
        _ = await storage.list_memory_slots()

        # Test creating and reading a verification slot
        await storage.save_memory("integrity_test", "Verification content")
        slot = await storage.read_memory("integrity_test")

        # Cleanup
        await storage.delete_slot("integrity_test")

        return slot is not None and slot.entries[0].content == "Verification content"
    except Exception:
        return False
