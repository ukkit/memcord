"""Tests for models.py core data structure contracts.

Tests data model validation, security, and business logic.

Coverage: 93%
- Security validation: XSS protection, SQL injection, path traversal
- Data validation: Content limits, group paths, search queries
- Business logic: Compression stats, timeline context, state management
- Edge cases: Boundary conditions, error scenarios

Tests focus on validation logic and security contracts.
"""

from datetime import datetime

import pytest
from pydantic import ValidationError

from memcord.models import CompressionInfo, MemoryEntry, MemorySlot


class TestMemoryEntryContracts:
    """Test MemoryEntry data structure contracts."""

    def test_memory_entry_valid_creation(self):
        """Test creating valid MemoryEntry objects."""
        from .conftest import MemoryEntryFactory, assert_valid_memory_entry

        entry = MemoryEntryFactory.create_manual_save("This is valid content")

        assert_valid_memory_entry(entry, "manual_save")
        assert entry.content == "This is valid content"
        assert entry.original_length is None
        assert entry.summary_length is None

    def test_memory_entry_auto_summary_type(self):
        """Test MemoryEntry with auto_summary type."""
        from .conftest import MemoryEntryFactory, assert_valid_memory_entry

        entry = MemoryEntryFactory.create_auto_summary("This is a summary", original_length=1000)

        assert_valid_memory_entry(entry, "auto_summary")
        assert entry.original_length == 1000
        assert entry.summary_length == len("This is a summary")

    def test_memory_entry_invalid_type(self):
        """Test that invalid entry types are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            MemoryEntry(type="invalid_type", content="Content")

        assert "String should match pattern" in str(exc_info.value)

    def test_memory_entry_empty_content(self):
        """Test that empty content is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            MemoryEntry(type="manual_save", content="")

        assert "String should have at least 1 character" in str(exc_info.value)

    def test_memory_entry_empty_content_custom_validator(self):
        """Test custom validator for empty content."""
        from memcord.models import MemoryEntry

        # Test the custom validator directly
        with pytest.raises(ValueError, match="Content cannot be empty"):
            MemoryEntry.validate_content_size("")

    def test_memory_entry_oversized_content_custom_validator(self):
        """Test custom validator for oversized content."""
        from memcord.models import MemoryEntry

        # Create content that's exactly over 10MB in bytes
        oversized_content = "x" * (10_485_760 + 1)  # 10MB + 1 byte

        # Test the custom validator directly
        with pytest.raises(ValueError, match="Content too large.*bytes \\(max 10MB\\)"):
            MemoryEntry.validate_content_size(oversized_content)

    def test_memory_entry_content_size_limit(self):
        """Test content size validation (10MB limit)."""
        from .conftest import create_test_content

        # Create content that exceeds 10MB
        large_content = create_test_content(size_mb=10.1)  # 10.1MB

        with pytest.raises(ValidationError) as exc_info:
            MemoryEntry(type="manual_save", content=large_content)

        assert "String should have at most 10485760 characters" in str(exc_info.value)

    def test_memory_entry_xss_protection(self):
        """Test XSS protection in content validation."""
        from .conftest import TestDataHelper

        for malicious_content in TestDataHelper.get_malicious_content_samples():
            with pytest.raises(ValidationError) as exc_info:
                MemoryEntry(type="manual_save", content=malicious_content)

            assert "potentially unsafe script elements" in str(exc_info.value)

    def test_memory_entry_unicode_content(self):
        """Test that Unicode content is properly handled."""
        unicode_content = "🚀 Unicode test: 你好世界 🌟 Café naïve résumé"

        from .conftest import MemoryEntryFactory

        entry = MemoryEntryFactory.create_manual_save(unicode_content)

        assert entry.content == unicode_content

    def test_memory_entry_metadata_handling(self):
        """Test metadata field functionality."""
        metadata = {
            "source": "test",
            "priority": 1,
            "tags": ["important", "test"],
            "nested": {"key": "value"},
        }

        from .conftest import MemoryEntryFactory

        entry = MemoryEntryFactory.create_manual_save("Content with metadata", metadata=metadata)

        assert entry.metadata == metadata

    def test_compression_info_structure(self):
        """Test CompressionInfo data structure."""
        compression = CompressionInfo(
            is_compressed=True,
            algorithm="gzip",
            original_size=1000,
            compressed_size=750,
            compression_ratio=0.75,
            compressed_at=datetime.now(),
        )

        assert compression.is_compressed is True
        assert compression.algorithm == "gzip"
        assert compression.compression_ratio == 0.75


