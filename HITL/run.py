#!/usr/bin/env python3
"""
Main entry point for the HITL Report Editor application.
This script initializes the application, sets up required directories,
and starts the Flask development server.
"""
import os
import sys
import logging
from pathlib import Path

# Add the backend directory to Python path
sys.path.insert(0, str(Path(__file__).parent / 'backend'))

from backend.app import create_app
from backend.config import Config

def setup_logging(debug=False):
    """Configure application logging."""
    log_level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('hitl.log')
        ]
    )

def initialize_directories():
    """Initialize required directories for the application."""
    directories = [
        Config.DATA_DIR,
        Config.REPORTS_DIR,
        Config.COMMENTS_DIR,
        Config.SUMMARIES_DIR,
        Path(__file__).parent / 'logs'
    ]
    
    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)
        print(f"✓ Directory initialized: {directory}")

def load_environment():
    """Load environment variables from .env file if it exists."""
    env_file = Path(__file__).parent / '.env'
    if env_file.exists():
        print(f"Loading environment from {env_file}")
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ.setdefault(key.strip(), value.strip())

def main():
    """Main application entry point."""
    print("=" * 50)
    print("HITL Report Editor - Starting Application")
    print("=" * 50)
    
    # Load environment variables
    load_environment()
    
    # Set default environment
    config_name = os.environ.get('FLASK_CONFIG', 'development')
    os.environ.setdefault('FLASK_CONFIG', config_name)
    
    # Initialize directories
    print("\nInitializing application directories...")
    initialize_directories()
    
    # Setup logging
    debug = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    setup_logging(debug)
    
    # Create and configure the application
    print(f"\nCreating Flask application (config: {config_name})...")
    app = create_app(config_name)
    
    # Get server configuration from environment
    host = os.environ.get('FLASK_HOST', '0.0.0.0')
    port = int(os.environ.get('FLASK_PORT', 5000))
    
    print(f"\nApplication Configuration:")
    print(f"  Environment: {config_name}")
    print(f"  Debug mode: {debug}")
    print(f"  Host: {host}")
    print(f"  Port: {port}")
    print(f"  Data directory: {Config.DATA_DIR}")
    print(f"  Ollama URL: {os.environ.get('OLLAMA_URL', 'http://localhost:11434')}")
    
    print(f"\n🚀 Starting HITL Report Editor on http://{host}:{port}")
    print("Press Ctrl+C to stop the server")
    print("=" * 50)
    
    try:
        app.run(host=host, port=port, debug=debug, use_reloader=debug)
    except KeyboardInterrupt:
        print("\n\n👋 HITL Report Editor stopped by user")
    except Exception as e:
        print(f"\n❌ Error starting application: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()