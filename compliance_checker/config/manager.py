"""
Configuration manager for loading and managing system settings.
"""

import json
import yaml
from pathlib import Path
from typing import Dict, Any, Optional
import logging

from .settings import SystemConfig


class ConfigurationManager:
    """Manages configuration loading, validation, and updates."""
    
    def __init__(self, config_file: Optional[Path] = None):
        self.config_file = config_file or Path("config.yaml")
        self.config: Optional[SystemConfig] = None
        self.logger = logging.getLogger(__name__)
    
    def load_config(self) -> SystemConfig:
        """Load configuration from file or environment variables."""
        if self.config_file.exists():
            self.config = self._load_from_file()
        else:
            self.logger.info("Config file not found, using environment variables and defaults")
            self.config = SystemConfig.from_env()
        
        # Validate configuration
        errors = self.config.validate()
        if errors:
            error_msg = "Configuration validation failed:\n" + "\n".join(f"- {error}" for error in errors)
            raise ValueError(error_msg)
        
        # Create necessary directories
        self.config.create_directories()
        
        return self.config
    
    def _load_from_file(self) -> SystemConfig:
        """Load configuration from YAML or JSON file."""
        try:
            with open(self.config_file, 'r') as f:
                if self.config_file.suffix.lower() == '.json':
                    data = json.load(f)
                else:
                    data = yaml.safe_load(f)
            
            # Convert dict to SystemConfig
            return self._dict_to_config(data)
        
        except Exception as e:
            self.logger.error(f"Failed to load config from {self.config_file}: {e}")
            raise
    
    def _dict_to_config(self, data: Dict[str, Any]) -> SystemConfig:
        """Convert dictionary to SystemConfig object."""
        # This is a simplified implementation
        # In a real system, you might want to use a library like pydantic
        config = SystemConfig()
        
        if 'ollama' in data:
            ollama_data = data['ollama']
            if 'base_url' in ollama_data:
                config.ollama.base_url = ollama_data['base_url']
            if 'timeout' in ollama_data:
                config.ollama.timeout = ollama_data['timeout']
            if 'cc_agent_1_model' in ollama_data:
                config.ollama.cc_agent_1_model = ollama_data['cc_agent_1_model']
            if 'cc_agent_2_model' in ollama_data:
                config.ollama.cc_agent_2_model = ollama_data['cc_agent_2_model']
            if 'ra_agent_model' in ollama_data:
                config.ollama.ra_agent_model = ollama_data['ra_agent_model']
        
        if 'vector_store' in data:
            vs_data = data['vector_store']
            if 'gdpr_docs_path' in vs_data:
                config.vector_store.gdpr_docs_path = vs_data['gdpr_docs_path']
            if 'index_path' in vs_data:
                config.vector_store.index_path = vs_data['index_path']
        
        if 'processing' in data:
            proc_data = data['processing']
            if 'max_file_size_mb' in proc_data:
                config.processing.max_file_size_mb = proc_data['max_file_size_mb']
            if 'temp_dir' in proc_data:
                config.processing.temp_dir = proc_data['temp_dir']
            if 'output_dir' in proc_data:
                config.processing.output_dir = proc_data['output_dir']
        
        if 'agents' in data:
            agent_data = data['agents']
            if 'max_feedback_iterations' in agent_data:
                config.agents.max_feedback_iterations = agent_data['max_feedback_iterations']
            if 'agent_timeout' in agent_data:
                config.agents.agent_timeout = agent_data['agent_timeout']
        
        return config
    
    def save_config(self, config: SystemConfig, file_path: Optional[Path] = None) -> None:
        """Save configuration to file."""
        output_file = file_path or self.config_file
        
        # Convert config to dictionary
        config_dict = self._config_to_dict(config)
        
        try:
            with open(output_file, 'w') as f:
                if output_file.suffix.lower() == '.json':
                    json.dump(config_dict, f, indent=2)
                else:
                    yaml.dump(config_dict, f, default_flow_style=False, indent=2)
            
            self.logger.info(f"Configuration saved to {output_file}")
        
        except Exception as e:
            self.logger.error(f"Failed to save config to {output_file}: {e}")
            raise
    
    def _config_to_dict(self, config: SystemConfig) -> Dict[str, Any]:
        """Convert SystemConfig to dictionary."""
        return {
            'ollama': {
                'base_url': config.ollama.base_url,
                'timeout': config.ollama.timeout,
                'max_retries': config.ollama.max_retries,
                'cc_agent_1_model': config.ollama.cc_agent_1_model,
                'cc_agent_2_model': config.ollama.cc_agent_2_model,
                'ra_agent_model': config.ollama.ra_agent_model,
                'model_settings': config.ollama.model_settings
            },
            'vector_store': {
                'gdpr_docs_path': config.vector_store.gdpr_docs_path,
                'index_path': config.vector_store.index_path,
                'embedding_model': config.vector_store.embedding_model,
                'chunk_size': config.vector_store.chunk_size,
                'top_k_results': config.vector_store.top_k_results
            },
            'processing': {
                'supported_formats': config.processing.supported_formats,
                'max_file_size_mb': config.processing.max_file_size_mb,
                'temp_dir': config.processing.temp_dir,
                'output_dir': config.processing.output_dir
            },
            'agents': {
                'max_feedback_iterations': config.agents.max_feedback_iterations,
                'concurrent_cc_agents': config.agents.concurrent_cc_agents,
                'agent_timeout': config.agents.agent_timeout,
                'min_confidence_threshold': config.agents.min_confidence_threshold
            },
            'log_level': config.log_level,
            'log_file': config.log_file,
            'max_concurrent_analyses': config.max_concurrent_analyses
        }
    
    def get_config(self) -> SystemConfig:
        """Get the current configuration."""
        if self.config is None:
            self.config = self.load_config()
        return self.config
    
    def reload_config(self) -> SystemConfig:
        """Reload configuration from file."""
        self.config = None
        return self.load_config()