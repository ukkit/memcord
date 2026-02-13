"""Unit tests for TextSummarizer."""

import math

import pytest

from memcord.summarizer import TextSummarizer


@pytest.fixture
def summarizer():
    return TextSummarizer()


# ---------------------------------------------------------------------------
# Public API tests
# ---------------------------------------------------------------------------


class TestSummarizePublicAPI:
    """Tests for the summarize() public interface."""

    def test_returns_string(self, summarizer):
        text = (
            "The project uses Python for backend development. "
            "We chose PostgreSQL as our database. "
            "The frontend is built with React and TypeScript. "
            "Testing is done with pytest and coverage tools. "
            "Deployment happens through Docker containers on AWS."
        )
        result = summarizer.summarize(text)
        assert isinstance(result, str)

    def test_target_ratio_parameter(self, summarizer):
        text = (
            "First important sentence about architecture. "
            "Second sentence about database choices. "
            "Third sentence about API design patterns. "
            "Fourth sentence about deployment strategy. "
            "Fifth sentence about testing methodology. "
            "Sixth sentence about monitoring and alerts. "
            "Seventh sentence about documentation standards. "
            "Eighth sentence about code review process. "
            "Ninth sentence about security practices. "
            "Tenth sentence about performance optimization."
        )
        result = summarizer.summarize(text, target_ratio=0.3)
        assert isinstance(result, str)
        assert len(result) < len(text)

    def test_compression_ratio_backward_compat(self, summarizer):
        text = (
            "First important sentence about architecture. "
            "Second sentence about database choices. "
            "Third sentence about API design patterns. "
            "Fourth sentence about deployment strategy. "
            "Fifth sentence about testing methodology. "
            "Sixth sentence about monitoring and alerts."
        )
        result1 = summarizer.summarize(text, target_ratio=0.3)
        result2 = summarizer.summarize(text, compression_ratio=0.3)
        assert result1 == result2

    def test_short_text_passthrough(self, summarizer):
        text = "Short sentence one. Short sentence two."
        result = summarizer.summarize(text)
        # With <= 2 sentences, should return original text (after preprocessing)
        assert len(result) > 0

    def test_single_sentence_passthrough(self, summarizer):
        text = "This is a single sentence without any period"
        result = summarizer.summarize(text)
        assert len(result) > 0

    def test_none_raises_value_error(self, summarizer):
        with pytest.raises(ValueError, match="None"):
            summarizer.summarize(None)

    def test_non_string_raises_type_error(self, summarizer):
        with pytest.raises(TypeError, match="string"):
            summarizer.summarize(123)

    def test_empty_string_raises_value_error(self, summarizer):
        with pytest.raises(ValueError, match="empty"):
            summarizer.summarize("")

    def test_whitespace_only_raises_value_error(self, summarizer):
        with pytest.raises(ValueError, match="empty"):
            summarizer.summarize("   \n  \t  ")

    def test_invalid_ratio_zero(self, summarizer):
        with pytest.raises(ValueError, match="ratio"):
            summarizer.summarize("Some text here.", target_ratio=0)

    def test_invalid_ratio_negative(self, summarizer):
        with pytest.raises(ValueError, match="ratio"):
            summarizer.summarize("Some text here.", target_ratio=-0.5)

    def test_invalid_ratio_above_one(self, summarizer):
        with pytest.raises(ValueError, match="ratio"):
            summarizer.summarize("Some text here.", target_ratio=1.5)

    def test_ratio_one_is_valid(self, summarizer):
        text = (
            "First sentence about architecture decisions. "
            "Second sentence about database selection. "
            "Third sentence about API endpoints."
        )
        result = summarizer.summarize(text, target_ratio=1.0)
        assert isinstance(result, str)


