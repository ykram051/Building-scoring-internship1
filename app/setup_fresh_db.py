"""
Special script to create a fresh PostgreSQL database with proper encoding.
Run this script to fix encoding issues with the database.
"""

import os
import sys
import logging
import psycopg2
from pathlib import Path

# Setup logging
logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Base directory
BASE_DIR = Path(__file__).resolve().parent

# Import configuration
sys.path.append(str(BASE_DIR))
from utils.config import DB_CONFIG

def reset_database():
    """Drop and recreate the database with proper UTF-8 encoding."""
    try:
        # Connect to PostgreSQL server (not to the specific database)
        conn = psycopg2.connect(
            host=DB_CONFIG["host"],
            port=DB_CONFIG["port"],
            user=DB_CONFIG["user"],
            password=DB_CONFIG["password"],
            database="postgres",  # Connect to default postgres database
            client_encoding='utf8'
        )
        conn.autocommit = True
        cursor = conn.cursor()
        
        # Check if our database exists
        cursor.execute(f"SELECT 1 FROM pg_database WHERE datname = '{DB_CONFIG['database']}'")
        exists = cursor.fetchone()
        
        if exists:
            # Drop existing database
            logger.info(f"Dropping existing database: {DB_CONFIG['database']}")
            cursor.execute(f"DROP DATABASE {DB_CONFIG['database']}")
        
        # Create database with UTF-8 encoding
        logger.info(f"Creating fresh database: {DB_CONFIG['database']} with UTF-8 encoding")
        cursor.execute(f"CREATE DATABASE {DB_CONFIG['database']} ENCODING 'UTF8'")
        
        cursor.close()
        conn.close()
        
        logger.info(f"Database {DB_CONFIG['database']} has been reset with UTF-8 encoding")
        return True
    except Exception as e:
        logger.error(f"Error resetting database: {e}")
        return False

if __name__ == "__main__":
    print("This will DROP and recreate your database with proper encoding.")
    confirmation = input("Are you sure you want to continue? (y/N): ")
    
    if confirmation.lower() == 'y':
        if reset_database():
            print("Database reset successful.")
            print("Now run 'python init_database.py' to create the tables and default data.")
            sys.exit(0)
        else:
            print("Database reset failed. Check the logs for details.")
            sys.exit(1)
    else:
        print("Operation cancelled.")
        sys.exit(0)
