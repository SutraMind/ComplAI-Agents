"""
Document and data processing components.

Contains document parsers, chain-of-thought processors, chunking strategies,
reranking modules, and the modular RAG pipeline.
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
    
    # RAG Pipeline
    'ModularRAGPipeline',
    'RAGConfig',
    'RAGPipelineBuilder',
    'create_rag_pipeline'
]