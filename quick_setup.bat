@echo off
echo Building Analytics Dashboard - Quick Setup
echo ==========================================
echo.

echo Setting up environment variables...
set DB_HOST=localhost
set DB_PORT=5432
set DB_NAME=building_analytics
set DB_USER=postgres
set DB_PASSWORD=root

echo.
echo Database Configuration:
echo - Host: %DB_HOST%
echo - Port: %DB_PORT%
echo - Database: %DB_NAME%
echo - User: %DB_USER%
echo - Password: %DB_PASSWORD%
echo.

echo Option 1: Start with Docker (Recommended)
echo ------------------------------------------
echo This will start PostgreSQL and the app in containers
echo Run: docker-compose up -d
echo.

echo Option 2: Setup Local Database
echo -------------------------------
echo If you have PostgreSQL installed locally:
echo 1. Create database 'building_analytics'
echo 2. Set password for 'postgres' user to 'root'
echo 3. Run: python scripts/setup_database.py
echo 4. Run: streamlit run app/main_db.py
echo.

echo Option 3: Run in Fallback Mode
echo -------------------------------
echo If no database is available, the app will automatically
echo use file-based authentication and limited functionality.
echo Run: streamlit run app/main_db.py
echo.

pause
