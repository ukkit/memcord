"""Non-NLTK summarizer backends: sumy, sentence-transformers, transformers."""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Any

from .summarizer_base import BaseSummarizer

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class SumySummarizer(BaseSummarizer):
    """Extractive summarizer using the sumy library (LexRank or LSA).

    Zero model files required. Uses graph-based sentence ranking.
    """

    def __init__(self, algorithm: str = "lexrank") -> None:
        """Initialize sumy summarizer.

        Args:
            algorithm: One of "lexrank", "lsa", or "edmundson".
        """
        self.algorithm = algorithm.lower()
        self._validate_imports()

    def _validate_imports(self) -> None:
        try:
            import sumy  # noqa: F401
        except ImportError as exc:
            raise ImportError(
                "sumy is required for SumySummarizer. "
                "Install it with: pip install sumy"
            ) from exc

    async def summarize(self, text: str, target_ratio: float = 0.15) -> str:
        from sumy.nlp.tokenizers import Tokenizer
        from sumy.parsers.plaintext import PlaintextParser
        from sumy.summarizers.edmundson import EdmundsonSummarizer
        from sumy.summarizers.lex_rank import LexRankSummarizer
        from sumy.summarizers.lsa import LsaSummarizer

        if not text or not text.strip():
            raise ValueError("Text cannot be empty")
        if target_ratio <= 0 or target_ratio > 1:
            raise ValueError("target_ratio must be between 0 and 1")

        parser = PlaintextParser.from_string(text, Tokenizer("english"))
        sentence_count = max(1, len(list(parser.document.sentences)))
        target_sentences = max(1, round(sentence_count * target_ratio))
        # Ensure we don't request more sentences than exist
        target_sentences = min(target_sentences, sentence_count)

        if self.algorithm == "lsa":
            summarizer: Any = LsaSummarizer()
        elif self.algorithm == "edmundson":
            summarizer = EdmundsonSummarizer()
            summarizer.bonus_words = []
            summarizer.stigma_words = []
            summarizer.null_words = []
        else:  # default: lexrank
            summarizer = LexRankSummarizer()

        selected = summarizer(parser.document, target_sentences)
        summary = " ".join(str(s) for s in selected)
        return summary if summary.strip() else text[:max(50, int(len(text) * target_ratio))]


class SemanticSummarizer(BaseSummarizer):
    """Embedding-based extractive summarizer using sentence-transformers + MMR.

    Requires ~80MB one-time model download.
    """

    def __init__(self, model_name: str = "all-MiniLM-L6-v2") -> None:
        self.model_name = model_name
        self._model: Any = None
        self._validate_imports()

    def _validate_imports(self) -> None:
        try:
            import sentence_transformers  # noqa: F401
        except ImportError as exc:
            raise ImportError(
                "sentence-transformers is required for SemanticSummarizer. "
                "Install it with: pip install sentence-transformers"
            ) from exc

    def _load_model(self) -> Any:
        if self._model is None:
            from sentence_transformers import SentenceTransformer

            logger.info("Loading sentence-transformers model: %s", self.model_name)
            self._model = SentenceTransformer(self.model_name)
        return self._model

    async def summarize(self, text: str, target_ratio: float = 0.15) -> str:
        import numpy as np

        if not text or not text.strip():
            raise ValueError("Text cannot be empty")
        if target_ratio <= 0 or target_ratio > 1:
            raise ValueError("target_ratio must be between 0 and 1")

        # Split into sentences (simple approach)
        sentences = self._split_sentences(text)
        if len(sentences) <= 2:
            return text

        target_count = max(1, round(len(sentences) * target_ratio))
        target_count = min(target_count, len(sentences))

        model = await asyncio.to_thread(self._load_model)
        embeddings = await asyncio.to_thread(model.encode, sentences, convert_to_numpy=True)

        # MMR selection
        selected_indices = self._mmr_select(embeddings, target_count)
        selected_indices.sort()
        summary = " ".join(sentences[i] for i in selected_indices)
        return summary if summary.strip() else text[:max(50, int(len(text) * target_ratio))]

    @staticmethod
    def _split_sentences(text: str) -> list[str]:
        import re

        parts = re.split(r"(?<=[.!?])\s+", text)
        return [s.strip() for s in parts if s.strip()]

    @staticmethod
    def _mmr_select(embeddings: Any, k: int, lambda_param: float = 0.7) -> list[int]:
        import numpy as np

        n = len(embeddings)
        if k >= n:
            return list(range(n))

        # Cosine similarity matrix
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        norms = np.where(norms == 0, 1e-10, norms)
        normed = embeddings / norms
        sim_matrix = normed @ normed.T

        selected: list[int] = []
        candidates = list(range(n))

        # Start with highest self-relevance (diagonal = 1, so pick best avg sim to others)
        avg_sim = sim_matrix.mean(axis=1)
        first = int(np.argmax(avg_sim))
        selected.append(first)
        candidates.remove(first)

        while len(selected) < k and candidates:
            best_idx = -1
            best_score = -float("inf")
            for c in candidates:
                relevance = float(avg_sim[c])
                redundancy = max(float(sim_matrix[c, s]) for s in selected)
                score = lambda_param * relevance - (1 - lambda_param) * redundancy
                if score > best_score:
                    best_score = score
                    best_idx = c
            if best_idx < 0:
                break
            selected.append(best_idx)
            candidates.remove(best_idx)

        return selected


