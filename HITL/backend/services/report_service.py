"""
Report service for managing report operations in the HITL Report Editor.
"""

import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any
from flask import current_app

from ..models.report import Report, ReportMetadata, ReportSection
from ..utils.file_operations import FileOperations, DataPersistence
from ..utils.security import SecurityValidator


class ReportService:
    """Service class for report management operations."""
    
    def __init__(self, data_directory: str = None):
        """Initialize the report service."""
        if data_directory is None:
            data_directory = str(current_app.config.get('DATA_DIR', 'data'))
        
        self.file_ops = FileOperations(data_directory)
        self.data_persistence = DataPersistence(data_directory)
        self.security = SecurityValidator(data_directory)
    
    def create_report(self, filename: str, content: str) -> Optional[Report]:
        """
        Create a new report from uploaded content.
        
        Args:
            filename: Name of the report file
            content: Text content of the report
            
        Returns:
            Report object if successful, None otherwise
        """
        try:
            # Validate inputs
            if not self.security.validate_filename(filename):
                raise ValueError(f"Invalid filename: {filename}")
            
            if not content.strip():
                raise ValueError("Report content cannot be empty")
            
            # Generate unique report ID
            report_id = str(uuid.uuid4())
            
            # Create metadata
            now = datetime.now()
            metadata = ReportMetadata(
                created_at=now,
                modified_at=now,
                file_size=len(content.encode('utf-8')),
                line_count=len(content.split('\n'))
            )
            
            # Parse content into sections
            sections = self._parse_content_into_sections(content)
            
            # Create report object
            report = Report(
                id=report_id,
                filename=filename,
                content=content,
                sections=sections,
                metadata=metadata
            )
            
            # Validate report
            if not report.validate():
                raise ValueError("Report validation failed")
            
            # Save report to file system
            if not self._save_report_to_file(report):
                raise RuntimeError("Failed to save report to file system")
            
            return report
            
        except Exception as e:
            current_app.logger.error(f"Error creating report: {str(e)}")
            return None
    
    def get_report(self, report_id: str) -> Optional[Report]:
        """
        Retrieve a report by its ID.
        
        Args:
            report_id: Unique identifier of the report
            
        Returns:
            Report object if found, None otherwise
        """
        try:
            if not self.security.validate_id(report_id):
                raise ValueError(f"Invalid report ID: {report_id}")
            
            # Try to load from JSON first
            report_data = self._load_report_from_file(report_id)
            if report_data:
                # Create report object from data
                report = Report.from_dict(report_data)
                
                # Validate loaded report
                if not report.validate():
                    current_app.logger.warning(f"Loaded report {report_id} failed validation")
                    return None
                
                return report
            
            # Try to load from text file
            reports_dir = Path(current_app.config['REPORTS_DIR'])
            for ext in ['.txt', '.md']:
                text_file = reports_dir / f"{report_id}{ext}"
                if text_file.exists():
                    content = text_file.read_text(encoding='utf-8')
                    stat = text_file.stat()
                    
                    # Create metadata
                    metadata = ReportMetadata(
                        created_at=datetime.fromtimestamp(stat.st_ctime),
                        modified_at=datetime.fromtimestamp(stat.st_mtime),
                        file_size=len(content.encode('utf-8')),
                        line_count=len(content.split('\n'))
                    )
                    
                    # Parse content into sections
                    sections = self._parse_content_into_sections(content)
                    
                    # Create report object
                    report = Report(
                        id=report_id,
                        filename=text_file.name,
                        content=content,
                        sections=sections,
                        metadata=metadata
                    )
                    
                    return report
            
            return None
            
        except Exception as e:
            current_app.logger.error(f"Error retrieving report {report_id}: {str(e)}")
            return None
    
    def update_report(self, report_id: str, content: str) -> Optional[Report]:
        """
        Update an existing report's content.
        
        Args:
            report_id: Unique identifier of the report
            content: New content for the report
            
        Returns:
            Updated Report object if successful, None otherwise
        """
        try:
            # Validate inputs
            if not self.security.validate_id(report_id):
                raise ValueError(f"Invalid report ID: {report_id}")
            
            if not content.strip():
                raise ValueError("Report content cannot be empty")
            
            # Get existing report
            existing_report = self.get_report(report_id)
            if not existing_report:
                raise ValueError(f"Report {report_id} not found")
            
            # Update content and metadata
            now = datetime.now()
            existing_report.content = content
            existing_report.metadata.modified_at = now
            existing_report.metadata.file_size = len(content.encode('utf-8'))
            existing_report.metadata.line_count = len(content.split('\n'))
            
            # Re-parse sections with new content
            existing_report.sections = self._parse_content_into_sections(content)
            
            # Validate updated report
            if not existing_report.validate():
                raise ValueError("Updated report validation failed")
            
            # Save updated report
            if not self._save_report_to_file(existing_report):
                raise RuntimeError("Failed to save updated report")
            
            return existing_report
            
        except Exception as e:
            current_app.logger.error(f"Error updating report {report_id}: {str(e)}")
            return None
    
    def delete_report(self, report_id: str) -> bool:
        """
        Delete a report and its associated files.
        
        Args:
            report_id: Unique identifier of the report
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if not self.security.validate_id(report_id):
                raise ValueError(f"Invalid report ID: {report_id}")
            
            # Check if report exists
            if not self.get_report(report_id):
                return False
            
            # Delete report file
            report_file = self._get_report_file_path(report_id)
            if report_file.exists():
                report_file.unlink()
            
            return True
            
        except Exception as e:
            current_app.logger.error(f"Error deleting report {report_id}: {str(e)}")
            return False
    
    def list_reports(self) -> List[Dict[str, Any]]:
        """
        Get a list of all available reports with basic metadata.
        
        Returns:
            List of report metadata dictionaries
        """
        try:
            reports_dir = Path(current_app.config['REPORTS_DIR'])
            report_list = []
            
            # Scan for both JSON and text files
            for report_file in reports_dir.glob('*'):
                if report_file.suffix in ['.json', '.txt', '.md']:
                    try:
                        report_id = report_file.stem
                        
                        if report_file.suffix == '.json':
                            # Load from JSON
                            report_data = self._load_report_from_file(report_id)
                            if report_data:
                                metadata = {
                                    'id': report_data.get('id'),
                                    'filename': report_data.get('filename'),
                                    'created_at': report_data.get('metadata', {}).get('created_at'),
                                    'modified_at': report_data.get('metadata', {}).get('modified_at'),
                                    'file_size': report_data.get('metadata', {}).get('file_size'),
                                    'line_count': report_data.get('metadata', {}).get('line_count'),
                                    'section_count': len(report_data.get('sections', []))
                                }
                                report_list.append(metadata)
                        else:
                            # Load from text file
                            content = report_file.read_text(encoding='utf-8')
                            stat = report_file.stat()
                            
                            metadata = {
                                'id': report_id,
                                'filename': report_file.name,
                                'created_at': datetime.fromtimestamp(stat.st_ctime).isoformat(),
                                'modified_at': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                                'file_size': len(content.encode('utf-8')),
                                'line_count': len(content.split('\n')),
                                'section_count': len(self._parse_content_into_sections(content))
                            }
                            report_list.append(metadata)
                        
                    except Exception as e:
                        current_app.logger.warning(f"Error processing report file {report_file}: {str(e)}")
                        continue
            
            # Sort by modified date (newest first)
            report_list.sort(key=lambda x: x.get('modified_at', ''), reverse=True)
            
            return report_list
            
        except Exception as e:
            current_app.logger.error(f"Error listing reports: {str(e)}")
            return []
    
    def get_report_sections(self, report_id: str) -> List[ReportSection]:
        """
        Get all sections for a specific report.
        
        Args:
            report_id: Unique identifier of the report
            
        Returns:
            List of ReportSection objects
        """
        try:
            report = self.get_report(report_id)
            if not report:
                return []
            
            return report.sections
            
        except Exception as e:
            current_app.logger.error(f"Error getting sections for report {report_id}: {str(e)}")
            return []
    
    def get_report_section(self, report_id: str, section_id: str) -> Optional[ReportSection]:
        """
        Get a specific section from a report.
        
        Args:
            report_id: Unique identifier of the report
            section_id: Unique identifier of the section
            
        Returns:
            ReportSection object if found, None otherwise
        """
        try:
            report = self.get_report(report_id)
            if not report:
                return None
            
            return report.get_section_by_id(section_id)
            
        except Exception as e:
            current_app.logger.error(f"Error getting section {section_id} from report {report_id}: {str(e)}")
            return None
    
    def _parse_content_into_sections(self, content: str) -> List[ReportSection]:
        """
        Parse report content into logical sections.
        
        Args:
            content: Text content to parse
            
        Returns:
            List of ReportSection objects
        """
        sections = []
        lines = content.split('\n')
        current_section = None
        section_lines = []
        
        for line_num, line in enumerate(lines, 1):
            # Check if line is a section header (starts with #, ##, etc. or is all caps)
            stripped_line = line.strip()
            
            if self._is_section_header(stripped_line):
                # Save previous section if exists
                if current_section and section_lines:
                    section_content = '\n'.join(section_lines)
                    section = ReportSection(
                        id=str(uuid.uuid4()),
                        title=current_section,
                        start_line=section_start_line,
                        end_line=line_num - 1,
                        content=section_content.strip()
                    )
                    sections.append(section)
                
                # Start new section
                current_section = stripped_line.lstrip('#').strip() or f"Section {len(sections) + 1}"
                section_start_line = line_num
                section_lines = []
            else:
                # Add line to current section
                section_lines.append(line)
        
        # Add final section
        if current_section and section_lines:
            section_content = '\n'.join(section_lines)
            section = ReportSection(
                id=str(uuid.uuid4()),
                title=current_section,
                start_line=section_start_line,
                end_line=len(lines),
                content=section_content.strip()
            )
            sections.append(section)
        
        # If no sections were found, create a single section with all content
        if not sections:
            section = ReportSection(
                id=str(uuid.uuid4()),
                title="Main Content",
                start_line=1,
                end_line=len(lines),
                content=content.strip()
            )
            sections.append(section)
        
        return sections
    
    def _is_section_header(self, line: str) -> bool:
        """
        Determine if a line is a section header.
        
        Args:
            line: Line to check
            
        Returns:
            True if line is a section header
        """
        if not line:
            return False
        
        # Markdown headers
        if line.startswith('#'):
            return True
        
        # All caps lines (likely headers)
        if len(line) > 3 and line.isupper() and not line.isdigit():
            return True
        
        # Lines ending with colon (likely headers)
        if line.endswith(':') and len(line.split()) <= 5:
            return True
        
        return False
    
    def _save_report_to_file(self, report: Report) -> bool:
        """
        Save report to file system.
        
        Args:
            report: Report object to save
            
        Returns:
            True if successful, False otherwise
        """
        try:
            report_file = self._get_report_file_path(report.id)
            report_data = report.to_dict()
            
            return self.data_persistence.save_json(f"reports/{report.id}.json", report_data)
            
        except Exception as e:
            current_app.logger.error(f"Error saving report {report.id}: {str(e)}")
            return False
    
    def _load_report_from_file(self, report_id: str) -> Optional[Dict[str, Any]]:
        """
        Load report data from file system.
        
        Args:
            report_id: Unique identifier of the report
            
        Returns:
            Report data dictionary if successful, None otherwise
        """
        try:
            report_file = self._get_report_file_path(report_id)
            
            if not report_file.exists():
                return None
            
            return self.data_persistence.load_json(f"reports/{report_id}.json")
            
        except Exception as e:
            current_app.logger.error(f"Error loading report {report_id}: {str(e)}")
            return None
    
    def _get_report_file_path(self, report_id: str) -> Path:
        """
        Get the file path for a report.
        
        Args:
            report_id: Unique identifier of the report
            
        Returns:
            Path object for the report file
        """
        reports_dir = Path(current_app.config['REPORTS_DIR'])
        return reports_dir / f"{report_id}.json"