"""
User authentication and authorization module for the Building Analytics Dashboard.
Provides login functionality and role-based access control using PostgreSQL database.
Enhanced with security improvements.
"""

import streamlit as st
import pandas as pd
import hashlib
import json
import os
from pathlib import Path
from datetime import datetime
from utils.db import execute_query, query_to_dataframe
from utils.logger import log_security_event, log_access_attempt, log_dataset_access
from utils.secure_auth import secure_auth

def hash_password(password, salt=None):
    """Create secure SHA-256 hash of a password with salt"""
    if salt is None:
        # For backward compatibility, use old method if no salt provided
        return hashlib.sha256(password.encode()).hexdigest()
    else:
        # Use new secure method with salt
        hashed, _ = secure_auth.hash_password(password, salt)
        return hashed

def get_users_data():
    """Load users data from database"""
    # Check if we should use fallback mode
    try:
        from utils.db import should_use_fallback
        if should_use_fallback():
            # In fallback mode, don't try to load from database
            print("Fallback mode requested - empty password in configuration")
            return {}
    except ImportError:
        pass
    
    try:
        users_df = query_to_dataframe("SELECT username, password, role, name FROM users")
        
        # Convert DataFrame to dictionary format similar to previous JSON structure
        users = {}
        for _, row in users_df.iterrows():
            users[row['username']] = {
                "password": row['password'],
                "role": row['role'],
                "name": row['name']
            }
        
        return users
    except Exception as e:
        print(f"Error loading users: {e}")
        # Fallback to empty dict  
        return {}

def check_password(username, password, users_data):
    """Verify username and password with enhanced security"""
    # Check if we should use fallback mode - if so, don't use this function
    try:
        from utils.db import should_use_fallback
        if should_use_fallback():
            return False  # Let fallback auth handle it
    except ImportError:
        pass
    
    # Sanitize input
    username = secure_auth.sanitize_input(username)
    
    # Check login attempts before proceeding
    if not secure_auth.check_login_attempts(username):
        return False
    
    if username in users_data:
        stored_password = users_data[username]["password"]
        
        # Check if password uses new salt-based format (contains ':')
        if ':' in stored_password:
            stored_hash, salt = stored_password.split(':', 1)
            if secure_auth.verify_password(password, stored_hash, salt):
                # Update last login time
                try:
                    execute_query(
                        "UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE username = :username",
                        {"username": username}
                    )
                except Exception:
                    pass  # Don't fail login if update fails
                secure_auth.record_login_attempt(username, True)
                return True
            else:
                secure_auth.record_login_attempt(username, False)
                return False
        else:
            # Legacy password format - still support but recommend update
            if stored_password == hash_password(password):
                # Update last login time
                try:
                    execute_query(
                        "UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE username = :username",
                        {"username": username}
                    )
                except Exception:
                    pass  # Don't fail login if update fails
                secure_auth.record_login_attempt(username, True)
                return True
            else:
                secure_auth.record_login_attempt(username, False)
                return False
    else:
        secure_auth.record_login_attempt(username, False)
        return False

def get_user_role(username, users_data):
    """Get the role for a specific user"""
    if username in users_data:
        return users_data[username]["role"]
    return None

def is_admin(username, users_data):
    """Check if user has admin role"""
    return get_user_role(username, users_data) == "admin"

def check_authentication():
    """Check if user is authenticated and session is valid"""
    # Initialize security session
    secure_auth.initialize_session_security()
    
    # Check session timeout
    if secure_auth.check_session_timeout():
        return False
    
    # Check if authenticated
    if not st.session_state.get("authenticated", False):
        return False
    
    # Set up user permissions if not already done
    username = st.session_state.get("username")
    user_role = st.session_state.get("user_role")
    
    if username and user_role and 'user_permissions' not in st.session_state:
        permissions = secure_auth.get_user_role_permissions(user_role)
        st.session_state.user_permissions = permissions
    
    return True

