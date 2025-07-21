#!/usr/bin/env python3
"""
Main entry point for the HITL Report Editor application.
"""
import os
import sys
from pathlib import Path

# Add the backend directory to Python path
sys.path.insert(0, str(Path(__file__).parent / 'backend'))

from backend.app import create_app

def main():
    """Main application entry point."""
    # Set default environment
    os.environ.setdefault('FLASK_CONFIG', 'development')
    
    # Create and run the application
    app = create_app()
    
    # Get configuration from environment
    host = os.environ.get('FLASK_HOST', '0.0.0.0')
    port = int(os.environ.get('FLASK_PORT', 5000))
    debug = os.environ.get('FLASK_DEBUG', 'True').lower() == 'true'
    
    print(f"Starting HITL Report Editor on http://{host}:{port}")
    print(f"Debug mode: {debug}")
    
    app.run(host=host, port=port, debug=debug)

if __name__ == '__main__':
    main()