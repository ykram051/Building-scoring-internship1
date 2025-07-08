# Building Analytics Dashboard - Windows Setup Script
# This script helps you set up and run the Building Analytics Dashboard on Windows

Write-Host "=" -Repeat 60
Write-Host "  Building Analytics Dashboard - Windows Setup"
Write-Host "=" -Repeat 60
Write-Host ""

# Check if Python is available
try {
    $pythonVersion = python --version 2>$null
    Write-Host "✅ Python available: $pythonVersion"
} catch {
    Write-Host "❌ Python not found. Please install Python first."
    exit 1
}

# Check if Docker is available
try {
    $dockerVersion = docker --version 2>$null
    Write-Host "✅ Docker available: $dockerVersion"
    $dockerAvailable = $true
} catch {
    Write-Host "❌ Docker not available"
    $dockerAvailable = $false
}

Write-Host ""
Write-Host "Setup options:"
Write-Host "1. Run with Docker (Full features, includes PostgreSQL)"
Write-Host "2. Run in fallback mode (Limited features, no database required)"
Write-Host "3. Exit"
Write-Host ""

do {
    $choice = Read-Host "Choose an option (1-3)"
    
    switch ($choice) {
        "1" {
            if (-not $dockerAvailable) {
                Write-Host "❌ Docker is required for this option. Please install Docker Desktop."
                continue
            }
            
            Write-Host ""
            Write-Host "🐳 Starting with Docker..."
            Write-Host ""
            
            # Create .env file if it doesn't exist
            if (-not (Test-Path ".env")) {
                @"
# Database Configuration
DB_HOST=postgres
DB_PORT=5432
DB_NAME=building_analytics
DB_USER=postgres
DB_PASSWORD=postgres
DEVELOPMENT_MODE=true
LOG_LEVEL=INFO
"@ | Out-File -FilePath ".env" -Encoding UTF8
                Write-Host "✅ Created .env file"
            }
            
            # Start Docker Compose
            Write-Host "Starting Docker containers..."
            docker-compose up -d
            
            if ($LASTEXITCODE -eq 0) {
                Write-Host ""
                Write-Host "✅ Application started successfully!"
                Write-Host ""
                Write-Host "🌐 Open your browser and go to: http://localhost:8501"
                Write-Host ""
                Write-Host "Default login credentials:"
                Write-Host "• admin / admin123 (Administrator)"
                Write-Host "• user / user123 (Regular User)"
                Write-Host "• analyst / analyst123 (Data Analyst)"
                Write-Host ""
                Write-Host "To stop the application, run: docker-compose down"
            } else {
                Write-Host "❌ Failed to start Docker containers. Check the error messages above."
            }
            break
        }
        
        "2" {
            Write-Host ""
            Write-Host "🔄 Setting up fallback mode..."
            Write-Host ""
            
            # Create data directory
            if (-not (Test-Path "app\data")) {
                New-Item -ItemType Directory -Path "app\data" -Force | Out-Null
                Write-Host "✅ Created data directory"
            }
            
            # Install Python dependencies
            Write-Host "Installing Python dependencies..."
            pip install -r app/requirements.txt
            
            if ($LASTEXITCODE -eq 0) {
                Write-Host ""
                Write-Host "✅ Dependencies installed successfully!"
                Write-Host ""
                Write-Host "Starting the application..."
                Write-Host ""
                
                # Start Streamlit
                streamlit run app/main_db.py
            } else {
                Write-Host "❌ Failed to install dependencies. Check the error messages above."
            }
            break
        }
        
        "3" {
            Write-Host "Exiting..."
            exit 0
        }
        
        default {
            Write-Host "Invalid choice. Please enter 1, 2, or 3."
        }
    }
} while ($true)
