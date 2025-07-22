"""
Main Flask application for the HITL Report Editor.
"""
import os
import logging
from pathlib import Path
from flask import Flask, send_from_directory, jsonify, request
from werkzeug.exceptions import NotFound
from .config import config

def create_app(config_name=None):
    """Application factory pattern for creating Flask app."""
    if config_name is None:
        config_name = os.environ.get('FLASK_CONFIG', 'default')
    
    # Determine paths for static and template folders
    app_root = Path(__file__).parent.parent
    
    # Check if React build exists, otherwise use static folder
    react_build = app_root / 'frontend' / 'build'
    static_folder = react_build / 'static' if react_build.exists() else app_root / 'frontend' / 'static'
    
    app = Flask(__name__, 
                static_folder=str(static_folder),
                static_url_path='/static')
    
    # Load configuration
    app.config.from_object(config[config_name])
    config[config_name].init_app(app)
    
    # Configure logging
    if not app.debug:
        logging.basicConfig(level=logging.INFO)
    
    # Register blueprints
    from .api import api_bp
    app.register_blueprint(api_bp, url_prefix='/api')
    
    # Main route to serve the frontend
    @app.route('/')
    def index():
        """Serve the main application page."""
        try:
            # Check if React build exists
            react_build = app_root / 'frontend' / 'build'
            if react_build.exists() and (react_build / 'index.html').exists():
                return send_from_directory(str(react_build), 'index.html')
            else:
                # Fallback to development HTML
                dev_html = app_root / 'frontend' / 'dev.html'
                if dev_html.exists():
                    return send_from_directory(str(app_root / 'frontend'), 'dev.html')
                else:
                    # Try clean static interface (without text highlighting issues)
                    clean_index = Path(app.static_folder) / 'clean-index.html'
                    if clean_index.exists():
                        return send_from_directory(app.static_folder, 'clean-index.html')
                    else:
                        # Try modern static interface
                        modern_index = Path(app.static_folder) / 'modern-index.html'
                        if modern_index.exists():
                            return send_from_directory(app.static_folder, 'modern-index.html')
                        else:
                            # Final fallback to basic static folder
                            static_index = Path(app.static_folder) / 'index.html'
                        if static_index.exists():
                            return send_from_directory(app.static_folder, 'index.html')
                        else:
                            # Return helpful error message
                            return jsonify({
                                'error': 'Frontend not found',
                                'message': 'No frontend files found. Please build the React app using: python build-frontend.py',
                                'help': {
                                    'step1': 'Install Node.js from https://nodejs.org/',
                                    'step2': 'Run: python build-frontend.py',
                                    'step3': 'Restart the server'
                                },
                                'api_available': True,
                                'api_endpoints': ['/api/reports', '/health']
                            }), 404
        except Exception as e:
            app.logger.error(f'Error serving frontend: {e}')
            return jsonify({
                'error': 'Frontend error',
                'message': str(e)
            }), 500
    
    # Serve static files with proper MIME types
    @app.route('/static/<path:filename>')
    def static_files(filename):
        """Serve static files with proper headers."""
        try:
            response = send_from_directory(app.static_folder, filename)
            
            # Set appropriate cache headers for static assets
            if filename.endswith(('.css', '.js', '.png', '.jpg', '.jpeg', '.gif', '.ico')):
                response.cache_control.max_age = 3600  # 1 hour cache for static assets
            
            return response
        except NotFound:
            return jsonify({
                'error': 'File not found',
                'message': f'Static file {filename} not found'
            }), 404
    
    # Health check endpoint
    @app.route('/health')
    def health_check():
        """Health check endpoint with system information."""
        return jsonify({
            'status': 'healthy',
            'service': 'HITL Report Editor',
            'version': '1.0.0',
            'config': config_name,
            'debug': app.debug,
            'static_folder': app.static_folder
        })
    
    # Error handlers
    @app.errorhandler(404)
    def not_found(error):
        """Handle 404 errors."""
        if request.path.startswith('/api/'):
            return jsonify({
                'error': 'API endpoint not found',
                'message': f'The requested API endpoint {request.path} does not exist'
            }), 404
        else:
            # For non-API routes, serve the main app (SPA behavior)
            return index()
    
    @app.errorhandler(500)
    def internal_error(error):
        """Handle 500 errors."""
        app.logger.error(f'Internal server error: {error}')
        return jsonify({
            'error': 'Internal server error',
            'message': 'An unexpected error occurred. Please try again later.'
        }), 500
    
    # Request logging middleware
    @app.before_request
    def log_request_info():
        """Log request information in debug mode."""
        if app.debug:
            app.logger.debug(f'{request.method} {request.url} - {request.remote_addr}')
    
    return app

# Create app instance for development
app = create_app()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)