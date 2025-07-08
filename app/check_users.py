"""
Script to check all users in the database.
This helps diagnose authentication issues.
"""

import os
import sys
from pathlib import Path
import psycopg2
import pandas as pd

def check_db_users():
    """Check all users in the database."""
    # Get database configuration from environment variables
    db_host = os.environ.get("DB_HOST", "localhost")
    db_port = os.environ.get("DB_PORT", "5432")
    db_name = os.environ.get("DB_NAME", "building_analytics")
    db_user = os.environ.get("DB_USER", "postgres")
    db_password = os.environ.get("DB_PASSWORD", "root")
    
    print(f"Connecting to PostgreSQL database: {db_name}")
    print(f"Host: {db_host}, Port: {db_port}")
    
    try:
        # Connect to the database
        conn = psycopg2.connect(
            host=db_host,
            port=db_port,
            dbname=db_name,
            user=db_user,
            password=db_password
        )
        
        # Create a cursor
        cur = conn.cursor()
        
        # Query to get all users
        cur.execute("SELECT username, role, name, password FROM users ORDER BY role, username")
        
        # Fetch all rows
        rows = cur.fetchall()
        
        if not rows:
            print("No users found in the database!")
            return
        
        # Print table header
        print("\nUsers in the database:")
        print("-" * 80)
        print(f"{'Username':<15} | {'Role':<10} | {'Name':<25} | {'Password Hash (first 15 chars)':<15}")
        print("-" * 80)
        
        # Print all users
        for row in rows:
            username, role, name, password = row
            # Only show the first 15 characters of the password hash for security
            password_preview = password[:15] + "..." if password else "None"
            print(f"{username:<15} | {role:<10} | {name:<25} | {password_preview:<15}")
        
        # Close cursor and connection
        cur.close()
        conn.close()
        
        print("\nDone!")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_db_users()
