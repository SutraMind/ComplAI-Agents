#!/usr/bin/env python3
"""
Simple deployment script for the HITL Report Editor.
This script helps set up the application for production deployment.
"""
import os
import sys
import shutil
import subprocess
from pathlib import Path

def create_production_config():
    """Create a production configuration file."""
    env_prod = Path(__file__).parent / '.env.production'
    
    if env_prod.exists():
        print(f"✓ Production config already exists: {env_prod}")
        return
    
    prod_config = """# Production Configuration for HITL Report Editor
FLASK_CONFIG=production
FLASK_DEBUG=false
FLASK_HOST=0.0.0.0
FLASK_PORT=8000
SECRET_KEY=CHANGE-THIS-IN-PRODUCTION-TO-A-SECURE-RANDOM-STRING

# Ollama Configuration
OLLAMA_URL=http://localhost:11434
OLLAMA_MODEL=gemma2:27b
OLLAMA_TIMEOUT=30

# Application Settings
MAX_CONTENT_LENGTH=16777216
SESSION_LIFETIME=3600

# Security Settings
SESSION_COOKIE_SECURE=true
SESSION_COOKIE_HTTPONLY=true
PREFERRED_URL_SCHEME=https

# Email Settings (optional - for error notifications)
# MAIL_SERVER=smtp.yourcompany.com
# MAIL_FROM=noreply@yourcompany.com
# MAIL_TO=admin@yourcompany.com
"""
    
    env_prod.write_text(prod_config)
    print(f"✓ Created production config: {env_prod}")
    print("⚠️  Remember to update SECRET_KEY and other sensitive settings!")

def create_systemd_service():
    """Create a systemd service file for Linux deployment."""
    service_content = f"""[Unit]
Description=HITL Report Editor
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory={Path(__file__).parent.absolute()}
Environment=PATH={Path(__file__).parent.absolute()}
EnvironmentFile={Path(__file__).parent.absolute()}/.env.production
ExecStart=/usr/bin/python3 {Path(__file__).parent.absolute()}/run.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
"""
    
    service_file = Path(__file__).parent / 'hitl-report-editor.service'
    service_file.write_text(service_content)
    print(f"✓ Created systemd service file: {service_file}")
    print("To install: sudo cp hitl-report-editor.service /etc/systemd/system/")
    print("To enable: sudo systemctl enable hitl-report-editor")
    print("To start: sudo systemctl start hitl-report-editor")

def create_nginx_config():
    """Create an nginx configuration for reverse proxy."""
    nginx_config = f"""# Nginx configuration for HITL Report Editor
server {{
    listen 80;
    server_name your-domain.com;  # Change this to your domain
    
    # Redirect HTTP to HTTPS
    return 301 https://$server_name$request_uri;
}}

server {{
    listen 443 ssl http2;
    server_name your-domain.com;  # Change this to your domain
    
    # SSL configuration (update paths to your certificates)
    ssl_certificate /path/to/your/certificate.crt;
    ssl_certificate_key /path/to/your/private.key;
    
    # Security headers
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
    
    # Proxy to Flask application
    location / {{
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket support (if needed in future)
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }}
    
    # Static files (optional optimization)
    location /static/ {{
        alias {Path(__file__).parent.absolute()}/frontend/static/;
        expires 1h;
        add_header Cache-Control "public, immutable";
    }}
    
    # Security: deny access to sensitive files
    location ~ /\\.env {{
        deny all;
    }}
    
    location ~ /data/ {{
        deny all;
    }}
}}
"""
    
    nginx_file = Path(__file__).parent / 'nginx-hitl.conf'
    nginx_file.write_text(nginx_config)
    print(f"✓ Created nginx config: {nginx_file}")
    print("To install: sudo cp nginx-hitl.conf /etc/nginx/sites-available/")
    print("To enable: sudo ln -s /etc/nginx/sites-available/nginx-hitl.conf /etc/nginx/sites-enabled/")

def check_production_readiness():
    """Check if the application is ready for production deployment."""
    print("Checking production readiness...")
    
    issues = []
    
    # Check if requirements are installed
    try:
        import flask, requests
        print("✓ Required Python packages are installed")
    except ImportError as e:
        issues.append(f"Missing Python package: {e}")
    
    # Check if production config exists
    env_prod = Path(__file__).parent / '.env.production'
    if env_prod.exists():
        print("✓ Production configuration file exists")
        
        # Check for default secret key
        content = env_prod.read_text()
        if 'CHANGE-THIS-IN-PRODUCTION' in content:
            issues.append("SECRET_KEY still contains default value")
    else:
        issues.append("Production configuration file missing")
    
    # Check directory permissions
    data_dir = Path(__file__).parent / 'data'
    if data_dir.exists() and os.access(data_dir, os.W_OK):
        print("✓ Data directory is writable")
    else:
        issues.append("Data directory is not writable")
    
    # Check if Ollama is accessible (non-blocking)
    try:
        import requests
        ollama_url = os.environ.get('OLLAMA_URL', 'http://localhost:11434')
        response = requests.get(f"{ollama_url}/api/tags", timeout=5)
        if response.status_code == 200:
            print("✓ Ollama server is accessible")
        else:
            print("⚠️  Ollama server not accessible (LLM features will be disabled)")
    except:
        print("⚠️  Ollama server not accessible (LLM features will be disabled)")
    
    if issues:
        print("\n❌ Production readiness issues found:")
        for issue in issues:
            print(f"   - {issue}")
        return False
    else:
        print("\n✅ Application appears ready for production deployment")
        return True

def main():
    """Main deployment script."""
    import argparse
    
    parser = argparse.ArgumentParser(description='HITL Report Editor Deployment Script')
    parser.add_argument('--create-config', action='store_true', 
                       help='Create production configuration files')
    parser.add_argument('--create-systemd', action='store_true',
                       help='Create systemd service file')
    parser.add_argument('--create-nginx', action='store_true',
                       help='Create nginx configuration')
    parser.add_argument('--check', action='store_true',
                       help='Check production readiness')
    parser.add_argument('--all', action='store_true',
                       help='Create all deployment files')
    
    args = parser.parse_args()
    
    if not any(vars(args).values()):
        parser.print_help()
        return
    
    print("=" * 50)
    print("HITL Report Editor - Deployment Script")
    print("=" * 50)
    
    if args.create_config or args.all:
        create_production_config()
    
    if args.create_systemd or args.all:
        create_systemd_service()
    
    if args.create_nginx or args.all:
        create_nginx_config()
    
    if args.check or args.all:
        check_production_readiness()
    
    print("\n" + "=" * 50)
    print("Deployment script completed!")
    print("=" * 50)

if __name__ == '__main__':
    main()