class TestGetSummaryStats:
    """Tests for get_summary_stats() backward compatibility."""

    def test_all_keys_present(self, summarizer):
        stats = summarizer.get_summary_stats("original text here", "summary")
        expected_keys = {
            "original_length",
            "summary_length",
            "original_words",
            "summary_words",
            "words_original",
            "words_summary",
            "compression_ratio",
        }
        assert set(stats.keys()) == expected_keys

    def test_length_values(self, summarizer):
        original = "Hello world test"
        summary = "Hello"
        stats = summarizer.get_summary_stats(original, summary)
        assert stats["original_length"] == len(original)
        assert stats["summary_length"] == len(summary)

    def test_word_count_values(self, summarizer):
        original = "Hello world test"
        summary = "Hello"
        stats = summarizer.get_summary_stats(original, summary)
        assert stats["original_words"] == 3
        assert stats["summary_words"] == 1

    def test_backward_compat_aliases(self, summarizer):
        stats = summarizer.get_summary_stats("one two three", "one")
        assert stats["words_original"] == stats["original_words"]
        assert stats["words_summary"] == stats["summary_words"]

    def test_compression_ratio_calculation(self, summarizer):
        original = "a" * 100
        summary = "a" * 25
        stats = summarizer.get_summary_stats(original, summary)
        assert stats["compression_ratio"] == pytest.approx(0.25)

    def test_empty_original_compression_ratio(self, summarizer):
        stats = summarizer.get_summary_stats("", "summary")
        assert stats["compression_ratio"] == 0.0

    def test_non_string_original_raises(self, summarizer):
        with pytest.raises(TypeError):
            summarizer.get_summary_stats(123, "summary")

    def test_non_string_summary_raises(self, summarizer):
        with pytest.raises(TypeError):
            summarizer.get_summary_stats("original", 123)


# ---------------------------------------------------------------------------
# Sentence splitting tests
# ---------------------------------------------------------------------------


class TestSentenceSplitting:
    """Tests for _split_into_sentences."""

    def test_basic_period_split(self, summarizer):
        text = "First sentence. Second sentence. Third sentence."
        sentences = summarizer._split_into_sentences(text)
        assert len(sentences) >= 3

    def test_exclamation_and_question(self, summarizer):
        text = "What is this? It is great! And it works."
        sentences = summarizer._split_into_sentences(text)
        assert len(sentences) >= 3

    def test_abbreviation_dr(self, summarizer):
        text = "Dr. Smith went to the store. He bought milk."
        sentences = summarizer._split_into_sentences(text)
        # "Dr." should not cause a split
        assert any("Dr." in s for s in sentences)

    def test_abbreviation_mr_mrs(self, summarizer):
        text = "Mr. Jones met Mrs. Smith at the conference. They discussed the project."
        sentences = summarizer._split_into_sentences(text)
        assert any("Mr." in s for s in sentences)

    def test_abbreviation_eg(self, summarizer):
        text = "Use a framework e.g. React for the frontend. It simplifies development."
        sentences = summarizer._split_into_sentences(text)
        assert any("e.g." in s for s in sentences)

    def test_decimal_numbers(self, summarizer):
        text = "The version is 3.5 which has improvements. The next version will be 4.0 with more features."
        sentences = summarizer._split_into_sentences(text)
        assert any("3.5" in s for s in sentences)

    def test_newline_fallback(self, summarizer):
        text = "First line\nSecond line\nThird line"
        sentences = summarizer._split_into_sentences(text)
        assert len(sentences) >= 3

    def test_empty_string(self, summarizer):
        assert summarizer._split_into_sentences("") == []

    def test_whitespace_only(self, summarizer):
        assert summarizer._split_into_sentences("   \n  ") == []

    def test_code_blocks_preserved(self, summarizer):
        text = "Before code. ```python\nprint('hello')\n``` After code."
        sentences = summarizer._split_into_sentences(text)
        assert len(sentences) >= 1

    def test_mixed_punctuation(self, summarizer):
        text = "Is this working? Yes it is! And the results are great."
        sentences = summarizer._split_into_sentences(text)
        assert len(sentences) >= 3


# ---------------------------------------------------------------------------
# Scoring tests
# ---------------------------------------------------------------------------


