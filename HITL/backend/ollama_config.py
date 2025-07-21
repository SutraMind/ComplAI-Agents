"""
Ollama server connection configuration and utilities.
"""
import requests
import json
from typing import Dict, Any, Optional
from .config import Config

class OllamaConfig:
    """Ollama server configuration and connection utilities."""
    
    def __init__(self, url: str = None, model: str = None):
        """Initialize Ollama configuration."""
        self.url = url or Config.OLLAMA_URL
        self.model = model or Config.OLLAMA_MODEL
        self.timeout = 30  # seconds
    
    def test_connection(self) -> Dict[str, Any]:
        """Test connection to Ollama server."""
        try:
            response = requests.get(f"{self.url}/api/tags", timeout=self.timeout)
            if response.status_code == 200:
                return {
                    'status': 'connected',
                    'url': self.url,
                    'available_models': response.json().get('models', [])
                }
            else:
                return {
                    'status': 'error',
                    'message': f'Server returned status {response.status_code}'
                }
        except requests.exceptions.ConnectionError:
            return {
                'status': 'error',
                'message': f'Cannot connect to Ollama server at {self.url}'
            }
        except requests.exceptions.Timeout:
            return {
                'status': 'error',
                'message': 'Connection timeout'
            }
        except Exception as e:
            return {
                'status': 'error',
                'message': f'Unexpected error: {str(e)}'
            }
    
    def check_model_availability(self) -> Dict[str, Any]:
        """Check if the configured model is available."""
        connection_status = self.test_connection()
        
        if connection_status['status'] != 'connected':
            return connection_status
        
        available_models = [model['name'] for model in connection_status.get('available_models', [])]
        
        if self.model in available_models:
            return {
                'status': 'available',
                'model': self.model,
                'message': f'Model {self.model} is available'
            }
        else:
            return {
                'status': 'unavailable',
                'model': self.model,
                'available_models': available_models,
                'message': f'Model {self.model} is not available. Available models: {available_models}'
            }
    
    def get_model_info(self) -> Optional[Dict[str, Any]]:
        """Get information about the configured model."""
        try:
            response = requests.post(
                f"{self.url}/api/show",
                json={'name': self.model},
                timeout=self.timeout
            )
            if response.status_code == 200:
                return response.json()
            return None
        except Exception:
            return None

# Global instance
ollama_config = OllamaConfig()