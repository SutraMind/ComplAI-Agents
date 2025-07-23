#!/usr/bin/env python3
"""
Basic test for GDPR Knowledge Base without heavy dependencies.
"""

import sys
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent))

def test_basic_imports():
    """Test that basic imports work."""
    print("Testing basic imports...")
    
    try:
        from compliance_checker.models.gdpr import GDPRArticle, GDPRRecital, GDPRKnowledgeEntry
        print("✓ GDPR models imported successfully")
        
        from compliance_checker.exceptions import DocumentProcessingError, VectorStoreError
        print("✓ Exceptions imported successfully")
        
        # Test model creation
        article = GDPRArticle(
            article_number="6",
            title="Lawfulness of processing",
            content="Test content",
            keywords=["consent", "processing"]
        )
        print(f"✓ GDPRArticle created: {article.get_full_reference()}")
        
        recital = GDPRRecital(
            recital_number="32",
            content="Test recital content",
            keywords=["consent"]
        )
        print(f"✓ GDPRRecital created: Recital {recital.recital_number}")
        
        entry = GDPRKnowledgeEntry(
            entry_id="test_1",
            entry_type="article",
            content="Test knowledge entry"
        )
        print(f"✓ GDPRKnowledgeEntry created: {entry.entry_id}")
        
        return True
        
    except Exception as e:
        print(f"❌ Import test failed: {e}")
        return False

def test_knowledge_base_structure():
    """Test knowledge base class structure without heavy dependencies."""
    print("\nTesting knowledge base structure...")
    
    try:
        import numpy as np
        # Mock the sentence transformers import
        with patch('compliance_checker.knowledge.gdpr_knowledge_base.SENTENCE_TRANSFORMERS_AVAILABLE', True):
            with patch('compliance_checker.knowledge.gdpr_knowledge_base.SentenceTransformer') as mock_st:
                mock_model = Mock()
                mock_model.encode.return_value = np.array([[0.1, 0.2, 0.3]])
                mock_st.return_value = mock_model
                
                from compliance_checker.knowledge.gdpr_knowledge_base import GDPRKnowledgeBase
                
                # Create temporary directory
                temp_dir = tempfile.mkdtemp()
                try:
                    gdpr_docs_path = Path(temp_dir) / "gdpr_docs"
                    gdpr_docs_path.mkdir()
                    index_path = Path(temp_dir) / "index"
                    
                    # Test initialization
                    kb = GDPRKnowledgeBase(
                        gdpr_docs_path=str(gdpr_docs_path),
                        index_path=str(index_path)
                    )
                    
                    print("✓ GDPRKnowledgeBase initialized successfully")
                    
                    # Test basic methods exist
                    assert hasattr(kb, 'build_vector_store')
                    assert hasattr(kb, 'query_relevant_articles')
                    assert hasattr(kb, 'similarity_search')
                    assert hasattr(kb, 'update_knowledge_base')
                    assert hasattr(kb, 'get_article_by_number')
                    assert hasattr(kb, 'get_all_articles')
                    assert hasattr(kb, 'get_statistics')
                    
                    print("✓ All required methods are present")
                    
                    # Test statistics
                    stats = kb.get_statistics()
                    assert isinstance(stats, dict)
                    assert 'total_entries' in stats
                    assert 'total_articles' in stats
                    print("✓ Statistics method works")
                    
                    return True
                    
                finally:
                    shutil.rmtree(temp_dir)
                    
    except Exception as e:
        print(f"❌ Knowledge base structure test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_content_classification():
    """Test content classification methods."""
    print("\nTesting content classification...")
    
    try:
        import numpy as np
        with patch('compliance_checker.knowledge.gdpr_knowledge_base.SENTENCE_TRANSFORMERS_AVAILABLE', True):
            with patch('compliance_checker.knowledge.gdpr_knowledge_base.SentenceTransformer') as mock_st:
                mock_model = Mock()
                mock_model.encode.return_value = np.array([[0.1, 0.2, 0.3]])
                mock_st.return_value = mock_model
                
                from compliance_checker.knowledge.gdpr_knowledge_base import GDPRKnowledgeBase
                
                temp_dir = tempfile.mkdtemp()
                try:
                    kb = GDPRKnowledgeBase(
                        gdpr_docs_path=str(Path(temp_dir) / "gdpr_docs"),
                        index_path=str(Path(temp_dir) / "index")
                    )
                    
                    # Test content classification
                    assert kb._classify_content_type("Article 6 Lawfulness") == "article"
                    assert kb._classify_content_type("Recital (32) Consent") == "recital"
                    assert kb._classify_content_type("Personal data means") == "definition"
                    assert kb._classify_content_type("General text") == "general"
                    
                    print("✓ Content classification works correctly")
                    
                    # Test keyword extraction
                    keywords = kb._extract_keywords("The data subject has given consent for processing personal data")
                    assert "consent" in keywords
                    assert "personal data" in keywords
                    assert "processing" in keywords
                    
                    print("✓ Keyword extraction works correctly")
                    
                    return True
                    
                finally:
                    shutil.rmtree(temp_dir)
                    
    except Exception as e:
        print(f"❌ Content classification test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all basic tests."""
    print("🚀 GDPR Knowledge Base Basic Tests")
    print("=" * 50)
    
    tests = [
        test_basic_imports,
        test_knowledge_base_structure,
        test_content_classification
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        print()
    
    print("=" * 50)
    print(f"Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All basic tests passed!")
        return True
    else:
        print("❌ Some tests failed")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)