def require_permission(permission: str):
    """Decorator/function to check if user has required permission"""
    if not check_authentication():
        st.error("Authentication required")
        st.stop()
    
    if not secure_auth.check_permission(permission):
        username = st.session_state.get("username", "unknown")
        log_security_event(
            event_type="access_attempt",
            username=username,
            resource=permission,
            success=False,
            details={"reason": "insufficient_permissions"}
        )
        st.error("Access denied: Insufficient permissions")
        st.stop()

def check_dataset_ownership(dataset_name: str) -> dict:
    """Check dataset ownership with enhanced security"""
    try:
        username = st.session_state.get("username")
        if not username:
            return {"owner": None, "has_access": False, "access_type": None}
        
        # Sanitize dataset name
        dataset_name = secure_auth.sanitize_input(dataset_name)
        
        # Query database for dataset ownership
        query = """
            SELECT owner, created_at, is_public 
            FROM dataset_ownership 
            WHERE dataset_name = :dataset_name
        """
        result = query_to_dataframe(query, {"dataset_name": dataset_name})
        
        if result.empty:
            return {"owner": None, "has_access": False, "access_type": None}
        
        owner = result.iloc[0]['owner']
        is_public = result.iloc[0].get('is_public', False)
        
        # Determine access
        if owner == username:
            access_type = "owner"
            has_access = True
        elif is_public:
            access_type = "public"
            has_access = True
        elif secure_auth.check_permission("view_all_datasets"):
            access_type = "admin"
            has_access = True
        else:
            access_type = None
            has_access = False
        
        # Log dataset access attempt
        log_dataset_access(username, dataset_name, f"ownership_check:{has_access}")
        
        return {
            "owner": owner,
            "has_access": has_access,
            "access_type": access_type,
            "is_public": is_public
        }
        
    except Exception as e:
        st.error(f"Error checking dataset ownership: {e}")
        return {"owner": None, "has_access": False, "access_type": None}

def logout():
    """Log out the current user with enhanced security"""
    username = st.session_state.get("username", "unknown")
    
    # Log the logout action
    secure_auth.log_user_action("logout", f"user: {username}")
    
    # Use secure logout method
    secure_auth.logout_user()
    
    # Additional cleanup
    st.session_state["authenticated"] = False
    st.session_state["username"] = None
    st.session_state["user_role"] = None
    if "comparison_buildings" in st.session_state:
        st.session_state["comparison_buildings"] = []
    if "current_df" in st.session_state:
        st.session_state["current_df"] = None
    if "change_log" in st.session_state:
        st.session_state["change_log"] = []
    
    # Log the logout event
    log_security_event("logout", username, success=True)
    return True

def login_form():
    """Display login form and handle authentication"""
    # Check if we should use fallback mode - if so, delegate to fallback auth
    try:
        from utils.db import should_use_fallback
        if should_use_fallback():
            from utils.fallback_auth import fallback_login
            return fallback_login()
    except ImportError:
        pass
    
    # Initialize session state for authentication
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False
    if "username" not in st.session_state:
        st.session_state["username"] = None
    if "user_role" not in st.session_state:
        st.session_state["user_role"] = None
    if "show_signup" not in st.session_state:
        st.session_state["show_signup"] = False
    
    # If already logged in, show logout option
    if st.session_state["authenticated"]:
        return True
    
    # Show signup form if requested
    if st.session_state.get("show_signup", False):
        signup_form()
        return False
    
    # Display login form in sidebar
    with st.sidebar:
        st.subheader("🔐 Login")
        users_data = get_users_data()
        
        # Login form
        username = st.text_input("Username", key="login_username")
        password = st.text_input("Password", type="password", key="login_password")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            login_button = st.button("Login")
        with col2:
            signup_button = st.button("Sign Up")
        with col3:
            demo_button = st.button("Demo")
        
        # Process login
        if login_button:
            if check_password(username, password, users_data):
                st.session_state["authenticated"] = True
                st.session_state["username"] = username
                st.session_state["user_role"] = get_user_role(username, users_data)
                
                # Log successful login
                log_security_event(
                    event_type="login",
                    username=username,
                    details={"role": st.session_state["user_role"]},
                    success=True
                )
                
                st.success(f"Welcome, {users_data[username].get('name', username)}!")
                return True
            else:
                # Log failed login attempt
                log_security_event(
                    event_type="login",
                    username=username,
                    details={"reason": "invalid_credentials"},
                    success=False
                )
                st.error("Invalid username or password")
        
        # Process signup button
        if signup_button:
            st.session_state["show_signup"] = True
            st.rerun()
                
        # Demo mode (unauthenticated access with limited features)
        if demo_button:
            st.session_state["authenticated"] = True
            st.session_state["username"] = "demo"
            st.session_state["user_role"] = "user"
            
            # Log demo mode login
            log_security_event(
                event_type="login",
                username="demo",
                details={"mode": "demo"},
                success=True
            )
            
            st.info("Demo mode activated - limited features available")
            return True
                
        st.info("Default credentials: admin/admin123 or user/user123")
        st.info("Or click 'Sign Up' to create a new account!")
        return False

