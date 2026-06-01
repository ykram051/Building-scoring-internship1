"""
Unified Database Manager
Combines the functionality of db_manager.py and simple_db_manager.py into a single, consolidated interface.
Supports both PostgreSQL and SQLite with proper fallback handling.
"""

import os
import logging
import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from utils.config import get_db_connection_string, is_database_enabled
import streamlit as st

# Initialize logger
logger = logging.getLogger(__name__)

class UnifiedDatabaseManager:
    """
    Unified database manager that handles both PostgreSQL and SQLite connections
    with proper fallback mechanisms and encoding issue workarounds.
    """
    
    def __init__(self):
        """Initialize the unified database manager."""
        self._engine = None
        self._connection_type = None  # 'postgresql', 'sqlite', or None
        self._initialized = False
        
    def initialize(self):
        """Initialize database connection with fallback hierarchy."""
        if self._initialized:
            return True
            
        # Check if we should use fallback mode first
        try:
            from utils.db import should_use_fallback
            if should_use_fallback():
                logger.info("Fallback mode requested - skipping database initialization")
                return False
        except ImportError:
            pass  # Continue with database initialization
        
        # Try PostgreSQL first
        if self._try_postgresql():
            self._connection_type = 'postgresql'
            self._initialized = True
            logger.info("PostgreSQL connection initialized successfully")
            return True
            
        # Try SQLite as fallback
        if self._try_sqlite():
            self._connection_type = 'sqlite'
            self._initialized = True
            logger.info("SQLite fallback connection initialized successfully")
            return True
            
        # Both failed
        logger.error("All database connection attempts failed")
        return False
        
    def _try_postgresql(self):
        """Try to establish PostgreSQL connection."""
        try:
            # Try to get configuration from Streamlit secrets first
            db_config = self._get_postgresql_config()
            if not db_config:
                return False
                
            # Create connection string
            conn_string = f"postgresql://{db_config['user']}:{db_config['password']}@{db_config['host']}:{db_config['port']}/{db_config['name']}"
            
            # Create engine
            self._engine = create_engine(conn_string)
            
            # Test connection
            with self._engine.begin() as conn:
                conn.execute(text("SELECT 1"))
                
            return True
        except Exception as e:
            logger.warning(f"PostgreSQL connection failed: {e}")
            return False
            
    def _try_sqlite(self):
        """Try to establish SQLite connection."""
        try:
            # Use SQLite as fallback
            from utils.sqlite_manager import get_sqlite_manager
            sqlite_manager = get_sqlite_manager()
            if sqlite_manager and sqlite_manager._initialized:
                self._engine = sqlite_manager.get_engine()
                return True
            return False
        except Exception as e:
            logger.warning(f"SQLite connection failed: {e}")
            return False
            
    def _get_postgresql_config(self):
        """Get PostgreSQL configuration with proper fallback hierarchy."""
        # Try Streamlit secrets first
        if hasattr(st, 'secrets'):
            for section_name in ['database', 'postgres']:
                if section_name in st.secrets:
                    section = st.secrets[section_name]
                    db_password = section.get('password', None)
                    
                    # Check for fallback mode conditions
                    if db_password is None or str(db_password).strip() == "":
                        logger.info("Empty or missing password in secrets - skipping PostgreSQL")
                        return None
                        
                    return {
                        'host': section.get('host', 'localhost'),
                        'port': section.get('port', '5432'),
                        'name': section.get('database', section.get('dbname', 'building_analytics')),
                        'user': section.get('user', 'postgres'),
                        'password': db_password
                    }
        
        # Fallback to environment variables
        db_password = os.environ.get("DB_PASSWORD", None)
        if not db_password or str(db_password).strip() == "":
            logger.info("Empty password detected in environment - skipping PostgreSQL")
            return None
            
        return {
            'host': os.environ.get("DB_HOST", "localhost"),
            'port': os.environ.get("DB_PORT", "5432"),
            'name': os.environ.get("DB_NAME", "building_analytics"),
            'user': os.environ.get("DB_USER", "postgres"),
            'password': db_password
        }
    
    def get_engine(self):
        """Get the SQLAlchemy engine."""
        if not self._initialized:
            self.initialize()
        return self._engine
        
    def get_connection(self):
        """Get a database connection."""
        if not self._initialized:
            self.initialize()
        return self._engine.connect() if self._engine else None
    
    def execute_query(self, query, params=None, fetch=True):
        """Execute a SQL query and optionally return results."""
        if not self._initialized:
            self.initialize()
            
        if not self._engine:
            logger.error("Database not initialized. Cannot execute query.")
            return None
            
        try:
            with self._engine.begin() as conn:
                if params:
                    result = conn.execute(text(query), params)
                else:
                    result = conn.execute(text(query))
                
                if fetch and result.returns_rows:
                    return result.fetchall()
                return None
        except Exception as e:
            logger.error(f"Query execution error: {e}")
            raise
    
    def dataframe_from_query(self, query, params=None):
        """Execute a query and return results as a pandas DataFrame."""
        if not self._initialized:
            self.initialize()
            
        if not self._engine:
            logger.error("Database not initialized. Cannot execute query.")
            return pd.DataFrame()
            
        try:
            with self._engine.connect() as conn:
                return pd.read_sql_query(text(query), conn, params=params)
        except Exception as e:
            logger.error(f"Error executing query to DataFrame: {e}")
            return pd.DataFrame()
    
    def save_dataframe(self, df, table_name, if_exists='append'):
        """Save a DataFrame to the database."""
        if not self._initialized:
            self.initialize()
            
        if not self._engine:
            logger.error("Database not initialized. Cannot save DataFrame.")
            return False
            
        try:
            df.to_sql(table_name, self._engine, if_exists=if_exists, index=False)
            return True
        except Exception as e:
            logger.error(f"Error saving DataFrame to {table_name}: {e}")
            return False
    
    def get_connection_type(self):
        """Get the type of database connection ('postgresql', 'sqlite', or None)."""
        return self._connection_type if self._initialized else None
    
    def is_initialized(self):
        """Check if the database manager is initialized."""
        return self._initialized

# Create a singleton instance
_unified_db_manager = UnifiedDatabaseManager()

def get_unified_db_manager():
    """Get the unified database manager instance."""
    if not _unified_db_manager.is_initialized():
        _unified_db_manager.initialize()
    return _unified_db_manager

def get_db_manager():
    """Alias for get_unified_db_manager for backward compatibility."""
    return get_unified_db_manager()
