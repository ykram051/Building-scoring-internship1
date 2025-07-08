# Database Setup and Troubleshooting Guide

## ⚠️ IMPORTANT: Password Updated to 'root'

**The database password has been changed from 'postgres' to 'root' in all configuration files.**

### Updated Files:
- `.env` - Environment variables for local development
- `docker-compose.yml` - Docker configuration  
- `app/utils/config.py` - Application configuration
- `app/utils/simple_db_manager.py` - Database manager
- `scripts/setup_database.py` - Database setup script

## Overview

The Building Analytics Dashboard can run in two modes:

1. **Database Mode** (Full Features): Uses PostgreSQL for user management, data storage, and advanced features
2. **Fallback Mode** (Limited Features): Uses file-based authentication and basic functionality

## Quick Start

### Option 1: Docker (Recommended)
```bash
# Start with Docker (includes PostgreSQL with password 'root')
docker-compose up -d

# Access the app at http://localhost:8501
```

### Option 2: Fallback Mode (No Database)
```bash
# Install dependencies
pip install -r app/requirements.txt

# Run in fallback mode
streamlit run app/main_db.py
```

### Option 3: Local PostgreSQL
```bash
# 1. Install and start PostgreSQL
# 2. Set up the database
python scripts/setup_database.py

# 3. Run the application
streamlit run app/main_db.py
```

## Default Login Credentials

- **admin** / **admin123** (Administrator)
- **user** / **user123** (Regular User)
- **analyst** / **analyst123** (Data Analyst)
- **manager** / **manager123** (Building Manager)

## Troubleshooting Database Issues

### Error: "password authentication failed for user 'postgres'"

**Cause**: Incorrect PostgreSQL credentials or PostgreSQL not running.

**Solutions**:
1. **Use Docker**: `docker-compose up -d` (easiest solution)
2. **Check PostgreSQL service**: 
   - Windows: Check Services for "postgresql" service
   - Linux/Mac: `sudo systemctl status postgresql`
3. **Reset PostgreSQL password**:
   ```sql
   ALTER USER postgres PASSWORD 'postgres';
   ```
4. **Update .env file** with correct credentials

### Error: "utf-8 codec can't decode byte"

**Cause**: Database encoding issues or corrupted data.

**Solutions**:
1. **Use Docker** (fresh database): `docker-compose down -v && docker-compose up -d`
2. **Check database encoding**:
   ```sql
   SHOW server_encoding;
   SHOW client_encoding;
   ```
3. **Recreate database**:
   ```sql
   DROP DATABASE IF EXISTS building_analytics;
   CREATE DATABASE building_analytics WITH ENCODING 'UTF8';
   ```

### Error: "connection to server at 'localhost' failed"

**Cause**: PostgreSQL not running or wrong connection settings.

**Solutions**:
1. **Start PostgreSQL**:
   - Windows: Start PostgreSQL service
   - Linux: `sudo systemctl start postgresql`
   - Mac: `brew services start postgresql`
2. **Use Docker**: `docker-compose up -d`
3. **Check port**: Ensure PostgreSQL is running on port 5432

## Environment Configuration

Create a `.env` file in the project root:

```env
# Database Configuration
DB_HOST=localhost
DB_PORT=5432
DB_NAME=building_analytics
DB_USER=postgres
DB_PASSWORD=postgres

# Development settings
DEVELOPMENT_MODE=true
LOG_LEVEL=INFO
```

For Docker deployment, use:
```env
DB_HOST=postgres
```

## Database Schema

The application creates these tables automatically:

- **users**: User accounts and roles
- **datasets**: Dataset metadata and ownership
- **buildings**: Building data storage

## Features by Mode

### Database Mode Features
- ✅ User management and authentication
- ✅ Dataset ownership and permissions
- ✅ Building data editing
- ✅ Audit logging
- ✅ Multi-user support
- ✅ Data export and reporting

### Fallback Mode Features
- ✅ Basic authentication (file-based)
- ✅ Data visualization
- ✅ Basic analytics
- ❌ User management
- ❌ Dataset ownership
- ❌ Building editing
- ❌ Audit logging
- ❌ Advanced permissions

## Switching Between Modes

The application automatically detects database availability:

1. **Database available**: Uses database mode
2. **Database unavailable**: Falls back to file mode

You can force fallback mode by setting `DATABASE_DISABLED=true` in your `.env` file.

## Data Migration

To migrate from file-based to database mode:

1. Set up PostgreSQL
2. Run `python scripts/setup_database.py`
3. The application will automatically detect and use the database

## Performance Tips

1. **Use Docker** for development (isolates dependencies)
2. **Limit dataset size** for better performance
3. **Enable caching** in Streamlit settings
4. **Use PostgreSQL indexes** for large datasets

## Security Notes

- Default passwords should be changed in production
- Use environment variables for sensitive configuration
- Enable SSL for production PostgreSQL connections
- Regularly backup your database

## Support

If you encounter issues:

1. Check the application logs in the Streamlit interface
2. Verify PostgreSQL is running: `docker ps` or `systemctl status postgresql`
3. Test database connection: `python scripts/setup_database.py`
4. Use fallback mode as a temporary solution

For development, fallback mode provides a quick way to test the application without setting up PostgreSQL.