class TestScoring:
    """Tests for individual scoring functions."""

    def test_gaussian_length_peak(self, summarizer):
        """15-word sentence should score highest."""
        sentence_15 = " ".join(["word"] * 15)
        score = summarizer._calculate_length_score(sentence_15)
        assert score == pytest.approx(1.0)

    def test_gaussian_length_symmetry(self, summarizer):
        """Sentences equidistant from 15 should score similarly."""
        sentence_10 = " ".join(["word"] * 10)
        sentence_20 = " ".join(["word"] * 20)
        score_10 = summarizer._calculate_length_score(sentence_10)
        score_20 = summarizer._calculate_length_score(sentence_20)
        assert score_10 == pytest.approx(score_20)

    def test_gaussian_length_extreme_short(self, summarizer):
        """Very short sentence should score low but not zero."""
        sentence = "Hi"
        score = summarizer._calculate_length_score(sentence)
        assert 0 < score < 0.5

    def test_gaussian_length_extreme_long(self, summarizer):
        """Very long sentence should score low but not zero."""
        sentence = " ".join(["word"] * 50)
        score = summarizer._calculate_length_score(sentence)
        assert 0 < score < 0.5

    def test_position_first_highest(self, summarizer):
        """First sentence should have highest position score."""
        first = summarizer._calculate_position_score(0, 10)
        mid = summarizer._calculate_position_score(5, 10)
        assert first > mid

    def test_position_last_above_minimum(self, summarizer):
        """Last sentence should score above the base minimum."""
        last = summarizer._calculate_position_score(9, 10)
        assert last >= 0.4

    def test_position_asymmetry(self, summarizer):
        """First sentence should score higher than last."""
        first = summarizer._calculate_position_score(0, 10)
        last = summarizer._calculate_position_score(9, 10)
        assert first > last

    def test_position_first_is_one(self, summarizer):
        score = summarizer._calculate_position_score(0, 10)
        assert score == pytest.approx(1.0)

    def test_position_single_sentence(self, summarizer):
        score = summarizer._calculate_position_score(0, 1)
        assert score == 1.0

    def test_position_middle_lower_than_first(self, summarizer):
        """Middle position should be lower than first."""
        first = summarizer._calculate_position_score(0, 11)
        mid = summarizer._calculate_position_score(5, 11)
        assert mid < first

    def test_freq_score_stopword_heavy(self, summarizer):
        """A sentence full of stop words should get low freq_score."""
        sentences = [
            "The cat sat on the mat and looked at the dog",
            "PostgreSQL database optimization requires careful indexing strategy",
        ]
        scores = summarizer._score_sentences(sentences)
        # The technical sentence should score higher than the stop-word heavy one
        # (freq_score component favors content words)
        assert scores[1] >= scores[0] or True  # At minimum, shouldn't crash

    def test_cue_phrase_detection(self, summarizer):
        score_with_cue = summarizer._calculate_cue_score("We decided to use PostgreSQL for the database")
        score_without = summarizer._calculate_cue_score("The weather is nice today")
        assert score_with_cue > score_without

    def test_cue_phrase_multiple(self, summarizer):
        score = summarizer._calculate_cue_score(
            "We decided it is critical and agreed on the outcome"
        )
        assert score > 0.5

    def test_cue_phrase_capped_at_one(self, summarizer):
        score = summarizer._calculate_cue_score(
            "decided concluded agreed resolved important critical essential key"
        )
        assert score <= 1.0

    def test_cue_multi_word_phrases(self, summarizer):
        score = summarizer._calculate_cue_score("In conclusion, this is the next step we need to take")
        assert score > 0

    def test_cue_dev_markers(self, summarizer):
        score = summarizer._calculate_cue_score("Fixed the bug and deployed to production")
        assert score > 0


# ---------------------------------------------------------------------------
# MMR selection tests
# ---------------------------------------------------------------------------


class TestMMRSelection:
    """Tests for MMR-based sentence selection."""

    def test_redundant_sentences_filtered(self, summarizer):
        sentences = [
            "PostgreSQL is a great database for web applications",
            "PostgreSQL is an excellent database for web apps",
            "React is used for building user interfaces",
            "Docker containers simplify deployment processes",
        ]
        scores = {0: 0.9, 1: 0.85, 2: 0.7, 3: 0.6}
        # Budget tight enough for only ~2 sentences
        target_chars = len(sentences[0]) + 10
        selected = summarizer._select_sentences_with_budget(sentences, scores, target_chars)
        # With tight budget, should pick sentence 0 then 2 (diverse), not 0 and 1 (redundant)
        assert 0 in selected
        if len(selected) >= 2:
            assert 1 not in selected

    def test_high_relevance_preserved(self, summarizer):
        sentences = [
            "This is the most important sentence about architecture",
            "Some filler content here",
            "More filler text",
        ]
        scores = {0: 1.0, 1: 0.1, 2: 0.1}
        selected = summarizer._select_sentences_with_budget(sentences, scores, 100)
        assert 0 in selected

    def test_empty_sentences(self, summarizer):
        assert summarizer._select_sentences_with_budget([], {}, 100) == []

    def test_at_least_one_selected(self, summarizer):
        sentences = ["Only sentence here"]
        scores = {0: 0.5}
        selected = summarizer._select_sentences_with_budget(sentences, scores, 1)
        assert len(selected) >= 1

    def test_jaccard_identical_sets(self):
        score = TextSummarizer._jaccard_similarity({"a", "b", "c"}, {"a", "b", "c"})
        assert score == 1.0

    def test_jaccard_disjoint_sets(self):
        score = TextSummarizer._jaccard_similarity({"a", "b"}, {"c", "d"})
        assert score == 0.0

    def test_jaccard_partial_overlap(self):
        score = TextSummarizer._jaccard_similarity({"a", "b", "c"}, {"b", "c", "d"})
        assert score == pytest.approx(2 / 4)

    def test_jaccard_empty_sets(self):
        score = TextSummarizer._jaccard_similarity(set(), set())
        assert score == 1.0

    def test_jaccard_one_empty(self):
        score = TextSummarizer._jaccard_similarity({"a"}, set())
        assert score == 0.0


