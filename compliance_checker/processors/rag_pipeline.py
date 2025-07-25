"""
Modular RAG Pipeline that combines chunking and reranking.
Allows configurable selection of chunking strategy and optional reranking.
"""

import logging
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path

from .chunking import ChunkingStrategy, ChunkingFactory, Chunk
from .reranking import RerankerStrategy, RerankerFactory, RetrievedDocument

logger = logging.getLogger(__name__)


@dataclass
class RAGConfig:
    """Configuration for the RAG pipeline."""
    # Chunking configuration
    chunking_strategy: str = "semantic"  # 'fixed', 'semantic', 'recursive', 'agentic'
    chunk_size: int = 1000
    chunk_overlap: int = 200
    min_chunk_size: int = 200
    max_chunk_size: int = 1500
    
    # Reranking configuration
    use_reranking: bool = False
    reranking_strategy: str = "none"  # 'none', 'cross_encoder', 'llm', 'bm25', 'rrf'
    
    # Retrieval configuration
    top_k: int = 10
    similarity_threshold: float = 0.0
    
    def __post_init__(self):
        """Validate configuration."""
        available_chunking = ChunkingFactory.get_available_strategies()
        if self.chunking_strategy not in available_chunking:
            raise ValueError(f"Unknown chunking strategy: {self.chunking_strategy}. "
                           f"Available: {available_chunking}")
        
        available_reranking = RerankerFactory.get_available_strategies()
        if self.reranking_strategy not in available_reranking:
            raise ValueError(f"Unknown reranking strategy: {self.reranking_strategy}. "
                           f"Available: {available_reranking}")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'chunking_strategy': self.chunking_strategy,
            'chunk_size': self.chunk_size,
            'chunk_overlap': self.chunk_overlap,
            'min_chunk_size': self.min_chunk_size,
            'max_chunk_size': self.max_chunk_size,
            'use_reranking': self.use_reranking,
            'reranking_strategy': self.reranking_strategy,
            'top_k': self.top_k,
            'similarity_threshold': self.similarity_threshold
        }


