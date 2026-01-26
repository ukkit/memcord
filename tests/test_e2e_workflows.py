"""End-to-end workflow tests for memcord commands.

These tests validate complete user workflows across multiple operations,
ensuring that common usage patterns work correctly. These tests would have
caught the search index staleness and acronym tokenization bugs.

Test philosophy:
- Test from user perspective (not internal implementation)
- Test cross-instance scenarios (multiple StorageManager instances)
- Test real-world workflows (save → search → read → query)
- Test with realistic content (acronyms, special characters, etc.)
"""

import asyncio
import tempfile
from pathlib import Path

import pytest

from memcord.models import SearchQuery
from memcord.storage import StorageManager


class TestBasicWorkflows:
    """Test basic memcord workflows that users commonly perform."""

    @pytest.fixture
    def temp_dir(self):
        """Provide temporary directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_save_and_search_workflow(self, temp_dir):
        """Test: Create slot → Save content → Search for it.

        This is the most basic workflow and should ALWAYS work.
        """
        storage = StorageManager(
            memory_dir=temp_dir,
            shared_dir=str(Path(temp_dir) / "shared"),
            enable_caching=False,
        )

        # User workflow
        await storage.save_memory("project-notes", "We decided to use PostgreSQL for the database")

        # Should be able to search immediately
        results = await storage.search_memory(SearchQuery(query="PostgreSQL"))
        assert len(results) > 0
        assert any("project-notes" in r.slot_name for r in results)

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_save_with_acronyms_workflow(self, temp_dir):
        """Test: Save content with common acronyms → Search by acronym.

        Tests that CI/CD, API, UI, DB, AWS and other 2-letter acronyms work.
        This test would have caught the acronym tokenization bug.
        """
        storage = StorageManager(memory_dir=temp_dir, shared_dir=str(Path(temp_dir) / "shared"))

        # Save content with various acronyms
        await storage.save_memory("devops-notes", "Set up CI/CD pipeline using AWS")
        await storage.save_memory("api-design", "REST API design for UI components")
        await storage.save_memory("database", "DB migration scripts")

        # Search by acronyms
        test_cases = [
            ("CI/CD", "devops-notes"),
            ("CI", "devops-notes"),
            ("AWS", "devops-notes"),
            ("API", "api-design"),
            ("UI", "api-design"),
            ("DB", "database"),
        ]

        for query, expected_slot in test_cases:
            results = await storage.search_memory(SearchQuery(query=query))
            assert len(results) > 0, f"Should find results for '{query}'"
            assert any(expected_slot in r.slot_name for r in results), (
                f"Should find '{expected_slot}' when searching for '{query}'"
            )

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_cross_session_discovery_workflow(self, temp_dir):
        """Test: Session A saves → Session B searches → Finds content.

        This simulates the real-world scenario of multiple conversation sessions.
        This test would have caught the search index staleness bug.
        """
        # Session A: Save some content
        session_a = StorageManager(memory_dir=temp_dir, shared_dir=str(Path(temp_dir) / "shared"))
        await session_a.save_memory("meeting-notes", "Discussed API authentication strategy")
        await session_a.save_memory("decisions", "Decided to use JWT tokens")

        # Session B: New conversation, should find Session A's content
        session_b = StorageManager(memory_dir=temp_dir, shared_dir=str(Path(temp_dir) / "shared"))
        results = await session_b.search_memory(SearchQuery(query="authentication"))

        assert len(results) > 0, "Session B should find content from Session A"
        assert any("meeting-notes" in r.slot_name for r in results)

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_save_progress_and_query_workflow(self, temp_dir):
        """Test: Save progress → Query with natural language.

        Tests the summarization and query workflow.
        """
        storage = StorageManager(memory_dir=temp_dir, shared_dir=str(Path(temp_dir) / "shared"))

        # Save some content (summary goes into content, not just summary field)
        content = """
        Today we made important decisions about the architecture.
        We chose PostgreSQL over MongoDB because we need strong ACID guarantees.
        The team agreed that REST API is better than GraphQL for our use case.
        """
        await storage.add_summary_entry("architecture-session", content, "Architecture decisions")

        # Should be searchable by content keywords
        # Search for word that appears in both original content and summary
        results = await storage.search_memory(SearchQuery(query="architecture"))
        assert len(results) > 0, "Should find content by keyword in summary"

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_tag_and_filter_workflow(self, temp_dir):
        """Test: Tag slots → Search with tag filters.

        Tests that tagging and filtered search work together.
        """
        storage = StorageManager(memory_dir=temp_dir, shared_dir=str(Path(temp_dir) / "shared"))

        # Create tagged slots
        await storage.save_memory("backend-notes", "Backend API development")
        await storage.add_tag_to_slot("backend-notes", "backend")
        await storage.add_tag_to_slot("backend-notes", "api")

        await storage.save_memory("frontend-notes", "Frontend UI components")
        await storage.add_tag_to_slot("frontend-notes", "frontend")
        await storage.add_tag_to_slot("frontend-notes", "ui")

        # Search with tag filter
        results = await storage.search_memory(SearchQuery(query="api", include_tags=["backend"]))
        assert len(results) > 0
        assert all("backend" in r.tags for r in results if r.tags)

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_list_and_read_workflow(self, temp_dir):
        """Test: Create multiple slots → List them → Read each one.

        Basic discovery workflow.
        """
        storage = StorageManager(memory_dir=temp_dir, shared_dir=str(Path(temp_dir) / "shared"))

        # Create several slots
        slots_created = ["project-a", "project-b", "project-c"]
        for slot_name in slots_created:
            await storage.save_memory(slot_name, f"Content for {slot_name}")

        # List should show all
        all_slots = await storage.list_memory_slots()
        slot_names = [s["name"] for s in all_slots]

        for created in slots_created:
            assert created in slot_names

        # Read each one
        for slot_name in slots_created:
            slot = await storage.read_memory(slot_name)
            assert slot is not None
            assert slot.slot_name == slot_name
            assert len(slot.entries) > 0


class TestConcurrentWorkflows:
    """Test workflows with concurrent operations."""

    @pytest.fixture
    def temp_dir(self):
        """Provide temporary directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_concurrent_saves_searchable(self, temp_dir):
        """Test: Multiple sessions save concurrently → All content searchable.

        Real-world scenario: Multiple Claude sessions working on same project.
        """
        # Create 3 concurrent sessions
        sessions = [StorageManager(memory_dir=temp_dir, shared_dir=str(Path(temp_dir) / "shared")) for _ in range(3)]

        # Concurrent saves with different content
        save_tasks = [
            sessions[0].save_memory("backend", "Backend API development with REST"),
            sessions[1].save_memory("frontend", "Frontend UI built with React"),
            sessions[2].save_memory("database", "Database design using PostgreSQL"),
        ]
        await asyncio.gather(*save_tasks)

        # New session should find all content
        search_session = StorageManager(memory_dir=temp_dir, shared_dir=str(Path(temp_dir) / "shared"))

        # Search for different keywords
        test_searches = [
            ("API", "backend"),
            ("React", "frontend"),
            ("PostgreSQL", "database"),
        ]

        for keyword, expected_slot in test_searches:
            results = await search_session.search_memory(SearchQuery(query=keyword))
            assert len(results) > 0, f"Should find results for '{keyword}'"
            assert any(expected_slot in r.slot_name for r in results), f"Should find '{expected_slot}' for '{keyword}'"

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_save_search_update_search_workflow(self, temp_dir):
        """Test: Save → Search → Update → Search again.

        Tests that updates are reflected in search.
        """
        storage = StorageManager(memory_dir=temp_dir, shared_dir=str(Path(temp_dir) / "shared"))

        # Initial save
        await storage.save_memory("project", "Using MongoDB for database")
        results1 = await storage.search_memory(SearchQuery(query="MongoDB"))
        assert len(results1) > 0
        assert any("project" in r.slot_name for r in results1)

        # Update the content (manual_save replaces all entries)
        await storage.save_memory("project", "Switched to PostgreSQL for database")

        # Should find new content
        results2 = await storage.search_memory(SearchQuery(query="PostgreSQL"))
        assert len(results2) > 0
        assert any("project" in r.slot_name for r in results2)

        # Verify the actual content was replaced
        slot = await storage.read_memory("project")
        assert "PostgreSQL" in slot.entries[0].content
        assert "MongoDB" not in slot.entries[0].content


