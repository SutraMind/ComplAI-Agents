#!/usr/bin/env python3
"""
Startup script for the HITL Report Editor application.
This script provides additional initialization and management capabilities.
"""
import os
import sys
import argparse
import subprocess
from pathlib import Path

def check_dependencies():
    """Check if required dependencies are installed."""
    print("Checking dependencies...")
    
    try:
        import flask
        print(f"✓ Flask {flask.__version__}")
    except ImportError:
        print("❌ Flask not found. Please install requirements: pip install -r requirements.txt")
        return False
    
    try:
        import requests
        print(f"✓ Requests {requests.__version__}")
    except ImportError:
        print("❌ Requests not found. Please install requirements: pip install -r requirements.txt")
        return False
    
    return True

def check_ollama_server():
    """Check if Ollama server is accessible."""
    import requests
    
    ollama_url = os.environ.get('OLLAMA_URL', 'http://localhost:11434')
    print(f"Checking Ollama server at {ollama_url}...")
    
    try:
        response = requests.get(f"{ollama_url}/api/tags", timeout=5)
        if response.status_code == 200:
            print("✓ Ollama server is accessible")
            return True
        else:
            print(f"⚠️  Ollama server responded with status {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"⚠️  Ollama server not accessible: {e}")
        print("   The application will work without LLM features")
        return False

def setup_sample_data():
    """Set up sample data for testing."""
    print("Setting up sample data...")
    
    # Create sample report
    reports_dir = Path(__file__).parent / 'data' / 'reports'
    reports_dir.mkdir(parents=True, exist_ok=True)
    
    sample_report = reports_dir / 'sample_report.txt'
    if not sample_report.exists():
        sample_content = """Sample Compliance Report

Executive Summary
This report provides an analysis of the current compliance status of our e-commerce platform.

Key Findings
1. Data Protection: The system implements GDPR-compliant data handling procedures.
2. Security Measures: Multi-factor authentication is properly configured.
3. User Privacy: Cookie consent mechanisms are in place and functioning.

Recommendations
- Implement additional logging for audit trails
- Review data retention policies quarterly
- Enhance user notification systems

Conclusion
Overall compliance status is satisfactory with minor improvements needed.
"""
        sample_report.write_text(sample_content)
        print(f"✓ Created sample report: {sample_report}")
    else:
        print(f"✓ Sample report already exists: {sample_report}")

def run_tests():
    """Run the test suite."""
    print("Running tests...")
    test_dir = Path(__file__).parent / 'tests'
    
    if not test_dir.exists():
        print("❌ Tests directory not found")
        return False
    
    try:
        result = subprocess.run([
            sys.executable, '-m', 'pytest', str(test_dir), '-v'
        ], cwd=Path(__file__).parent)
        return result.returncode == 0
    except FileNotFoundError:
        print("❌ pytest not found. Install with: pip install pytest")
        return False

def main():
    """Main startup script."""
    parser = argparse.ArgumentParser(description='HITL Report Editor Startup Script')
    parser.add_argument('--config', choices=['development', 'production'], 
                       default='development', help='Configuration environment')
    parser.add_argument('--host', default='0.0.0.0', help='Host to bind to')
    parser.add_argument('--port', type=int, default=5000, help='Port to bind to')
    parser.add_argument('--no-check', action='store_true', help='Skip dependency checks')
    parser.add_argument('--setup-data', action='store_true', help='Set up sample data')
    parser.add_argument('--test', action='store_true', help='Run tests instead of starting server')
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("HITL Report Editor - Startup Script")
    print("=" * 60)
    
    # Set environment variables
    os.environ['FLASK_CONFIG'] = args.config
    os.environ['FLASK_HOST'] = args.host
    os.environ['FLASK_PORT'] = str(args.port)
    
    if not args.no_check:
        # Check dependencies
        if not check_dependencies():
            sys.exit(1)
        
        # Check Ollama server (non-blocking)
        check_ollama_server()
    
    # Set up sample data if requested
    if args.setup_data:
        setup_sample_data()
    
    # Run tests if requested
    if args.test:
        success = run_tests()
        sys.exit(0 if success else 1)
    
    print(f"\nStarting application with configuration: {args.config}")
    print(f"Server will be available at: http://{args.host}:{args.port}")
    print("=" * 60)
    
    # Import and run the main application
    try:
        from run import main as run_main
        run_main()
    except KeyboardInterrupt:
        print("\n\n👋 Application stopped by user")
    except Exception as e:
        print(f"\n❌ Error starting application: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()