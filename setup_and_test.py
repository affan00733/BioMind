#!/usr/bin/env python3
"""
Complete setup and testing script for BioMind Voice Lab
"""

import os
import sys
import subprocess
import time

def check_python_version():
    """Check if Python version is compatible."""
    print("🐍 Checking Python version...")
    if sys.version_info < (3, 9):
        print("❌ Python 3.9+ required. Current version:", sys.version)
        return False
    print(f"✅ Python {sys.version_info.major}.{sys.version_info.minor} is compatible")
    return True

def check_virtual_environment():
    """Check if virtual environment is active."""
    print("\n🔧 Checking virtual environment...")
    if hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
        print("✅ Virtual environment is active")
        return True
    else:
        print("⚠️  Virtual environment not detected")
        print("💡 Run: python3 -m venv .venv && source .venv/bin/activate")
        return False

def install_dependencies():
    """Install required dependencies."""
    print("\n📦 Installing dependencies...")
    try:
        subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"], 
                      check=True, capture_output=True)
        print("✅ Dependencies installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install dependencies: {e}")
        return False

def check_gcp_auth():
    """Check Google Cloud authentication."""
    print("\n🔐 Checking Google Cloud authentication...")
    try:
        result = subprocess.run(["gcloud", "auth", "list"], 
                              capture_output=True, text=True)
        if "ACTIVE" in result.stdout:
            print("✅ Google Cloud authentication found")
            return True
        else:
            print("⚠️  No active Google Cloud authentication")
            print("💡 Run: gcloud auth application-default login")
            return False
    except FileNotFoundError:
        print("❌ gcloud CLI not found")
        print("💡 Install Google Cloud SDK first")
        return False

def test_imports():
    """Test if all required modules can be imported."""
    print("\n📚 Testing imports...")
    
    required_modules = [
        "google.cloud.bigquery",
        "google.cloud.aiplatform", 
        "google.generativeai",
        "Bio",
        "requests",
        "beautifulsoup4",
        "dotenv"
    ]
    
    failed_imports = []
    for module in required_modules:
        try:
            if module == "beautifulsoup4":
                import bs4
            elif module == "dotenv":
                from dotenv import load_dotenv
            else:
                __import__(module)
            print(f"✅ {module}")
        except ImportError:
            print(f"❌ {module}")
            failed_imports.append(module)
    
    return len(failed_imports) == 0

def test_configuration():
    """Test system configuration."""
    print("\n⚙️  Testing configuration...")
    
    # Check if .env file exists
    if os.path.exists(".env"):
        print("✅ .env file found")
    else:
        print("⚠️  .env file not found")
        print("💡 Copy env_template.txt to .env and configure")
    
    # Test configuration loading
    try:
        from utils.config_utils import get_config
        project_id = get_config('PROJECT_ID')
        print(f"✅ Project ID: {project_id}")
        return True
    except Exception as e:
        print(f"❌ Configuration error: {e}")
        return False

def run_basic_test():
    """Run a basic functionality test."""
    print("\n🧪 Running basic functionality test...")
    
    try:
        # Test coordinator import
        from agents.coordinator_agent import CoordinatorAgent
        print("✅ Coordinator agent imported")
        
        # Test retriever import
        from agents.retriever_agent import retrieve_relevant_docs
        print("✅ Retriever agent imported")
        
        # Test connector imports
        import connectors.pubmed.connector as pubmed_connector
        import connectors.uniprot.connector as uniprot_connector
        import connectors.drugbank.connector as drugbank_connector
        print("✅ All connectors imported")
        
        print("✅ Basic functionality test passed")
        return True
        
    except Exception as e:
        print(f"❌ Basic test failed: {e}")
        return False

def main():
    """Main setup and test function."""
    print("🧠 BioMind Voice Lab - Setup and Test")
    print("=" * 50)
    
    tests = [
        ("Python Version", check_python_version),
        ("Virtual Environment", check_virtual_environment),
        ("Dependencies", install_dependencies),
        ("Google Cloud Auth", check_gcp_auth),
        ("Imports", test_imports),
        ("Configuration", test_configuration),
        ("Basic Functionality", run_basic_test)
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} test crashed: {e}")
            results.append((test_name, False))
        
        time.sleep(0.5)  # Small delay between tests
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 TEST SUMMARY")
    print("=" * 50)
    
    passed = 0
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name:20} {status}")
        if result:
            passed += 1
    
    print(f"\n🎯 Overall: {passed}/{len(results)} tests passed")
    
    if passed == len(results):
        print("\n🎉 All tests passed! You can now run:")
        print("   python main.py")
    else:
        print("\n⚠️  Some tests failed. Please fix the issues above.")
        print("💡 Common solutions:")
        print("   - Install missing dependencies: pip install -r requirements.txt")
        print("   - Set up GCP auth: gcloud auth application-default login")
        print("   - Create .env file: cp env_template.txt .env")

if __name__ == "__main__":
    main()
