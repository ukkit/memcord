"""Factory for building summarizer backends from slot config and env vars."""

from __future__ import annotations

import logging
import os

from .models import SlotConfig
from .summarizer_base import BaseSummarizer

logger = logging.getLogger(__name__)

# MEMCORD_SUMMARIZER env var overrides per-slot config when set.
_ENV_VAR = "MEMCORD_SUMMARIZER"


def build_summarizer(config: SlotConfig) -> BaseSummarizer:
    """Build and return the appropriate BaseSummarizer for the given slot config.

    The MEMCORD_SUMMARIZER environment variable overrides the per-slot config
    when set, enabling deployment-level overrides (Docker, CI, etc.).

    Built per-call so that config changes take effect immediately on the next
    save_progress without restarting the server.

    Falls back to SumySummarizer (or NLTKSummarizer) with a warning if the
    requested backend fails to initialize.

    Args:
        config: Per-slot configuration specifying the backend and its options.

    Returns:
        An initialized BaseSummarizer instance ready to summarize text.
    """
    backend = os.environ.get(_ENV_VAR, "").strip().lower() or config.summarizer_backend.lower()

    try:
        return _create(backend, config)
    except Exception as exc:
        logger.warning(
            "Failed to initialize summarizer backend '%s': %s. Falling back to sumy.",
            backend,
            exc,
        )

    # First fallback: sumy
    if backend != "sumy":
        try:
            return _create("sumy", config)
        except Exception as exc2:
            logger.warning("sumy fallback also failed: %s. Falling back to nltk.", exc2)

    # Last resort: NLTK
    from .summarizer import NLTKSummarizer

    return NLTKSummarizer()


def _create(backend: str, config: SlotConfig) -> BaseSummarizer:
    """Instantiate a summarizer for the given backend key."""
    if backend == "nltk":
        from .summarizer import NLTKSummarizer

        return NLTKSummarizer()

    if backend == "sumy":
        from .llm_summarizer import SumySummarizer

        return SumySummarizer(algorithm=config.sumy_algorithm)

    if backend == "semantic":
        from .llm_summarizer import SemanticSummarizer

        return SemanticSummarizer(model_name=config.semantic_model)

    if backend == "transformers":
        from .llm_summarizer import TransformersSummarizer

        return TransformersSummarizer(
            model_name=config.transformers_model,
            device=config.hf_device,
        )

    raise ValueError(f"Unknown summarizer backend: '{backend}'. Valid values: nltk, sumy, semantic, transformers")