class TestMemorySlotContracts:
    """Test MemorySlot data structure contracts."""

    def test_memory_slot_valid_creation(self):
        """Test creating valid MemorySlot objects."""
        from .conftest import MemorySlotFactory

        slot = MemorySlotFactory.create_basic("test_slot")

        assert slot.slot_name == "test_slot"
        assert len(slot.entries) == 1
        assert isinstance(slot.created_at, datetime)
        assert isinstance(slot.updated_at, datetime)
        assert slot.current_slot is False
        assert len(slot.tags) == 0

    def test_memory_slot_name_validation_basic(self):
        """Test basic slot name validation."""
        # Valid names should work
        from .conftest import MemorySlotFactory, TestDataHelper

        for name in TestDataHelper.get_valid_slot_names():
            slot = MemorySlotFactory.create_basic(name)
            assert slot.slot_name == name

    def test_memory_slot_name_security_validation(self):
        """Test security validation for slot names."""
        dangerous_names = [
            "<script>alert('xss')</script>",
            "test'; DROP TABLE slots; --",
            "test/../../../etc/passwd",
            "test..\\windows\\system32",
            "CON",  # Windows reserved
            "PRN",  # Windows reserved
            "__ZERO__",  # memcord reserved
        ]

        for dangerous_name in dangerous_names:
            with pytest.raises(ValidationError):
                MemorySlot(slot_name=dangerous_name)

    def test_memory_slot_name_sql_injection_protection(self):
        """Test SQL injection protection in slot names."""
        # Test cases that should be REJECTED
        rejected_cases = [
            ("test'; DROP TABLE slots; --", "unsafe characters"),  # Contains ; and '
            ("test UNION SELECT * FROM users", "SQL keyword or pattern: UNION"),
            ("test; DELETE FROM slots", "unsafe characters"),  # Contains ;
            ("test/* comment */", "SQL keyword or pattern"),  # Contains /*
            ("test-- comment", "SQL keyword or pattern"),  # Contains --
        ]

        for case, expected_error in rejected_cases:
            with pytest.raises(ValidationError) as exc_info:
                MemorySlot(slot_name=case)

            assert expected_error in str(exc_info.value)

        # Test cases that should be ALLOWED (actual behavior validation)
        # Note: SQL keywords are checked with 'in' operator, so they're strict
        allowed_cases = [
            "testword",  # Simple word
            "my_project",  # Underscore allowed
            "project-alpha",  # Dash allowed
            "notes2025",  # Numbers allowed
        ]

        for case in allowed_cases:
            # Should not raise exception
            slot = MemorySlot(slot_name=case)
            assert slot.slot_name == case

    def test_memory_slot_path_traversal_protection(self):
        """Test path traversal protection."""
        traversal_attempts = [
            "test/../../../etc/passwd",
            "test..\\windows\\system32",
            "../../../root",
            "test/../../config",
        ]

        for traversal_attempt in traversal_attempts:
            with pytest.raises(ValidationError) as exc_info:
                MemorySlot(slot_name=traversal_attempt)

            assert "path traversal" in str(exc_info.value)

    def test_memory_slot_group_path_validation(self):
        """Test group path validation and security."""
        # Valid group paths
        valid_groups = [
            "projects/work",
            "personal/notes",
            "team-meetings",
            None,  # Should allow None
        ]

        for group_path in valid_groups:
            slot = MemorySlot(slot_name="test", group_path=group_path)
            assert slot.group_path == group_path

        # Invalid group paths (path traversal)
        with pytest.raises(ValidationError):
            MemorySlot(slot_name="test", group_path="projects/../../../etc")

    def test_memory_slot_group_path_system_directory_protection(self):
        """Test group path protection against system directories."""
        # Test system directory protection using actual dangerous paths from validator
        dangerous_paths = ["/etc/config", "/proc/status", "/root/admin", "/usr/bin/test", "/var/log/app.log"]

        for dangerous_path in dangerous_paths:
            with pytest.raises(ValidationError) as exc_info:
                MemorySlot(slot_name="test", group_path=dangerous_path)

            # Verify the correct error message
            assert "Group path cannot access system directories" in str(exc_info.value)

    def test_memory_slot_group_path_empty_components(self):
        """Test group path validation for empty components."""
        # Test empty path components that don't trigger earlier validations
        # These should get past path traversal checks but fail on empty components
        invalid_paths = ["project//subdir", "test///middle", "start//end"]

        for path in invalid_paths:
            with pytest.raises(ValidationError) as exc_info:
                MemorySlot(slot_name="test", group_path=path)

            assert "Group path cannot have empty components" in str(exc_info.value)

    def test_memory_slot_group_path_single_dot_components(self):
        """Test group path validation for single dot components."""
        # Test single dots that don't trigger the path traversal check
        # Use forward slashes only and avoid .. patterns
        invalid_paths = ["project/.", "middle/./end"]

        for path in invalid_paths:
            with pytest.raises(ValidationError) as exc_info:
                MemorySlot(slot_name="test", group_path=path)

            assert "Group path cannot contain . or .. components" in str(exc_info.value)

    def test_memory_slot_tags_handling(self):
        """Test tag management in memory slots."""
        from .conftest import MemorySlotFactory

        slot = MemorySlotFactory.create_with_tags("test_tags", tags={"project", "important", "work"})

        assert len(slot.tags) == 3
        assert "project" in slot.tags
        assert "important" in slot.tags
        assert "work" in slot.tags

    def test_memory_slot_content_length_calculation(self):
        """Test total content length calculation."""
        from .conftest import MemoryEntryFactory

        slot = MemorySlot(
            slot_name="length_test",
            entries=[
                MemoryEntryFactory.create_manual_save("First entry"),  # 11 chars
                MemoryEntryFactory.create_manual_save("Second entry"),  # 12 chars
                MemoryEntryFactory.create_auto_summary("Summary"),  # 7 chars
            ],
        )

        total_length = slot.get_total_content_length()
        assert total_length == 30  # 11 + 12 + 7

    def test_memory_slot_entry_management(self):
        """Test adding and managing entries in memory slots."""
        from .conftest import MemorySlotFactory

        slot = MemorySlotFactory.create_basic("entry_test", entries=[])

        # Start with empty entries
        assert len(slot.entries) == 0

        # Add entries
        from .conftest import MemoryEntryFactory

        entry1 = MemoryEntryFactory.create_manual_save("First")
        entry2 = MemoryEntryFactory.create_auto_summary("Summary")

        slot.entries.append(entry1)
        slot.entries.append(entry2)

        assert len(slot.entries) == 2
        assert slot.entries[0].content == "First"
        assert slot.entries[1].content == "Summary"

    def test_memory_slot_archival_contract(self):
        """Test archival state management."""
        from .conftest import MemorySlotFactory

        slot = MemorySlotFactory.create_archived("archive_test", reason="project_completed")

        assert slot.is_archived is True
        assert slot.archived_at is not None
        assert slot.archive_reason == "project_completed"

    def test_memory_slot_priority_system(self):
        """Test priority level handling."""
        from .conftest import MemorySlotFactory

        # Normal priority
        normal_slot = MemorySlotFactory.create_basic("normal", priority=0)
        assert normal_slot.priority == 0

        # High priority
        high_slot = MemorySlotFactory.create_basic("high", priority=1)
        assert high_slot.priority == 1

        # Low priority
        low_slot = MemorySlotFactory.create_basic("low", priority=-1)
        assert low_slot.priority == -1

    def test_memory_slot_json_serialization(self):
        """Test JSON serialization with complex data."""
        from .conftest import MemoryEntryFactory

        slot = MemorySlot(
            slot_name="json_test",
            entries=[MemoryEntryFactory.create_manual_save("Test content", metadata={"key": "value"})],
            tags={"tag1", "tag2"},
            group_path="test/group",
            description="Test description",
            priority=1,
        )

        # Should be serializable to dict
        slot_dict = slot.model_dump()

        assert slot_dict["slot_name"] == "json_test"
        assert len(slot_dict["entries"]) == 1
        # Note: Pydantic keeps tags as set in model_dump, but can be configured differently
        assert "tags" in slot_dict
        assert slot_dict["group_path"] == "test/group"
        assert slot_dict["priority"] == 1

    def test_memory_slot_compression_error_handling(self):
        """Test compression decompression error handling."""
        from unittest.mock import patch

        from memcord.models import CompressionInfo, MemoryEntry, MemorySlot

        # Create an entry with compression info that will fail decompression
        corrupted_compression_info = CompressionInfo(
            is_compressed=True, algorithm="corrupted", original_size=100, compressed_size=50
        )

        corrupted_entry = MemoryEntry(
            type="manual_save", content="corrupted_compressed_data", compression_info=corrupted_compression_info
        )

        slot = MemorySlot(slot_name="test_compression_error", entries=[corrupted_entry])

        # Mock the decompression to fail and test error handling
        with patch("memcord.compression.ContentCompressor") as mock_compressor_class:
            mock_compressor = mock_compressor_class.return_value
            mock_compressor.decompress_json_content.side_effect = Exception("Decompression failed")

            # This should handle the exception gracefully and continue (lines 247-251)
            with patch("builtins.print") as mock_print:
                searchable_content = slot.get_searchable_content()

                # Should have printed the warning (line 250)
                mock_print.assert_called_once()
                warning_call = mock_print.call_args[0][0]
                assert "Warning: Failed to decompress content for search" in warning_call
                assert "Decompression failed" in warning_call

                # Should still return content (without the failed entry)
                assert "test_compression_error" in searchable_content

    def test_memory_slot_compression_stats_calculation(self):
        """Test compression statistics calculation."""
        from memcord.models import CompressionInfo, MemoryEntry, MemorySlot

        # Create entries with mixed compression states
        uncompressed_entry = MemoryEntry(type="manual_save", content="This is uncompressed content")

        compressed_entry = MemoryEntry(
            type="auto_summary",
            content="compressed_data",
            compression_info=CompressionInfo(
                is_compressed=True, algorithm="gzip", original_size=1000, compressed_size=500
            ),
        )

        slot = MemorySlot(slot_name="compression_stats_test", entries=[uncompressed_entry, compressed_entry])

        # Test
        stats = slot.get_compression_stats()

        # Verify all the calculated values
        assert stats["total_entries"] == 2
        assert stats["compressed_entries"] == 1
        assert stats["compression_percentage"] == 50.0  # 1/2 * 100

        # Test
        expected_uncompressed_size = len(b"This is uncompressed content")
        expected_total_original = 1000 + expected_uncompressed_size  # compressed + uncompressed
        assert stats["total_original_size"] == expected_total_original

        # Test compressed size calculation
        expected_total_compressed = 500 + expected_uncompressed_size  # compressed + uncompressed
        assert stats["total_compressed_size"] == expected_total_compressed

        # Test
        expected_ratio = expected_total_compressed / expected_total_original
        assert stats["compression_ratio"] == expected_ratio

    def test_memory_slot_compression_stats_empty_slot(self):
        """Test compression stats with empty slot (edge case)."""
        from memcord.models import MemorySlot

        empty_slot = MemorySlot(slot_name="empty_test", entries=[])

        stats = empty_slot.get_compression_stats()

        # Should handle division by zero case
        assert stats["total_entries"] == 0
        assert stats["compressed_entries"] == 0
        assert stats["compression_ratio"] == 1.0  # Default when total_original_size is 0

    def test_memory_slot_relative_time_entry_retrieval(self):
        """Test relative time entry retrieval."""
        from unittest.mock import patch

        from memcord.models import MemoryEntry, MemorySlot

        # Create slot with multiple entries at different times
        entry1 = MemoryEntry(type="manual_save", content="First entry")
        entry2 = MemoryEntry(type="manual_save", content="Second entry")
        entry3 = MemoryEntry(type="manual_save", content="Third entry")

        slot = MemorySlot(slot_name="time_test", entries=[entry1, entry2, entry3])

        # Test
        with patch("memcord.temporal_parser.TemporalParser.parse_relative_time", return_value=None):
            result = slot.get_entry_by_relative_time("invalid_time_desc")
            assert result is None

        # Test
        with patch("memcord.temporal_parser.TemporalParser.parse_relative_time", return_value=("latest", None, None)):
            result = slot.get_entry_by_relative_time("latest")
            assert result is not None
            index, entry = result
            assert index == 2  # Last index
            assert entry == entry3  # Last entry

        # Test
        with patch("memcord.temporal_parser.TemporalParser.parse_relative_time", return_value=("oldest", None, None)):
            result = slot.get_entry_by_relative_time("oldest")
            assert result is not None
            index, entry = result
            assert index == 0  # First index
            assert entry == entry1  # First entry

        # Test with empty slot
        empty_slot = MemorySlot(slot_name="empty", entries=[])
        with patch("memcord.temporal_parser.TemporalParser.parse_relative_time", return_value=("latest", None, None)):
            result = empty_slot.get_entry_by_relative_time("latest")
            assert result is None

    def test_memory_slot_entry_by_index_method(self):
        """Test get_entry_by_index method."""
        from memcord.models import MemoryEntry, MemorySlot

        # Create slot with multiple entries for indexing tests
        entries = [
            MemoryEntry(type="manual_save", content="Entry 0"),
            MemoryEntry(type="manual_save", content="Entry 1"),
            MemoryEntry(type="manual_save", content="Entry 2"),
        ]

        slot = MemorySlot(slot_name="index_test", entries=entries)

        # Test
        empty_slot = MemorySlot(slot_name="empty", entries=[])
        assert empty_slot.get_entry_by_index(0) is None

        # Test
        result = slot.get_entry_by_index(0, reverse=False)
        assert result is not None
        index, entry = result
        assert index == 0
        assert entry.content == "Entry 0"

        # Test
        result = slot.get_entry_by_index(-1, reverse=False)
        assert result is not None
        index, entry = result
        assert index == 2  # len(entries) + (-1) = 3 + (-1) = 2
        assert entry.content == "Entry 2"

        # Test
        result = slot.get_entry_by_index(0, reverse=True)
        assert result is not None
        index, entry = result
        assert index == 2  # len(entries) - 1 - 0 = 2
        assert entry.content == "Entry 2"

        # Test
        result = slot.get_entry_by_index(-1, reverse=True)
        assert result is not None
        index, entry = result
        assert index == 2  # len(entries) + (-1) = 3 + (-1) = 2
        assert entry.content == "Entry 2"

        # Test out of bounds index (should return None)
        assert slot.get_entry_by_index(99) is None
        assert slot.get_entry_by_index(-99) is None

    def test_memory_slot_timeline_context_method(self):
        """Test get_timeline_context method."""
        from datetime import datetime, timedelta

        from memcord.models import MemoryEntry, MemorySlot

        # Create entries with different timestamps
        base_time = datetime.now()
        entries = [
            MemoryEntry(type="manual_save", content="First", timestamp=base_time - timedelta(hours=2)),
            MemoryEntry(type="auto_summary", content="Second", timestamp=base_time - timedelta(hours=1)),
            MemoryEntry(type="manual_save", content="Third", timestamp=base_time),
        ]

        slot = MemorySlot(slot_name="timeline_test", entries=entries)

        # Test
        assert slot.get_timeline_context(-1) == {}
        assert slot.get_timeline_context(99) == {}

        # Test empty slot
        empty_slot = MemorySlot(slot_name="empty", entries=[])
        assert empty_slot.get_timeline_context(0) == {}

        # Test valid middle entry (should have both previous and next)
        context = slot.get_timeline_context(1)

        # Verify basic context info (lines 373-378)
        assert context["position"] == "2 of 3 entries"
        assert context["selected_type"] == "auto_summary"
        assert context["total_entries"] == 3

        # Verify previous entry info (lines 381-384)
        assert "previous_entry" in context
        assert context["previous_entry"]["type"] == "manual_save"

        # Verify next entry info (lines 385+)
        assert "next_entry" in context
        assert context["next_entry"]["type"] == "manual_save"

        # Test first entry (no previous, but has next)
        first_context = slot.get_timeline_context(0)
        assert "previous_entry" not in first_context
        assert "next_entry" in first_context

        # Test last entry (has previous, no next)
        last_context = slot.get_timeline_context(2)
        assert "previous_entry" in last_context
        assert "next_entry" not in last_context

    def test_search_query_validation_security(self):
        """Test search query validation for security."""
        from memcord.models import SearchQuery

        # Test
        with pytest.raises(ValidationError):
            SearchQuery(query="")

        with pytest.raises(ValidationError):
            SearchQuery(query="   ")  # Only whitespace

        # Test
        dangerous_patterns = ["(?", "(*", "(?=", "(?!", "(?<=", "(?<!"]

        for pattern in dangerous_patterns:
            malicious_query = f"search{pattern}malicious"
            with pytest.raises(ValidationError) as exc_info:
                SearchQuery(query=malicious_query)

            assert "Search query contains potentially dangerous regex pattern" in str(exc_info.value)

        # Test
        too_many_wildcards = "a*b*c*d*e*f*g*h*i*j*k*"  # 11 wildcards
        with pytest.raises(ValidationError) as exc_info:
            SearchQuery(query=too_many_wildcards)

        assert "Search query contains too many wildcards (max 10)" in str(exc_info.value)

        # Test valid queries pass
        valid_queries = [
            "simple search",
            "search with * wildcards",
            "regex-safe query",
            "a*b*c*d*e*f*g*h*i*j",  # Exactly 10 wildcards (should pass)
        ]

        for query in valid_queries:
            # Should not raise exception
            search_req = SearchQuery(query=query)
            assert search_req.query == query.strip()

    def test_search_query_tag_filters_validation(self):
        """Test tag filter validation."""
        from memcord.models import SearchQuery

        # Test
        too_many_tags = [f"tag{i}" for i in range(51)]  # 51 tags
        with pytest.raises(ValidationError) as exc_info:
            SearchQuery(query="test", include_tags=too_many_tags)

        assert "Too many tags in filter (max 50)" in str(exc_info.value)

        # Test
        invalid_tags = ["", "   ", None, 123]
        for invalid_tag in invalid_tags:
            if invalid_tag is not None:  # Skip None as it's filtered by Pydantic
                with pytest.raises(ValidationError):
                    SearchQuery(query="test", include_tags=["valid", invalid_tag])

        # Test
        long_tag = "x" * 101  # 101 characters
        with pytest.raises(ValidationError) as exc_info:
            SearchQuery(query="test", include_tags=[long_tag])

        assert "Tag too long (max 100 chars)" in str(exc_info.value)

        # Test
        search_query = SearchQuery(query="test", include_tags=["  UPPERCASE  ", "MixedCase", "lowercase"])
        # Should be stripped and lowercased
        assert search_query.include_tags == ["uppercase", "mixedcase", "lowercase"]

    def test_search_query_group_filters_validation(self):
        """Test group filter validation."""
        from memcord.models import SearchQuery

        # Test
        too_many_groups = [f"group{i}" for i in range(21)]  # 21 groups
        with pytest.raises(ValidationError) as exc_info:
            SearchQuery(query="test", include_groups=too_many_groups)

        assert "Too many groups in filter (max 20)" in str(exc_info.value)

        # Test invalid group types (similar to tags)
        invalid_groups = ["", "   "]
        for invalid_group in invalid_groups:
            with pytest.raises(ValidationError):
                SearchQuery(query="test", include_groups=["valid", invalid_group])

        # Test valid groups pass
        search_query = SearchQuery(
            query="test", include_groups=["project/web", "meetings"], exclude_groups=["archived"]
        )
        assert len(search_query.include_groups) == 2
        assert len(search_query.exclude_groups) == 1

    def test_server_state_management(self):
        """Test ServerState methods."""
        from memcord.models import GroupInfo, ServerState

        state = ServerState()

        # Test
        state.set_current_slot("test_slot")
        assert state.current_slot == "test_slot"
        assert "test_slot" in state.available_slots

        # Test adding slot that doesn't exist yet
        state.set_current_slot("new_slot")
        assert state.current_slot == "new_slot"
        assert "new_slot" in state.available_slots

        # Test tag management (lines 544, 548)
        state.add_tag_to_global_set("  PROJECT  ")  # Test normalization
        assert "project" in state.all_tags

        state.remove_tag_from_global_set("PROJECT")  # Test removal
        assert "project" not in state.all_tags

        # Test group management (lines 552, 556-558)
        group_info = GroupInfo(path="test/group", name="Test Group", description="Test group")
        state.add_group(group_info)
        assert "test/group" in state.groups

        # Test
        removed = state.remove_group("test/group")
        assert removed is True
        assert "test/group" not in state.groups

        # Test remove non-existent group
        removed = state.remove_group("nonexistent")
        assert removed is False

    def test_server_state_utility_methods(self):
        """Test ServerState utility methods."""
        from memcord.models import GroupInfo, ServerState

        state = ServerState()

        # Test
        group1 = GroupInfo(path="parent/child1", name="Child 1", parent_path="parent")
        group2 = GroupInfo(path="parent/child2", name="Child 2", parent_path="parent")
        group3 = GroupInfo(path="orphan", name="Orphan")  # No parent_path

        state.add_group(group1)
        state.add_group(group2)
        state.add_group(group3)

        hierarchy = state.get_group_hierarchy()

        # Should group by parent
        assert "parent" in hierarchy
        assert len(hierarchy["parent"]) == 2
        assert "parent/child1" in hierarchy["parent"]
        assert "parent/child2" in hierarchy["parent"]

        # Orphan should be under "root"
        assert "root" in hierarchy
        assert "orphan" in hierarchy["root"]

        # Test
        assert state.is_zero_mode() is False  # Initially not in zero mode

        state.activate_zero_mode()
        assert state.current_slot == "__ZERO__"
        assert state.is_zero_mode() is True

    def test_memory_entry_compression_info_edge_cases(self):
        """Test CompressionInfo edge cases and validation."""
        from memcord.models import CompressionInfo, MemoryEntry

        # Test CompressionInfo with edge cases
        compression_info = CompressionInfo(
            is_compressed=True,
            algorithm="custom_algorithm",
            original_size=None,  # Test None values
            compressed_size=None,
            compression_ratio=None,
        )

        # Test entry with this compression info
        entry = MemoryEntry(
            type="auto_summary",
            content="test content",
            original_length=1000,
            summary_length=500,
            compression_info=compression_info,
        )

        assert entry.compression_info.is_compressed is True
        assert entry.compression_info.original_size is None
        assert entry.original_length == 1000

        # Test default CompressionInfo
        default_entry = MemoryEntry(type="manual_save", content="default test")
        assert default_entry.compression_info.is_compressed is False
        assert default_entry.compression_info.algorithm == "none"

    def test_memory_slot_edge_cases(self):
        """Test edge cases in memory slot handling."""
        # Very long but valid slot name
        from .conftest import MemorySlotFactory

        long_name = "a" * 100  # Max length
        slot = MemorySlotFactory.create_basic(long_name)
        assert slot.slot_name == long_name

        # Name that's too long should fail
        with pytest.raises(ValidationError):
            MemorySlot(slot_name="a" * 101)

        # Very long description (at limit)
        long_desc = "x" * 1000  # Max length
        slot = MemorySlotFactory.create_basic("test", description=long_desc)
        assert slot.description == long_desc

        # Description too long should fail
        with pytest.raises(ValidationError):
            MemorySlot(slot_name="test", description="x" * 1001)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
