"""Tests for pluggable summarizer backends and the summarizer factory."""

import os
from unittest.mock import patch

import pytest

from memcord.models import SlotConfig
from memcord.summarizer import NLTKSummarizer
from memcord.summarizer_base import BaseSummarizer
from memcord.summarizer_factory import build_summarizer

SAMPLE_TEXT = (
    "We decided to use Python for the backend API. "
    "The database layer will use PostgreSQL with async drivers. "
    "React was chosen for the frontend because of its ecosystem. "
    "We agreed to write integration tests for every new endpoint. "
    "The deployment pipeline runs on GitHub Actions and pushes to AWS ECS. "
    "Security scanning is done with Bandit and Trivy on every PR. "
    "The team resolved to do code reviews within one business day. "
    "Performance benchmarks will be tracked in CI to catch regressions early."
)


# ---------------------------------------------------------------------------
# BaseSummarizer contract
# ---------------------------------------------------------------------------


class TestBaseSummarizerContract:
    """BaseSummarizer is abstract — concrete subclasses must satisfy the contract."""

    def test_cannot_instantiate_directly(self):
        with pytest.raises(TypeError):
            BaseSummarizer()  # type: ignore[abstract]

    def test_get_summary_stats_base_impl(self):
        """get_summary_stats on BaseSummarizer returns expected keys."""

        class MinimalSummarizer(BaseSummarizer):
            async def summarize(self, text: str, target_ratio: float = 0.15) -> str:
                return text[:10]

        s = MinimalSummarizer()
        stats = s.get_summary_stats("hello world test", "hello")
        assert "original_length" in stats
        assert "summary_length" in stats
        assert "compression_ratio" in stats
        assert stats["original_length"] == len("hello world test")
        assert stats["compression_ratio"] == pytest.approx(len("hello") / len("hello world test"))


# ---------------------------------------------------------------------------
# NLTKSummarizer adapter
# ---------------------------------------------------------------------------


class TestNLTKSummarizer:
    def test_is_base_summarizer(self):
        assert isinstance(NLTKSummarizer(), BaseSummarizer)

    @pytest.mark.asyncio
    async def test_summarize_returns_string(self):
        s = NLTKSummarizer()
        result = await s.summarize(SAMPLE_TEXT, target_ratio=0.3)
        assert isinstance(result, str)
        assert result.strip()

    @pytest.mark.asyncio
    async def test_summarize_shorter_than_original(self):
        s = NLTKSummarizer()
        result = await s.summarize(SAMPLE_TEXT, target_ratio=0.2)
        assert len(result) <= len(SAMPLE_TEXT)

    def test_get_summary_stats_returns_expected_keys(self):
        s = NLTKSummarizer()
        stats = s.get_summary_stats(SAMPLE_TEXT, "short summary.")
        for key in ("original_length", "summary_length", "compression_ratio"):
            assert key in stats


# ---------------------------------------------------------------------------
# SumySummarizer (conditionally skip if sumy not installed)
# ---------------------------------------------------------------------------


@pytest.mark.skipif(
    not pytest.importorskip("sumy", reason="sumy not installed"),
    reason="sumy not installed",
)
class TestSumySummarizer:
    def test_import_succeeds(self):
        from memcord.llm_summarizer import SumySummarizer  # noqa: F401

    def test_is_base_summarizer(self):
        from memcord.llm_summarizer import SumySummarizer

        assert isinstance(SumySummarizer(), BaseSummarizer)

    @pytest.mark.asyncio
    async def test_lexrank_summarizes(self):
        from memcord.llm_summarizer import SumySummarizer

        s = SumySummarizer(algorithm="lexrank")
        result = await s.summarize(SAMPLE_TEXT, target_ratio=0.3)
        assert isinstance(result, str)
        assert result.strip()

    @pytest.mark.asyncio
    async def test_lsa_summarizes(self):
        from memcord.llm_summarizer import SumySummarizer

        s = SumySummarizer(algorithm="lsa")
        result = await s.summarize(SAMPLE_TEXT, target_ratio=0.3)
        assert isinstance(result, str)
        assert result.strip()

    @pytest.mark.asyncio
    async def test_empty_text_raises(self):
        from memcord.llm_summarizer import SumySummarizer

        s = SumySummarizer()
        with pytest.raises(ValueError):
            await s.summarize("", target_ratio=0.3)

    @pytest.mark.asyncio
    async def test_invalid_ratio_raises(self):
        from memcord.llm_summarizer import SumySummarizer

        s = SumySummarizer()
        with pytest.raises(ValueError):
            await s.summarize(SAMPLE_TEXT, target_ratio=0.0)

    @pytest.mark.asyncio
    async def test_short_text_returns_something(self):
        from memcord.llm_summarizer import SumySummarizer

        s = SumySummarizer()
        result = await s.summarize("One sentence only.", target_ratio=0.5)
        assert isinstance(result, str)
        assert result.strip()


