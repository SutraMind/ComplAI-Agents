"""
Security utilities for file path validation and access control.
"""

import os
import re
from pathlib import Path
from typing import List, Optional


class PathValidator:
    """Validates file paths for security and correctness."""
    
    # Dangerous path patterns to block
    DANGEROUS_PATTERNS = [
        r'\.\./',  # Directory traversal
        r'\.\.\\'  # Windows directory traversal
    ]
    
    # Allowed file extensions
    ALLOWED_EXTENSIONS = {'.txt', '.json', '.md'}
    
    def __init__(self, base_directory: str):
        """Initialize with base directory for path validation."""
        self.base_directory = Path(base_directory).resolve()
        
        # Ensure base directory exists
        self.base_directory.mkdir(parents=True, exist_ok=True)
    
    def is_safe_path(self, file_path: str) -> bool:
        """Check if a file path is safe from directory traversal attacks."""
        # Check for dangerous patterns
        for pattern in self.DANGEROUS_PATTERNS:
            if re.search(pattern, file_path):
                return False
        
        # Resolve the path and check if it's within base directory
        try:
            resolved_path = (self.base_directory / file_path).resolve()
            return resolved_path.is_relative_to(self.base_directory)
        except (ValueError, OSError):
            return False
    
    def validate_filename(self, filename: str) -> bool:
        """Validate filename for security and format."""
        if not filename or not filename.strip():
            return False
        
        # Check for invalid characters
        invalid_chars = '<>:"|?*'
        if any(char in filename for char in invalid_chars):
            return False
        
        # Check for reserved names (Windows)
        reserved_names = {
            'CON', 'PRN', 'AUX', 'NUL',
            'COM1', 'COM2', 'COM3', 'COM4', 'COM5', 'COM6', 'COM7', 'COM8', 'COM9',
            'LPT1', 'LPT2', 'LPT3', 'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9'
        }
        
        name_without_ext = Path(filename).stem.upper()
        if name_without_ext in reserved_names:
            return False
        
        return True
    
    def validate_extension(self, filename: str) -> bool:
        """Validate file extension."""
        extension = Path(filename).suffix.lower()
        return extension in self.ALLOWED_EXTENSIONS
    
    def get_safe_path(self, file_path: str) -> Optional[Path]:
        """Get a safe, resolved path within the base directory."""
        if not self.is_safe_path(file_path):
            return None
        
        return (self.base_directory / file_path).resolve()
    
    def sanitize_filename(self, filename: str) -> str:
        """Sanitize filename by removing/replacing invalid characters."""
        # Remove invalid characters
        invalid_chars = '<>:"|?*'
        sanitized = filename
        
        for char in invalid_chars:
            sanitized = sanitized.replace(char, '_')
        
        # Remove leading/trailing whitespace and dots
        sanitized = sanitized.strip(' .')
        
        # Ensure it's not empty
        if not sanitized:
            sanitized = 'unnamed_file'
        
        return sanitized


class SecurityManager:
    """Manages security aspects of file operations."""
    
    def __init__(self, data_directory: str):
        """Initialize security manager with data directory."""
        self.data_directory = Path(data_directory)
        self.path_validator = PathValidator(data_directory)
    
    def validate_file_access(self, file_path: str, operation: str = 'read') -> bool:
        """Validate if file access is allowed for the given operation."""
        # Check path safety
        if not self.path_validator.is_safe_path(file_path):
            return False
        
        # Get the actual file path
        safe_path = self.path_validator.get_safe_path(file_path)
        if not safe_path:
            return False
        
        # For read operations, file should exist
        if operation == 'read' and not safe_path.exists():
            return False
        
        # For write operations, check if directory is writable
        if operation in ['write', 'create']:
            parent_dir = safe_path.parent
            if not parent_dir.exists():
                try:
                    parent_dir.mkdir(parents=True, exist_ok=True)
                except OSError:
                    return False
            
            # Check if directory is writable
            if not os.access(parent_dir, os.W_OK):
                return False
        
        return True
    
    def get_secure_file_path(self, relative_path: str, filename: str) -> Optional[Path]:
        """Get a secure file path for the given relative path and filename."""
        # Validate and sanitize filename
        if not self.path_validator.validate_filename(filename):
            filename = self.path_validator.sanitize_filename(filename)
        
        # Construct full path
        full_path = os.path.join(relative_path, filename)
        
        # Validate the full path
        if not self.validate_file_access(full_path, 'write'):
            return None
        
        return self.path_validator.get_safe_path(full_path)
    
    def create_secure_directory(self, directory_path: str) -> bool:
        """Create a directory securely within the data directory."""
        if not self.path_validator.is_safe_path(directory_path):
            return False
        
        safe_path = self.path_validator.get_safe_path(directory_path)
        if not safe_path:
            return False
        
        try:
            safe_path.mkdir(parents=True, exist_ok=True)
            return True
        except OSError:
            return False
    
    def list_safe_files(self, directory_path: str, extension_filter: Optional[str] = None) -> List[str]:
        """List files in a directory safely."""
        if not self.path_validator.is_safe_path(directory_path):
            return []
        
        safe_path = self.path_validator.get_safe_path(directory_path)
        if not safe_path or not safe_path.exists() or not safe_path.is_dir():
            return []
        
        files = []
        try:
            for file_path in safe_path.iterdir():
                if file_path.is_file():
                    # Apply extension filter if provided
                    if extension_filter and not file_path.name.endswith(extension_filter):
                        continue
                    
                    # Validate file extension
                    if self.path_validator.validate_extension(file_path.name):
                        files.append(file_path.name)
        except OSError:
            return []
        
        return sorted(files)
    
    def get_file_info(self, file_path: str) -> Optional[dict]:
        """Get safe file information."""
        if not self.validate_file_access(file_path, 'read'):
            return None
        
        safe_path = self.path_validator.get_safe_path(file_path)
        if not safe_path or not safe_path.exists():
            return None
        
        try:
            stat = safe_path.stat()
            return {
                'size': stat.st_size,
                'modified': stat.st_mtime,
                'created': stat.st_ctime,
                'is_file': safe_path.is_file(),
                'is_directory': safe_path.is_dir(),
                'extension': safe_path.suffix.lower()
            }
        except OSError:
            return None