def add_user_management():
    """Add user management UI for admin users"""
    # Only admins can manage users
    if not (st.session_state.get("authenticated") and st.session_state.get("user_role") == "admin"):
        st.warning("Admin access required to manage users")
        return
    
    from utils.roles import get_available_roles, get_role_description
    
    users_data = get_users_data()
    
    # User management section
    st.subheader("User Management")
    
    # Create new user
    with st.expander("Add New User"):
        new_username = st.text_input("Username", key="new_username")
        new_password = st.text_input("Password", type="password", key="new_password")
        new_name = st.text_input("Display Name", key="new_name")
        
        # Get available roles from roles module
        roles = get_available_roles()
        role_options = [(role, f"{role.capitalize()} - {get_role_description(role)}") for role in roles]
        
        new_role = st.selectbox(
            "Role", 
            options=[r[0] for r in role_options],
            format_func=lambda x: next((r[1] for r in role_options if r[0] == x), x),
            key="new_role"
        )
        
        if st.button("Create User"):
            if not new_username or not new_password:
                st.error("Username and password are required")
            elif new_username in users_data:
                st.error(f"Username '{new_username}' already exists")
            else:
                try:
                    # Insert the new user into the database
                    execute_query(
                        """
                        INSERT INTO users (username, password, name, role)
                        VALUES (:username, :password, :name, :role)
                        """,
                        {
                            "username": new_username,
                            "password": hash_password(new_password),
                            "name": new_name,
                            "role": new_role
                        }
                    )
                    
                    # Log user creation
                    log_security_event(
                        event_type="user_created",
                        username=st.session_state.get("username"),
                        details={"new_user": new_username, "role": new_role},
                        success=True
                    )
                    
                    st.success(f"User '{new_username}' created successfully")
                    # Refresh users data
                    users_data = get_users_data()
                except Exception as e:
                    st.error(f"Error creating user: {e}")
    
    # Edit existing users
    with st.expander("Manage Existing Users"):
        user_list = list(users_data.keys())
        if not user_list:
            st.info("No users found")
        else:
            selected_user = st.selectbox("Select User", user_list)
            
            if selected_user:
                user_info = users_data[selected_user]
                edit_name = st.text_input("Display Name", value=user_info.get("name", ""), key="edit_name")
                edit_role = st.selectbox("Role", ["user", "admin", "analyst"], 
                                       index=0 if user_info["role"] == "user" else 
                                             1 if user_info["role"] == "admin" else 2, 
                                       key="edit_role")
                change_password = st.checkbox("Change Password")
                
                if change_password:
                    new_pass = st.text_input("New Password", type="password", key="edit_password")
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("Save Changes"):
                        try:
                            # Update user in the database
                            query = """
                            UPDATE users SET 
                                name = :name, 
                                role = :role
                            """
                            
                            params = {
                                "username": selected_user,
                                "name": edit_name,
                                "role": edit_role
                            }
                            
                            if change_password and new_pass:
                                query += ", password = :password"
                                params["password"] = hash_password(new_pass)
                                
                            query += " WHERE username = :username"
                            
                            execute_query(query, params)
                            
                            # Log user update
                            log_security_event(
                                event_type="user_updated",
                                username=st.session_state.get("username"),
                                details={"target_user": selected_user, "role": edit_role},
                                success=True
                            )
                            
                            st.success(f"User '{selected_user}' updated successfully")
                            # Refresh users data
                            users_data = get_users_data()
                        except Exception as e:
                            st.error(f"Error updating user: {e}")
                
                with col2:
                    # Cannot delete yourself
                    delete_disabled = selected_user == st.session_state.get("username", "")
                    
                    if st.button("Delete User", disabled=delete_disabled):
                        # Confirm deletion
                        if st.checkbox(f"Confirm deletion of user '{selected_user}'"):
                            try:
                                # Delete user from database
                                execute_query(
                                    "DELETE FROM users WHERE username = :username",
                                    {"username": selected_user}
                                )
                                
                                # Log user deletion
                                log_security_event(
                                    event_type="user_deleted",
                                    username=st.session_state.get("username"),
                                    details={"target_user": selected_user},
                                    success=True
                                )
                                
                                st.success(f"User '{selected_user}' deleted successfully")
                                # Refresh users data
                                users_data = get_users_data()
                            except Exception as e:
                                st.error(f"Error deleting user: {e}")
                    
                    if delete_disabled:
                        st.info("Cannot delete your own account")

