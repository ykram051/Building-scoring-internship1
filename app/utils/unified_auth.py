"""
Unified Authentication Manager
Consolidates functionality from secure_auth.py, auth_db.py, and fallback_auth.py
into a single, coherent authentication system with multiple backends.
"""

import hashlib
import secrets
import time
import json
import os
import re
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Tuple, List
import streamlit as st
import pandas as pd

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/security.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class UnifiedAuth:
    """Unified authentication system with multiple backends (database, file-based)"""
    
    def __init__(self, data_dir=None):
        """Initialize the unified auth system."""
        self.session_timeout = 3600  # 1 hour in seconds
        self.max_login_attempts = 3
        self.lockout_duration = 900  # 15 minutes
        self.backend = None  # Will be set to 'database' or 'file'
        
        # File-based fallback setup
        if data_dir is None:
            self.data_dir = Path(__file__).parent.parent / "data"
        else:
            self.data_dir = Path(data_dir)
        self.users_file = self.data_dir / "users.json"
        
        # Initialize backend
        self._initialize_backend()
        
    def _initialize_backend(self):
        """Initialize the appropriate authentication backend."""
        # Try database first
        if self._try_database_backend():
            self.backend = 'database'
            logger.info("Using database authentication backend")
        else:
            # Fall back to file-based
            self._ensure_file_backend()
            self.backend = 'file'
            logger.info("Using file-based authentication backend")
    
    def _try_database_backend(self):
        """Try to initialize database backend."""
        try:
            from utils.unified_db_manager import get_unified_db_manager
            db_manager = get_unified_db_manager()
            if db_manager.is_initialized():
                # Test if users table exists
                result = db_manager.execute_query("SELECT COUNT(*) FROM users LIMIT 1", fetch=True)
                return result is not None
        except Exception as e:
            logger.debug(f"Database backend not available: {e}")
        return False
    
    def _ensure_file_backend(self):
        """Ensure file-based backend is ready."""
        self.data_dir.mkdir(exist_ok=True)
        if not self.users_file.exists():
            self._create_default_users()
    
    def _create_default_users(self):
        """Create default users for file-based backend."""
        default_users = {
            "admin": {
                "password": self.hash_password("admin123")[0],
                "salt": self.hash_password("admin123")[1],
                "role": "admin",
                "name": "Administrator",
                "created_at": datetime.now().isoformat()
            },
            "user": {
                "password": self.hash_password("user123")[0],
                "salt": self.hash_password("user123")[1],
                "role": "user", 
                "name": "Default User",
                "created_at": datetime.now().isoformat()
            }
        }
        
        try:
            with open(self.users_file, "w", encoding="utf-8") as f:
                json.dump(default_users, f, indent=2)
            logger.info("Created default users file")
        except Exception as e:
            logger.error(f"Error creating default users file: {e}")
    
    def generate_salt(self) -> str:
        """Generate a random salt for password hashing."""
        return secrets.token_hex(32)
    
    def hash_password(self, password: str, salt: str = None) -> Tuple[str, str]:
        """
        Securely hash password using SHA-256 with salt.
        Returns: (hashed_password, salt)
        """
        if salt is None:
            salt = self.generate_salt()
        
        # Combine password and salt
        password_salt = f"{password}{salt}"
        
        # Hash with SHA-256
        hashed = hashlib.sha256(password_salt.encode('utf-8')).hexdigest()
        
        return hashed, salt
    
    def verify_password(self, password: str, stored_hash: str, salt: str = None) -> bool:
        """Verify a password against its hash."""
        if salt:
            # New method with salt
            test_hash, _ = self.hash_password(password, salt)
            return test_hash == stored_hash
        else:
            # Legacy method without salt for backward compatibility
            legacy_hash = hashlib.sha256(password.encode()).hexdigest()
            return legacy_hash == stored_hash
    
    def get_users_data(self) -> Dict:
        """Load users data from the active backend."""
        if self.backend == 'database':
            return self._get_users_from_database()
        else:
            return self._get_users_from_file()
    
    def _get_users_from_database(self) -> Dict:
        """Load users from database."""
        try:
            from utils.unified_db_manager import get_unified_db_manager
            db_manager = get_unified_db_manager()
            
            # Try to get users with salt column first (new schema)
            users_df = None
            has_salt = False
            
            try:
                users_df = db_manager.dataframe_from_query(
                    "SELECT username, password, salt, role, name FROM users"
                )
                if users_df is not None and not users_df.empty:
                    has_salt = True
                    logger.debug("Using new database schema with salt column")
                else:
                    users_df = None  # Force fallback
            except Exception as e:
                logger.debug(f"Salt column query failed: {e}")
                users_df = None  # Force fallback
            
            # If first query failed or returned empty, try without salt column
            if users_df is None or users_df.empty:
                try:
                    users_df = db_manager.dataframe_from_query(
                        "SELECT username, password, role, name FROM users"
                    )
                    has_salt = False
                    logger.debug("Using legacy database schema without salt column")
                except Exception as e:
                    logger.error(f"Both database queries failed: {e}")
                    return {}
            
            if users_df is None or users_df.empty:
                logger.warning("No users found in database")
                return {}
            
            users = {}
            for _, row in users_df.iterrows():
                user_data = {
                    "password": row['password'],
                    "role": row['role'],
                    "name": row['name']
                }
                if has_salt and 'salt' in row and pd.notna(row['salt']):
                    user_data["salt"] = row['salt']
                    
                users[row['username']] = user_data
                
            logger.debug(f"Loaded {len(users)} users from database (has_salt={has_salt})")
            return users
        except Exception as e:
            logger.error(f"Error loading users from database: {e}")
            return {}
    
    def _get_users_from_file(self) -> Dict:
        """Load users from JSON file."""
        if not self.users_file.exists():
            return {}
        
        try:
            with open(self.users_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading users file: {e}")
            return {}
    
    def authenticate_user(self, username: str, password: str) -> Tuple[bool, Optional[Dict], str]:
        """
        Authenticate a user.
        Returns: (success, user_info, message)
        """
        users = self.get_users_data()
        
        if username not in users:
            logger.warning(f"Login attempt for non-existent user: {username}")
            return False, None, "Invalid username or password"
        
        user_info = users[username]
        
        # Check password
        salt = user_info.get('salt')
        if self.verify_password(password, user_info['password'], salt):
            logger.info(f"Successful login for user: {username}")
            return True, user_info, "Login successful"
        else:
            logger.warning(f"Failed login attempt for user: {username}")
            return False, None, "Invalid username or password"
    
    def create_user(self, username: str, password: str, role: str = "user", name: str = None) -> Tuple[bool, str]:
        """
        Create a new user.
        Returns: (success, message)
        """
        users = self.get_users_data()
        
        if username in users:
            return False, "Username already exists"
        
        # Hash password with salt
        hashed_password, salt = self.hash_password(password)
        
        user_data = {
            "password": hashed_password,
            "salt": salt,
            "role": role,
            "name": name or username,
            "created_at": datetime.now().isoformat()
        }
        
        if self.backend == 'database':
            return self._create_user_in_database(username, user_data)
        else:
            return self._create_user_in_file(username, user_data)
    
    def _create_user_in_database(self, username: str, user_data: Dict) -> Tuple[bool, str]:
        """Create user in database."""
        try:
            from utils.unified_db_manager import get_unified_db_manager
            db_manager = get_unified_db_manager()
            
            db_manager.execute_query(
                """
                INSERT INTO users (username, password, salt, role, name, created_at)
                VALUES (:username, :password, :salt, :role, :name, :created_at)
                """,
                {
                    "username": username,
                    "password": user_data["password"],
                    "salt": user_data["salt"],
                    "role": user_data["role"],
                    "name": user_data["name"],
                    "created_at": user_data["created_at"]
                },
                fetch=False
            )
            return True, "User created successfully"
        except Exception as e:
            logger.error(f"Error creating user in database: {e}")
            return False, f"Error creating user: {str(e)}"
    
    def _create_user_in_file(self, username: str, user_data: Dict) -> Tuple[bool, str]:
        """Create user in file."""
        try:
            users = self.get_users_data()
            users[username] = user_data
            
            with open(self.users_file, "w", encoding="utf-8") as f:
                json.dump(users, f, indent=2)
            
            return True, "User created successfully"
        except Exception as e:
            logger.error(f"Error creating user in file: {e}")
            return False, f"Error creating user: {str(e)}"
    
    def get_backend_type(self) -> str:
        """Get the current backend type."""
        return self.backend
    
    def validate_password_strength(self, password: str) -> Tuple[bool, str]:
        """Validate password strength."""
        if len(password) < 8:
            return False, "Password must be at least 8 characters long"
        
        if not re.search(r"[A-Za-z]", password):
            return False, "Password must contain at least one letter"
        
        if not re.search(r"\d", password):
            return False, "Password must contain at least one number"
        
        return True, "Password strength is acceptable"

# Create a singleton instance
_unified_auth = UnifiedAuth()

def get_unified_auth():
    """Get the unified authentication instance."""
    return _unified_auth

def authenticate_user(username: str, password: str):
    """Authenticate user using unified auth system."""
    return _unified_auth.authenticate_user(username, password)

def create_user(username: str, password: str, role: str = "user", name: str = None):
    """Create user using unified auth system."""
    return _unified_auth.create_user(username, password, role, name)

def get_users_data():
    """Get users data using unified auth system."""
    return _unified_auth.get_users_data()

# Compatibility functions for existing codebase
def login_form():
    """Display login form compatible with existing main_db.py."""
    import streamlit as st
    
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    
    if not st.session_state.authenticated:
        st.title("🏢 Building Analytics Dashboard - Login")
        
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submit = st.form_submit_button("Login")
            
            if submit:
                success, user_info, message = _unified_auth.authenticate_user(username, password)
                
                if success:
                    st.session_state.authenticated = True
                    st.session_state.username = username
                    st.session_state.user_role = user_info.get('role', 'user')
                    st.session_state.user_name = user_info.get('name', username)
                    st.success(message)
                    st.rerun()
                else:
                    st.error(message)
        
        return False
    return True

def check_feature_access(feature_name, allowed_roles=None):
    """Check if current user has access to a feature."""
    if "authenticated" not in st.session_state or not st.session_state.authenticated:
        return False
    
    if allowed_roles:
        user_role = st.session_state.get('user_role', 'user')
        return user_role in allowed_roles
    
    return True

def check_secure_feature_access(feature_name, allowed_roles=None):
    """Check if current user has secure access to a feature."""
    return check_feature_access(feature_name, allowed_roles)

def check_dataset_ownership(dataset_name):
    """Check if current user owns a dataset."""
    return True  # Simplified for now

def is_admin():
    """Check if current user is admin."""
    return st.session_state.get('user_role') == 'admin'

def get_current_user():
    """Get current user."""
    return st.session_state.get('username')

def get_user_role():
    """Get current user role."""
    return st.session_state.get('user_role', 'user')

def is_authenticated():
    """Check if user is authenticated."""
    return st.session_state.get('authenticated', False)

def logout():
    """Log out current user."""
    import streamlit as st
    for key in ['authenticated', 'username', 'user_role', 'user_name']:
        if key in st.session_state:
            del st.session_state[key]
    st.rerun()

def add_user_management():
    """Display user management interface."""
    import streamlit as st
    
    if not is_admin():
        st.error("Access denied. Admin privileges required.")
        return
    
    st.subheader("User Management")
    
    # Create new user
    with st.expander("Create New User"):
        with st.form("create_user"):
            new_username = st.text_input("Username")
            new_password = st.text_input("Password", type="password")
            new_role = st.selectbox("Role", ["user", "admin"])
            new_name = st.text_input("Full Name")
            
            if st.form_submit_button("Create User"):
                success, message = _unified_auth.create_user(new_username, new_password, new_role, new_name)
                if success:
                    st.success(message)
                else:
                    st.error(message)
    
    # List existing users
    st.subheader("Existing Users")
    users = _unified_auth.get_users_data()
    if users:
        users_df = pd.DataFrame.from_dict(users, orient='index')
        users_df = users_df[['name', 'role']].reset_index()
        users_df.columns = ['Username', 'Full Name', 'Role']
        st.dataframe(users_df)
