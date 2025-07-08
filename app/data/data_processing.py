"""
Unified Data Processing Module

This module provides utilities for processing building-performance datasets from
various sources, including local CSV files and PostgreSQL databases.
"""

import os
import pandas as pd
import numpy as np
import json
import traceback
from datetime import datetime
from pyproj import Transformer
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
import logging
from utils.db import query_to_dataframe, execute_query, dataframe_to_sql

logger = logging.getLogger(__name__)

# Unified function to process city data
def process_city_data(city_name, input_source="csv", input_filename=None, year=None):
    """
    Process building data for a specific city from a specified source.
    Includes automatic fallback if primary source fails.

    Args:
        city_name (str): Name of the city to process.
        input_source (str): Source of the data ('csv' or 'db').
        input_filename (str, optional): Custom input filename (for CSV source).
        year (int, optional): Year to filter data by (for DB source).
    """
    data = None
    
    # Try the primary source first
    if input_source == "csv":
        data = _process_city_data_csv(city_name, input_filename)
    elif input_source == "db":
        data = _process_city_data_db(city_name, year)
    else:
        logger.error(f"Invalid input source: {input_source}")
        return None
        
    # If primary source failed, try the alternative source
    if data is None:
        print(f"Primary source {input_source} failed for {city_name}, trying alternative source...")
        
        if input_source == "csv":
            # CSV failed, try database
            print(f"Trying to load {city_name} from database instead...")
            data = _process_city_data_db(city_name, year)
        elif input_source == "db":
            # Database failed, try CSV
            print(f"Trying to load {city_name} from CSV file instead...")
            data = _process_city_data_csv(city_name, input_filename)
    
    # Return whatever data we could find (might still be None)
    return data

# Private function to process data from CSV
def _process_city_data_csv(city_name, input_filename=None):
    print(f"Processing data for {city_name} from CSV...")

    # Try different possible file locations and formats
    possible_files = []
    
    # Standard csv format
    if input_filename is not None:
        possible_files.append(input_filename)
    
    # Try both lowercase and original case
    possible_files.append(f"{city_name.lower()}.csv")
    possible_files.append(f"{city_name}.csv")
    
    # Try reduced format files in different case variations
    possible_files.append(f"reduced_{city_name.lower()}_buildings.csv")
    possible_files.append(f"reduced_{city_name}_buildings.csv")
    
    # Try with year variants
    from datetime import datetime
    current_year = datetime.now().year
    possible_files.append(f"reduced_{city_name.lower()}_buildings_{current_year}.csv")
    possible_files.append(f"reduced_{city_name}_buildings_{current_year}.csv")
    possible_files.append(f"reduced_{city_name.lower()}_buildings_all_years.csv")
    possible_files.append(f"reduced_{city_name}_buildings_all_years.csv")
    
    # Add data directory path variants
    data_dirs = [
        "",  # Current directory
        "data/",
        "app/data/",
        os.path.join(os.path.dirname(os.path.dirname(__file__)), "data/")
    ]
    
    all_possible_paths = []
    for data_dir in data_dirs:
        for file in possible_files:
            all_possible_paths.append(os.path.join(data_dir, file))
    
    # Try all possible paths
    for file_path in all_possible_paths:
        if os.path.exists(file_path):
            try:
                df = pd.read_csv(file_path)
                print(f"✅ Found and loaded file: {file_path}")
                
                # Check if we need to convert coordinates
                if "coordonnee_cartographique_x_ban" in df.columns and "coordonnee_cartographique_y_ban" in df.columns:
                    # Convert coordinates
                    transformer = Transformer.from_crs("EPSG:2154", "EPSG:4326", always_xy=True)
                    lon, lat = transformer.transform(df["coordonnee_cartographique_x_ban"].values,
                                                    df["coordonnee_cartographique_y_ban"].values)
                    df["longitude"] = lon
                    df["latitude"] = lat
                
                # If we successfully loaded the file, add the city name and return
                df["city"] = city_name
                return df
                
            except Exception as e:
                logger.error(f"Error reading file {file_path}: {e}")
                continue  # Try next file
    
    # If we get here, we couldn't find or read any file
    logger.error(f"Error: No valid data file found for {city_name}!")
    
    # As a last resort, generate a small sample dataset
    print(f"🔧 Generating sample data for {city_name}...")
    df = _generate_sample_data(city_name)
    return df

# Private function to process data from DB
def _process_city_data_db(city_name, year=None):
    print(f"Processing data for {city_name} from DB...")

    try:
        query = """
        SELECT * FROM building_data
        WHERE city = :city_name
        """
        params = {"city_name": city_name}

        if year:
            query += " AND year = :year"
            params["year"] = year

        df = query_to_dataframe(query, params)
        return df
    except Exception as e:
        logger.error(f"Failed to process city data from DB: {e}")
        return None

# Add unified implementation of process_city_with_years
def process_city_with_years(city_name, input_source="csv", input_filename=None, base_year=2024, future_years=None):
    """
    Process city data for multiple years from a specified source.

    Args:
        city_name (str): Name of the city
        input_source (str): Source of the data ('csv' or 'db').
        input_filename (str, optional): Input filename (for CSV source).
        base_year (int): Base year
        future_years (list): List of future years

    Returns:
        DataFrame: Combined multi-year data
    """
    if future_years is None:
        future_years = []

    if input_source == "csv":
        base_df = _process_city_data_csv(city_name, input_filename)
    elif input_source == "db":
        base_df = _process_city_data_db(city_name, base_year)
    else:
        logger.error(f"Invalid input source: {input_source}")
        return None

    if base_df is None:
        logger.error(f"Failed to process base data for {city_name}")
        return None

    all_dfs = [base_df]
    for year in future_years:
        try:
            if input_source == "csv":
                future_df = generate_future_data(base_df, city_name, year)
            else:
                future_df = _process_city_data_db(city_name, year)

            if future_df is not None:
                all_dfs.append(future_df)
        except Exception as e:
            logger.error(f"Error processing data for {city_name} in year {year}: {e}")

    return pd.concat(all_dfs, ignore_index=True)

# Unified implementation of process_uploaded_data moved to line ~475

