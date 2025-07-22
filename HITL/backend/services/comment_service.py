"""
Comment service for managing comment operations in the HITL Report Editor.
"""

import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any
from flask import current_app

from ..models.comment import Comment, TextSelection
from ..utils.file_operations import FileOperations
from ..utils.security import SecurityValidator


class CommentService:
    """Service class for comment management operations."""
    
    def __init__(self):
        """Initialize the comment service."""
        self.file_ops = FileOperations()
        self.security = SecurityValidator()
    
    def create_comment(self, report_id: str, start_position: int, end_position: int, 
                      selected_text: str, comment_text: str, author: str, 
                      section_context: str = "") -> Optional[Comment]:
        """
        Create a new comment on a report.
        
        Args:
            report_id: ID of the report being commented on
            start_position: Start character position of selection
            end_position: End character position of selection
            selected_text: The selected text being commented on
            comment_text: The comment content
            author: Author of the comment
            section_context: Context about the section being commented on
            
        Returns:
            Comment object if successful, None otherwise
        """
        try:
            # Validate inputs
            if not self.security.validate_id(report_id):
                raise ValueError(f"Invalid report ID: {report_id}")
            
            if not comment_text.strip():
                raise ValueError("Comment text cannot be empty")
            
            if not author.strip():
                raise ValueError("Author cannot be empty")
            
            if start_position < 0 or end_position < 0 or start_position > end_position:
                raise ValueError("Invalid text selection positions")
            
            if not selected_text.strip():
                raise ValueError("Selected text cannot be empty")
            
            # Create text selection
            text_selection = TextSelection(
                start_position=start_position,
                end_position=end_position,
                selected_text=selected_text
            )
            
            # Generate unique comment ID
            comment_id = str(uuid.uuid4())
            
            # Create comment object
            comment = Comment(
                id=comment_id,
                report_id=report_id,
                text_selection=text_selection,
                comment_text=comment_text,
                author=author,
                timestamp=datetime.now(),
                section_context=section_context
            )
            
            # Validate comment
            if not comment.validate():
                raise ValueError("Comment validation failed")
            
            # Save comment to file system
            if not self._save_comment_to_file(comment):
                raise RuntimeError("Failed to save comment to file system")
            
            return comment
            
        except Exception as e:
            current_app.logger.error(f"Error creating comment: {str(e)}")
            return None
    
    def get_comment(self, comment_id: str) -> Optional[Comment]:
        """
        Retrieve a comment by its ID.
        
        Args:
            comment_id: Unique identifier of the comment
            
        Returns:
            Comment object if found, None otherwise
        """
        try:
            if not self.security.validate_id(comment_id):
                raise ValueError(f"Invalid comment ID: {comment_id}")
            
            # Load comment from file system
            comment_data = self._load_comment_from_file(comment_id)
            if not comment_data:
                return None
            
            # Create comment object from data
            comment = Comment.from_dict(comment_data)
            
            # Validate loaded comment
            if not comment.validate():
                current_app.logger.warning(f"Loaded comment {comment_id} failed validation")
                return None
            
            return comment
            
        except Exception as e:
            current_app.logger.error(f"Error retrieving comment {comment_id}: {str(e)}")
            return None
    
    def update_comment(self, comment_id: str, comment_text: str) -> Optional[Comment]:
        """
        Update an existing comment's text.
        
        Args:
            comment_id: Unique identifier of the comment
            comment_text: New comment text
            
        Returns:
            Updated Comment object if successful, None otherwise
        """
        try:
            # Validate inputs
            if not self.security.validate_id(comment_id):
                raise ValueError(f"Invalid comment ID: {comment_id}")
            
            if not comment_text.strip():
                raise ValueError("Comment text cannot be empty")
            
            # Get existing comment
            existing_comment = self.get_comment(comment_id)
            if not existing_comment:
                raise ValueError(f"Comment {comment_id} not found")
            
            # Update comment text and timestamp
            if not existing_comment.update_comment_text(comment_text):
                raise ValueError("Failed to update comment text")
            
            # Validate updated comment
            if not existing_comment.validate():
                raise ValueError("Updated comment validation failed")
            
            # Save updated comment
            if not self._save_comment_to_file(existing_comment):
                raise RuntimeError("Failed to save updated comment")
            
            return existing_comment
            
        except Exception as e:
            current_app.logger.error(f"Error updating comment {comment_id}: {str(e)}")
            return None
    
    def delete_comment(self, comment_id: str) -> bool:
        """
        Delete a comment.
        
        Args:
            comment_id: Unique identifier of the comment
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if not self.security.validate_id(comment_id):
                raise ValueError(f"Invalid comment ID: {comment_id}")
            
            # Check if comment exists
            if not self.get_comment(comment_id):
                return False
            
            # Delete comment file
            comment_file = self._get_comment_file_path(comment_id)
            if comment_file.exists():
                comment_file.unlink()
            
            return True
            
        except Exception as e:
            current_app.logger.error(f"Error deleting comment {comment_id}: {str(e)}")
            return False
    
    def get_comments_for_report(self, report_id: str) -> List[Comment]:
        """
        Get all comments for a specific report.
        
        Args:
            report_id: Unique identifier of the report
            
        Returns:
            List of Comment objects
        """
        try:
            if not self.security.validate_id(report_id):
                raise ValueError(f"Invalid report ID: {report_id}")
            
            comments = []
            comments_dir = Path(current_app.config['COMMENTS_DIR'])
            
            # Scan comments directory for files related to this report
            for comment_file in comments_dir.glob('*.json'):
                try:
                    comment_data = self._load_comment_from_file(comment_file.stem)
                    if comment_data and comment_data.get('report_id') == report_id:
                        comment = Comment.from_dict(comment_data)
                        if comment.validate():
                            comments.append(comment)
                        else:
                            current_app.logger.warning(f"Invalid comment data in file {comment_file}")
                            
                except Exception as e:
                    current_app.logger.warning(f"Error processing comment file {comment_file}: {str(e)}")
                    continue
            
            # Sort comments by timestamp (oldest first)
            comments.sort(key=lambda x: x.timestamp)
            
            return comments
            
        except Exception as e:
            current_app.logger.error(f"Error getting comments for report {report_id}: {str(e)}")
            return []
    
    def get_comments_by_author(self, author: str) -> List[Comment]:
        """
        Get all comments by a specific author.
        
        Args:
            author: Author name to filter by
            
        Returns:
            List of Comment objects
        """
        try:
            if not author.strip():
                raise ValueError("Author cannot be empty")
            
            comments = []
            comments_dir = Path(current_app.config['COMMENTS_DIR'])
            
            # Scan all comment files
            for comment_file in comments_dir.glob('*.json'):
                try:
                    comment_data = self._load_comment_from_file(comment_file.stem)
                    if comment_data and comment_data.get('author') == author:
                        comment = Comment.from_dict(comment_data)
                        if comment.validate():
                            comments.append(comment)
                            
                except Exception as e:
                    current_app.logger.warning(f"Error processing comment file {comment_file}: {str(e)}")
                    continue
            
            # Sort comments by timestamp (newest first)
            comments.sort(key=lambda x: x.timestamp, reverse=True)
            
            return comments
            
        except Exception as e:
            current_app.logger.error(f"Error getting comments by author {author}: {str(e)}")
            return []
    
    def get_comments_in_range(self, report_id: str, start_position: int, 
                             end_position: int) -> List[Comment]:
        """
        Get comments that overlap with a specific text range.
        
        Args:
            report_id: Unique identifier of the report
            start_position: Start character position
            end_position: End character position
            
        Returns:
            List of Comment objects that overlap with the range
        """
        try:
            if not self.security.validate_id(report_id):
                raise ValueError(f"Invalid report ID: {report_id}")
            
            if start_position < 0 or end_position < 0 or start_position > end_position:
                raise ValueError("Invalid position range")
            
            # Get all comments for the report
            all_comments = self.get_comments_for_report(report_id)
            
            # Filter comments that overlap with the specified range
            overlapping_comments = [
                comment for comment in all_comments
                if comment.overlaps_with_position(start_position, end_position)
            ]
            
            return overlapping_comments
            
        except Exception as e:
            current_app.logger.error(f"Error getting comments in range for report {report_id}: {str(e)}")
            return []
    
    def get_recent_comments(self, hours: int = 24) -> List[Comment]:
        """
        Get comments created within the specified time period.
        
        Args:
            hours: Number of hours to look back
            
        Returns:
            List of recent Comment objects
        """
        try:
            if hours <= 0:
                raise ValueError("Hours must be positive")
            
            comments = []
            comments_dir = Path(current_app.config['COMMENTS_DIR'])
            
            # Scan all comment files
            for comment_file in comments_dir.glob('*.json'):
                try:
                    comment_data = self._load_comment_from_file(comment_file.stem)
                    if comment_data:
                        comment = Comment.from_dict(comment_data)
                        if comment.validate() and comment.is_recent(hours):
                            comments.append(comment)
                            
                except Exception as e:
                    current_app.logger.warning(f"Error processing comment file {comment_file}: {str(e)}")
                    continue
            
            # Sort comments by timestamp (newest first)
            comments.sort(key=lambda x: x.timestamp, reverse=True)
            
            return comments
            
        except Exception as e:
            current_app.logger.error(f"Error getting recent comments: {str(e)}")
            return []
    
    def get_comment_statistics(self, report_id: str) -> Dict[str, Any]:
        """
        Get statistics about comments for a report.
        
        Args:
            report_id: Unique identifier of the report
            
        Returns:
            Dictionary containing comment statistics
        """
        try:
            comments = self.get_comments_for_report(report_id)
            
            if not comments:
                return {
                    'total_comments': 0,
                    'unique_authors': 0,
                    'average_comment_length': 0.0,
                    'most_active_author': None,
                    'latest_comment_time': None
                }
            
            # Calculate statistics
            total_comments = len(comments)
            authors = set(comment.author for comment in comments)
            unique_authors = len(authors)
            
            # Average comment length
            total_length = sum(comment.get_comment_length() for comment in comments)
            average_length = total_length / total_comments if total_comments > 0 else 0.0
            
            # Most active author
            author_counts = {}
            for comment in comments:
                author_counts[comment.author] = author_counts.get(comment.author, 0) + 1
            
            most_active_author = max(author_counts.items(), key=lambda x: x[1])[0] if author_counts else None
            
            # Latest comment time
            latest_comment = max(comments, key=lambda x: x.timestamp)
            latest_comment_time = latest_comment.timestamp.isoformat()
            
            return {
                'total_comments': total_comments,
                'unique_authors': unique_authors,
                'average_comment_length': round(average_length, 2),
                'most_active_author': most_active_author,
                'latest_comment_time': latest_comment_time
            }
            
        except Exception as e:
            current_app.logger.error(f"Error getting comment statistics for report {report_id}: {str(e)}")
            return {}
    
    def _save_comment_to_file(self, comment: Comment) -> bool:
        """
        Save comment to file system.
        
        Args:
            comment: Comment object to save
            
        Returns:
            True if successful, False otherwise
        """
        try:
            comment_file = self._get_comment_file_path(comment.id)
            comment_data = comment.to_dict()
            
            return self.file_ops.write_json_file(str(comment_file), comment_data)
            
        except Exception as e:
            current_app.logger.error(f"Error saving comment {comment.id}: {str(e)}")
            return False
    
    def _load_comment_from_file(self, comment_id: str) -> Optional[Dict[str, Any]]:
        """
        Load comment data from file system.
        
        Args:
            comment_id: Unique identifier of the comment
            
        Returns:
            Comment data dictionary if successful, None otherwise
        """
        try:
            comment_file = self._get_comment_file_path(comment_id)
            
            if not comment_file.exists():
                return None
            
            return self.file_ops.read_json_file(str(comment_file))
            
        except Exception as e:
            current_app.logger.error(f"Error loading comment {comment_id}: {str(e)}")
            return None
    
    def _get_comment_file_path(self, comment_id: str) -> Path:
        """
        Get the file path for a comment.
        
        Args:
            comment_id: Unique identifier of the comment
            
        Returns:
            Path object for the comment file
        """
        comments_dir = Path(current_app.config['COMMENTS_DIR'])
        return comments_dir / f"{comment_id}.json"