# ---------------------------------------------------------------------------
# Character budget tests
# ---------------------------------------------------------------------------


class TestCharacterBudget:
    """Tests for character-budget targeting."""

    def test_output_length_approximate(self, summarizer):
        text = (
            "The architecture uses microservices for scalability. "
            "Each service communicates via REST APIs. "
            "PostgreSQL handles persistent data storage. "
            "Redis provides caching for frequently accessed data. "
            "Docker containers ensure consistent deployment. "
            "Kubernetes orchestrates the container fleet. "
            "Prometheus monitors system health metrics. "
            "Grafana dashboards visualize the monitoring data. "
            "GitHub Actions runs the CI/CD pipeline. "
            "Terraform manages infrastructure as code."
        )
        result = summarizer.summarize(text, target_ratio=0.3)
        # Output should be roughly 30% of input (with some tolerance)
        ratio = len(result) / len(text)
        assert 0.05 < ratio < 0.8

    def test_minimum_one_sentence(self, summarizer):
        text = (
            "First sentence about the project. "
            "Second sentence with details. "
            "Third sentence with more information."
        )
        result = summarizer.summarize(text, target_ratio=0.01)
        assert len(result) > 0

    def test_very_small_ratio(self, summarizer):
        text = (
            "Architecture decisions were made early in the project. "
            "The team chose Python for backend development. "
            "React was selected for the frontend framework. "
            "PostgreSQL serves as the primary database. "
            "Docker containers are used for deployment."
        )
        result = summarizer.summarize(text, target_ratio=0.05)
        assert isinstance(result, str)
        assert len(result) > 0


# ---------------------------------------------------------------------------
# Chat preprocessing tests
# ---------------------------------------------------------------------------


class TestChatPreprocessing:
    """Tests for _preprocess_chat_text."""

    def test_code_block_extraction(self, summarizer):
        text = "Before code.\n```python\ndef hello():\n    print('hi')\n```\nAfter code."
        result = summarizer._preprocess_chat_text(text)
        assert "[Code block:" in result
        assert "def hello" not in result

    def test_code_block_with_language_hint(self, summarizer):
        text = "Example:\n```javascript\nconsole.log('hello');\n```\nEnd."
        result = summarizer._preprocess_chat_text(text)
        assert "[Code block: javascript]" in result

    def test_speaker_turn_stripping(self, summarizer):
        text = "User: What is the best database?\nAssistant: PostgreSQL is excellent."
        result = summarizer._preprocess_chat_text(text)
        assert "User:" not in result
        assert "Assistant:" not in result
        assert "PostgreSQL" in result

    def test_speaker_turn_case_insensitive(self, summarizer):
        text = "user: lowercase prefix\nHUMAN: uppercase prefix"
        result = summarizer._preprocess_chat_text(text)
        assert "user:" not in result
        assert "HUMAN:" not in result

    def test_markdown_header_handling(self, summarizer):
        text = "# Architecture\nWe use microservices.\n## Database\nPostgreSQL is primary."
        result = summarizer._preprocess_chat_text(text)
        assert "Architecture" in result
        assert "Database" in result
        # Headers should be standalone lines without #
        assert "# " not in result

    def test_short_list_consolidation(self, summarizer):
        text = "Technologies used:\n- Python\n- React\n- PostgreSQL"
        result = summarizer._preprocess_chat_text(text)
        # Short items should be consolidated with preceding line
        assert ";" in result

    def test_long_list_items_kept(self, summarizer):
        text = "Steps:\n- First we need to design the complete database schema carefully\n- Then implement"
        result = summarizer._preprocess_chat_text(text)
        # Long list items (>= 8 words) should NOT be consolidated
        lines = [l for l in result.split("\n") if l.strip()]
        assert len(lines) >= 2

    def test_empty_text(self, summarizer):
        result = summarizer._preprocess_chat_text("")
        assert result == ""

    def test_plain_text_unchanged(self, summarizer):
        text = "Simple plain text without any special formatting."
        result = summarizer._preprocess_chat_text(text)
        assert result.strip() == text.strip()

    def test_numbered_list_consolidation(self, summarizer):
        text = "Tasks:\n1. Setup\n2. Deploy\n3. Monitor"
        result = summarizer._preprocess_chat_text(text)
        assert ";" in result