# ---------------------------------------------------------------------------
# SemanticSummarizer (skip if sentence-transformers not installed)
# ---------------------------------------------------------------------------


@pytest.mark.skipif(
    not pytest.importorskip("sentence_transformers", reason="sentence-transformers not installed"),
    reason="sentence-transformers not installed",
)
class TestSemanticSummarizer:
    @pytest.mark.asyncio
    async def test_summarizes(self):
        from memcord.llm_summarizer import SemanticSummarizer

        s = SemanticSummarizer()
        result = await s.summarize(SAMPLE_TEXT, target_ratio=0.3)
        assert isinstance(result, str)
        assert result.strip()

    @pytest.mark.asyncio
    async def test_empty_text_raises(self):
        from memcord.llm_summarizer import SemanticSummarizer

        s = SemanticSummarizer()
        with pytest.raises(ValueError):
            await s.summarize("", target_ratio=0.3)


# ---------------------------------------------------------------------------
# Summarizer factory
# ---------------------------------------------------------------------------


class TestBuildSummarizer:
    def test_nltk_backend(self):
        config = SlotConfig(summarizer_backend="nltk")
        s = build_summarizer(config)
        assert isinstance(s, NLTKSummarizer)

    def test_sumy_backend_returns_sumy_or_fallback(self):
        config = SlotConfig(summarizer_backend="sumy")
        s = build_summarizer(config)
        assert isinstance(s, BaseSummarizer)

    def test_unknown_backend_falls_back(self):
        config = SlotConfig(summarizer_backend="nonexistent_xyz")
        # Should not raise — falls back gracefully
        s = build_summarizer(config)
        assert isinstance(s, BaseSummarizer)

    def test_env_var_overrides_config(self):
        """MEMCORD_SUMMARIZER env var overrides per-slot config."""
        config = SlotConfig(summarizer_backend="sumy")
        with patch.dict(os.environ, {"MEMCORD_SUMMARIZER": "nltk"}):
            s = build_summarizer(config)
        assert isinstance(s, NLTKSummarizer)

    def test_env_var_empty_uses_config(self):
        """Empty MEMCORD_SUMMARIZER falls through to per-slot config."""
        config = SlotConfig(summarizer_backend="nltk")
        with patch.dict(os.environ, {"MEMCORD_SUMMARIZER": ""}):
            s = build_summarizer(config)
        assert isinstance(s, NLTKSummarizer)

    def test_sumy_algorithm_passed(self):
        """SlotConfig.sumy_algorithm is forwarded to SumySummarizer."""
        try:
            from memcord.llm_summarizer import SumySummarizer
        except ImportError:
            pytest.skip("sumy not installed")

        config = SlotConfig(summarizer_backend="sumy", sumy_algorithm="lsa")
        s = build_summarizer(config)
        if isinstance(s, SumySummarizer):
            assert s.algorithm == "lsa"

    def test_invalid_backend_import_falls_back_to_sumy_then_nltk(self):
        """If a backend raises ImportError, factory falls back through sumy → nltk."""
        config = SlotConfig(summarizer_backend="transformers")

        with patch("memcord.summarizer_factory._create") as mock_create:
            call_count = 0

            def side_effect(backend, cfg):
                nonlocal call_count
                call_count += 1
                if backend in ("transformers", "sumy"):
                    raise ImportError("not installed")
                # Allow nltk
                from memcord.summarizer import NLTKSummarizer

                return NLTKSummarizer()

            mock_create.side_effect = side_effect
            s = build_summarizer(config)

        assert isinstance(s, NLTKSummarizer)
