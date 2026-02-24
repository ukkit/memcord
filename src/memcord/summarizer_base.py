"""Abstract base class for summarizer backends."""

from abc import ABC, abstractmethod


class BaseSummarizer(ABC):
    """Abstract base class for all summarizer backends."""

    @abstractmethod
    async def summarize(self, text: str, target_ratio: float = 0.15) -> str:
        """Summarize text to approximately target_ratio of the original length.

        Args:
            text: Input text to summarize.
            target_ratio: Target length as ratio of original (0.15 = 15%).

        Returns:
            Summary text.
        """

    def get_summary_stats(self, original: str, summary: str) -> dict[str, int | float]:
        """Get statistics about the summarization.

        Args:
            original: Original text.
            summary: Summary text.

        Returns:
            Dict with original_length, summary_length, compression_ratio, etc.
        """
        orig_len = len(original)
        summ_len = len(summary)
        return {
            "original_length": orig_len,
            "summary_length": summ_len,
            "original_words": len(original.split()),
            "summary_words": len(summary.split()),
            "compression_ratio": summ_len / orig_len if orig_len else 0.0,
        }