def check_feature_access(feature_name):
    """Check if current user has access to a specific feature"""
    # Check if we should use fallback mode - if so, always allow access
    try:
        from utils.db import should_use_fallback
        if should_use_fallback():
            return True  # In fallback mode, allow all access
    except ImportError:
        pass
    
    from utils.roles import has_permission
    
    # Get user role from session state
    user_role = st.session_state.get("user_role")
    
    # If no role is set or user is not authenticated, deny access
    if not user_role or not st.session_state.get("authenticated", False):
        return False
    
    # Check if user has permission for the requested feature
    return has_permission(user_role, feature_name)

def check_secure_feature_access(feature_name, allowed_roles=None):
    """
    Enhanced security check that verifies both permissions and roles.
    
    Args:
        feature_name (str): The feature permission to check
        allowed_roles (list): List of roles that are allowed to access this feature
                             even if they have the permission
    
    Returns:
        bool: True if user has both the permission and an allowed role
    """
    # Check if we should use fallback mode - if so, always allow access
    try:
        from utils.db import should_use_fallback
        if should_use_fallback():
            return True  # In fallback mode, allow all access
    except ImportError:
        pass
    
    # First check if the user has the basic permission
    has_permission = check_feature_access(feature_name)
    
    # If they don't have the basic permission, deny access
    if not has_permission:
        log_access_attempt(
            username=st.session_state.get("username", "unknown"),
            resource=feature_name,
            success=False,
            details={"reason": "missing_permission", "required_roles": allowed_roles}
        )
        return False
        
    # If no specific roles are required, permission alone is enough
    if allowed_roles is None:
        log_access_attempt(
            username=st.session_state.get("username", "unknown"),
            resource=feature_name,
            success=True,
            details={"reason": "has_permission"}
        )
        return True
        
    # Otherwise, also check if the user's role is in the allowed list
    user_role = st.session_state.get("user_role")
    has_role = user_role in allowed_roles
    
    # Log the access attempt with appropriate details
    log_access_attempt(
        username=st.session_state.get("username", "unknown"),
        resource=feature_name,
        success=has_role,
        details={
            "user_role": user_role,
            "allowed_roles": allowed_roles,
            "reason": "role_check" if has_role else "role_denied"
        }
    )
    
    return has_role

