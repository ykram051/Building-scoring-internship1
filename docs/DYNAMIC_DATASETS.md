# Dynamic Dataset Management System

## Overview

This system allows users to upload datasets with arbitrary schemas while maintaining security, performance, and queryability. It uses a hybrid approach combining JSONB storage for flexibility and dedicated tables for performance.

## Architecture

### Database Schema

1. **user_datasets** - Metadata table storing dataset information
2. **dataset_data** - JSONB storage for flexible data (datasets < 10k rows)
3. **Dynamic tables** - Dedicated tables for large datasets (datasets > 10k rows)

### Key Components

1. **DatasetManager** (`utils/dataset_manager.py`) - Core management class
2. **Dataset Explorer** (`utils/dataset_explorer.py`) - UI interface
3. **Database Integration** - Enhanced schema in `utils/db.py`
4. **Security Integration** - RBAC through `utils/secure_auth.py`

## Usage Examples

### 1. Upload Dataset with Arbitrary Schema

```python
from utils.dataset_manager import dataset_manager

# Upload a dataset
success, message, dataset_id = dataset_manager.upload_dataset(
    uploaded_file=file_object,
    dataset_name="my_custom_dataset",
    display_name="My Custom Dataset",
    description="Dataset with custom schema",
    tags=["custom", "analysis"]
)
```

### 2. Query Dataset Flexibly

```python
# Query with filters
success, result_df, message = dataset_manager.query_dataset(
    dataset_name="my_custom_dataset",
    filters={"category": "residential", "year": "2024"},
    columns=["building_id", "energy_rating", "location"],
    limit=1000
)
```

### 3. Get Dataset Preview

```python
# Get preview of any dataset
success, preview_df, message = dataset_manager.get_dataset_preview(
    dataset_name="my_custom_dataset",
    limit=100
)
```

## Storage Strategy

### JSONB Storage (< 10k rows)
- **Pros**: Flexible schema, fast queries with GIN indexes
- **Cons**: Limited performance with very large datasets
- **Use case**: Small to medium datasets, prototyping

### Dedicated Tables (> 10k rows)
- **Pros**: High performance, optimized for large datasets
- **Cons**: Fixed schema per dataset
- **Use case**: Large production datasets

## Security Features

### Authentication & Authorization
- User isolation - users only see their own datasets
- Role-based permissions (upload, view, delete)
- Audit logging for all operations

### Data Validation
- File type validation (CSV, Excel)
- Size limits (1M rows max)
- SQL injection prevention
- Input sanitization

### Privacy
- User-specific dataset namespaces
- Optional public dataset sharing
- Secure file handling

## Performance Optimizations

### Indexing Strategy
```sql
-- GIN index for JSONB queries
CREATE INDEX idx_dataset_data_jsonb ON dataset_data USING GIN (data);

-- B-tree indexes for metadata
CREATE INDEX idx_user_datasets_owner ON user_datasets(owner);
CREATE INDEX idx_user_datasets_name_owner ON user_datasets(dataset_name, owner);
```

### Caching
- Dataset metadata caching
- Query result caching for frequent queries
- Schema information caching

### Batch Operations
- Bulk insert for dataset uploads
- Chunked processing for large files
- Transaction management

## API Reference

### DatasetManager Methods

#### `upload_dataset(uploaded_file, dataset_name, display_name=None, description=None, tags=None)`
Upload a new dataset with flexible schema.

**Parameters:**
- `uploaded_file`: File object (CSV/Excel)
- `dataset_name`: Unique identifier
- `display_name`: Human-readable name
- `description`: Optional description
- `tags`: List of tags for categorization

**Returns:** `(success: bool, message: str, dataset_id: int)`

#### `get_user_datasets(username=None)`
Get all datasets for a user.

**Returns:** `DataFrame` with dataset metadata

#### `query_dataset(dataset_name, filters=None, columns=None, limit=1000)`
Query dataset with flexible filters.

**Parameters:**
- `dataset_name`: Name of dataset to query
- `filters`: Dict of column:value filters
- `columns`: List of columns to select
- `limit`: Maximum rows to return

**Returns:** `(success: bool, result_df: DataFrame, message: str)`

#### `delete_dataset(dataset_name)`
Delete a dataset and all its data.

**Returns:** `(success: bool, message: str)`

## Integration Points

### Main Application Integration
```python
# In main_db.py
from data.data_processing import upload_flexible_dataset

# Upload with flexible schema
success, message, dataset_id = upload_flexible_dataset(
    uploaded_file, dataset_name, display_name, description, tags
)
```

### Dataset Explorer UI
```python
# In utils/dataset_explorer.py
from utils.dataset_manager import dataset_manager

# Display datasets
datasets_df = dataset_manager.get_user_datasets()
```

## Migration Guide

### From Legacy System
1. Run the migration script: `python scripts/migrate_flexible_datasets.py`
2. Existing datasets remain unchanged
3. New uploads use flexible system automatically

### Database Setup
```sql
-- Core tables are created automatically
-- Manual indexes for optimization:
CREATE INDEX CONCURRENTLY idx_dataset_data_dataset_row 
ON dataset_data(dataset_id, row_index);
```

## Configuration

### Environment Variables
```bash
# Database connection
DB_HOST=localhost
DB_PORT=5432
DB_NAME=building_analytics
DB_USER=postgres
DB_PASSWORD=your_password

# Dataset limits
MAX_DATASET_SIZE_ROWS=1000000
MAX_FILE_SIZE_MB=100
JSONB_THRESHOLD_ROWS=10000
```

### Streamlit Secrets
```toml
# .streamlit/secrets.toml
[database]
host = "localhost"
port = 5432
database = "building_analytics"
username = "postgres"
password = "your_password"

[datasets]
max_size_mb = 100
max_rows = 1000000
```

## Troubleshooting

### Common Issues

1. **Import Error: dataset_manager not found**
   - Solution: Ensure `utils/dataset_manager.py` is in the correct location
   - Check Python path includes the app directory

2. **Database Connection Failed**
   - Solution: Verify PostgreSQL is running and credentials are correct
   - Check network connectivity and firewall settings

3. **Upload Failed: File too large**
   - Solution: Increase limits in configuration
   - Consider data preprocessing to reduce size

4. **Query Performance Slow**
   - Solution: Check if dataset should use dedicated table storage
   - Verify indexes are created properly

### Debug Mode
```python
import logging
logging.getLogger('utils.dataset_manager').setLevel(logging.DEBUG)
```

## Future Enhancements

### Planned Features
1. **Advanced Query Builder**: SQL-like interface
2. **Data Transformation**: ETL pipeline for uploads
3. **Visualization Integration**: Chart generation from arbitrary schemas
4. **Export Formats**: JSON, Parquet, Excel export
5. **Collaboration**: Dataset sharing and permissions
6. **Version Control**: Dataset versioning and history

### Performance Improvements
1. **Parallel Processing**: Multi-threaded uploads
2. **Compression**: Data compression for storage efficiency
3. **Partitioning**: Table partitioning for very large datasets
4. **Materialized Views**: Pre-computed aggregations
