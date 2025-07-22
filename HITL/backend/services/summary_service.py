"""
Summary service for generating intelligent summaries with LLM enhancement.
"""

import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any
from flask import current_app

from ..models.summary import Summary, CommentsBySection, SummaryStatistics
from ..models.report import Report
from ..models.comment import Comment
from ..services.llm_service import LLMService
from ..utils.file_operations import FileOperations
from ..utils.security import SecurityValidator


class SummaryService:
    """Service class for summary generation with LLM enhancement."""
    
    def __init__(self):
        """Initialize the summary service."""
        self.file_ops = FileOperations()
        self.security = SecurityValidator()
        self.llm_service = LLMService()
    
    def generate_summary(self, report: Report, comments: List[Comment]) -> Optional[Summary]:
        """
        Generate a comprehensive summary of a report and its comments.
        
        Args:
            report: Report object to summarize
            comments: List of Comment objects associated with the report
            
        Returns:
            Summary object if successful, None otherwise
        """
        try:
            if not report or not report.validate():
                raise ValueError("Invalid report provided")
            
            # Organize comments by sections
            comments_by_section = self._organize_comments_by_section(report, comments)
            
            # Enhance with LLM analysis
            enhanced_sections = self._enhance_sections_with_llm(comments_by_section, report.content)
            
            # Generate summary statistics
            statistics = self._generate_summary_statistics(comments, enhanced_sections)
            
            # Create summary object
            summary = Summary(
                report_id=report.id,
                generated_at=datetime.now(),
                total_comments=len(comments),
                comments_by_section=enhanced_sections,
                summary_statistics=statistics
            )
            
            # Validate summary
            if not summary.validate():
                raise ValueError("Generated summary failed validation")
            
            # Save summary to file system
            if not self._save_summary_to_file(summary):
                raise RuntimeError("Failed to save summary to file system")
            
            return summary
            
        except Exception as e:
            current_app.logger.error(f"Error generating summary for report {report.id if report else 'unknown'}: {str(e)}")
            return None
    
    def get_summary(self, report_id: str) -> Optional[Summary]:
        """
        Retrieve a summary by report ID.
        
        Args:
            report_id: Unique identifier of the report
            
        Returns:
            Summary object if found, None otherwise
        """
        try:
            if not self.security.validate_id(report_id):
                raise ValueError(f"Invalid report ID: {report_id}")
            
            # Load summary from file system
            summary_data = self._load_summary_from_file(report_id)
            if not summary_data:
                return None
            
            # Create summary object from data
            summary = Summary.from_dict(summary_data)
            
            # Validate loaded summary
            if not summary.validate():
                current_app.logger.warning(f"Loaded summary for report {report_id} failed validation")
                return None
            
            return summary
            
        except Exception as e:
            current_app.logger.error(f"Error retrieving summary for report {report_id}: {str(e)}")
            return None
    
    def update_summary(self, report: Report, comments: List[Comment]) -> Optional[Summary]:
        """
        Update an existing summary or create a new one.
        
        Args:
            report: Report object
            comments: Updated list of Comment objects
            
        Returns:
            Updated Summary object if successful, None otherwise
        """
        try:
            # Delete existing summary if it exists
            existing_summary = self.get_summary(report.id)
            if existing_summary:
                self.delete_summary(report.id)
            
            # Generate new summary
            return self.generate_summary(report, comments)
            
        except Exception as e:
            current_app.logger.error(f"Error updating summary for report {report.id}: {str(e)}")
            return None
    
    def delete_summary(self, report_id: str) -> bool:
        """
        Delete a summary.
        
        Args:
            report_id: Unique identifier of the report
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if not self.security.validate_id(report_id):
                raise ValueError(f"Invalid report ID: {report_id}")
            
            # Delete summary file
            summary_file = self._get_summary_file_path(report_id)
            if summary_file.exists():
                summary_file.unlink()
                return True
            
            return False
            
        except Exception as e:
            current_app.logger.error(f"Error deleting summary for report {report_id}: {str(e)}")
            return False
    
    def export_summary_to_text(self, report_id: str) -> Optional[str]:
        """
        Export summary to formatted text.
        
        Args:
            report_id: Unique identifier of the report
            
        Returns:
            Formatted text string if successful, None otherwise
        """
        try:
            summary = self.get_summary(report_id)
            if not summary:
                return None
            
            return summary.export_to_text()
            
        except Exception as e:
            current_app.logger.error(f"Error exporting summary for report {report_id}: {str(e)}")
            return None
    
    def get_summary_insights(self, report_id: str) -> Dict[str, Any]:
        """
        Get LLM-powered insights about the summary.
        
        Args:
            report_id: Unique identifier of the report
            
        Returns:
            Dictionary containing insights and analysis
        """
        try:
            summary = self.get_summary(report_id)
            if not summary:
                return {'status': 'error', 'message': 'Summary not found'}
            
            # Prepare data for LLM analysis
            all_comments = []
            for section in summary.comments_by_section:
                all_comments.extend(section.comments)
            
            # Get LLM insights
            categorization = self.llm_service.categorize_comments(all_comments)
            
            # Extract key themes from summary content
            summary_text = summary.export_to_text()
            themes = self.llm_service.extract_key_themes(summary_text[:2000], all_comments)
            
            return {
                'status': 'success',
                'categorization': categorization,
                'key_themes': themes,
                'total_comments': summary.total_comments,
                'sections_with_comments': len([s for s in summary.comments_by_section if s.get_comment_count() > 0]),
                'most_active_section': summary.summary_statistics.most_commented_section,
                'average_comment_length': summary.summary_statistics.average_comment_length
            }
            
        except Exception as e:
            current_app.logger.error(f"Error getting summary insights for report {report_id}: {str(e)}")
            return {'status': 'error', 'message': str(e)}
    
    def _organize_comments_by_section(self, report: Report, comments: List[Comment]) -> List[CommentsBySection]:
        """
        Organize comments by report sections.
        
        Args:
            report: Report object containing sections
            comments: List of Comment objects
            
        Returns:
            List of CommentsBySection objects
        """
        sections_with_comments = []
        
        # Create a section for each report section
        for section in report.sections:
            section_comments = []
            
            # Find comments that fall within this section's line range
            for comment in comments:
                # Convert character positions to approximate line positions
                content_lines = report.content[:comment.text_selection.start_position].count('\n') + 1
                
                if section.start_line <= content_lines <= section.end_line:
                    section_comments.append(comment.to_summary_format())
            
            # Create CommentsBySection object
            comments_by_section = CommentsBySection(
                section_title=section.title,
                section_content=section.content[:500] + "..." if len(section.content) > 500 else section.content,
                comments=section_comments
            )
            
            sections_with_comments.append(comments_by_section)
        
        # Add any orphaned comments to a general section
        orphaned_comments = []
        for comment in comments:
            content_lines = report.content[:comment.text_selection.start_position].count('\n') + 1
            
            # Check if comment belongs to any existing section
            belongs_to_section = False
            for section in report.sections:
                if section.start_line <= content_lines <= section.end_line:
                    belongs_to_section = True
                    break
            
            if not belongs_to_section:
                orphaned_comments.append(comment.to_summary_format())
        
        if orphaned_comments:
            general_section = CommentsBySection(
                section_title="General Comments",
                section_content="Comments not associated with specific sections",
                comments=orphaned_comments
            )
            sections_with_comments.append(general_section)
        
        return sections_with_comments
    
    def _enhance_sections_with_llm(self, sections: List[CommentsBySection], 
                                  report_content: str) -> List[CommentsBySection]:
        """
        Enhance sections with LLM analysis.
        
        Args:
            sections: List of CommentsBySection objects
            report_content: Full report content for context
            
        Returns:
            Enhanced list of CommentsBySection objects
        """
        enhanced_sections = []
        
        for section in sections:
            if section.get_comment_count() > 0:
                # Analyze comments in this section
                comment_analysis = self.llm_service.categorize_comments(section.comments)
                
                # Add LLM insights to section (store in a way that doesn't break validation)
                enhanced_section = CommentsBySection(
                    section_title=section.section_title,
                    section_content=section.section_content,
                    comments=section.comments
                )
                
                # Store LLM insights as additional attributes (not part of base model)
                enhanced_section._llm_themes = comment_analysis.get('themes', [])
                enhanced_section._llm_categories = comment_analysis.get('categories', {})
                enhanced_section._llm_priority = comment_analysis.get('priority_comments', [])
                
                enhanced_sections.append(enhanced_section)
            else:
                enhanced_sections.append(section)
        
        return enhanced_sections
    
    def _generate_summary_statistics(self, comments: List[Comment], 
                                   sections: List[CommentsBySection]) -> SummaryStatistics:
        """
        Generate summary statistics with LLM enhancement.
        
        Args:
            comments: List of Comment objects
            sections: List of CommentsBySection objects
            
        Returns:
            SummaryStatistics object
        """
        # Find most commented section
        most_commented_section = ""
        max_comments = 0
        
        for section in sections:
            comment_count = section.get_comment_count()
            if comment_count > max_comments:
                max_comments = comment_count
                most_commented_section = section.section_title
        
        # Calculate average comment length
        if comments:
            total_length = sum(comment.get_comment_length() for comment in comments)
            average_length = total_length / len(comments)
        else:
            average_length = 0.0
        
        # Estimate total review time (rough calculation)
        estimated_minutes = len(comments) * 2 + sum(len(comment.comment_text) for comment in comments) // 100
        total_review_time = f"{estimated_minutes} minutes"
        
        return SummaryStatistics(
            most_commented_section=most_commented_section,
            average_comment_length=round(average_length, 2),
            total_review_time=total_review_time
        )
    
    def _save_summary_to_file(self, summary: Summary) -> bool:
        """
        Save summary to file system.
        
        Args:
            summary: Summary object to save
            
        Returns:
            True if successful, False otherwise
        """
        try:
            summary_file = self._get_summary_file_path(summary.report_id)
            summary_data = summary.to_dict()
            
            return self.file_ops.write_json_file(str(summary_file), summary_data)
            
        except Exception as e:
            current_app.logger.error(f"Error saving summary for report {summary.report_id}: {str(e)}")
            return False
    
    def _load_summary_from_file(self, report_id: str) -> Optional[Dict[str, Any]]:
        """
        Load summary data from file system.
        
        Args:
            report_id: Unique identifier of the report
            
        Returns:
            Summary data dictionary if successful, None otherwise
        """
        try:
            summary_file = self._get_summary_file_path(report_id)
            
            if not summary_file.exists():
                return None
            
            return self.file_ops.read_json_file(str(summary_file))
            
        except Exception as e:
            current_app.logger.error(f"Error loading summary for report {report_id}: {str(e)}")
            return None
    
    def _get_summary_file_path(self, report_id: str) -> Path:
        """
        Get the file path for a summary.
        
        Args:
            report_id: Unique identifier of the report
            
        Returns:
            Path object for the summary file
        """
        summaries_dir = Path(current_app.config['SUMMARIES_DIR'])
        return summaries_dir / f"{report_id}_summary.json"
    
    def generate_summary_preview(self, report: Report, comments: List[Comment]) -> Dict[str, Any]:
        """
        Generate a quick preview of what the summary would contain.
        
        Args:
            report: Report object
            comments: List of Comment objects
            
        Returns:
            Dictionary containing preview information
        """
        try:
            if not comments:
                return {
                    'status': 'success',
                    'preview': {
                        'total_comments': 0,
                        'sections_with_comments': 0,
                        'estimated_themes': [],
                        'top_authors': []
                    }
                }
            
            # Basic statistics
            total_comments = len(comments)
            authors = list(set(comment.author for comment in comments))
            
            # Count sections with comments
            sections_with_comments = 0
            for section in report.sections:
                has_comments = False
                for comment in comments:
                    content_lines = report.content[:comment.text_selection.start_position].count('\n') + 1
                    if section.start_line <= content_lines <= section.end_line:
                        has_comments = True
                        break
                if has_comments:
                    sections_with_comments += 1
            
            # Get LLM theme preview (limited analysis)
            comment_texts = [comment.comment_text for comment in comments[:5]]  # Sample first 5
            themes = self.llm_service.extract_key_themes(report.content[:1000], 
                                                        [{'comment': text} for text in comment_texts])
            
            return {
                'status': 'success',
                'preview': {
                    'total_comments': total_comments,
                    'sections_with_comments': sections_with_comments,
                    'estimated_themes': themes[:5],
                    'top_authors': authors[:5],
                    'average_comment_length': sum(len(c.comment_text) for c in comments) / total_comments
                }
            }
            
        except Exception as e:
            current_app.logger.error(f"Error generating summary preview: {str(e)}")
            return {'status': 'error', 'message': str(e)}