class ModularRAGPipeline:
    """
    Modular RAG pipeline with configurable chunking and optional reranking.
    
    Usage:
        # Create pipeline with default config
        pipeline = ModularRAGPipeline(llm_client=client, knowledge_base=kb)
        
        # Or with custom config
        config = RAGConfig(
            chunking_strategy='agentic',
            use_reranking=True,
            reranking_strategy='cross_encoder'
        )
        pipeline = ModularRAGPipeline(llm_client=client, knowledge_base=kb, config=config)
        
        # Query
        results = pipeline.retrieve("GDPR consent requirements")
    """
    
    def __init__(self, 
                 llm_client=None,
                 knowledge_base=None,
                 embedding_model=None,
                 config: Optional[RAGConfig] = None):
        """
        Initialize the RAG pipeline.
        
        Args:
            llm_client: LLM client for agentic chunking and LLM reranking
            knowledge_base: Knowledge base for document retrieval
            embedding_model: Embedding model for semantic search
            config: RAG configuration (uses defaults if not provided)
        """
        self.config = config or RAGConfig()
        self.llm_client = llm_client
        self.knowledge_base = knowledge_base
        self.embedding_model = embedding_model
        
        # Initialize chunking strategy
        self.chunker = self._init_chunking_strategy()
        
        # Initialize reranking strategy
        self.reranker = self._init_reranking_strategy()
        
        # Store chunks
        self.document_chunks: List[Chunk] = []
        self.chunk_embeddings: Optional[np.ndarray] = None
        
        # Stats
        self.stats = {
            'total_documents': 0,
            'total_chunks': 0,
            'retrieval_calls': 0,
            'reranking_applied': 0
        }
        
        logger.info(f"Initialized ModularRAGPipeline with chunking={self.config.chunking_strategy}, "
                   f"reranking={'enabled' if self.config.use_reranking else 'disabled'}")
    
    def _init_chunking_strategy(self) -> ChunkingStrategy:
        """Initialize the chunking strategy."""
        chunking_kwargs = {
            'chunk_size': self.config.chunk_size,
            'overlap': self.config.chunk_overlap,
            'min_chunk_size': self.config.min_chunk_size,
            'max_chunk_size': self.config.max_chunk_size
        }
        
        if self.config.chunking_strategy == 'agentic':
            chunking_kwargs['llm_client'] = self.llm_client
        
        return ChunkingFactory.create(
            self.config.chunking_strategy,
            llm_client=self.llm_client,
            **chunking_kwargs
        )
    
    def _init_reranking_strategy(self) -> RerankerStrategy:
        """Initialize the reranking strategy."""
        if not self.config.use_reranking:
            return RerankerFactory.create('none')
        
        reranking_kwargs = {}
        if self.config.reranking_strategy == 'llm':
            reranking_kwargs['llm_client'] = self.llm_client
        
        return RerankerFactory.create(
            self.config.reranking_strategy,
            llm_client=self.llm_client,
            **reranking_kwargs
        )
    
    def ingest_document(self, 
                        text: str, 
                        metadata: Optional[Dict[str, Any]] = None) -> List[Chunk]:
        """
        Ingest a document and chunk it.
        
        Args:
            text: Document text to process
            metadata: Optional metadata for the document
            
        Returns:
            List of created chunks
        """
        metadata = metadata or {}
        
        # Chunk the document
        chunks = self.chunker.chunk(
            text,
            chunk_size=self.config.chunk_size,
            overlap=self.config.chunk_overlap,
            min_chunk_size=self.config.min_chunk_size,
            max_chunk_size=self.config.max_chunk_size
        )
        
        # Add metadata to each chunk
        for chunk in chunks:
            chunk.metadata.update(metadata)
        
        # Store chunks
        self.document_chunks.extend(chunks)
        self.stats['total_documents'] += 1
        self.stats['total_chunks'] += len(chunks)
        
        logger.info(f"Ingested document: created {len(chunks)} chunks using {self.config.chunking_strategy}")
        return chunks
    
    def ingest_documents(self, 
                        documents: List[Tuple[str, Dict[str, Any]]]) -> List[Chunk]:
        """
        Ingest multiple documents.
        
        Args:
            documents: List of (text, metadata) tuples
            
        Returns:
            List of all created chunks
        """
        all_chunks = []
        for text, metadata in documents:
            chunks = self.ingest_document(text, metadata)
            all_chunks.extend(chunks)
        
        return all_chunks
    
    def build_chunk_index(self, embedding_model=None) -> None:
        """
        Build an index of chunk embeddings for fast retrieval.
        
        Args:
            embedding_model: Model to use for embeddings
        """
        if not self.document_chunks:
            logger.warning("No chunks to index")
            return
        
        model = embedding_model or self.embedding_model
        if not model:
            raise ValueError("No embedding model provided")
        
        # Get embeddings for all chunks
        texts = [chunk.text for chunk in self.document_chunks]
        embeddings = model.encode(texts, show_progress_bar=True)
        
        # Normalize embeddings
        self.chunk_embeddings = embeddings / np.linalg.norm(embeddings, axis=1, keepdims=True)
        
        logger.info(f"Built chunk index with {len(self.chunk_embeddings)} embeddings")
    
    def retrieve(self, 
                 query: str, 
                 top_k: Optional[int] = None,
                 use_reranking: Optional[bool] = None) -> List[RetrievedDocument]:
        """
        Retrieve relevant documents for a query.
        
        Args:
            query: The search query
            top_k: Number of results to return (uses config if not provided)
            use_reranking: Override reranking setting
            
        Returns:
            List of retrieved documents with scores
        """
        top_k = top_k or self.config.top_k
        use_reranking = use_reranking if use_reranking is not None else self.config.use_reranking
        
        self.stats['retrieval_calls'] += 1
        
        if not self.document_chunks:
            logger.warning("No documents indexed")
            return []
        
        # Get query embedding
        if self.embedding_model:
            query_embedding = self.embedding_model.encode([query])
            query_embedding = query_embedding / np.linalg.norm(query_embedding)
            query_embedding = query_embedding.astype('float32')
            
            # Search using FAISS-like approach (or actual FAISS if available)
            if self.chunk_embeddings is not None:
                scores = np.dot(self.chunk_embeddings, query_embedding.T).flatten()
                top_indices = np.argsort(scores)[::-1][:top_k * 2]
            else:
                # Fallback to simple scoring if no index
                top_indices = range(min(top_k * 2, len(self.document_chunks)))
                scores = [1.0] * len(self.document_chunks)
        else:
            # Use knowledge base if available
            if self.knowledge_base:
                return self._retrieve_from_kb(query, top_k, use_reranking)
            else:
                logger.error("No embedding model or knowledge base available")
                return []
        
        # Create retrieved documents
        retrieved = []
        for idx in top_indices:
            if idx < len(self.document_chunks):
                chunk = self.document_chunks[idx]
                score = float(scores[idx]) if isinstance(scores, np.ndarray) else scores[idx]
                
                if score >= self.config.similarity_threshold:
                    retrieved.append(RetrievedDocument(
                        content=chunk.text,
                        score=score,
                        metadata={
                            'chunk_id': chunk.chunk_id,
                            'start_index': chunk.start_index,
                            'end_index': chunk.end_index,
                            'chunk_metadata': chunk.metadata
                        }
                    ))
        
        # Apply reranking if enabled
        if use_reranking and self.reranker and self.config.use_reranking:
            retrieved = self.reranker.rerank(query, retrieved)
            self.stats['reranking_applied'] += 1
        
        # Limit to top_k
        retrieved = retrieved[:top_k]
        
        logger.info(f"Retrieved {len(retrieved)} documents for query: {query[:50]}...")
        return retrieved
    
    def _retrieve_from_kb(self, query: str, top_k: int, use_reranking: bool) -> List[RetrievedDocument]:
        """Retrieve from knowledge base."""
        if not self.knowledge_base:
            return []
        
        articles = self.knowledge_base.query_relevant_articles(query, top_k=top_k)
        
        retrieved = []
        for article in articles:
            retrieved.append(RetrievedDocument(
                content=article.content,
                score=getattr(article, 'relevance_score', 0.5),
                metadata={
                    'article_number': article.article_number,
                    'title': article.title,
                    'keywords': article.keywords
                }
            ))
        
        # Apply reranking if enabled
        if use_reranking and self.reranker:
            retrieved = self.reranker.rerank(query, retrieved)
            self.stats['reranking_applied'] += 1
        
        return retrieved
    
    def update_config(self, config: RAGConfig) -> None:
        """Update the pipeline configuration."""
        self.config = config
        
        # Reinitialize chunker and reranker
        self.chunker = self._init_chunking_strategy()
        self.reranker = self._init_reranking_strategy()
        
        logger.info(f"Updated pipeline config: {config.to_dict()}")
    
    def set_chunking_strategy(self, strategy: str, **kwargs) -> None:
        """Change chunking strategy at runtime."""
        self.config.chunking_strategy = strategy
        
        # Update with new params
        if 'chunk_size' in kwargs:
            self.config.chunk_size = kwargs['chunk_size']
        if 'chunk_overlap' in kwargs:
            self.config.chunk_overlap = kwargs['chunk_overlap']
        
        # Reinitialize chunker
        self.chunker = self._init_chunking_strategy()
        
        logger.info(f"Changed chunking strategy to: {strategy}")
    
    def set_reranking(self, enabled: bool, strategy: Optional[str] = None) -> None:
        """Enable or disable reranking at runtime."""
        self.config.use_reranking = enabled
        
        if strategy:
            self.config.reranking_strategy = strategy
        
        # Reinitialize reranker
        self.reranker = self._init_reranking_strategy()
        
        logger.info(f"Reranking {'enabled' if enabled else 'disabled'}" + 
                   (f" with strategy: {strategy}" if strategy else ""))
    
    def get_stats(self) -> Dict[str, Any]:
        """Get pipeline statistics."""
        stats = self.stats.copy()
        stats['config'] = self.config.to_dict()
        stats['total_chunks_indexed'] = len(self.document_chunks)
        stats['chunking_strategy'] = self.chunker.get_strategy_name()
        stats['reranking_strategy'] = self.reranker.get_strategy_name()
        return stats
    
    def clear(self) -> None:
        """Clear all indexed documents."""
        self.document_chunks = []
        self.chunk_embeddings = None
        self.stats = {
            'total_documents': 0,
            'total_chunks': 0,
            'retrieval_calls': 0,
            'reranking_applied': 0
        }
        logger.info("Cleared pipeline index")


