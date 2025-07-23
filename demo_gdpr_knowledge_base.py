#!/usr/bin/env python3
"""
Demo script for GDPR Knowledge Base functionality.
"""

import logging
import sys
from pathlib import Path

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent))

from compliance_checker.knowledge.gdpr_knowledge_base import GDPRKnowledgeBase
from compliance_checker.exceptions import DocumentProcessingError, VectorStoreError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def main():
    """Main demo function."""
    print("🚀 GDPR Knowledge Base Demo")
    print("=" * 50)
    
    try:
        # Initialize knowledge base
        print("\n1. Initializing GDPR Knowledge Base...")
        kb = GDPRKnowledgeBase(
            gdpr_docs_path="policies",  # Using existing policies folder
            index_path="gdpr_index",
            embedding_model="all-MiniLM-L6-v2"
        )
        print("✓ Knowledge base initialized successfully")
        
        # Build vector store
        print("\n2. Building vector store from GDPR documents...")
        kb.build_vector_store()
        print("✓ Vector store built successfully")
        
        # Display statistics
        print("\n3. Knowledge Base Statistics:")
        stats = kb.get_statistics()
        for key, value in stats.items():
            print(f"   {key}: {value}")
        
        # Display articles found
        print("\n4. GDPR Articles Found:")
        articles = kb.get_all_articles()
        for article in articles[:5]:  # Show first 5 articles
            print(f"   - Article {article.article_number}: {article.title}")
            print(f"     Keywords: {', '.join(article.keywords[:5])}")  # Show first 5 keywords
        
        if len(articles) > 5:
            print(f"   ... and {len(articles) - 5} more articles")
        
        # Test similarity search
        print("\n5. Testing Similarity Search:")
        test_queries = [
            "data subject consent",
            "personal data processing",
            "lawful basis",
            "data protection rights"
        ]
        
        for query in test_queries:
            print(f"\n   Query: '{query}'")
            try:
                results = kb.similarity_search(query, top_k=3)
                for i, (entry, score) in enumerate(results, 1):
                    content_preview = entry.content[:100].replace('\n', ' ')
                    print(f"     {i}. Score: {score:.3f} - {content_preview}...")
            except Exception as e:
                print(f"     Error: {e}")
        
        # Test article querying
        print("\n6. Testing Article Querying:")
        for query in test_queries[:2]:  # Test first 2 queries
            print(f"\n   Query: '{query}'")
            try:
                articles = kb.query_relevant_articles(query, top_k=3)
                for i, article in enumerate(articles, 1):
                    score_text = f" (Score: {article.relevance_score:.3f})" if hasattr(article, 'relevance_score') else ""
                    print(f"     {i}. Article {article.article_number}: {article.title}{score_text}")
            except Exception as e:
                print(f"     Error: {e}")
        
        # Test specific article retrieval
        print("\n7. Testing Specific Article Retrieval:")
        test_article_numbers = ["6", "7", "25", "32"]
        for article_num in test_article_numbers:
            article = kb.get_article_by_number(article_num)
            if article:
                print(f"   ✓ Article {article_num}: {article.title}")
            else:
                print(f"   ✗ Article {article_num}: Not found")
        
        print("\n🎉 Demo completed successfully!")
        
    except DocumentProcessingError as e:
        print(f"\n❌ Document processing error: {e}")
        print("Make sure the 'policies' folder contains GDPR documents (PDF or TXT files)")
        
    except VectorStoreError as e:
        print(f"\n❌ Vector store error: {e}")
        print("This might be due to missing dependencies or insufficient resources")
        
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        logger.exception("Unexpected error occurred")
    
    print("\n" + "=" * 50)


if __name__ == "__main__":
    main()