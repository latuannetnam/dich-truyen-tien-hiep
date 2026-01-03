"""Term scoring for intelligent glossary selection.

This module provides TF-IDF based term scoring to select the most relevant
glossary entries for each translation chunk.

The abstraction layer (TermScorer Protocol) allows easy replacement of the
pure Python implementation with external libraries like jieba/sklearn.
"""

import math
from typing import Protocol, Optional
from collections import Counter


class TermScorer(Protocol):
    """Protocol for term scoring implementations.
    
    This abstraction allows easy replacement of the scoring algorithm.
    Future implementations could use jieba, sklearn, or other libraries.
    """
    
    def fit(self, documents: list[str], terms: list[str]) -> None:
        """Pre-calculate IDF scores from all documents for given terms.
        
        Args:
            documents: List of all chapter contents
            terms: List of glossary terms to track
        """
        ...
    
    def score_for_chunk(self, chunk: str) -> dict[str, float]:
        """Calculate TF-IDF scores for terms present in a chunk.
        
        Args:
            chunk: Text chunk to score terms for
            
        Returns:
            Dictionary mapping term -> TF-IDF score (higher = more relevant)
        """
        ...
    
    def is_fitted(self) -> bool:
        """Check if the scorer has been fitted with documents."""
        ...


class SimpleTermScorer:
    """Pure Python TF-IDF scorer for glossary terms.
    
    This implementation doesn't require external dependencies.
    It only calculates TF-IDF for known glossary terms, not all words.
    
    Example:
        scorer = SimpleTermScorer()
        scorer.fit(all_chapters, glossary_terms)
        
        # For each chunk:
        scores = scorer.score_for_chunk(chunk)
        # Returns: {"陈平安": 2.5, "骊珠洞天": 4.1, ...}
    """
    
    def __init__(self):
        self.terms: list[str] = []
        self.doc_count: int = 0
        self.doc_freq: Counter[str] = Counter()
        self._fitted: bool = False
    
    def fit(self, documents: list[str], terms: list[str]) -> None:
        """Pre-calculate IDF scores from all documents.
        
        IDF (Inverse Document Frequency) = log(total_docs / docs_containing_term)
        Higher IDF means the term is rarer and more distinctive.
        
        Args:
            documents: List of all chapter contents
            terms: List of glossary terms to track
        """
        self.terms = terms
        self.doc_count = len(documents)
        self.doc_freq = Counter()
        
        # Count how many documents contain each term
        for doc in documents:
            for term in terms:
                if term in doc:
                    self.doc_freq[term] += 1
        
        self._fitted = True
    
    def score_for_chunk(self, chunk: str) -> dict[str, float]:
        """Calculate TF-IDF scores for terms present in chunk.
        
        TF (Term Frequency) = count of term in chunk
        TF-IDF = TF * IDF
        
        Args:
            chunk: Text chunk to score terms for
            
        Returns:
            Dictionary mapping term -> TF-IDF score
        """
        if not self._fitted:
            return {}
        
        scores = {}
        for term in self.terms:
            if term in chunk:
                df = self.doc_freq.get(term, 0)
                if df > 0:
                    # TF = frequency in this chunk
                    tf = chunk.count(term)
                    # IDF = log(total_docs / docs_with_term)
                    # Add 1 to avoid division by zero
                    idf = math.log((self.doc_count + 1) / (df + 1)) + 1
                    scores[term] = tf * idf
        
        return scores
    
    def is_fitted(self) -> bool:
        """Check if the scorer has been fitted."""
        return self._fitted
    
    def get_idf(self, term: str) -> float:
        """Get IDF score for a specific term.
        
        Args:
            term: Term to get IDF for
            
        Returns:
            IDF score (higher = rarer)
        """
        if not self._fitted or self.doc_count == 0:
            return 0.0
        
        df = self.doc_freq.get(term, 0)
        if df == 0:
            return 0.0
        
        return math.log((self.doc_count + 1) / (df + 1)) + 1


# Future implementations can be added here:
# class JiebaTermScorer(TermScorer): ...
# class SklearnTermScorer(TermScorer): ...
