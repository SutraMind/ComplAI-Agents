"""
Reranking module for RAG pipeline.
Provides multiple reranking strategies with modular selection.
"""

import re
import json
import logging
import numpy as np
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from collections import Counter

logger = logging.getLogger(__name__)


@dataclass
class RetrievedDocument:
    """Represents a retrieved document with score."""
    content: str
    score: float
    metadata: Dict[str, Any]
    rerank_score: Optional[float] = None


class RerankerStrategy(ABC):
    """Abstract base class for reranking strategies."""
    
    @abstractmethod
    def rerank(self, query: str, documents: List[RetrievedDocument], **kwargs) -> List[RetrievedDocument]:
        """Rerank the documents based on the query."""
        pass
    
    @abstractmethod
    def get_strategy_name(self) -> str:
        """Return the name of the reranking strategy."""
        pass


class NoOpReranker(RerankerStrategy):
    """No reranking - returns documents in original order."""
    
    def rerank(self, query: str, documents: List[RetrievedDocument], **kwargs) -> List[RetrievedDocument]:
        """Return documents without reranking."""
        for doc in documents:
            doc.rerank_score = doc.score
        return documents
    
    def get_strategy_name(self) -> str:
        return "none"


class CrossEncoderReranker(RerankerStrategy):
    """Cross-encoder based reranking."""
    
    def __init__(self, model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"):
        self.model_name = model_name
        self.model = None
        self._load_model()
    
    def _load_model(self):
        """Load the cross-encoder model."""
        try:
            from sentence_transformers import CrossEncoder
            self.model = CrossEncoder(self.model_name)
            logger.info(f"Loaded cross-encoder model: {self.model_name}")
        except ImportError:
            logger.warning("sentence-transformers not available, cross-encoder reranking disabled")
        except Exception as e:
            logger.error(f"Failed to load cross-encoder model: {e}")
    
    def rerank(self, query: str, documents: List[RetrievedDocument], **kwargs) -> List[RetrievedDocument]:
        """Rerank documents using cross-encoder."""
        if not self.model:
            logger.warning("Cross-encoder model not loaded, skipping reranking")
            return self.no_rerank(query, documents)
        
        if not documents:
            return documents
        
        try:
            # Create query-document pairs
            pairs = [(query, doc.content) for doc in documents]
            
            # Get scores
            scores = self.model.predict(pairs)
            
            # Update rerank scores and sort
            for doc, score in zip(documents, scores):
                doc.rerank_score = float(score)
            
            # Sort by rerank score (descending)
            documents.sort(key=lambda x: x.rerank_score, reverse=True)
            
            logger.info(f"CrossEncoderReranker reranked {len(documents)} documents")
            return documents
            
        except Exception as e:
            logger.error(f"Error in cross-encoder reranking: {e}")
            return self.no_rerank(query, documents)
    
    def no_rerank(self, query: str, documents: List[RetrievedDocument]) -> List[RetrievedDocument]:
        """Fallback when model unavailable."""
        for doc in documents:
            doc.rerank_score = doc.score
        return documents
    
    def get_strategy_name(self) -> str:
        return f"cross_encoder_{self.model_name.split('/')[-1]}"


class LLMReranker(RerankerStrategy):
    """LLM-based reranking using pairwise comparison."""
    
    def __init__(self, llm_client=None, top_k: int = 10):
        self.llm_client = llm_client
        self.top_k = top_k
    
    def rerank(self, query: str, documents: List[RetrievedDocument], **kwargs) -> List[RetrievedDocument]:
        """Rerank documents using LLM pairwise comparison."""
        if not self.llm_client:
            logger.warning("No LLM client provided, using original order")
            return self.no_rerank(query, documents)
        
        top_k = kwargs.get('top_k', self.top_k)
        
        if len(documents) <= top_k:
            # No need to rerank if fewer documents than top_k
            return self.no_rerank(query, documents)
        
        try:
            # Use LLM to score each document
            scored_docs = []
            
            for doc in documents:
                score = self._score_document(query, doc.content)
                doc.rerank_score = score
                scored_docs.append(doc)
            
            # Sort by rerank score
            scored_docs.sort(key=lambda x: x.rerank_score, reverse=True)
            
            logger.info(f"LLMReranker reranked {len(documents)} documents")
            return scored_docs[:top_k]
            
        except Exception as e:
            logger.error(f"Error in LLM reranking: {e}")
            return self.no_rerank(query, documents)
    
    def _score_document(self, query: str, document: str) -> float:
        """Use LLM to score relevance of document to query."""
        prompt = f"""Rate the relevance of the following document to the query on a scale of 0-1.

QUERY: {query}

DOCUMENT: {document[:500]}

Respond with ONLY a number between 0 and 1 (e.g., 0.85). 

Consider:
- 1.0: Document is highly relevant and directly addresses the query
- 0.5: Document is somewhat relevant
- 0.0: Document is not relevant at all

SCORE:"""

        try:
            response = self.llm_client.generate(
                prompt=prompt,
                temperature=0.1,
                max_tokens=10
            )
            
            if response.success:
                # Extract score from response
                score_text = response.content.strip()
                # Try to find a number in the response
                match = re.search(r'0?\.\d+|\d+(?:\.\d+)?', score_text)
                if match:
                    score = float(match.group())
                    return min(max(score, 0.0), 1.0)
            
            return 0.5  # Default score
            
        except Exception as e:
            logger.warning(f"Error scoring document: {e}")
            return 0.5
    
    def no_rerank(self, query: str, documents: List[RetrievedDocument]) -> List[RetrievedDocument]:
        """Fallback to original order."""
        for doc in documents:
            doc.rerank_score = doc.score
        return documents
    
    def get_strategy_name(self) -> str:
        return "llm_based"


class BM25Reranker(RerankerStrategy):
    """BM25-based keyword reranking."""
    
    def __init__(self, k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.avg_doc_length = 0
        self.doc_freqs = {}
        self.idf = {}
    
    def fit(self, documents: List[RetrievedDocument]) -> 'BM25Reranker':
        """Fit the reranker on the document collection."""
        if not documents:
            return self
        
        # Calculate average document length
        doc_lengths = [len(doc.content.split()) for doc in documents]
        self.avg_doc_length = sum(doc_lengths) / len(doc_lengths) if doc_lengths else 0
        
        # Calculate document frequencies
        all_terms = set()
        for doc in documents:
            terms = set(doc.content.lower().split())
            all_terms.update(terms)
            for term in terms:
                self.doc_freqs[term] = self.doc_freqs.get(term, 0) + 1
        
        # Calculate IDF
        N = len(documents)
        for term, df in self.doc_freqs.items():
            self.idf[term] = np.log((N - df + 0.5) / (df + 0.5) + 1)
        
        logger.info(f"BM25 fitted on {len(documents)} documents, {len(self.idf)} unique terms")
        return self
    
    def rerank(self, query: str, documents: List[RetrievedDocument], **kwargs) -> List[RetrievedDocument]:
        """Rerank documents using BM25."""
        if not documents:
            return documents
        
        # Fit on documents if not already
        if not self.idf:
            self.fit(documents)
        
        query_terms = query.lower().split()
        
        for doc in documents:
            score = self._bm25_score(query_terms, doc.content)
            doc.rerank_score = score
        
        # Sort by rerank score
        documents.sort(key=lambda x: x.rerank_score, reverse=True)
        
        logger.info(f"BM25Reranker reranked {len(documents)} documents")
        return documents
    
    def _bm25_score(self, query_terms: List[str], document: str) -> float:
        """Calculate BM25 score for a document."""
        doc_terms = document.lower().split()
        doc_length = len(doc_terms)
        
        if doc_length == 0:
            return 0.0
        
        # Count term frequencies
        term_freqs = Counter(doc_terms)
        
        score = 0.0
        for term in query_terms:
            if term not in term_freqs:
                continue
            
            tf = term_freqs[term]
            idf = self.idf.get(term, 0)
            
            # BM25 term scoring
            numerator = tf * (self.k1 + 1)
            denominator = tf + self.k1 * (1 - self.b + self.b * (doc_length / self.avg_doc_length))
            
            score += idf * (numerator / denominator)
        
        return score
    
    def get_strategy_name(self) -> str:
        return f"bm25_k1={self.k1}_b={self.b}"


class HybridReranker(RerankerStrategy):
    """Combines multiple reranking strategies."""
    
    def __init__(self, 
                 rerankers: List[RerankerStrategy],
                 weights: Optional[List[float]] = None):
        self.rerankers = rerankers
        self.weights = weights or [1.0] * len(rerankers)
        
        if len(self.weights) != len(self.rerankers):
            raise ValueError("Number of weights must match number of rerankers")
        
        # Normalize weights
        total = sum(self.weights)
        self.weights = [w / total for w in self.weights]
    
    def rerank(self, query: str, documents: List[RetrievedDocument], **kwargs) -> List[RetrievedDocument]:
        """Combine multiple reranking strategies."""
        if not documents or not self.rerankers:
            return documents
        
        # Store all scores
        all_scores = []
        
        for reranker in self.rerankers:
            # Apply each reranker
            reranked = reranker.rerank(query, documents)
            
            # Collect scores
            scores = []
            for doc in reranked:
                idx = next(i for i, d in enumerate(documents) if d.content == doc.content and d.score == doc.score)
                scores.append((idx, doc.rerank_score or doc.score))
            
            all_scores.append(scores)
        
        # Combine scores with weights
        combined_scores = []
        for i in range(len(documents)):
            combined = sum(
                weight * score[idx][1]
                for weight, scores in zip(self.weights, all_scores)
                for idx, sc in scores
                if idx == i
            )
            combined_scores.append(combined)
        
        # Update and sort documents
        for i, doc in enumerate(documents):
            doc.rerank_score = combined_scores[i]
        
        documents.sort(key=lambda x: x.rerank_score, reverse=True)
        
        logger.info(f"HybridReranker combined {len(self.rerankers)} strategies")
        return documents
    
    def get_strategy_name(self) -> str:
        names = [r.get_strategy_name() for r in self.rerankers]
        return f"hybrid_{'+'.join(names)}"


class ReciprocalRankReranker(RerankerStrategy):
    """Reciprocal Rank Fusion - combines multiple retrieval runs."""
    
    def __init__(self, k: float = 60):
        self.k = k
    
    def rerank(self, query: str, documents: List[RetrievedDocument], **kwargs) -> List[RetrievedDocument]:
        """
        Rerank using Reciprocal Rank Fusion.
        This works best when documents have been retrieved by multiple methods.
        """
        if not documents:
            return documents
        
        # Group documents by their ranking positions
        # For single retrieval, use the scores as ranking
        
        # Normalize scores to get pseudo-rankings
        scores = [doc.score for doc in documents]
        if not scores or max(scores) == min(scores):
            # All same, keep original order
            return self.no_rerank(query, documents)
        
        # Calculate ranks
        sorted_indices = np.argsort(scores)[::-1]
        rank_map = {idx: rank + 1 for rank, idx in enumerate(sorted_indices)}
        
        # Apply RRF formula
        rrf_scores = []
        for i, doc in enumerate(documents):
            rank = rank_map[i]
            rrf_score = 1.0 / (self.k + rank)
            doc.rerank_score = rrf_score
            rrf_scores.append(rrf_score)
        
        # Sort by RRF score
        documents.sort(key=lambda x: x.rerank_score, reverse=True)
        
        logger.info(f"ReciprocalRankReranker processed {len(documents)} documents")
        return documents
    
    def no_rerank(self, query: str, documents: List[RetrievedDocument]) -> List[RetrievedDocument]:
        """Fallback."""
        for doc in documents:
            doc.rerank_score = doc.score
        return documents
    
    def get_strategy_name(self) -> str:
        return f"rrf_k={self.k}"


class RerankerFactory:
    """Factory for creating reranking strategies."""
    
    STRATEGIES = {
        'none': NoOpReranker,
        'cross_encoder': CrossEncoderReranker,
        'llm': LLMReranker,
        'bm25': BM25Reranker,
        'rrf': ReciprocalRankReranker,
    }
    
    @classmethod
    def create(cls, 
               strategy: str, 
               llm_client=None,
               **kwargs) -> RerankerStrategy:
        """
        Create a reranking strategy.
        
        Args:
            strategy: Name of the reranking strategy
                    ('none', 'cross_encoder', 'llm', 'bm25', 'rrf')
            llm_client: LLM client (required for 'llm' strategy)
            **kwargs: Additional parameters for the strategy
        
        Returns:
            RerankerStrategy instance
        """
        if strategy not in cls.STRATEGIES:
            raise ValueError(f"Unknown reranking strategy: {strategy}. "
                           f"Available: {list(cls.STRATEGIES.keys())}")
        
        if strategy == 'cross_encoder':
            model = kwargs.get('model', 'cross-encoder/ms-marco-MiniLM-L-6-v2')
            return CrossEncoderReranker(model_name=model)
        
        if strategy == 'llm':
            return LLMReranker(llm_client=llm_client, **kwargs)
        
        if strategy == 'bm25':
            return BM25Reranker(**kwargs)
        
        if strategy == 'rrf':
            k = kwargs.get('k', 60)
            return ReciprocalRankReranker(k=k)
        
        return cls.STRATEGIES[strategy](**kwargs)
    
    @classmethod
    def create_hybrid(cls, 
                      strategies: List[str],
                      llm_client=None,
                      weights: Optional[List[float]] = None) -> RerankerStrategy:
        """Create a hybrid reranker combining multiple strategies."""
        rerankers = []
        for strategy in strategies:
            reranker = cls.create(strategy, llm_client=llm_client)
            rerankers.append(reranker)
        
        return HybridReranker(rerankers, weights)
    
    @classmethod
    def get_available_strategies(cls) -> List[str]:
        """Get list of available reranking strategies."""
        return list(cls.STRATEGIES.keys())
