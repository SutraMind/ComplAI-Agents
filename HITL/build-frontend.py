#!/usr/bin/env python3
"""
Build script for the React frontend of HITL Report Editor.
This script builds the React app and sets up the Flask app to serve it.
"""
import os
import sys
import subprocess
import shutil
from pathlib import Path

def run_command(command, cwd=None):
    """Run a shell command and return the result."""
    try:
        result = subprocess.run(
            command,
            shell=True,
            cwd=cwd,
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"Error running command: {command}")
        print(f"Error output: {e.stderr}")
        return None

def check_node_npm():
    """Check if Node.js and npm are installed."""
    print("Checking Node.js and npm...")
    
    node_version = run_command("node --version")
    if not node_version:
        print("❌ Node.js is not installed. Please install Node.js from https://nodejs.org/")
        return False
    
    npm_version = run_command("npm --version")
    if not npm_version:
        print("❌ npm is not installed. Please install npm.")
        return False
    
    print(f"✓ Node.js {node_version}")
    print(f"✓ npm {npm_version}")
    return True

def install_dependencies():
    """Install npm dependencies."""
    frontend_dir = Path(__file__).parent / 'frontend'
    
    print("Installing npm dependencies...")
    result = run_command("npm install", cwd=frontend_dir)
    
    if result is None:
        print("❌ Failed to install dependencies")
        return False
    
    print("✓ Dependencies installed successfully")
    return True

def build_react_app():
    """Build the React application."""
    frontend_dir = Path(__file__).parent / 'frontend'
    
    print("Building React application...")
    result = run_command("npm run build", cwd=frontend_dir)
    
    if result is None:
        print("❌ Failed to build React app")
        return False
    
    print("✓ React app built successfully")
    return True

def setup_flask_static():
    """Set up Flask to serve the built React app."""
    frontend_dir = Path(__file__).parent / 'frontend'
    build_dir = frontend_dir / 'build'
    static_dir = frontend_dir / 'static'
    
    if not build_dir.exists():
        print("❌ Build directory not found. React build may have failed.")
        return False
    
    # Create static directory if it doesn't exist
    static_dir.mkdir(exist_ok=True)
    
    # Copy built files to static directory
    print("Setting up Flask static files...")
    
    # Copy index.html
    if (build_dir / 'index.html').exists():
        shutil.copy2(build_dir / 'index.html', static_dir / 'index.html')
        print("✓ Copied index.html")
    
    # Copy static assets
    build_static = build_dir / 'static'
    if build_static.exists():
        # Remove old static files
        for item in static_dir.glob('static/*'):
            if item.is_file():
                item.unlink()
            elif item.is_dir():
                shutil.rmtree(item)
        
        # Copy new static files
        target_static = static_dir / 'static'
        if target_static.exists():
            shutil.rmtree(target_static)
        shutil.copytree(build_static, target_static)
        print("✓ Copied static assets")
    
    print("✓ Flask static files set up successfully")
    return True

def create_dev_html():
    """Create a development HTML file that works without building."""
    frontend_dir = Path(__file__).parent / 'frontend'
    dev_html = frontend_dir / 'dev.html'
    
    dev_content = '''<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>HITL Report Editor - Development</title>
    <style>
      body {
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Oxygen', 'Ubuntu', 'Cantarell', sans-serif;
        margin: 0;
        padding: 20px;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        min-height: 100vh;
        display: flex;
        align-items: center;
        justify-content: center;
      }
      .container {
        background: white;
        padding: 40px;
        border-radius: 20px;
        box-shadow: 0 20px 40px rgba(0,0,0,0.1);
        text-align: center;
        max-width: 600px;
      }
      h1 {
        color: #2563eb;
        margin-bottom: 20px;
      }
      .status {
        background: #fef3c7;
        border: 1px solid #f59e0b;
        border-radius: 8px;
        padding: 20px;
        margin: 20px 0;
      }
      .button {
        background: linear-gradient(135deg, #2563eb 0%, #3b82f6 100%);
        color: white;
        padding: 12px 24px;
        border: none;
        border-radius: 8px;
        font-size: 16px;
        cursor: pointer;
        text-decoration: none;
        display: inline-block;
        margin: 10px;
      }
      .button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(37, 99, 235, 0.3);
      }
    </style>
  </head>
  <body>
    <div class="container">
      <h1>🚀 HITL Report Editor</h1>
      <div class="status">
        <h3>Development Mode</h3>
        <p>The React frontend is not built yet. To use the full modern interface:</p>
        <ol style="text-align: left; display: inline-block;">
          <li>Install Node.js from <a href="https://nodejs.org/" target="_blank">nodejs.org</a></li>
          <li>Run: <code>python build-frontend.py</code></li>
          <li>Restart the server</li>
        </ol>
      </div>
      <a href="/api/reports" class="button">Test API</a>
      <a href="/health" class="button">Health Check</a>
      <p style="margin-top: 30px; color: #666;">
        <small>Backend is running successfully! 🎉</small>
      </p>
    </div>
  </body>
</html>'''
    
    dev_html.write_text(dev_content, encoding='utf-8')
    print("✓ Created development HTML file")

def main():
    """Main build process."""
    print("=" * 60)
    print("HITL Report Editor - Frontend Build Script")
    print("=" * 60)
    
    # Create development HTML regardless
    create_dev_html()
    
    # Check if Node.js and npm are available
    if not check_node_npm():
        print("\n⚠️  Node.js/npm not found. Created development HTML instead.")
        print("Install Node.js to build the full React frontend.")
        return
    
    # Install dependencies
    if not install_dependencies():
        print("\n❌ Build failed at dependency installation")
        return
    
    # Build React app
    if not build_react_app():
        print("\n❌ Build failed at React build step")
        return
    
    # Set up Flask static files
    if not setup_flask_static():
        print("\n❌ Build failed at Flask setup step")
        return
    
    print("\n" + "=" * 60)
    print("✅ Frontend build completed successfully!")
    print("=" * 60)
    print("The React frontend has been built and is ready to use.")
    print("Restart your Flask server to see the new interface.")
    print("=" * 60)

if __name__ == '__main__':
    main()