"""
Role-based access control for the Building Analytics Dashboard.
This module defines the available roles and their permissions.
"""

# Define all roles available in the system
ROLES = {
    "admin": {
        "description": "Administrator with full access",
        "permissions": [
            "view_dashboard", 
            "upload_custom_dataset", 
            "export_data", 
            "generate_report",
            "change_building_data",
            "user_management", 
            "city_comparison",
            "system_settings",
            "data_management",
            "view_building_data_tab",
            "view_export_reports_tab"
        ]
    },    "user": {
        "description": "Regular user with personal dataset management",
        "permissions": [
            "view_dashboard",
            "upload_custom_dataset",
            "edit_own_dataset",
            "export_own_data",
            "export_data",
            "generate_report",
            "view_building_data_tab",
            "view_export_reports_tab",
            "city_comparison"
        ]
    },
    "analyst": {
        "description": "Data analyst with export capabilities",
        "permissions": [
            "view_dashboard",
            "upload_custom_dataset",
            "export_data",
            "generate_report",
            "view_building_data_tab",
            "view_export_reports_tab",
            "city_comparison"
        ]
    },
    "manager": {
        "description": "Building manager with view and export capabilities",
        "permissions": [
            "view_dashboard",
            "upload_custom_dataset",
            "export_data",
            "generate_report",
            "change_building_data",
            "view_building_data_tab",
            "view_export_reports_tab",
            "city_comparison"
        ]
    }
}

def has_permission(user_role, permission):
    """
    Check if a user role has a specific permission
    
    Args:
        user_role (str): The role of the user
        permission (str): The permission to check
    
    Returns:
        bool: True if the user has the permission, False otherwise
    """
    if user_role not in ROLES:
        return False
    
    return permission in ROLES[user_role]["permissions"]

def get_available_roles():
    """
    Get a list of available roles
    
    Returns:
        list: List of role names
    """
    return list(ROLES.keys())

def get_role_description(role):
    """
    Get the description of a role
    
    Args:
        role (str): The role name
    
    Returns:
        str: The role description
    """
    if role not in ROLES:
        return "Unknown role"
    
    return ROLES[role]["description"]
