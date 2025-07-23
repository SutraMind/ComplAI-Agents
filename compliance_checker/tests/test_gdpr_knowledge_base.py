"""
Unit tests for GDPR Knowledge Base functionality.
"""

import os
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import pytest
import numpy as np

from compliance_checker.knowledge.gdpr_knowledge_base import GDPRKnowledgeBase
from compliance_checker.models.gdpr import GDPRArticle, GDPRRecital, GDPRKnowledgeEntry
from compliance_checker.exceptions import DocumentProcessingError, VectorStoreError


class TestGDPRKnowledgeBase:
    """Test cases for GDPRKnowledgeBase class."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for testing."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def sample_gdpr_content(self):
        """Sample GDPR content for testing."""
        return """
        Article 6
        Lawfulness of processing
        
        1. Processing shall be lawful only if and to the extent that at least one of the following applies:
        (a) the data subject has given consent to the processing of his or her personal data for one or more specific purposes;
        (b) processing is necessary for the performance of a contract to which the data subject is party;
        
        Article 7
        Conditions for consent
        
        1. Where processing is based on consent, the controller shall be able to demonstrate that the data subject has consented to processing of his or her personal data.
        """
    
    @pytest.fixture
    def sample_recital_content(self):
        """Sample recital content for testing."""
        return """
        Recital (32)
        Consent should be given by a clear affirmative act establishing a freely given, specific, informed and unambiguous indication of the data subject's agreement to the processing of personal data relating to him or her.
        """
    
    @pytest.fixture
    def mock_embedding_model(self):
        """Mock sentence transformer model."""
        mock_model = Mock()
        mock_model.encode.return_value = np.random.rand(2, 384).astype('float32')
        return mock_model
    
    @pytest.fixture
    def knowledge_base(self, temp_dir, mock_embedding_model):
        """Create GDPRKnowledgeBase instance for testing."""
        gdpr_docs_path = Path(temp_dir) / "gdpr_docs"
        gdpr_docs_path.mkdir()
        index_path = Path(temp_dir) / "index"
        
        with patch('compliance_checker.knowledge.gdpr_knowledge_base.SentenceTransformer') as mock_st:
            mock_st.return_value = mock_embedding_model
            kb = GDPRKnowledgeBase(
                gdpr_docs_path=str(gdpr_docs_path),
                index_path=str(index_path)
            )
            return kb
    
    def test_initialization_success(self, temp_dir, mock_embedding_model):
        """Test successful initialization of knowledge base."""
        gdpr_docs_path = Path(temp_dir) / "gdpr_docs"
        gdpr_docs_path.mkdir()
        
        with patch('compliance_checker.knowledge.gdpr_knowledge_base.SentenceTransformer') as mock_st:
            mock_st.return_value = mock_embedding_model
            
            kb = GDPRKnowledgeBase(
                gdpr_docs_path=str(gdpr_docs_path),
                index_path=str(Path(temp_dir) / "index")
            )
            
            assert kb.gdpr_docs_path == gdpr_docs_path
            assert kb.embedding_model is not None
            assert kb.faiss_index is not None
            assert kb.knowledge_entries == []
    
    def test_initialization_embedding_model_failure(self, temp_dir):
        """Test initialization failure when embedding model cannot be loaded."""
        gdpr_docs_path = Path(temp_dir) / "gdpr_docs"
        gdpr_docs_path.mkdir()
        
        with patch('compliance_checker.knowledge.gdpr_knowledge_base.SentenceTransformer') as mock_st:
            mock_st.side_effect = Exception("Model loading failed")
            
            with pytest.raises(VectorStoreError, match="Failed to initialize embedding model"):
                GDPRKnowledgeBase(
                    gdpr_docs_path=str(gdpr_docs_path),
                    index_path=str(Path(temp_dir) / "index")
                )
    
    def test_build_vector_store_missing_folder(self, knowledge_base):
        """Test build_vector_store with missing GDPR_docs folder."""
        # Remove the GDPR docs folder
        shutil.rmtree(knowledge_base.gdpr_docs_path)
        
        with pytest.raises(DocumentProcessingError, match="GDPR_docs folder not found"):
            knowledge_base.build_vector_store()
    
    def test_build_vector_store_empty_folder(self, knowledge_base):
        """Test build_vector_store with empty GDPR_docs folder."""
        with pytest.raises(DocumentProcessingError, match="No GDPR documents found"):
            knowledge_base.build_vector_store()
    
    def test_build_vector_store_success(self, knowledge_base, sample_gdpr_content):
        """Test successful vector store building."""
        # Create sample GDPR document
        gdpr_file = knowledge_base.gdpr_docs_path / "gdpr.txt"
        gdpr_file.write_text(sample_gdpr_content)
        
        with patch.object(knowledge_base, '_save_index') as mock_save:
            knowledge_base.build_vector_store()
            
            # Verify knowledge entries were created
            assert len(knowledge_base.knowledge_entries) > 0
            
            # Verify articles were extracted
            assert len(knowledge_base.articles) > 0
            assert "6" in knowledge_base.articles
            assert "7" in knowledge_base.articles
            
            # Verify FAISS index was built
            assert knowledge_base.faiss_index.ntotal > 0
            
            # Verify save was called
            mock_save.assert_called_once()
    
    def test_process_document_pdf(self, knowledge_base):
        """Test processing PDF document."""
        # Create a dummy PDF file
        pdf_file = knowledge_base.gdpr_docs_path / "test.pdf"
        pdf_file.write_text("dummy pdf content")  # This would normally be binary
        
        with patch('compliance_checker.knowledge.gdpr_knowledge_base.PyPDFLoader') as mock_loader:
            mock_doc = Mock()
            mock_doc.page_content = "Article 6 test content"
            mock_doc.metadata = {'source': 'test.pdf'}
            mock_loader.return_value.load.return_value = [mock_doc]
            
            documents = knowledge_base._process_document(pdf_file)
            
            assert len(documents) > 0
            assert documents[0].metadata['source_file'] == 'test.pdf'
            assert documents[0].metadata['document_type'] == 'gdpr_regulation'
    
    def test_process_document_txt(self, knowledge_base, sample_gdpr_content):
        """Test processing text document."""
        txt_file = knowledge_base.gdpr_docs_path / "test.txt"
        txt_file.write_text(sample_gdpr_content)
        
        with patch('compliance_checker.knowledge.gdpr_knowledge_base.TextLoader') as mock_loader:
            mock_doc = Mock()
            mock_doc.page_content = sample_gdpr_content
            mock_doc.metadata = {'source': 'test.txt'}
            mock_loader.return_value.load.return_value = [mock_doc]
            
            documents = knowledge_base._process_document(txt_file)
            
            assert len(documents) > 0
            assert documents[0].metadata['source_file'] == 'test.txt'
    
    def test_process_document_unsupported_format(self, knowledge_base):
        """Test processing unsupported document format."""
        unsupported_file = knowledge_base.gdpr_docs_path / "test.docx"
        unsupported_file.write_text("content")
        
        with pytest.raises(DocumentProcessingError, match="Unsupported file format"):
            knowledge_base._process_document(unsupported_file)
    
    def test_classify_content_type(self, knowledge_base):
        """Test content type classification."""
        # Test article classification
        article_content = "Article 6 Lawfulness of processing"
        assert knowledge_base._classify_content_type(article_content) == "article"
        
        # Test recital classification
        recital_content = "Recital (32) Consent should be given"
        assert knowledge_base._classify_content_type(recital_content) == "recital"
        
        # Test definition classification
        definition_content = "Personal data means any information"
        assert knowledge_base._classify_content_type(definition_content) == "definition"
        
        # Test general classification
        general_content = "This regulation applies to"
        assert knowledge_base._classify_content_type(general_content) == "general"
    
    def test_extract_article_info(self, knowledge_base):
        """Test article information extraction."""
        content = """
        Article 6
        Lawfulness of processing
        
        Processing shall be lawful only if consent is given.
        """
        
        article = knowledge_base._extract_article_info(content, {})
        
        assert article is not None
        assert article.article_number == "6"
        assert "Lawfulness of processing" in article.title
        assert article.content == content
        assert "consent" in article.keywords
    
    def test_extract_recital_info(self, knowledge_base, sample_recital_content):
        """Test recital information extraction."""
        recital = knowledge_base._extract_recital_info(sample_recital_content, {})
        
        assert recital is not None
        assert recital.recital_number == "32"
        assert recital.content == sample_recital_content
        assert "consent" in recital.keywords
    
    def test_extract_keywords(self, knowledge_base):
        """Test keyword extraction."""
        content = "The data subject has given consent for processing personal data"
        keywords = knowledge_base._extract_keywords(content)
        
        assert "consent" in keywords
        assert "personal data" in keywords
        assert "processing" in keywords
    
    def test_query_relevant_articles(self, knowledge_base, sample_gdpr_content):
        """Test querying relevant articles."""
        # Setup knowledge base with sample content
        gdpr_file = knowledge_base.gdpr_docs_path / "gdpr.txt"
        gdpr_file.write_text(sample_gdpr_content)
        
        with patch.object(knowledge_base, '_save_index'):
            knowledge_base.build_vector_store()
        
        # Mock the search results
        with patch.object(knowledge_base.faiss_index, 'search') as mock_search:
            mock_search.return_value = (
                np.array([[0.9, 0.8]]),  # scores
                np.array([[0, 1]])       # indices
            )
            
            # Add article metadata to knowledge entries
            knowledge_base.knowledge_entries[0].metadata['article_number'] = '6'
            knowledge_base.knowledge_entries[1].metadata['article_number'] = '7'
            
            articles = knowledge_base.query_relevant_articles("consent processing", top_k=2)
            
            assert len(articles) <= 2
            mock_search.assert_called_once()
    
    def test_similarity_search(self, knowledge_base, sample_gdpr_content):
        """Test similarity search functionality."""
        # Setup knowledge base
        gdpr_file = knowledge_base.gdpr_docs_path / "gdpr.txt"
        gdpr_file.write_text(sample_gdpr_content)
        
        with patch.object(knowledge_base, '_save_index'):
            knowledge_base.build_vector_store()
        
        # Mock the search results
        with patch.object(knowledge_base.faiss_index, 'search') as mock_search:
            mock_search.return_value = (
                np.array([[0.9, 0.8]]),  # scores
                np.array([[0, 1]])       # indices
            )
            
            results = knowledge_base.similarity_search("consent", top_k=2)
            
            assert len(results) == 2
            assert all(isinstance(result[0], GDPRKnowledgeEntry) for result in results)
            assert all(isinstance(result[1], float) for result in results)
            mock_search.assert_called_once()
    
    def test_update_knowledge_base(self, knowledge_base, sample_gdpr_content):
        """Test knowledge base update functionality."""
        # Create initial document
        gdpr_file = knowledge_base.gdpr_docs_path / "gdpr.txt"
        gdpr_file.write_text(sample_gdpr_content)
        
        with patch.object(knowledge_base, 'build_vector_store') as mock_build:
            knowledge_base.update_knowledge_base()
            mock_build.assert_called_once()
    
    def test_update_knowledge_base_no_files(self, knowledge_base):
        """Test knowledge base update with no files."""
        with patch.object(knowledge_base, 'build_vector_store') as mock_build:
            knowledge_base.update_knowledge_base()
            mock_build.assert_not_called()
    
    def test_get_article_by_number(self, knowledge_base):
        """Test getting article by number."""
        # Add sample article
        article = GDPRArticle(
            article_number="6",
            title="Lawfulness of processing",
            content="Test content"
        )
        knowledge_base.articles["6"] = article
        
        retrieved_article = knowledge_base.get_article_by_number("6")
        assert retrieved_article == article
        
        # Test non-existent article
        assert knowledge_base.get_article_by_number("999") is None
    
    def test_get_all_articles(self, knowledge_base):
        """Test getting all articles."""
        # Add sample articles
        article1 = GDPRArticle(article_number="6", title="Test 1", content="Content 1")
        article2 = GDPRArticle(article_number="7", title="Test 2", content="Content 2")
        
        knowledge_base.articles["6"] = article1
        knowledge_base.articles["7"] = article2
        
        all_articles = knowledge_base.get_all_articles()
        assert len(all_articles) == 2
        assert article1 in all_articles
        assert article2 in all_articles
    
    def test_get_statistics(self, knowledge_base):
        """Test getting knowledge base statistics."""
        # Add sample data
        knowledge_base.knowledge_entries = [Mock(), Mock(), Mock()]
        knowledge_base.articles = {"6": Mock(), "7": Mock()}
        knowledge_base.recitals = {"32": Mock()}
        
        stats = knowledge_base.get_statistics()
        
        assert stats['total_entries'] == 3
        assert stats['total_articles'] == 2
        assert stats['total_recitals'] == 1
        assert 'index_size' in stats
        assert 'embedding_dimension' in stats
    
    def test_save_and_load_index(self, knowledge_base, sample_gdpr_content):
        """Test saving and loading FAISS index."""
        # Build initial knowledge base
        gdpr_file = knowledge_base.gdpr_docs_path / "gdpr.txt"
        gdpr_file.write_text(sample_gdpr_content)
        knowledge_base.build_vector_store()
        
        # Save current state
        original_entries_count = len(knowledge_base.knowledge_entries)
        original_articles_count = len(knowledge_base.articles)
        
        # Create new knowledge base instance (should load existing index)
        with patch('compliance_checker.knowledge.gdpr_knowledge_base.SentenceTransformer') as mock_st:
            mock_st.return_value = knowledge_base.embedding_model
            
            new_kb = GDPRKnowledgeBase(
                gdpr_docs_path=str(knowledge_base.gdpr_docs_path),
                index_path=str(knowledge_base.index_path)
            )
            
            # Verify loaded state
            assert len(new_kb.knowledge_entries) == original_entries_count
            assert len(new_kb.articles) == original_articles_count
    
    def test_error_handling_corrupted_document(self, knowledge_base):
        """Test error handling for corrupted documents."""
        # Create a file that will cause processing to fail
        bad_file = knowledge_base.gdpr_docs_path / "corrupted.pdf"
        bad_file.write_text("not a real pdf")
        
        with patch('compliance_checker.knowledge.gdpr_knowledge_base.PyPDFLoader') as mock_loader:
            mock_loader.side_effect = Exception("Corrupted file")
            
            with pytest.raises(DocumentProcessingError, match="Failed to process"):
                knowledge_base.build_vector_store()
    
    def test_embedding_generation_failure(self, knowledge_base, sample_gdpr_content):
        """Test handling of embedding generation failure."""
        gdpr_file = knowledge_base.gdpr_docs_path / "gdpr.txt"
        gdpr_file.write_text(sample_gdpr_content)
        
        # Mock embedding model to fail
        knowledge_base.embedding_model.encode.side_effect = Exception("Embedding failed")
        
        with pytest.raises(VectorStoreError, match="Failed to generate embeddings"):
            knowledge_base.build_vector_store()
    
    def test_faiss_index_build_failure(self, knowledge_base, sample_gdpr_content):
        """Test handling of FAISS index build failure."""
        gdpr_file = knowledge_base.gdpr_docs_path / "gdpr.txt"
        gdpr_file.write_text(sample_gdpr_content)
        
        with patch.object(knowledge_base.faiss_index, 'add') as mock_add:
            mock_add.side_effect = Exception("FAISS error")
            
            with pytest.raises(VectorStoreError, match="Failed to build FAISS index"):
                knowledge_base.build_vector_store()


class TestGDPRKnowledgeBaseIntegration:
    """Integration tests for GDPR Knowledge Base."""
    
    @pytest.fixture
    def real_temp_dir(self):
        """Create temporary directory for integration testing."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    def test_end_to_end_workflow(self, real_temp_dir):
        """Test complete end-to-end workflow with real components."""
        # Skip if sentence-transformers not available
        pytest.importorskip("sentence_transformers")
        pytest.importorskip("faiss")
        
        # Create GDPR docs directory and sample content
        gdpr_docs_path = Path(real_temp_dir) / "gdpr_docs"
        gdpr_docs_path.mkdir()
        
        sample_content = """
        Article 6
        Lawfulness of processing
        
        1. Processing shall be lawful only if and to the extent that at least one of the following applies:
        (a) the data subject has given consent to the processing of his or her personal data for one or more specific purposes;
        
        Article 7
        Conditions for consent
        
        1. Where processing is based on consent, the controller shall be able to demonstrate that the data subject has consented to processing of his or her personal data.
        """
        
        gdpr_file = gdpr_docs_path / "gdpr_sample.txt"
        gdpr_file.write_text(sample_content)
        
        # Create knowledge base
        kb = GDPRKnowledgeBase(
            gdpr_docs_path=str(gdpr_docs_path),
            index_path=str(Path(real_temp_dir) / "index"),
            embedding_model="all-MiniLM-L6-v2"
        )
        
        # Build vector store
        kb.build_vector_store()
        
        # Verify results
        assert len(kb.knowledge_entries) > 0
        assert len(kb.articles) >= 2
        assert "6" in kb.articles
        assert "7" in kb.articles
        
        # Test querying
        articles = kb.query_relevant_articles("consent processing", top_k=2)
        assert len(articles) > 0
        
        # Test similarity search
        results = kb.similarity_search("data subject consent", top_k=3)
        assert len(results) > 0
        
        # Test statistics
        stats = kb.get_statistics()
        assert stats['total_entries'] > 0
        assert stats['total_articles'] >= 2
        assert stats['index_size'] > 0