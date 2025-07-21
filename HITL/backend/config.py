"""
Configuration settings for the HITL Report Editor application.
"""
import os
from pathlib import Path

class Config:
    """Base configuration class."""
    
    # Flask configuration
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    DEBUG = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    
    # Application paths
    BASE_DIR = Path(__file__).parent.parent
    DATA_DIR = BASE_DIR / 'data'
    REPORTS_DIR = DATA_DIR / 'reports'
    COMMENTS_DIR = DATA_DIR / 'comments'
    SUMMARIES_DIR = DATA_DIR / 'summaries'
    
    # Ollama server configuration
    OLLAMA_URL = os.environ.get('OLLAMA_URL', 'http://localhost:11434')
    OLLAMA_MODEL = os.environ.get('OLLAMA_MODEL', 'gemma2:27b')
    
    # File upload settings
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    ALLOWED_EXTENSIONS = {'txt'}
    
    # Session configuration
    PERMANENT_SESSION_LIFETIME = 3600  # 1 hour
    
    @staticmethod
    def init_app(app):
        """Initialize application with configuration."""
        # Create necessary directories
        Config.DATA_DIR.mkdir(exist_ok=True)
        Config.REPORTS_DIR.mkdir(exist_ok=True)
        Config.COMMENTS_DIR.mkdir(exist_ok=True)
        Config.SUMMARIES_DIR.mkdir(exist_ok=True)

class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True

class ProductionConfig(Config):
    """Production configuration."""
    DEBUG = False

config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}