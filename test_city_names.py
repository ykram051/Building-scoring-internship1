import pandas as pd
from io import StringIO, BytesIO
import sys
import os

sys.path.append("app")
from data.data_processing import get_available_cities

# Load and check the current city list to see if we have duplicates
print("Checking current city list...")
cities = get_available_cities()
print(f"Current cities: {cities}")

# Check for case-insensitive duplicates
city_lowercase = [c.lower() for c in cities]
if len(city_lowercase) != len(set(city_lowercase)):
    print("WARNING: Found case-insensitive duplicates!")
    
    # Find the duplicates
    seen = set()
    duplicates = []
    for c in city_lowercase:
        if c in seen:
            duplicates.append(c)
        else:
            seen.add(c)
    print(f"Duplicated cities (lowercase): {duplicates}")
else:
    print("No case-insensitive duplicates found - our fix is working correctly!")

# Check for files with auch in the name
print("\nChecking for properly named output files...")
data_dir = "app/data"
files = os.listdir(data_dir)

# Look for files related to our city
auch_files = [f for f in files if "auch" in f.lower()]
print(f"Found {len(auch_files)} files related to 'auch':")
for f in auch_files:
    print(f"  - {f}")

print("\nVerifying capitalization consistency:")
capitalized_versions = set()
for f in auch_files:
    if "reduced_" in f:
        city_part = f.replace("reduced_", "").replace("_buildings.csv", "")
        city_part = city_part.replace("_buildings_all_years.csv", "")
        city_part = city_part.replace("_buildings_2025.csv", "").replace("_buildings_2026.csv", "")
        capitalized_versions.add(city_part)

print(f"Unique capitalized versions found in filenames: {capitalized_versions}")

# Check the CSV file to see how city names are saved within the data
csv_files = [f for f in auch_files if f.endswith('.csv')]
if csv_files:
    print("\nChecking city column values in CSV files:")
    for f in csv_files[:3]:  # Check just the first few files
        try:
            df = pd.read_csv(os.path.join(data_dir, f))
            if 'city' in df.columns:
                unique_cities = df['city'].unique()
                print(f"  - {f}: city values = {unique_cities}")
        except Exception as e:
            print(f"  - Error reading {f}: {e}")
