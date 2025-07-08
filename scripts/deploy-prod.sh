#!/bin/bash
# Production deployment script for Building Analytics Dashboard

set -e  # Exit on error

# Display header
echo "================================================="
echo "Building Analytics Dashboard Production Deployment"
echo "================================================="

# Check if docker and docker-compose are installed
if ! command -v docker &> /dev/null; then
    echo "Error: docker is not installed. Please install docker first."
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "Error: docker-compose is not installed. Please install docker-compose first."
    exit 1
fi

# Set up environment
echo "Setting up production environment..."

# Create production .env file if it doesn't exist
if [ ! -f "app/.env.production" ]; then
    echo "Creating production environment file..."
    cp app/.env.template app/.env.production
    echo "Please update app/.env.production with your production database credentials."
    echo "Press Enter to continue after editing or Ctrl+C to abort."
    read
fi

# Use production .env
cp app/.env.production app/.env

# Build and start the containers
echo "Building and starting containers..."
docker-compose -f docker-compose.prod.yml build
docker-compose -f docker-compose.prod.yml up -d

# Initialize the database
echo "Initializing database..."
docker-compose -f docker-compose.prod.yml exec app python init_database.py --exit-on-failure

echo ""
echo "Deployment completed successfully!"
echo "Application is now running at http://localhost:8501"
echo ""
echo "To check logs:"
echo "docker-compose -f docker-compose.prod.yml logs -f app"
echo ""
echo "To stop the application:"
echo "docker-compose -f docker-compose.prod.yml down"
