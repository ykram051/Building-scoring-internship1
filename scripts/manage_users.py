"""
Script to add users to the system from the command line.
This is useful for initial setup or for adding users in batch.
"""

import argparse
import json
import hashlib
import os
from pathlib import Path

# Define path for user data storage
DATA_DIR = Path("data")
USERS_FILE = DATA_DIR / "users.json"

def hash_password(password):
    """Create SHA-256 hash of a password"""
    return hashlib.sha256(password.encode()).hexdigest()

def get_users_data():
    """Load users data from JSON file or create if not exists"""
    if not USERS_FILE.exists():
        # Create empty users dict if file doesn't exist
        users = {}
        # Ensure data directory exists
        DATA_DIR.mkdir(exist_ok=True)
        # Save empty users
        with open(USERS_FILE, "w") as f:
            json.dump(users, f)
    else:
        # Load existing users
        with open(USERS_FILE, "r") as f:
            users = json.load(f)
    
    return users

def add_user(username, password, role, name=None):
    """Add a user to the system"""
    users = get_users_data()
    
    if username in users:
        print(f"User '{username}' already exists")
        return False
    
    users[username] = {
        "password": hash_password(password),
        "role": role,
        "name": name or username
    }
    
    # Save updated users
    with open(USERS_FILE, "w") as f:
        json.dump(users, f)
    
    print(f"User '{username}' added successfully")
    return True

def list_users():
    """List all users in the system"""
    users = get_users_data()
    
    if not users:
        print("No users found")
        return
    
    print(f"{'Username':<20} {'Role':<10} {'Display Name':<20}")
    print("-" * 50)
    
    for username, user_data in users.items():
        print(f"{username:<20} {user_data.get('role', 'user'):<10} {user_data.get('name', ''):<20}")

def reset_password(username, new_password):
    """Reset a user's password"""
    users = get_users_data()
    
    if username not in users:
        print(f"User '{username}' not found")
        return False
    
    users[username]["password"] = hash_password(new_password)
    
    # Save updated users
    with open(USERS_FILE, "w") as f:
        json.dump(users, f)
    
    print(f"Password for user '{username}' reset successfully")
    return True

def delete_user(username):
    """Delete a user from the system"""
    users = get_users_data()
    
    if username not in users:
        print(f"User '{username}' not found")
        return False
    
    del users[username]
    
    # Save updated users
    with open(USERS_FILE, "w") as f:
        json.dump(users, f)
    
    print(f"User '{username}' deleted successfully")
    return True

def main():
    """Main function to handle command line arguments"""
    parser = argparse.ArgumentParser(description="User management script")
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")
    
    # Add user command
    add_parser = subparsers.add_parser("add", help="Add a new user")
    add_parser.add_argument("username", help="Username")
    add_parser.add_argument("password", help="Password")
    add_parser.add_argument("--role", help="User role", default="user", choices=["admin", "user", "analyst", "manager"])
    add_parser.add_argument("--name", help="Display name")
    
    # List users command
    list_parser = subparsers.add_parser("list", help="List all users")
    
    # Reset password command
    reset_parser = subparsers.add_parser("reset", help="Reset a user's password")
    reset_parser.add_argument("username", help="Username")
    reset_parser.add_argument("new_password", help="New password")
    
    # Delete user command
    delete_parser = subparsers.add_parser("delete", help="Delete a user")
    delete_parser.add_argument("username", help="Username")
    
    # Initialize command
    init_parser = subparsers.add_parser("init", help="Initialize the user system with default admin user")
    
    args = parser.parse_args()
    
    if args.command == "add":
        add_user(args.username, args.password, args.role, args.name)
    elif args.command == "list":
        list_users()
    elif args.command == "reset":
        reset_password(args.username, args.new_password)
    elif args.command == "delete":
        delete_user(args.username)
    elif args.command == "init":
        # Create default admin and user
        add_user("admin", "admin123", "admin", "Administrator")
        add_user("user", "user123", "user", "Regular User")
        add_user("analyst", "analyst123", "analyst", "Data Analyst")
        add_user("manager", "manager123", "manager", "Building Manager")
        print("User system initialized with default users")
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
