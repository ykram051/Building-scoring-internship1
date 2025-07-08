"""
Quick setup script for the Building Analytics Dashboard.
This script provides options to set up the application with or without PostgreSQL.
"""

import os
import sys
from pathlib import Path

def print_header():
    """Print the setup header."""
    print("=" * 60)
    print("  Building Analytics Dashboard - Quick Setup")
    print("=" * 60)
    print()

def check_docker():
    """Check if Docker is available."""
    try:
        import subprocess
        result = subprocess.run(['docker', '--version'], capture_output=True, text=True)
        return result.returncode == 0
    except:
        return False

def check_postgresql():
    """Check if PostgreSQL is running locally."""
    try:
        import psycopg2
        conn = psycopg2.connect(
            host="localhost",
            port="5432",
            database="postgres",
            user="postgres",
            password="root"
        )
        conn.close()
        return True
    except:
        return False

def create_env_file():
    """Create a .env file with default settings."""
    env_content = """# Database Configuration
# PostgreSQL database connection settings

# For local development (requires PostgreSQL to be installed locally)
DB_HOST=localhost
DB_PORT=5432
DB_NAME=building_analytics
DB_USER=postgres
DB_PASSWORD=postgres

# For development/testing
DEVELOPMENT_MODE=true

# Logging level
LOG_LEVEL=INFO
"""
    
    env_file = Path(".env")
    if not env_file.exists():
        with open(env_file, "w") as f:
            f.write(env_content)
        print(f"✅ Created {env_file}")
    else:
        print(f"⚠️  {env_file} already exists")

def main():
    """Main setup function."""
    print_header()
    
    print("This script will help you set up the Building Analytics Dashboard.")
    print("You can run it with or without a PostgreSQL database.")
    print()
    
    # Check prerequisites
    print("Checking prerequisites...")
    
    docker_available = check_docker()
    postgresql_available = check_postgresql()
    
    print(f"Docker available: {'✅' if docker_available else '❌'}")
    print(f"PostgreSQL running locally: {'✅' if postgresql_available else '❌'}")
    print()
    
    # Setup options
    print("Setup options:")
    print("1. Run with Docker (PostgreSQL + App) - Full features")
    print("2. Run with local PostgreSQL - Full features")
    print("3. Run in fallback mode (no database) - Limited features")
    print("4. Just create configuration files")
    print()
    
    while True:
        choice = input("Choose an option (1-4): ").strip()
        
        if choice == "1":
            if not docker_available:
                print("❌ Docker is not available. Please install Docker first.")
                continue
            setup_docker()
            break
        elif choice == "2":
            setup_local_postgresql()
            break
        elif choice == "3":
            setup_fallback()
            break
        elif choice == "4":
            create_config_files()
            break
        else:
            print("Invalid choice. Please enter 1, 2, 3, or 4.")

def setup_docker():
    """Set up with Docker."""
    print("\n🐳 Setting up with Docker...")
    
    create_env_file()
    
    print("\nTo start the application with Docker:")
    print("1. Run: docker-compose up -d")
    print("2. Wait for the database to initialize")
    print("3. Open: http://localhost:8501")
    print("\nDefault login credentials:")
    print("• admin / admin123 (Administrator)")
    print("• user / user123 (Regular User)")
    print("• analyst / analyst123 (Data Analyst)")

def setup_local_postgresql():
    """Set up with local PostgreSQL."""
    print("\n🗃️ Setting up with local PostgreSQL...")
    
    create_env_file()
    
    print("\nTo complete the setup:")
    print("1. Make sure PostgreSQL is running")
    print("2. Run: python scripts/setup_database.py")
    print("3. Run: streamlit run app/main_db.py")
    print("\nDefault login credentials will be created automatically.")

def setup_fallback():
    """Set up in fallback mode."""
    print("\n🔄 Setting up in fallback mode...")
    
    # Create data directory and users file
    data_dir = Path("app/data")
    data_dir.mkdir(parents=True, exist_ok=True)
    
    print("✅ Created data directory")
    
    print("\nTo run the application:")
    print("1. Run: streamlit run app/main_db.py")
    print("2. The app will automatically create default users")
    print("\nDefault login credentials:")
    print("• admin / admin123 (Administrator)")
    print("• user / user123 (Regular User)")
    print("• analyst / analyst123 (Data Analyst)")
    print("\nNote: Limited features available without database.")

def create_config_files():
    """Just create configuration files."""
    print("\n📄 Creating configuration files...")
    
    create_env_file()
    
    # Create data directory
    data_dir = Path("app/data")
    data_dir.mkdir(parents=True, exist_ok=True)
    print("✅ Created data directory")
    
    print("\nConfiguration files created. Choose your setup method later.")

if __name__ == "__main__":
    main()
