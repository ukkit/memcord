"""Shared constants used across the memcord package."""

# Minimal stop words used for search indexing.
# Kept small intentionally so that common technical terms (can, this, that …)
# remain searchable in the inverted index.
STOP_WORDS_INDEX: frozenset[str] = frozenset(
    {
        "the", "a", "an", "and", "or", "but",
        "in", "on", "at", "to", "for", "of", "with", "by",
        "is", "are", "was", "were", "be", "been", "being",
        "have", "has", "had",
        "do", "does", "did",
        "will", "would", "could", "should",
    }
)

# Extended stop words for summarization and query term extraction.
# Superset of STOP_WORDS_INDEX plus pronouns, question words, and filler words.
STOP_WORDS_FULL: frozenset[str] = STOP_WORDS_INDEX | frozenset(
    {
        # Pronouns
        "i", "you", "he", "she", "it", "we", "they",
        "me", "him", "her", "us", "them",
        "my", "your", "his", "its", "our", "their",
        "this", "that", "these", "those",
        # Auxiliaries / modals not in base
        "am", "may", "might", "can",
        # Question words
        "what", "when", "where", "who", "why", "how", "tell", "about",
        # Filler / common words
        "so", "no", "if", "as", "up", "go", "not",
        "all", "just", "more", "also", "than", "then",
        "very", "some", "here", "there",
        "from", "into",
        "which", "each", "other", "much", "such",
        "only", "own", "same", "any", "both", "new", "now",
    }
)
