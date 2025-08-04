# Building Analytics Dashboard

A Streamlit-based dashboard for analyzing building energy efficiency with multiple classification models and interactive visualizations, now with PostgreSQL database integration for scalable enterprise deployment.

## Features

- Interactive map visualization of building energy classes
- Multiple classification methods (Mahalanobis, PCA, Weighted, Tree, Cosine Distance, Topsis)
- Building comparison and benchmarking
- Data export and reporting
- Year-over-year analytics
- City-to-city comparisons
- **🤖 AI Assistant**: Intelligent chatbot for data analysis and feature explanations
- **🔒 Enterprise Security**: Comprehensive security implementation with authentication, authorization, and audit logging
- **NEW**: PostgreSQL database integration
  - Scalable storage solution for large building datasets
  - High-performance database queries
  - Multi-user concurrent access support
  - Secure user authentication and authorization
  - Centralized data management

## 🔒 Security Features

The Building Analytics Dashboard implements enterprise-grade security:

### Authentication & Session Management
- **Secure password hashing** with SHA-256 and cryptographic salts
- **Session timeout protection** (configurable, default 30 minutes)
- **Failed login attempt tracking** and account lockout protection
- **Strong password policies** with complexity requirements

### Authorization & Access Control
- **Role-based access control (RBAC)** with granular permissions
- **User data isolation** - users can only access their own datasets
- **Administrative controls** for user and system management
- **Permission validation** for every system operation

### Data Protection
- **Input validation and sanitization** to prevent XSS and injection attacks
- **Parameterized SQL queries** to prevent SQL injection
- **Secure file uploads** with type, size, and content validation
- **User-specific file directories** for data isolation

### Audit & Compliance
- **Comprehensive security logging** of authentication and authorization events
- **Audit trail** for all data modifications and system changes
- **Session tracking** with detailed user activity logs
- **Database logging** of all security-relevant operations

### Production Security
- **Environment-based configuration** with secure secret management
- **Streamlit security headers** including XSRF protection
- **Docker security best practices** with non-root execution
- **Error handling** that prevents information disclosure

For detailed security information, see [Security Documentation](docs/SECURITY.md).

## Project Structure

The project has been reorganized for better maintainability:

### Core Components

- `app/main_db.py` - Main application with database integration
- `app/data/data_processing.py` - Unified data processing module
- `app/utils/` - Utilities for authentication, logging, and building data management
- `app/models/` - Classification models for energy efficiency analysis
- `app/visualization/` - Charts and map visualization components

### Security Components

- `app/utils/secure_auth.py` - Secure authentication and session management
- `app/utils/secure_file_handler.py` - Secure file upload and validation
- `app/utils/logger.py` - Enhanced security and audit logging
- `.streamlit/config.toml` - Production security configuration
- `docs/SECURITY.md` - Comprehensive security documentation

### Data Processing

Data uploads are handled through `data_processing.py` which implements consistent processing:
- Column normalization and standardization
- Feature engineering
- Future year projections
- Database integration

### Dataset Management

The application supports:
- Built-in datasets (Lyon, Lille, etc.)
- User-uploaded custom datasets
- Automatic city detection and processing

## Authentication System

The dashboard includes a role-based authentication system with the following roles:

- **Admin**: Full access to all dashboard features, including user management, data import/export, and building data editing
- **User**: Basic access for viewing visualizations and analytics
- **Analyst**: Access to data export and report generation features
- **Manager**: Access to building data editing features

### Default Credentials

- Admin: `admin` / `admin123`
- User: `user` / `user123`
- Analyst: `analyst` / `analyst123`
- Manager: `manager` / `manager123`

### Managing Users

Administrators can manage users through the Admin Settings tab in the dashboard.

To manage users via command line:

```bash
# Initialize the user system with default users
python app/scripts/manage_users.py init

# List all users
python app/scripts/manage_users.py list

# Add a new user
python app/scripts/manage_users.py add username password --role admin --name "Display Name"

# Reset a password
python app/scripts/manage_users.py reset username new_password

# Delete a user
python app/scripts/manage_users.py delete username
```

## Installation

### Prerequisites
- Python 3.8+ with conda/anaconda
- PostgreSQL 12+ (optional - app can run in fallback mode)

### Setup Steps

1. Clone the repository
2. Install dependencies:
   ```bash
   # Install via conda (recommended)
   conda install -c conda-forge streamlit pandas numpy plotly
   
   # Install AI chatbot dependencies via pip
   pip install openai langchain langchain-openai langchain-experimental pandasai tiktoken
   
   # Or install all at once
   pip install -r app/requirements.txt
   ```

