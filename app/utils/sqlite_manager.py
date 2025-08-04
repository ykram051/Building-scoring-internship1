"""
SQLite Database Manager - Lightweight alternative to PostgreSQL
"""

import sqlite3
import pandas as pd
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class SQLiteManager:
    """SQLite database manager for lightweight deployment"""
    
    def __init__(self, db_path=None):
        if db_path is None:
            # Default to app/data directory
            data_dir = Path(__file__).parent.parent / "data"
            data_dir.mkdir(exist_ok=True)
            self.db_path = data_dir / "building_analytics.db"
        else:
            self.db_path = Path(db_path)
        
        self.connection = None
        self.initialize_database()
    
    def get_connection(self):
        """Get SQLite connection"""
        if self.connection is None:
            self.connection = sqlite3.connect(self.db_path, check_same_thread=False)
            self.connection.row_factory = sqlite3.Row  # Enable column access by name
        return self.connection
    
    def initialize_database(self):
        """Initialize SQLite database with required tables"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Create users table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                username TEXT PRIMARY KEY,
                password TEXT NOT NULL,
                name TEXT,
                role TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP
            )
            """)
            
            # Create datasets table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS datasets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                owner TEXT REFERENCES users(username),
                description TEXT,
                city TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_system BOOLEAN DEFAULT FALSE
            )
            """)
            
            # Create default users
            default_users = [
                ('admin', 'admin123', 'Administrator', 'admin'),
                ('user', 'user123', 'Regular User', 'user'),
                ('analyst', 'analyst123', 'Data Analyst', 'analyst'),
            ]
            
            for username, password, name, role in default_users:
                cursor.execute("""
                INSERT OR IGNORE INTO users (username, password, name, role)
                VALUES (?, ?, ?, ?)
                """, (username, password, name, role))
            
            conn.commit()
            logger.info("SQLite database initialized successfully")
            
        except Exception as e:
            logger.error(f"Error initializing SQLite database: {e}")
            raise
    
    def execute_query(self, query, params=None):
        """Execute a query with optional parameters"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            
            conn.commit()
            return cursor.fetchall()
            
        except Exception as e:
            logger.error(f"Error executing query: {e}")
            raise
    
    def close(self):
        """Close database connection"""
        if self.connection:
            self.connection.close()
            self.connection = None

# Global SQLite manager instance
sqlite_manager = SQLiteManager()

def get_sqlite_manager():
    """Get the global SQLite manager instance"""
    return sqlite_manager
