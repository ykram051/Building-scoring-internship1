"""
Module to provide a customized database manager that works around encoding issues.
"""

import os
import logging
from sqlalchemy import create_engine, text

# Initialize logger
logger = logging.getLogger(__name__)

class SimpleDBManager:
    """
    A simpler database manager that avoids encoding issues by directly using
    environment variables instead of going through other configuration layers.
    """
    def __init__(self):
        """Initialize the database manager."""
        self._engine = None
        self._initialized = False
        
    def initialize(self):
        """Initialize database connection directly with env vars."""
        if self._initialized:
            return True
            
        try:
            # Get database configuration from environment variables
            db_host = os.environ.get("DB_HOST", "localhost")
            db_port = os.environ.get("DB_PORT", "5432")
            db_name = os.environ.get("DB_NAME", "building_analytics")
            db_user = os.environ.get("DB_USER", "postgres")
            db_password = os.environ.get("DB_PASSWORD", "root")
            
            # Create connection string directly
            conn_string = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
            
            # Create engine
            self._engine = create_engine(conn_string)
            
            # Test connection
            with self._engine.begin() as conn:  # Use begin() for SQLAlchemy 2.0+ compatibility
                conn.execute(text("SELECT 1"))
                
            self._initialized = True
            logger.info("Database connection initialized successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            # Provide helpful error messages for common issues
            error_str = str(e).lower()
            if "password authentication failed" in error_str:
                logger.error("Database password authentication failed. Check your credentials or run setup_database.py")
            elif "could not connect" in error_str or "connection refused" in error_str:
                logger.error("Could not connect to PostgreSQL. Make sure PostgreSQL is running or use Docker Compose")
            elif "utf-8" in error_str or "decode" in error_str:
                logger.error("Database encoding issue. Check data integrity or character encoding settings")
            return False
            
    def get_engine(self):
        """Get the SQLAlchemy engine."""
        if not self._initialized:
            self.initialize()
        return self._engine
        
# Create a singleton instance
simple_db_manager = SimpleDBManager()

def get_simple_db_manager():
    """Get the database manager instance."""
    simple_db_manager.initialize()
    return simple_db_manager
