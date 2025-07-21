"""
Comment data model for the HITL Report Editor system.
"""

from datetime import datetime
from typing import Dict, Any, Optional
from .base import BaseModel


class TextSelection(BaseModel):
    """Text selection information for a comment."""
    
    def __init__(self, start_position: int, end_position: int, 
                 selected_text: str, **kwargs):
        super().__init__(
            start_position=start_position,
            end_position=end_position,
            selected_text=selected_text,
            **kwargs
        )
    
    def _get_required_fields(self) -> list:
        return ['start_position', 'end_position', 'selected_text']
    
    def _get_field_types(self) -> Dict[str, type]:
        return {
            'start_position': int,
            'end_position': int,
            'selected_text': str
        }
    
    def validate(self) -> bool:
        """Validate text selection with additional business rules."""
        if not super().validate():
            return False
        
        # Validate position values
        if self.start_position < 0 or self.end_position < 0:
            return False
        
        if self.start_position > self.end_position:
            return False
        
        # Validate selected text is not empty
        if not self.selected_text.strip():
            return False
        
        return True
    
    def get_selection_length(self) -> int:
        """Get the length of the text selection."""
        return self.end_position - self.start_position
    
    def contains_position(self, position: int) -> bool:
        """Check if a position is within this text selection."""
        return self.start_position <= position <= self.end_position


class Comment(BaseModel):
    """Comment data model."""
    
    def __init__(self, id: str, report_id: str, text_selection: Dict[str, Any], 
                 comment_text: str, author: str, timestamp: datetime, 
                 section_context: str, **kwargs):
        # Convert text_selection to proper object
        text_selection_object = (
            TextSelection.from_dict(text_selection) if isinstance(text_selection, dict) 
            else text_selection
        )
        
        super().__init__(
            id=id,
            report_id=report_id,
            text_selection=text_selection_object,
            comment_text=comment_text,
            author=author,
            timestamp=timestamp,
            section_context=section_context,
            **kwargs
        )
    
    def _get_required_fields(self) -> list:
        return ['id', 'report_id', 'text_selection', 'comment_text', 'author', 'timestamp', 'section_context']
    
    def _get_field_types(self) -> Dict[str, type]:
        return {
            'id': str,
            'report_id': str,
            'text_selection': TextSelection,
            'comment_text': str,
            'author': str,
            'timestamp': datetime,
            'section_context': str
        }
    
    def validate(self) -> bool:
        """Validate comment with additional business rules."""
        if not super().validate():
            return False
        
        # Validate comment text is not empty
        if not self.comment_text.strip():
            return False
        
        # Validate author is not empty
        if not self.author.strip():
            return False
        
        # Validate text selection
        if not isinstance(self.text_selection, TextSelection) or not self.text_selection.validate():
            return False
        
        return True
    
    def get_comment_length(self) -> int:
        """Get the length of the comment text."""
        return len(self.comment_text)
    
    def get_selected_text_length(self) -> int:
        """Get the length of the selected text."""
        return self.text_selection.get_selection_length()
    
    def is_recent(self, hours: int = 24) -> bool:
        """Check if the comment was created within the specified hours."""
        from datetime import timedelta
        time_threshold = datetime.now() - timedelta(hours=hours)
        return self.timestamp > time_threshold
    
    def update_comment_text(self, new_text: str) -> bool:
        """Update the comment text with validation."""
        if not new_text.strip():
            return False
        
        self.comment_text = new_text
        self.timestamp = datetime.now()  # Update timestamp on edit
        return True
    
    def matches_text_position(self, start_pos: int, end_pos: int) -> bool:
        """Check if this comment matches the given text position range."""
        return (self.text_selection.start_position == start_pos and 
                self.text_selection.end_position == end_pos)
    
    def overlaps_with_position(self, start_pos: int, end_pos: int) -> bool:
        """Check if this comment overlaps with the given position range."""
        return not (self.text_selection.end_position < start_pos or 
                   self.text_selection.start_position > end_pos)
    
    def get_context_preview(self, max_length: int = 100) -> str:
        """Get a preview of the section context."""
        if len(self.section_context) <= max_length:
            return self.section_context
        
        return self.section_context[:max_length - 3] + "..."
    
    def to_summary_format(self) -> Dict[str, Any]:
        """Convert comment to format suitable for summary generation."""
        return {
            'selected_text': self.text_selection.selected_text,
            'comment': self.comment_text,
            'author': self.author,
            'timestamp': self.timestamp.isoformat()
        }