# Add function to generate synthetic data for future years
def generate_future_data(df, city_name, target_year):
    """
    Generate synthetic data for a future year based on existing data.

    Args:
        df (DataFrame): Source dataframe
        city_name (str): Name of the city
        target_year (int): Target year for synthetic data

    Returns:
        DataFrame: Synthetic data for the target year
    """
    logger.info(f"Generating synthetic data for {city_name}, year {target_year}...")

    # Make a copy of the dataframe
    future_df = df.copy()
    future_df['city'] = city_name
    # Update year
    future_df['year'] = target_year

    # Get the number of buildings
    n_buildings = len(future_df)

    # Generate multipliers for different metrics
    energy_multipliers = draw_multipliers(n_buildings)
    co2_multipliers = draw_multipliers(n_buildings)
    water_multipliers = draw_multipliers(n_buildings)

    # Apply multipliers to core metrics
    if "Energy_Consumption" in future_df.columns:
        future_df["Energy_Consumption"] = future_df["Energy_Consumption"] * energy_multipliers

    if "Energy_Intensity" in future_df.columns:
        future_df["Energy_Intensity"] = future_df["Energy_Intensity"] * energy_multipliers

    if "CO2_Usage" in future_df.columns:
        future_df["CO2_Usage"] = future_df["CO2_Usage"] * co2_multipliers

    if "CO2_Intensity" in future_df.columns:
        future_df["CO2_Intensity"] = future_df["CO2_Intensity"] * co2_multipliers

    if "Water_Usage" in future_df.columns:
        future_df["Water_Usage"] = future_df["Water_Usage"] * water_multipliers

    return future_df

# Add function to generate multipliers for synthetic data
def draw_multipliers(n_buildings, improvement_chance=0.6):
    """
    Generate multipliers for synthetic future data that maintains class distribution
    while allowing for some improvements.

    Args:
        n_buildings (int): Number of buildings
        improvement_chance (float): Chance of improvement vs degradation (0.0 to 1.0)

    Returns:
        numpy.ndarray: Array of multipliers centered around 1.0
    """
    # Start with a base of 1.0 for all buildings
    base = np.ones(n_buildings)

    # Add small random variations for natural fluctuations
    noise = np.random.normal(loc=0, scale=0.02, size=n_buildings)

    # Determine which buildings will improve vs degrade
    improve_mask = np.random.random(size=n_buildings) < improvement_chance
    degrade_mask = ~improve_mask

    # Generate improvements and degradations
    improvements = np.zeros(n_buildings)
    degradations = np.zeros(n_buildings)

    if improve_mask.sum() > 0:
        improvements[improve_mask] = np.random.uniform(0.02, 0.08, size=improve_mask.sum())
    if degrade_mask.sum() > 0:
        degradations[degrade_mask] = np.random.uniform(-0.04, -0.01, size=degrade_mask.sum())

    # Combine all effects
    multipliers = base + noise + improvements + degradations

    # Ensure no negative or extreme values
    multipliers = np.clip(multipliers, 0.85, 1.15)

    return multipliers

# Add load_city_data_db function for database loading
def load_city_data_db(city_name):
    """
    Load city data from the database.
    
    Args:
        city_name (str): Name of the city to load
        
    Returns:
        pd.DataFrame: DataFrame containing the city's building data
    """
    try:
        query = """
        SELECT b.*
        FROM buildings b
        JOIN datasets d ON b.dataset_id = d.id
        WHERE d.city = :city_name
        """
        df = query_to_dataframe(query, {"city_name": city_name})
        
        if df is None or df.empty:
            logger.warning(f"No data found in database for city {city_name}")
            # Try to load from file
            return load_city_data_from_file(city_name)
            
        # Ensure consistent column names
        if "id" in df.columns and "building_id" not in df.columns:
            df = df.rename(columns={"id": "building_id"})
            
        return df
    except Exception as e:
        logger.error(f"Error loading city data from database: {e}")
        return load_city_data_from_file(city_name)
        
def load_city_data_from_file(city_name):
    """
    Load city data from CSV files as a fallback mechanism.
    
    Args:
        city_name (str): Name of the city to load
        
    Returns:
        pd.DataFrame: DataFrame containing the city's building data
    """
    try:
        # Only print debug info in debug mode
        if logger.isEnabledFor(logging.DEBUG):
            print(f"Attempting to load data for city: '{city_name}'")
        
        # Define potential base paths to look for data files
        base_paths = [
            "",  # Current directory
            "data",  # data subdirectory
            "app/data",  # app/data subdirectory
            os.path.join(os.path.dirname(os.path.dirname(__file__)), "data"),  # Absolute path to data dir
            os.path.dirname(os.path.dirname(__file__))  # Absolute path to app dir
        ]
        
        # Different file patterns to try
        file_patterns = [
            f"reduced_{city_name.lower()}_buildings_all_years.csv",  # All years
            f"reduced_{city_name.lower()}_buildings.csv",  # Base file
            f"{city_name.lower()}_buildings.csv",  # Simple naming
            f"{city_name.lower()}.csv"  # Just city name
        ]
        
        # Try year-specific files too
        current_year = datetime.now().year
        file_patterns.insert(1, f"reduced_{city_name.lower()}_buildings_{current_year}.csv")
        
        # User uploads may not have the "reduced_" prefix and "_buildings" suffix
        if not city_name.lower() in ['lyon', 'gordes', 'lille', 'nancy']:
            file_patterns.insert(0, f"{city_name}.csv")  # Try exact filename for user uploads
        
        # Search for files
        for base_path in base_paths:
            for pattern in file_patterns:
                file_path = os.path.join(base_path, pattern) if base_path else pattern
                
                # Only log detailed file searches in debug mode
                if logger.isEnabledFor(logging.DEBUG):
                    print(f"Looking for: {file_path}")
                    
                if os.path.exists(file_path):
                    print(f"✅ Found file: {file_path}")
                    logger.info(f"Loading data for {city_name} from {file_path}")
                    df = pd.read_csv(file_path)
                    # Add city column if not present to help with identification
                    if 'city' not in df.columns:
                        df['city'] = city_name
                    return df
        
        # Try to recreate missing standard datasets
        if city_name.lower() in ["lyon", "lille", "gordes", "nancy"]:
            print(f"⚠️ Could not find {city_name} data, attempting to recreate standard datasets")
            logger.warning(f"Could not find {city_name} data, attempting to recreate standard datasets")
            check_and_recreate_missing_datasets()
            
            # Try one more time with the specified city
            for base_path in base_paths:
                recreated_file = os.path.join(base_path, f"reduced_{city_name.lower()}_buildings_all_years.csv") if base_path else f"reduced_{city_name.lower()}_buildings_all_years.csv"
                if os.path.exists(recreated_file):
                    print(f"✅ Successfully recreated data for {city_name}")
                    logger.info(f"Successfully recreated data for {city_name}")
                    return pd.read_csv(recreated_file)
        
        # Try default cities as a last resort
        for default_city in ["lyon", "lille", "gordes", "nancy"]:
            if default_city.lower() != city_name.lower():
                for base_path in base_paths:
                    default_file = os.path.join(base_path, f"reduced_{default_city.lower()}_buildings_all_years.csv") if base_path else f"reduced_{default_city.lower()}_buildings_all_years.csv"
                    if os.path.exists(default_file):
                        print(f"⚠️ Could not find {city_name} data, falling back to {default_city}")
                        logger.warning(f"Could not find {city_name} data, falling back to {default_city}")
                        return pd.read_csv(default_file)
        
        print(f"❌ Could not find any data files for city: {city_name}")
        logger.error(f"No data files found for city: {city_name}")
        
        # If nothing found, return an empty DataFrame with the expected columns
        return pd.DataFrame(columns=[
            "building_id", "latitude", "longitude", 
            "Energy_Consumption", "CO2_Usage", "Water_Usage",
            "Energy_Intensity", "CO2_Intensity",
            "city", "year"
        ])
        
    except Exception as e:
        print(f"❌ Error loading city data from file: {e}")
        logger.error(f"Error loading city data from file: {e}")
        return None

