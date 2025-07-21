"""
Report data model for the HITL Report Editor system.
"""

from datetime import datetime
from typing import Dict, Any, List, Optional
from .base import BaseModel


class ReportMetadata(BaseModel):
    """Metadata for a report."""
    
    def __init__(self, created_at: datetime, modified_at: datetime, 
                 file_size: int, line_count: int, **kwargs):
        super().__init__(
            created_at=created_at,
            modified_at=modified_at,
            file_size=file_size,
            line_count=line_count,
            **kwargs
        )
    
    def _get_required_fields(self) -> list:
        return ['created_at', 'modified_at', 'file_size', 'line_count']
    
    def _get_field_types(self) -> Dict[str, type]:
        return {
            'created_at': datetime,
            'modified_at': datetime,
            'file_size': int,
            'line_count': int
        }


class ReportSection(BaseModel):
    """A section within a report."""
    
    def __init__(self, id: str, title: str, start_line: int, 
                 end_line: int, content: str, **kwargs):
        super().__init__(
            id=id,
            title=title,
            start_line=start_line,
            end_line=end_line,
            content=content,
            **kwargs
        )
    
    def _get_required_fields(self) -> list:
        return ['id', 'title', 'start_line', 'end_line', 'content']
    
    def _get_field_types(self) -> Dict[str, type]:
        return {
            'id': str,
            'title': str,
            'start_line': int,
            'end_line': int,
            'content': str
        }
    
    def validate(self) -> bool:
        """Validate section with additional business rules."""
        if not super().validate():
            return False
        
        # Validate line numbers
        if self.start_line < 0 or self.end_line < 0:
            return False
        
        if self.start_line > self.end_line:
            return False
        
        # Validate content is not empty
        if not self.content.strip():
            return False
        
        return True


class Report(BaseModel):
    """Main report data model."""
    
    def __init__(self, id: str, filename: str, content: str, 
                 sections: List[Dict[str, Any]], metadata: Dict[str, Any], **kwargs):
        # Convert sections and metadata to proper objects
        section_objects = [
            ReportSection.from_dict(section) if isinstance(section, dict) else section
            for section in sections
        ]
        
        metadata_object = (
            ReportMetadata.from_dict(metadata) if isinstance(metadata, dict) else metadata
        )
        
        super().__init__(
            id=id,
            filename=filename,
            content=content,
            sections=section_objects,
            metadata=metadata_object,
            **kwargs
        )
    
    def _get_required_fields(self) -> list:
        return ['id', 'filename', 'content', 'sections', 'metadata']
    
    def _get_field_types(self) -> Dict[str, type]:
        return {
            'id': str,
            'filename': str,
            'content': str,
            'sections': list,
            'metadata': ReportMetadata
        }
    
    def validate(self) -> bool:
        """Validate report with additional business rules."""
        if not super().validate():
            return False
        
        # Validate filename is not empty
        if not self.filename.strip():
            return False
        
        # Validate content is not empty
        if not self.content.strip():
            return False
        
        # Validate all sections
        for section in self.sections:
            if not isinstance(section, ReportSection) or not section.validate():
                return False
        
        # Validate metadata
        if not isinstance(self.metadata, ReportMetadata) or not self.metadata.validate():
            return False
        
        return True
    
    def get_section_by_id(self, section_id: str) -> Optional[ReportSection]:
        """Get a section by its ID."""
        for section in self.sections:
            if section.id == section_id:
                return section
        return None
    
    def get_sections_by_line_range(self, start_line: int, end_line: int) -> List[ReportSection]:
        """Get sections that overlap with the given line range."""
        overlapping_sections = []
        
        for section in self.sections:
            # Check if section overlaps with the given range
            if (section.start_line <= end_line and section.end_line >= start_line):
                overlapping_sections.append(section)
        
        return overlapping_sections
    
    def add_section(self, section: ReportSection) -> bool:
        """Add a new section to the report."""
        if not isinstance(section, ReportSection) or not section.validate():
            return False
        
        # Check for duplicate IDs
        if self.get_section_by_id(section.id):
            return False
        
        self.sections.append(section)
        return True
    
    def remove_section(self, section_id: str) -> bool:
        """Remove a section by its ID."""
        for i, section in enumerate(self.sections):
            if section.id == section_id:
                del self.sections[i]
                return True
        return False
    
    def get_total_lines(self) -> int:
        """Get the total number of lines in the report."""
        return len(self.content.split('\n'))
    
    def get_content_excerpt(self, start_pos: int, end_pos: int) -> str:
        """Get a content excerpt by character position."""
        if start_pos < 0 or end_pos > len(self.content) or start_pos > end_pos:
            return ""
        
        return self.content[start_pos:end_pos]