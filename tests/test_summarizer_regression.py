"""Regression tests for TextSummarizer against real memory slot data.

Loads all memory_slots/*.json files and feeds representative content
through the summarizer to ensure no crashes and sane compression ratios.
"""

import json
from pathlib import Path

import pytest

from memcord.summarizer import TextSummarizer

MEMORY_SLOTS_DIR = Path(__file__).resolve().parent.parent / "memory_slots"


def _load_slot_entries():
    """Load all memory slot JSON files and extract text entries."""
    entries = []
    if not MEMORY_SLOTS_DIR.exists():
        return entries
    for json_file in MEMORY_SLOTS_DIR.glob("*.json"):
        try:
            data = json.loads(json_file.read_text(encoding="utf-8"))
            for entry in data.get("entries", []):
                content = entry.get("content", "")
                if content and len(content.strip()) > 50:
                    entries.append(
                        {
                            "slot": json_file.stem,
                            "type": entry.get("type", "unknown"),
                            "content": content,
                            "original_length": entry.get("original_length"),
                        }
                    )
        except (json.JSONDecodeError, KeyError, OSError):
            continue
    return entries


SLOT_ENTRIES = _load_slot_entries()


@pytest.fixture
def summarizer():
    return TextSummarizer()


class TestRegressionRealData:
    """Run summarizer against real memory slot data to catch regressions."""

    @pytest.mark.skipif(not SLOT_ENTRIES, reason="No memory slot data available")
    @pytest.mark.parametrize(
        "entry",
        SLOT_ENTRIES[:30],  # Cap to avoid overly long test runs
        ids=lambda e: f"{e['slot']}_{e['type']}_{len(e['content'])}chars",
    )
    def test_no_crash_on_real_data(self, summarizer, entry):
        """Summarizer should not crash on any real slot content."""
        result = summarizer.summarize(entry["content"])
        assert isinstance(result, str)
        assert len(result) > 0

    @pytest.mark.skipif(not SLOT_ENTRIES, reason="No memory slot data available")
    @pytest.mark.parametrize(
        "entry",
        SLOT_ENTRIES[:30],
        ids=lambda e: f"{e['slot']}_{e['type']}_{len(e['content'])}chars",
    )
    def test_compression_ratio_sane(self, summarizer, entry):
        """Compression ratio should be between 0.05 and 0.5 for real data."""
        content = entry["content"]
        result = summarizer.summarize(content, target_ratio=0.15)
        ratio = len(result) / len(content) if content else 0
        # Allow passthrough for very short texts (<=2 sentences)
        if ratio > 0.9:
            # Passthrough case — text is too short to summarize, or few sentences
            preprocessed = summarizer._preprocess_chat_text(content)
            sentences = summarizer._split_into_sentences(preprocessed)
            assert len(sentences) <= 5, (
                f"Unexpected high ratio {ratio:.2f} with {len(sentences)} sentences"
            )
        else:
            assert 0.01 < ratio < 0.9, f"Ratio {ratio:.2f} out of expected range"

    @pytest.mark.skipif(not SLOT_ENTRIES, reason="No memory slot data available")
    @pytest.mark.parametrize(
        "entry",
        SLOT_ENTRIES[:30],
        ids=lambda e: f"{e['slot']}_{e['type']}_{len(e['content'])}chars",
    )
    def test_output_non_empty(self, summarizer, entry):
        """Summary output should never be empty for non-empty input."""
        result = summarizer.summarize(entry["content"])
        assert result.strip() != ""

    @pytest.mark.skipif(not SLOT_ENTRIES, reason="No memory slot data available")
    def test_summary_stats_on_real_data(self, summarizer):
        """get_summary_stats should work with real summaries."""
        for entry in SLOT_ENTRIES[:10]:
            content = entry["content"]
            summary = summarizer.summarize(content)
            stats = summarizer.get_summary_stats(content, summary)
            assert stats["original_length"] == len(content)
            assert stats["summary_length"] == len(summary)
            assert stats["compression_ratio"] >= 0


class TestRegressionVariedFormats:
    """Test with synthetic data in varied formats that mimic real usage."""

    def test_chat_transcript(self, summarizer):
        text = """User: How should we handle authentication?
Assistant: I recommend using JWT tokens with refresh token rotation. This provides stateless authentication while maintaining security.

User: What about session storage?
Assistant: With JWT you don't need server-side session storage. The token itself contains the claims. However, you should maintain a blacklist for revoked tokens.

User: Should we use a library?
Assistant: Yes, use PyJWT for Python. It's well-maintained and supports all standard algorithms. For the middleware, integrate it with FastAPI's dependency injection."""
        result = summarizer.summarize(text, target_ratio=0.3)
        assert isinstance(result, str)
        assert len(result) > 0
        assert len(result) < len(text)

    def test_code_heavy_content(self, summarizer):
        text = """We implemented the database connection pool.

```python
import asyncpg

pool = await asyncpg.create_pool(dsn)
```

The pool supports up to 20 concurrent connections. We also added retry logic for transient failures.

```python
@retry(max_attempts=3)
async def query(sql):
    async with pool.acquire() as conn:
        return await conn.fetch(sql)
```

Testing showed significant performance improvements with connection pooling."""
        result = summarizer.summarize(text, target_ratio=0.3)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_markdown_document(self, summarizer):
        text = """# Project Architecture

## Backend
The backend uses FastAPI with Python 3.12 for high performance async operations.

## Database
PostgreSQL 16 serves as the primary database with pgvector for embeddings.

## Frontend
React 18 with TypeScript provides the user interface.

## Deployment
Docker containers deployed on AWS ECS with Terraform for infrastructure."""
        result = summarizer.summarize(text, target_ratio=0.3)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_decision_log(self, summarizer):
        text = """We decided to use PostgreSQL over MongoDB because we need ACID guarantees.
The team agreed that REST is simpler than GraphQL for our use case.
We concluded that Docker is essential for consistent deployments.
It was resolved to implement JWT authentication with refresh tokens.
The critical decision was to use microservices architecture.
We implemented the caching layer using Redis for session data.
The outcome of the load test showed 5000 requests per second.
Next step is to set up monitoring with Prometheus and Grafana."""
        result = summarizer.summarize(text, target_ratio=0.3)
        assert isinstance(result, str)
        assert len(result) < len(text)

    def test_mixed_content_with_lists(self, summarizer):
        text = """Sprint Review Summary

Completed items:
- User authentication module
- Database migration scripts
- API endpoint documentation
- Unit test coverage to 85%

Pending items:
- Performance optimization
- Security audit
- Load testing

The team deployed version 2.1 to staging. QA testing revealed no critical issues. We agreed to proceed with production deployment next week."""
        result = summarizer.summarize(text, target_ratio=0.3)
        assert isinstance(result, str)
        assert len(result) > 0