class RAGPipelineBuilder:
    """Builder for creating RAG pipelines with fluent API."""
    
    def __init__(self):
        self._llm_client = None
        self._knowledge_base = None
        self._embedding_model = None
        self._config = RAGConfig()
    
    def with_llm_client(self, client) -> 'RAGPipelineBuilder':
        """Set LLM client."""
        self._llm_client = client
        return self
    
    def with_knowledge_base(self, kb) -> 'RAGPipelineBuilder':
        """Set knowledge base."""
        self._knowledge_base = kb
        return self
    
    def with_embedding_model(self, model) -> 'RAGPipelineBuilder':
        """Set embedding model."""
        self._embedding_model = model
        return self
    
    def with_chunking_strategy(self, strategy: str, **kwargs) -> 'RAGPipelineBuilder':
        """Set chunking strategy."""
        self._config.chunking_strategy = strategy
        for key, value in kwargs.items():
            if hasattr(self._config, key):
                setattr(self._config, key, value)
        return self
    
    def with_reranking(self, enabled: bool = True, strategy: str = 'none') -> 'RAGPipelineBuilder':
        """Configure reranking."""
        self._config.use_reranking = enabled
        self._config.reranking_strategy = strategy
        return self
    
    def with_top_k(self, top_k: int) -> 'RAGPipelineBuilder':
        """Set top_k for retrieval."""
        self._config.top_k = top_k
        return self
    
    def build(self) -> ModularRAGPipeline:
        """Build the RAG pipeline."""
        return ModularRAGPipeline(
            llm_client=self._llm_client,
            knowledge_base=self._knowledge_base,
            embedding_model=self._embedding_model,
            config=self._config
        )


# Convenience function
def create_rag_pipeline(
    chunking_strategy: str = "semantic",
    use_reranking: bool = False,
    reranking_strategy: str = "none",
    llm_client=None,
    knowledge_base=None,
    embedding_model=None,
    **kwargs
) -> ModularRAGPipeline:
    """
    Create a RAG pipeline with specified configuration.
    
    Example:
        pipeline = create_rag_pipeline(
            chunking_strategy='agentic',
            use_reranking=True,
            reranking_strategy='cross_encoder',
            llm_client=client
        )
    """
    config = RAGConfig(
        chunking_strategy=chunking_strategy,
        use_reranking=use_reranking,
        reranking_strategy=reranking_strategy,
        **kwargs
    )
    
    return ModularRAGPipeline(
        llm_client=llm_client,
        knowledge_base=knowledge_base,
        embedding_model=embedding_model,
        config=config
    )
