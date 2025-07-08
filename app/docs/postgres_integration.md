# PostgreSQL Integration Guide

This document outlines how to set up and use PostgreSQL with the Building Analytics Dashboard.

## Prerequisites

1. Install PostgreSQL (version 12 or newer)
2. Create a PostgreSQL user with permissions to create databases
3. Install the Python dependencies:
   ```
   pip install psycopg2-binary sqlalchemy python-dotenv pandas
   ```
   
> **Note:** All required dependencies are included in the project's `requirements.txt` file. You can install all dependencies at once using `pip install -r app/requirements.txt`

## Setup Steps

### 1. Configure Database Connection

Create or edit the `.env` file in the `app` directory with your PostgreSQL connection details:

```
DB_HOST=localhost
DB_PORT=5432
DB_NAME=building_analytics
DB_USER=postgres
DB_PASSWORD=your_secure_password
```

### 2. Initialize Database

Run the initialization script to create the database and tables:

```bash
cd app
python scripts/initialize_db.py
```

This will:
- Create the `building_analytics` database (if it doesn't exist)
- Create all required tables
- Add necessary indexes
- Create default users (admin/admin123 and user/user123)

### 3. Migrate Existing Data

If you have existing data in CSV files, run the migration script:

```bash
cd app
python scripts/migrate_to_db.py
```

This will:
- Migrate users from `data/users.json`
- Migrate datasets from CSV files in the data directory
- Migrate dataset ownership information

For a full initialization and migration, you can run:

```bash
cd app
python scripts/full_migration.py
```

### 4. Run the Application

Start the application with:

```bash
cd app
streamlit run main.py
```

The application will now use PostgreSQL for all data storage and retrieval.

### Using the Windows PowerShell Launcher

For Windows users, we provide a comprehensive PowerShell-based launcher that simplifies all database operations:

1. Open a PowerShell window (or Command Prompt) and navigate to the project directory
2. Run the PowerShell launcher:
   ```
   .\Run-Dashboard.ps1
   ```

3. The launcher provides a menu with the following options:
   - Launch Dashboard with Database
   - Launch Dashboard in File-only Mode
   - Initialize Database
   - Migrate File Data to Database
   - Backup Database
   - Restore Database
   - Edit Configuration
   - Check System Status

4. For first-time setup:
   - Start by selecting option 7 to edit your configuration
   - Then use option 3 to initialize the database
   - Followed by option 4 to migrate your existing data
   - Finally, use option 1 to launch the application

## Database Schema

### Users Table
- `username`: User's login name (primary key)
- `password`: Hashed password (SHA-256)
- `name`: User's display name
- `role`: User's role (admin, analyst, user)
- `created_at`: Account creation timestamp
- `last_login`: Last login timestamp

### Datasets Table
- `id`: Dataset ID (primary key)
- `name`: Dataset name (unique)
- `owner`: Username of dataset owner (foreign key)
- `description`: Dataset description
- `city`: City name associated with dataset
- `created_at`: Dataset creation timestamp
- `is_system`: Whether this is a system dataset (vs. user-uploaded)

### Buildings Table
- `building_id`: Building ID
- `dataset_id`: Dataset ID (foreign key)
- `city`: City name
- `year`: Year of data
- `latitude`, `longitude`: Geographic coordinates
- `energy_consumption`, `co2_usage`, `water_usage`: Core metrics
- `energy_intensity`, `co2_intensity`: Intensity metrics
- `true_energy_label`, `true_ges_label`: Energy labels
- Various address fields, construction details, etc.
- Transformed values like log1p_energy_consumption
- `pc1`, `pc2`: Principal component values
- `cluster`: Cluster assignment

### Security & Audit Logs
- Security events (login/logout, access attempts)
- Data modifications
- Dataset access events

## Database-Only Mode

This application operates exclusively in database mode. There is no option for file-based storage.

### Database Connection Pooling

The application uses connection pooling to efficiently manage database connections. This is handled automatically by SQLAlchemy, but you can tune the parameters in the `db.py` file if needed:

```python
ENGINE_KWARGS = {
    'pool_size': 5,               # Maximum number of connections in the pool
    'max_overflow': 10,           # Maximum number of connections that can be created beyond pool_size
    'pool_timeout': 30,           # Seconds to wait before giving up on getting a connection from the pool
    'pool_recycle': 1800,         # Connections older than this many seconds will be recycled
    'pool_pre_ping': True,        # Check connection validity before using it from the pool
}
```

For high-traffic deployments, you might want to increase the `pool_size` and `max_overflow` values.

## Database Backup and Restore

### Automated Backup and Restore

For Windows users, the easiest way to manage backups is through the PowerShell launcher menu (options 5 and 6).

You can also use the batch files provided:
- `backup_database.bat` - Creates a timestamped backup in the `backups` folder
- `restore_database.bat` - Interactively restores from a selected backup file

### Manual Backup

To manually backup your database:

```bash
# Export the database to a file
pg_dump -h localhost -p 5432 -U postgres -f backup_file.sql building_analytics
```

### Manual Restore

To restore from a backup:

```bash
# Create a clean database
psql -h localhost -p 5432 -U postgres -c "DROP DATABASE IF EXISTS building_analytics;" postgres
psql -h localhost -p 5432 -U postgres -c "CREATE DATABASE building_analytics;" postgres

# Restore from backup
psql -h localhost -p 5432 -U postgres -d building_analytics -f backup_file.sql
```

## Troubleshooting

### Common Issues

1. **Connection Refused Error**
   - Verify PostgreSQL is running: `pg_isready -h localhost`
   - Check if the port is correct in your `.env` file
   - Ensure there are no firewall restrictions

2. **Authentication Failed Error**
   - Verify username and password in `.env` file
   - Check PostgreSQL's `pg_hba.conf` authentication settings

3. **Database Does Not Exist**
   - Run the initialization script: `python app/scripts/initialize_db.py`

4. **Permission Denied Errors**
   - Ensure your database user has proper permissions
   - For new installations, try: `ALTER USER postgres WITH SUPERUSER;`

### Log Files

Check the application logs for database-related errors:
- `app/logs/app.log` - General application logs
- PostgreSQL logs (location varies by installation)
