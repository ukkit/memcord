"""Natural language query processing for memory slots."""

import re
from datetime import datetime, timedelta
from typing import Any

from .models import SearchQuery, SearchResult
from .search import SearchEngine


class QueryProcessor:
    """Process natural language queries and convert them to structured searches."""

    def __init__(self, search_engine: SearchEngine):
        self.search_engine = search_engine
        self._question_patterns = self._compile_patterns()

    def _compile_patterns(self) -> dict[str, list[re.Pattern]]:
        """Compile regex patterns for different question types."""
        return {
            # Factual questions
            "what": [
                re.compile(r"what (is|was|are|were) (.+)", re.IGNORECASE),
                re.compile(r"what did (.+)", re.IGNORECASE),
                re.compile(r"what (.+)", re.IGNORECASE),
            ],
            # Temporal questions
            "when": [
                re.compile(r"when (did|was|were) (.+)", re.IGNORECASE),
                re.compile(r"when (.+)", re.IGNORECASE),
            ],
            # People/entity questions
            "who": [
                re.compile(r"who (is|was|said|did) (.+)", re.IGNORECASE),
                re.compile(r"who (.+)", re.IGNORECASE),
            ],
            # Location questions
            "where": [
                re.compile(r"where (is|was|did) (.+)", re.IGNORECASE),
                re.compile(r"where (.+)", re.IGNORECASE),
            ],
            # Reasoning questions
            "why": [
                re.compile(r"why (did|was|is) (.+)", re.IGNORECASE),
                re.compile(r"why (.+)", re.IGNORECASE),
            ],
            # Process questions
            "how": [
                re.compile(r"how (do|did|can|to) (.+)", re.IGNORECASE),
                re.compile(r"how (.+)", re.IGNORECASE),
            ],
            # Decision questions
            "decision": [
                re.compile(r"what decision (.+)", re.IGNORECASE),
                re.compile(r"what (was|were) decided (.+)", re.IGNORECASE),
                re.compile(r"(decision|decide|chose|choice) (.+)", re.IGNORECASE),
            ],
            # Progress/status questions
            "status": [
                re.compile(r"(status|progress) (.+)", re.IGNORECASE),
                re.compile(r"what.*(progress|status) (.+)", re.IGNORECASE),
                re.compile(r"how.*(going|progressing) (.+)", re.IGNORECASE),
            ],
            # List/enumeration questions
            "list": [
                re.compile(r"(list|show|tell me) (.+)", re.IGNORECASE),
                re.compile(r"what are (.+)", re.IGNORECASE),
            ],
        }

    async def process_query(self, question: str, max_results: int = 10) -> dict[str, Any]:
        """Process a natural language query and return structured results."""
        # Clean and normalize the question
        question = question.strip()
        if not question:
            return {"error": "Empty question"}

        # Identify question type and extract key terms
        question_type, key_terms = self._classify_question(question)

        # Extract temporal constraints
        time_constraints = self._extract_time_constraints(question)

        # Build search query
        search_query = self._build_search_query(question, key_terms, time_constraints, max_results)

        # Perform search
        search_results = self.search_engine.search(search_query)

        # Generate natural language response
        response = await self._generate_response(question, question_type, search_results, key_terms)

        return {
            "question": question,
            "question_type": question_type,
            "key_terms": key_terms,
            "time_constraints": time_constraints,
            "search_results": len(search_results),
            "response": response,
            "sources": [
                {
                    "slot_name": result.slot_name,
                    "relevance": result.relevance_score,
                    "snippet": result.snippet,
                    "timestamp": result.timestamp.isoformat(),
                }
                for result in search_results[:5]  # Top 5 sources
            ],
        }

    def _classify_question(self, question: str) -> tuple[str, list[str]]:
        """Classify the question type and extract key terms."""

        # Check each pattern category
        for q_type, patterns in self._question_patterns.items():
            for pattern in patterns:
                match = pattern.search(question)
                if match:
                    # Extract key terms from the matched groups
                    key_terms = self._extract_key_terms(match.groups())
                    return q_type, key_terms

        # Default fallback - extract all meaningful words
        key_terms = self._extract_key_terms([question])
        return "general", key_terms

    def _extract_key_terms(self, text_groups: tuple[str, ...]) -> list[str]:
        """Extract meaningful terms from text groups."""
        all_text = " ".join(text_groups)

        # Remove common stop words and extract meaningful terms
        stop_words = {
            "the",
            "a",
            "an",
            "and",
            "or",
            "but",
            "in",
            "on",
            "at",
            "to",
            "for",
            "of",
            "with",
            "by",
            "is",
            "are",
            "was",
            "were",
            "be",
            "been",
            "being",
            "have",
            "has",
            "had",
            "do",
            "does",
            "did",
            "will",
            "would",
            "could",
            "should",
            "may",
            "might",
            "can",
            "this",
            "that",
            "these",
            "those",
            "i",
            "you",
            "he",
            "she",
            "it",
            "we",
            "they",
            "me",
            "him",
            "her",
            "us",
            "them",
        }

        # Extract words, remove punctuation
        words = re.findall(r"\b\w+\b", all_text.lower())

        # Filter meaningful terms
        key_terms = [word for word in words if len(word) > 2 and word not in stop_words]

        return key_terms[:10]  # Limit to top 10 terms

    def _extract_time_constraints(self, question: str) -> dict[str, datetime | None]:
        """Extract temporal constraints from the question."""
        time_patterns = {
            "today": timedelta(days=0),
            "yesterday": timedelta(days=1),
            "last week": timedelta(weeks=1),
            "last month": timedelta(days=30),
            "recent": timedelta(days=7),
            "recently": timedelta(days=7),
            "this week": timedelta(weeks=1),
            "this month": timedelta(days=30),
        }

        question_lower = question.lower()
        now = datetime.now()

        for time_phrase, delta in time_patterns.items():
            if time_phrase in question_lower:
                return {"date_from": now - delta, "date_to": now}

        return {"date_from": None, "date_to": None}

    def _build_search_query(
        self, question: str, key_terms: list[str], time_constraints: dict[str, datetime | None], max_results: int
    ) -> SearchQuery:
        """Build a SearchQuery from the processed question."""
        # Use the full question as the search query for better context
        # But also include key terms if the question is very short
        if len(question.split()) < 3:
            query_text = " ".join(key_terms)
        else:
            query_text = question

        return SearchQuery(
            query=query_text,
            date_from=time_constraints["date_from"],
            date_to=time_constraints["date_to"],
            max_results=max_results,
            case_sensitive=False,
        )

    async def _generate_response(
        self, question: str, question_type: str, results: list[SearchResult], key_terms: list[str]
    ) -> str:
        """Generate a natural language response based on search results."""
        if not results:
            return f"I couldn't find any information about {' '.join(key_terms)} in your memory slots."

        # Group results by slot for better organization
        slots_info = {}
        for result in results:
            if result.slot_name not in slots_info:
                slots_info[result.slot_name] = []
            slots_info[result.slot_name].append(result)

        response_parts = []

        # Add contextual introduction based on question type
        intro = self._get_response_intro(question_type, len(results))
        response_parts.append(intro)

        # Add information from top results
        for i, (slot_name, slot_results) in enumerate(slots_info.items()):
            if i >= 3:  # Limit to top 3 slots
                break

            best_result = max(slot_results, key=lambda r: r.relevance_score)

            # Format the information
            slot_info = f"**{slot_name}** (relevance: {best_result.relevance_score:.2f}):"

            if best_result.tags:
                slot_info += f" [Tags: {', '.join(best_result.tags)}]"

            response_parts.append(slot_info)
            response_parts.append(f"- {best_result.snippet}")
            response_parts.append(f"- Last updated: {best_result.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
            response_parts.append("")

        # Add summary
        if len(slots_info) > 3:
            response_parts.append(f"...and {len(slots_info) - 3} more memory slots contain related information.")

        return "\n".join(response_parts)

    def _get_response_intro(self, question_type: str, result_count: int) -> str:
        """Get an appropriate introduction for the response."""
        intros = {
            "what": f"Based on your memory slots, here's what I found ({result_count} results):",
            "when": f"Here's the timing information I found ({result_count} results):",
            "who": f"Here's information about the people/entities ({result_count} results):",
            "where": f"Here's location information I found ({result_count} results):",
            "why": f"Here's the reasoning/explanation I found ({result_count} results):",
            "how": f"Here's the process/method information ({result_count} results):",
            "decision": f"Here are the decisions I found ({result_count} results):",
            "status": f"Here's the status/progress information ({result_count} results):",
            "list": f"Here's what I found ({result_count} items):",
            "general": f"I found {result_count} relevant results:",
        }

        return intros.get(question_type, f"I found {result_count} relevant results:")


class SimpleQueryProcessor:
    """Simplified query processor for basic natural language queries."""

    def __init__(self, search_engine: SearchEngine):
        self.search_engine = search_engine

    async def answer_question(self, question: str, max_results: int = 5) -> str:
        """Answer a simple natural language question."""
        # Extract key terms and search
        key_terms = self._extract_key_terms(question)

        if not key_terms:
            return "I need more specific terms to search for."

        search_query = SearchQuery(query=" ".join(key_terms), max_results=max_results)

        results = self.search_engine.search(search_query)

        if not results:
            return f"I couldn't find any information about '{' '.join(key_terms)}' in your memory slots."

        # Format simple response
        response_parts = [f"I found {len(results)} relevant results:"]

        for i, result in enumerate(results[:3], 1):
            response_parts.append(f"{i}. {result.slot_name}: {result.snippet}")

        if len(results) > 3:
            response_parts.append(f"...and {len(results) - 3} more results.")

        return "\n".join(response_parts)

    def _extract_key_terms(self, text: str) -> list[str]:
        """Extract key terms from text."""
        stop_words = {
            "the",
            "a",
            "an",
            "and",
            "or",
            "but",
            "in",
            "on",
            "at",
            "to",
            "for",
            "of",
            "with",
            "by",
            "is",
            "are",
            "was",
            "were",
            "be",
            "been",
            "being",
            "have",
            "has",
            "had",
            "do",
            "does",
            "did",
            "will",
            "would",
            "could",
            "should",
            "what",
            "when",
            "where",
            "who",
            "why",
            "how",
            "can",
            "tell",
            "me",
            "about",
        }

        words = re.findall(r"\b\w+\b", text.lower())
        return [word for word in words if len(word) > 2 and word not in stop_words]
