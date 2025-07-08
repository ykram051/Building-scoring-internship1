"""
Script to add standard users to the database.
Run this script to ensure all required users exist.
"""

import os
import sys
import hashlib
from pathlib import Path
import psycopg2

def add_standard_users():
    """Add the standard set of users to the database."""
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
        
        # Define standard users
        standard_users = [
            {
                "username": "user",
                "password": "user123",
                "name": "Regular User",
                "role": "user"
            },
            {
                "username": "analyst",
                "password": "analyst123",
                "name": "Data Analyst",
                "role": "analyst"
            },
            {
                "username": "manager",
                "password": "manager123",
                "name": "Building Manager", 
                "role": "manager"
            }
        ]
        
        # Check and add each user
        for user in standard_users:
            # Check if user exists
            cur.execute("SELECT 1 FROM users WHERE username = %s", (user["username"],))
            exists = cur.fetchone()
            
            if not exists:
                # Hash password
                hashed_password = hashlib.sha256(user["password"].encode()).hexdigest()
                
                # Insert user
                cur.execute("""
                INSERT INTO users (username, password, name, role)
                VALUES (%s, %s, %s, %s)
                """, (
                    user["username"],
                    hashed_password,
                    user["name"],
                    user["role"]
                ))
                
                print(f"Added user: {user['username']} with role: {user['role']}")
            else:
                print(f"User {user['username']} already exists.")
        
        # Commit changes
        conn.commit()
        
        # Close cursor and connection
        cur.close()
        conn.close()
        
        print("\nDone! All standard users have been added.")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    add_standard_users()
