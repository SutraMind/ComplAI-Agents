#!/usr/bin/env python3
"""
Verify that the HITL Report Editor setup is correct.
"""
import sys
import os
from pathlib import Path

def check_directory_structure():
    """Check that all required directories exist."""
    base_dir = Path(__file__).parent
    required_dirs = [
        'backend',
        'frontend',
        'frontend/static',
        'data',
        'tests'
    ]
    
    print("Checking directory structure...")
    for dir_path in required_dirs:
        full_path = base_dir / dir_path
        if full_path.exists():
            print(f"✓ {dir_path}")
        else:
            print(f"✗ {dir_path} - MISSING")
            return False
    return True

def check_required_files():
    """Check that all required files exist."""
    base_dir = Path(__file__).parent
    required_files = [
        'requirements.txt',
        'run.py',
        '.env.example',
        'backend/__init__.py',
        'backend/config.py',
        'backend/app.py',
        'backend/ollama_config.py',
        'frontend/static/index.html',
        'tests/__init__.py',
        'tests/test_config.py'
    ]
    
    print("\nChecking required files...")
    for file_path in required_files:
        full_path = base_dir / file_path
        if full_path.exists():
            print(f"✓ {file_path}")
        else:
            print(f"✗ {file_path} - MISSING")
            return False
    return True

def test_imports():
    """Test that key modules can be imported."""
    print("\nTesting imports...")
    
    # Add backend to path
    sys.path.insert(0, str(Path(__file__).parent / 'backend'))
    
    try:
        from backend.config import Config
        print("✓ Config import successful")
    except ImportError as e:
        print(f"✗ Config import failed: {e}")
        return False
    
    try:
        from backend.app import create_app
        print("✓ App import successful")
    except ImportError as e:
        print(f"✗ App import failed: {e}")
        return False
    
    try:
        from backend.ollama_config import OllamaConfig
        print("✓ OllamaConfig import successful")
    except ImportError as e:
        print(f"✗ OllamaConfig import failed: {e}")
        return False
    
    return True

def test_app_creation():
    """Test that Flask app can be created."""
    print("\nTesting app creation...")
    
    sys.path.insert(0, str(Path(__file__).parent / 'backend'))
    
    try:
        from backend.app import create_app
        app = create_app('development')
        print("✓ Flask app creation successful")
        return True
    except Exception as e:
        print(f"✗ Flask app creation failed: {e}")
        return False

def main():
    """Main verification function."""
    print("HITL Report Editor Setup Verification")
    print("=" * 40)
    
    checks = [
        check_directory_structure,
        check_required_files,
        test_imports,
        test_app_creation
    ]
    
    all_passed = True
    for check in checks:
        if not check():
            all_passed = False
    
    print("\n" + "=" * 40)
    if all_passed:
        print("✓ All setup checks passed!")
        print("\nNext steps:")
        print("1. Copy .env.example to .env and configure as needed")
        print("2. Install dependencies: pip install -r requirements.txt")
        print("3. Run the application: python run.py")
    else:
        print("✗ Some setup checks failed. Please fix the issues above.")
        sys.exit(1)

if __name__ == '__main__':
    main()