def get_available_cities():
    """
    Get list of available cities from the database.
    
    Returns:
        list: List of available city names
    """
    # Use a dictionary to track the preferred case version of each city
    # Keys are lowercase city names, values are the preferred capitalized version
    unique_cities = {}
    found_sources = {}  # Track where each city was found to avoid duplicates
    
    # Try database first (these get priority for casing)
    try:
        query = "SELECT DISTINCT city FROM datasets ORDER BY city"
        df = query_to_dataframe(query)
        if df is not None and not df.empty:
            for city in df["city"].tolist():
                city_lower = city.lower()  # Normalize to lowercase for comparison
                unique_cities[city_lower] = city  # Use database casing as preferred
                found_sources[city_lower] = "database"
    except Exception as e:
        if logger.isEnabledFor(logging.DEBUG):  # Only log if debug is enabled
            logger.error(f"Error getting cities from database: {e}")
    
    # Then check filesystem for all datasets regardless of database success
    possible_data_dirs = [
        "data",
        "app/data",
        os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
    ]
    
    for data_dir in possible_data_dirs:
        if not os.path.exists(data_dir):
            continue
            
        try:
            # Look for standard format files
            city_files = [f for f in os.listdir(data_dir) if f.startswith("reduced_") and 
                         (f.endswith("_buildings.csv") or "_buildings_" in f)]
            
            for f in city_files:
                city_name = f.replace("reduced_", "").replace("_buildings.csv", "")
                # Handle year-specific files
                if "_buildings_" in city_name:
                    city_name = city_name.split("_buildings_")[0]
                
                # Add city with proper capitalization and avoid duplicates
                city_lower = city_name.lower()
                if city_lower not in found_sources or found_sources[city_lower] != "database":
                    # Use capitalized version but only if we don't already have one from the database
                    if city_lower not in unique_cities:
                        unique_cities[city_lower] = city_name.capitalize()
                    found_sources[city_lower] = "file"
                
            # Also look for uploaded datasets in user_datasets folder
            user_datasets_dir = os.path.join(data_dir, "user_datasets")
            if os.path.exists(user_datasets_dir):
                ownership_file = os.path.join(user_datasets_dir, "ownership.json")
                if os.path.exists(ownership_file):
                    with open(ownership_file, "r") as f:
                        try:
                            ownership_data = json.load(f)
                            for city_name in ownership_data.keys():
                                city_lower = city_name.lower()
                                # Only add if not already from database (which has priority)
                                if city_lower not in found_sources or found_sources[city_lower] != "database":
                                    if city_lower not in unique_cities:
                                        unique_cities[city_lower] = city_name  # Use ownership casing
                                    found_sources[city_lower] = "ownership"
                        except json.JSONDecodeError:
                            if logger.isEnabledFor(logging.DEBUG):
                                logger.error("Error parsing user datasets ownership file")
            
            # Check for custom uploaded city files - they might just be named after the city
            standard_city_files = ['Lyon.csv', 'Gordes.csv', 'Lille.csv', 'Nancy.csv']
            csv_files = [f for f in os.listdir(data_dir) if f.endswith('.csv') and 
                        not f.startswith('reduced_') and not f in standard_city_files]
            
            for f in csv_files:
                city_name = os.path.splitext(f)[0]  # Remove the .csv extension
                city_lower = city_name.lower()
                
                # Only add if we haven't found this city before or it wasn't in the database
                if city_lower not in found_sources:
                    unique_cities[city_lower] = city_name  # Use file casing
                    found_sources[city_lower] = "custom_file"
                
        except Exception as e:
            if logger.isEnabledFor(logging.DEBUG):  # Only log if debug is enabled
                logger.error(f"Error scanning directory {data_dir}: {e}")
    
    # Return the values from our dictionary, which are the preferred capitalization of each city name
    city_list = sorted(unique_cities.values())
    
    # If we found no cities, return a default list of sample cities
    if not city_list:
        print("No cities found in database or files, providing default city list")
        city_list = ["Lyon", "Paris", "Marseille", "Lille", "Bordeaux", "Strasbourg", 
                     "Nancy", "Toulouse", "Nice", "Rennes", "Auch"]
    
    # Always ensure that Auch and Ciry_le_noble are available for testing
    if "Auch" not in city_list and "auch" not in city_list:
        city_list.append("Auch")
    
    if "Ciry_le_noble" not in city_list and "ciry_le_noble" not in city_list:
        city_list.append("Ciry_le_noble")
        
    return sorted(city_list)

def get_available_years_for_city(city_name):
    """
    Get list of available years for a city from the database.
    
    Args:
        city_name (str): Name of the city
        
    Returns:
        list: List of available years for the city
    """
    try:
        query = """
        SELECT DISTINCT year 
        FROM buildings b
        JOIN datasets d ON b.dataset_id = d.id
        WHERE d.city = :city_name
        ORDER BY year
        """
        df = query_to_dataframe(query, {"city_name": city_name})
        if df is not None and not df.empty:
            return df["year"].tolist()
        else:
            return [datetime.now().year]  # Default to current year
    except Exception as e:
        logger.error(f"Error getting available years: {e}")
        return [datetime.now().year]  # Default to current year

def get_city_dataset_id(city_name):
    """
    Get dataset ID for a city from the database.
    
    Args:
        city_name (str): Name of the city
        
    Returns:
        int: Dataset ID for the city
    """
    try:
        query = "SELECT id FROM datasets WHERE city = :city_name LIMIT 1"
        df = query_to_dataframe(query, {"city_name": city_name})
        if df is not None and not df.empty:
            return df["id"].iloc[0]
        else:
            return None
    except Exception as e:
        logger.error(f"Error getting dataset ID: {e}")
        return None

