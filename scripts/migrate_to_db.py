"""
Data migration script to move existing data from files to PostgreSQL database.
"""

import os
import json
import pandas as pd
from pathlib import Path
import logging
import hashlib
import sys

# Add the parent directory to path so we can import our modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app"))

from utils.db import initialize_db, dataframe_to_sql, execute_query, query_to_dataframe

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Define paths
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
USERS_FILE = DATA_DIR / "users.json"
OWNERSHIP_FILE = DATA_DIR / "user_datasets" / "ownership.json"

def hash_password(password):
    """Create SHA-256 hash of a password"""
    return hashlib.sha256(password.encode()).hexdigest()

def migrate_users():
    """Migrate users from JSON file to database."""
    if not USERS_FILE.exists():
        logger.error(f"Users file not found: {USERS_FILE}")
        return False
    
    try:
        # Load users from JSON
        with open(USERS_FILE, "r") as f:
            users_data = json.load(f)
        
        logger.info(f"Found {len(users_data)} users to migrate")
        
        # Prepare data for the database
        user_records = []
        for username, data in users_data.items():
            user_records.append({
                "username": username,
                "password": data["password"],
                "name": data.get("name", username),
                "role": data.get("role", "user")
            })
        
        # Convert to DataFrame and save to database
        users_df = pd.DataFrame(user_records)
        if dataframe_to_sql(users_df, "users", if_exists="replace"):
            logger.info("Users migrated successfully")
            return True
        else:
            logger.error("Failed to migrate users")
            return False
            
    except Exception as e:
        logger.error(f"Error migrating users: {e}")
        return False

def migrate_datasets_and_buildings():
    """Migrate datasets and buildings from CSV files to database."""
    try:
        # Find all CSV files that match our dataset pattern
        csv_files = list(DATA_DIR.glob("reduced_*_buildings*.csv"))
        logger.info(f"Found {len(csv_files)} dataset files to migrate")
        
        # Track datasets for reference
        datasets_map = {}  # Filename to dataset_id mapping
        
        # Process each file
        for csv_file in csv_files:
            file_name = csv_file.name
            
            # Extract city and year information
            parts = file_name.replace("reduced_", "").replace(".csv", "").split("_")
            city = parts[0]
            
            # Determine if this is a year-specific or all-years file
            is_all_years = "all_years" in file_name
            year = None
            if len(parts) > 2 and not is_all_years:
                try:
                    year = int(parts[-1])
                except ValueError:
                    pass
            
            # Create dataset record
            dataset_name = f"{city}"
            if year:
                dataset_name = f"{city}_{year}"
            elif is_all_years:
                dataset_name = f"{city}_all_years"
            
            # Add dataset to database
            try:
                dataset_id = execute_query(
                    """
                    INSERT INTO datasets (name, city, is_system)
                    VALUES (:name, :city, TRUE)
                    ON CONFLICT (name) DO UPDATE 
                    SET city = EXCLUDED.city
                    RETURNING id
                    """,
                    {"name": dataset_name, "city": city},
                    fetch=True
                )[0][0]
                
                datasets_map[file_name] = dataset_id
                logger.info(f"Added dataset: {dataset_name} with ID {dataset_id}")
                
                # Load and process CSV data
                df = pd.read_csv(csv_file)
                
                # Rename columns to match database schema (lowercase)
                df_renamed = df.rename(columns={
                    'building_id': 'building_id',
                    'latitude': 'latitude',
                    'longitude': 'longitude',
                    'Energy_Consumption': 'energy_consumption',
                    'CO2_Usage': 'co2_usage',
                    'Water_Usage': 'water_usage',
                    'Energy_Intensity': 'energy_intensity',
                    'CO2_Intensity': 'co2_intensity',
                    'true_energy_label': 'true_energy_label',
                    'true_ges_label': 'true_ges_label',
                    'adresse_ban': 'address',
                    'numero_voie_ban': 'street_number',
                    'nom_rue_ban': 'street_name',
                    'code_postal_ban': 'postal_code',
                    'nom_commune_ban': 'commune_name',
                    'identifiant_ban': 'address_id',
                    'annee_construction': 'construction_year',
                    'surface_habitable_immeuble': 'surface_area',
                    'log1p_Energy_Consumption': 'log1p_energy_consumption',
                    'log1p_CO2_Usage': 'log1p_co2_usage',
                    'log1p_Energy_Intensity': 'log1p_energy_intensity',
                    'log1p_CO2_Intensity': 'log1p_co2_intensity',
                    'PC1': 'pc1',
                    'PC2': 'pc2',
                    'cluster': 'cluster',
                    'city': 'city',
                    'year': 'year'
                })
                
                # Add dataset_id to every row
                df_renamed['dataset_id'] = dataset_id
                
                # Ensure column order matches the database schema
                expected_cols = [
                    'building_id', 'dataset_id', 'city', 'year', 
                    'latitude', 'longitude', 
                    'energy_consumption', 'co2_usage', 'water_usage',
                    'energy_intensity', 'co2_intensity',
                    'true_energy_label', 'true_ges_label',
                    'address', 'street_number', 'street_name',
                    'postal_code', 'commune_name', 'address_id',
                    'construction_year', 'surface_area',
                    'log1p_energy_consumption', 'log1p_co2_usage',
                    'log1p_energy_intensity', 'log1p_co2_intensity',
                    'pc1', 'pc2', 'cluster'
                ]
                
                # Only include columns that exist in the dataframe
                available_cols = [col for col in expected_cols if col in df_renamed.columns]
                df_final = df_renamed[available_cols]
                
                # Save buildings to database
                dataframe_to_sql(df_final, "buildings", if_exists="append")
                logger.info(f"Migrated {len(df_final)} buildings from {file_name}")
                
            except Exception as e:
                logger.error(f"Error processing file {file_name}: {e}")
        
        return True
    except Exception as e:
        logger.error(f"Error migrating datasets and buildings: {e}")
        return False

def migrate_dataset_ownership():
    """Migrate dataset ownership information from JSON to database."""
    if not OWNERSHIP_FILE.exists():
        logger.warning(f"Ownership file not found: {OWNERSHIP_FILE}. Skipping ownership migration.")
        return True
    
    try:
        # Load ownership data
        with open(OWNERSHIP_FILE, "r") as f:
            ownership_data = json.load(f)
        
        logger.info(f"Found ownership data for {len(ownership_data)} datasets")
        
        # Update dataset ownership in the database
        for dataset_name, data in ownership_data.items():
            owner = data.get("owner")
            if owner:
                execute_query(
                    """
                    UPDATE datasets
                    SET owner = :owner
                    WHERE name = :name
                    """,
                    {"name": dataset_name, "owner": owner}
                )
        
        logger.info("Dataset ownership migrated successfully")
        return True
    except Exception as e:
        logger.error(f"Error migrating dataset ownership: {e}")
        return False

def run_migration():
    """Run the complete migration process."""
    logger.info("Starting database migration process...")
    
    # Initialize database
    if not initialize_db():
        logger.error("Failed to initialize database. Migration aborted.")
        return False
    
    # Migrate users
    if not migrate_users():
        logger.error("User migration failed. Continuing with other migrations...")
    
    # Migrate datasets and buildings
    if not migrate_datasets_and_buildings():
        logger.error("Dataset and building migration failed.")
        return False
    
    # Migrate dataset ownership
    if not migrate_dataset_ownership():
        logger.error("Dataset ownership migration failed.")
    
    logger.info("Migration completed successfully!")
    return True

if __name__ == "__main__":
    run_migration()
