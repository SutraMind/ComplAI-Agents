"""
Tests for data models.
"""

import pytest
from datetime import datetime
import sys
import os

# Add the backend directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from models.report import Report, ReportSection, ReportMetadata
from models.comment import Comment, TextSelection
from models.summary import Summary, CommentsBySection, SummaryStatistics


class TestReportModels:
    """Test cases for Report-related models."""
    
    def test_report_metadata_creation(self):
        """Test ReportMetadata creation and validation."""
        now = datetime.now()
        metadata = ReportMetadata(
            created_at=now,
            modified_at=now,
            file_size=1024,
            line_count=50
        )
        
        assert metadata.created_at == now
        assert metadata.modified_at == now
        assert metadata.file_size == 1024
        assert metadata.line_count == 50
        assert metadata.validate()
    
    def test_report_section_creation(self):
        """Test ReportSection creation and validation."""
        section = ReportSection(
            id="section_1",
            title="Introduction",
            start_line=1,
            end_line=10,
            content="This is the introduction section."
        )
        
        assert section.id == "section_1"
        assert section.title == "Introduction"
        assert section.start_line == 1
        assert section.end_line == 10
        assert section.validate()
    
    def test_report_section_invalid_lines(self):
        """Test ReportSection validation with invalid line numbers."""
        section = ReportSection(
            id="section_1",
            title="Introduction",
            start_line=10,
            end_line=5,  # Invalid: end before start
            content="This is the introduction section."
        )
        
        assert not section.validate()
    
    def test_report_creation(self):
        """Test Report creation and validation."""
        now = datetime.now()
        
        metadata = ReportMetadata(
            created_at=now,
            modified_at=now,
            file_size=1024,
            line_count=50
        )
        
        section = ReportSection(
            id="section_1",
            title="Introduction",
            start_line=1,
            end_line=10,
            content="This is the introduction section."
        )
        
        report = Report(
            id="report_1",
            filename="test_report.txt",
            content="Full report content here...",
            sections=[section.to_dict()],
            metadata=metadata.to_dict()
        )
        
        assert report.id == "report_1"
        assert report.filename == "test_report.txt"
        assert len(report.sections) == 1
        assert isinstance(report.sections[0], ReportSection)
        assert isinstance(report.metadata, ReportMetadata)
        assert report.validate()
    
    def test_report_json_serialization(self):
        """Test Report JSON serialization and deserialization."""
        now = datetime.now()
        
        metadata = ReportMetadata(
            created_at=now,
            modified_at=now,
            file_size=1024,
            line_count=50
        )
        
        section = ReportSection(
            id="section_1",
            title="Introduction",
            start_line=1,
            end_line=10,
            content="This is the introduction section."
        )
        
        report = Report(
            id="report_1",
            filename="test_report.txt",
            content="Full report content here...",
            sections=[section.to_dict()],
            metadata=metadata.to_dict()
        )
        
        # Test to_dict and to_json
        report_dict = report.to_dict()
        assert isinstance(report_dict, dict)
        assert report_dict['id'] == "report_1"
        
        json_str = report.to_json()
        assert isinstance(json_str, str)
        
        # Test from_dict and from_json
        report_from_dict = Report.from_dict(report_dict)
        assert report_from_dict.id == report.id
        assert report_from_dict.filename == report.filename
        
        report_from_json = Report.from_json(json_str)
        assert report_from_json.id == report.id
        assert report_from_json.filename == report.filename


class TestCommentModels:
    """Test cases for Comment-related models."""
    
    def test_text_selection_creation(self):
        """Test TextSelection creation and validation."""
        selection = TextSelection(
            start_position=10,
            end_position=25,
            selected_text="selected text here"
        )
        
        assert selection.start_position == 10
        assert selection.end_position == 25
        assert selection.selected_text == "selected text here"
        assert selection.validate()
        assert selection.get_selection_length() == 15
    
    def test_text_selection_invalid_positions(self):
        """Test TextSelection validation with invalid positions."""
        selection = TextSelection(
            start_position=25,
            end_position=10,  # Invalid: end before start
            selected_text="selected text here"
        )
        
        assert not selection.validate()
    
    def test_comment_creation(self):
        """Test Comment creation and validation."""
        now = datetime.now()
        
        selection = TextSelection(
            start_position=10,
            end_position=25,
            selected_text="selected text here"
        )
        
        comment = Comment(
            id="comment_1",
            report_id="report_1",
            text_selection=selection.to_dict(),
            comment_text="This is a comment about the selected text.",
            author="John Doe",
            timestamp=now,
            section_context="Introduction section context"
        )
        
        assert comment.id == "comment_1"
        assert comment.report_id == "report_1"
        assert isinstance(comment.text_selection, TextSelection)
        assert comment.comment_text == "This is a comment about the selected text."
        assert comment.author == "John Doe"
        assert comment.validate()
    
    def test_comment_json_serialization(self):
        """Test Comment JSON serialization and deserialization."""
        now = datetime.now()
        
        selection = TextSelection(
            start_position=10,
            end_position=25,
            selected_text="selected text here"
        )
        
        comment = Comment(
            id="comment_1",
            report_id="report_1",
            text_selection=selection.to_dict(),
            comment_text="This is a comment about the selected text.",
            author="John Doe",
            timestamp=now,
            section_context="Introduction section context"
        )
        
        # Test serialization
        comment_dict = comment.to_dict()
        assert isinstance(comment_dict, dict)
        assert comment_dict['id'] == "comment_1"
        
        json_str = comment.to_json()
        assert isinstance(json_str, str)
        
        # Test deserialization
        comment_from_dict = Comment.from_dict(comment_dict)
        assert comment_from_dict.id == comment.id
        assert comment_from_dict.comment_text == comment.comment_text


