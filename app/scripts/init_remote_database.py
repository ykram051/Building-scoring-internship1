#!/usr/bin/env python3
"""
Remote Database Setup Script for Web Deployment

This script initializes a PostgreSQL database for web deployment of the Building Analytics Dashboard.
It connects to a remote database specified in environment variables or command-line arguments.
"""

import os
import sys
import argparse
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Ensure we can import from parent directory
current_dir = Path(__file__).resolve().parent
app_dir = current_dir.parent if current_dir.name == "scripts" else current_dir
sys.path.append(str(app_dir))

try:
    import psycopg2
except ImportError:
    logger.error("psycopg2 is not installed. Please install it using: pip install psycopg2-binary")
    sys.exit(1)

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Initialize remote PostgreSQL database for web deployment')
    parser.add_argument('--host', default=os.environ.get('DB_HOST'),
                        help='Database host (default: from DB_HOST env var)')
    parser.add_argument('--port', type=int, default=int(os.environ.get('DB_PORT', 5432)),
                        help='Database port (default: from DB_PORT env var or 5432)')
    parser.add_argument('--dbname', default=os.environ.get('DB_NAME'),
                        help='Database name (default: from DB_NAME env var)')
    parser.add_argument('--user', default=os.environ.get('DB_USER'),
                        help='Database user (default: from DB_USER env var)')
    parser.add_argument('--password', default=os.environ.get('DB_PASSWORD'),
                        help='Database password (default: from DB_PASSWORD env var)')
    parser.add_argument('--verbose', action='store_true', help='Enable verbose output')
    return parser.parse_args()

def create_tables(conn):
    """Create database tables."""
    cursor = conn.cursor()
    
    try:
        # Users table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username VARCHAR(50) UNIQUE NOT NULL,
            password VARCHAR(255) NOT NULL,
            name VARCHAR(100),
            email VARCHAR(100),
            role VARCHAR(20) NOT NULL DEFAULT 'user',
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP
        )
        """)
        
        # Datasets table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS datasets (
            id SERIAL PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            city VARCHAR(100) NOT NULL,
            description TEXT,
            owner VARCHAR(50) REFERENCES users(username),
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            file_path VARCHAR(255),
            years VARCHAR(255),
            is_public BOOLEAN DEFAULT true
        )
        """)
        
        # Buildings table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS buildings (
            id SERIAL PRIMARY KEY,
            building_id VARCHAR(50) NOT NULL,
            dataset_id INTEGER REFERENCES datasets(id),
            year INTEGER,
            country VARCHAR(50),
            city VARCHAR(100),
            address VARCHAR(255),
            latitude FLOAT,
            longitude FLOAT,
            building_type VARCHAR(100),
            floor_area FLOAT,
            energy_consumption FLOAT,
            energy_intensity FLOAT,
            co2_usage FLOAT,
            co2_intensity FLOAT,
            water_usage FLOAT,
            construction_year INTEGER,
            renovation_year INTEGER,
            classification VARCHAR(20),
            cluster INTEGER,
            UNIQUE (building_id, dataset_id, year)
        )
        """)
        
        # Security logs
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS security_logs (
            id SERIAL PRIMARY KEY,
            timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            event_type VARCHAR(50) NOT NULL,
            username VARCHAR(50),
            ip_address VARCHAR(50),
            details JSONB,
            success BOOLEAN DEFAULT false
        )
        """)
        
        # Audit logs
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS audit_logs (
            id SERIAL PRIMARY KEY,
            timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            action VARCHAR(50) NOT NULL,
            username VARCHAR(50),
            dataset VARCHAR(100),
            entity_id VARCHAR(50),
            details JSONB,
            old_value TEXT,
            new_value TEXT
        )
        """)
        
        logger.info("Successfully created database tables")
        return True
    
    except Exception as e:
        logger.error(f"Error creating tables: {e}")
        return False
    finally:
        cursor.close()

def create_default_admin(conn):
    """Create default admin user if none exists."""
    cursor = conn.cursor()
    
    try:
        # Check if any users exist
        cursor.execute("SELECT COUNT(*) FROM users")
        count = cursor.fetchone()[0]
        
        if count == 0:
            # Create default admin user with SHA-256 hash of 'admin123'
            admin_password = "a665a45920422f9d417e4867efdc4fb8a04a1f3fff1fa07e998e86f7f7a27ae3"  # SHA-256 hash of 'admin123'
            
            cursor.execute(
                """
                INSERT INTO users (username, password, name, role)
                VALUES (%s, %s, %s, %s)
                """,
                ("admin", admin_password, "Administrator", "admin")
            )
            
            # Also create a regular user
            user_password = "12dea96fec20593566ab75692c9949596833adc9"  # SHA-256 hash of 'user123'
            
            cursor.execute(
                """
                INSERT INTO users (username, password, name, role)
                VALUES (%s, %s, %s, %s)
                """,
                ("user", user_password, "Regular User", "user")
            )
            
            logger.info("Created default users: admin/admin123 and user/user123")
        else:
            logger.info(f"Users already exist ({count} users found)")
            
        return True
    except Exception as e:
        logger.error(f"Error creating default users: {e}")
        return False
    finally:
        cursor.close()

def main():
    """Main function to initialize the database."""
    args = parse_args()
    
    if args.verbose:
        # Set logging level to debug
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Show connection details (without password)
    logger.info(f"Connecting to database: {args.host}:{args.port}/{args.dbname} as {args.user}")
    
    try:
        # Connect to database
        conn = psycopg2.connect(
            host=args.host,
            port=args.port,
            database=args.dbname,
            user=args.user,
            password=args.password
        )
        conn.autocommit = True
        
        # Create tables
        tables_created = create_tables(conn)
        if not tables_created:
            logger.error("Failed to create tables")
            sys.exit(1)
        
        # Create default admin user
        admin_created = create_default_admin(conn)
        if not admin_created:
            logger.error("Failed to create default admin")
            # Continue anyway - this isn't critical
        
        conn.close()
        logger.info("Database initialization completed successfully!")
        
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
