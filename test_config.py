#!/usr/bin/env python3
"""
Test script to verify all configurations are set correctly.
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_config():
    """Test all configuration values."""
    print("🔍 Testing BioMind Voice Lab Configuration")
    print("=" * 50)
    
    # Test GCP Configuration
    gcp_project = os.getenv("GCP_PROJECT_ID", "trusty-frame-474816-m0")
    print(f"✅ GCP Project ID: {gcp_project}")
    
    bigquery_dataset = os.getenv("BIGQUERY_DATASET", "biomind_data")
    print(f"✅ BigQuery Dataset: {bigquery_dataset}")
    
    # Test Connector Flags
    print("\n🔌 Connector Status:")
    enable_pubmed = os.getenv("ENABLE_PUBMED", "true").lower() == "true"
    enable_uniprot = os.getenv("ENABLE_UNIPROT", "true").lower() == "true"
    enable_drugbank = os.getenv("ENABLE_DRUGBANK", "false").lower() == "true"
    enable_google_health = os.getenv("ENABLE_GOOGLE_HEALTH_BLOG", "false").lower() == "true"
    
    print(f"📚 PubMed: {'🟢 ENABLED' if enable_pubmed else '🔴 DISABLED'}")
    print(f"🧬 UniProt: {'🟢 ENABLED' if enable_uniprot else '🔴 DISABLED'}")
    print(f"💊 DrugBank: {'🟢 ENABLED' if enable_drugbank else '🔴 DISABLED'}")
    print(f"🏥 Google Health Blog: {'🟢 ENABLED' if enable_google_health else '🔴 DISABLED'}")
    
    # Test API Keys
    print("\n🔑 API Configuration:")
    pubmed_email = os.getenv("PUBMED_EMAIL", "")
    if pubmed_email and pubmed_email != "your-email@example.com":
        print(f"✅ PubMed Email: {pubmed_email}")
    else:
        print("⚠️  PubMed Email: Not set (using default)")
    
    drugbank_key = os.getenv("DRUGBANK_API_KEY", "")
    if drugbank_key:
        print(f"✅ DrugBank API Key: {'*' * (len(drugbank_key) - 4) + drugbank_key[-4:]}")
    else:
        print("⚠️  DrugBank API Key: Not set (will use mock data)")
    
    # Test Google Cloud Authentication
    google_creds = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "")
    if google_creds:
        print(f"✅ Google Credentials: {google_creds}")
    else:
        print("⚠️  Google Credentials: Not set in env (may use gcloud auth)")
    
    print("\n" + "=" * 50)
    print("🎯 Configuration Test Complete!")
    print("\n💡 Tips:")
    print("- Set ENABLE_DRUGBANK=false if you don't have DrugBank API access")
    print("- PubMed email can be any valid email")
    print("- DrugBank API key is optional (mock data will be used if not set)")
    print("- Run 'gcloud auth application-default login' for Google Cloud auth")
    print("- Use environment variables to enable/disable connectors")

if __name__ == "__main__":
    test_config()