class TestSummaryModels:
    """Test cases for Summary-related models."""
    
    def test_summary_statistics_creation(self):
        """Test SummaryStatistics creation and validation."""
        stats = SummaryStatistics(
            most_commented_section="Introduction",
            average_comment_length=45.5,
            total_review_time="2 hours 30 minutes"
        )
        
        assert stats.most_commented_section == "Introduction"
        assert stats.average_comment_length == 45.5
        assert stats.total_review_time == "2 hours 30 minutes"
        assert stats.validate()
    
    def test_comments_by_section_creation(self):
        """Test CommentsBySection creation and validation."""
        comments_data = [
            {
                'selected_text': 'important text',
                'comment': 'This is important',
                'author': 'John Doe',
                'timestamp': '2024-01-01T10:00:00'
            }
        ]
        
        section = CommentsBySection(
            section_title="Introduction",
            section_content="This is the introduction content...",
            comments=comments_data
        )
        
        assert section.section_title == "Introduction"
        assert len(section.comments) == 1
        assert section.get_comment_count() == 1
        assert section.validate()
    
    def test_summary_creation(self):
        """Test Summary creation and validation."""
        now = datetime.now()
        
        comments_data = [
            {
                'selected_text': 'important text',
                'comment': 'This is important',
                'author': 'John Doe',
                'timestamp': '2024-01-01T10:00:00'
            }
        ]
        
        section = CommentsBySection(
            section_title="Introduction",
            section_content="This is the introduction content...",
            comments=comments_data
        )
        
        stats = SummaryStatistics(
            most_commented_section="Introduction",
            average_comment_length=45.5,
            total_review_time="2 hours 30 minutes"
        )
        
        summary = Summary(
            report_id="report_1",
            generated_at=now,
            total_comments=1,
            comments_by_section=[section.to_dict()],
            summary_statistics=stats.to_dict()
        )
        
        assert summary.report_id == "report_1"
        assert summary.total_comments == 1
        assert len(summary.comments_by_section) == 1
        assert isinstance(summary.comments_by_section[0], CommentsBySection)
        assert isinstance(summary.summary_statistics, SummaryStatistics)
        assert summary.validate()
    
    def test_summary_json_serialization(self):
        """Test Summary JSON serialization and deserialization."""
        now = datetime.now()
        
        comments_data = [
            {
                'selected_text': 'important text',
                'comment': 'This is important',
                'author': 'John Doe',
                'timestamp': '2024-01-01T10:00:00'
            }
        ]
        
        section = CommentsBySection(
            section_title="Introduction",
            section_content="This is the introduction content...",
            comments=comments_data
        )
        
        stats = SummaryStatistics(
            most_commented_section="Introduction",
            average_comment_length=45.5,
            total_review_time="2 hours 30 minutes"
        )
        
        summary = Summary(
            report_id="report_1",
            generated_at=now,
            total_comments=1,
            comments_by_section=[section.to_dict()],
            summary_statistics=stats.to_dict()
        )
        
        # Test serialization
        summary_dict = summary.to_dict()
        assert isinstance(summary_dict, dict)
        assert summary_dict['report_id'] == "report_1"
        
        json_str = summary.to_json()
        assert isinstance(json_str, str)
        
        # Test deserialization
        summary_from_dict = Summary.from_dict(summary_dict)
        assert summary_from_dict.report_id == summary.report_id
        assert summary_from_dict.total_comments == summary.total_comments


if __name__ == "__main__":
    pytest.main([__file__])