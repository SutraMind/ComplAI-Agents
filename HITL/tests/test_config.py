"""
Tests for application configuration.
"""
import unittest
import os
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'backend'))

from backend.config import Config, DevelopmentConfig, ProductionConfig
from backend.app import create_app

class TestConfig(unittest.TestCase):
    """Test configuration classes."""
    
    def test_base_config(self):
        """Test base configuration values."""
        self.assertIsNotNone(Config.SECRET_KEY)
        self.assertEqual(Config.OLLAMA_URL, 'http://localhost:11434')
        self.assertEqual(Config.OLLAMA_MODEL, 'gemma2:27b')
        self.assertEqual(Config.MAX_CONTENT_LENGTH, 16 * 1024 * 1024)
    
    def test_development_config(self):
        """Test development configuration."""
        self.assertTrue(DevelopmentConfig.DEBUG)
    
    def test_production_config(self):
        """Test production configuration."""
        self.assertFalse(ProductionConfig.DEBUG)
    
    def test_app_creation(self):
        """Test Flask app creation."""
        app = create_app('development')
        self.assertIsNotNone(app)
        self.assertTrue(app.config['DEBUG'])
        
        app = create_app('production')
        self.assertFalse(app.config['DEBUG'])

class TestOllamaConfig(unittest.TestCase):
    """Test Ollama configuration."""
    
    def test_ollama_config_import(self):
        """Test that Ollama config can be imported."""
        from backend.ollama_config import OllamaConfig, ollama_config
        
        self.assertIsInstance(ollama_config, OllamaConfig)
        self.assertEqual(ollama_config.url, 'http://localhost:11434')
        self.assertEqual(ollama_config.model, 'gemma2:27b')

if __name__ == '__main__':
    unittest.main()