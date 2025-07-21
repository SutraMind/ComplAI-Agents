"""
Summary data model for the HITL Report Editor system.
"""

from datetime import datetime
from typing import Dict, Any, List, Optional
from .base import BaseModel


class SummaryStatistics(BaseModel):
    """Statistics for a summary."""
    
    def __init__(self, most_commented_section: str, average_comment_length: float, 
                 total_review_time: str, **kwargs):
        super().__init__(
            most_commented_section=most_commented_section,
            average_comment_length=average_comment_length,
            total_review_time=total_review_time,
            **kwargs
        )
    
    def _get_required_fields(self) -> list:
        return ['most_commented_section', 'average_comment_length', 'total_review_time']
    
    def _get_field_types(self) -> Dict[str, type]:
        return {
            'most_commented_section': str,
            'average_comment_length': (int, float),  # Allow both int and float
            'total_review_time': str
        }
    
    def _validate_field_types(self, data: Dict[str, Any]) -> None:
        """Override to handle numeric types properly."""
        field_types = self._get_field_types()
        
        for field_name, expected_type in field_types.items():
            if field_name in data and data[field_name] is not None:
                value = data[field_name]
                
                # Special handling for numeric types
                if field_name == 'average_comment_length':
                    if not isinstance(value, (int, float)):
                        raise TypeError(f"Field '{field_name}' must be numeric, got {type(value).__name__}")
                elif not isinstance(value, expected_type):
                    raise TypeError(f"Field '{field_name}' must be of type {expected_type.__name__}, got {type(value).__name__}")


class CommentsBySection(BaseModel):
    """Comments organized by section."""
    
    def __init__(self, section_title: str, section_content: str, 
                 comments: List[Dict[str, Any]], **kwargs):
        super().__init__(
            section_title=section_title,
            section_content=section_content,
            comments=comments,
            **kwargs
        )
    
    def _get_required_fields(self) -> list:
        return ['section_title', 'section_content', 'comments']
    
    def _get_field_types(self) -> Dict[str, type]:
        return {
            'section_title': str,
            'section_content': str,
            'comments': list
        }
    
    def validate(self) -> bool:
        """Validate comments by section with additional business rules."""
        if not super().validate():
            return False
        
        # Validate each comment has required fields
        required_comment_fields = ['selected_text', 'comment', 'author', 'timestamp']
        
        for comment in self.comments:
            if not isinstance(comment, dict):
                return False
            
            for field in required_comment_fields:
                if field not in comment:
                    return False
                
                # Validate non-empty strings
                if field in ['selected_text', 'comment', 'author'] and not comment[field].strip():
                    return False
        
        return True
    
    def get_comment_count(self) -> int:
        """Get the number of comments in this section."""
        return len(self.comments)
    
    def get_total_comment_length(self) -> int:
        """Get the total length of all comments in this section."""
        return sum(len(comment.get('comment', '')) for comment in self.comments)
    
    def get_authors(self) -> List[str]:
        """Get unique list of authors who commented on this section."""
        authors = set()
        for comment in self.comments:
            if 'author' in comment:
                authors.add(comment['author'])
        return list(authors)
    
    def add_comment(self, comment_data: Dict[str, Any]) -> bool:
        """Add a comment to this section."""
        required_fields = ['selected_text', 'comment', 'author', 'timestamp']
        
        # Validate comment data
        for field in required_fields:
            if field not in comment_data:
                return False
            if field in ['selected_text', 'comment', 'author'] and not comment_data[field].strip():
                return False
        
        self.comments.append(comment_data)
        return True


