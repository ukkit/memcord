"""Search engine for chat memory content."""

import re
import math
from collections import defaultdict
from datetime import datetime
from typing import Dict, List, Set, Optional, Tuple
from pathlib import Path

from .models import MemorySlot, SearchResult, SearchQuery


class SearchIndex:
    """Inverted index for fast text searching."""
    
    def __init__(self):
        self.word_to_slots: Dict[str, Set[str]] = defaultdict(set)
        self.slot_word_counts: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
        self.slot_total_words: Dict[str, int] = defaultdict(int)
        self.total_slots = 0
        self.dirty = True
    
    def add_slot(self, slot: MemorySlot) -> None:
        """Add a memory slot to the search index."""
        content = slot.get_searchable_content()
        words = self._tokenize(content)
        
        # Remove existing slot data if it exists
        self.remove_slot(slot.slot_name)
        
        # Add new word counts
        word_counts = defaultdict(int)
        for word in words:
            word_counts[word] += 1
            self.word_to_slots[word].add(slot.slot_name)
        
        self.slot_word_counts[slot.slot_name] = dict(word_counts)
        self.slot_total_words[slot.slot_name] = len(words)
        self.total_slots += 1
        self.dirty = False
    
    def remove_slot(self, slot_name: str) -> None:
        """Remove a memory slot from the search index."""
        if slot_name not in self.slot_word_counts:
            return
        
        # Remove slot from word mappings
        for word in self.slot_word_counts[slot_name]:
            self.word_to_slots[word].discard(slot_name)
            if not self.word_to_slots[word]:
                del self.word_to_slots[word]
        
        # Remove slot data
        del self.slot_word_counts[slot_name]
        del self.slot_total_words[slot_name]
        self.total_slots = max(0, self.total_slots - 1)
        self.dirty = False
    
    def search(self, query: str, case_sensitive: bool = False, use_regex: bool = False) -> Dict[str, float]:
        """Search for slots matching the query. Returns slot_name -> relevance_score mapping."""
        if not query.strip():
            return {}
        
        if use_regex:
            return self._regex_search(query, case_sensitive)
        else:
            return self._text_search(query, case_sensitive)
    
    def _text_search(self, query: str, case_sensitive: bool) -> Dict[str, float]:
        """Perform text-based search with TF-IDF scoring."""
        query_words = self._tokenize(query, case_sensitive)
        if not query_words:
            return {}
        
        # Find slots containing query words
        candidate_slots = set()
        for word in query_words:
            candidate_slots.update(self.word_to_slots.get(word, set()))
        
        if not candidate_slots:
            return {}
        
        # Calculate TF-IDF scores
        scores = {}
        for slot_name in candidate_slots:
            score = self._calculate_tfidf_score(query_words, slot_name)
            if score > 0:
                scores[slot_name] = score
        
        return scores
    
    def _regex_search(self, pattern: str, case_sensitive: bool) -> Dict[str, float]:
        """Perform regex-based search."""
        try:
            flags = 0 if case_sensitive else re.IGNORECASE
            regex = re.compile(pattern, flags)
        except re.error:
            return {}
        
        scores = {}
        for slot_name in self.slot_word_counts.keys():
            # Simple scoring based on match count for regex
            match_count = len(regex.findall(' '.join(self.slot_word_counts[slot_name].keys())))
            if match_count > 0:
                scores[slot_name] = min(1.0, match_count / 10.0)  # Normalize to 0-1
        
        return scores
    
    def _calculate_tfidf_score(self, query_words: List[str], slot_name: str) -> float:
        """Calculate TF-IDF score for a slot given query words."""
        if slot_name not in self.slot_word_counts or self.total_slots == 0:
            return 0.0
        
        slot_word_counts = self.slot_word_counts[slot_name]
        slot_total_words = self.slot_total_words[slot_name]
        
        score = 0.0
        for word in query_words:
            if word in slot_word_counts:
                # Term Frequency
                tf = slot_word_counts[word] / slot_total_words
                
                # Document Frequency
                df = len(self.word_to_slots.get(word, set()))
                
                # Inverse Document Frequency
                idf = math.log(self.total_slots / df) if df > 0 else 0
                
                # If IDF is 0 (single document), use TF only
                if idf == 0:
                    score += tf
                else:
                    score += tf * idf
        
        return min(1.0, score)  # Normalize to 0-1
    
    def _tokenize(self, text: str, case_sensitive: bool = False) -> List[str]:
        """Tokenize text into searchable words."""
        if not case_sensitive:
            text = text.lower()
        
        # Extract words, removing punctuation
        words = re.findall(r'\b\w+\b', text)
        
        # Filter out very short words and common stop words
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should'}
        
        return [word for word in words if len(word) > 2 and word not in stop_words]


