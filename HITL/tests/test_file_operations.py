"""
Tests for file operations utilities.
"""

import pytest
import tempfile
import shutil
import os
import json
from datetime import datetime
import sys

# Add the backend directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from utils.file_operations import FileManager, DataPersistence
from utils.security import PathValidator, SecurityManager
from models.report import Report, ReportSection, ReportMetadata


class TestPathValidator:
    """Test cases for PathValidator."""
    
    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.validator = PathValidator(self.temp_dir)
    
    def teardown_method(self):
        """Clean up test environment."""
        shutil.rmtree(self.temp_dir)
    
    def test_safe_path_validation(self):
        """Test safe path validation."""
        # Safe paths
        assert self.validator.is_safe_path("test.txt")
        assert self.validator.is_safe_path("folder/test.txt")
        assert self.validator.is_safe_path("reports/report1.txt")
        
        # Unsafe paths
        assert not self.validator.is_safe_path("../test.txt")
        assert not self.validator.is_safe_path("..\\test.txt")
        assert not self.validator.is_safe_path("/etc/passwd")
    
    def test_filename_validation(self):
        """Test filename validation."""
        # Valid filenames
        assert self.validator.validate_filename("test.txt")
        assert self.validator.validate_filename("report_1.json")
        assert self.validator.validate_filename("my-file.md")
        
        # Invalid filenames
        assert not self.validator.validate_filename("test<file>.txt")
        assert not self.validator.validate_filename("test|file.txt")
        assert not self.validator.validate_filename("CON.txt")  # Reserved name
        assert not self.validator.validate_filename("")
    
    def test_extension_validation(self):
        """Test file extension validation."""
        # Valid extensions
        assert self.validator.validate_extension("test.txt")
        assert self.validator.validate_extension("data.json")
        assert self.validator.validate_extension("readme.md")
        
        # Invalid extensions
        assert not self.validator.validate_extension("test.exe")
        assert not self.validator.validate_extension("script.py")
        assert not self.validator.validate_extension("file.doc")
    
    def test_filename_sanitization(self):
        """Test filename sanitization."""
        assert self.validator.sanitize_filename("test<file>.txt") == "test_file_.txt"
        assert self.validator.sanitize_filename("test|file.txt") == "test_file.txt"
        assert self.validator.sanitize_filename("  test.txt  ") == "test.txt"
        assert self.validator.sanitize_filename("") == "unnamed_file"


class TestFileManager:
    """Test cases for FileManager."""
    
    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.file_manager = FileManager(self.temp_dir)
    
    def teardown_method(self):
        """Clean up test environment."""
        shutil.rmtree(self.temp_dir)
    
    def test_text_file_operations(self):
        """Test text file read/write operations."""
        test_content = "This is test content\nWith multiple lines"
        file_path = "test.txt"
        
        # Write file
        assert self.file_manager.write_text_file(file_path, test_content)
        
        # Read file
        read_content = self.file_manager.read_text_file(file_path)
        assert read_content == test_content
        
        # Check file exists
        assert self.file_manager.file_exists(file_path)
    
    def test_directory_operations(self):
        """Test directory creation and listing."""
        # Create directory
        assert self.file_manager.create_directory("test_dir")
        
        # Create file in directory
        file_path = "test_dir/test.txt"
        assert self.file_manager.write_text_file(file_path, "test content")
        
        # List files
        files = self.file_manager.list_files("test_dir")
        assert "test.txt" in files
    
    def test_file_copy_and_delete(self):
        """Test file copy and delete operations."""
        # Create source file
        source_path = "source.txt"
        test_content = "Source file content"
        assert self.file_manager.write_text_file(source_path, test_content)
        
        # Copy file
        dest_path = "destination.txt"
        assert self.file_manager.copy_file(source_path, dest_path)
        
        # Verify copy
        assert self.file_manager.file_exists(dest_path)
        read_content = self.file_manager.read_text_file(dest_path)
        assert read_content == test_content
        
        # Delete file
        assert self.file_manager.delete_file(dest_path)
        assert not self.file_manager.file_exists(dest_path)
    
    def test_file_info(self):
        """Test file information retrieval."""
        file_path = "info_test.txt"
        test_content = "Test content for file info"
        
        assert self.file_manager.write_text_file(file_path, test_content)
        
        info = self.file_manager.get_file_info(file_path)
        assert info is not None
        assert info['is_file'] is True
        assert info['size'] > 0
        assert info['extension'] == '.txt'


