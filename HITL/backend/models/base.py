"""
Base model class with common functionality for all data models.
"""

import json
from datetime import datetime
from typing import Dict, Any, Optional
from abc import ABC, abstractmethod


class BaseModel(ABC):
    """Base class for all data models with validation and serialization."""
    
    def __init__(self, **kwargs):
        """Initialize model with keyword arguments."""
        self._validate_required_fields(kwargs)
        self._set_attributes(kwargs)
    
    @abstractmethod
    def _get_required_fields(self) -> list:
        """Return list of required field names."""
        pass
    
    @abstractmethod
    def _get_field_types(self) -> Dict[str, type]:
        """Return dictionary mapping field names to their expected types."""
        pass
    
    def _validate_required_fields(self, data: Dict[str, Any]) -> None:
        """Validate that all required fields are present."""
        required_fields = self._get_required_fields()
        missing_fields = [field for field in required_fields if field not in data]
        
        if missing_fields:
            raise ValueError(f"Missing required fields: {', '.join(missing_fields)}")
    
    def _validate_field_types(self, data: Dict[str, Any]) -> None:
        """Validate field types against expected types."""
        field_types = self._get_field_types()
        
        for field_name, expected_type in field_types.items():
            if field_name in data and data[field_name] is not None:
                value = data[field_name]
                
                # Special handling for datetime strings
                if expected_type == datetime and isinstance(value, str):
                    try:
                        data[field_name] = datetime.fromisoformat(value.replace('Z', '+00:00'))
                    except ValueError:
                        raise ValueError(f"Invalid datetime format for field '{field_name}': {value}")
                elif not isinstance(value, expected_type):
                    raise TypeError(f"Field '{field_name}' must be of type {expected_type.__name__}, got {type(value).__name__}")
    
    def _set_attributes(self, data: Dict[str, Any]) -> None:
        """Set object attributes from data dictionary."""
        self._validate_field_types(data)
        
        for key, value in data.items():
            setattr(self, key, value)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary for JSON serialization."""
        result = {}
        
        for key, value in self.__dict__.items():
            if isinstance(value, datetime):
                result[key] = value.isoformat()
            elif isinstance(value, BaseModel):
                result[key] = value.to_dict()
            elif isinstance(value, list):
                result[key] = [
                    item.to_dict() if isinstance(item, BaseModel) else item
                    for item in value
                ]
            else:
                result[key] = value
        
        return result
    
    def to_json(self) -> str:
        """Convert model to JSON string."""
        return json.dumps(self.to_dict(), indent=2)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]):
        """Create model instance from dictionary."""
        return cls(**data)
    
    @classmethod
    def from_json(cls, json_str: str):
        """Create model instance from JSON string."""
        try:
            data = json.loads(json_str)
            return cls.from_dict(data)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON format: {e}")
    
    def validate(self) -> bool:
        """Validate the current model instance."""
        try:
            self._validate_required_fields(self.__dict__)
            self._validate_field_types(self.__dict__)
            return True
        except (ValueError, TypeError):
            return False
    
    def __repr__(self) -> str:
        """String representation of the model."""
        class_name = self.__class__.__name__
        attrs = ', '.join(f"{k}={v!r}" for k, v in self.__dict__.items())
        return f"{class_name}({attrs})"