class TestErrorRecoveryWorkflows:
    """Test workflows with errors and edge cases."""

    @pytest.fixture
    def temp_dir(self):
        """Provide temporary directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_search_empty_database_workflow(self, temp_dir):
        """Test: Search when no slots exist → Graceful handling."""
        storage = StorageManager(memory_dir=temp_dir, shared_dir=str(Path(temp_dir) / "shared"))

        # Search with no content
        results = await storage.search_memory(SearchQuery(query="anything"))

        # Should return empty list, not crash
        assert isinstance(results, list)
        assert len(results) == 0

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_save_empty_content_workflow(self, temp_dir):
        """Test: Save empty content → Proper error."""
        storage = StorageManager(memory_dir=temp_dir, shared_dir=str(Path(temp_dir) / "shared"))

        # Should raise error for empty content
        with pytest.raises(ValueError, match="empty"):
            await storage.save_memory("test", "")

        with pytest.raises(ValueError, match="empty"):
            await storage.save_memory("test", "   ")

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_read_nonexistent_slot_workflow(self, temp_dir):
        """Test: Read slot that doesn't exist → Return None."""
        storage = StorageManager(memory_dir=temp_dir, shared_dir=str(Path(temp_dir) / "shared"))

        result = await storage.read_memory("nonexistent-slot")
        assert result is None

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_tag_operations_workflow(self, temp_dir):
        """Test: Create slot → Add tags → Remove tags → List tags."""
        storage = StorageManager(memory_dir=temp_dir, shared_dir=str(Path(temp_dir) / "shared"))

        # Create slot
        await storage.save_memory("test-slot", "Test content")

        # Add multiple tags
        await storage.add_tag_to_slot("test-slot", "python")
        await storage.add_tag_to_slot("test-slot", "testing")
        await storage.add_tag_to_slot("test-slot", "development")

        # Read slot and verify tags
        slot = await storage.read_memory("test-slot")
        assert len(slot.tags) == 3
        assert "python" in slot.tags

        # Remove a tag
        await storage.remove_tag_from_slot("test-slot", "development")
        slot = await storage.read_memory("test-slot")
        assert len(slot.tags) == 2
        assert "development" not in slot.tags

        # List all tags
        all_tags = await storage.list_all_tags()
        assert "python" in all_tags
        assert "testing" in all_tags


