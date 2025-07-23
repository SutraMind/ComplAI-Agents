"""
Configuration settings for the HITL Report Editor application.
"""
import os
import logging
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
    FEEDBACK_DIR = DATA_DIR / 'feedback'
    LOGS_DIR = BASE_DIR / 'logs'
    
    # Ollama server configuration
    OLLAMA_URL = os.environ.get('OLLAMA_URL', 'http://localhost:11434')
    OLLAMA_MODEL = os.environ.get('OLLAMA_MODEL', 'gemma3:27b')
    OLLAMA_TIMEOUT = int(os.environ.get('OLLAMA_TIMEOUT', '30'))
    
    # File upload settings
    MAX_CONTENT_LENGTH = int(os.environ.get('MAX_CONTENT_LENGTH', 16 * 1024 * 1024))  # 16MB default
    ALLOWED_EXTENSIONS = {'txt', 'md'}
    
    # Session configuration
    PERMANENT_SESSION_LIFETIME = int(os.environ.get('SESSION_LIFETIME', 3600))  # 1 hour default
    
    # Security settings
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = None
    
    # JSON settings
    JSON_SORT_KEYS = False
    JSONIFY_PRETTYPRINT_REGULAR = True
    
    @staticmethod
    def init_app(app):
        """Initialize application with configuration."""
        # Create necessary directories
        directories = [
            Config.DATA_DIR,
            Config.REPORTS_DIR,
            Config.COMMENTS_DIR,
            Config.SUMMARIES_DIR,
            Config.FEEDBACK_DIR,
            Config.LOGS_DIR
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
        
        # Set up logging
        if not app.debug:
            # Production logging
            file_handler = logging.FileHandler(Config.LOGS_DIR / 'hitl.log')
            file_handler.setFormatter(logging.Formatter(
                '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
            ))
            file_handler.setLevel(logging.INFO)
            app.logger.addHandler(file_handler)
            app.logger.setLevel(logging.INFO)
            app.logger.info('HITL Report Editor startup')

class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True
    
    # Development-specific settings
    TESTING = False
    
    # More verbose logging in development
    LOG_LEVEL = logging.DEBUG
    
    # Disable CSRF for easier development
    WTF_CSRF_ENABLED = False
    
    @staticmethod
    def init_app(app):
        """Initialize development configuration."""
        Config.init_app(app)
        
        # Development-specific logging
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.DEBUG)
        console_handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        ))
        app.logger.addHandler(console_handler)
        app.logger.setLevel(logging.DEBUG)

class ProductionConfig(Config):
    """Production configuration."""
    DEBUG = False
    TESTING = False
    
    # Production-specific settings
    LOG_LEVEL = logging.WARNING
    
    # Enhanced security for production
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    
    # Require HTTPS in production
    PREFERRED_URL_SCHEME = 'https'
    
    @staticmethod
    def init_app(app):
        """Initialize production configuration."""
        Config.init_app(app)
        
        # Production-specific logging with rotation
        import logging.handlers
        
        # File handler with rotation
        file_handler = logging.handlers.RotatingFileHandler(
            Config.LOGS_DIR / 'hitl.log',
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=10
        )
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        ))
        file_handler.setLevel(logging.WARNING)
        app.logger.addHandler(file_handler)
        app.logger.setLevel(logging.WARNING)
        
        # Email handler for critical errors (if configured)
        mail_handler = None
        if os.environ.get('MAIL_SERVER'):
            mail_handler = logging.handlers.SMTPHandler(
                mailhost=os.environ.get('MAIL_SERVER'),
                fromaddr=os.environ.get('MAIL_FROM', 'noreply@hitl.local'),
                toaddrs=os.environ.get('MAIL_TO', '').split(','),
                subject='HITL Report Editor Error'
            )
            mail_handler.setLevel(logging.ERROR)
            app.logger.addHandler(mail_handler)

class TestingConfig(Config):
    """Testing configuration."""
    TESTING = True
    DEBUG = True
    
    # Use in-memory or temporary directories for testing
    import tempfile
    TEMP_DIR = Path(tempfile.mkdtemp())
    DATA_DIR = TEMP_DIR / 'data'
    REPORTS_DIR = DATA_DIR / 'reports'
    COMMENTS_DIR = DATA_DIR / 'comments'
    SUMMARIES_DIR = DATA_DIR / 'summaries'
    FEEDBACK_DIR = DATA_DIR / 'feedback'
    
    # Disable CSRF for testing
    WTF_CSRF_ENABLED = False
    
    # Use a test secret key
    SECRET_KEY = 'test-secret-key'

config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}