class SearchEngine:
    """Advanced search engine for memory slots."""
    
    def __init__(self):
        self.index = SearchIndex()
        self.slots_cache: Dict[str, MemorySlot] = {}
    
    def add_slot(self, slot: MemorySlot) -> None:
        """Add or update a slot in the search engine."""
        self.slots_cache[slot.slot_name] = slot
        self.index.add_slot(slot)
    
    def remove_slot(self, slot_name: str) -> None:
        """Remove a slot from the search engine."""
        self.index.remove_slot(slot_name)
        self.slots_cache.pop(slot_name, None)
    
    def search(self, query: SearchQuery) -> List[SearchResult]:
        """Perform advanced search with filtering and ranking."""
        # Get initial search results
        relevance_scores = self.index.search(query.query, query.case_sensitive, query.use_regex)
        
        if not relevance_scores:
            return []
        
        # Apply filters and create results
        results = []
        for slot_name, score in relevance_scores.items():
            slot = self.slots_cache.get(slot_name)
            if not slot:
                continue
            
            # Apply filters
            if not self._passes_filters(slot, query):
                continue
            
            # Find matching entries and create results
            slot_results = self._create_search_results(slot, query, score)
            results.extend(slot_results)
        
        # Sort by relevance score and limit results
        results.sort(key=lambda r: r.relevance_score, reverse=True)
        return results[:query.max_results]
    
    def boolean_search(self, query_parts: List[str], operator: str = 'AND') -> Dict[str, float]:
        """Perform boolean search with AND/OR/NOT operators."""
        if not query_parts:
            return {}
        
        if operator.upper() == 'AND':
            # All terms must be present
            result_sets = [set(self.index.search(part).keys()) for part in query_parts]
            if not result_sets:
                return {}
            
            intersection = result_sets[0]
            for result_set in result_sets[1:]:
                intersection &= result_set
            
            # Calculate combined scores
            scores = {}
            for slot_name in intersection:
                combined_score = 0.0
                for part in query_parts:
                    part_scores = self.index.search(part)
                    combined_score += part_scores.get(slot_name, 0.0)
                scores[slot_name] = min(1.0, combined_score / len(query_parts))
            
            return scores
        
        elif operator.upper() == 'OR':
            # Any term can be present
            all_scores = {}
            for part in query_parts:
                part_scores = self.index.search(part)
                for slot_name, score in part_scores.items():
                    all_scores[slot_name] = max(all_scores.get(slot_name, 0.0), score)
            
            return all_scores
        
        else:  # NOT logic would need special handling
            return self.index.search(query_parts[0])
    
    def _passes_filters(self, slot: MemorySlot, query: SearchQuery) -> bool:
        """Check if a slot passes all search filters."""
        # Tag filters
        if query.include_tags:
            if not any(slot.has_tag(tag) for tag in query.include_tags):
                return False
        
        if query.exclude_tags:
            if any(slot.has_tag(tag) for tag in query.exclude_tags):
                return False
        
        # Group filters
        if query.include_groups and slot.group_path:
            if not any(group in slot.group_path for group in query.include_groups):
                return False
        
        if query.exclude_groups and slot.group_path:
            if any(group in slot.group_path for group in query.exclude_groups):
                return False
        
        # Date filters
        if query.date_from or query.date_to:
            slot_dates = [entry.timestamp for entry in slot.entries]
            if query.date_from:
                if not any(date >= query.date_from for date in slot_dates):
                    return False
            if query.date_to:
                if not any(date <= query.date_to for date in slot_dates):
                    return False
        
        # Content type filters
        if query.content_types:
            entry_types = {entry.type for entry in slot.entries}
            if not entry_types.intersection(query.content_types):
                return False
        
        return True
    
    def _create_search_results(self, slot: MemorySlot, query: SearchQuery, base_score: float) -> List[SearchResult]:
        """Create search results for a slot with matching entries."""
        results = []
        
        # Check for slot-level matches (name, tags, group)
        slot_content = f"{slot.slot_name} {' '.join(slot.tags)} {slot.group_path or ''}"
        if self._content_matches_query(slot_content, query):
            snippet = self._create_snippet(slot_content, query.query)
            results.append(SearchResult(
                slot_name=slot.slot_name,
                entry_index=None,
                relevance_score=base_score,
                snippet=snippet,
                match_type='slot',
                timestamp=slot.updated_at,
                tags=list(slot.tags),
                group_path=slot.group_path
            ))
        
        # Check individual entries
        for i, entry in enumerate(slot.entries):
            if entry.type not in query.content_types:
                continue
            
            # Get entry content, decompressing if necessary
            entry_content = entry.content
            if entry.compression_info.is_compressed:
                try:
                    from .compression import ContentCompressor
                    compressor = ContentCompressor()
                    entry_content = compressor.decompress_json_content(entry.content, entry.compression_info)
                except Exception:
                    # If decompression fails, skip this entry
                    continue
            
            if self._content_matches_query(entry_content, query):
                snippet = self._create_snippet(entry_content, query.query)
                # Boost score slightly for direct content matches
                entry_score = min(1.0, base_score * 1.1)
                
                results.append(SearchResult(
                    slot_name=slot.slot_name,
                    entry_index=i,
                    relevance_score=entry_score,
                    snippet=snippet,
                    match_type='entry',
                    timestamp=entry.timestamp,
                    tags=list(slot.tags),
                    group_path=slot.group_path
                ))
        
        return results
    
    def _content_matches_query(self, content: str, query: SearchQuery) -> bool:
        """Check if content matches the search query."""
        if query.use_regex:
            try:
                flags = 0 if query.case_sensitive else re.IGNORECASE
                return bool(re.search(query.query, content, flags))
            except re.error:
                return False
        else:
            search_content = content if query.case_sensitive else content.lower()
            search_query = query.query if query.case_sensitive else query.query.lower()
            return search_query in search_content
    
    def _create_snippet(self, content: str, query: str, max_length: int = 150) -> str:
        """Create a preview snippet highlighting the search query."""
        if not query or len(content) <= max_length:
            return content[:max_length]
        
        # Find the query in content (case-insensitive)
        lower_content = content.lower()
        lower_query = query.lower()
        
        match_pos = lower_content.find(lower_query)
        if match_pos == -1:
            return content[:max_length]
        
        # Calculate snippet boundaries
        snippet_start = max(0, match_pos - max_length // 3)
        snippet_end = min(len(content), snippet_start + max_length)
        
        snippet = content[snippet_start:snippet_end]
        
        # Add ellipsis if truncated
        if snippet_start > 0:
            snippet = "..." + snippet[3:]
        if snippet_end < len(content):
            snippet = snippet[:-3] + "..."
        
        return snippet
    
    def get_stats(self) -> Dict[str, any]:
        """Get search engine statistics."""
        return {
            "total_slots": self.index.total_slots,
            "total_words": sum(self.index.slot_total_words.values()),
            "unique_words": len(self.index.word_to_slots),
            "average_words_per_slot": sum(self.index.slot_total_words.values()) / max(1, self.index.total_slots),
            "index_dirty": self.index.dirty
        }