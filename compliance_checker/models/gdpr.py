"""
Data models for GDPR articles and knowledge base.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional


@dataclass
class GDPRArticle:
    """Represents a GDPR article with its content and metadata."""
    article_number: str
    title: str
    content: str
    recitals: List[str] = field(default_factory=list)
    keywords: List[str] = field(default_factory=list)
    
    # Additional metadata
    chapter: Optional[str] = None
    section: Optional[str] = None
    relevance_score: Optional[float] = None
    embedding: Optional[List[float]] = None
    
    def get_full_reference(self) -> str:
        """Get the full GDPR article reference."""
        return f"GDPR Article {self.article_number}: {self.title}"
    
    def matches_keywords(self, keywords: List[str]) -> bool:
        """Check if the article matches any of the provided keywords."""
        article_keywords = [kw.lower() for kw in self.keywords]
        search_keywords = [kw.lower() for kw in keywords]
        return any(kw in article_keywords for kw in search_keywords)


@dataclass
class GDPRRecital:
    """Represents a GDPR recital."""
    recital_number: str
    content: str
    related_articles: List[str] = field(default_factory=list)
    keywords: List[str] = field(default_factory=list)


@dataclass
class GDPRKnowledgeEntry:
    """Represents an entry in the GDPR knowledge base."""
    entry_id: str
    entry_type: str  # "article", "recital", "definition"
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    embedding: Optional[List[float]] = None
    
    # Relationships
    related_entries: List[str] = field(default_factory=list)
    parent_entry: Optional[str] = None