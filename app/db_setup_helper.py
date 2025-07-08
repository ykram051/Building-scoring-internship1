"""
Special database setup script for Building Analytics Dashboard.
This script creates a PostgreSQL database with explicit debugging information.
"""

import os
import sys
import logging
from pathlib import Path
import psycopg2

# Setup logging
logging.basicConfig(level=logging.DEBUG,
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Base directory
BASE_DIR = Path(__file__).resolve().parent

# Database configuration
DB_CONFIG = {
    "host": "localhost",
    "port": "5432",
    "database": "building_analytics",
    "user": "postgres",
    "password": "postgres"
}

def create_clean_database():
    """Create a clean PostgreSQL database."""
    try:
        # First try connecting to the default postgres database
        print(f"Connecting to PostgreSQL server with user: {DB_CONFIG['user']} and password: {DB_CONFIG['password']}")
        conn = psycopg2.connect(
            host=DB_CONFIG["host"],
            port=DB_CONFIG["port"],
            user=DB_CONFIG["user"],
            password=DB_CONFIG["password"],
            database="postgres",  # Connect to default postgres database
            client_encoding='utf8'
        )
        conn.autocommit = True
        
        # Check server version
        cursor = conn.cursor()
        cursor.execute("SELECT version();")
        version = cursor.fetchone()
        print(f"PostgreSQL server version: {version[0]}")
        
        # Check for existing database
        print(f"Checking if database '{DB_CONFIG['database']}' exists...")
        cursor.execute("SELECT 1 FROM pg_database WHERE datname = %s", (DB_CONFIG['database'],))
        exists = cursor.fetchone()
        
        if exists:
            print(f"Database '{DB_CONFIG['database']}' already exists. Dropping it...")
            # Close all connections to the database before dropping
            cursor.execute("""
            SELECT pg_terminate_backend(pg_stat_activity.pid)
            FROM pg_stat_activity
            WHERE pg_stat_activity.datname = %s
            AND pid <> pg_backend_pid();
            """, (DB_CONFIG['database'],))
            
            cursor.execute(f'DROP DATABASE "{DB_CONFIG["database"]}";')
            print(f"Database '{DB_CONFIG['database']}' has been dropped.")
        
        # Create new database
        print(f"Creating new database '{DB_CONFIG['database']}' with UTF-8 encoding...")
        cursor.execute(f'CREATE DATABASE "{DB_CONFIG["database"]}" ENCODING \'UTF8\';')
        print(f"Database '{DB_CONFIG['database']}' has been created successfully.")
        
        cursor.close()
        conn.close()
        print("Connection to PostgreSQL server closed.")
        
        # Now connect to the new database and create tables
        print(f"Connecting to new database '{DB_CONFIG['database']}'...")
        conn = psycopg2.connect(
            host=DB_CONFIG["host"],
            port=DB_CONFIG["port"],
            user=DB_CONFIG["user"],
            password=DB_CONFIG["password"],
            database=DB_CONFIG["database"],
            client_encoding='utf8'
        )
        conn.autocommit = True
        cursor = conn.cursor()
        
        # Create users table
        print("Creating tables...")
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            username VARCHAR(50) PRIMARY KEY,
            password VARCHAR(256) NOT NULL,
            name VARCHAR(100),
            role VARCHAR(20) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP
        );
        """)
        
        # Create datasets table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS datasets (
            id SERIAL PRIMARY KEY,
            name VARCHAR(100) UNIQUE NOT NULL,
            owner VARCHAR(50) REFERENCES users(username),
            description TEXT,
            city VARCHAR(50),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_system BOOLEAN DEFAULT FALSE
        );
        """)
        
        # Create a simple test user
        import hashlib
        print("Creating default admin user...")
        admin_password = hashlib.sha256("admin123".encode()).hexdigest()
        cursor.execute(
            """
            INSERT INTO users (username, password, name, role)
            VALUES (%s, %s, %s, %s)
            """,
            ("admin", admin_password, "Administrator", "admin")
        )
        
        print("Database setup completed successfully!")
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("===============================")
    print("Database Setup Helper")
    print("===============================")
    
    # Ask for PostgreSQL credentials
    print("\nPlease enter your PostgreSQL credentials:")
    
    DB_CONFIG["host"] = input(f"Host [{DB_CONFIG['host']}]: ") or DB_CONFIG["host"]
    DB_CONFIG["port"] = input(f"Port [{DB_CONFIG['port']}]: ") or DB_CONFIG["port"]
    DB_CONFIG["user"] = input(f"Username [{DB_CONFIG['user']}]: ") or DB_CONFIG["user"] 
    DB_CONFIG["password"] = input(f"Password [{DB_CONFIG['password']}]: ") or DB_CONFIG["password"]
    
    print("\nConnecting to PostgreSQL and setting up database...")
    if create_clean_database():
        print("\nSUCCESS: Database setup completed successfully.")
        print("You can now run the Building Analytics Dashboard.")
    else:
        print("\nERROR: Database setup failed.")
