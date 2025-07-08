"""
Database connection and management module for PostgreSQL integration.
Provides a centralized way to connect to the database and execute queries.
"""

import os
import logging
import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
import streamlit as st

# Try to load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv not installed, will use environment variables directly

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Get database configuration from environment variables or use defaults
DB_HOST = os.environ.get("DB_HOST", "localhost")
DB_PORT = os.environ.get("DB_PORT", "5432")
DB_NAME = os.environ.get("DB_NAME", "building_analytics")
DB_USER = os.environ.get("DB_USER", "postgres")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "postgres")

def get_connection_string():
    """Get the database connection string."""
    return f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

def get_db_engine():
    """Get a SQLAlchemy engine instance."""
    try:
        engine = create_engine(get_connection_string())
        return engine
    except Exception as e:
        logger.error(f"Error creating database engine: {e}")
        raise

def initialize_db():
    """Initialize the database with required tables if they don't exist."""
    try:
        engine = get_db_engine()
        
        # Create users table
        with engine.connect() as conn:
            conn.execute(text("""
            CREATE TABLE IF NOT EXISTS users (
                username VARCHAR(50) PRIMARY KEY,
                password VARCHAR(256) NOT NULL,
                name VARCHAR(100),
                role VARCHAR(20) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP
            );
            """))
            
            # Create datasets table
            conn.execute(text("""
            CREATE TABLE IF NOT EXISTS datasets (
                id SERIAL PRIMARY KEY,
                name VARCHAR(100) UNIQUE NOT NULL,
                owner VARCHAR(50) REFERENCES users(username),
                description TEXT,
                city VARCHAR(50),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_system BOOLEAN DEFAULT FALSE
            );
            """))
            
            # Create buildings table
            conn.execute(text("""
            CREATE TABLE IF NOT EXISTS buildings (
                building_id VARCHAR(50) NOT NULL,
                dataset_id INT REFERENCES datasets(id),
                city VARCHAR(50),
                year INT,
                latitude FLOAT,
                longitude FLOAT,
                energy_consumption FLOAT,
                co2_usage FLOAT,
                water_usage FLOAT,
                energy_intensity FLOAT,
                co2_intensity FLOAT,
                true_energy_label VARCHAR(10),
                true_ges_label VARCHAR(10),
                address TEXT,
                street_number VARCHAR(20),
                street_name VARCHAR(100),
                postal_code VARCHAR(20),
                commune_name VARCHAR(100),
                address_id VARCHAR(50),
                construction_year INT,
                surface_area FLOAT,
                log1p_energy_consumption FLOAT,
                log1p_co2_usage FLOAT,
                log1p_energy_intensity FLOAT,
                log1p_co2_intensity FLOAT,
                pc1 FLOAT,
                pc2 FLOAT,
                cluster INT,
                PRIMARY KEY (building_id, dataset_id, year)
            );
            """))
            
            # Create security logs table
            conn.execute(text("""
            CREATE TABLE IF NOT EXISTS security_logs (
                id SERIAL PRIMARY KEY,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                event_type VARCHAR(50) NOT NULL,
                username VARCHAR(50),
                success BOOLEAN DEFAULT TRUE,
                details JSONB,
                ip_address VARCHAR(50)
            );
            """))
            
            # Create audit logs table
            conn.execute(text("""
            CREATE TABLE IF NOT EXISTS audit_logs (
                id SERIAL PRIMARY KEY,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                action VARCHAR(50) NOT NULL,
                username VARCHAR(50),
                dataset VARCHAR(100),
                entity_id VARCHAR(50),
                changes JSONB
            );
            """))
            
            conn.commit()
        
        logger.info("Database initialized successfully")
        return True
    except SQLAlchemyError as e:
        logger.error(f"Error initializing database: {e}")
        return False

def execute_query(query, params=None, fetch=True):
    """Execute a query with parameters and optionally fetch results."""
    try:
        engine = get_db_engine()
        with engine.connect() as conn:
            if params:
                result = conn.execute(text(query), params)
            else:
                result = conn.execute(text(query))
                
            conn.commit()
            
            if fetch and result.returns_rows:
                return result.fetchall()
            return None
    except SQLAlchemyError as e:
        logger.error(f"Query execution error: {e}")
        raise

def query_to_dataframe(query, params=None):
    """Execute a query and return results as a pandas DataFrame."""
    try:
        engine = get_db_engine()
        return pd.read_sql_query(text(query), engine, params=params)
    except SQLAlchemyError as e:
        logger.error(f"Error executing query to DataFrame: {e}")
        raise

def dataframe_to_sql(df, table_name, if_exists='append'):
    """Save a DataFrame to a SQL table."""
    try:
        engine = get_db_engine()
        df.to_sql(table_name, engine, if_exists=if_exists, index=False)
        return True
    except SQLAlchemyError as e:
        logger.error(f"Error saving DataFrame to SQL: {e}")
        return False

def get_db_connection():
    """Get a database connection for use with Streamlit caching."""
    # Use SQLAlchemy for connection pooling
    engine = get_db_engine()
    return engine.connect()

# Create a Streamlit cache for database connections
@st.cache_resource
def get_cached_db_engine():
    """Get a cached database engine for reuse."""
    return get_db_engine()
