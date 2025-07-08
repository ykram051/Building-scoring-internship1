"""
Database setup and initialization script.
This script creates the necessary database tables and adds initial users.
"""

import sys
import os
from pathlib import Path

# Add the app directory to sys.path for imports
current_dir = Path(__file__).parent
app_dir = current_dir.parent / "app"
sys.path.insert(0, str(app_dir))

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    env_file = current_dir.parent / ".env"
    if env_file.exists():
        load_dotenv(env_file)
        print(f"Loaded environment from {env_file}")
    else:
        print(f"No .env file found at {env_file}")
except ImportError:
    print("python-dotenv not installed, using system environment variables only")

import logging
from sqlalchemy import create_engine, text
import hashlib

# Import from utils
try:
    from utils.config import get_db_connection_string
    print("Successfully imported config from utils.config")
except ImportError as e:
    print(f"Import failed: {e}")
    # Fallback if import fails
    def get_db_connection_string():
        host = os.environ.get("DB_HOST", "localhost")
        port = os.environ.get("DB_PORT", "5432")
        database = os.environ.get("DB_NAME", "building_analytics")
        user = os.environ.get("DB_USER", "postgres")
        password = os.environ.get("DB_PASSWORD", "root")
        print(f"Using fallback connection: postgresql://{user}:***@{host}:{port}/{database}")
        return f"postgresql://{user}:{password}@{host}:{port}/{database}"

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def hash_password(password):
    """Create SHA-256 hash of a password"""
    return hashlib.sha256(password.encode()).hexdigest()

def create_database_tables(engine):
    """Create the necessary database tables."""
    
    # SQL to create users table
    create_users_table = """
    CREATE TABLE IF NOT EXISTS users (
        id SERIAL PRIMARY KEY,
        username VARCHAR(50) UNIQUE NOT NULL,
        password VARCHAR(255) NOT NULL,
        name VARCHAR(100) NOT NULL,
        role VARCHAR(20) NOT NULL DEFAULT 'user',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """
    
    # SQL to create datasets table
    create_datasets_table = """
    CREATE TABLE IF NOT EXISTS datasets (
        id SERIAL PRIMARY KEY,
        name VARCHAR(255) UNIQUE NOT NULL,
        owner VARCHAR(50) NOT NULL,
        city VARCHAR(100),
        description TEXT,
        is_system BOOLEAN DEFAULT FALSE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (owner) REFERENCES users(username) ON DELETE CASCADE
    );
    """
    
    # SQL to create buildings table (for storing building data)
    create_buildings_table = """
    CREATE TABLE IF NOT EXISTS buildings (
        id SERIAL PRIMARY KEY,
        dataset_id INTEGER NOT NULL,
        building_id VARCHAR(100),
        address TEXT,
        city VARCHAR(100),
        year INTEGER,
        energy_score FLOAT,
        co2_score FLOAT,
        geometry TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (dataset_id) REFERENCES datasets(id) ON DELETE CASCADE
    );
    """
    
    # Execute table creation
    with engine.connect() as conn:
        conn.execute(text(create_users_table))
        conn.execute(text(create_datasets_table))
        conn.execute(text(create_buildings_table))
        conn.commit()
        logger.info("Database tables created successfully")

def create_default_users(engine):
    """Create default users if they don't exist."""
    
    default_users = [
        ("admin", "admin123", "Administrator", "admin"),
        ("user", "user123", "Regular User", "user"),
        ("analyst", "analyst123", "Data Analyst", "analyst"),
        ("manager", "manager123", "Building Manager", "manager")
    ]
    
    with engine.connect() as conn:
        for username, password, name, role in default_users:
            # Check if user exists
            result = conn.execute(
                text("SELECT username FROM users WHERE username = :username"),
                {"username": username}
            )
            
            if not result.fetchone():
                # Create user
                password_hash = hash_password(password)
                conn.execute(
                    text("""
                        INSERT INTO users (username, password, name, role)
                        VALUES (:username, :password, :name, :role)
                    """),
                    {
                        "username": username,
                        "password": password_hash,
                        "name": name,
                        "role": role
                    }
                )
                logger.info(f"Created user: {username}")
            else:
                logger.info(f"User {username} already exists")
        
        conn.commit()

def test_database_connection():
    """Test the database connection."""
    try:
        engine = create_engine(get_db_connection_string())
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            logger.info("Database connection successful")
            return engine
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        return None

def main():
    """Main setup function."""
    logger.info("Starting database setup...")
    
    # Test connection
    engine = test_database_connection()
    if not engine:
        logger.error("Cannot connect to database. Please ensure PostgreSQL is running and configured correctly.")
        logger.error("Database connection details:")
        logger.error(f"Connection string: {get_db_connection_string()}")
        return False
    
    try:
        # Create tables
        create_database_tables(engine)
        
        # Create default users
        create_default_users(engine)
        
        logger.info("Database setup completed successfully!")
        logger.info("Default users created:")
        logger.info("  admin / admin123 (Administrator)")
        logger.info("  user / user123 (Regular User)")
        logger.info("  analyst / analyst123 (Data Analyst)")
        logger.info("  manager / manager123 (Building Manager)")
        
        return True
        
    except Exception as e:
        logger.error(f"Database setup failed: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
