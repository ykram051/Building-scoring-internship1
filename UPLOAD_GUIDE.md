# Building Dataset Upload Guide

This guide explains how to prepare your building datasets for upload into the Building Analytics Dashboard.

## Required Columns

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

## Example Dataset Format

Here's an example of a minimal dataset that will work with the system:

```
id,coordonnee_cartographique_x_ban,coordonnee_cartographique_y_ban,surface,height,emission,consumption
1,651784.5,6863758.2,120,15,75,180
2,652123.7,6863892.1,95,12,65,150
3,651432.8,6864123.4,150,18,80,200
4,652341.9,6863567.8,110,14,70,170
5,651890.3,6864245.6,130,16,85,190
```

This dataset will be processed to:
1. Convert coordinates to latitude/longitude
2. Rename columns as needed
3. Generate missing required columns
4. Create future year projections

## Processing Logic

When you upload a dataset, the system will:
1. Automatically detect and convert coordinates
2. Generate any missing required columns
3. Create log-transformed features
4. Generate future year projections
5. Save the data in multiple formats
6. Make it available as a selectable city

## Troubleshooting

If you encounter issues with dataset uploads:

1. Check that your CSV file is properly formatted
2. Ensure coordinate columns are properly named
3. Verify that numeric columns contain valid numbers
4. Make sure the file has a descriptive name (this will be used as the city name)

For any issues, please contact the system administrator.
