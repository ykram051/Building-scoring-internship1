"""
Enhanced Security Authentication Module
Implements secure password hashing, session management, and role-based access control
"""
import hashlib
import secrets
import time
from datetime import datetime, timedelta
import streamlit as st
import pandas as pd
import logging
from typing import Optional, Dict, Tuple, List
import os
import re
import json

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

class SecureAuth:
    """Enhanced security authentication with proper hashing and session management"""
    
    def __init__(self):
        self.session_timeout = 3600  # 1 hour in seconds
        self.max_login_attempts = 3
        self.lockout_duration = 900  # 15 minutes
        
    def generate_salt(self) -> str:
        """Generate a random salt for password hashing"""
        return secrets.token_hex(32)
    
    def hash_password(self, password: str, salt: str = None) -> Tuple[str, str]:
        """
        Securely hash password using SHA-256 with salt
        Returns: (hashed_password, salt)
        """
        if salt is None:
            salt = self.generate_salt()
        
        # Combine password and salt
        password_salt = f"{password}{salt}"
        
        # Hash with SHA-256
        hashed = hashlib.sha256(password_salt.encode()).hexdigest()
        
        return hashed, salt
    
    def verify_password(self, password: str, hashed_password: str, salt: str) -> bool:
        """Verify password against stored hash"""
        test_hash, _ = self.hash_password(password, salt)
        return test_hash == hashed_password
    
    def validate_password_strength(self, password: str) -> Tuple[bool, List[str]]:
        """
        Validate password strength
        Returns: (is_valid, list_of_issues)
        """
        issues = []
        
        if len(password) < 8:
            issues.append("Password must be at least 8 characters long")
        
        if not re.search(r"[A-Z]", password):
            issues.append("Password must contain at least one uppercase letter")
        
        if not re.search(r"[a-z]", password):
            issues.append("Password must contain at least one lowercase letter")
        
        if not re.search(r"\d", password):
            issues.append("Password must contain at least one number")
        
        if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
            issues.append("Password must contain at least one special character")
        
        return len(issues) == 0, issues
    
    def sanitize_input(self, user_input: str) -> str:
        """Sanitize user input to prevent injection attacks"""
        if not isinstance(user_input, str):
            return str(user_input)
        
        # Remove potentially dangerous characters
        sanitized = re.sub(r'[<>"\';\\]', '', user_input)
        
        # Limit length
        sanitized = sanitized[:255]
        
        return sanitized.strip()
    
    def validate_email(self, email: str) -> bool:
        """Validate email format"""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None
    
    def initialize_session_security(self):
        """Initialize secure session state"""
        if 'session_start_time' not in st.session_state:
            st.session_state.session_start_time = time.time()
        
        if 'login_attempts' not in st.session_state:
            st.session_state.login_attempts = {}
        
        if 'user_permissions' not in st.session_state:
            st.session_state.user_permissions = {}
    
    def check_session_timeout(self) -> bool:
        """Check if session has timed out"""
        if 'session_start_time' not in st.session_state:
            return True
        
        current_time = time.time()
        elapsed_time = current_time - st.session_state.session_start_time
        
        if elapsed_time > self.session_timeout:
            self.logout_user()
            return True
        
        # Update session time on activity
        st.session_state.session_start_time = current_time
        return False
    
    def check_login_attempts(self, username: str) -> bool:
        """Check if user is locked out due to failed login attempts"""
        # Initialize login_attempts if it doesn't exist
        if not hasattr(st.session_state, 'login_attempts'):
            st.session_state.login_attempts = {}
            
        if username not in st.session_state.login_attempts:
            return True
        
        attempts_data = st.session_state.login_attempts[username]
        current_time = time.time()
        
        # Check if lockout period has expired
        if (current_time - attempts_data['last_attempt']) > self.lockout_duration:
            # Reset attempts
            st.session_state.login_attempts[username] = {
                'count': 0,
                'last_attempt': current_time
            }
            return True
        
        return attempts_data['count'] < self.max_login_attempts
    
    def record_login_attempt(self, username: str, success: bool):
        """Record login attempt for rate limiting"""
        current_time = time.time()
        
        # Initialize login_attempts if it doesn't exist
        if not hasattr(st.session_state, 'login_attempts'):
            st.session_state.login_attempts = {}
        
        if username not in st.session_state.login_attempts:
            st.session_state.login_attempts[username] = {
                'count': 0,
                'last_attempt': current_time
            }
        
        if success:
            # Reset attempts on successful login
            st.session_state.login_attempts[username] = {
                'count': 0,
                'last_attempt': current_time
            }
            logger.info(f"Successful login for user: {username}")
        else:
            # Increment failed attempts
            st.session_state.login_attempts[username]['count'] += 1
            st.session_state.login_attempts[username]['last_attempt'] = current_time
            logger.warning(f"Failed login attempt for user: {username}")
    
    def get_user_role_permissions(self, role: str) -> Dict[str, bool]:
        """Get permissions based on user role"""
        permissions = {
            'admin': {
                'view_all_datasets': True,
                'upload_datasets': True,
                'delete_datasets': True,
                'manage_users': True,
                'view_logs': True,
                'export_data': True,
                'run_analysis': True,
                'view_building_data': True,
                'city_comparison': True
            },
            'analyst': {
                'view_all_datasets': True,
                'upload_datasets': True,
                'delete_datasets': False,
                'manage_users': False,
                'view_logs': False,
                'export_data': True,
                'run_analysis': True,
                'view_building_data': True,
                'city_comparison': False
            },
            'user': {
                'view_all_datasets': False,
                'upload_datasets': True,
                'delete_datasets': False,
                'manage_users': False,
                'view_logs': False,
                'export_data': False,
                'run_analysis': True,
                'view_building_data': False,
                'city_comparison': False
            }
        }
        
        return permissions.get(role, permissions['user'])
    
    def check_permission(self, permission: str) -> bool:
        """Check if current user has specific permission"""
        if 'user_role' not in st.session_state or 'user_permissions' not in st.session_state:
            return False
        
        return st.session_state.user_permissions.get(permission, False)
    
    def logout_user(self):
        """Securely logout user and clear session"""
        username = st.session_state.get('username', 'Unknown')
        logger.info(f"User logout: {username}")
        
        # Clear sensitive session data
        sensitive_keys = [
            'username', 'user_role', 'user_permissions', 'session_start_time',
            'authenticated', 'chatbot_messages', 'chatbot_dataset'
        ]
        
        for key in sensitive_keys:
            if key in st.session_state:
                del st.session_state[key]
    
    def log_user_action(self, action: str, details: str = ""):
        """Log user actions for audit trail"""
        username = st.session_state.get('username', 'Anonymous')
        timestamp = datetime.now().isoformat()
        
        log_entry = f"{timestamp} - User: {username} - Action: {action}"
        if details:
            log_entry += f" - Details: {details}"
        
        logger.info(log_entry)
        
        # Also log to file for audit purposes
        try:
            os.makedirs('logs', exist_ok=True)
            with open('logs/user_actions.log', 'a') as f:
                f.write(log_entry + '\n')
        except Exception as e:
            logger.error(f"Failed to write to audit log: {e}")

# Global instance
secure_auth = SecureAuth()
