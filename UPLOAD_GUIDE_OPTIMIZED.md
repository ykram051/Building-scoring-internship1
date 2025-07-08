# Dataset Upload Guide

## Optimized Upload Process

The dataset upload process has been optimized to provide a better user experience. Here's what to expect when uploading datasets:

### What Happens When You Upload a Dataset

1. **Initial Processing**: The system reads your CSV file and performs basic validation.

2. **Progress Tracking**: A progress bar shows you exactly where your upload is in the process:
   - Loading data
   - Processing city name
   - Adding required columns
   - Converting coordinates
   - Generating derived metrics
   - Saving files
   - Creating future projections
   - Saving to database

3. **Automatic Data Enhancement**: The system will automatically:
   - Generate building IDs if missing
   - Convert coordinates to latitude/longitude
   - Calculate performance metrics if missing
   - Create future year projections
   - Save data in multiple formats for compatibility

4. **Feedback**: You'll receive clear messages about:
   - Upload progress
   - Any issues encountered
   - Successful completion

### Tips for Faster Uploads

1. **Prepare Your Data**: Make sure your CSV file is well-formatted with:
   - A header row with column names
   - Building identifiers (if possible)
   - Energy and emissions data
   - Location data (coordinates or address)

2. **Optimize File Size**: For very large datasets:
   - Remove unnecessary columns before uploading
   - Consider splitting very large files (>100MB) into smaller chunks
   - Compress data if possible (remove duplicate entries)

3. **Name Your Files Properly**: Use the city name as the filename (e.g., "Paris.csv")
   - Use simple alphanumeric names
   - Avoid special characters
   - Use underscores instead of spaces

### Required and Optional Columns

#### Core Required Columns
The system will generate these if missing:

- `building_id`: Unique identifier for each building
- `Energy_Consumption`: Total energy consumption
- `CO2_Usage`: Carbon emissions 
- `Water_Usage`: Water consumption
- `Energy_Intensity`: Energy use per square meter
- `CO2_Intensity`: Emissions per square meter
- `latitude` & `longitude`: Geographic coordinates

#### Supported Coordinate Formats

The system can convert these coordinate formats:

1. French BAN format:
   - `coordonnee_cartographique_x_ban`
   - `coordonnee_cartographique_y_ban`

2. Generic X/Y coordinates:
   - Columns containing 'x'/'y' in their names
   - Lambert-93 projection (EPSG:2154) is assumed

If no coordinates are found, random coordinates will be generated.

#### Other Useful Columns

These enhance analytics but aren't required:

- `true_energy_label`: Official energy rating (A-G)
- `true_ges_label`: Official emissions rating (A-G)
- `adresse_ban`: Full address
- `code_postal_ban`: Postal code
- `nom_commune_ban`: City/commune name
- `annee_construction`: Year built
- `surface_habitable_immeuble`: Floor area

## Troubleshooting

If you encounter issues during upload:

1. **Check Your File Format**: Ensure it's a valid CSV with headers
2. **Look for Missing Data**: Critical columns might be empty
3. **Check Column Names**: The system maps common names but may miss custom ones
4. **File Size**: Very large files (>100MB) might time out
5. **Special Characters**: Avoid non-ASCII characters in filenames

For persistent issues, please check the application logs or contact the administrator.
