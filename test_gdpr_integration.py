#!/usr/bin/env python3
"""
Integration test for GDPR Knowledge Base with actual PDF processing.
"""

import sys
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent))

def test_pdf_processing():
    """Test PDF processing functionality."""
    print("Testing PDF processing...")
    
    try:
        import numpy as np
        from compliance_checker.knowledge.gdpr_knowledge_base import GDPRKnowledgeBase
        
        # Check if GDPR.pdf exists
        gdpr_pdf_path = Path("policies/GDPR.pdf")
        if not gdpr_pdf_path.exists():
            print("❌ GDPR.pdf not found in policies folder")
            return False
        
        print(f"✓ Found GDPR.pdf at {gdpr_pdf_path}")
        
        # Create temporary directory for testing
        temp_dir = tempfile.mkdtemp()
        try:
            # Copy GDPR.pdf to temp directory
            temp_gdpr_dir = Path(temp_dir) / "gdpr_docs"
            temp_gdpr_dir.mkdir()
            temp_gdpr_file = temp_gdpr_dir / "GDPR.pdf"
            shutil.copy2(gdpr_pdf_path, temp_gdpr_file)
            
            print("✓ Copied GDPR.pdf to temporary directory")
            
            # Mock sentence transformers to avoid dependency issues
            with patch('compliance_checker.knowledge.gdpr_knowledge_base.SENTENCE_TRANSFORMERS_AVAILABLE', True):
                with patch('compliance_checker.knowledge.gdpr_knowledge_base.SentenceTransformer') as mock_st:
                    # Create a more realistic mock that returns different embeddings
                    mock_model = Mock()
                    def mock_encode(texts, **kwargs):
                        # Return different embeddings for different texts
                        return np.random.rand(len(texts), 384).astype('float32')
                    mock_model.encode = mock_encode
                    mock_st.return_value = mock_model
                    
                    # Initialize knowledge base
                    kb = GDPRKnowledgeBase(
                        gdpr_docs_path=str(temp_gdpr_dir),
                        index_path=str(Path(temp_dir) / "index")
                    )
                    
                    print("✓ Knowledge base initialized")
                    
                    # Build vector store
                    kb.build_vector_store()
                    
                    print("✓ Vector store built successfully")
                    
                    # Check statistics
                    stats = kb.get_statistics()
                    print(f"✓ Knowledge base statistics:")
                    print(f"   - Total entries: {stats['total_entries']}")
                    print(f"   - Total articles: {stats['total_articles']}")
                    print(f"   - Total recitals: {stats['total_recitals']}")
                    print(f"   - Index size: {stats['index_size']}")
                    
                    # Verify we have some content
                    assert stats['total_entries'] > 0, "No knowledge entries created"
                    assert stats['index_size'] > 0, "FAISS index is empty"
                    
                    print("✓ Vector store contains expected content")
                    
                    # Test article retrieval
                    all_articles = kb.get_all_articles()
                    if all_articles:
                        print(f"✓ Found {len(all_articles)} articles")
                        for i, article in enumerate(all_articles[:3]):  # Show first 3
                            print(f"   - Article {article.article_number}: {article.title}")
                    else:
                        print("⚠ No articles extracted (this might be expected for complex PDFs)")
                    
                    # Test similarity search
                    test_queries = ["consent", "personal data", "processing"]
                    for query in test_queries:
                        results = kb.similarity_search(query, top_k=3)
                        print(f"✓ Similarity search for '{query}': {len(results)} results")
                        
                        if results:
                            best_result = results[0]
                            content_preview = best_result[0].content[:100].replace('\n', ' ')
                            print(f"   Best match: {content_preview}...")
                    
                    return True
                    
        finally:
            shutil.rmtree(temp_dir)
            
    except Exception as e:
        print(f"❌ PDF processing test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_error_handling():
    """Test error handling scenarios."""
    print("\nTesting error handling...")
    
    try:
        import numpy as np
        from compliance_checker.knowledge.gdpr_knowledge_base import GDPRKnowledgeBase
        from compliance_checker.exceptions import DocumentProcessingError
        
        temp_dir = tempfile.mkdtemp()
        try:
            # Test with missing GDPR docs folder
            with patch('compliance_checker.knowledge.gdpr_knowledge_base.SENTENCE_TRANSFORMERS_AVAILABLE', True):
                with patch('compliance_checker.knowledge.gdpr_knowledge_base.SentenceTransformer') as mock_st:
                    mock_model = Mock()
                    mock_model.encode.return_value = np.array([[0.1, 0.2, 0.3]])
                    mock_st.return_value = mock_model
                    
                    kb = GDPRKnowledgeBase(
                        gdpr_docs_path=str(Path(temp_dir) / "nonexistent"),
                        index_path=str(Path(temp_dir) / "index")
                    )
                    
                    try:
                        kb.build_vector_store()
                        print("❌ Expected DocumentProcessingError for missing folder")
                        return False
                    except DocumentProcessingError:
                        print("✓ Correctly raised DocumentProcessingError for missing folder")
            
            # Test with empty GDPR docs folder
            empty_dir = Path(temp_dir) / "empty_gdpr"
            empty_dir.mkdir()
            
            with patch('compliance_checker.knowledge.gdpr_knowledge_base.SENTENCE_TRANSFORMERS_AVAILABLE', True):
                with patch('compliance_checker.knowledge.gdpr_knowledge_base.SentenceTransformer') as mock_st:
                    mock_model = Mock()
                    mock_model.encode.return_value = np.array([[0.1, 0.2, 0.3]])
                    mock_st.return_value = mock_model
                    
                    kb = GDPRKnowledgeBase(
                        gdpr_docs_path=str(empty_dir),
                        index_path=str(Path(temp_dir) / "index2")
                    )
                    
                    try:
                        kb.build_vector_store()
                        print("❌ Expected DocumentProcessingError for empty folder")
                        return False
                    except DocumentProcessingError:
                        print("✓ Correctly raised DocumentProcessingError for empty folder")
            
            return True
            
        finally:
            shutil.rmtree(temp_dir)
            
    except Exception as e:
        print(f"❌ Error handling test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run integration tests."""
    print("🚀 GDPR Knowledge Base Integration Tests")
    print("=" * 60)
    
    tests = [
        test_pdf_processing,
        test_error_handling
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        print()
    
    print("=" * 60)
    print(f"Results: {passed}/{total} integration tests passed")
    
    if passed == total:
        print("🎉 All integration tests passed!")
        return True
    else:
        print("❌ Some integration tests failed")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)