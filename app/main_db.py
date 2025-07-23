import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import logging
import json
import os
import time
import warnings

# Configure logging to reduce verbosity
logging.basicConfig(level=logging.WARNING, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logging.getLogger('pgmpy').setLevel(logging.WARNING)
logging.getLogger('data.data_processing').setLevel(logging.WARNING)

# Suppress LightGBM warnings
logging.getLogger('lightgbm').setLevel(logging.ERROR)
warnings.filterwarnings('ignore', category=UserWarning, module='lightgbm')
warnings.filterwarnings('ignore', message='.*No further splits with positive gain.*')
# Import DB manager and initialize database connection (cached to avoid repetition)
@st.cache_resource
def get_database_manager():
    """Initialize database manager with caching to avoid repetitive connections."""
    try:
        from utils.simple_db_manager import get_simple_db_manager
        db_manager = get_simple_db_manager()
        if db_manager._initialized:
            return db_manager, "simple_db", True
        else:
            # Fall back to regular DB manager
            try:
                from utils.db_manager import get_db_manager
                db_manager = get_db_manager()
                if db_manager._initialized:
                    return db_manager, "regular_db", True
                else:
                    return None, "failed", False
            except Exception as e:
                st.warning(f"Database connection issues: {str(e)}")
                return None, "failed", False
    except Exception as e:
        st.warning(f"Database initialization failed: {str(e)}")
        return None, "failed", False

# Get cached database manager
db_manager, db_type, database_available = get_database_manager()

# Only show connection status once
if "db_connection_logged" not in st.session_state:
    if database_available and db_manager and db_manager._initialized:
        st.success(f"✅ Database connected ({db_type})")
    else:
        st.warning("⚠️ Database connection failed - using fallback mode")
    st.session_state.db_connection_logged = True

# Configure pandas display
pd.set_option("styler.render.max_elements", 500_000)

# Import database utilities and modules (with reduced logging)
if 'db_modules_imported' not in st.session_state:
    try:
        # Try importing database modules first
        if database_available:
            # Import database utilities
            from utils.db import execute_query
            
            # Import database version of data processing module
            from data.data_processing import process_city_data, get_available_cities, process_uploaded_data, process_city_with_years
            
            # Import DB version of authentication and authorization modules
            from utils.auth_db import (
                login_form, check_feature_access, check_secure_feature_access, 
                check_dataset_ownership, add_user_management, is_admin, logout
            )
            
            from utils.building_editor import display_building_editor, display_edit_history, save_building_changes
            from utils.logger import log_security_event, log_dataset_access, log_data_change
            
            auth_mode = "database"
            
        else:
            # Use fallback mode
            from utils.fallback_auth import (
                fallback_login as login_form,
                is_authenticated, get_current_user, is_admin, fallback_logout as logout
            )
            
            # Stub functions for database-specific features
            def check_feature_access(feature_name): return True
            def check_secure_feature_access(feature_name): return True
            def check_dataset_ownership(dataset_name): return True
            def add_user_management(): st.info("User management requires database connection.")
            def log_security_event(event, details): pass
            def log_dataset_access(dataset_name, username): pass
            def log_data_change(details): pass
            def display_building_editor(): st.info("Building editor requires database connection.")
            def display_edit_history(): st.info("Edit history requires database connection.")
            def save_building_changes(changes): return False
            
            # Import file-based data processing
            try:
                from data.data_processing import process_city_data, get_available_cities, process_uploaded_data, process_city_with_years
            except ImportError:
                # Create stub functions if data processing fails
                def process_city_data(city_name): return pd.DataFrame()
                def get_available_cities(): return ["Demo City"]
                def process_uploaded_data(file): return pd.DataFrame()
                def process_city_with_years(city_name, years): return pd.DataFrame()
            
            auth_mode = "fallback"
        
        st.session_state.db_modules_imported = True
        st.session_state.auth_mode = auth_mode
        db_imports_successful = True
        
    except Exception as e:
        st.error(f"Failed to import modules: {str(e)}")
        db_imports_successful = False
        st.stop()
else:
    # Modules already imported, get auth mode
    auth_mode = st.session_state.get('auth_mode', 'fallback')
    
    if auth_mode == "database" and database_available:
        from utils.db import execute_query
        from data.data_processing import process_city_data, get_available_cities, process_uploaded_data, process_city_with_years
        from utils.auth_db import (
            login_form, check_feature_access, check_secure_feature_access, 
            check_dataset_ownership, add_user_management, is_admin, logout
        )
        from utils.building_editor import display_building_editor, display_edit_history, save_building_changes
        from utils.logger import log_security_event, log_dataset_access, log_data_change
    else:
        # Use fallback imports
        from utils.fallback_auth import (
            fallback_login as login_form,
            is_authenticated, get_current_user, is_admin, fallback_logout as logout
        )
        
        # Recreate stub functions
        def check_feature_access(feature_name): return True
        def check_secure_feature_access(feature_name): return True
        def check_dataset_ownership(dataset_name): return True
        def add_user_management(): st.info("User management requires database connection.")
        def log_security_event(event, details): pass
        def log_dataset_access(dataset_name, username): pass
        def log_data_change(details): pass
        def display_building_editor(): st.info("Building editor requires database connection.")
        def display_edit_history(): st.info("Edit history requires database connection.")
        def save_building_changes(changes): return False
        
        try:
            from data.data_processing import process_city_data, get_available_cities, process_uploaded_data, process_city_with_years
        except ImportError:
            def process_city_data(city_name): return pd.DataFrame()
            def get_available_cities(): return ["Demo City"]
            def process_uploaded_data(file): return pd.DataFrame()
            def process_city_with_years(city_name, years): return pd.DataFrame()
    
    db_imports_successful = True

from models.mahalanobis import classify_mahalanobis
from models.pca import classify_pca
from models.weighted import classify_weighted
from models.tree_classifier import classify_robust_tree
from models.cosine import classify_cosine
import sys
import os
from pathlib import Path

# Add the parent directory to the Python path for importing scripts
current_dir = Path(__file__).resolve().parent
parent_dir = current_dir.parent
scripts_dir = parent_dir / "scripts"

# Add paths to sys.path if they're not already there
for path in [str(parent_dir), str(scripts_dir)]:
    if path not in sys.path:
        sys.path.insert(0, path)

try:
    from scripts.validate_data import add_classifications, validate_and_preprocess_dataset, ensure_classifications
    from scripts.compute_feature_ranges import compute_ranges
    scripts_imported = True
except ImportError as e:
    print(f"Warning: Could not import scripts: {e}")
    # Define fallback functions
    def add_classifications(df, features, weights=None):
        return df
    def validate_and_preprocess_dataset(df, scoring_basis):
        return df
    def ensure_classifications(df, features, weights=None):
        return df
    def compute_ranges(df):
        return {}
    scripts_imported = False
from visualization.map import display_map
from visualization.charts import display_relationship_plot, display_distribution_plot
from visualization.model_specific import display_model_visualization
from utils.metrics import display_metrics_overview
from utils.export import add_export_section, add_benchmark_comparison
from utils.css_loader import load_css
from pathlib import Path

# Define data directory
data_dir = Path("data")

from utils.building_selection import (
    display_building_lookup,
    display_building_classifications,
)

# Set page config with icon and expanded layout
st.set_page_config(
    page_title="Building Analytics Dashboard",
    layout="wide",
    initial_sidebar_state="expanded"
)

# In DB mode, load_city_data fetches from the database
@st.cache_data
def load_city_data(city_name):
    """Load a city dataset from the database"""
    try:
        from data.data_processing import load_city_data_db
        df_city = load_city_data_db(city_name)
        if 'year' not in df_city.columns:
            df_city['year'] = datetime.now().year
        return df_city
    except Exception as e:
        st.error(f"Error loading dataset for {city_name}: {str(e)}")
        return None

def get_filtered_df(df, year=None):
    """Get dataset filtered by year if specified"""
    if df is None:
        print("Received None dataframe in get_filtered_df")
        return None
        
    try:
        # Check if df is a DataFrame and has columns attribute
        if not hasattr(df, 'columns'):
            st.warning("Invalid dataframe object - missing columns attribute")
            return None
            
        # Check if dataframe is empty
        if df.empty:
            print("Empty dataframe in get_filtered_df")
            return df.copy()  # Return an empty copy
            
        # Filter by year if requested and possible
        if year is not None and 'year' in df.columns:
            # Check if year is in the dataframe
            available_years = df['year'].unique()
            if year not in available_years:
                print(f"Year {year} not found in dataframe. Available years: {available_years}")
                
                # If specific year not found but we have data, try to use the closest available year
                if len(available_years) > 0:
                    closest_year = min(available_years, key=lambda x: abs(x - year))
                    st.info(f"Year {year} not available. Using closest available year: {closest_year}")
                    filtered = df[df['year'] == closest_year].copy()
                    if not filtered.empty:
                        return filtered
                
                # If we couldn't find a close year or the filtered result is empty
                st.info(f"No data for year {year} in dataset. Using all available data.")
                return df.copy()
            
            filtered = df[df['year'] == year].copy()
            # Check if filtered result is empty
            if filtered.empty:
                st.info(f"No data for year {year} in dataset. Using all available data.")
                return df.copy()  # Return original data if filtered is empty
            return filtered
            
        return df.copy()
    except Exception as e:
        st.error(f"Error filtering dataframe: {e}")
        print(f"Exception in get_filtered_df: {e}")
        # Return the original dataframe if there was an error
        return df.copy() if df is not None else None

# Load CSS from external file (cached to avoid repetition)
@st.cache_resource
def load_app_css():
    """Load CSS with caching to avoid repetitive loading."""
    from utils.css_loader import load_css
    load_css("styles.css")
    return True

# Load CSS
load_app_css()

# Authentication system (only show login if not already authenticated)
auth_mode = st.session_state.get('auth_mode', 'fallback')

if auth_mode == "fallback":
    # Use fallback authentication
    if not st.session_state.get("authenticated", False):
        if not login_form():
            # If not authenticated, show only login form and stop execution
            st.stop()
    else:
        # User is already authenticated, just validate session
        if "username" not in st.session_state or not st.session_state.get("username"):
            # Session seems corrupted, reset
            st.session_state.authenticated = False
            st.rerun()
else:
    # Use database authentication
    if not st.session_state.get("authenticated", False):
        if not login_form():
            # If not authenticated, show only login form and stop execution
            st.stop()
    else:
        # User is already authenticated, just validate session
        if "username" not in st.session_state or not st.session_state.get("username"):
            # Session seems corrupted, reset
            st.session_state.authenticated = False
            st.rerun()

# Display user info and admin badge
if auth_mode == "fallback":
    user_info = get_current_user()
    username = st.session_state.get("username", "Guest")
    user_role = user_info.get("role", "user") if user_info else "user"
else:
    user_role = st.session_state.get("user_role", "user")
    username = st.session_state.get("username", "Guest")

if user_role == "admin":
    st.sidebar.markdown("### 👑 Admin Mode")
    st.sidebar.info(f"Logged in as: **{username}** (Admin)")
else:
    role_display = user_role.capitalize() if user_role else "User"
    st.sidebar.info(f"Logged in as: **{username}** ({role_display})")

# Authentication mode indicator
if auth_mode == "fallback":
    st.sidebar.caption("🔄 Fallback Authentication Mode")
else:
    st.sidebar.caption("🗃️ Database Authentication Mode")

# Add logout button
if st.sidebar.button("📤 Logout"):
    logout()
    st.rerun()  # Rerun the app to show the login form

# App header with gradient
st.markdown('<div class="main-header"><h1 style="text-align: center;"> Building Analytics Dashboard</h1></div>', unsafe_allow_html=True)

# Display DB mode status (only show once per session)
if 'db_status_shown' not in st.session_state:
    auth_mode = st.session_state.get('auth_mode', 'fallback')
    
    if database_available and db_manager and db_manager._initialized and db_imports_successful:
        st.success("✅ Database mode active - Connected to PostgreSQL database")
    elif auth_mode == "fallback":
        st.info("🔄 Running in fallback mode - Using file-based authentication and data")
        with st.expander("Database Connection Details"):
            st.warning("PostgreSQL database is not available. The app is running with limited functionality:")
            st.text("• Using file-based authentication")
            st.text("• Limited dataset management")
            st.text("• No user management features")
            st.text("• No audit logging")
            st.text("")
            st.text("To enable full functionality:")
            st.text("1. Install and start PostgreSQL")
            st.text("2. Run: docker-compose up -d")
            st.text("3. Or run: python scripts/setup_database.py")
    else:
        st.warning("⚠️ Database mode active but with issues - Check logs for details")
        with st.expander("Database Connection Details"):
            if not db_manager:
                st.error("Database manager initialization failed")
            elif not db_manager._initialized:
                st.error("Database connection not initialized")
            if not db_imports_successful:
                st.error("Database module imports failed")
    st.session_state.db_status_shown = True

# Initialize session state for comparison and data
if 'comparison_buildings' not in st.session_state:
    st.session_state['comparison_buildings'] = []
if 'current_df' not in st.session_state:
    st.session_state['current_df'] = None

# Sidebar configuration
with st.sidebar:
    st.title("Dashboard Controls")
    st.header("📊 Dataset Selection")
    
    # Get cities from the database
    available_cities = get_available_cities()
    upload_option = "Upload Custom Dataset"
    
    # Show all users' personal datasets
    if not os.path.exists(data_dir / "user_datasets"):
        os.makedirs(data_dir / "user_datasets")
    
    # Initialize user datasets tracking if not exists
    user_datasets_file = data_dir / "user_datasets" / "ownership.json"
    if not os.path.exists(user_datasets_file):
        with open(user_datasets_file, "w") as f:
            json.dump({}, f)
    
    # Load dataset ownership information
    with open(user_datasets_file, "r") as f:
        dataset_ownership = json.load(f)
    
    # Store ownership info in session state for later use
    st.session_state["dataset_ownership"] = dataset_ownership
    
    # Label user's own datasets in the dropdown
    labeled_cities = []
    for city in available_cities:
        city_label = city
        if city in dataset_ownership and dataset_ownership[city]["owner"] == st.session_state.get("username"):
            city_label = f"{city} (Your Dataset)"
        labeled_cities.append((city, city_label))
    
    # Create dataset options with custom labels
    dataset_options = [city[0] for city in labeled_cities]
    dataset_options.append(upload_option)
    
    # Create a format function to display the labels
    def format_dataset_option(option):
        if option == upload_option:
            return "➕ Upload Custom Dataset"
        for city, label in labeled_cities:
            if city == option:
                return label
        return option

    # Show a success message that we're in DB mode (only once per session)
    if 'db_mode_message_shown' not in st.session_state:
        st.success("Running in database mode")
        st.session_state.db_mode_message_shown = True

    dataset_option = st.selectbox(
        "Choose Dataset",
        dataset_options,
        format_func=format_dataset_option,
        key="dataset_option"
    )
    
    # Add Delete Dataset button for user-owned datasets or for admin users
    if dataset_option != upload_option:
        # Protected datasets that shouldn't be deleted by anyone
        protected_datasets = ["lyon", "lille", "gordes", "nancy"]
        
        # Check for permission to delete:
        # 1. Admin can delete any non-protected dataset
        # 2. Regular users can delete their own datasets
        is_admin = st.session_state.get("user_role") == "admin"
        is_owner = dataset_option in dataset_ownership and dataset_ownership[dataset_option].get("owner") == st.session_state.get("username")
        is_protected = dataset_option.lower() in protected_datasets
        
        # Show delete button if the user is admin or owner, and the dataset isn't protected
        if (is_admin or is_owner) and not is_protected:
            col1, col2 = st.columns([3, 1])
            with col2:
                # Show the delete button
                delete_button = st.button("🗑️ Delete", 
                                         key=f"delete_{dataset_option}", 
                                         help="Delete this dataset permanently",
                                         type="secondary")
                
                if delete_button:
                    # Ask for confirmation first
                    st.warning(f"Are you sure you want to permanently delete '{dataset_option}'? This cannot be undone.")
                    confirm_col1, confirm_col2 = st.columns([1, 1])
                    with confirm_col1:
                        if st.button("✓ Yes, delete it", key=f"confirm_delete_{dataset_option}", type="primary"):
                            try:
                                # Import delete_dataset function
                                from data.data_processing import delete_dataset
                                
                                # Delete the dataset
                                success, message = delete_dataset(dataset_option, st.session_state.get("username"))
                                
                                if success:
                                    st.success(f"Successfully deleted dataset: {dataset_option}")
                                    
                                    # Refresh the page to update the dataset list
                                    time.sleep(1)  # Short delay for the success message to be visible
                                    st.rerun()
                                else:
                                    st.error(f"Error deleting dataset: {message}")
                            except Exception as e:
                                st.error(f"Error: {str(e)}")
                    with confirm_col2:
                        if st.button("✗ Cancel", key=f"cancel_delete_{dataset_option}"):
                            st.info("Deletion cancelled")

    # Initialize variables
    df = None
    selected_city = None
    is_custom_data = False

    # ── 2) Handle upload branch ──
    if dataset_option == "Upload Custom Dataset":
        # Check upload permission
        if not check_secure_feature_access("upload_custom_dataset", allowed_roles=["admin", "user", "analyst"]):
            st.warning("You need appropriate privileges to upload custom datasets")
            st.stop()
            
        is_custom_data = True
        
        # Show clear information about user permissions for their own datasets
        st.markdown("""
        ### Upload Your Own Dataset
        
        When you upload your own dataset, you'll have full access to:
        - 📊 View detailed building data
        - ✏️ Edit building information
        - 📥 Export data and generate reports
        - 📈 Analyze and compare buildings
        
        Your dataset will be saved and labeled as yours for future sessions.
        """)
        
        uploaded_file = st.file_uploader(
            "Upload CSV file",
            type=["csv"],
            key="upload_custom_csv"
        )
        if not uploaded_file:
            st.info("Please upload a CSV file to proceed.")
            st.stop()

        # suggest a name (filename without extension)
        default_name = Path(uploaded_file.name).stem
        city_name = st.text_input(
            "Name this dataset:",
            value=default_name,
            key="custom_dataset_name"
        )

        if not city_name.strip():
            st.warning("Please provide a name for your dataset.")
            st.stop()

        # Process the uploaded dataset using the unified pipeline from DataPreprocessing.ipynb
        with st.spinner(f"Processing dataset for {city_name}..."):
            try:
                # Always use the process_uploaded_data function from data_processing.py
                from data.data_processing import process_uploaded_data
                
                # We're only using the standard processing now
                using_unified_pipeline = False  # This variable is kept for backward compatibility
                
                # Update the uploaded file name to match the city name provided by the user
                # This ensures the data is saved with the user-specified name
                uploaded_file.name = f"{city_name}.csv"
                
                # Show processing message
                with st.spinner(f"Processing your dataset '{city_name}'... This may take a moment."):
                    # Process the uploaded data using the optimized processing function
                    # The function now handles progress bars internally
                    city_data, processed_city_name = process_uploaded_data(
                        uploaded_file=uploaded_file,
                        username=st.session_state.get("username", "admin")
                    )
                
                if city_data is None:
                    st.error(f"Error processing uploaded dataset")
                    st.stop()
                    
                # Make sure city_name is consistent
                city_name = processed_city_name or city_name
                
                # Update dataset ownership record
                data_dir.mkdir(parents=True, exist_ok=True)
                (data_dir / "user_datasets").mkdir(parents=True, exist_ok=True)
                
                # Track dataset ownership
                user_datasets_file = data_dir / "user_datasets" / "ownership.json"
                try:
                    with open(user_datasets_file, "r") as f:
                        dataset_ownership = json.load(f)
                except (FileNotFoundError, json.JSONDecodeError):
                    dataset_ownership = {}
                
                # Add current dataset to ownership tracking
                dataset_ownership[city_name] = {
                    "owner": st.session_state.get("username", "admin"),
                    "uploaded_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "processed_with": "unified_pipeline" if using_unified_pipeline else "standard_processing"
                }
                
                # Save updated ownership information
                with open(user_datasets_file, "w") as f:
                    json.dump(dataset_ownership, f)
                    
                # Show success message
                st.success(f"Dataset '{city_name}' uploaded and processed successfully!")
                
                # Update the cities list without requiring a full page refresh
                st.session_state.available_cities = get_available_cities()
                    
                print(f"Updated dataset ownership for: {city_name}")
                
                # Update session state
                st.session_state["dataset_ownership"] = dataset_ownership
                
                # Use the full processed dataset
                df = city_data
                selected_city = city_name
                st.success(f"Successfully processed and saved dataset for {city_name}!")
                st.rerun()  # Refresh to update the city list
                
            except Exception as e:
                st.error(f"Error processing uploaded file: {str(e)}")
                import traceback
                st.error(traceback.format_exc())  # Show detailed error information
                st.stop()

    else:
        # ── 3) Load selected dataset ──
        with st.spinner(f"Loading {dataset_option} data…"):
            df_all = load_city_data(dataset_option)
            if df_all is None:
                st.error(f"Could not load dataset for {dataset_option}")
                st.stop()
                
            # Additional check for empty dataframe
            if df_all.empty:
                st.error(f"Dataset for {dataset_option} is empty")
                st.stop()
            
            # Get data for current year
            df = get_filtered_df(df_all, year=datetime.now().year)
            if df is None or len(df) == 0:
                # If no data for current year, take all data
                st.info(f"No data for current year in {dataset_option}, using all available data")
                df = df_all.copy()
                
            # Final safety check
            if df is None or df.empty:
                st.error(f"No valid data found for {dataset_option}")
                st.stop()
                
            selected_city = dataset_option

    # Cache current state
    st.session_state["current_df"] = df
    st.session_state["selected_city"] = selected_city
    st.session_state["is_custom_data"] = is_custom_data

    st.write(f"Selected city: **{selected_city}**")  
    st.write(f"Data type: {'Custom Upload' if is_custom_data else 'Built-in Dataset'}")
    
    # Scoring basis
    st.subheader("Scoring Basis")
    scoring_basis = st.radio(
        "Choose scoring basis",
        ["Total (kWh)", "Per m² (kWh/m²/year)"]
    )

    # Validate and preprocess dataset - but don't revert for custom data
    if is_custom_data:
        # For custom data, do minimal validation to preserve the processed data
        try:
            # Just ensure we have the basic structure
            if df is None or len(df) == 0:
                st.error("Invalid custom dataset")
                st.stop()
            
            # Check for essential columns
            essential_cols = ['building_id', 'Energy_Consumption', 'CO2_Usage']
            missing_cols = [col for col in essential_cols if col not in df.columns]
            
            if missing_cols:
                st.error(f"Custom dataset is missing required columns: {missing_cols}")
                st.stop()
                
        except Exception as e:
            st.error(f"Error validating custom dataset: {e}")
            st.stop()
    
    else:
        # For built-in datasets, use full validation
        df = validate_and_preprocess_dataset(df, scoring_basis)
        if df is None:
            # Try different paths for the default dataset
            default_paths = [
                "data/reduced_lyon_buildings_all_years.csv",
                "app/data/reduced_lyon_buildings_all_years.csv",
                Path(__file__).parent / "data" / "reduced_lyon_buildings_all_years.csv"
            ]
            
            for path in default_paths:
                try:
                    df = pd.read_csv(path)
                    break
                except FileNotFoundError:
                    continue
            
            if df is None or df.empty:
                st.error("Could not find default dataset. Please check your data directory.")
                st.stop()
                
            selected_city = "Lyon"
            st.warning("Invalid dataset. Reverted to default Lyon dataset")
            df = validate_and_preprocess_dataset(df, scoring_basis)

    # Replace metrics for intensity‐based scoring
    if scoring_basis == "Per m² (kWh/m²/year)":
        if "Energy_Intensity" in df.columns and "CO2_Intensity" in df.columns:
            df["Energy_Consumption"] = df["Energy_Intensity"]
            df["CO2_Usage"] = df["CO2_Intensity"]
        else:
            if is_custom_data:
                st.warning("Custom dataset doesn't have intensity columns. Using total consumption values.")
            else:
                st.error("Intensity columns not found in dataset")

    st.subheader("Classification Features")
    available_features = [
        "Energy_Consumption", "CO2_Usage", "Water_Usage",
        "Energy_Intensity", "CO2_Intensity"
    ]
    available_features = [f for f in available_features if f in df.columns]
    
    if len(available_features) == 0:
        st.error("No classification features found in dataset")
        st.stop()

    # Set default features based on what's available
    default_features = []
    if "Energy_Consumption" in available_features:
        default_features.append("Energy_Consumption")
    if "CO2_Usage" in available_features:
        default_features.append("CO2_Usage")
    if len(default_features) == 0:
        default_features = available_features[:2]  # Take first 2 available

    selected_features = st.multiselect(
        "Select Features for Classification",
        options=available_features,
        default=default_features,
        key="classification_features"
    )

    # enforce at least one feature
    if len(selected_features) < 1:
        st.error("Please select at least one feature for classification.")
        st.stop()

    # Cache in session state
    st.session_state["df"] = df
    st.session_state["city"] = selected_city
    st.session_state["is_custom_data"] = is_custom_data

    # Classification method selection
    st.header("Analysis Method")
    classification_methods = {
        "cosine Distance": "cosine Distance",
        "Mahalanobis Distance": "Mahalanobis Distance",
        "PCA Classification": "PCA Classification",
        "Weighted Classification": "Weighted Classification",
        "tree Classification": "tree Classification",
        "Topsis": "Topsis",
    }

    classification_method = st.radio(
        "Select Classification Method",
        options=list(classification_methods.keys()),
        format_func=lambda x: classification_methods[x]
    )
    
    weights = None
    if classification_method == "Weighted Classification":
        st.subheader("Enter weights for each feature")
        weights = []
        # Show a number_input for each selected feature:
        for feat in selected_features:
            w = st.number_input(
                f"Weight for {feat}",
                min_value=0.0, 
                max_value=1.0, 
                value=round(1/len(selected_features), 2),
                step=0.01,
                key=f"weight_{feat}"
            )
            weights.append(w)
    
    # Ensure classifications exist
    df = ensure_classifications(df, selected_features, weights)
        
    # Apply selected classification
    with st.spinner(f"Applying {classification_method}..."):
        class_column_mapping = {
            "cosine Distance": "class_cosine",
            "Mahalanobis Distance": "class_mahalanobis",
            "PCA Classification": "class_pca",
            "Weighted Classification": "class_weighted",
            "tree Classification": "class_tree",
            "Topsis": "class_topsis"
        }
        selected_class_column = class_column_mapping[classification_method]
        from sklearn.preprocessing import MinMaxScaler

        # Compute optimal point
        optimal_point = df[selected_features].min().values
        scaler = MinMaxScaler()
        X_scaled = scaler.fit_transform(df[selected_features])
        optimal_scaled = scaler.transform([optimal_point])[0]

        # Euclidean distances
        distances = np.linalg.norm(X_scaled - optimal_scaled, axis=1)

        # Bin distances into labels A–F
        df['class_label'] = pd.qcut(distances, q=6, labels=['A', 'B', 'C', 'D', 'E', 'F'])

        # Apply the selected classification method
        try:
            if classification_method == "cosine Distance":
                from models.cosine import classify_cosine
                df = classify_cosine(df, features=selected_features)
            elif classification_method == "Mahalanobis Distance":
                from models.mahalanobis import classify_mahalanobis
                df = classify_mahalanobis(df, features=selected_features, return_distance=True)
            elif classification_method == "PCA Classification":
                from models.pca import classify_pca
                df = classify_pca(df, features=selected_features)
            elif classification_method == "Weighted Classification":
                from models.weighted import classify_weighted
                df = classify_weighted(df, features=selected_features, weights=weights)
            elif classification_method == "tree Classification":
                from models.tree_classifier import classify_robust_tree
                df = classify_robust_tree(df, numeric_features=selected_features)
            elif classification_method == "Topsis":
                from models.topsis import classify_topsis
                df = classify_topsis(df, features=selected_features, weights=weights)
            
            # Assign class_label from the mapped column
            if selected_class_column in df.columns:
                df["class_label"] = df[selected_class_column]
            else:
                st.warning(f"Column '{selected_class_column}' not found after classification. Using default classification.")
                # Keep the existing class_label from qcut
                
        except Exception as e:
            st.error(f"Error applying {classification_method}: {e}")
            if is_custom_data:
                st.info("This might be due to custom data format. Try a different classification method.")
            # Keep the default class_label from qcut
        
        # Cache updated DataFrame
        st.session_state["df"] = df

# Check if empty
if df.empty:
    st.error("No data available. Please check your dataset.")
    st.stop()
# Advanced filters in an expander
with st.expander("🔍 Advanced Filters", expanded=False):
    col1, col2 = st.columns(2)
    
    with col1:
        co2_min, co2_max = st.slider(
            "CO₂ Usage (kg)", 
            float(df["CO2_Usage"].min()), 
            float(df["CO2_Usage"].max()), 
            (float(df["CO2_Usage"].min()), float(df["CO2_Usage"].max()))
        )
        
        water_min, water_max = st.slider(
            "Water Usage (L)", 
            float(df["Water_Usage"].min()), 
            float(df["Water_Usage"].max()), 
            (float(df["Water_Usage"].min()), float(df["Water_Usage"].max()))
        )
    
    with col2:
        energy_min, energy_max = st.slider(
            "Energy (kWh)", 
            float(df["Energy_Consumption"].min()), 
            float(df["Energy_Consumption"].max()), 
            (float(df["Energy_Consumption"].min()), float(df["Energy_Consumption"].max()))
        )
        
    
    # Class filter with colored chips
    st.subheader("Building Class Filter")
    all_classes = ['A', 'B', 'C', 'D', 'E', 'F']
    class_colors = {
        'A': '#28a745', 'B': '#5cb85c', 'C': '#ffc107',
        'D': '#fd7e14', 'E': '#dc3545', 'F': '#6c757d'
    }
    
    class_cols = st.columns(6)
    selected_classes = []
    
    for i, cls in enumerate(all_classes):
        with class_cols[i]:
            if st.checkbox(f"Class {cls}", value=True, key=f"class_{cls}"):
                selected_classes.append(cls)
    
    color_by = st.selectbox(
        "Color Buildings By", 
        ["class_label", "CO2_Usage", "Water_Usage", "Energy_Consumption"],
        format_func=lambda x: {
            "class_label": "Energy Class",
            "CO2_Usage": "CO₂ Emissions",
            "Water_Usage": "Water Consumption",
            "Energy_Consumption": "Energy Usage",
        }.get(x, x)
    )

# Filter the dataframe
filtered_df = df[
    (df["CO2_Usage"] >= co2_min) & (df["CO2_Usage"] <= co2_max) &
    (df["Water_Usage"] >= water_min) & (df["Water_Usage"] <= water_max) &
    (df["Energy_Consumption"] >= energy_min) & (df["Energy_Consumption"] <= energy_max) &
    (df["class_label"].isin(selected_classes))
]

# Info bar
col1, col2, col3 = st.columns([2, 2, 1])
with col1:
    st.info(f" Showing {len(filtered_df)} of {len(df)} buildings in {selected_city}")
with col2:
    st.metric(
        "Average Energy Class", 
        f"{filtered_df['class_label'].mode()[0] if not filtered_df.empty else 'N/A'}",
        delta=None
    )
with col3:
    st.metric(
        "Data Last Updated", 
        datetime.now().strftime("%Y-%m-%d"),
        delta=None
    )

# Define base tabs that all users can access
base_tabs = [
    "Interactive Map", 
    "Analytics & Insights", 
    "City Statistics",
    "Year-over-Year Comparison",
    "Compare Cities",
    "🤖 AI Assistant"  # New chatbot tab
]

# Define restricted tabs
tabs = base_tabs.copy()

# Check if this is a dataset uploaded by the current user
is_user_dataset = check_dataset_ownership(selected_city)
# For backward compatibility with existing code
dataset_owner = st.session_state["dataset_ownership"].get(selected_city, {}).get("owner") if st.session_state.get("dataset_ownership") else None

# Add Building Data tab only if:
# 1. User has admin/analyst permission through role OR
# 2. It's their own uploaded dataset AND they have edit_own_dataset permission
if check_secure_feature_access("view_building_data_tab", allowed_roles=["admin", "analyst"]) or (is_user_dataset and check_feature_access("edit_own_dataset")):
    tabs.insert(2, "Building Data")  # Insert after Analytics & Insights
    
# Add Export & Reports tab only if:
# 1. User has admin/analyst permission through role OR
# 2. It's their own uploaded dataset AND they have export_own_data permission
if check_secure_feature_access("view_export_reports_tab", allowed_roles=["admin", "analyst"]) or (is_user_dataset and check_feature_access("export_own_data")):
    tabs.insert(3 if "Building Data" in tabs else 2, "Export & Reports")
    
# Add Admin tab only for admin users
if st.session_state.get("user_role") == "admin":
    tabs.append("Admin Settings")
    
# Create the tabs - we'll need to handle them dynamically
tab_objects = st.tabs(tabs)

# Set up tab index tracking
tab_index = 0

# Interactive Map tab (always first)
with tab_objects[tab_index]:
    tab_index += 1
    if not filtered_df.empty:
        # Limit to maximum 2000 buildings for map display
        map_df = filtered_df.head(2000) if len(filtered_df) > 2000 else filtered_df
        if len(filtered_df) > 2000:
            st.warning(f"Map showing 2,000 of {len(filtered_df):,} buildings. Apply filters to refine results.")
        display_map(map_df, selected_city, color_by)
    else:
        st.warning("No buildings match the current filters")
        st.stop() 

    st.markdown("---")

    # Free-text lookup below the map
    st.subheader("🔎 Find a Building by Keyword")
    search_fields = [
        "adresse_ban", "nom_rue_ban", "code_postal_ban",
        "nom_commune_ban", "adresse_brut"
    ]
    building_id = display_building_lookup(
        st.session_state["df"],
        info_fields=search_fields
    )

    # Show details & "Add to Comparison"
    if building_id:
        bd = st.session_state["df"].loc[
            st.session_state["df"]["building_id"] == building_id
        ].iloc[0]

        st.markdown("### 🏢 Building Details")
        col1, col2 = st.columns([3,1])
        with col1:
            st.markdown(f"**ID:** {building_id}")
            st.markdown(f"**Class:** {bd['class_label']}")
            st.markdown(f"**CO₂ Usage:** {bd['CO2_Usage']:.1f} kg")
            st.markdown(f"**Energy Consumption:** {bd['Energy_Consumption']:.1f} kWh")
        with col2:
            if st.button("➕ Add to Comparison", key="add_to_comp"):
                existing = [b["building_id"] for b in st.session_state['comparison_buildings']]
                if building_id in existing:
                    st.warning("Already in comparison")
                else:
                    st.session_state['comparison_buildings'].append(bd.to_dict())
                    st.success("Added to comparison")

        st.markdown("---")
        display_building_classifications(st.session_state["df"], building_id)

    # Comparison table at the bottom
    if st.session_state['comparison_buildings']:
        st.markdown("---")
        st.subheader("📊 Comparison of Selected Buildings")
        comp_df = pd.DataFrame(st.session_state['comparison_buildings'])
        st.dataframe(
            comp_df[[
                "building_id", "class_label",
                "CO2_Usage", "Energy_Consumption", "Water_Usage"
            ]],
            use_container_width=True
        )


# Analytics & Insights tab (always second)
with tab_objects[tab_index]:
    tab_index += 1
    # Analytics
    analysis_tab1, analysis_tab2, analysis_tab3 = st.tabs([
        " Class Distribution", 
        " Classification Results", 
        " Relationships"
    ])
    
    with analysis_tab1:
        st.markdown("### Building Class Distribution")
        # Check if filtered_df exists and is not empty
        if filtered_df is not None and not filtered_df.empty:
            display_distribution_plot(filtered_df, color_by)
            
            # Class metrics
            st.markdown("### Class Breakdown")
            class_counts = filtered_df["class_label"].value_counts().reset_index()
            class_counts.columns = ["Class", "Count"]
            
            class_metrics = st.columns(len(class_counts))
            for i, (_, row) in enumerate(class_counts.iterrows()):
                with class_metrics[i]:
                    st.markdown(
                        f"<div class='metric-card' style='border-left: 5px solid {class_colors.get(row['Class'], '#777')};'>"
                        f"<h3 style='color: #333;'>Class {row['Class']}</h3>"
                        f"<h2 style='color: #333;'>{row['Count']}</h2>"
                        f"<p style='color: #333;'>{row['Count']/len(filtered_df)*100:.1f}% of buildings</p>"
                        f"</div>",
                        unsafe_allow_html=True
                    )
        else:
            st.warning("No valid data available for analysis. Please select a different city or dataset.")
    
    with analysis_tab2:
        st.markdown("### Classification Visualization")
        if filtered_df is not None and not filtered_df.empty:
            display_model_visualization(filtered_df, classification_method)
            st.markdown("### Classification Summary")
            st.write(f"Using **{classification_method}** to classify buildings in {selected_city}")
            
            # Metrics overview
            st.markdown('<div class="card">', unsafe_allow_html=True)
            display_metrics_overview(filtered_df)
            st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.warning("No valid data available for visualization. Please select a different city or dataset.")
    
    with analysis_tab3:
        st.markdown("### Metric Relationships")
        if not filtered_df.empty:
            display_relationship_plot(filtered_df, color_by)
            

# Building Data tab (if user has permission)
if "Building Data" in tabs:
    with tab_objects[tab_index]:
        tab_index += 1
        # Building data
        st.markdown("### Building Data Explorer")
        
        if not filtered_df.empty:
            # Search and sort options
            search_col, sort_col = st.columns(2)
            with search_col:
                search_term = st.text_input("🔍 Search by Building ID")
            
            with sort_col:
                sort_by = st.selectbox(
                    "Sort By", 
                    ["building_id", "class_label", "CO2_Usage", "Water_Usage", "Energy_Consumption"]
                )
                ascending = st.checkbox("Ascending", value=True)
            
            # Filter by search and sort
            if search_term:
                display_df = filtered_df[filtered_df["building_id"].astype(str).str.contains(search_term)]
            else:
                display_df = filtered_df
            
            display_df = display_df.sort_values(by=sort_by, ascending=ascending)
            
            # Limit rows for better rendering (e.g., 300 rows only)
            preview_df = display_df.head(300)

            st.dataframe(
                preview_df.style.format({
                    "CO2_Usage": "{:.2f}",
                    "Water_Usage": "{:.2f}",
                    "Energy_Consumption": "{:.2f}",
                    "latitude": "{:.5f}",
                    "longitude": "{:.5f}"
                }),
                use_container_width=True,
                hide_index=True
            )

        
        # Building comparison section
        if st.session_state['comparison_buildings']:
            st.markdown("### Building Comparison")
            
            # Create comparison dataframe
            comparison_df = pd.DataFrame(st.session_state['comparison_buildings'])
            
            # Display comparison
            st.dataframe(
                comparison_df[[
                    "building_id", "class_label", "CO2_Usage", "Water_Usage",
                    "Energy_Consumption"
                ]].style.format({
                    "CO2_Usage": "{:.2f}",
                    "Water_Usage": "{:.2f}",
                    "Energy_Consumption": "{:.2f}"                }),
                use_container_width=True,
                hide_index=True
            )
            
            # Comparison chart
            if len(st.session_state['comparison_buildings']) > 1:
                metrics_to_compare = ["CO2_Usage", "Water_Usage", "Energy_Consumption"]
                
                for metric in metrics_to_compare:
                    fig = {
                        "data": [{
                            "type": "bar",
                            "x": comparison_df["building_id"],
                            "y": comparison_df[metric],
                            "marker": {"color": comparison_df["class_label"].map(class_colors)}
                        }],
                        "layout": {
                            "title": f"{metric} Comparison",
                            "xaxis": {"title": "Building ID"},
                            "yaxis": {"title": metric}
                        }
                    }
                    st.plotly_chart(fig, use_container_width=True)
            
            if st.button("Clear Comparison"):
                st.session_state['comparison_buildings'] = []
                st.rerun()

        else:
            st.warning("No buildings match the current filters")

        # Building editing functionality
        # Check if user is admin or if this is their own uploaded dataset
        is_owner = check_dataset_ownership(selected_city)
        # For backward compatibility with existing code
        dataset_owner = st.session_state["dataset_ownership"].get(selected_city, {}).get("owner") if st.session_state.get("dataset_ownership") else None
        
        # More clearly show editing options for user's own datasets
        # Regular users should ONLY be able to edit their own uploaded datasets
        can_edit = (check_secure_feature_access("change_building_data", allowed_roles=["admin"]) or 
                   (is_owner and check_feature_access("edit_own_dataset")))
        
        if can_edit:
            st.markdown("---")
            editor_title = "✏️ Building Editor"
            if st.session_state.get("user_role") == "admin":
                editor_title += " (Admin)"
            elif dataset_owner == st.session_state.get("username"):
                editor_title += " (Your Dataset)"
                
            st.subheader(editor_title)
            
            # Select a building to edit
            edit_building_id = st.selectbox(
                "Select a building to edit",
                options=filtered_df["building_id"].unique(),
                format_func=lambda x: f"Building {x}",
                key="edit_building_select"
            )
            
            if edit_building_id:
                # Display building editor
                updated_df = display_building_editor(df, edit_building_id)
                
                # If building was edited, update the dataframe
                if updated_df is not None:
                    df = updated_df
                    # Re-filter the dataframe
                    filtered_df = df[
                        (df["CO2_Usage"] >= co2_min) & (df["CO2_Usage"] <= co2_max) &
                        (df["Water_Usage"] >= water_min) & (df["Water_Usage"] <= water_max) &
                        (df["Energy_Consumption"] >= energy_min) & (df["Energy_Consumption"] <= energy_max) &
                        (df["class_label"].isin(selected_classes))
                    ]
                    # Update session state
                    st.session_state["df"] = df
                    
                    # Save changes to file
                    if st.button("Save all changes to file"):
                        # In DB mode, we save to database
                        save_building_changes(df, selected_city)
                        
            # Display edit history
            with st.expander("View Edit History", expanded=False):
                display_edit_history()

        # Building comparison section
        if st.session_state['comparison_buildings']:
            st.markdown("---")
            st.subheader("📊 Comparison of Selected Buildings")
            comp_df = pd.DataFrame(st.session_state['comparison_buildings'])
            st.dataframe(
                comp_df[[
                    "building_id", "class_label",
                    "CO2_Usage", "Energy_Consumption", "Water_Usage"
                ]],
                use_container_width=True
            )

# Export & Reports tab (if user has permission)
if "Export & Reports" in tabs:
    with tab_objects[tab_index]:
        tab_index += 1
        # Export and reports
        # Check if user is admin or if this is their own uploaded dataset for export permissions
        is_owner = check_dataset_ownership(selected_city)
        # For backward compatibility with existing code
        dataset_owner = st.session_state["dataset_ownership"].get(selected_city, {}).get("owner") if st.session_state.get("dataset_ownership") else None
        
        # Regular users should ONLY be able to export their own uploaded datasets
        can_export = (check_secure_feature_access("export_data", allowed_roles=["admin", "analyst"]) or
                     (is_owner and check_feature_access("export_own_data")))
        
        if can_export:
            export_col1, export_col2 = st.columns(2)
            
            with export_col1:
                st.markdown("### Export Filtered Data")
                add_export_section(filtered_df)
            
            with export_col2:
                st.markdown("### Generate Report")
                report_name = st.text_input("Report Name", f"{selected_city} Building Analysis")
                include_map = st.checkbox("Include Map", value=True)
                include_analytics = st.checkbox("Include Analytics", value=True)
                include_raw_data = st.checkbox("Include Raw Data", value=False)
                
                if st.button("Generate PDF Report"):
                    with st.spinner("Generating report..."):
                        # This would typically connect to a report generation function
                        st.success(f"Report '{report_name}' generated successfully!")
                        st.download_button(
                            label="Download Report",
                            data=b"This would be a PDF report",  # Replace with actual PDF data
                            file_name=f"{report_name.replace(' ', '_')}.pdf",
                            mime="application/pdf"
                        )
            
            # Benchmarks section
            add_benchmark_comparison(filtered_df)
        else:
            # For users without export permission
            if is_custom_data:
                st.info("🔍 To export data from your own uploaded datasets, you need appropriate permissions. Try logging in with appropriate credentials or uploading your own dataset.")
            else:
                st.info("🔒 Admin or analyst privileges required to export data from built-in datasets")
            
            # For non-admin users, show a preview but disable export functionality
            st.markdown("### Data Preview (Export Restricted)")
            st.dataframe(
                filtered_df.head(10).style.format({
                    "CO2_Usage": "{:.2f}",
                    "Water_Usage": "{:.2f}",
                    "Energy_Consumption": "{:.2f}",
                }),
                use_container_width=True,
            )
            
            if not is_custom_data:
                st.markdown("You can upload your own dataset to have full access to export and edit features.")

# City Statistics tab (always available)
with tab_objects[tab_index]:
    tab_index += 1
    import plotly.express as px

    st.header("📊 City Statistics by Feature & Class")

    # 1) Pick method & class
    methods = {
        "PCA"        : "class_pca",
        "cosine"  : "class_cosine",
        "Mahalanobis": "class_mahalanobis",
        "Weighted"   : "class_weighted",
        "tree"   : "class_tree",
        "Topsis"     : "class_topsis",
    }
    method_name = st.selectbox("Classification Method", list(methods))
    class_col = methods[method_name]
    classes = sorted(st.session_state["df"][class_col].dropna().unique())
    selected_class = st.selectbox("Energy Class", classes)

    # 2) Features split
    consumption_feats = {
        "Energy_Consumption": "Energy (kWh)",
        "CO2_Usage":          "CO₂ (kg)",
        "Water_Usage":        "Water (L)"
    }
    intensity_feats = {
        "Energy_Intensity": "Energy Intensity (kWh/m²)",
        "CO2_Intensity":    "CO₂ Intensity (kg/m²)"
    }

    # Filter data for selected class
    dfc = st.session_state["df"]
    dfc = dfc[dfc[class_col] == selected_class]

    def compute_stats(feat_map):
        rows = []
        for feat, label in feat_map.items():
            if feat not in dfc.columns:
                continue
            mn = dfc[feat].min()
            mx = dfc[feat].max()
            avg = dfc[feat].mean()
            std = dfc[feat].std()  # Added standard deviation
            rows.append({
                "Feature": label,
                "Min": mn,
                "Mean": avg,
                "Max": mx,
                "Std": std  # Added standard deviation
            })
        return pd.DataFrame(rows)

    # 3) Consumption stats & chart
    cons_df = compute_stats(consumption_feats)
    st.subheader(f"🛢️ Consumption Stats for Class {selected_class} ({method_name})")
    st.table(cons_df[["Feature", "Min", "Mean", "Max", "Std"]].style.format({
        "Min": "{:.1f}",
        "Mean": "{:.1f}",
        "Max": "{:.1f}",
        "Std": "{:.2f}"  # Format for standard deviation
    }))

    # For chart, we'll use min, mean, max (standard deviation used for error bars)
    chart_df = cons_df[["Feature", "Min", "Mean", "Max"]].melt(
        id_vars="Feature", var_name="Stat", value_name="Value"
    )

    fig1 = px.bar(
        chart_df,
        x="Value", y="Feature", color="Stat",
        barmode="group", text="Value",
        color_discrete_map={"Min":"#A6A6A6","Mean":"#1F78B4","Max":"#333333"},
        labels={"Value":"Usage","Feature":""},
        title="Consumption: Min vs Mean vs Max",
        error_y=None  # We'll add custom error bars if needed
    )
    fig1.update_traces(texttemplate="%{text:.1f}", textposition="outside")
    fig1.update_layout(margin=dict(l=150, r=20, t=50, b=20), height=350)
    st.plotly_chart(fig1, use_container_width=True)

    # 4) Intensity stats & chart (if available)
    int_df = compute_stats(intensity_feats)
    if not int_df.empty:
        st.subheader(f"📐 Intensity Stats for Class {selected_class} ({method_name})")
        st.table(int_df[["Feature", "Min", "Mean", "Max", "Std"]].style.format({
            "Min": "{:.2f}",
            "Mean": "{:.2f}",
            "Max": "{:.2f}",
            "Std": "{:.2f}"  # Format for standard deviation
        }))
        
        # For chart, similar to above
        int_chart_df = int_df[["Feature", "Min", "Mean", "Max"]].melt(
            id_vars="Feature", var_name="Stat", value_name="Value"
        )
        
        fig2 = px.bar(
            int_chart_df,
            x="Value", y="Feature", color="Stat",
            barmode="group", text="Value",
            color_discrete_map={"Min":"#A6A6A6","Mean":"#33A02C","Max":"#333333"},
            labels={"Value":"Intensity","Feature":""},
            title="Intensity: Min vs Mean vs Max"
        )
        fig2.update_traces(texttemplate="%{text:.2f}", textposition="outside")
        fig2.update_layout(margin=dict(l=200, r=20, t=50, b=20), height=300)
        st.plotly_chart(fig2, use_container_width=True)
    else:
        st.info("No intensity columns found; showing consumption only.")

# Year-over-Year Comparison tab (always available)
with tab_objects[tab_index]:
    tab_index += 1
    st.header("📊 Year-over-Year Comparison")

    # 1) Load the full historical dataset
    if selected_city in st.session_state.get("uploaded_dfs", {}):
        df_all = st.session_state["uploaded_dfs"][selected_city]
    else:
        df_all = process_city_data(selected_city)
    
    # Check if df_all exists before validation
    if df_all is None:
        st.error(f"Could not load data for {selected_city} for year-over-year comparison.")
        st.stop()

    # 2) Validate & preprocess the entire dataset
    df_all = validate_and_preprocess_dataset(df_all, scoring_basis)
    if df_all is None or df_all.empty:
        st.error("Unable to load full historical data for year-over-year comparison.")
        st.stop()

    # 3) Ensure we have all class_* columns
    df_all = ensure_classifications(df_all, selected_features, weights)

    # 4) Re-apply classification method across all years
    if classification_method == "cosine Distance":
        from models.cosine import classify_cosine
        df_all = classify_cosine(df_all, features=selected_features)
        col = "class_cosine"
    elif classification_method == "Mahalanobis Distance":
        from models.mahalanobis import classify_mahalanobis
        df_all = classify_mahalanobis(df_all, features=selected_features, return_distance=True)
        col = "class_mahalanobis"
    elif classification_method == "PCA Classification":
        from models.pca import classify_pca
        df_all = classify_pca(df_all, features=selected_features)
        col = "class_pca"
    elif classification_method == "Weighted Classification":
        from models.weighted import classify_weighted
        df_all = classify_weighted(df_all, features=selected_features, weights=weights)
        col = "class_weighted"
    elif classification_method == "Topsis":
        from models.topsis import classify_topsis
        df_all = classify_topsis(df_all, features=selected_features, weights=weights)
        col = "class_topsis"
    else:  # tree
        from sklearn.preprocessing import MinMaxScaler
        import numpy as np

        # Ensure df_all has class_label
        if 'class_label' not in df_all.columns:
            optimal_point = df_all[selected_features].min().values
            scaler = MinMaxScaler()
            X_scaled = scaler.fit_transform(df_all[selected_features])
            optimal_scaled = scaler.transform([optimal_point])[0]
            distances = np.linalg.norm(X_scaled - optimal_scaled, axis=1)
            
            df_all['class_label'] = pd.qcut(distances, q=6, labels=['A', 'B', 'C', 'D', 'E', 'F'])

        from models.tree_classifier  import classify_robust_tree
        df_all = classify_robust_tree(df_all, numeric_features=selected_features)
        col = "class_tree"
    df_all["class_label"] = df_all[col]

    # 5) Counts by class & year
    counts = (
        df_all
        .groupby(["class_label", "year"])
        .size()
        .unstack(fill_value=0)
        .sort_index(axis=1)
    )
    st.subheader("Building Counts by Class and Year")
    st.dataframe(counts)

    years_present = list(counts.columns)

    # 6) Prepare min/max/avg tables
    metrics = {
        "Energy_Consumption": "Energy (kWh)",
        "CO2_Usage":          "CO₂ Emissions (kg)",
        "Water_Usage":        "Water Usage (L)"
    }
    data_frames = {
        m: {
            "min": pd.DataFrame(index=counts.index, columns=years_present),
            "max": pd.DataFrame(index=counts.index, columns=years_present),
            "avg": pd.DataFrame(index=counts.index, columns=years_present)
        }
        for m in metrics
    }

    for yr in years_present:
        df_y = df_all[df_all["year"] == yr]
        for cls in counts.index:
            df_c = df_y[df_y["class_label"] == cls]
            if not df_c.empty:
                for m in metrics:
                    data_frames[m]["min"].loc[cls, yr] = df_c[m].min()
                    data_frames[m]["max"].loc[cls, yr] = df_c[m].max()
                    data_frames[m]["avg"].loc[cls, yr] = df_c[m].mean()

    # 7) User controls
    col1, col2, col3 = st.columns([2,2,1])
    with col1:
        comparison_type = st.radio(
            "Select comparison type:",
            ["Minimum Values", "Maximum Values", "Average Values"],
            horizontal=True
        )
    with col2:
        selected_metric = st.selectbox(
            "Select metric to compare:",
            options=list(metrics.keys()),
            format_func=lambda x: metrics[x]
        )
    with col3:
        use_log = st.checkbox(
            "Use log scale", value=True,
            help="Log scale helps when values vary widely"
        )

    # Map the user label to our dict key
    key_map = {
        "Minimum Values": "min",
        "Maximum Values": "max",
        "Average Values": "avg"
    }
    key = key_map[comparison_type]
    values_df = data_frames[selected_metric][key]

    # 8) Plot grouped bar chart
    import plotly.graph_objects as go
    title_map = {"min": "Minimum", "max": "Maximum", "avg": "Average"}

    fig = go.Figure()
    for yr in years_present:
        yv = pd.to_numeric(values_df[yr], errors="coerce").fillna(0)
        fig.add_trace(go.Bar(
            name=str(yr),
            x=values_df.index,
            y=yv,
            text=[f"{v:,.1f}" for v in yv],
            textposition="auto"
        ))

    fig.update_layout(
        barmode="group",
        title=f"{title_map[key]} {metrics[selected_metric]} by Class Across Years",
        xaxis_title="Energy Class",
        yaxis_title=f"{title_map[key]} {metrics[selected_metric]}",
        legend_title="Year",
        height=500
    )
    if use_log:
        fig.update_layout(yaxis_type="log")

    st.plotly_chart(fig, use_container_width=True)

    # 9) Detailed table toggle
    if st.checkbox(f"Show detailed data for {title_map[key].lower()} {selected_metric}"):
        st.dataframe(values_df.style.format("{:,.2f}"), use_container_width=True)

# Compare Cities tab (always listed but may be restricted)
with tab_objects[tab_index]:
    tab_index += 1
    if check_secure_feature_access("city_comparison", allowed_roles=["admin"]):
        from datetime import datetime

        # — Helper to load & classify (no hashing on method_fn) —
        @st.cache_data(show_spinner=False)
        def load_and_prepare(city_name, year, features, weights, _method_fn, col_name, sel_class, scoring_basis):
            # Always assume DB mode in main_db.py
            try:
                # DB mode
                df = process_city_data(city_name, input_source="db", year=year)
                if df is None:
                    # Try fallback to file
                    st.info(f"Falling back to file-based data for {city_name}")
                    df = process_city_data(city_name)
            except Exception as e:
                st.error(f"Error loading data for {city_name}: {e}")
                return pd.DataFrame()  # Empty dataframe
            
            # Check if data was loaded successfully
            if df is None:
                st.warning(f"Could not load data for {city_name} (year {year})")
                return pd.DataFrame()  # Return empty dataframe
                    
            # Validate and preprocess the data
            df = validate_and_preprocess_dataset(df, scoring_basis)
            if df is None:
                st.warning(f"Data validation failed for {city_name} (year {year})")
                return pd.DataFrame()  # Return empty dataframe
                
            df = ensure_classifications(df, features, weights)
            
            # Apply classification method
            try:
                df = _method_fn(df)
                df["class_label"] = df[col_name]
                if sel_class != "All":
                    df = df[df["class_label"] == sel_class]
                return df
            except Exception as e:
                st.error(f"Error applying classification to {city_name}: {e}")
                return pd.DataFrame()  # Return empty dataframe

        # — Controls —
        # Get years - always assume DB mode in main_db.py
        try:
            # DB mode
            query = "SELECT DISTINCT year FROM buildings ORDER BY year"
            result = execute_query(query, fetch=True)
            years = sorted([row[0] for row in result])
            if not years:
                # Fallback if no years in database
                years = [datetime.now().year, datetime.now().year-1, datetime.now().year+1]
        except Exception as e:
            st.warning(f"Could not fetch years from database: {e}")
            years = [datetime.now().year, datetime.now().year-1, datetime.now().year+1]
        
        current_year = datetime.now().year
        idx = years.index(current_year) if current_year in years else 0
        sel_year = st.selectbox("Select Year to Compare", years, index=idx)

        # Get city list
        try:
            # Get all available cities
            available_compare_cities = get_available_cities()
            if not available_compare_cities:
                st.error("No cities available for comparison")
                st.stop()
        except Exception as e:
            st.error(f"Error getting available cities: {e}")
            available_compare_cities = [selected_city]  # Fallback to just the current city
            
        sel_cities = st.multiselect(
            "Cities to Compare",
            options=available_compare_cities,
            default=available_compare_cities[:min(2, len(available_compare_cities))]
        )
        if len(sel_cities) < 2:
            st.info("Please select at least two cities.")
            st.stop()

        sel_class = st.selectbox("Filter by Energy Class (optional)", ["All"] + list("ABCDEF"))

        methods = {
            "cosine":   lambda d: classify_cosine(d, features=selected_features),
            "Mahalanobis": lambda d: classify_mahalanobis(d, features=selected_features, return_distance=True),
            "PCA":         lambda d: classify_pca(d, features=selected_features),
            "Weighted":    lambda d: classify_weighted(d, features=selected_features, weights=weights),
            "tree":    lambda d: classify_robust_tree(d, numeric_features=selected_features),
            "Topsis":     lambda d: classify_topsis(d, features=selected_features, weights=weights)
        }
        cols_map = {
            "cosine":   "class_cosine",
            "Mahalanobis": "class_mahalanobis",
            "PCA":         "class_pca",
            "Weighted":    "class_weighted",
            "tree":    "class_tree",
            "Topsis":     "class_topsis"
        }
        sel_method = st.selectbox("Classification Method", list(methods.keys()))
        method_fn  = methods[sel_method]
        col_name   = cols_map[sel_method]

        # — Load & prepare each city's data —
        city_dfs = {}
        for city in sel_cities:
            dfc = load_and_prepare(
                city,
                sel_year,
                selected_features,
                weights,
                method_fn,
                col_name,
                sel_class,
                scoring_basis
            )
            if not dfc.empty:
                city_dfs[city] = dfc

        if not city_dfs:
            st.error(f"No data for {sel_year} with those filters.")
            # Display more helpful information
            st.info("Try selecting different cities or a different year.")
            
            # Try to load data without the year filter as a last resort
            retry_dfs = {}
            for city in sel_cities:
                try:
                    retry_df = load_and_prepare(
                        city,
                        None,  # No year filter
                        selected_features,
                        weights,
                        method_fn,
                        col_name,
                        sel_class,
                        scoring_basis
                    )
                    if not retry_df.empty:
                        retry_dfs[city] = retry_df
                except Exception as e:
                    st.error(f"Error loading data for {city}: {e}")
            
            if retry_dfs:
                st.success(f"Found data for {len(retry_dfs)} cities without year filter.")
                city_dfs = retry_dfs
            else:
                st.stop()

        # — Build summary DataFrame —
        records = []
        for city, dfc in city_dfs.items():
            e_col = "Energy_Consumption" if scoring_basis == "Total (kWh)" else "Energy_Intensity"
            records.append({
                "City": city,
                "Total Buildings": len(dfc),
                "Avg Energy (kWh)": dfc[e_col].mean(),
                "Avg CO₂ (kg)":     dfc["CO2_Usage"].mean(),
                "Avg Water (L)":    dfc["Water_Usage"].mean()
            })
        summary_df = pd.DataFrame(records).set_index("City")

        # — Dashboard Title & Highlights —
        st.markdown(f"## City Comparison for {sel_year}")
        best = summary_df["Avg Energy (kWh)"].idxmin()
        worst = summary_df["Avg Energy (kWh)"].idxmax()
        st.markdown(
            f"- 🔥 **Lowest average energy**: {best} ({summary_df.loc[best,'Avg Energy (kWh)']:.1f} kWh)\n"
            f"- ❄️ **Highest average energy**: {worst} ({summary_df.loc[worst,'Avg Energy (kWh)']:.1f} kWh)"
        )
        st.markdown("---")

        # — Metric Cards: Total buildings + averages —
        st.subheader("🏆 Key Metrics by City")
        metric_cols = st.columns(len(summary_df))
        for (city, row), col in zip(summary_df.iterrows(), metric_cols):
            col.markdown(f"**{city}**")
            col.metric("🏘️ Total Buildings", f"{row['Total Buildings']:,}")
            col.metric("⚡ Avg Energy",      f"{row['Avg Energy (kWh)']:.1f}")
            col.metric("🌱 Avg CO₂",         f"{row['Avg CO₂ (kg)']:.1f}")
            col.metric("💧 Avg Water",       f"{row['Avg Water (L)']:.1f}")

        st.markdown("---")

        # — Two-column charts: Grouped bar + Radar —
        left, right = st.columns(2)

        with left:
            st.subheader("📊 Multimetric Bar Chart")
            melt = summary_df.reset_index().melt(
                id_vars="City",
                value_vars=["Avg Energy (kWh)", "Avg CO₂ (kg)", "Avg Water (L)"],
                var_name="Metric",
                value_name="Value"
            )
            fig_bar = px.bar(
                melt,
                x="City",
                y="Value",
                color="Metric",
                barmode="group",
                text_auto=".1f",
                title="Avg Energy, CO₂ & Water"
            )
            fig_bar.update_layout(yaxis_title="Value", height=450)
            st.plotly_chart(fig_bar, use_container_width=True)

        with right:
            st.subheader("📊 Multimetric Radar Chart")
            radar = go.Figure()
            for city, row in summary_df.iterrows():
                radar.add_trace(go.Scatterpolar(
                    r=[row["Avg Energy (kWh)"], row["Avg CO₂ (kg)"], row["Avg Water (L)"]],
                    theta=["Energy","CO₂","Water"],
                    name=city,
                    fill="toself"
                ))
            radar.update_layout(
                polar=dict(radialaxis=dict(visible=True, tickformat=".1f")),
                showlegend=True,
                height=450,
                title="Radar: Energy vs CO₂ vs Water"
            )
            st.plotly_chart(radar, use_container_width=True)

        st.markdown("---")

        # — Feature comparison across cities by class —
        st.subheader("📊 Feature Comparison by Class Across Cities")
        
        # Define available metrics with proper display names and units
        metrics = {
            "Energy_Consumption": "Energy (kWh)",
            "CO2_Usage": "CO₂ Emissions (kg)",
            "Water_Usage": "Water Usage (L)"
        }
        
        # UI Controls
        col1, col2, col3 = st.columns([2, 2, 1])
        with col1:
            comparison_type = st.radio(
                "Select comparison type:",
                ["Minimum Values", "Maximum Values", "Average Values"],
                horizontal=True,
                key="city_comparison_type"
            )
        with col2:
            selected_metric = st.selectbox(
                "Select metric to compare:",
                options=list(metrics.keys()),
                format_func=lambda x: metrics[x],
                key="city_comparison_metric"
            )
        with col3:
            use_log_scale = st.checkbox("Log scale", value=True, 
                                       help="Logarithmic scale works better for data with large variations",
                                       key="city_log_scale")
        
        # Add explanation about multi-feature classification
        st.info(
            "📊 **Note on Classification vs. Metrics:** Buildings are classified based on multiple features "
            "(energy, CO₂, water usage), not just the selected metric. This means a Class B building might "
            "have higher values in one metric than a Class C building, while performing better on other metrics. "
            "These visualizations show actual metric values within each class, not the classification criteria."
        )
        
        # Create dataframes to store the values
        all_classes = sorted(set().union(*[set(df["class_label"]) for df in city_dfs.values()]))
        
        # Build the data for the visualization
        comparison_data = []
        
        for city, city_df in city_dfs.items():
            for cls in all_classes:
                class_data = city_df[city_df["class_label"] == cls]
                if not class_data.empty:
                    if comparison_type == "Minimum Values":
                        value = class_data[selected_metric].min()
                        type_label = "Min"
                    elif comparison_type == "Maximum Values":
                        value = class_data[selected_metric].max()
                        type_label = "Max"
                    else:  # Average Values
                        value = class_data[selected_metric].mean()
                        type_label = "Avg"
                    
                    comparison_data.append({
                        "City": city,
                        "Class": cls,
                        "Value": value,
                        "Metric": metrics[selected_metric]
                    })
        
        if comparison_data:
            # Convert to DataFrame
            comp_df = pd.DataFrame(comparison_data)
            
            # Create visualization
            fig_comp = px.bar(
                comp_df,
                x="Class",
                y="Value",
                color="City",
                barmode="group",
                title=f"{type_label} {metrics[selected_metric]} by Class Across Cities",
                labels={"Value": f"{type_label} {metrics[selected_metric]}"}
            )
            
            if use_log_scale:
                fig_comp.update_layout(yaxis_type="log")
            
            fig_comp.update_layout(height=500)
            st.plotly_chart(fig_comp, use_container_width=True)
            
            # Optional detailed data table
            if st.checkbox(f"Show detailed data for {type_label.lower()} {selected_metric}"):
                # Pivot the data for better display
                pivot_df = comp_df.pivot(index="Class", columns="City", values="Value")
                st.dataframe(
                    pivot_df.style.format("{:,.2f}"),
                    use_container_width=True
                )
            
            # Show best and worst cities for each class
            st.subheader("🏆 Best Performing Cities by Class")
            
            # Prepare a summary table
            summary_rows = []
            for cls in all_classes:
                cls_data = comp_df[comp_df["Class"] == cls]
                if not cls_data.empty:
                    if comparison_type == "Minimum Values" or comparison_type == "Average Values":
                        # For min and avg, lower is better
                        best_city = cls_data.loc[cls_data["Value"].idxmin()]["City"]
                        best_value = cls_data["Value"].min()
                        worst_city = cls_data.loc[cls_data["Value"].idxmax()]["City"]
                        worst_value = cls_data["Value"].max()
                    else:
                        # For max, higher is better
                        best_city = cls_data.loc[cls_data["Value"].idxmax()]["City"]
                        best_value = cls_data["Value"].max()
                        worst_city = cls_data.loc[cls_data["Value"].idxmin()]["City"]
                        worst_value = cls_data["Value"].min()
                    
                    summary_rows.append({
                        "Class": cls,
                        "Best City": best_city,
                        f"Best Value ({selected_metric})": best_value,
                        "Worst City": worst_city,
                        f"Worst Value ({selected_metric})": worst_value,
                        "Difference (%)": ((worst_value - best_value) / best_value * 100) if best_value != 0 else 0
                    })
            
            if summary_rows:
                summary_df = pd.DataFrame(summary_rows)
                st.dataframe(
                    summary_df.style.format({
                        f"Best Value ({selected_metric})": "{:,.2f}",
                        f"Worst Value ({selected_metric})": "{:,.2f}",
                        "Difference (%)": "{:+.1f}%"
                    }),
                    use_container_width=True
                )
        else:
            st.warning("Not enough data to compare features across cities by class.")

    else:
        st.info("🔒 Admin privileges required to access City Comparison feature")
        
        # Show a simplified preview for non-admin users
        st.markdown("### City Comparison Preview")
        st.write("This feature allows administrators to compare building metrics across different cities.")
        
        st.image("https://placehold.co/600x400?text=City+Comparison+Feature&font=roboto", 
                caption="City Comparison (Admin Access Required)")
        
        st.markdown("""
        **Features available to administrators:**
        * Compare energy usage across multiple cities
        * Analyze building class distributions between cities
        * Generate comparative reports
        * Identify trends and anomalies between regions
        
        Contact your administrator for access to this feature.
        """)

# AI Assistant tab (available to all users)
if "🤖 AI Assistant" in tabs:
    with tab_objects[tab_index]:
        tab_index += 1
        
        # Import and render chatbot
        try:
            from utils.chatbot import render_chatbot_tab, show_chat_examples
            
            # Show chat examples in sidebar
            show_chat_examples()
            
            # Render the main chatbot interface
            # Pass the current filtered dataset to the chatbot
            current_dataset = filtered_df if not filtered_df.empty else None
            render_chatbot_tab(current_dataset)
            
        except ImportError as e:
            st.error("Chatbot module not available. Please install required dependencies.")
            st.code("pip install openai langchain langchain-openai langchain-experimental pandasai tiktoken")
        except Exception as e:
            st.error(f"Error loading chatbot: {str(e)}")
            st.info("The AI Assistant requires an OpenAI API key. Please configure it in your secrets.toml file.")

st.markdown("""
    <div style="text-align: center; margin-top: 30px; padding: 10px; background-color: #f8f9fa; border-radius: 5px;">
        <p style="margin: 0; color: #1a1a1a;">Building Analytics Dashboard • Created with ❤️ • Data updated: Mai 2025</p>
    </div>
""", unsafe_allow_html=True)

# Registration system
if 'register' not in st.session_state:
    st.session_state['register'] = False

if st.session_state['register']:
    st.title("Register")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    confirm_password = st.text_input("Confirm Password", type="password")

    if st.button("Register"):
        if password != confirm_password:
            st.error("Passwords do not match")
        else:
            try:
                from utils.auth_db import register_user
                success = register_user(username, password)
                if success:
                    st.success("Registration successful! Please log in.")
                    st.session_state['register'] = False
                else:
                    st.error("Registration failed. Username might already exist.")
            except Exception as e:
                st.error(f"Error during registration: {str(e)}")

    if st.button("Back to Login"):
        st.session_state['register'] = False
else:
    if not login_form():
        if st.button("Register"):
            st.session_state['register'] = True
        st.stop()