def get_buildings_for_city(city_name, year=None):
    """
    Get buildings for a city from the database, optionally filtered by year.
    
    Args:
        city_name (str): Name of the city
        year (int, optional): Year to filter by
        
    Returns:
        pd.DataFrame: DataFrame containing the city's building data
    """
    try:
        if year:
            query = """
            SELECT b.*
            FROM buildings b
            JOIN datasets d ON b.dataset_id = d.id
            WHERE d.city = :city_name AND b.year = :year
            """
            df = query_to_dataframe(query, {"city_name": city_name, "year": year})
        else:
            query = """
            SELECT b.*
            FROM buildings b
            JOIN datasets d ON b.dataset_id = d.id
            WHERE d.city = :city_name
            """
            df = query_to_dataframe(query, {"city_name": city_name})
        
        if df is None or df.empty:
            logger.warning(f"No data found in database for city {city_name}")
            return None
            
        # Ensure consistent column names
        if "id" in df.columns and "building_id" not in df.columns:
            df = df.rename(columns={"id": "building_id"})
            
        return df
    except Exception as e:
        logger.error(f"Error loading buildings: {e}")
        return None

def process_uploaded_data(uploaded_file, username=None):
    """
    Process an uploaded CSV file with flexible column handling.
    Uses the same processing logic as process_city_data to ensure consistency.
    Optimized for speed and reduced logging.
    
    Args:
        uploaded_file: File-like object from Streamlit file_uploader
        username: Username who uploaded the file
    
    Returns:
        tuple: (processed_dataframe, city_name)
    """
    import pandas as pd
    import numpy as np
    from datetime import datetime
    import os
    import streamlit as st
    
    # Log start at INFO level
    logger.info(f"Processing uploaded file: {uploaded_file.name}")
    
    try:
        # Use streamlit progress indicator
        progress_text = "Processing your dataset..."
        progress_bar = st.progress(0, text=progress_text)
        
        # Read CSV data
        df = pd.read_csv(uploaded_file)
        progress_bar.progress(5, text=f"{progress_text} (Loaded {len(df)} rows)")
        
        # Determine city name
        original_name = os.path.splitext(uploaded_file.name)[0]
        existing_cities = get_available_cities()
        city_lower = original_name.lower()
        
        # Check for existing city names with same case-insensitive name
        existing_match = next((city for city in existing_cities if city.lower() == city_lower), None)
        
        if existing_match:
            city_name = existing_match
        else:
            # Normalize new city name
            city_name = ' '.join(word.capitalize() for word in original_name.strip().split())
            city_name = city_name.replace(" ", "_").replace("-", "_")
            city_name = ''.join(c for c in city_name if c.isalnum() or c == '_')
        
        progress_bar.progress(10, text=f"{progress_text} (Using city name: {city_name})")
        
        # Create a copy to avoid modifying the original
        df_processed = df.copy()
        
        # Update progress
        progress_bar.progress(15, text=f"{progress_text} (Preprocessing data)")
        
        # Step 1: Handle building_id
        if "building_id" not in df_processed.columns:
            if "numero_dpe" in df_processed.columns:
                df_processed["building_id"] = df_processed["numero_dpe"]
            else:
                # Generate building IDs in vectorized operation
                df_processed["building_id"] = [f"BLD{i+1:06d}" for i in range(len(df_processed))]
        
        # Step 2: Rename columns - consolidated and vectorized where possible
        rename_map = {
            "numero_dpe": "building_id",
            "conso_5 usages_ef": "Energy_Consumption",
            "conso_5_usages_ef": "Energy_Consumption",
            "emission_ges_5_usages": "CO2_Usage",
            "etiquette_dpe": "true_energy_label",
            "etiquette_ges": "true_ges_label",
            "conso_5 usages_par_m2_ef": "Energy_Intensity",
            "conso_5_usages_par_m2_ef": "Energy_Intensity",
            "emission_ges_5_usages par_m2": "CO2_Intensity",
            "emission_ges_5_usages_par_m2": "CO2_Intensity"
        }
        
        # Apply renaming only for columns that exist
        existing_rename = {k: v for k, v in rename_map.items() if k in df_processed.columns}
        if existing_rename:
            df_processed = df_processed.rename(columns=existing_rename)
        
        # Update progress
        progress_bar.progress(25, text=f"{progress_text} (Adding missing columns)")
        
        # Step 3: Handle required columns - all at once with minimal logging
        # Set up a generator for random values - more efficient
        n_rows = len(df_processed)
        
        # Generate missing core metrics in one block
        if "Energy_Consumption" not in df_processed.columns:
            df_processed["Energy_Consumption"] = np.random.uniform(1000, 10000, n_rows)
            
        if "CO2_Usage" not in df_processed.columns:
            df_processed["CO2_Usage"] = df_processed["Energy_Consumption"] * np.random.uniform(0.1, 0.3, n_rows)
            
        if "Water_Usage" not in df_processed.columns:
            df_processed["Water_Usage"] = df_processed["Energy_Consumption"] * 0.3
            
        if "Energy_Intensity" not in df_processed.columns:
            df_processed["Energy_Intensity"] = np.random.uniform(50, 300, n_rows)
            
        if "CO2_Intensity" not in df_processed.columns:
            df_processed["CO2_Intensity"] = df_processed["Energy_Intensity"] * np.random.uniform(0.1, 0.3, n_rows)
        
        # Update progress
        progress_bar.progress(40, text=f"{progress_text} (Processing coordinates)")
        
        # Step 4: Use the optimized coordinate conversion function
        df_processed = convert_coordinates(df_processed)
        
        # Update progress
        progress_bar.progress(60, text=f"{progress_text} (Adding derived columns)")
        
        # Step 5: Add log-transformed features for numeric columns
        numeric_cols = ["Energy_Consumption", "CO2_Usage", "Energy_Intensity", "CO2_Intensity"]
        existing_numeric = [col for col in numeric_cols if col in df_processed.columns]
        
        # Create log transformations in one batch operation
        for col in existing_numeric:
            df_processed[f"log1p_{col}"] = np.log1p(df_processed[col])
        
        # Step 6: Add city and year tags
        current_year = datetime.now().year
        df_processed['city'] = city_name
        df_processed['year'] = current_year
        
        # Update progress
        progress_bar.progress(70, text=f"{progress_text} (Finalizing dataset)")
        
        # Step 7: Select final columns in the same order as in process_city_data
        final_cols = [
            # Primary key & location
            "building_id", "latitude", "longitude",
            # Core performance metrics
            "Energy_Consumption", "CO2_Usage", "Water_Usage", 
            "Energy_Intensity", "CO2_Intensity",
            # Official DPE labels
            "true_energy_label", "true_ges_label",
            # BAN address fields (normalized)
            "adresse_ban", "numero_voie_ban", "nom_rue_ban", 
            "code_postal_ban", "nom_commune_ban", "identifiant_ban",
            # Raw-fallback address fields
            "adresse_brut", "nom_commune_brut", "code_postal_brut",
            # Basic building attributes for filters
            "annee_construction", "surface_habitable_immeuble",
            # Log transformed columns
            *[f"log1p_{col}" for col in existing_numeric],
            # City and year identifiers
            "city", "year"
        ]
        
        # Filter only columns that exist
        available_cols = [col for col in final_cols if col in df_processed.columns]
        
        # Ensure required columns always exist
        required = [
            "building_id", "Energy_Consumption", "CO2_Usage", "Water_Usage", 
            "Energy_Intensity", "CO2_Intensity", "latitude", "longitude",
            "city", "year"
        ]
        
        # Final check for any missing required columns
        for col in required:
            if col not in df_processed.columns:
                if col in ["latitude", "longitude"]:
                    df_processed["latitude"] = np.random.uniform(43.0, 51.0, n_rows)
                    df_processed["longitude"] = np.random.uniform(0.0, 8.0, n_rows)
                elif col in ["Energy_Consumption", "Energy_Intensity"]:
                    df_processed[col] = np.random.uniform(50, 300, n_rows)
                elif col in ["CO2_Usage", "CO2_Intensity"]:
                    df_processed[col] = np.random.uniform(5, 30, n_rows)
                elif col == "Water_Usage":
                    df_processed[col] = np.random.uniform(300, 3000, n_rows)
                else:
                    df_processed[col] = f"Unknown_{col}"
        
        # Select columns and drop rows with missing values in required columns
        df_clean = df_processed[available_cols].dropna(subset=required)
        
        # Update progress
        progress_bar.progress(80, text=f"{progress_text} (Saving files)")
        
        # Save processed files - with minimal logging
        os.makedirs("data", exist_ok=True)
        
        # Define output filenames
        base_output = f"reduced_{city_name.lower()}_buildings.csv"
        year_output = f"reduced_{city_name.lower()}_buildings_{current_year}.csv"
        all_years_output = f"reduced_{city_name.lower()}_buildings_all_years.csv"
        simple_output = f"{city_name}.csv"
        
        # Save all formats (essential for compatibility)
        df_clean.to_csv(os.path.join("data", base_output), index=False)
        df_clean.to_csv(os.path.join("data", year_output), index=False)
        df_clean.to_csv(os.path.join("data", simple_output), index=False)
        
        # Update progress
        progress_bar.progress(85, text=f"{progress_text} (Generating future data)")
        
        # Generate future data more efficiently
        try:
            future_year = current_year + 1
            
            # Define vectorized helper function for generating multipliers
            def generate_future_data(df, future_year):
                """Generate future data more efficiently with vectorized operations"""
                future_df = df.copy()
                future_df['year'] = future_year
                
                n_buildings = len(future_df)
                
                # Generate scenarios and multipliers in one go
                scenarios = np.random.choice(["normal", "uniform", "lognormal"], 
                                          size=n_buildings, p=[0.6, 0.3, 0.1])
                
                # Pre-generate all multipliers at once
                multipliers = np.zeros(n_buildings)
                
                # Normal distribution (60% of buildings)
                normal_mask = scenarios == "normal"
                multipliers[normal_mask] = np.random.normal(loc=1.0, scale=0.05, size=normal_mask.sum())
                
                # Uniform distribution (30% of buildings)
                uniform_mask = scenarios == "uniform"
                multipliers[uniform_mask] = np.random.uniform(0.9, 1.1, size=uniform_mask.sum())
                
                # Lognormal distribution (10% of buildings)
                lognormal_mask = scenarios == "lognormal"
                multipliers[lognormal_mask] = np.random.lognormal(mean=0, sigma=0.1, size=lognormal_mask.sum())
                
                # Apply multipliers to core metrics
                for col in ["Energy_Consumption", "Energy_Intensity"]:
                    if col in future_df.columns:
                        future_df[col] *= multipliers
                        
                for col in ["CO2_Usage", "CO2_Intensity"]:
                    if col in future_df.columns:
                        # Generate different multipliers for CO2
                        co2_multipliers = np.random.normal(loc=1.0, scale=0.05, size=n_buildings)
                        future_df[col] *= co2_multipliers
                
                if "Water_Usage" in future_df.columns:
                    # Generate different multipliers for water
                    water_multipliers = np.random.normal(loc=1.0, scale=0.05, size=n_buildings)
                    future_df["Water_Usage"] *= water_multipliers
                
                # Re-calculate log transformations
                for col in existing_numeric:
                    log_col = f"log1p_{col}"
                    if log_col in future_df.columns:
                        future_df[log_col] = np.log1p(future_df[col])
                
                return future_df
            
            # Generate future data in one function call
            future_df = generate_future_data(df_clean, future_year)
            
            # Save future year data
            future_output = f"reduced_{city_name.lower()}_buildings_{future_year}.csv"
            future_df.to_csv(os.path.join("data", future_output), index=False)
            
            # Combine current and future years
            all_years_df = pd.concat([df_clean, future_df], ignore_index=True)
            all_years_df.to_csv(os.path.join("data", all_years_output), index=False)
            
        except Exception as e:
            logger.warning(f"Could not generate future data: {str(e)}")
            # Continue processing - this is non-critical
        
        # Update progress
        progress_bar.progress(90, text=f"{progress_text} (Saving to database)")
        
        # Try to save to database
        try:
            if username:
                # Create dataset entry
                from utils.db import dataframe_to_sql, execute_query
                result = execute_query("""
                    INSERT INTO datasets (name, city, owner, created_at)
                    VALUES (%s, %s, %s, %s) RETURNING id
                """, (city_name, city_name, username, datetime.now().isoformat()), fetch=True)
                
                if result and result[0]:
                    dataset_id = result[0][0]
                    df_clean["dataset_id"] = dataset_id
                    
                    # Save to database
                    dataframe_to_sql(df_clean, "buildings")
                    logger.info(f"Saved {len(df_clean)} rows to database for dataset {dataset_id}")
        except Exception as e:
            logger.warning(f"Could not save to database: {str(e)}")
            # Continue with file-based approach
        
        # Complete the progress bar
        progress_bar.progress(100, text="Dataset processing complete!")
        
        # Log completion
        logger.info(f"Successfully processed dataset '{city_name}' with {len(df_clean)} rows")
        return df_clean, city_name
        
    except Exception as e:
        # Clean up the progress bar on error
        if 'progress_bar' in locals():
            progress_bar.progress(100, text="Error processing dataset")
            
        logger.error(f"Error processing uploaded data: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return None, None

def process_city_with_years(city_name, input_filename, base_year=None, future_years=None):
    """
    Process city data and generate predictions for future years.
    
    Args:
        city_name (str): Name of the city
        input_filename (str): Input filename for the data
        base_year (int, optional): Base year for the data
        future_years (list, optional): List of future years to generate predictions for
        
    Returns:
        pd.DataFrame: DataFrame containing the city's building data for all years
    """
    try:
        # Default values
        if base_year is None:
            base_year = datetime.now().year
        
        if future_years is None:
            future_years = [base_year + 1]
        
        # Read the input file
        df = pd.read_csv(input_filename)
        
        # Add year column if missing
        if "year" not in df.columns:
            df["year"] = base_year
        
        # Make copies for future years with simulated changes
        dfs = [df.copy()]  # Include original data
        
        for year in future_years:
            if year != base_year:
                future_df = df.copy()
                future_df["year"] = year
                
                # Simulate changes (e.g., 2-5% improvement in key metrics)
                improvement = np.random.uniform(0.02, 0.05)  # 2-5% improvement
                
                # Apply improvements to key metrics
                for col in ["Energy_Consumption", "CO2_Usage", "Water_Usage"]:
                    if col in future_df.columns:
                        future_df[col] = future_df[col] * (1 - improvement)
                
                dfs.append(future_df)
        
        # Combine all years
        combined_df = pd.concat(dfs, ignore_index=True)
        
        # Save to database if available
        try:
            # Get or create dataset in DB
            dataset_id = get_city_dataset_id(city_name)
            
            if not dataset_id:
                # Create new dataset
                query = """
                INSERT INTO datasets (name, city, owner, created_at)
                VALUES (:name, :city, :owner, :created_at)
                RETURNING id
                """
                result = execute_query(query, {
                    "name": city_name,
                    "city": city_name,
                    "owner": "system",  # Default owner for system-generated data
                    "created_at": datetime.now().isoformat()
                }, fetch=True)
                
                if result and result[0]:
                    dataset_id = result[0][0]
            
            if dataset_id:
                # Add dataset_id to dataframe
                combined_df["dataset_id"] = dataset_id
                
                # Save to database
                dataframe_to_sql(combined_df, "buildings")
        except Exception as e:
            logger.error(f"Error saving city data with years to database: {e}")
        
        return combined_df
    
    except Exception as e:
        logger.error(f"Error processing city with years: {e}")
        return None

def delete_dataset(city_name, username=None):
    """
    Delete a dataset completely from both filesystem and database.
    
    Args:
        city_name (str): Name of the city/dataset to delete
        username (str, optional): Username requesting the deletion (for permission checking)
    
    Returns:
        tuple: (success, message) where success is a boolean and message describes the result
    """
    import os
    import glob
    import shutil
    
    logger.info(f"Attempting to delete dataset: {city_name}")
    print(f"Attempting to delete dataset: {city_name}")
    
    success = True
    message = ""
    errors = []
    
    # 1. Check if this is a built-in dataset that shouldn't be deleted
    protected_datasets = ["lyon", "lille", "gordes", "nancy"]
    if city_name.lower() in protected_datasets:
        logger.warning(f"Cannot delete protected dataset: {city_name}")
        return False, f"'{city_name}' is a built-in dataset and cannot be deleted."
    
    # 2. Delete from database if connected
    try:
        # First get the dataset ID
        dataset_id = get_city_dataset_id(city_name)
        
        if dataset_id:
            # Delete from buildings table
            execute_query(
                "DELETE FROM buildings WHERE dataset_id = :dataset_id",
                {"dataset_id": dataset_id}
            )
            logger.info(f"Deleted buildings with dataset_id={dataset_id}")
            print(f"Deleted buildings with dataset_id={dataset_id}")
            
            # Delete from datasets table
            execute_query(
                "DELETE FROM datasets WHERE id = :dataset_id",
                {"dataset_id": dataset_id}
            )
            logger.info(f"Deleted dataset with id={dataset_id}")
            print(f"Deleted dataset with id={dataset_id}")
            
            message += f"Deleted dataset from database. "
        else:
            logger.info(f"No database entry found for dataset: {city_name}")
            print(f"No database entry found for dataset: {city_name}")
    except Exception as e:
        logger.error(f"Error deleting from database: {e}")
        print(f"Error deleting from database: {e}")
        errors.append(f"Database error: {str(e)}")
        success = False
    
    # 3. Delete from filesystem
    try:
        # Define data directory paths to check
        data_dirs = [
            "data",
            "app/data",
            os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
        ]
        
        files_deleted = 0
        # Search for all related files across possible directories
        for data_dir in data_dirs:
            if not os.path.exists(data_dir):
                continue
                
            # File patterns to search for
            file_patterns = [
                f"{city_name}.csv",
                f"reduced_{city_name.lower()}_buildings.csv",
                f"reduced_{city_name.lower()}_buildings_*.csv",
                f"reduced_{city_name.lower()}_buildings_all_years.csv"
            ]
            
            # Find and delete matching files
            for pattern in file_patterns:
                file_path = os.path.join(data_dir, pattern)
                matching_files = glob.glob(file_path)
                
                for file in matching_files:
                    try:
                        os.remove(file)
                        files_deleted += 1
                        logger.info(f"Deleted file: {file}")
                        print(f"Deleted file: {file}")
                    except Exception as e:
                        logger.error(f"Error deleting file {file}: {e}")
                        print(f"Error deleting file {file}: {e}")
                        errors.append(f"File error: {str(e)}")
                        success = False
        
        # 4. Check ownership JSON and remove entry if exists
        try:
            for data_dir in data_dirs:
                user_datasets_dir = os.path.join(data_dir, "user_datasets")
                ownership_file = os.path.join(user_datasets_dir, "ownership.json")
                
                if os.path.exists(ownership_file):
                    try:
                        # Load ownership data
                        with open(ownership_file, "r") as f:
                            ownership_data = json.load(f)
                        
                        # Remove entry if exists
                        if city_name in ownership_data:
                            del ownership_data[city_name]
                            logger.info(f"Removed {city_name} from ownership records")
                            print(f"Removed {city_name} from ownership records")
                            
                            # Save updated ownership data
                            with open(ownership_file, "w") as f:
                                json.dump(ownership_data, f, indent=2)
                    except Exception as e:
                        logger.error(f"Error updating ownership data: {e}")
                        print(f"Error updating ownership data: {e}")
                        errors.append(f"Ownership record error: {str(e)}")
        except Exception as e:
            logger.error(f"Error checking ownership records: {e}")
            print(f"Error checking ownership records: {e}")
            
        message += f"Deleted {files_deleted} file(s) from filesystem."
        
    except Exception as e:
        logger.error(f"Error in filesystem deletion: {e}")
        print(f"Error in filesystem deletion: {e}")
        errors.append(f"File system error: {str(e)}")
        success = False
    
    # 5. Final status message
    if success:
        logger.info(f"Successfully deleted dataset: {city_name}")
        return True, message
    else:
        error_msg = f"Encountered errors while deleting {city_name}: {'; '.join(errors)}"
        logger.warning(error_msg)
        return False, error_msg

def check_and_recreate_missing_datasets():
    """
    Check for required datasets and recreate them if they're missing.
    This is helpful when users are running into "Could not find default dataset" errors.
    """
    import os
    
    # Define the standard datasets that should always be available
    standard_cities = ["lyon", "lille", "gordes", "nancy"]
    
    # Define data directory paths to check
    data_dirs = [
        "data",
        "app/data",
        os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
    ]
    
    # Find a valid data directory
    data_dir = None
    for dir_path in data_dirs:
        if os.path.exists(dir_path) and os.path.isdir(dir_path):
            data_dir = dir_path
            break
    
    if data_dir is None:
        logger.error("Could not find a valid data directory")
        print("Could not find a valid data directory")
        return False
    
    missing_cities = []
    
    # Check which cities are missing their 'all_years' file
    for city in standard_cities:
        all_years_file = os.path.join(data_dir, f"reduced_{city.lower()}_buildings_all_years.csv")
        if not os.path.exists(all_years_file):
            missing_cities.append(city)
    
    if not missing_cities:
        print("All standard datasets are available")
        return True
    
    # Let's try to recreate the missing datasets with sample data
    for city in missing_cities:
        try:
            print(f"Creating sample data for {city}...")
            
            # Create basic sample data with 5 buildings for current year and next year
            current_year = datetime.now().year
            next_year = current_year + 1
            
            # Define coordinates based on city
            if city.lower() == "lyon":
                lat_base, lon_base = 45.76, 4.84
                prefix = "LYN"
            elif city.lower() == "lille":
                lat_base, lon_base = 50.63, 3.07
                prefix = "LIL"
            elif city.lower() == "gordes":
                lat_base, lon_base = 43.91, 5.20
                prefix = "GOR"
            elif city.lower() == "nancy":
                lat_base, lon_base = 48.69, 6.18
                prefix = "NAN"
            else:
                lat_base, lon_base = 48.85, 2.35  # Paris coordinates as fallback
                prefix = "BLD"
            
            # Create sample data for current year
            current_year_data = []
            for i in range(5):
                building = {
                    "building_id": f"{prefix}{i+1:06d}",
                    "latitude": lat_base + i * 0.001,
                    "longitude": lon_base + i * 0.001,
                    "Energy_Consumption": 5000 + i * 200 + np.random.randint(-100, 100),
                    "CO2_Usage": 500 + i * 20 + np.random.randint(-10, 10),
                    "Water_Usage": 1500 + i * 60 + np.random.randint(-30, 30),
                    "Energy_Intensity": 150 + i * 5 + np.random.randint(-5, 5),
                    "CO2_Intensity": 15 + i * 0.5 + np.random.uniform(-0.5, 0.5),
                    "city": city.capitalize(),
                    "year": current_year
                }
                current_year_data.append(building)
            
            # Create sample data for next year with slight improvements
            next_year_data = []
            for i in range(5):
                # Copy from current year and apply a small improvement
                building = dict(current_year_data[i])
                building["year"] = next_year
                building["Energy_Consumption"] *= 0.95  # 5% improvement
                building["CO2_Usage"] *= 0.95
                building["Water_Usage"] *= 0.95
                building["Energy_Intensity"] *= 0.95
                building["CO2_Intensity"] *= 0.95
                next_year_data.append(building)
            
            # Combine data for both years
            all_data = current_year_data + next_year_data
            
            # Convert to DataFrame
            df = pd.DataFrame(all_data)
            
            # Save files
            base_file = os.path.join(data_dir, f"reduced_{city.lower()}_buildings.csv")
            year_file = os.path.join(data_dir, f"reduced_{city.lower()}_buildings_{current_year}.csv")
            all_years_file = os.path.join(data_dir, f"reduced_{city.lower()}_buildings_all_years.csv")
            simple_file = os.path.join(data_dir, f"{city.capitalize()}.csv")
            
            # Save current year data
            pd.DataFrame(current_year_data).to_csv(base_file, index=False)
            pd.DataFrame(current_year_data).to_csv(year_file, index=False)
            
            # Save all years data
            df.to_csv(all_years_file, index=False)
            
            # Save simple named file
            pd.DataFrame(current_year_data).to_csv(simple_file, index=False)
            
            print(f"✅ Created sample data files for {city}")
            logger.info(f"Created sample data files for {city}")
            
        except Exception as e:
            print(f"❌ Error creating sample data for {city}: {e}")
            logger.error(f"Error creating sample data for {city}: {e}")
    
    print("✅ Finished checking and recreating missing datasets")
    return True

def _generate_sample_data(city_name):
    """
    Generate sample building data for a city when no data file is found.
    This ensures we always have some data to display.
    
    Args:
        city_name (str): Name of the city
        
    Returns:
        pd.DataFrame: Sample building data
    """
    import numpy as np
    from datetime import datetime
    
    print(f"Generating sample data for {city_name}")
    
    # Number of buildings to generate
    num_buildings = 50
    current_year = datetime.now().year
    
    # Generate building IDs
    building_ids = [f"{city_name[:3].upper()}_SAMPLE_{i:03d}" for i in range(1, num_buildings + 1)]
    
    # Generate random latitudes and longitudes for France
    # Approximate bounding box for France
    lat_min, lat_max = 42.0, 51.0
    lon_min, lon_max = -5.0, 9.0
    
    # Create random coordinates within France
    latitudes = np.random.uniform(lat_min, lat_max, num_buildings)
    longitudes = np.random.uniform(lon_min, lon_max, num_buildings)
    
    # Generate random energy consumption, CO2 usage, and water usage
    # with reasonable distributions for buildings
    energy_consumption = np.random.lognormal(mean=10, sigma=1, size=num_buildings)
    co2_usage = energy_consumption * np.random.uniform(0.1, 0.3, num_buildings)
    water_usage = np.random.lognormal(mean=8, sigma=1.2, size=num_buildings)
    
    # Calculate energy intensity based on random building areas
    building_areas = np.random.uniform(50, 500, num_buildings)
    energy_intensity = energy_consumption / building_areas
    co2_intensity = co2_usage / building_areas
    
    # Generate classes A through G with decreasing probability
    class_weights = [0.05, 0.1, 0.15, 0.3, 0.2, 0.1, 0.1]  # A through G
    classes = np.random.choice(["A", "B", "C", "D", "E", "F", "G"], size=num_buildings, p=class_weights)
    
    # Create DataFrame with all the columns we need
    df = pd.DataFrame({
        "building_id": building_ids,
        "latitude": latitudes,
        "longitude": longitudes,
        "Energy_Consumption": energy_consumption,
        "CO2_Usage": co2_usage,
        "Water_Usage": water_usage,
        "Energy_Intensity": energy_intensity,
        "CO2_Intensity": co2_intensity,
        "year": current_year,
        "city": city_name,
        "address": [f"Sample Address {i}, {city_name}" for i in range(1, num_buildings + 1)],
        "building_type": np.random.choice(["Residential", "Commercial", "Industrial", "Public"], size=num_buildings),
        "construction_year": np.random.randint(1900, 2020, size=num_buildings),
        "class_label": classes,
        "class_cosine": classes,
        "class_mahalanobis": classes,
        "class_pca": classes,
        "class_weighted": classes,
        "class_tree": classes,
        "class_topsis": classes
    })
    
    print(f"✅ Generated sample data with {num_buildings} buildings for {city_name}")
    
    # Save the sample data to file for future use
    try:
        data_dir = os.path.dirname(__file__)
        sample_filename = os.path.join(data_dir, f"sample_{city_name.lower()}.csv")
        df.to_csv(sample_filename, index=False)
        print(f"✅ Saved sample data to {sample_filename}")
    except Exception as e:
        print(f"⚠️ Could not save sample data: {e}")
    
    return df

def convert_coordinates(df):
    """
    Optimized utility function to convert coordinates from various formats to lat/long.
    Tries multiple common coordinate formats and falls back to random coordinates if needed.
    Uses vectorized operations for better performance.
    
    Args:
        df: DataFrame containing coordinate data in some format
        
    Returns:
        DataFrame with latitude/longitude columns added
    """
    # If latitude and longitude already exist, return as-is
    if "latitude" in df.columns and "longitude" in df.columns:
        return df
        
    # Clone the dataframe to avoid modifying the original
    df = df.copy()
    
    try:
        # Try to identify coordinate columns in priority order
        if "coordonnee_cartographique_x_ban" in df.columns and "coordonnee_cartographique_y_ban" in df.columns:
            # French BAN coordinates (Lambert-93)
            x_col, y_col = "coordonnee_cartographique_x_ban", "coordonnee_cartographique_y_ban"
            from_crs = "EPSG:2154"  # Lambert-93
        elif any(c for c in df.columns if c.lower() == 'x' or '_x' in c.lower() or 'x_' in c.lower()) and \
             any(c for c in df.columns if c.lower() == 'y' or '_y' in c.lower() or 'y_' in c.lower()):
            # Generic X/Y coordinates - find the first matching pair
            x_cols = [c for c in df.columns if c.lower() == 'x' or '_x' in c.lower() or 'x_' in c.lower()]
            y_cols = [c for c in df.columns if c.lower() == 'y' or '_y' in c.lower() or 'y_' in c.lower()]
            x_col, y_col = x_cols[0], y_cols[0]
            from_crs = "EPSG:2154"  # Assume French Lambert-93 by default
        else:
            # No recognizable coordinate columns
            raise ValueError("No coordinate columns found")
            
        # Check if coordinates are valid numbers
        if not pd.api.types.is_numeric_dtype(df[x_col]) or not pd.api.types.is_numeric_dtype(df[y_col]):
            # Try to convert to numeric if possible
            df[x_col] = pd.to_numeric(df[x_col], errors='coerce')
            df[y_col] = pd.to_numeric(df[y_col], errors='coerce')
            
            # If conversion failed and we have too many NaNs, raise an error
            if df[x_col].isna().sum() > 0.5 * len(df) or df[y_col].isna().sum() > 0.5 * len(df):
                raise ValueError(f"Coordinates in {x_col}/{y_col} cannot be converted to numbers")
                
        # Convert coordinates using pyproj
        from pyproj import Transformer
        transformer = Transformer.from_crs(from_crs, "EPSG:4326", always_xy=True)
            
        # Use mask to handle NaN values in coordinate columns
        valid_mask = ~df[x_col].isna() & ~df[y_col].isna()
        
        # Initialize lat/long columns with NaN
        df["longitude"] = np.nan
        df["latitude"] = np.nan
        
        if valid_mask.any():
            # Only transform valid coordinates
            lon, lat = transformer.transform(
                df.loc[valid_mask, x_col].values,
                df.loc[valid_mask, y_col].values
            )
            df.loc[valid_mask, "longitude"] = lon
            df.loc[valid_mask, "latitude"] = lat
            
            # Generate random coordinates only for rows with invalid original coordinates
            n_invalid = (~valid_mask).sum()
            if n_invalid > 0:
                df.loc[~valid_mask, "latitude"] = np.random.uniform(43.0, 51.0, n_invalid)
                df.loc[~valid_mask, "longitude"] = np.random.uniform(0.0, 8.0, n_invalid)
        else:
            raise ValueError("No valid coordinates found")
            
        # Validate the results are in sensible range for France
        valid_lat = (df["latitude"] >= 41.0) & (df["latitude"] <= 52.0)
        valid_lon = (df["longitude"] >= -5.0) & (df["longitude"] <= 10.0)
        invalid_coords = ~(valid_lat & valid_lon)
        
        # Generate random coordinates for any implausible values
        if invalid_coords.any():
            n_invalid = invalid_coords.sum()
            df.loc[invalid_coords, "latitude"] = np.random.uniform(43.0, 51.0, n_invalid)
            df.loc[invalid_coords, "longitude"] = np.random.uniform(0.0, 8.0, n_invalid)
            
        return df
        
    except Exception as e:
        # Generate random coordinates for all rows as a last resort
        n_rows = len(df)
        df["latitude"] = np.random.uniform(43.0, 51.0, n_rows)
        df["longitude"] = np.random.uniform(0.0, 8.0, n_rows)
        logger.warning(f"Using random coordinates: {str(e)}")
        return df
