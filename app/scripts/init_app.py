"""
Initialize the Building Analytics Dashboard application.
This script sets up all necessary components for the application to run.
"""
import sys
import os
import argparse
import json
from pathlib import Path
import shutil

# Add the parent directory to the path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import required modules
from utils.auth_db import get_users_data, hash_password

def init_auth(reset=False):
    """Initialize the authentication system"""
    from scripts.manage_users import add_user
    
    # Path to users.json
    data_dir = Path("data")
    users_file = data_dir / "users.json"
    
    # Ensure data directory exists
    data_dir.mkdir(exist_ok=True)
    
    if reset and users_file.exists():
        # Backup existing file
        backup_path = users_file.with_suffix('.json.bak')
        shutil.copy(users_file, backup_path)
        print(f"Backed up existing users file to {backup_path}")
        
        # Remove existing file
        users_file.unlink()
        print(f"Removed existing users file")
    
    # Create default users
    print("Creating default users...")
    add_user("admin", "admin123", "admin", "Administrator")
    add_user("user", "user123", "user", "Regular User")
    add_user("analyst", "analyst123", "analyst", "Data Analyst")
    add_user("manager", "manager123", "manager", "Building Manager")
    
    print("Default users created successfully")

def init_app():
    """Initialize the application"""
    print("Initializing Building Analytics Dashboard...")
    
    # Create required directories
    dirs = ["data", "cache"]
    for d in dirs:
        Path(d).mkdir(exist_ok=True)
        print(f"Created directory: {d}")
    
    print("Application initialized successfully")
    print("\nTo run the application, use the following command:")
    print("streamlit run main.py")

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Initialize the Building Analytics Dashboard")
    parser.add_argument("--reset-auth", action="store_true", help="Reset authentication data")
    
    args = parser.parse_args()
    
    # Initialize the application
    init_app()
    
    # Initialize the authentication system
    init_auth(reset=args.reset_auth)
    
    print("\nInitialization complete")

if __name__ == "__main__":
    main()
