"""
GDPR Knowledge Base implementation using FAISS vector storage.
"""

import os
import logging
import pickle
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import json

import faiss
import numpy as np
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain.schema import Document

try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SentenceTransformer = None
    SENTENCE_TRANSFORMERS_AVAILABLE = False

from ..models.gdpr import GDPRArticle, GDPRRecital, GDPRKnowledgeEntry
from ..exceptions import VectorStoreError, DocumentProcessingError


logger = logging.getLogger(__name__)


class GDPRKnowledgeBase:
    """
    GDPR Knowledge Base that processes documents from GDPR_docs folder using LangChain
    and provides FAISS vector storage for similarity search.
    """
    
    def __init__(self, gdpr_docs_path: str = "policies", 
                 index_path: str = "gdpr_index",
                 embedding_model: str = "all-MiniLM-L6-v2"):
        """
        Initialize GDPR Knowledge Base.
        
        Args:
            gdpr_docs_path: Path to folder containing GDPR documents
            index_path: Path to store FAISS index and metadata
            embedding_model: Sentence transformer model for embeddings
        """
        self.gdpr_docs_path = Path(gdpr_docs_path)
        self.index_path = Path(index_path)
        self.embedding_model_name = embedding_model
        
        # Initialize components
        self.embedding_model = None
        self.faiss_index = None
        self.knowledge_entries: List[GDPRKnowledgeEntry] = []
        self.articles: Dict[str, GDPRArticle] = {}
        self.recitals: Dict[str, GDPRRecital] = {}
        
        # Text splitter for chunking documents
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            separators=["\n\n", "\n", ". ", " ", ""]
        )
        
        # Ensure directories exist
        self.index_path.mkdir(parents=True, exist_ok=True)
        
        # Initialize embedding model
        self._initialize_embedding_model()
        
        # Load existing index if available
        self._load_existing_index()
    
    def _initialize_embedding_model(self) -> None:
        """Initialize the sentence transformer model."""
        if not SENTENCE_TRANSFORMERS_AVAILABLE:
            logger.error("sentence-transformers library is not available")
            raise VectorStoreError("sentence-transformers library is required but not installed")
        
        try:
            logger.info(f"Loading embedding model: {self.embedding_model_name}")
            self.embedding_model = SentenceTransformer(self.embedding_model_name)
            logger.info("Embedding model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load embedding model: {e}")
            raise VectorStoreError(f"Failed to initialize embedding model: {e}")
    
    def _load_existing_index(self) -> None:
        """Load existing FAISS index and metadata if available."""
        index_file = self.index_path / "gdpr.index"
        metadata_file = self.index_path / "metadata.pkl"
        
        if index_file.exists() and metadata_file.exists():
            try:
                logger.info("Loading existing FAISS index")
                self.faiss_index = faiss.read_index(str(index_file))
                
                with open(metadata_file, 'rb') as f:
                    metadata = pickle.load(f)
                    self.knowledge_entries = metadata.get('knowledge_entries', [])
                    self.articles = metadata.get('articles', {})
                    self.recitals = metadata.get('recitals', {})
                
                logger.info(f"Loaded {len(self.knowledge_entries)} knowledge entries")
            except Exception as e:
                logger.warning(f"Failed to load existing index: {e}")
                self._initialize_empty_index()
        else:
            self._initialize_empty_index()
    
    def _initialize_empty_index(self) -> None:
        """Initialize empty FAISS index."""
        # Get embedding dimension from model
        sample_embedding = self.embedding_model.encode(["sample text"])
        embedding_dim = sample_embedding.shape[1]
        
        # Create FAISS index (using IndexFlatIP for cosine similarity)
        self.faiss_index = faiss.IndexFlatIP(embedding_dim)
        logger.info(f"Initialized empty FAISS index with dimension {embedding_dim}")
    
    def build_vector_store(self) -> None:
        """
        Build the GDPR vector store from documents in the GDPR_docs folder.
        
        Raises:
            DocumentProcessingError: If GDPR_docs folder is missing or empty
            VectorStoreError: If vector store creation fails
        """
        logger.info("Building GDPR vector store")
        
        # Check if GDPR docs folder exists
        if not self.gdpr_docs_path.exists():
            error_msg = f"GDPR_docs folder not found at {self.gdpr_docs_path}"
            logger.error(error_msg)
            raise DocumentProcessingError(error_msg)
        
        # Get all GDPR documents
        gdpr_files = list(self.gdpr_docs_path.glob("*.pdf")) + \
                    list(self.gdpr_docs_path.glob("*.txt"))
        
        if not gdpr_files:
            error_msg = f"No GDPR documents found in {self.gdpr_docs_path}"
            logger.error(error_msg)
            raise DocumentProcessingError(error_msg)
        
        logger.info(f"Found {len(gdpr_files)} GDPR documents")
        
        # Process each document
        all_documents = []
        for file_path in gdpr_files:
            try:
                documents = self._process_document(file_path)
                all_documents.extend(documents)
                logger.info(f"Processed {file_path.name}: {len(documents)} chunks")
            except Exception as e:
                logger.error(f"Failed to process {file_path}: {e}")
                raise DocumentProcessingError(f"Failed to process {file_path}: {e}")
        
        if not all_documents:
            raise DocumentProcessingError("No content extracted from GDPR documents")
        
        # Create knowledge entries and embeddings
        self._create_knowledge_entries(all_documents)
        
        # Save the index
        self._save_index()
        
        logger.info(f"Successfully built vector store with {len(self.knowledge_entries)} entries")
    
    def _process_document(self, file_path: Path) -> List[Document]:
        """
        Process a single GDPR document.
        
        Args:
            file_path: Path to the document
            
        Returns:
            List of LangChain Document objects
        """
        try:
            if file_path.suffix.lower() == '.pdf':
                loader = PyPDFLoader(str(file_path))
            elif file_path.suffix.lower() == '.txt':
                loader = TextLoader(str(file_path))
            else:
                raise DocumentProcessingError(f"Unsupported file format: {file_path.suffix}")
            
            # Load and split document
            documents = loader.load()
            split_documents = self.text_splitter.split_documents(documents)
            
            # Add metadata
            for doc in split_documents:
                doc.metadata.update({
                    'source_file': file_path.name,
                    'document_type': 'gdpr_regulation'
                })
            
            return split_documents
            
        except Exception as e:
            logger.error(f"Error processing document {file_path}: {e}")
            raise DocumentProcessingError(f"Failed to process {file_path}: {e}")
    
    def _create_knowledge_entries(self, documents: List[Document]) -> None:
        """
        Create knowledge entries from processed documents and generate embeddings.
        
        Args:
            documents: List of processed LangChain documents
        """
        logger.info("Creating knowledge entries and generating embeddings")
        
        # Clear existing entries
        self.knowledge_entries = []
        self.articles = {}
        self.recitals = {}
        
        # Process documents and extract structured information
        for i, doc in enumerate(documents):
            # Create knowledge entry
            entry = GDPRKnowledgeEntry(
                entry_id=f"entry_{i}",
                entry_type=self._classify_content_type(doc.page_content),
                content=doc.page_content,
                metadata=doc.metadata
            )
            
            # Try to extract structured information
            if entry.entry_type == "article":
                article = self._extract_article_info(doc.page_content, doc.metadata)
                if article:
                    self.articles[article.article_number] = article
                    entry.metadata['article_number'] = article.article_number
                    entry.metadata['article_title'] = article.title
            
            elif entry.entry_type == "recital":
                recital = self._extract_recital_info(doc.page_content, doc.metadata)
                if recital:
                    self.recitals[recital.recital_number] = recital
                    entry.metadata['recital_number'] = recital.recital_number
            
            self.knowledge_entries.append(entry)
        
        # Generate embeddings for all entries
        self._generate_embeddings()
        
        # Build FAISS index
        self._build_faiss_index()
    
    def _classify_content_type(self, content: str) -> str:
        """
        Classify the type of GDPR content.
        
        Args:
            content: Text content to classify
            
        Returns:
            Content type: "article", "recital", "definition", or "general"
        """
        content_lower = content.lower()
        
        if "article" in content_lower and any(char.isdigit() for char in content):
            return "article"
        elif "recital" in content_lower and any(char.isdigit() for char in content):
            return "recital"
        elif "definition" in content_lower or "means" in content_lower:
            return "definition"
        else:
            return "general"
    
    def _extract_article_info(self, content: str, metadata: Dict[str, Any]) -> Optional[GDPRArticle]:
        """
        Extract structured article information from content.
        
        Args:
            content: Article content
            metadata: Document metadata
            
        Returns:
            GDPRArticle object or None if extraction fails
        """
        try:
            # Simple extraction logic - can be enhanced with more sophisticated parsing
            lines = content.split('\n')
            article_number = None
            title = None
            
            for line in lines:
                line = line.strip()
                if line.lower().startswith('article') and any(char.isdigit() for char in line):
                    # Extract article number and title
                    parts = line.split()
                    for i, part in enumerate(parts):
                        if part.lower() == 'article' and i + 1 < len(parts):
                            # Get the number (might include periods, letters)
                            number_part = parts[i + 1].rstrip('.')
                            article_number = number_part
                            
                            # Get title (rest of the line after article number)
                            if len(parts) > i + 2:
                                title = ' '.join(parts[i + 2:])
                            break
                    break
            
            if article_number:
                # Extract keywords from content
                keywords = self._extract_keywords(content)
                
                return GDPRArticle(
                    article_number=article_number,
                    title=title or f"Article {article_number}",
                    content=content,
                    keywords=keywords
                )
        
        except Exception as e:
            logger.warning(f"Failed to extract article info: {e}")
        
        return None
    
    def _extract_recital_info(self, content: str, metadata: Dict[str, Any]) -> Optional[GDPRRecital]:
        """
        Extract structured recital information from content.
        
        Args:
            content: Recital content
            metadata: Document metadata
            
        Returns:
            GDPRRecital object or None if extraction fails
        """
        try:
            # Simple extraction logic for recitals
            lines = content.split('\n')
            recital_number = None
            
            for line in lines:
                line = line.strip()
                if line.lower().startswith('recital') or '(' in line and ')' in line:
                    # Look for recital number in parentheses
                    import re
                    match = re.search(r'\((\d+)\)', line)
                    if match:
                        recital_number = match.group(1)
                        break
            
            if recital_number:
                keywords = self._extract_keywords(content)
                
                return GDPRRecital(
                    recital_number=recital_number,
                    content=content,
                    keywords=keywords
                )
        
        except Exception as e:
            logger.warning(f"Failed to extract recital info: {e}")
        
        return None
    
    def _extract_keywords(self, content: str) -> List[str]:
        """
        Extract keywords from content using simple heuristics.
        
        Args:
            content: Text content
            
        Returns:
            List of extracted keywords
        """
        # Common GDPR-related keywords
        gdpr_keywords = [
            'personal data', 'processing', 'consent', 'controller', 'processor',
            'data subject', 'lawful basis', 'legitimate interest', 'privacy',
            'protection', 'rights', 'breach', 'notification', 'assessment',
            'impact', 'dpo', 'supervisory authority', 'transfer', 'adequacy'
        ]
        
        content_lower = content.lower()
        found_keywords = []
        
        for keyword in gdpr_keywords:
            if keyword in content_lower:
                found_keywords.append(keyword)
        
        return found_keywords
    
    def _generate_embeddings(self) -> None:
        """Generate embeddings for all knowledge entries."""
        logger.info("Generating embeddings for knowledge entries")
        
        texts = [entry.content for entry in self.knowledge_entries]
        
        try:
            embeddings = self.embedding_model.encode(texts, show_progress_bar=True)
            
            # Normalize embeddings for cosine similarity
            embeddings = embeddings / np.linalg.norm(embeddings, axis=1, keepdims=True)
            
            # Store embeddings in knowledge entries
            for entry, embedding in zip(self.knowledge_entries, embeddings):
                entry.embedding = embedding.tolist()
            
            logger.info(f"Generated embeddings for {len(self.knowledge_entries)} entries")
            
        except Exception as e:
            logger.error(f"Failed to generate embeddings: {e}")
            raise VectorStoreError(f"Failed to generate embeddings: {e}")
    
    def _build_faiss_index(self) -> None:
        """Build FAISS index from embeddings."""
        logger.info("Building FAISS index")
        
        try:
            # Get embeddings as numpy array
            embeddings = np.array([entry.embedding for entry in self.knowledge_entries])
            embeddings = embeddings.astype('float32')
            
            # Add to FAISS index
            self.faiss_index.add(embeddings)
            
            logger.info(f"Built FAISS index with {self.faiss_index.ntotal} vectors")
            
        except Exception as e:
            logger.error(f"Failed to build FAISS index: {e}")
            raise VectorStoreError(f"Failed to build FAISS index: {e}")
    
    def query_relevant_articles(self, query: str, top_k: int = 5) -> List[GDPRArticle]:
        """
        Query for relevant GDPR articles using similarity search.
        
        Args:
            query: Search query
            top_k: Number of top results to return
            
        Returns:
            List of relevant GDPRArticle objects
        """
        try:
            # Get query embedding
            query_embedding = self.embedding_model.encode([query])
            query_embedding = query_embedding / np.linalg.norm(query_embedding, axis=1, keepdims=True)
            query_embedding = query_embedding.astype('float32')
            
            # Search FAISS index
            scores, indices = self.faiss_index.search(query_embedding, top_k * 2)  # Get more to filter
            
            # Filter for articles and collect unique ones
            articles = []
            seen_articles = set()
            
            for score, idx in zip(scores[0], indices[0]):
                if idx < len(self.knowledge_entries):
                    entry = self.knowledge_entries[idx]
                    
                    # Look for associated article
                    article_number = entry.metadata.get('article_number')
                    if article_number and article_number in self.articles:
                        if article_number not in seen_articles:
                            article = self.articles[article_number]
                            article.relevance_score = float(score)
                            articles.append(article)
                            seen_articles.add(article_number)
                    
                    # If we have enough articles, break
                    if len(articles) >= top_k:
                        break
            
            logger.info(f"Found {len(articles)} relevant articles for query: {query[:50]}...")
            return articles
            
        except Exception as e:
            logger.error(f"Failed to query articles: {e}")
            raise VectorStoreError(f"Failed to query articles: {e}")
    
    def similarity_search(self, query: str, top_k: int = 10) -> List[Tuple[GDPRKnowledgeEntry, float]]:
        """
        Perform similarity search on the knowledge base.
        
        Args:
            query: Search query
            top_k: Number of top results to return
            
        Returns:
            List of tuples (GDPRKnowledgeEntry, similarity_score)
        """
        try:
            # Get query embedding
            query_embedding = self.embedding_model.encode([query])
            query_embedding = query_embedding / np.linalg.norm(query_embedding, axis=1, keepdims=True)
            query_embedding = query_embedding.astype('float32')
            
            # Search FAISS index
            scores, indices = self.faiss_index.search(query_embedding, top_k)
            
            # Collect results
            results = []
            for score, idx in zip(scores[0], indices[0]):
                if idx < len(self.knowledge_entries):
                    entry = self.knowledge_entries[idx]
                    results.append((entry, float(score)))
            
            logger.info(f"Similarity search returned {len(results)} results")
            return results
            
        except Exception as e:
            logger.error(f"Failed to perform similarity search: {e}")
            raise VectorStoreError(f"Failed to perform similarity search: {e}")
    
    def update_knowledge_base(self) -> None:
        """
        Update the knowledge base when new GDPR documents are added.
        """
        logger.info("Updating GDPR knowledge base")
        
        # Check if there are new or modified files
        current_files = set(self.gdpr_docs_path.glob("*.pdf")) | set(self.gdpr_docs_path.glob("*.txt"))
        
        if current_files:
            # Rebuild the entire knowledge base
            # In a production system, you might want to implement incremental updates
            self.build_vector_store()
            logger.info("Knowledge base updated successfully")
        else:
            logger.warning("No GDPR documents found for update")
    
    def _save_index(self) -> None:
        """Save FAISS index and metadata to disk."""
        try:
            # Save FAISS index
            index_file = self.index_path / "gdpr.index"
            faiss.write_index(self.faiss_index, str(index_file))
            
            # Save metadata
            metadata_file = self.index_path / "metadata.pkl"
            metadata = {
                'knowledge_entries': self.knowledge_entries,
                'articles': self.articles,
                'recitals': self.recitals
            }
            
            with open(metadata_file, 'wb') as f:
                pickle.dump(metadata, f)
            
            logger.info("FAISS index and metadata saved successfully")
            
        except Exception as e:
            logger.error(f"Failed to save index: {e}")
            raise VectorStoreError(f"Failed to save index: {e}")
    
    def get_article_by_number(self, article_number: str) -> Optional[GDPRArticle]:
        """
        Get a specific GDPR article by its number.
        
        Args:
            article_number: Article number to retrieve
            
        Returns:
            GDPRArticle object or None if not found
        """
        return self.articles.get(article_number)
    
    def get_all_articles(self) -> List[GDPRArticle]:
        """
        Get all GDPR articles in the knowledge base.
        
        Returns:
            List of all GDPRArticle objects
        """
        return list(self.articles.values())
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about the knowledge base.
        
        Returns:
            Dictionary with knowledge base statistics
        """
        return {
            'total_entries': len(self.knowledge_entries),
            'total_articles': len(self.articles),
            'total_recitals': len(self.recitals),
            'index_size': self.faiss_index.ntotal if self.faiss_index else 0,
            'embedding_dimension': self.faiss_index.d if self.faiss_index else 0
        }