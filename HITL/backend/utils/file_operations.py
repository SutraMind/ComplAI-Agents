"""
File operations utilities for safe data persistence.
"""

import json
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Union
from .security import SecurityManager


class FileManager:
    """Manages file operations with security and error handling."""
    
    def __init__(self, base_directory: str):
        """Initialize file manager with base directory."""
        self.base_directory = Path(base_directory)
        self.security_manager = SecurityManager(base_directory)
        
        # Ensure base directory exists
        self.base_directory.mkdir(parents=True, exist_ok=True)
    
    def read_text_file(self, file_path: str, encoding: str = 'utf-8') -> Optional[str]:
        """Read a text file safely."""
        if not self.security_manager.validate_file_access(file_path, 'read'):
            return None
        
        safe_path = self.security_manager.path_validator.get_safe_path(file_path)
        if not safe_path:
            return None
        
        try:
            with open(safe_path, 'r', encoding=encoding) as file:
                return file.read()
        except (IOError, UnicodeDecodeError) as e:
            print(f"Error reading file {file_path}: {e}")
            return None
    
    def write_text_file(self, file_path: str, content: str, encoding: str = 'utf-8') -> bool:
        """Write content to a text file safely."""
        if not self.security_manager.validate_file_access(file_path, 'write'):
            return False
        
        safe_path = self.security_manager.path_validator.get_safe_path(file_path)
        if not safe_path:
            return False
        
        try:
            # Ensure parent directory exists
            safe_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(safe_path, 'w', encoding=encoding) as file:
                file.write(content)
            return True
        except IOError as e:
            print(f"Error writing file {file_path}: {e}")
            return False
    
    def copy_file(self, source_path: str, destination_path: str) -> bool:
        """Copy a file safely."""
        # Validate both source and destination
        if not self.security_manager.validate_file_access(source_path, 'read'):
            return False
        
        if not self.security_manager.validate_file_access(destination_path, 'write'):
            return False
        
        source_safe_path = self.security_manager.path_validator.get_safe_path(source_path)
        dest_safe_path = self.security_manager.path_validator.get_safe_path(destination_path)
        
        if not source_safe_path or not dest_safe_path:
            return False
        
        try:
            # Ensure destination directory exists
            dest_safe_path.parent.mkdir(parents=True, exist_ok=True)
            
            shutil.copy2(source_safe_path, dest_safe_path)
            return True
        except (IOError, shutil.Error) as e:
            print(f"Error copying file from {source_path} to {destination_path}: {e}")
            return False
    
    def delete_file(self, file_path: str) -> bool:
        """Delete a file safely."""
        if not self.security_manager.validate_file_access(file_path, 'read'):
            return False
        
        safe_path = self.security_manager.path_validator.get_safe_path(file_path)
        if not safe_path or not safe_path.exists():
            return False
        
        try:
            safe_path.unlink()
            return True
        except OSError as e:
            print(f"Error deleting file {file_path}: {e}")
            return False
    
    def create_directory(self, directory_path: str) -> bool:
        """Create a directory safely."""
        return self.security_manager.create_secure_directory(directory_path)
    
    def list_files(self, directory_path: str = "", extension_filter: Optional[str] = None) -> List[str]:
        """List files in a directory safely."""
        return self.security_manager.list_safe_files(directory_path, extension_filter)
    
    def file_exists(self, file_path: str) -> bool:
        """Check if a file exists safely."""
        if not self.security_manager.validate_file_access(file_path, 'read'):
            return False
        
        safe_path = self.security_manager.path_validator.get_safe_path(file_path)
        return safe_path is not None and safe_path.exists() and safe_path.is_file()
    
    def get_file_info(self, file_path: str) -> Optional[Dict[str, Any]]:
        """Get file information safely."""
        return self.security_manager.get_file_info(file_path)
    
    def backup_file(self, file_path: str, backup_suffix: str = '.backup') -> bool:
        """Create a backup of a file."""
        if not self.file_exists(file_path):
            return False
        
        backup_path = file_path + backup_suffix
        return self.copy_file(file_path, backup_path)


