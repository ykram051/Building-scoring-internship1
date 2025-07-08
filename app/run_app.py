"""
Launcher script for the Building Analytics Dashboard.
Enforces database-only mode with no fallback to file storage.
"""

import os
import sys
import logging
from pathlib import Path
import subprocess
import streamlit.web.cli as stcli
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Base paths
BASE_DIR = Path(__file__).resolve().parent
ENV_FILE = BASE_DIR / ".env"

# Load environment variables
if ENV_FILE.exists():
    load_dotenv(ENV_FILE)
    logger.info(f"Loaded environment from {ENV_FILE}")

def check_database_connection():
    """Check if we can connect to the database."""
    try:
        # Import our database module
        sys.path.append(str(BASE_DIR))
        
        # Import the database initialization module
        import 
        
        # First, ensure the database and tables are initialized
        db_init_success = init_database.initialize()
        if not db_init_success:
            logger.error("Database initialization failed")
            return False
            
        # Test the connection with the db_manager
        from utils.db_manager import db_manager
        
        # Test the connection by trying to initialize db_manager
        conn_success = db_manager.initialize()
        
        # If connection is successful, also test a simple query
        if conn_success:
            try:
                from utils.db import execute_query
                result = execute_query("SELECT 1 as test", fetch=True)
                if result and result[0][0] == 1:
                    logger.info("Database connection and query test successful")
                    return True
            except Exception as e:
                logger.error(f"Database query test failed: {e}")
                return False
                
        return conn_success
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        return False

def main():
    """Main launcher function."""
    logger.info("Starting Building Analytics Dashboard")
    
    # App is in database-only mode    logger.info("Database-only mode is enabled. Checking connection...")
    db_connected = check_database_connection()
    if not db_connected:
        print("\n" + "="*80)
        print("ERROR: Database connection failed! Application requires a working PostgreSQL connection.")
        print("Please make sure PostgreSQL is running and check your connection settings in .env file.")
        print("="*80 + "\n")
        sys.exit(1)
    
    logger.info("Database connection successful - launching application")
    
    # Launch Streamlit app
    main_path = BASE_DIR / "main.py"
    sys.argv = ["streamlit", "run", str(main_path)]
    sys.exit(stcli.main())

if __name__ == "__main__":
    main()
