"""
Main Flask application for the HITL Report Editor.
"""
import os
from flask import Flask, render_template, send_from_directory
from .config import config

def create_app(config_name=None):
    """Application factory pattern for creating Flask app."""
    if config_name is None:
        config_name = os.environ.get('FLASK_CONFIG', 'default')
    
    app = Flask(__name__, 
                static_folder='../frontend/static',
                template_folder='../frontend/templates')
    
    # Load configuration
    app.config.from_object(config[config_name])
    config[config_name].init_app(app)
    
    # Register blueprints
    from .api import api_bp
    app.register_blueprint(api_bp, url_prefix='/api')
    
    # Main route to serve the frontend
    @app.route('/')
    def index():
        """Serve the main application page."""
        return send_from_directory(app.static_folder, 'index.html')
    
    # Serve static files
    @app.route('/static/<path:filename>')
    def static_files(filename):
        """Serve static files."""
        return send_from_directory(app.static_folder, filename)
    
    # Health check endpoint
    @app.route('/health')
    def health_check():
        """Health check endpoint."""
        return {'status': 'healthy', 'service': 'HITL Report Editor'}
    
    return app

# Create app instance for development
app = create_app()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)