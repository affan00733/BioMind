#!/usr/bin/env python3
"""
Connector Management Script for BioMind Voice Lab
Allows you to easily enable/disable data source connectors.
"""

import os
import sys
from dotenv import load_dotenv

def load_env():
    """Load environment variables."""
    load_dotenv()
    return os.environ.copy()

def save_env(env_vars):
    """Save environment variables to .env file."""
    with open('.env', 'w') as f:
        for key, value in env_vars.items():
            f.write(f"{key}={value}\n")

def show_status():
    """Show current connector status."""
    env = load_env()
    
    print("🔌 BioMind Voice Lab - Connector Status")
    print("=" * 50)
    
    connectors = {
        "PubMed": env.get("ENABLE_PUBMED", "true"),
        "UniProt": env.get("ENABLE_UNIPROT", "true"),
        "DrugBank": env.get("ENABLE_DRUGBANK", "false"),
        "Google Health Blog": env.get("ENABLE_GOOGLE_HEALTH_BLOG", "false")
    }
    
    for name, status in connectors.items():
        status_icon = "🟢 ENABLED" if status.lower() == "true" else "🔴 DISABLED"
        print(f"{name:20} {status_icon}")

def toggle_connector(connector_name):
    """Toggle a connector on/off."""
    env = load_env()
    
    connector_map = {
        "pubmed": "ENABLE_PUBMED",
        "uniprot": "ENABLE_UNIPROT", 
        "drugbank": "ENABLE_DRUGBANK",
        "google": "ENABLE_GOOGLE_HEALTH_BLOG"
    }
    
    if connector_name.lower() not in connector_map:
        print(f"❌ Unknown connector: {connector_name}")
        print(f"Available connectors: {', '.join(connector_map.keys())}")
        return
    
    env_key = connector_map[connector_name.lower()]
    current_status = env.get(env_key, "true" if connector_name.lower() != "drugbank" else "false")
    new_status = "false" if current_status.lower() == "true" else "true"
    
    env[env_key] = new_status
    save_env(env)
    
    status_icon = "🟢 ENABLED" if new_status == "true" else "🔴 DISABLED"
    print(f"✅ {connector_name.title()} connector: {status_icon}")

def main():
    """Main function."""
    if len(sys.argv) < 2:
        show_status()
        print("\n💡 Usage:")
        print("  python manage_connectors.py status          # Show status")
        print("  python manage_connectors.py toggle pubmed   # Toggle PubMed")
        print("  python manage_connectors.py toggle uniprot  # Toggle UniProt")
        print("  python manage_connectors.py toggle drugbank # Toggle DrugBank")
        print("  python manage_connectors.py toggle google   # Toggle Google Health Blog")
        return
    
    command = sys.argv[1].lower()
    
    if command == "status":
        show_status()
    elif command == "toggle":
        if len(sys.argv) < 3:
            print("❌ Please specify which connector to toggle")
            return
        toggle_connector(sys.argv[2])
    else:
        print(f"❌ Unknown command: {command}")
        print("Available commands: status, toggle")

if __name__ == "__main__":
    main()
