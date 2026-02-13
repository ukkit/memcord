"""Text summarization functionality."""

import math
import re
from collections import Counter


class TextSummarizer:
    """Simple extractive text summarizer."""

    def __init__(self):
        # Common stop words for filtering
        self.stop_words = {
            "the", "a", "an", "and", "or", "but", "in", "on", "at", "to",
            "for", "of", "with", "by", "is", "are", "was", "were", "be",
            "been", "being", "have", "has", "had", "do", "does", "did",
            "will", "would", "could", "should", "i", "you", "he", "she",
            "it", "we", "they", "me", "him", "her", "us", "them", "this",
            "that", "these", "those", "my", "your", "his", "its", "our",
            "their",
            # Short common words (visible after removing len>2 filter)
            "so", "no", "if", "as", "up", "am", "go", "not", "all", "can",
            "just", "more", "also", "than", "then", "when", "what", "how",
            "very", "some", "here", "there", "from", "into", "about",
            "which", "each", "other", "much", "such", "only", "own",
            "same", "any", "both", "new", "now",
        }

    def summarize(self, text: str, target_ratio: float = 0.15, compression_ratio: float | None = None) -> str:
        """
        Create an extractive summary of the text.

        Args:
            text: Input text to summarize
            target_ratio: Target length as ratio of original (0.1 = 10%)
            compression_ratio: Alternative name for target_ratio (for backward compatibility)

        Returns:
            Summary text
        """
        # Handle backward compatibility with compression_ratio parameter
        if compression_ratio is not None:
            target_ratio = compression_ratio

        # Validate inputs
        if text is None:
            raise ValueError("Text cannot be None")
        if not isinstance(text, str):
            raise TypeError("Text must be a string")
        if not text.strip():
            raise ValueError("Text cannot be empty")
        if target_ratio <= 0 or target_ratio > 1:
            raise ValueError("Compression ratio must be between 0 and 1")

        # Preprocess chat/code content
        text = self._preprocess_chat_text(text)

        # Split into sentences
        sentences = self._split_into_sentences(text)

        if len(sentences) <= 2:
            # Too short to summarize meaningfully
            return text

        # Score sentences
        sentence_scores = self._score_sentences(sentences)

        # Character-budget targeting
        target_chars = max(50, int(len(text) * target_ratio))

        # Select sentences using MMR with character budget
        selected = self._select_sentences_with_budget(sentences, sentence_scores, target_chars)

        # Reconstruct summary maintaining original order
        summary = self._reconstruct_summary(sentences, selected)

        return summary

    # Known abbreviations that should not trigger sentence splits
    _ABBREVIATIONS = {
        "dr", "mr", "mrs", "ms", "prof", "sr", "jr", "st", "vs",
        "etc", "inc", "ltd", "corp", "dept", "univ", "approx",
    }
    # Two-letter abbreviations like "e.g", "i.e" handled separately
    _ABBREV_PAIRS = {"e.g", "i.e", "u.s", "u.k"}

    def _split_into_sentences(self, text: str) -> list[str]:
        """Split text into sentences with awareness of abbreviations, decimals, and code blocks."""
        text = text.strip()
        if not text:
            return []

        # Protect fenced code blocks with placeholders
        code_blocks: list[str] = []
        def _replace_code_block(m: re.Match) -> str:
            code_blocks.append(m.group(0))
            return f"\x00CODEBLOCK{len(code_blocks) - 1}\x00"

        text = re.sub(r"```[\s\S]*?```", _replace_code_block, text)

        # Split on sentence-ending punctuation followed by whitespace then uppercase
        parts = re.split(r"(?<=[.!?])\s+(?=[A-Z])", text)

        # Merge splits that occurred after known abbreviations
        merged: list[str] = []
        for part in parts:
            if merged and self._is_abbreviation_split(merged[-1]):
                merged[-1] = merged[-1] + " " + part
            else:
                merged.append(part)

        # Merge splits where the period was between digits (e.g. "version 3.5 was released")
        final: list[str] = []
        for part in merged:
            if final and re.search(r"\d\.$", final[-1].rstrip()):
                final[-1] = final[-1] + " " + part
            else:
                final.append(part)

        # Clean up and restore code blocks
        sentences = []
        for s in final:
            s = s.strip()
            if not s:
                continue
            # Restore code block placeholders
            for i, block in enumerate(code_blocks):
                s = s.replace(f"\x00CODEBLOCK{i}\x00", block)
            sentences.append(s)

        # If we only got one sentence, try splitting on newlines
        if len(sentences) <= 1:
            sentences = [s.strip() for s in text.split("\n") if s.strip()]
            # Restore code block placeholders in newline-split results
            restored = []
            for s in sentences:
                for i, block in enumerate(code_blocks):
                    s = s.replace(f"\x00CODEBLOCK{i}\x00", block)
                restored.append(s)
            sentences = restored

        return sentences

    def _is_abbreviation_split(self, text: str) -> bool:
        """Check if text ends with a known abbreviation."""
        text = text.rstrip()
        if not text.endswith("."):
            return False
        # Check two-letter abbreviation pairs like "e.g.", "i.e."
        lower = text.lower()
        for pair in self._ABBREV_PAIRS:
            if lower.endswith(pair + "."):
                return True
        # Check single-word abbreviations
        # Extract the last word before the period
        match = re.search(r"(\w+)\.$", lower)
        if match and match.group(1) in self._ABBREVIATIONS:
            return True
        return False

    # Speaker turn prefixes to strip for scoring but preserve in output
    _SPEAKER_PATTERN = re.compile(r"^(User|Assistant|Human|Claude|System):\s*", re.IGNORECASE)

    def _preprocess_chat_text(self, text: str) -> str:
        """Preprocess chat/code content before sentence splitting."""
        lines = text.split("\n")
        result: list[str] = []
        i = 0
        while i < len(lines):
            line = lines[i]
            stripped = line.strip()

            # Handle fenced code blocks: collapse to summary line
            if stripped.startswith("```"):
                first_line = stripped[3:].strip()  # Language hint or first code line
                # Consume until closing ```
                code_lines = []
                i += 1
                while i < len(lines) and not lines[i].strip().startswith("```"):
                    if not code_lines and lines[i].strip():
                        code_lines.append(lines[i].strip())
                    i += 1
                i += 1  # skip closing ```
                label = first_line or (code_lines[0] if code_lines else "code")
                result.append(f"[Code block: {label}]")
                continue

            # Markdown headers: keep as standalone sentences
            header_match = re.match(r"^(#{1,3})\s+(.+)", stripped)
            if header_match:
                result.append(header_match.group(2).strip())
                i += 1
                continue

            # Strip speaker turn prefixes
            speaker_match = self._SPEAKER_PATTERN.match(stripped)
            if speaker_match:
                stripped = stripped[speaker_match.end():]

            # Consolidate short list items with preceding context
            list_match = re.match(r"^[-*]\s+(.+)$|^(\d+)[.)]\s+(.+)$", stripped)
            if list_match:
                item_text = list_match.group(1) or list_match.group(3)
                if item_text and len(item_text.split()) < 8 and result:
                    # Append short list item to preceding line
                    result[-1] = result[-1].rstrip(".") + "; " + item_text
                    i += 1
                    continue

            if stripped:
                result.append(stripped)
            i += 1

        return "\n".join(result)

    def _score_sentences(self, sentences: list[str]) -> dict[int, float]:
        """Score sentences based on word frequency and position."""
        # Calculate word frequencies
        word_freq = self._calculate_word_frequencies(sentences)

        sentence_scores = {}

        for i, sentence in enumerate(sentences):
            # Word frequency score
            words = self._tokenize(sentence.lower())
            content_words = [w for w in words if w not in self.stop_words]
            freq_score = sum(word_freq.get(word, 0) for word in content_words)
            freq_score = freq_score / len(content_words) if content_words else 0

            # Position score (U-shaped: boost beginning and end)
            position_score = self._calculate_position_score(i, len(sentences))

            # Length score (Gaussian curve centered at 15 words)
            length_score = self._calculate_length_score(sentence)

            # Cue phrase score
            cue_score = self._calculate_cue_score(sentence)

            # Combined score
            total_score = freq_score * 0.4 + position_score * 0.2 + length_score * 0.2 + cue_score * 0.2

            sentence_scores[i] = total_score

        return sentence_scores

    def _calculate_word_frequencies(self, sentences: list[str]) -> dict[str, float]:
        """Calculate normalized word frequencies."""
        word_count: Counter[str] = Counter()

        for sentence in sentences:
            words = self._tokenize(sentence.lower())
            for word in words:
                if word not in self.stop_words:
                    word_count[word] += 1

        # Normalize frequencies
        max_freq = max(word_count.values()) if word_count else 1
        return {word: count / max_freq for word, count in word_count.items()}

    def _tokenize(self, text: str) -> list[str]:
        """Simple word tokenization."""
        # Remove punctuation and split
        text = re.sub(r"[^\w\s]", " ", text)
        return [word.strip() for word in text.split() if word.strip()]

    def _calculate_length_score(self, sentence: str) -> float:
        """Score based on sentence length using Gaussian curve centered at 15 words."""
        length = len(sentence.split())
        return math.exp(-((length - 15) ** 2) / (2 * 10 ** 2))

    def _calculate_position_score(self, index: int, total: int) -> float:
        """U-shaped position score: boost beginning and end, with asymmetry favoring beginnings."""
        if total <= 1:
            return 1.0
        # Normalized position 0..1
        pos = index / (total - 1)
        # Cosine U-shape: high at edges, low in middle
        # cos(pi * pos) goes from 1 -> -1 -> 1; shift and scale to 0.4..1.0 range
        u = math.cos(math.pi * pos)
        # Map [-1, 1] to [0.4, 1.0]
        base = 0.4 + 0.3 * (u + 1.0)
        # Asymmetry: slight boost for earlier positions
        asymmetry = 0.15 * (1.0 - pos)
        return min(1.0, base + asymmetry)

    # Cue phrase categories for scoring
    _CUE_PHRASES = {
        "decided", "concluded", "agreed", "resolved",
        "important", "critical", "essential", "key",
        "result", "outcome",
        "todo", "follow",
        "fixed", "implemented", "deployed", "merged", "committed",
    }
    _CUE_MULTI_PHRASES = [
        "in conclusion", "in summary", "next step", "follow up", "need to",
    ]

    def _calculate_cue_score(self, sentence: str) -> float:
        """Score based on presence of discourse cue phrases."""
        lower = sentence.lower()
        cue_count = 0
        # Check single-word cues
        words = set(self._tokenize(lower))
        cue_count += len(words & self._CUE_PHRASES)
        # Check multi-word cues
        for phrase in self._CUE_MULTI_PHRASES:
            if phrase in lower:
                cue_count += 1
        return min(1.0, cue_count * 0.3)

    @staticmethod
    def _jaccard_similarity(set_a: set, set_b: set) -> float:
        """Calculate Jaccard similarity between two word sets."""
        if not set_a and not set_b:
            return 1.0
        if not set_a or not set_b:
            return 0.0
        intersection = len(set_a & set_b)
        union = len(set_a | set_b)
        return intersection / union if union else 0.0

    def _select_sentences_with_budget(
        self, sentences: list[str], scores: dict[int, float], target_chars: int, lambda_param: float = 0.7
    ) -> list[int]:
        """Select sentences using MMR with character budget."""
        if not sentences:
            return []

        # Precompute word sets for Jaccard similarity
        word_sets = {i: set(self._tokenize(s.lower())) - self.stop_words for i, s in enumerate(sentences)}

        selected: list[int] = []
        selected_chars = 0
        candidates = set(scores.keys())

        while candidates and selected_chars < target_chars:
            best_idx = -1
            best_mmr = -float("inf")

            for idx in candidates:
                relevance = scores[idx]

                # Max similarity to already-selected sentences
                if selected:
                    max_sim = max(self._jaccard_similarity(word_sets[idx], word_sets[s]) for s in selected)
                else:
                    max_sim = 0.0

                mmr = lambda_param * relevance - (1 - lambda_param) * max_sim

                if mmr > best_mmr:
                    best_mmr = mmr
                    best_idx = idx

            if best_idx < 0:
                break

            selected.append(best_idx)
            selected_chars += len(sentences[best_idx])
            candidates.discard(best_idx)

        # Always select at least 1 sentence
        if not selected and scores:
            best = max(scores, key=lambda i: scores[i])
            selected.append(best)

        return selected

    def _reconstruct_summary(self, original_sentences: list[str], selected_indices: list[int]) -> str:
        """Reconstruct summary maintaining original sentence order."""
        # Sort selected indices to maintain original order
        selected_indices.sort()

        summary_sentences = [original_sentences[i] for i in selected_indices]

        # Join sentences with space; only add period if sentence doesn't already end with punctuation
        parts = []
        for s in summary_sentences:
            s = s.strip()
            if parts and not s[0:1].isupper():
                # Lowercase continuation — join with space
                parts.append(s)
            else:
                parts.append(s)

        summary = " ".join(parts)

        # Clean up double periods / whitespace
        summary = re.sub(r"\.\s*\.", ".", summary)
        summary = summary.strip()

        # Ensure proper ending
        if summary and not summary.endswith((".", "!", "?")):
            summary += "."

        return summary

    def get_summary_stats(self, original: str, summary: str) -> dict[str, int | float]:
        """Get statistics about the summarization."""
        # Validate inputs
        if not isinstance(original, str):
            raise TypeError("Original text must be a string")
        if not isinstance(summary, str):
            raise TypeError("Summary text must be a string")

        return {
            "original_length": len(original),
            "summary_length": len(summary),
            "original_words": len(original.split()),
            "summary_words": len(summary.split()),
            "words_original": len(original.split()),  # Alternative name for backward compatibility
            "words_summary": len(summary.split()),  # Alternative name for backward compatibility
            "compression_ratio": len(summary) / len(original) if original else 0.0,
        }