class TestDataPersistence:
    """Test cases for DataPersistence."""
    
    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.data_persistence = DataPersistence(self.temp_dir)
    
    def teardown_method(self):
        """Clean up test environment."""
        shutil.rmtree(self.temp_dir)
    
    def test_json_operations(self):
        """Test JSON save/load operations."""
        test_data = {
            "name": "Test Data",
            "value": 42,
            "items": ["item1", "item2", "item3"]
        }
        
        file_path = "test_data.json"
        
        # Save JSON
        assert self.data_persistence.save_json(file_path, test_data)
        
        # Load JSON
        loaded_data = self.data_persistence.load_json(file_path)
        assert loaded_data == test_data
    
    def test_model_operations(self):
        """Test model save/load operations."""
        now = datetime.now()
        
        # Create test model
        metadata = ReportMetadata(
            created_at=now,
            modified_at=now,
            file_size=1024,
            line_count=50
        )
        
        section = ReportSection(
            id="section_1",
            title="Test Section",
            start_line=1,
            end_line=10,
            content="Test section content"
        )
        
        report = Report(
            id="test_report",
            filename="test.txt",
            content="Test report content",
            sections=[section.to_dict()],
            metadata=metadata.to_dict()
        )
        
        file_path = "test_report.json"
        
        # Save model
        assert self.data_persistence.save_model(file_path, report)
        
        # Load model
        loaded_report = self.data_persistence.load_model(file_path, Report)
        assert loaded_report is not None
        assert loaded_report.id == report.id
        assert loaded_report.filename == report.filename
        assert len(loaded_report.sections) == 1
    
    def test_models_list_operations(self):
        """Test models list save/load operations."""
        now = datetime.now()
        
        # Create test models
        metadata1 = ReportMetadata(
            created_at=now,
            modified_at=now,
            file_size=1024,
            line_count=50
        )
        
        metadata2 = ReportMetadata(
            created_at=now,
            modified_at=now,
            file_size=2048,
            line_count=100
        )
        
        models_list = [metadata1, metadata2]
        file_path = "metadata_list.json"
        
        # Save models list
        assert self.data_persistence.save_models_list(file_path, models_list)
        
        # Load models list
        loaded_list = self.data_persistence.load_models_list(file_path, ReportMetadata)
        assert loaded_list is not None
        assert len(loaded_list) == 2
        assert loaded_list[0].file_size == 1024
        assert loaded_list[1].file_size == 2048
    
    def test_data_directories_creation(self):
        """Test creation of standard data directories."""
        assert self.data_persistence.create_data_directories()
        
        # Check that directories were created
        expected_dirs = ['reports', 'comments', 'summaries', 'backups']
        for directory in expected_dirs:
            dir_path = os.path.join(self.temp_dir, directory)
            assert os.path.exists(dir_path)
            assert os.path.isdir(dir_path)
    
    def test_backup_functionality(self):
        """Test backup creation during save operations."""
        test_data = {"version": 1, "data": "original"}
        file_path = "backup_test.json"
        
        # Save initial data
        assert self.data_persistence.save_json(file_path, test_data, create_backup=False)
        
        # Update data with backup
        updated_data = {"version": 2, "data": "updated"}
        assert self.data_persistence.save_json(file_path, updated_data, create_backup=True)
        
        # Verify updated data
        loaded_data = self.data_persistence.load_json(file_path)
        assert loaded_data["version"] == 2
        
        # Check that backup was created
        files = self.data_persistence.file_manager.list_files("")
        backup_files = [f for f in files if f.startswith("backup_test.json.") and f.endswith(".backup")]
        assert len(backup_files) > 0


if __name__ == "__main__":
    pytest.main([__file__])