3. Set up PostgreSQL (Optional):
   - Install PostgreSQL from [postgresql.org](https://www.postgresql.org/download/)
   - Create a database called `building_analytics` (or use a name of your choice)
   - Update the database credentials in `.env`

4. Configure AI Assistant (Optional):
   - Get an OpenAI API key from [OpenAI Platform](https://platform.openai.com/api-keys)
   - Add it to `.streamlit/secrets.toml`:
     ```toml
     [openai]
     api_key = "your-openai-api-key-here"
     ```

## 🚀 **Quick Start** 

**The chatbot requires the conda environment where langchain is installed.**

### Option 1: Manual Startup (Recommended)
```bash
# 1. Open Anaconda Prompt or PowerShell
# 2. Navigate to project directory
cd "c:\Users\USER\Desktop\Building_Scoring_internship\Building-scoring"

# 3. Activate conda environment
conda activate base

# 4. Go to app directory and run
cd app
streamlit run main_db.py
```

### Option 2: Direct Conda Command
```bash
# Run directly with conda (from Building-scoring directory)
conda run streamlit run app/main_db.py
```

### ⚠️ **Important Note**
- Running with regular `python` or `streamlit` will show "Chatbot module not available" 
- You **must** use the conda environment where langchain packages are installed
- All other features work fine, only the AI chatbot requires conda environment
   
## Deployment Options

This application requires PostgreSQL, but we provide several deployment options to make it easier for end users:

### Option 1: Docker Deployment (Recommended for Production)

We provide Docker configurations to package both the application and PostgreSQL database together:

```bash
# Start the application with Docker
./docker-start.sh  # or docker-start.bat on Windows
```

This automatically sets up PostgreSQL and the application in containers, making it easy to deploy without installing PostgreSQL separately.

### Option 2: Cloud Database

You can connect to a hosted PostgreSQL database instead of installing it locally:

1. Set up a PostgreSQL database on a cloud provider (AWS RDS, Azure, etc.)
2. Update the `.env` file with your cloud database credentials
3. Run the application normally

For detailed instructions on deployment options, see the [Cloud Deployment Guide](CLOUD_DEPLOYMENT.md).

## Role-Based Features

### Admin Features
- Upload custom datasets
- Export data
- Generate reports
- Edit building information
- Manage users
- Compare cities
- Configure system settings

### User Features
- View building data on interactive map
- Analyze building energy efficiency
- Filter and sort buildings
- View building details

### Analyst Features
- All user features
- Export data
- Generate reports

### Manager Features
- All user features
- Edit building information

## Development

### Adding a New Role

To add a new role, update the `ROLES` dictionary in `app/utils/roles.py` with the new role and its permissions.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## PostgreSQL Integration

The dashboard uses PostgreSQL database for enhanced performance, reliability, and scalability.

### For End Users (Web Access)

When the application is deployed as a web service, end users can access it through their web browsers without installing anything. See our [Web Deployment Guide](WEB_DEPLOYMENT.md) for details on how to deploy the application for web access.

### For Developers and Administrators (Local Setup)

If you're setting up the application locally for development or administration:

- PostgreSQL 12+ installed and running
- Python 3.8+ 
- Python packages (install with `pip install -r app/requirements.txt`):
  - psycopg2-binary (PostgreSQL driver)
  - SQLAlchemy (ORM and database toolkit)
  - pandas, numpy (data processing)
  - streamlit (web interface)
- Database credentials with CREATE DATABASE permissions

### Quick Start (Windows)

1. Run the PowerShell launcher script:
   ```
   .\Run-Dashboard.ps1
   ```
   
2. From the menu, first select "7" to configure your database connection parameters
   
3. Select "3" to initialize the database structure
   
4. Select "4" to migrate existing CSV data to the database
   
5. Select "1" to run the application with database support

### Quick Start (Unix/Linux/Mac)

1. Run the bash script:
   ```bash
   ./run_with_db.sh
   ```

### Manual Setup

1. Install required dependencies:
   ```
   pip install -r app/requirements.txt
   ```

2. Create a `.env` file in the app directory with the following structure:
   ```
   # Database Configuration
   DB_HOST=localhost
   DB_PORT=5432
   DB_NAME=building_analytics
   DB_USER=postgres
   DB_PASSWORD=your_password
   
   # Application Settings
   DEBUG=false
   LOG_LEVEL=INFO
   
   # AI Assistant (Optional)
   OPENAI_API_KEY=your-openai-api-key-here
   ```

3. **🤖 Enable AI Assistant**:
   
   The AI Assistant provides intelligent help with data analysis and is **already configured** with all required dependencies.
   
   **To enable full functionality** (optional):
   - Get an OpenAI API key from https://platform.openai.com/api-keys
   - Add it to `.streamlit/secrets.toml`:
     ```toml
     [openai]
     api_key = "your-openai-api-key-here"
     ```
   
   **Without an API key**, the chatbot will run in demo mode with limited functionality.
   
   The AI Assistant provides:
   - Natural language data queries ("Show me the worst performing buildings")
   - Automated chart generation
   - ML model explanations
   - Dataset insights and analysis

4. **Database Setup**:
   ```
   python app/scripts/setup_database.py
   ```

5. **Migrate Existing CSV Data**:
   ```
   python app/scripts/migrate_to_db.py
   ```

6. **Run the Application**:
   ```
   streamlit run app/main_db.py
   ```

## Uploading Custom Datasets

The application supports custom building dataset uploads. Requirements:

1. CSV format with building data
2. Required columns:
   - `id` or `building_id` (or will be auto-generated)
   - Geographic coordinates (latitude/longitude)
   - Energy metrics (consumption, emissions, etc.)

The upload process will:
1. Normalize column names
2. Process data according to standard transformations
3. Generate future year projections (2024, 2025)
4. Store data in both file system and database
5. Make the dataset immediately available as a selectable city

For details on the data processing workflow, see the `app/data/DataPreprocessing.ipynb` notebook.

## Development
