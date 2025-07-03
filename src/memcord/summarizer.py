"""Text summarization functionality."""

import re
import math
from typing import List, Dict, Tuple
from collections import Counter


class TextSummarizer:
    """Simple extractive text summarizer."""
    
    def __init__(self):
        # Common stop words for filtering
        self.stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 
            'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 
            'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should',
            'i', 'you', 'he', 'she', 'it', 'we', 'they', 'me', 'him', 'her', 'us', 'them',
            'this', 'that', 'these', 'those', 'my', 'your', 'his', 'her', 'its', 'our', 'their'
        }
    
    def summarize(self, text: str, target_ratio: float = 0.15, compression_ratio: float = None) -> str:
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
        
        # Split into sentences
        sentences = self._split_into_sentences(text)
        
        if len(sentences) <= 2:
            # Too short to summarize meaningfully
            return text
        
        # Calculate target sentence count
        target_count = max(1, int(len(sentences) * target_ratio))
        target_count = min(target_count, len(sentences))
        
        # Score sentences
        sentence_scores = self._score_sentences(sentences)
        
        # Select top sentences
        top_sentences = self._select_top_sentences(sentences, sentence_scores, target_count)
        
        # Reconstruct summary maintaining original order
        summary = self._reconstruct_summary(sentences, top_sentences)
        
        return summary
    
    def _split_into_sentences(self, text: str) -> List[str]:
        """Split text into sentences."""
        # Simple sentence splitting on periods, exclamation marks, and question marks
        sentence_pattern = r'[.!?]+\s+'
        sentences = re.split(sentence_pattern, text.strip())
        
        # Clean up sentences
        sentences = [s.strip() for s in sentences if s.strip()]
        
        # If we only got one sentence, try splitting on newlines
        if len(sentences) == 1:
            sentences = [s.strip() for s in text.split('\n') if s.strip()]
        
        return sentences
    
    def _score_sentences(self, sentences: List[str]) -> Dict[int, float]:
        """Score sentences based on word frequency and position."""
        # Calculate word frequencies
        word_freq = self._calculate_word_frequencies(sentences)
        
        sentence_scores = {}
        
        for i, sentence in enumerate(sentences):
            # Word frequency score
            words = self._tokenize(sentence.lower())
            freq_score = sum(word_freq.get(word, 0) for word in words if word not in self.stop_words)
            freq_score = freq_score / len(words) if words else 0
            
            # Position score (earlier sentences get slight boost)
            position_score = 1.0 - (i / len(sentences)) * 0.3
            
            # Length score (prefer medium-length sentences)
            length_score = self._calculate_length_score(sentence)
            
            # Keyword density score
            keyword_score = self._calculate_keyword_score(sentence, word_freq)
            
            # Combined score
            total_score = (freq_score * 0.4 + 
                          position_score * 0.2 + 
                          length_score * 0.2 + 
                          keyword_score * 0.2)
            
            sentence_scores[i] = total_score
        
        return sentence_scores
    
    def _calculate_word_frequencies(self, sentences: List[str]) -> Dict[str, float]:
        """Calculate normalized word frequencies."""
        word_count = Counter()
        
        for sentence in sentences:
            words = self._tokenize(sentence.lower())
            for word in words:
                if word not in self.stop_words and len(word) > 2:
                    word_count[word] += 1
        
        # Normalize frequencies
        max_freq = max(word_count.values()) if word_count else 1
        return {word: count / max_freq for word, count in word_count.items()}
    
    def _tokenize(self, text: str) -> List[str]:
        """Simple word tokenization."""
        # Remove punctuation and split
        text = re.sub(r'[^\w\s]', ' ', text)
        return [word.strip() for word in text.split() if word.strip()]
    
    def _calculate_length_score(self, sentence: str) -> float:
        """Score based on sentence length (prefer medium length)."""
        length = len(sentence.split())
        
        if length < 5:
            return 0.3  # Too short
        elif length > 40:
            return 0.5  # Too long
        else:
            # Optimal range 8-25 words
            if 8 <= length <= 25:
                return 1.0
            else:
                return 0.7
    
    def _calculate_keyword_score(self, sentence: str, word_freq: Dict[str, float]) -> float:
        """Score based on presence of high-frequency keywords."""
        words = self._tokenize(sentence.lower())
        if not words:
            return 0
        
        # Get top keywords (high frequency words)
        top_keywords = set(word for word, freq in word_freq.items() if freq > 0.7)
        
        keyword_count = sum(1 for word in words if word in top_keywords)
        return keyword_count / len(words)
    
    def _select_top_sentences(self, sentences: List[str], scores: Dict[int, float], count: int) -> List[int]:
        """Select the top N sentences by score."""
        sorted_indices = sorted(scores.keys(), key=lambda i: scores[i], reverse=True)
        return sorted_indices[:count]
    
    def _reconstruct_summary(self, original_sentences: List[str], selected_indices: List[int]) -> str:
        """Reconstruct summary maintaining original sentence order."""
        # Sort selected indices to maintain original order
        selected_indices.sort()
        
        summary_sentences = [original_sentences[i] for i in selected_indices]
        
        # Join sentences with appropriate spacing
        summary = '. '.join(summary_sentences)
        
        # Clean up the summary
        summary = re.sub(r'\.\s*\.', '.', summary)  # Remove double periods
        summary = summary.strip()
        
        # Ensure proper ending
        if summary and not summary.endswith(('.', '!', '?')):
            summary += '.'
        
        return summary
    
    def get_summary_stats(self, original: str, summary: str) -> Dict[str, int]:
        """Get statistics about the summarization."""
        # Validate inputs
        if not isinstance(original, str):
            raise TypeError("Original text must be a string")
        if not isinstance(summary, str):
            raise TypeError("Summary text must be a string")
        
        return {
            'original_length': len(original),
            'summary_length': len(summary),
            'original_words': len(original.split()),
            'summary_words': len(summary.split()),
            'words_original': len(original.split()),  # Alternative name for backward compatibility
            'words_summary': len(summary.split()),    # Alternative name for backward compatibility
            'compression_ratio': len(summary) / len(original) if original else 0
        }