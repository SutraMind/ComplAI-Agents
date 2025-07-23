"""
Data models for specification documents and requirements.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime
from pathlib import Path


@dataclass
class DocumentSection:
    """Represents a section within a specification document."""
    id: str
    title: str
    content: str
    level: int
    parent_id: Optional[str] = None
    subsections: List[str] = field(default_factory=list)


@dataclass
class Requirement:
    """Represents a requirement extracted from a specification document."""
    id: str
    text: str
    section: str
    category: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    priority: Optional[str] = None
    source_line: Optional[int] = None


@dataclass
class SpecificationDocument:
    """Represents a parsed specification document."""
    content: str
    metadata: Dict[str, Any]
    requirements: List[Requirement] = field(default_factory=list)
    sections: List[DocumentSection] = field(default_factory=list)
    
    # Document identification
    document_id: Optional[str] = None
    filename: Optional[str] = None
    file_path: Optional[Path] = None
    
    # Processing metadata
    processed_at: datetime = field(default_factory=datetime.now)
    file_size: Optional[int] = None
    document_hash: Optional[str] = None
    
    def get_requirement_by_id(self, requirement_id: str) -> Optional[Requirement]:
        """Get a requirement by its ID."""
        for req in self.requirements:
            if req.id == requirement_id:
                return req
        return None
    
    def get_section_by_id(self, section_id: str) -> Optional[DocumentSection]:
        """Get a section by its ID."""
        for section in self.sections:
            if section.id == section_id:
                return section
        return None
    
    def get_requirements_by_section(self, section_id: str) -> List[Requirement]:
        """Get all requirements from a specific section."""
        return [req for req in self.requirements if req.section == section_id]