class Summary(BaseModel):
    """Summary data model."""
    
    def __init__(self, report_id: str, generated_at: datetime, total_comments: int,
                 comments_by_section: List[Dict[str, Any]], 
                 summary_statistics: Dict[str, Any], **kwargs):
        # Convert comments_by_section to proper objects
        section_objects = [
            CommentsBySection.from_dict(section) if isinstance(section, dict) else section
            for section in comments_by_section
        ]
        
        # Convert summary_statistics to proper object
        statistics_object = (
            SummaryStatistics.from_dict(summary_statistics) if isinstance(summary_statistics, dict) 
            else summary_statistics
        )
        
        super().__init__(
            report_id=report_id,
            generated_at=generated_at,
            total_comments=total_comments,
            comments_by_section=section_objects,
            summary_statistics=statistics_object,
            **kwargs
        )
    
    def _get_required_fields(self) -> list:
        return ['report_id', 'generated_at', 'total_comments', 'comments_by_section', 'summary_statistics']
    
    def _get_field_types(self) -> Dict[str, type]:
        return {
            'report_id': str,
            'generated_at': datetime,
            'total_comments': int,
            'comments_by_section': list,
            'summary_statistics': SummaryStatistics
        }
    
    def validate(self) -> bool:
        """Validate summary with additional business rules."""
        if not super().validate():
            return False
        
        # Validate total_comments is non-negative
        if self.total_comments < 0:
            return False
        
        # Validate all sections
        for section in self.comments_by_section:
            if not isinstance(section, CommentsBySection) or not section.validate():
                return False
        
        # Validate statistics
        if not isinstance(self.summary_statistics, SummaryStatistics) or not self.summary_statistics.validate():
            return False
        
        # Validate total_comments matches actual comment count
        actual_total = sum(section.get_comment_count() for section in self.comments_by_section)
        if self.total_comments != actual_total:
            return False
        
        return True
    
    def get_section_by_title(self, title: str) -> Optional[CommentsBySection]:
        """Get a section by its title."""
        for section in self.comments_by_section:
            if section.section_title == title:
                return section
        return None
    
    def get_all_authors(self) -> List[str]:
        """Get unique list of all authors across all sections."""
        authors = set()
        for section in self.comments_by_section:
            authors.update(section.get_authors())
        return list(authors)
    
    def get_sections_with_comments(self) -> List[CommentsBySection]:
        """Get only sections that have comments."""
        return [section for section in self.comments_by_section if section.get_comment_count() > 0]
    
    def get_most_active_section(self) -> Optional[CommentsBySection]:
        """Get the section with the most comments."""
        if not self.comments_by_section:
            return None
        
        return max(self.comments_by_section, key=lambda section: section.get_comment_count())
    
    def calculate_average_comment_length(self) -> float:
        """Calculate the average length of all comments."""
        if self.total_comments == 0:
            return 0.0
        
        total_length = sum(
            section.get_total_comment_length() 
            for section in self.comments_by_section
        )
        
        return total_length / self.total_comments
    
    def add_section(self, section: CommentsBySection) -> bool:
        """Add a new section to the summary."""
        if not isinstance(section, CommentsBySection) or not section.validate():
            return False
        
        # Check for duplicate section titles
        if self.get_section_by_title(section.section_title):
            return False
        
        self.comments_by_section.append(section)
        self.total_comments += section.get_comment_count()
        return True
    
    def update_statistics(self) -> None:
        """Update summary statistics based on current data."""
        if not self.comments_by_section:
            return
        
        # Find most commented section
        most_active = self.get_most_active_section()
        most_commented_section = most_active.section_title if most_active else ""
        
        # Calculate average comment length
        average_length = self.calculate_average_comment_length()
        
        # Update statistics object
        self.summary_statistics.most_commented_section = most_commented_section
        self.summary_statistics.average_comment_length = average_length
    
    def export_to_text(self) -> str:
        """Export summary to a formatted text representation."""
        lines = []
        lines.append(f"Summary Report for: {self.report_id}")
        lines.append(f"Generated at: {self.generated_at.isoformat()}")
        lines.append(f"Total Comments: {self.total_comments}")
        lines.append("=" * 50)
        lines.append("")
        
        for section in self.comments_by_section:
            if section.get_comment_count() > 0:
                lines.append(f"Section: {section.section_title}")
                lines.append(f"Comments: {section.get_comment_count()}")
                lines.append("-" * 30)
                
                for i, comment in enumerate(section.comments, 1):
                    lines.append(f"{i}. Selected Text: \"{comment['selected_text']}\"")
                    lines.append(f"   Comment: {comment['comment']}")
                    lines.append(f"   Author: {comment['author']}")
                    lines.append(f"   Timestamp: {comment['timestamp']}")
                    lines.append("")
                
                lines.append("")
        
        lines.append("Statistics:")
        lines.append(f"Most Commented Section: {self.summary_statistics.most_commented_section}")
        lines.append(f"Average Comment Length: {self.summary_statistics.average_comment_length:.2f}")
        lines.append(f"Total Review Time: {self.summary_statistics.total_review_time}")
        
        return "\n".join(lines)