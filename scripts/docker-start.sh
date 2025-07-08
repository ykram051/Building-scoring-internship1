#!/bin/bash

# Start the application with Docker Compose
docker-compose up -d

# Initialize the database
echo "Initializing database..."
docker-compose exec app python init_database.py

echo ""
echo "Application is now running at http://localhost:8501"
