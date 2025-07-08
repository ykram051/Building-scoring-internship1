"""
Full migration script to set up the PostgreSQL database, create tables, and migrate data.
"""

import sys
import logging
from pathlib import Path
import time

# Set up logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Add the parent directory to path so we can import our modules
current_dir = Path(__file__).resolve().parent
parent_dir = current_dir.parent
sys.path.append(str(parent_dir))

def main():
    """Run the full migration process."""
    logger.info("Starting full migration process")
    
    # Step 1: Initialize database
    logger.info("Step 1: Initialize database")
    from scripts.initialize_db import initialize_database
    
    if not initialize_database():
        logger.error("Database initialization failed. Aborting migration.")
        return False
    
    logger.info("Waiting 2 seconds for database setup to complete...")
    time.sleep(2)
    
    # Step 2: Migrate data
    logger.info("Step 2: Migrate data")
    from scripts.migrate_to_db import run_migration
    
    if not run_migration():
        logger.error("Data migration failed.")
        return False
    
    # Step 3: Verify migration
    logger.info("Step 3: Verify migration")
    
    from utils.db_manager import db_manager
    
    db_manager.initialize()
    
    # Check users
    users_df = db_manager.get_users()
    logger.info(f"Found {len(users_df)} users in database")
    
    # Check datasets
    datasets_df = db_manager.get_datasets()
    logger.info(f"Found {len(datasets_df)} datasets in database")
    
    # Check a sample of buildings
    buildings_sample = db_manager.get_buildings(limit=5)
    logger.info(f"Sample buildings: {len(buildings_sample)} rows")
    
    logger.info("Migration completed successfully!")
    return True

if __name__ == "__main__":
    main()