class TestRealWorldScenarios:
    """Test real-world usage scenarios."""

    @pytest.fixture
    def temp_dir(self):
        """Provide temporary directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_multi_project_context_switching(self, temp_dir):
        """Test: Multiple projects → Switch between them → Find content.

        Real scenario: Developer working on multiple projects.
        """
        storage = StorageManager(memory_dir=temp_dir, shared_dir=str(Path(temp_dir) / "shared"))

        # Project A work
        await storage.save_memory("project-a-backend", "Backend uses FastAPI and PostgreSQL")
        await storage.save_memory("project-a-frontend", "Frontend uses React and TypeScript")

        # Project B work
        await storage.save_memory("project-b-api", "GraphQL API with Apollo Server")
        await storage.save_memory("project-b-db", "MongoDB for flexible schema")

        # Search should find content from both projects
        postgres_results = await storage.search_memory(SearchQuery(query="PostgreSQL"))
        assert any("project-a" in r.slot_name for r in postgres_results)

        mongodb_results = await storage.search_memory(SearchQuery(query="MongoDB"))
        assert any("project-b" in r.slot_name for r in mongodb_results)

        # Search for technology should find all relevant projects
        api_results = await storage.search_memory(SearchQuery(query="API"))
        assert len(api_results) >= 2  # Both projects have API

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_decision_tracking_workflow(self, temp_dir):
        """Test: Track decisions over time → Find related decisions.

        Real scenario: Looking back at why certain choices were made.
        """
        storage = StorageManager(memory_dir=temp_dir, shared_dir=str(Path(temp_dir) / "shared"))

        # Save decisions over time
        await storage.save_memory("db-decision", "Decided PostgreSQL over MongoDB due to ACID requirements")
        await storage.add_tag_to_slot("db-decision", "decision")
        await storage.add_tag_to_slot("db-decision", "database")

        await storage.save_memory("api-decision", "Chose REST over GraphQL for simplicity and caching")
        await storage.add_tag_to_slot("api-decision", "decision")
        await storage.add_tag_to_slot("api-decision", "api")

        # Find all decisions
        decision_results = await storage.search_memory(SearchQuery(query="decision", include_tags=["decision"]))
        assert len(decision_results) >= 2

        # Find database-related decisions
        db_decisions = await storage.search_memory(SearchQuery(query="database", include_tags=["decision"]))
        assert len(db_decisions) >= 1
        assert any("db-decision" in r.slot_name for r in db_decisions)

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_long_running_project_workflow(self, temp_dir):
        """Test: Session accumulates content over time → All searchable.

        Real scenario: Long development session with many saves.
        """
        storage = StorageManager(memory_dir=temp_dir, shared_dir=str(Path(temp_dir) / "shared"))

        # Simulate accumulating knowledge over time
        saves = [
            ("day1", "Started project, chose tech stack: Python, FastAPI, PostgreSQL"),
            ("day2", "Implemented user authentication with JWT"),
            ("day3", "Added API endpoints for CRUD operations"),
            ("day4", "Set up CI/CD pipeline with GitHub Actions"),
            ("day5", "Deployed to AWS using Docker containers"),
        ]

        for slot_name, content in saves:
            await storage.save_memory(slot_name, content)
            await asyncio.sleep(0.01)  # Small delay to ensure distinct mtimes

        # Search should find content from any day
        test_searches = [
            ("FastAPI", "day1"),
            ("JWT", "day2"),
            ("API", "day3"),
            ("CI/CD", "day4"),
            ("AWS", "day5"),
        ]

        for keyword, expected_day in test_searches:
            results = await storage.search_memory(SearchQuery(query=keyword))
            assert len(results) > 0, f"Should find content for '{keyword}'"
            assert any(expected_day in r.slot_name for r in results), (
                f"Should find '{expected_day}' when searching '{keyword}'"
            )


class TestCommandInteractions:
    """Test how different commands interact with each other."""

    @pytest.fixture
    def temp_dir(self):
        """Provide temporary directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_list_tags_after_tagging(self, temp_dir):
        """Test: Add tags to slots → List all tags → Verify presence."""
        storage = StorageManager(memory_dir=temp_dir, shared_dir=str(Path(temp_dir) / "shared"))

        # Create slots with tags
        await storage.save_memory("slot1", "Content 1")
        await storage.add_tag_to_slot("slot1", "python")
        await storage.add_tag_to_slot("slot1", "testing")

        await storage.save_memory("slot2", "Content 2")
        await storage.add_tag_to_slot("slot2", "python")
        await storage.add_tag_to_slot("slot2", "development")

        # List tags
        all_tags = await storage.list_all_tags()

        assert "python" in all_tags
        assert "testing" in all_tags
        assert "development" in all_tags

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_use_switch_read_workflow(self, temp_dir):
        """Test: Create slots → Switch between them → Read correct content."""
        storage = StorageManager(memory_dir=temp_dir, shared_dir=str(Path(temp_dir) / "shared"))

        # Create multiple slots
        await storage.save_memory("slot-a", "Content A")
        await storage.save_memory("slot-b", "Content B")

        # Read specific slots
        slot_a = await storage.read_memory("slot-a")
        assert slot_a.entries[0].content == "Content A"

        slot_b = await storage.read_memory("slot-b")
        assert slot_b.entries[0].content == "Content B"

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_save_overwrite_workflow(self, temp_dir):
        """Test: Save → Save again → Content replaced (not appended).

        Validates that manual_save REPLACES content.
        """
        storage = StorageManager(memory_dir=temp_dir, shared_dir=str(Path(temp_dir) / "shared"))

        # First save
        await storage.save_memory("test-slot", "Original content")
        slot1 = await storage.read_memory("test-slot")
        assert len(slot1.entries) == 1

        # Second save
        await storage.save_memory("test-slot", "Updated content")
        slot2 = await storage.read_memory("test-slot")

        # Should have only 1 entry (replaced, not appended)
        assert len(slot2.entries) == 1
        assert slot2.entries[0].content == "Updated content"
        assert slot2.entries[0].content != "Original content"

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_save_progress_appends_workflow(self, temp_dir):
        """Test: Save → Save progress → Content appended.

        Validates that auto_summary APPENDS content.
        """
        storage = StorageManager(memory_dir=temp_dir, shared_dir=str(Path(temp_dir) / "shared"))

        # First save
        await storage.save_memory("session", "Initial discussion about architecture")

        # Add summary
        await storage.add_summary_entry(
            "session", "More discussion about implementation details", "Summary of implementation discussion"
        )

        slot = await storage.read_memory("session")

        # Should have 2 entries (manual_save + auto_summary)
        assert len(slot.entries) == 2
        assert slot.entries[0].type == "manual_save"
        assert slot.entries[1].type == "auto_summary"


