# Building Analytics Dashboard: Cloud Deployment Guide

This guide explains how to configure the Building Analytics Dashboard to use a remote PostgreSQL database service, 
eliminating the need for users to install PostgreSQL locally.

## Option 1: Deploy with Docker (Recommended)

Using Docker is the simplest way to deploy the application as it packages both the application and database together.

### Prerequisites
- Docker and Docker Compose installed on the host machine

### Steps

1. Make sure Docker and Docker Compose are installed on your system
2. Clone or download the repository
3. Run the start script:
   ```
   # Windows
   .\docker-start.bat
   
   # Linux/macOS
   ./docker-start.sh
   ```
4. Access the application at http://localhost:8501

## Option 2: Using a Remote Database

You can deploy the PostgreSQL database on a cloud service (AWS RDS, Azure Database for PostgreSQL, GCP Cloud SQL, etc.)
and have users connect to this shared database.

### Setup Steps

1. Create a PostgreSQL database on your preferred cloud provider
   - AWS RDS: https://aws.amazon.com/rds/postgresql/
   - Azure Database for PostgreSQL: https://azure.microsoft.com/en-us/products/postgresql/
   - Google Cloud SQL: https://cloud.google.com/sql/docs/postgres
   - Digital Ocean: https://www.digitalocean.com/products/managed-databases-postgresql

2. Configure the database connection in the `.env` file:
   ```
   DB_HOST=your-database-hostname.cloud-provider.com
   DB_PORT=5432
   DB_NAME=building_analytics
   DB_USER=your_db_username
   DB_PASSWORD=your_secure_password
   STRICT_DB_MODE=true
   ```

3. Initialize the database schema:
   ```
   python app/init_database.py --exit-on-failure
   ```

4. Run the application normally:
   ```
   # Windows
   .\run.bat
   
   # Linux/macOS
   ./run.sh
   ```

## Option 3: Streamlit Cloud Deployment

For a completely serverless approach, you can deploy the application on Streamlit Cloud and connect it to a managed database service.

1. Create a PostgreSQL database on your preferred cloud provider (see Option 2)

2. Create a GitHub repository with your application code

3. Create a `.streamlit/secrets.toml` file with your database credentials:
   ```toml
   [postgres]
   host = "your-database-hostname.cloud-provider.com"
   port = 5432
   dbname = "building_analytics"
   user = "your_db_username"
   password = "your_secure_password"
   ```
   
4. Modify `utils/config.py` to use Streamlit secrets when available:
   ```python
   # In utils/config.py
   import streamlit as st
   
   # Try to get credentials from Streamlit secrets if deployed on Streamlit Cloud
   if hasattr(st, 'secrets') and 'postgres' in st.secrets:
       DB_CONFIG = {
           "host": st.secrets.postgres.host,
           "port": st.secrets.postgres.port,
           "database": st.secrets.postgres.dbname,
           "user": st.secrets.postgres.user,
           "password": st.secrets.postgres.password
       }
   else:
       # Fall back to .env file
       DB_CONFIG = {
           "host": os.environ.get("DB_HOST", "localhost"),
           "port": os.environ.get("DB_PORT", "5432"),
           "database": os.environ.get("DB_NAME", "building_analytics"),
           "user": os.environ.get("DB_USER", "postgres"),
           "password": os.environ.get("DB_PASSWORD", "postgres")
       }
   ```

5. Deploy on Streamlit Cloud: https://docs.streamlit.io/streamlit-cloud/get-started

## Security Considerations

When using a remote database:

1. Ensure the database connection is secured with SSL
2. Use a strong password and restrict IP access where possible
3. Create appropriate database users with least privilege access
4. Consider implementing connection pooling for better performance
