# Production Deployment Guide

This guide explains how to deploy the Building Analytics Dashboard to a production environment.

## Prerequisites

- Docker and Docker Compose
- SSL certificate (for HTTPS)
- PostgreSQL database (can be containerized or external)

## Deployment Options

### Option 1: Docker Compose Deployment (Recommended)

The easiest way to deploy the application to production is using Docker Compose:

1. Create a production environment file:
   ```bash
   cp app/.env.template app/.env.production
   ```

2. Edit `app/.env.production` with your production settings:
   - Set secure database credentials
   - Generate strong random values for SECRET_KEY and AUTH_SECRET_KEY
   - Set DEBUG=False

3. Run the deployment script:
   ```bash
   # On Linux/Mac
   ./deploy-prod.sh
   
   # On Windows
   # Use PowerShell or WSL to run the script
   ```

4. Access the application at:
   - http://localhost:8501 (direct)
   - https://your-domain.com (if using NGINX with SSL)

### Option 2: Streamlit Cloud Deployment

For managed deployment with zero infrastructure management:

1. Push your code to GitHub
2. Go to [Streamlit Cloud](https://streamlit.io/cloud)
3. Connect to your repository
4. Configure the secrets in the Streamlit dashboard:
   ```toml
   [postgres]
   host = "your-production-db-host.com"
   port = 5432
   dbname = "building_analytics_prod"
   user = "secure_user"
   password = "secure_password"
   ```

## Security Best Practices

1. **Database Security**:
   - Use strong passwords for database users
   - Restrict network access to the database
   - Enable SSL for database connections

2. **Application Security**:
   - Set DEBUG=False in production
   - Use HTTPS with valid SSL certificates
   - Generate strong random secret keys
   - Run as a non-root user (handled by Dockerfile.prod)

3. **Updates and Maintenance**:
   - Regularly update dependencies (use `pip-audit` to check for vulnerabilities)
   - Back up the database regularly (see backup scripts)
   - Monitor logs for errors or suspicious activity

## Backup and Recovery

Use the included scripts for database backup:

```bash
# Create a backup
./backup_database.bat  # Windows
./backup_database.sh   # Linux/Mac

# Restore from backup
./restore_database.bat  # Windows
./restore_database.sh   # Linux/Mac
```

## Monitoring

For production monitoring, consider adding:

- Prometheus for metrics collection
- Grafana for dashboards
- Loki for log aggregation

## Troubleshooting

Common issues:

1. **Database connection errors**:
   - Check database credentials
   - Verify network connectivity
   - Make sure PostgreSQL is running

2. **Web server issues**:
   - Check NGINX configuration
   - Verify SSL certificate validity
   - Check firewall settings
