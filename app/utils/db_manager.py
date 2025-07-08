"""
Database manager module that provides a centralized interface for DB operations.
This helps maintain a consistent approach to database access across the application.
"""

import pandas as pd
import streamlit as st
import logging
from sqlalchemy import create_engine, text
from utils.config import get_db_connection_string, is_database_enabled

# Initialize logger
logger = logging.getLogger(__name__)

class DatabaseManager:
    """
    A class to manage database operations consistently across the application.
    """
    def __init__(self):
        """Initialize the database manager."""
        self._engine = None
        self._connection = None
        self._initialized = False
        
    def initialize(self):
        """Initialize database connection."""
        if self._initialized:
            return True
            
        # In strict database-only mode, is_database_enabled() always returns True
        # but we'll keep this check for code clarity
        if not is_database_enabled():
            logger.error("Database is required but disabled. Application cannot run.")
            return False
            
        try:
            self._engine = create_engine(get_db_connection_string())
            # Test connection
            with self._engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            self._initialized = True
            logger.info("Database connection initialized successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            # In strict mode, database failures are critical
            return False
            
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
            with self._engine.connect() as conn:
                if params:
                    result = conn.execute(text(query), params)
                else:
                    result = conn.execute(text(query))
                
                conn.commit()
                
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
            return pd.read_sql_query(text(query), self._engine, params=params)
        except Exception as e:
            logger.error(f"Error executing query to DataFrame: {e}")
            return pd.DataFrame()
    
    def save_dataframe(self, df, table_name, if_exists='append'):
        """Save a pandas DataFrame to a database table."""
        if not self._initialized:
            self.initialize()
            
        if not self._engine:
            logger.error("Database not initialized. Cannot save DataFrame.")
            return False
            
        try:
            df.to_sql(table_name, self._engine, if_exists=if_exists, index=False)
            return True
        except Exception as e:
            logger.error(f"Error saving DataFrame to database: {e}")
            return False
    
    # User-related methods
    def get_users(self):
        """Get all users from the database."""
        return self.dataframe_from_query("SELECT * FROM users ORDER BY username")
    
    def get_user(self, username):
        """Get a user by username."""
        return self.dataframe_from_query("SELECT * FROM users WHERE username = :username", {"username": username})
    
    def create_user(self, username, password_hash, name, role):
        """Create a new user."""
        try:
            self.execute_query(
                """
                INSERT INTO users (username, password, name, role)
                VALUES (:username, :password, :name, :role)
                """,
                {
                    "username": username,
                    "password": password_hash,
                    "name": name,
                    "role": role
                },
                fetch=False
            )
            return True
        except Exception as e:
            logger.error(f"Error creating user: {e}")
            return False
    
    # Dataset-related methods
    def get_datasets(self):
        """Get all datasets from the database."""
        return self.dataframe_from_query("""
            SELECT d.*, u.username as owner_username 
            FROM datasets d
            LEFT JOIN users u ON d.owner = u.username
            ORDER BY d.name
        """)
    
    def get_user_datasets(self, username):
        """Get datasets owned by a specific user."""
        return self.dataframe_from_query(
            """
            SELECT * FROM datasets
            WHERE owner = :username
            ORDER BY name
            """,
            {"username": username}
        )
    
    def get_dataset(self, dataset_name):
        """Get a dataset by name."""
        return self.dataframe_from_query(
            "SELECT * FROM datasets WHERE name = :name",
            {"name": dataset_name}
        )
    
    def get_dataset_by_id(self, dataset_id):
        """Get a dataset by ID."""
        return self.dataframe_from_query(
            "SELECT * FROM datasets WHERE id = :id",
            {"id": dataset_id}
        )
    
    def create_dataset(self, name, owner, city=None, description=None, is_system=False):
        """Create a new dataset."""
        try:
            result = self.execute_query(
                """
                INSERT INTO datasets (name, owner, city, description, is_system)
                VALUES (:name, :owner, :city, :description, :is_system)
                RETURNING id
                """,
                {
                    "name": name,
                    "owner": owner,
                    "city": city,
                    "description": description,
                    "is_system": is_system
                },
                fetch=True
            )
            if result:
                return result[0][0]  # Return the new dataset ID
            return None
        except Exception as e:
            logger.error(f"Error creating dataset: {e}")
            return None
    
    # Building-related methods
    def get_buildings(self, dataset_id=None, city=None, year=None, limit=1000):
        """
        Get buildings from the database with optional filters.
        
        Args:
            dataset_id: Filter by dataset ID
            city: Filter by city name
            year: Filter by year
            limit: Maximum number of rows to return
        """
        query = "SELECT * FROM buildings"
        params = {}
        where_clauses = []
        
        if dataset_id:
            where_clauses.append("dataset_id = :dataset_id")
            params["dataset_id"] = dataset_id
        
        if city:
            where_clauses.append("city = :city")
            params["city"] = city
        
        if year:
            where_clauses.append("year = :year")
            params["year"] = year
        
        if where_clauses:
            query += " WHERE " + " AND ".join(where_clauses)
        
        query += f" LIMIT {limit}"
        
        return self.dataframe_from_query(query, params)
    
    def get_buildings_for_dataset(self, dataset_name, limit=1000):
        """Get buildings for a specific dataset."""
        return self.dataframe_from_query(
            """
            SELECT b.* 
            FROM buildings b
            JOIN datasets d ON b.dataset_id = d.id
            WHERE d.name = :name
            LIMIT :limit
            """,
            {"name": dataset_name, "limit": limit}
        )
    
    # Security and audit logs
    def get_security_logs(self, limit=100):
        """Get security logs from the database."""
        return self.dataframe_from_query(
            """
            SELECT * FROM security_logs
            ORDER BY timestamp DESC
            LIMIT :limit
            """,
            {"limit": limit}
        )
    
    def get_audit_logs(self, limit=100):
        """Get audit logs from the database."""
        return self.dataframe_from_query(
            """
            SELECT * FROM audit_logs
            ORDER BY timestamp DESC
            LIMIT :limit
            """,
            {"limit": limit}
        )
    
    def log_security_event(self, event_type, username, details=None, success=True):
        """Log a security event to the database."""
        import json
        
        if not self._initialized:
            self.initialize()
            
        if not self._engine:
            logger.error("Database not initialized. Cannot log security event.")
            return False
            
        try:
            self.execute_query(
                """
                INSERT INTO security_logs 
                    (event_type, username, success, details) 
                VALUES 
                    (:event_type, :username, :success, :details::jsonb)
                """,
                {
                    "event_type": event_type, 
                    "username": username,
                    "success": success,
                    "details": json.dumps(details) if details else "{}"
                },
                fetch=False
            )
            return True
        except Exception as e:
            logger.error(f"Failed to log security event: {e}")
            return False
    
    def log_audit_event(self, action, username, dataset, entity_id=None, changes=None):
        """Log an audit event to the database."""
        import json
        
        if not self._initialized:
            self.initialize()
            
        if not self._engine:
            logger.error("Database not initialized. Cannot log audit event.")
            return False
            
        try:
            self.execute_query(
                """
                INSERT INTO audit_logs 
                    (action, username, dataset, entity_id, changes) 
                VALUES 
                    (:action, :username, :dataset, :entity_id, :changes::jsonb)
                """,
                {
                    "action": action, 
                    "username": username,
                    "dataset": dataset,
                    "entity_id": entity_id,
                    "changes": json.dumps(changes) if changes else "{}"
                },
                fetch=False
            )
            return True
        except Exception as e:
            logger.error(f"Failed to log audit event: {e}")
            return False

# Create a singleton instance for use throughout the app
db_manager = DatabaseManager()

# Streamlit cache for database engine
@st.cache_resource
def get_db_manager():
    """Get cached database manager for use in Streamlit app."""
    db_manager.initialize()
    return db_manager
