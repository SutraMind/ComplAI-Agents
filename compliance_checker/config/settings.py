"""
Configuration settings for the multi-agent compliance checker system.
"""

import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from pathlib import Path


@dataclass
class OllamaConfig:
    """Configuration for Ollama service."""
    base_url: str = "http://localhost:11434"
    timeout: int = 30
    max_retries: int = 3
    retry_delay: float = 1.0
    retry_backoff_factor: float = 2.0
    
    # Model configurations
    cc_agent_1_model: str = "deepseek-r1:8b"
    cc_agent_2_model: str = "Gemma3:27b"
    ra_agent_model: str = "qwq:32b"
    
    # Model-specific settings
    model_settings: Dict[str, Dict[str, Any]] = field(default_factory=lambda: {
        "deepseek-r1:8b": {
            "temperature": 0.1,
            "top_p": 0.9,
            "max_tokens": 4096
        },
        "Gemma3:27b": {
            "temperature": 0.2,
            "top_p": 0.85,
            "max_tokens": 4096
        },
        "qwq:32b": {
            "temperature": 0.1,
            "top_p": 0.9,
            "max_tokens": 8192
        }
    })


@dataclass
class VectorStoreConfig:
    """Configuration for FAISS vector store."""
    gdpr_docs_path: str = "GDPR_docs"
    index_path: str = "gdpr_index"
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    chunk_size: int = 512
    chunk_overlap: int = 50
    top_k_results: int = 5
    similarity_threshold: float = 0.7


@dataclass
class ProcessingConfig:
    """Configuration for document processing."""
    supported_formats: List[str] = field(default_factory=lambda: [
        ".pdf", ".doc", ".docx", ".txt"
    ])
    max_file_size_mb: int = 50
    temp_dir: str = "temp"
    output_dir: str = "output"
    
    # Chain-of-thought settings
    max_reasoning_steps: int = 10
    reasoning_temperature: float = 0.1


@dataclass
class AgentConfig:
    """Configuration for agent behavior."""
    max_feedback_iterations: int = 3
    concurrent_cc_agents: bool = True
    agent_timeout: int = 300  # 5 minutes
    
    # Confidence thresholds
    min_confidence_threshold: float = 0.6
    high_confidence_threshold: float = 0.8
    
    # Report settings
    max_findings_per_report: int = 100
    include_reasoning_in_report: bool = True


@dataclass
class SystemConfig:
    """Main system configuration."""
    ollama: OllamaConfig = field(default_factory=OllamaConfig)
    vector_store: VectorStoreConfig = field(default_factory=VectorStoreConfig)
    processing: ProcessingConfig = field(default_factory=ProcessingConfig)
    agents: AgentConfig = field(default_factory=AgentConfig)
    
    # Logging configuration
    log_level: str = "INFO"
    log_file: Optional[str] = "compliance_checker.log"
    
    # Security settings
    enable_input_validation: bool = True
    max_concurrent_analyses: int = 5
    
    @classmethod
    def from_env(cls) -> 'SystemConfig':
        """Create configuration from environment variables."""
        config = cls()
        
        # Ollama configuration from environment
        if os.getenv('OLLAMA_BASE_URL'):
            config.ollama.base_url = os.getenv('OLLAMA_BASE_URL')
        if os.getenv('OLLAMA_TIMEOUT'):
            config.ollama.timeout = int(os.getenv('OLLAMA_TIMEOUT'))
        if os.getenv('CC_AGENT_1_MODEL'):
            config.ollama.cc_agent_1_model = os.getenv('CC_AGENT_1_MODEL')
        if os.getenv('CC_AGENT_2_MODEL'):
            config.ollama.cc_agent_2_model = os.getenv('CC_AGENT_2_MODEL')
        if os.getenv('RA_AGENT_MODEL'):
            config.ollama.ra_agent_model = os.getenv('RA_AGENT_MODEL')
        
        # Vector store configuration from environment
        if os.getenv('GDPR_DOCS_PATH'):
            config.vector_store.gdpr_docs_path = os.getenv('GDPR_DOCS_PATH')
        if os.getenv('VECTOR_INDEX_PATH'):
            config.vector_store.index_path = os.getenv('VECTOR_INDEX_PATH')
        
        # Processing configuration from environment
        if os.getenv('MAX_FILE_SIZE_MB'):
            config.processing.max_file_size_mb = int(os.getenv('MAX_FILE_SIZE_MB'))
        if os.getenv('TEMP_DIR'):
            config.processing.temp_dir = os.getenv('TEMP_DIR')
        if os.getenv('OUTPUT_DIR'):
            config.processing.output_dir = os.getenv('OUTPUT_DIR')
        
        # Agent configuration from environment
        if os.getenv('MAX_FEEDBACK_ITERATIONS'):
            config.agents.max_feedback_iterations = int(os.getenv('MAX_FEEDBACK_ITERATIONS'))
        if os.getenv('AGENT_TIMEOUT'):
            config.agents.agent_timeout = int(os.getenv('AGENT_TIMEOUT'))
        
        # System configuration from environment
        if os.getenv('LOG_LEVEL'):
            config.log_level = os.getenv('LOG_LEVEL')
        if os.getenv('LOG_FILE'):
            config.log_file = os.getenv('LOG_FILE')
        if os.getenv('MAX_CONCURRENT_ANALYSES'):
            config.max_concurrent_analyses = int(os.getenv('MAX_CONCURRENT_ANALYSES'))
        
        return config
    
    def validate(self) -> List[str]:
        """Validate configuration and return list of errors."""
        errors = []
        
        # Validate paths
        if not Path(self.vector_store.gdpr_docs_path).exists():
            errors.append(f"GDPR docs path does not exist: {self.vector_store.gdpr_docs_path}")
        
        # Validate numeric values
        if self.ollama.timeout <= 0:
            errors.append("Ollama timeout must be positive")
        if self.agents.max_feedback_iterations < 1:
            errors.append("Max feedback iterations must be at least 1")
        if self.processing.max_file_size_mb <= 0:
            errors.append("Max file size must be positive")
        
        # Validate model names
        required_models = [
            self.ollama.cc_agent_1_model,
            self.ollama.cc_agent_2_model,
            self.ollama.ra_agent_model
        ]
        if len(set(required_models)) != 3:
            errors.append("All agent models must be different")
        
        return errors
    
    def create_directories(self) -> None:
        """Create necessary directories if they don't exist."""
        directories = [
            self.processing.temp_dir,
            self.processing.output_dir,
            self.vector_store.index_path
        ]
        
        for directory in directories:
            Path(directory).mkdir(parents=True, exist_ok=True)