class DataPersistence:
    """Handles JSON data persistence with validation and error handling."""
    
    def __init__(self, base_directory: str):
        """Initialize data persistence with base directory."""
        self.file_manager = FileManager(base_directory)
        self.base_directory = base_directory
    
    def save_json(self, file_path: str, data: Union[Dict[str, Any], List[Any]], 
                  create_backup: bool = True) -> bool:
        """Save data as JSON file safely."""
        try:
            # Create backup if file exists and backup is requested
            if create_backup and self.file_manager.file_exists(file_path):
                backup_path = f"{file_path}.{datetime.now().strftime('%Y%m%d_%H%M%S')}.backup"
                if not self.file_manager.copy_file(file_path, backup_path):
                    print(f"Warning: Failed to create backup for {file_path}")
            
            # Convert data to JSON string
            json_content = json.dumps(data, indent=2, ensure_ascii=False, default=str)
            
            # Write to file
            return self.file_manager.write_text_file(file_path, json_content)
            
        except (TypeError, ValueError) as e:
            print(f"Error serializing data to JSON for {file_path}: {e}")
            return False
    
    def load_json(self, file_path: str) -> Optional[Union[Dict[str, Any], List[Any]]]:
        """Load data from JSON file safely."""
        content = self.file_manager.read_text_file(file_path)
        if content is None:
            return None
        
        try:
            return json.loads(content)
        except json.JSONDecodeError as e:
            print(f"Error parsing JSON from {file_path}: {e}")
            return None
    
    def save_model(self, file_path: str, model_instance, create_backup: bool = True) -> bool:
        """Save a model instance to JSON file."""
        if not hasattr(model_instance, 'to_dict'):
            print(f"Model instance must have 'to_dict' method")
            return False
        
        try:
            data = model_instance.to_dict()
            return self.save_json(file_path, data, create_backup)
        except Exception as e:
            print(f"Error saving model to {file_path}: {e}")
            return False
    
    def load_model(self, file_path: str, model_class):
        """Load a model instance from JSON file."""
        data = self.load_json(file_path)
        if data is None:
            return None
        
        try:
            if hasattr(model_class, 'from_dict'):
                return model_class.from_dict(data)
            else:
                return model_class(**data)
        except Exception as e:
            print(f"Error loading model from {file_path}: {e}")
            return None
    
    def save_models_list(self, file_path: str, models_list: List[Any], 
                        create_backup: bool = True) -> bool:
        """Save a list of model instances to JSON file."""
        try:
            data_list = []
            for model in models_list:
                if hasattr(model, 'to_dict'):
                    data_list.append(model.to_dict())
                else:
                    data_list.append(model)
            
            return self.save_json(file_path, data_list, create_backup)
        except Exception as e:
            print(f"Error saving models list to {file_path}: {e}")
            return False
    
    def load_models_list(self, file_path: str, model_class) -> Optional[List[Any]]:
        """Load a list of model instances from JSON file."""
        data = self.load_json(file_path)
        if data is None or not isinstance(data, list):
            return None
        
        try:
            models_list = []
            for item_data in data:
                if hasattr(model_class, 'from_dict'):
                    model = model_class.from_dict(item_data)
                else:
                    model = model_class(**item_data)
                models_list.append(model)
            
            return models_list
        except Exception as e:
            print(f"Error loading models list from {file_path}: {e}")
            return None
    
    def create_data_directories(self) -> bool:
        """Create standard data directories for the HITL system."""
        directories = [
            'reports',
            'comments', 
            'summaries',
            'backups'
        ]
        
        success = True
        for directory in directories:
            if not self.file_manager.create_directory(directory):
                print(f"Failed to create directory: {directory}")
                success = False
        
        return success
    
    def get_available_reports(self) -> List[str]:
        """Get list of available report files."""
        return self.file_manager.list_files('reports', '.txt')
    
    def get_available_comments(self, report_id: str) -> List[str]:
        """Get list of comment files for a specific report."""
        comments_dir = f'comments/{report_id}'
        return self.file_manager.list_files(comments_dir, '.json')
    
    def get_available_summaries(self) -> List[str]:
        """Get list of available summary files."""
        return self.file_manager.list_files('summaries', '.json')
    
    def cleanup_old_backups(self, max_backups: int = 10) -> bool:
        """Clean up old backup files, keeping only the most recent ones."""
        try:
            backup_files = self.file_manager.list_files('backups')
            
            if len(backup_files) <= max_backups:
                return True
            
            # Sort by modification time (newest first)
            backup_info = []
            for backup_file in backup_files:
                file_path = f'backups/{backup_file}'
                info = self.file_manager.get_file_info(file_path)
                if info:
                    backup_info.append((backup_file, info['modified']))
            
            backup_info.sort(key=lambda x: x[1], reverse=True)
            
            # Delete old backups
            for backup_file, _ in backup_info[max_backups:]:
                file_path = f'backups/{backup_file}'
                self.file_manager.delete_file(file_path)
            
            return True
        except Exception as e:
            print(f"Error cleaning up backups: {e}")
            return False
    
    def export_data(self, export_path: str, include_backups: bool = False) -> bool:
        """Export all data to a specified directory."""
        try:
            export_manager = FileManager(export_path)
            
            # Export reports
            reports = self.get_available_reports()
            for report in reports:
                source_path = f'reports/{report}'
                dest_path = f'reports/{report}'
                content = self.file_manager.read_text_file(source_path)
                if content:
                    export_manager.write_text_file(dest_path, content)
            
            # Export comments
            for report in reports:
                report_id = Path(report).stem
                comments = self.get_available_comments(report_id)
                for comment_file in comments:
                    source_path = f'comments/{report_id}/{comment_file}'
                    dest_path = f'comments/{report_id}/{comment_file}'
                    data = self.load_json(source_path)
                    if data:
                        export_manager.file_manager.security_manager.create_secure_directory(f'comments/{report_id}')
                        DataPersistence(export_path).save_json(dest_path, data, create_backup=False)
            
            # Export summaries
            summaries = self.get_available_summaries()
            for summary in summaries:
                source_path = f'summaries/{summary}'
                dest_path = f'summaries/{summary}'
                data = self.load_json(source_path)
                if data:
                    DataPersistence(export_path).save_json(dest_path, data, create_backup=False)
            
            return True
        except Exception as e:
            print(f"Error exporting data: {e}")
            return False