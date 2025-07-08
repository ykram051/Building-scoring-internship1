"""
Main application file for the Building Analytics Dashboard with PostgreSQL integration.
This version uses database-only storage and retrieval.
"""

import streamlit as st
import pandas as pd
import numpy as np
import sys
from datetime import datetime
import logging
import json
import os
from pathlib import Path

# Configure logging to suppress INFO messages from pgmpy
logging.getLogger('pgmpy').setLevel(logging.WARNING)

# Configure app-level logging
logging.basicConfig(level=logging.WARNING, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
                   
# Set data_processing logger to WARNING to reduce verbosity
logging.getLogger('data.data_processing').setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

# Set pandas display options
pd.set_option("styler.render.max_elements", 500_000)

# Import utility modules
from utils.css_loader import load_css

# Load CSS from external file
load_css("styles.css")

# Initialize database manager
from utils.db_manager import db_manager, get_db_manager

# Database is always enabled in this version
logger.info("Running in database-only mode")

# Import database-enabled modules
from utils.auth_db import (
    login_form, check_feature_access, check_secure_feature_access, 
    check_dataset_ownership, add_user_management, is_admin, logout
)
from utils.building_editor import display_building_editor, display_edit_history, save_building_changes
from utils.logger import log_security_event, log_dataset_access, log_data_change
from data.data_processing import (
    process_city_data, get_available_cities, get_available_years_for_city, get_city_dataset_id,
    get_buildings_for_city, process_uploaded_data
)

# Initialize the database manager
db_manager.initialize()
st.session_state["db_manager"] = get_db_manager()

logger.info("Database integration active")

# Import model and visualization modules (these don't change based on database mode)
from models.mahalanobis import classify_mahalanobis
from models.pca import classify_pca
from models.weighted import classify_weighted
from models.tree_classifier import classify_robust_tree
from models.cosine import classify_cosine
from scripts.validate_data import add_classifications, validate_and_preprocess_dataset, ensure_classifications
from visualization.map import display_map
from visualization.charts import display_relationship_plot, display_distribution_plot
from visualization.model_specific import display_model_visualization
from utils.metrics import display_metrics_overview
from utils.export import add_export_section, add_benchmark_comparison
from utils.building_selection import (
    display_building_lookup,
    display_building_classifications,
)
from scripts.compute_feature_ranges import compute_ranges

# Define data directory
data_dir = Path("data")

# Set page config with icon and expanded layout
st.set_page_config(
    page_title="Building Analytics Dashboard",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Authentication system
if not login_form():
    # If not authenticated, show only login form and stop execution
    st.stop()

# Log successful access
log_security_event(
    event_type="app_access",
    username=st.session_state.get("username", "unknown"),
    details={"role": st.session_state.get("user_role")},
    success=True
)

# Get cities from database based on user role
username = st.session_state.get("username", "Unknown User")
user_role = st.session_state.get("user_role", "Unknown Role")

if user_role == "admin":
    # Admins can view all datasets
    available_cities = get_available_cities()
    logger.info(f"Admin user {username} loaded all available cities: {len(available_cities)}")
else:
    # Regular users can only view their own datasets
    if "db_manager" in st.session_state:
        user_datasets = st.session_state["db_manager"].get_user_datasets(username)
        available_cities = user_datasets['city'].unique().tolist() if not user_datasets.empty else []
        logger.info(f"User {username} loaded their {len(available_cities)} cities")
    else:
        available_cities = []
        logger.warning("Database manager not initialized in session state")

CITY_PATHS = {city: city for city in available_cities}

# Create a sidebar for navigation and filters
st.sidebar.title("🏢 Building Analytics")

# Show user info
username = st.session_state.get("username", "Unknown User")
user_role = st.session_state.get("user_role", "Unknown Role")

with st.sidebar.container():
    user_col1, user_col2 = st.columns([1, 1])
    user_col1.write(f"👤 **{username}**")
    user_col2.write(f"🔑 *{user_role}*")
    
    # Show database mode
    st.sidebar.success("📊 Database Mode: Active")
    
    if st.sidebar.button("Logout"):
        logout()
        st.rerun()

# Top-level section selection
st.sidebar.subheader("Sections")
section = st.sidebar.radio(
    "Select section",
    [
        "Dashboard", 
        "Explore & Compare",
        "Admin"
    ],
    index=0,
    key="section_selector"
)

if section == "Dashboard":
    st.title("🏢 Building Analytics Dashboard")
    
    # City selection
    cities = list(CITY_PATHS.keys())
    
    if not cities:
        st.error("No city data available. Please add data files.")
        st.stop()
    
    selected_city = st.selectbox("Select City", cities, key="city_selector")
    
    if not selected_city:
        st.warning("Please select a city to continue")
        st.stop()
      # Check if this is a dataset uploaded by the current user
    is_user_dataset = check_dataset_ownership(selected_city)
    
    # Display ownership information
    if is_user_dataset:
        if st.session_state.get("user_role") == "admin":
            st.success("🔑 Admin access: You have full access to this dataset.")
        else:
            st.success("🔑 You are the owner of this dataset.")
    else:
        # If not admin and not owner, they shouldn't get this far, but just in case
        if st.session_state.get("user_role") != "admin":
            st.warning("⚠️ You do not have permission to view this dataset.")
            st.stop()
            
    # Load city data from database
    df = get_buildings_for_city(selected_city)
    
    # Store current dataset and dataframe in session state
    st.session_state["current_dataset"] = selected_city
    st.session_state["current_df"] = df
    
    if df is None or df.empty:
        st.error(f"No data available for {selected_city}")
        st.stop()
    
    # Determine available years
    available_years = sorted(df['year'].unique()) if 'year' in df.columns else [None]
    
    # Year selection if multiple years available
    if len(available_years) > 1:
        selected_year = st.selectbox("Select Year", available_years, index=0)
        filtered_df = df[df['year'] == selected_year]
    else:
        filtered_df = df
    
    # Basic dashboard content
    st.write(f"### {selected_city.capitalize()} Building Analytics")
    
    # Display summary metrics
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Buildings", f"{len(filtered_df):,}")
        
    with col2:
        if "energy_consumption" in filtered_df.columns:
            total_energy = filtered_df["energy_consumption"].sum()
            st.metric("Total Energy", f"{total_energy:,.0f} kWh")
        
    with col3:
        if "co2_usage" in filtered_df.columns:
            total_co2 = filtered_df["co2_usage"].sum()
            st.metric("CO₂ Emissions", f"{total_co2:,.0f} kg")
    
    # Display map if coordinates are available
    if "latitude" in filtered_df.columns and "longitude" in filtered_df.columns:
        st.write("### Geographic Distribution")
        color_by = st.selectbox(
            "Color buildings by",
            ["energy_consumption", "co2_usage", "water_usage", "cluster"],
            format_func=lambda x: {
                "energy_consumption": "Energy Consumption",
                "co2_usage": "CO₂ Emissions",
                "water_usage": "Water Usage",
                "cluster": "Cluster"
            }.get(x, x)
        )
        
        if color_by in filtered_df.columns:
            display_map(filtered_df, city_name=selected_city, color_by=color_by)
    
    # Add tabs for different views
    tabs = ["Overview", "Statistics"]
    
    # Only show building data tab if user has access
    if check_secure_feature_access("view_building_data_tab", allowed_roles=["admin", "analyst"]) or (is_user_dataset and check_feature_access("edit_own_dataset")):
        tabs.insert(2, "Building Data")
    
    # Only show export tab if user has access
    if check_secure_feature_access("view_export_reports_tab", allowed_roles=["admin", "analyst"]) or (is_user_dataset and check_feature_access("export_own_data")):
        tabs.append("Export & Reports")
    
    selected_tab = st.tabs(tabs)
    
    # Tab 1: Overview
    with selected_tab[0]:
        st.write("### Building Performance Overview")
        
        # Display metrics overview
        display_metrics_overview(filtered_df)
        
        # Add distribution plots
        st.write("### Distribution Analysis")
        metric_options = [col for col in ["energy_consumption", "co2_usage", "water_usage", 
                                         "energy_intensity", "co2_intensity"] 
                         if col in filtered_df.columns]
        
        if metric_options:
            selected_metric = st.selectbox("Select metric", metric_options,
                                         format_func=lambda x: x.replace("_", " ").title())
            
            if selected_metric in filtered_df.columns:
                display_distribution_plot(filtered_df, selected_metric, dataset_name=selected_city)
    
    # Tab 2: Statistics
    with selected_tab[1]:
        st.write("### Statistical Analysis")
        
        # Add correlation analysis
        st.write("#### Correlation Matrix")
        numeric_cols = [col for col in filtered_df.columns 
                      if filtered_df[col].dtype in ['float64', 'int64']
                      and col not in ['latitude', 'longitude', 'year']]
        
        if len(numeric_cols) >= 2:
            selected_metrics = st.multiselect(
                "Select metrics for correlation analysis",
                options=numeric_cols,
                default=numeric_cols[:5] if len(numeric_cols) > 5 else numeric_cols,
                format_func=lambda x: x.replace("_", " ").title()
            )
            
            if selected_metrics and len(selected_metrics) >= 2:
                display_relationship_plot(filtered_df, selected_metrics, dataset_name=selected_city)
        
        # Add building lookup
        st.write("#### Individual Building Analysis")
        display_building_lookup(filtered_df)
    
    # Tab 3: Building Data (if accessible)
    if "Building Data" in tabs:
        with selected_tab[tabs.index("Building Data")]:
            st.write("### Building Data Management")
            
            # Determine if user can edit
            can_edit = (check_secure_feature_access("change_building_data", allowed_roles=["admin"]) or 
                       (is_user_dataset and check_feature_access("edit_own_dataset")))
            
            if can_edit:
                st.info("You have edit access to this dataset")
            
            # Display building editor
            selected_building_id = st.text_input("Building ID", key="building_editor_id")
            
            if selected_building_id:
                if selected_building_id in filtered_df["building_id"].values:
                    if can_edit:
                        updated_df = display_building_editor(filtered_df, selected_building_id, selected_city)
                        if updated_df is not None:
                        # Update dataframe with edited values
                            st.session_state["current_df"] = updated_df
                    else:
                        # View-only mode
                        building_row = filtered_df[filtered_df["building_id"] == selected_building_id].iloc[0]
                        st.write("#### Building Details (View Only)")
                        st.write(f"Building ID: {selected_building_id}")
                        
                        # Display building attributes
                        for col in filtered_df.columns:
                            if col != "building_id":
                                st.write(f"{col.replace('_', ' ').title()}: {building_row[col]}")
                else:
                    st.error(f"Building ID {selected_building_id} not found")
            
            # Show edit history for admins or dataset owners
            if can_edit:
                display_edit_history()
    
    # Tab 4: Export & Reports (if accessible)
    if "Export & Reports" in tabs:
        with selected_tab[tabs.index("Export & Reports")]:
            st.write("### Export & Generate Reports")
            
            # Determine export permissions
            can_export = (check_secure_feature_access("export_data", allowed_roles=["admin", "analyst"]) or
                         (is_user_dataset and check_feature_access("export_own_data")))
            
            if can_export:
                add_export_section(filtered_df, f"{selected_city}_buildings_export")
                
                # Benchmark comparison for admins and analysts
                if check_secure_feature_access("benchmark_comparison", allowed_roles=["admin", "analyst"]):
                    add_benchmark_comparison(filtered_df, CITY_PATHS.keys())
            else:
                st.warning("You don't have permission to export this dataset")

elif section == "Explore & Compare":
    st.title("🔎 Explore & Compare")
    
    # City comparison tab for admins
    if check_secure_feature_access("city_comparison", allowed_roles=["admin"]):
        st.write("### City Comparison")
        
        available_cities = list(CITY_PATHS.keys())
        selected_cities = st.multiselect("Select Cities to Compare", available_cities,
                                       default=available_cities[:2] if len(available_cities) >= 2 else available_cities)
        
        if selected_cities and len(selected_cities) >= 2:
            # Load data for selected cities
            city_data = {}
            for city in selected_cities:                # Get data from database
                df = get_buildings_for_city(city)
                
                if df is not None and not df.empty:
                    # Add a 'city' column if it doesn't exist
                    if 'city' not in df.columns:
                        df['city'] = city
                    
                    city_data[city] = df
            
            if city_data:
                # Combine data for comparison
                combined_df = pd.concat(city_data.values())
                
                # Display comparison charts
                st.write("#### Energy Consumption Comparison")
                if "energy_consumption" in combined_df.columns:
                    fig = display_relationship_plot(combined_df, ["energy_consumption"], 
                                                  group_by="city", return_fig=True)
                    st.plotly_chart(fig, use_container_width=True)
                
                # Add more comparison plots as needed
                st.write("#### Building Classification Comparison")
                if "true_energy_label" in combined_df.columns:
                    display_building_classifications(combined_df, group_by="city")
    
    # Custom dataset upload
    st.write("### Upload Custom Dataset")
    
    if not check_secure_feature_access("upload_custom_dataset", allowed_roles=["admin", "user", "analyst"]):
        st.warning("You don't have permission to upload custom datasets")
    else:
        st.info("Upload a CSV file with building data")
        uploaded_file = st.file_uploader("Choose a CSV file", type="csv")
        
        if uploaded_file:
            with st.spinner("Processing upload..."):
                # Process the uploaded file
                result_df, dataset_name = process_uploaded_data(
                    uploaded_file, 
                    st.session_state.get("username", "unknown")
                )
                
                if result_df is not None:
                    st.success(f"Dataset '{dataset_name}' uploaded successfully with {len(result_df)} buildings")
                    
                    # Add dataset to list of available cities (for this session)
                    CITY_PATHS[dataset_name] = dataset_name
                    
                    # Show preview of uploaded data
                    st.write("#### Data Preview")
                    st.dataframe(result_df.head())
                else:
                    st.error("Failed to process uploaded file")

elif section == "Admin":
    st.title("⚙️ Administration")
    
    # Check admin access
    if not check_secure_feature_access("admin_features", allowed_roles=["admin"]):
        st.warning("You don't have permission to access the admin panel")
        st.stop()
    
    # Admin tabs
    admin_tabs = st.tabs(["User Management", "Database Status", "System Information", "Security Logs"])
    
    # User Management tab
    with admin_tabs[0]:
        st.write("### 👥 User Management")
        add_user_management()
      # Database Status tab
    with admin_tabs[1]:
        st.write("### 🗃️ Database Status")
        
        try:
            # Get database statistics
            datasets = db_manager.get_datasets()
            users = db_manager.get_users()
            
            # Show database stats
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Users", len(users))
            
            with col2:
                st.metric("Datasets", len(datasets))
            
            with col3:
                # Get building count
                result = db_manager.execute_query("SELECT COUNT(*) FROM buildings", fetch=True)
                building_count = result[0][0] if result else 0
                st.metric("Buildings", building_count)
            
            # Show recent datasets
            st.write("#### Recent Datasets")
            st.dataframe(
                datasets[["name", "city", "owner", "created_at"]].sort_values(by="created_at", ascending=False).head(10)
            )
            
            # Database connection info
            st.write("#### Database Connection")
            st.success("Connected to PostgreSQL database")
            st.info(f"Host: {os.environ.get('DB_HOST', 'localhost')}")
            st.info(f"Database: {os.environ.get('DB_NAME', 'building_analytics')}")
            
        except Exception as e:
            st.error(f"Error accessing database: {e}")
    
    # System Information tab
    with admin_tabs[2]:
        st.write("### 💻 System Information")
        
        # Python and dependencies
        st.write("#### Python Environment")
        st.code(f"""
        Python version: {sys.version}
        Pandas version: {pd.__version__}
        NumPy version: {np.__version__}
        Streamlit version: {st.__version__}
        """)
        
        # File system
        st.write("#### File System")
        st.code(f"""
        Current directory: {os.getcwd()}
        Data directory: {data_dir.absolute()}
        Number of CSV files: {len(list(data_dir.glob("*.csv")))}
        """)
          # Application state
        st.write("#### Application State")
        st.code(f"""
        Database mode: Active
        Authentication: {'Active' if st.session_state.get("authenticated") else 'Inactive'}
        Current user: {st.session_state.get("username", "None")}
        User role: {st.session_state.get("user_role", "None")}
        """)
      # Security Logs tab
    with admin_tabs[3]:
        st.write("### 🔒 Security Logs")
        
        try:
            # Get logs from database
            security_logs = db_manager.get_security_logs(limit=100)
            audit_logs = db_manager.get_audit_logs(limit=100)
            
            # Security events
            st.write("#### Security Events")
            if not security_logs.empty:
                st.dataframe(security_logs[["timestamp", "event_type", "username", "success"]])
            else:
                st.info("No security events logged yet")
            
            # Audit logs
            st.write("#### Data Changes")
            if not audit_logs.empty:
                st.dataframe(audit_logs[["timestamp", "action", "username", "dataset", "entity_id"]])
            else:
                st.info("No audit events logged yet")
            
        except Exception as e:
            st.error(f"Error retrieving logs: {e}")
                
# Footer
st.markdown("---")
st.markdown(
    "Building Analytics Dashboard | "
    f"Version 2.0 | PostgreSQL Edition | "
    f"User: {st.session_state.get('username', 'Guest')} | "
    f"Storage: Database"
)