class TransformersSummarizer(BaseSummarizer):
    """Abstractive summarizer using a HuggingFace seq2seq model.

    Lazy-loads ~400MB model on first call. Default model is dialogue-trained.
    """

    def __init__(
        self,
        model_name: str = "philschmid/bart-large-cnn-samsum",
        device: str = "auto",
    ) -> None:
        self.model_name = model_name
        self.device = device
        self._pipeline: Any = None
        self._validate_imports()

    def _validate_imports(self) -> None:
        try:
            import transformers  # noqa: F401
        except ImportError as exc:
            raise ImportError(
                "transformers (and torch) are required for TransformersSummarizer. "
                "Install with: pip install transformers torch"
            ) from exc

    def _load_pipeline(self) -> Any:
        if self._pipeline is None:
            from transformers import pipeline

            logger.info("Loading transformers model: %s", self.model_name)
            device_arg: Any = None
            if self.device == "auto":
                try:
                    import torch

                    if torch.cuda.is_available():
                        device_arg = 0
                    else:
                        device_arg = -1  # CPU
                except ImportError:
                    device_arg = -1
            elif self.device == "cpu":
                device_arg = -1
            elif self.device == "cuda":
                device_arg = 0
            else:
                device_arg = -1

            self._pipeline = pipeline("summarization", model=self.model_name, device=device_arg)
        return self._pipeline

    async def summarize(self, text: str, target_ratio: float = 0.15) -> str:
        if not text or not text.strip():
            raise ValueError("Text cannot be empty")
        if target_ratio <= 0 or target_ratio > 1:
            raise ValueError("target_ratio must be between 0 and 1")

        pipe = await asyncio.to_thread(self._load_pipeline)

        orig_len = len(text.split())
        min_len = max(10, int(orig_len * target_ratio * 0.5))
        max_len = max(min_len + 10, int(orig_len * target_ratio * 1.5))

        # Truncate input to model max (typically 1024 tokens ≈ 4096 chars)
        truncated = text[:4096] if len(text) > 4096 else text

        result = await asyncio.to_thread(pipe, truncated, min_length=min_len, max_length=max_len, do_sample=False)
        if result and isinstance(result, list) and "summary_text" in result[0]:
            return str(result[0]["summary_text"]).strip()

        return text[:max(50, int(len(text) * target_ratio))]
