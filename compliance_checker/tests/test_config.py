"""
Tests for configuration management system.
"""

import pytest
import tempfile
import os
from pathlib import Path

from ..config.settings import SystemConfig, OllamaConfig, VectorStoreConfig
from ..config.manager import ConfigurationManager


class TestSystemConfig:
    """Test the SystemConfig class."""
    
    def test_default_config_creation(self):
        """Test creating a default configuration."""
        config = SystemConfig()
        
        assert config.ollama.base_url == "http://localhost:11434"
        assert config.ollama.cc_agent_1_model == "deepseek-r1:8b"
        assert config.ollama.cc_agent_2_model == "Gemma3:27b"
        assert config.ollama.ra_agent_model == "qwq:32b"
        assert config.vector_store.gdpr_docs_path == "GDPR_docs"
        assert config.agents.max_feedback_iterations == 3
    
    def test_config_from_env(self):
        """Test creating configuration from environment variables."""
        # Set environment variables
        os.environ['OLLAMA_BASE_URL'] = 'http://test:11434'
        os.environ['CC_AGENT_1_MODEL'] = 'test-model-1'
        os.environ['MAX_FEEDBACK_ITERATIONS'] = '5'
        
        try:
            config = SystemConfig.from_env()
            
            assert config.ollama.base_url == 'http://test:11434'
            assert config.ollama.cc_agent_1_model == 'test-model-1'
            assert config.agents.max_feedback_iterations == 5
        
        finally:
            # Clean up environment variables
            for key in ['OLLAMA_BASE_URL', 'CC_AGENT_1_MODEL', 'MAX_FEEDBACK_ITERATIONS']:
                if key in os.environ:
                    del os.environ[key]
    
    def test_config_validation(self):
        """Test configuration validation."""
        config = SystemConfig()
        
        # Valid configuration should pass
        with tempfile.TemporaryDirectory() as temp_dir:
            config.vector_store.gdpr_docs_path = temp_dir
            errors = config.validate()
            assert len(errors) == 0
        
        # Invalid configuration should fail
        config.vector_store.gdpr_docs_path = "/nonexistent/path"
        config.ollama.timeout = -1
        config.agents.max_feedback_iterations = 0
        
        errors = config.validate()
        assert len(errors) > 0
        assert any("does not exist" in error for error in errors)
        assert any("timeout must be positive" in error for error in errors)
        assert any("iterations must be at least 1" in error for error in errors)


class TestConfigurationManager:
    """Test the ConfigurationManager class."""
    
    def test_load_default_config(self):
        """Test loading default configuration when no file exists."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_file = Path(temp_dir) / "nonexistent.yaml"
            manager = ConfigurationManager(config_file)
            
            # Mock the GDPR docs path to exist for validation
            with tempfile.TemporaryDirectory() as gdpr_temp:
                os.environ['GDPR_DOCS_PATH'] = gdpr_temp
                try:
                    config = manager.load_config()
                    assert isinstance(config, SystemConfig)
                    assert config.vector_store.gdpr_docs_path == gdpr_temp
                finally:
                    if 'GDPR_DOCS_PATH' in os.environ:
                        del os.environ['GDPR_DOCS_PATH']
    
    def test_save_and_load_config(self):
        """Test saving and loading configuration from file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_file = Path(temp_dir) / "test_config.yaml"
            manager = ConfigurationManager(config_file)
            
            # Create a test configuration
            config = SystemConfig()
            config.ollama.base_url = "http://test:11434"
            config.agents.max_feedback_iterations = 5
            
            # Create GDPR docs directory for validation
            gdpr_dir = Path(temp_dir) / "gdpr_docs"
            gdpr_dir.mkdir()
            config.vector_store.gdpr_docs_path = str(gdpr_dir)
            
            # Save configuration
            manager.save_config(config, config_file)
            assert config_file.exists()
            
            # Load configuration
            loaded_config = manager.load_config()
            assert loaded_config.ollama.base_url == "http://test:11434"
            assert loaded_config.agents.max_feedback_iterations == 5
    
    def test_config_validation_error(self):
        """Test that configuration validation errors are raised."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_file = Path(temp_dir) / "invalid_config.yaml"
            
            # Create invalid config file
            with open(config_file, 'w') as f:
                f.write("""
ollama:
  timeout: -1
vector_store:
  gdpr_docs_path: "/nonexistent/path"
agents:
  max_feedback_iterations: 0
""")
            
            manager = ConfigurationManager(config_file)
            
            with pytest.raises(ValueError) as exc_info:
                manager.load_config()
            
            assert "Configuration validation failed" in str(exc_info.value)


class TestOllamaConfig:
    """Test the OllamaConfig class."""
    
    def test_default_model_settings(self):
        """Test that default model settings are properly configured."""
        config = OllamaConfig()
        
        assert "deepseek-r1:8b" in config.model_settings
        assert "Gemma3:27b" in config.model_settings
        assert "qwq:32b" in config.model_settings
        
        # Check model-specific settings
        deepseek_settings = config.model_settings["deepseek-r1:8b"]
        assert deepseek_settings["temperature"] == 0.1
        assert deepseek_settings["max_tokens"] == 4096
        
        qwq_settings = config.model_settings["qwq:32b"]
        assert qwq_settings["max_tokens"] == 8192  # Higher for RA agent


class TestVectorStoreConfig:
    """Test the VectorStoreConfig class."""
    
    def test_default_vector_store_settings(self):
        """Test default vector store configuration."""
        config = VectorStoreConfig()
        
        assert config.gdpr_docs_path == "GDPR_docs"
        assert config.chunk_size == 512
        assert config.chunk_overlap == 50
        assert config.top_k_results == 5
        assert config.similarity_threshold == 0.7