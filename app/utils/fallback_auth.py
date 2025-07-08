"""
Fallback authentication module that works when database is not available.
This uses file-based authentication as a backup.
"""

import json
import hashlib
import logging
from pathlib import Path
import streamlit as st

logger = logging.getLogger(__name__)

class FallbackAuth:
    """File-based authentication system as fallback when database is unavailable."""
    
    def __init__(self, data_dir=None):
        """Initialize the fallback auth system."""
        if data_dir is None:
            # Default to app/data directory
            self.data_dir = Path(__file__).parent.parent / "data"
        else:
            self.data_dir = Path(data_dir)
        
        self.users_file = self.data_dir / "users.json"
        self.ensure_data_directory()
        self.ensure_default_users()
    
    def ensure_data_directory(self):
        """Ensure the data directory exists."""
        self.data_dir.mkdir(exist_ok=True)
    
    def hash_password(self, password):
        """Create SHA-256 hash of a password."""
        return hashlib.sha256(password.encode()).hexdigest()
    
    def load_users(self):
        """Load users from JSON file."""
        if not self.users_file.exists():
            return {}
        
        try:
            with open(self.users_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading users file: {e}")
            return {}
    
    def save_users(self, users):
        """Save users to JSON file."""
        try:
            with open(self.users_file, "w", encoding="utf-8") as f:
                json.dump(users, f, indent=2)
            return True
        except Exception as e:
            logger.error(f"Error saving users file: {e}")
            return False
    
    def ensure_default_users(self):
        """Ensure default users exist."""
        users = self.load_users()
        
        default_users = {
            "admin": {
                "password": self.hash_password("admin123"),
                "name": "Administrator",
                "role": "admin"
            },
            "user": {
                "password": self.hash_password("user123"),
                "name": "Regular User",
                "role": "user"
            },
            "analyst": {
                "password": self.hash_password("analyst123"),
                "name": "Data Analyst",
                "role": "analyst"
            },
            "manager": {
                "password": self.hash_password("manager123"),
                "name": "Building Manager",
                "role": "manager"
            }
        }
        
        # Add missing default users
        updated = False
        for username, user_data in default_users.items():
            if username not in users:
                users[username] = user_data
                updated = True
                logger.info(f"Created default user: {username}")
        
        if updated:
            self.save_users(users)
    
    def authenticate(self, username, password):
        """Authenticate a user."""
        users = self.load_users()
        
        if username not in users:
            return False
        
        password_hash = self.hash_password(password)
        return users[username]["password"] == password_hash
    
    def get_user_info(self, username):
        """Get user information."""
        users = self.load_users()
        
        if username not in users:
            return None
        
        user_data = users[username].copy()
        # Remove password from returned data
        user_data.pop("password", None)
        user_data["username"] = username
        
        return user_data
    
    def create_user(self, username, password, name, role):
        """Create a new user."""
        users = self.load_users()
        
        if username in users:
            return False, "User already exists"
        
        users[username] = {
            "password": self.hash_password(password),
            "name": name,
            "role": role
        }
        
        if self.save_users(users):
            return True, "User created successfully"
        else:
            return False, "Failed to save user"
    
    def list_users(self):
        """List all users (without passwords)."""
        users = self.load_users()
        result = []
        
        for username, user_data in users.items():
            user_info = user_data.copy()
            user_info.pop("password", None)
            user_info["username"] = username
            result.append(user_info)
        
        return result

# Global fallback auth instance
fallback_auth = FallbackAuth()

def fallback_login():
    """Streamlit login interface using fallback authentication."""
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    
    if not st.session_state.authenticated:
        st.title("🏢 Building Analytics Dashboard")
        st.subheader("Login (Fallback Mode)")
        
        # Show warning about fallback mode
        st.warning("⚠️ Database connection unavailable. Using file-based authentication.")
        
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submit_button = st.form_submit_button("Login")
            
            if submit_button:
                if fallback_auth.authenticate(username, password):
                    st.session_state.authenticated = True
                    st.session_state.username = username
                    st.session_state.user_info = fallback_auth.get_user_info(username)
                    st.success("Login successful!")
                    st.rerun()
                else:
                    st.error("Invalid username or password")
        
        # Show default credentials
        with st.expander("Default Login Credentials"):
            st.text("admin / admin123 (Administrator)")
            st.text("user / user123 (Regular User)")
            st.text("analyst / analyst123 (Data Analyst)")
            st.text("manager / manager123 (Building Manager)")
        
        return False
    
    return True

def fallback_logout():
    """Logout function for fallback authentication."""
    st.session_state.authenticated = False
    st.session_state.username = None
    st.session_state.user_info = None
    st.rerun()

def is_authenticated():
    """Check if user is authenticated."""
    return st.session_state.get("authenticated", False)

def get_current_user():
    """Get current user information."""
    return st.session_state.get("user_info", None)

def is_admin():
    """Check if current user is admin."""
    user_info = get_current_user()
    return user_info and user_info.get("role") == "admin"
