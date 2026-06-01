"""
Configuration module for the Building Analytics Dashboard.
This provides environment variable loading and centralized configuration.
"""

import os
from pathlib import Path
import logging
from dotenv import load_dotenv
import json

# Set up logging
logging.basicConfig(level=logging.WARNING, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Base application directory
BASE_DIR = Path(__file__).resolve().parent.parent

# Try to load environment variables from .env file
env_file = BASE_DIR / ".env"
if env_file.exists():
    load_dotenv(env_file)
    logger.info(f"Loaded environment from {env_file}")
else:
    logger.warning(f"No .env file found at {env_file}")

# Database configuration
# Try to get database credentials from Streamlit secrets if deployed on Streamlit Cloud
try:
    import streamlit as st
    if hasattr(st, 'secrets') and 'postgres' in st.secrets:
        logger.info("Using database credentials from Streamlit secrets")
        DB_CONFIG = {
            "host": st.secrets.postgres.host,
            "port": st.secrets.postgres.port,
            "database": st.secrets.postgres.dbname,
            "user": st.secrets.postgres.user,
            "password": st.secrets.postgres.password
        }
    else:
        # Fall back to environment variables
        DB_CONFIG = {
            "host": os.environ.get("DB_HOST", "localhost"),
            "port": os.environ.get("DB_PORT", "5432"),
            "database": os.environ.get("DB_NAME", "building_analytics"),
            "user": os.environ.get("DB_USER", "postgres"),
            "password": os.environ.get("DB_PASSWORD", "root")
        }
except ImportError:
    # Streamlit not available or not being used
    DB_CONFIG = {
        "host": os.environ.get("DB_HOST", "localhost"),
        "port": os.environ.get("DB_PORT", "5432"),
        "database": os.environ.get("DB_NAME", "building_analytics"),
        "user": os.environ.get("DB_USER", "postgres"),
        "password": os.environ.get("DB_PASSWORD", "root")
    }

# File paths (maintained for migration purposes only)
DATA_DIR = BASE_DIR / "data"
USERS_FILE = DATA_DIR / "users.json"
OWNERSHIP_FILE = DATA_DIR / "user_datasets" / "ownership.json"

def get_db_connection_string():
    """Get the database connection string."""
    return f"postgresql://{DB_CONFIG['user']}:{DB_CONFIG['password']}@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}"

def is_database_enabled():
    """Check if database connections should be used.
    In strict database-only mode, this always returns True.
    """
    return True
