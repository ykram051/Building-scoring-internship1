"""
Database Migration Script for Dynamic Datasets

Run this script to initialize the flexible dataset schema in your database.
"""

import sys
import os
import logging
from pathlib import Path

# Add app directory to Python path
current_dir = Path(__file__).resolve().parent
app_dir = current_dir.parent / "app"
sys.path.insert(0, str(app_dir))

# Import database utilities
try:
    from utils.db import initialize_database
    from utils.dataset_manager import dataset_manager
    
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    def main():
        """Initialize the flexible dataset schema."""
        print("🚀 Initializing flexible dataset schema...")
        
        # Initialize base database
        print("📊 Setting up base database tables...")
        if not initialize_database():
            print("❌ Failed to initialize base database")
            return False
        
        # Initialize dataset manager schema
        print("📈 Setting up flexible dataset schema...")
        if not dataset_manager.initialize_schema():
            print("❌ Failed to initialize dataset manager schema")
            return False
        
        print("✅ Flexible dataset schema initialized successfully!")
        print("\n🎉 You can now upload datasets with arbitrary schemas!")
        print("\n📋 Features available:")
        print("   • Upload CSV/Excel files with any column structure")
        print("   • Automatic schema detection and validation")
        print("   • JSONB storage for flexible querying")
        print("   • Dedicated tables for large datasets")
        print("   • Advanced dataset explorer interface")
        print("   • Role-based access control")
        
        return True
    
    if __name__ == "__main__":
        success = main()
        sys.exit(0 if success else 1)
        
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Please ensure you're running this from the project root directory")
    print("and that all dependencies are installed.")
    sys.exit(1)
except Exception as e:
    print(f"❌ Error: {e}")
    sys.exit(1)
