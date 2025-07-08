"""
Test script to verify the database connection.
This helps isolate and diagnose connection issues.
"""

import os
import logging
from sqlalchemy import create_engine, text
from pathlib import Path
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Base application directory
BASE_DIR = Path(__file__).resolve().parent

def test_connection():
    """Test the database connection with explicit parameters."""
    # Load environment variables
    env_file = BASE_DIR / ".env"
    if env_file.exists():
        load_dotenv(env_file)
        print(f"Loaded environment from {env_file}")
    
    # Get database configuration from environment variables
    db_host = os.environ.get("DB_HOST", "localhost")
    db_port = os.environ.get("DB_PORT", "5432")
    db_name = os.environ.get("DB_NAME", "building_analytics")
    db_user = os.environ.get("DB_USER", "postgres")
    db_password = os.environ.get("DB_PASSWORD", "postgres")
    
    # Print config (with password masked)
    print(f"Database config: host={db_host}, port={db_port}, name={db_name}, user={db_user}, password={'*' * len(db_password)}")
    
    # Create connection string
    conn_string = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
    print(f"Connection string: postgresql://{db_user}:{'*' * len(db_password)}@{db_host}:{db_port}/{db_name}")
    
    try:
        # Try to connect
        print("Attempting to create engine...")
        engine = create_engine(conn_string)
        
        print("Attempting to connect...")
        with engine.connect() as conn:
            print("Executing test query...")
            result = conn.execute(text("SELECT 1")).fetchone()
            print(f"Query result: {result}")
            
        print("Database connection successful!")
        return True
    except Exception as e:
        print(f"Database connection failed: {str(e)}")
        return False

if __name__ == "__main__":
    success = test_connection()
    print(f"Connection test result: {'SUCCESS' if success else 'FAILED'}")
