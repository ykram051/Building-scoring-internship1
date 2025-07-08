# Dataset Management Guide

This guide explains how to manage datasets in the Building Analytics Dashboard.

## Uploading Datasets

You can upload custom datasets through the sidebar:

1. Click on "➕ Upload Custom Dataset" in the dropdown menu
2. Select a CSV file with building data (see format requirements below)
3. Provide a name for your dataset
4. Wait for processing to complete

The system will:
- Process your data and generate required columns if missing
- Convert coordinates to latitude/longitude if needed
- Generate future year projections
- Store the dataset in both filesystem and database

## Deleting Datasets

To delete a dataset that you own:

1. Select your dataset from the dropdown menu in the sidebar
2. Click the "🗑️ Delete" button that appears for your own datasets
3. Confirm the deletion when prompted

The deletion process:
- Removes all related files from the filesystem
- Deletes all records from the database
- Removes ownership records
- Updates the dataset list automatically

## Dataset Ownership

When you upload a dataset:
- It's marked as owned by your user account
- Your datasets are labeled with "(Your Dataset)" in the dropdown
- Only you and administrators can delete your datasets
- Built-in datasets (Lyon, Gordes, etc.) cannot be deleted

## Dataset Format Requirements

Your CSV file should include these important columns:

| Column | Description | Required? | Notes |
|--------|-------------|-----------|-------|
| `building_id` | Unique identifier | Yes | Will be auto-generated if missing |
| `latitude` | Geographic latitude | Yes | Will be converted or generated |
| `longitude` | Geographic longitude | Yes | Will be converted or generated |
| `Energy_Consumption` | Total energy use | Yes | Will be generated if missing |
| `CO2_Usage` | Carbon emissions | Yes | Will be generated if missing |
| `Water_Usage` | Water consumption | Yes | Will be generated if missing |
| `Energy_Intensity` | Energy per square meter | Yes | Will be generated if missing |
| `CO2_Intensity` | Emissions per square meter | Yes | Will be generated if missing |

## Coordinate Formats

The system supports the following coordinate formats:

1. **WGS84 (EPSG:4326)** - Standard latitude/longitude:
   - `latitude`, `longitude` columns

2. **French RGF93/Lambert-93 (EPSG:2154)**:
   - `coordonnee_cartographique_x_ban`, `coordonnee_cartographique_y_ban` columns
   
3. **Other X/Y Coordinate Systems**:
   - Any columns starting with or containing 'x' and 'y'
   - Example: `x`, `y`, `point_x`, `point_y`, etc.
