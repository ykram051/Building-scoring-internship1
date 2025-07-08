# Web Deployment Guide for Building Analytics Dashboard

This guide explains how to deploy the Building Analytics Dashboard as a web application so users can access it through their browsers without installing PostgreSQL.

## Deployment Options

### Option 1: Streamlit Cloud (Easiest)

[Streamlit Cloud](https://streamlit.io/cloud) offers free hosting for Streamlit apps, making it ideal for quick deployment.

1. **Set up a hosted PostgreSQL database**:
   - Create a database on [ElephantSQL](https://www.elephantsql.com/) (free tier available)
   - Or use [Heroku Postgres](https://www.heroku.com/postgres), [AWS RDS](https://aws.amazon.com/rds/), etc.
   - Note your database connection details

2. **Deploy to Streamlit Cloud**:
   - Fork/push this repository to GitHub
   - Go to [Streamlit Cloud](https://streamlit.io/cloud) and log in
   - Click "New app" and select your repository
   - Set the main file path to: `app/main.py`
   - In "Advanced settings" → "Secrets", add your database credentials:
     ```toml
     [postgres]
     host = "your-database-hostname.com"
     port = 5432
     dbname = "building_analytics"
     user = "your_username"
     password = "your_password"
     ```
   - Deploy the app

3. **Initialize the database**:
   - Connect to your database using a PostgreSQL client
   - Run the `app/init_database.py` script against your hosted database

4. **Share with users**:
   - Share the Streamlit Cloud URL with your users
   - Users can access the dashboard with just a web browser
   - No PostgreSQL installation required for end users

### Option 2: Heroku Deployment

1. **Create a new app on Heroku**:
   ```
   heroku create building-analytics-dashboard
   ```

2. **Add PostgreSQL add-on**:
   ```
   heroku addons:create heroku-postgresql:hobby-dev
   ```

3. **Deploy the application**:
   ```
   git push heroku main
   ```

4. **Initialize the database**:
   ```
   heroku run python app/init_database.py
   ```

5. **Open the application**:
   ```
   heroku open
   ```

### Option 3: Cloud VPS with Docker

For more control over your deployment:

1. **Rent a VPS** (DigitalOcean, Linode, AWS EC2, etc.)
2. **Install Docker and Docker Compose**
3. **Clone the repository and deploy**:
   ```
   git clone <repository-url>
   cd Building_Scoring-khaoula
   docker-compose up -d
   ```
4. **Set up a domain name** and configure HTTPS

## Authentication and Security

The application includes built-in authentication. Default credentials:
- Admin: `admin` / `admin123`
- User: `user` / `user123`

For production, update these credentials immediately after deployment.

## Scaling Considerations

- **Database Performance**: Consider upgrading to a larger database plan for datasets over 1GB
- **Application Scaling**: Deploy behind a load balancer for high-traffic scenarios
- **Caching**: Enable Redis for session caching in high-traffic deployments