def check_dataset_ownership(dataset_name):
    """
    Check if the current user owns a specific dataset.
    
    Args:
        dataset_name (str): The name of the dataset to check ownership for
    
    Returns:
        bool: True if user owns the dataset or is an admin, False otherwise
    """
    # Check if we should use fallback mode - if so, always allow access
    try:
        from utils.db import should_use_fallback
        if should_use_fallback():
            return True  # In fallback mode, allow all access
    except ImportError:
        pass
    
    username = st.session_state.get("username", "unknown")
    user_role = st.session_state.get("user_role")
    
    # Admins have ownership rights to all datasets
    if user_role == "admin":
        log_dataset_access(
            username=username,
            dataset=dataset_name,
            purpose="ownership_check_admin_access"
        )
        return True
    
    try:
        # Check dataset ownership in the database
        result = execute_query(
            """
            SELECT COUNT(*) 
            FROM datasets 
            WHERE name = :name AND owner = :username
            """,
            {"name": dataset_name, "username": username},
            fetch=True
        )
        
        is_owner = result[0][0] > 0 if result else False
        
        log_dataset_access(
            username=username,
            dataset=dataset_name,
            purpose=f"ownership_check:{is_owner}"
        )
        
        return is_owner
    except Exception as e:
        # Log error and return False
        log_dataset_access(
            username=username,
            dataset=dataset_name,
            purpose="ownership_check_error"
        )
        return False

def handle_unauthorized_access(dataset_name, action_type="view"):
    """
    Handle unauthorized access attempt uniformly across the application.
    
    Args:
        dataset_name (str): The name of the dataset being accessed
        action_type (str): The type of action being attempted (view, edit, etc.)
    
    Returns:
        None: Displays error message and logs the attempt
    """
    username = st.session_state.get("username", "unknown")
    
    # Log unauthorized access attempt
    log_dataset_access(
        username=username,
        dataset=dataset_name,
        purpose=f"unauthorized_{action_type}"
    )
    
    # Show visual indicator
    st.error(f"You don't have permission to {action_type} this dataset.")
    
    # Add visual ownership indicator if appropriate
    st.warning("You can only access datasets that you own or are shared with you.")
    
    return False

def create_new_user(username, password, name, email=None):
    """Create a new user in the database"""
    try:
        # Check if username already exists
        users_data = get_users_data()
        if username in users_data:
            return False, "Username already exists"
        
        # Validate inputs
        if not username or not password or not name:
            return False, "Username, password, and name are required"
        
        if len(username) < 3:
            return False, "Username must be at least 3 characters long"
        
        if len(password) < 6:
            return False, "Password must be at least 6 characters long"
        
        # Hash the password
        password_hash = hash_password(password)
        
        # Insert new user into database
        execute_query(
            """
            INSERT INTO users (username, password, name, role)
            VALUES (:username, :password, :name, :role)
            """,
            {
                "username": username,
                "password": password_hash,
                "name": name,
                "role": "user"  # Default role for new signups
            }
        )
        
        # Log the signup event
        log_security_event(
            event_type="signup",
            username=username,
            details={"name": name},
            success=True
        )
        
        return True, "Account created successfully!"
        
    except Exception as e:
        # Log failed signup
        log_security_event(
            event_type="signup",
            username=username,
            details={"error": str(e)},
            success=False
        )
        return False, f"Error creating account: {str(e)}"

def signup_form():
    """Display signup form and handle user registration"""
    st.subheader("📝 Create Account")
    
    with st.form("signup_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            new_username = st.text_input("Username*", placeholder="Enter username (min 3 chars)")
            new_password = st.text_input("Password*", type="password", placeholder="Enter password (min 6 chars)")
        
        with col2:
            new_name = st.text_input("Full Name*", placeholder="Enter your full name")
            # Remove email input since database doesn't support it
        
        st.markdown("*Required fields")
        
        col1, col2 = st.columns(2)
        with col1:
            signup_button = st.form_submit_button("Create Account", type="primary")
        with col2:
            cancel_button = st.form_submit_button("Cancel")
        
        if signup_button:
            success, message = create_new_user(new_username, new_password, new_name)
            
            if success:
                st.success(message)
                st.info("You can now log in with your new account!")
                # Switch back to login mode
                st.session_state["show_signup"] = False
                st.rerun()
            else:
                st.error(message)
        
        if cancel_button:
            st.session_state["show_signup"] = False
            st.rerun()
