"""
Document and data processing components.

Contains document parsers, chain-of-thought processors, chunking strategies,
reranking modules, query expansion, and the modular RAG pipeline.
"""

from .base import (
    DocumentProcessor as BaseDocumentProcessor,
    ChainOfThoughtProcessor,
    ReportGenerator,
    KnowledgeBaseProcessor
)
from .document_processor import DocumentProcessor

# Chunking
from .chunking import (
    ChunkingStrategy,
    ChunkingFactory,
    Chunk,
    FixedSizeChunking,
    SemanticChunking,
    RecursiveChunking,
    AgenticChunking
)

# Reranking
from .reranking import (
    RerankerStrategy,
    RerankerFactory,
    RetrievedDocument,
    NoOpReranker,
    CrossEncoderReranker,
    LLMReranker,
    BM25Reranker,
    ReciprocalRankReranker,
    HybridReranker
)

# Query Expansion
from .query_expansion import (
    QueryExpansionStrategy,
    QueryExpansionFactory,
    ExpandedQuery,
    NoExpansionStrategy,
    SynonymExpansionStrategy,
    LLMExpansionStrategy,
    HybridExpansionStrategy
)

# RAG Pipeline
from .rag_pipeline import (
    ModularRAGPipeline,
    RAGConfig,
    RAGPipelineBuilder,
    create_rag_pipeline
)

__all__ = [
    # Base
    'BaseDocumentProcessor',
    'DocumentProcessor',
    'ChainOfThoughtProcessor',
    'ReportGenerator',
    'KnowledgeBaseProcessor',
    
    # Chunking
    'ChunkingStrategy',
    'ChunkingFactory',
    'Chunk',
    'FixedSizeChunking',
    'SemanticChunking',
    'RecursiveChunking',
    'AgenticChunking',
    
    # Reranking
    'RerankerStrategy',
    'RerankerFactory',
    'RetrievedDocument',
    'NoOpReranker',
    'CrossEncoderReranker',
    'LLMReranker',
    'BM25Reranker',
    'ReciprocalRankReranker',
    'HybridReranker',
    
    # Query Expansion
    'QueryExpansionStrategy',
    'QueryExpansionFactory',
    'ExpandedQuery',
    'NoExpansionStrategy',
    'SynonymExpansionStrategy',
    'LLMExpansionStrategy',
    'HybridExpansionStrategy',
    
    # RAG Pipeline
    'ModularRAGPipeline',
    'RAGConfig',
    'RAGPipelineBuilder',
    'create_rag_pipeline'
]