class TestEdgeCasesAndRegression:
    """Test edge cases that commonly cause bugs."""

    @pytest.fixture
    def temp_dir(self):
        """Provide temporary directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_special_characters_in_search(self, temp_dir):
        """Test: Content with special characters → Searchable."""
        storage = StorageManager(memory_dir=temp_dir, shared_dir=str(Path(temp_dir) / "shared"))

        await storage.save_memory("special", "Email: user@example.com, URL: https://example.com/api")

        # Should find even with special characters
        results = await storage.search_memory(SearchQuery(query="email"))
        assert len(results) > 0

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_case_insensitive_search_workflow(self, temp_dir):
        """Test: Save with mixed case → Search case-insensitive."""
        storage = StorageManager(memory_dir=temp_dir, shared_dir=str(Path(temp_dir) / "shared"))

        await storage.save_memory("test", "PostgreSQL Database Setup")

        # Different cases should all find it
        for query in ["postgresql", "PostgreSQL", "POSTGRESQL"]:
            results = await storage.search_memory(SearchQuery(query=query))
            assert len(results) > 0, f"Should find with query '{query}'"

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_unicode_content_workflow(self, temp_dir):
        """Test: Unicode content → Save and search work."""
        storage = StorageManager(memory_dir=temp_dir, shared_dir=str(Path(temp_dir) / "shared"))

        # Unicode content
        await storage.save_memory("unicode-test", "Testing with émojis 🎉 and ünîcödé characters")

        # Should save and read correctly
        slot = await storage.read_memory("unicode-test")
        assert "🎉" in slot.entries[0].content
        assert "ünîcödé" in slot.entries[0].content

        # Search should work
        results = await storage.search_memory(SearchQuery(query="unicode"))
        assert len(results) > 0
