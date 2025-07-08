# Building Analytics Dashboard Security Model

## Overview

The Building Analytics Dashboard implements a comprehensive security model based on:
1. **Authentication**: Verifying user identity
2. **Role-Based Access Control**: Permissions based on user roles
3. **Data Ownership**: Access controls for user-uploaded datasets
4. **Audit Logging**: Tracking security events and data changes

## Authentication

The system provides a login mechanism that:
- Verifies usernames and passwords against a secure store
- Uses SHA-256 password hashing
- Maintains authentication state in the Streamlit session
- Supports logout to clear session data

## User Roles

The system supports the following roles:

| Role    | Description |
|---------|-------------|
| Admin   | Full access to all features and datasets |
| Analyst | Access to analytical features with limited editing capabilities |
| User    | Basic access with management of own datasets only |
| Demo    | Limited read-only access for demonstration purposes |

## Permission Model

Permissions are separate from roles and represent specific capabilities:

| Permission | Description |
|------------|-------------|
| view_building_data_tab | Access to view the building data tab |
| edit_own_dataset | Ability to edit datasets owned by the user |
| change_building_data | Ability to modify building data |
| export_data | Ability to export data |
| export_own_data | Ability to export only user-owned data |
| admin_features | Access to administrative features |

## Security Functions

### Basic Permission Check
`check_feature_access(feature_name)` - Checks if a user has permission for a specific feature based on their role.

### Enhanced Security Check
`check_secure_feature_access(feature_name, allowed_roles)` - Enhanced security that checks both:
1. Whether the user has the basic permission
2. Whether the user's role is in the allowed list

### Dataset Ownership Check
`check_dataset_ownership(dataset_name)` - Verifies if the current user:
1. Is the original uploader/owner of the dataset, or
2. Has admin privileges

## Security Workflow

1. **Authentication Flow**:
   - User enters credentials
   - System validates credentials and establishes session
   - User role and permissions are loaded

2. **Access Control Flow**:
   - User attempts to access a feature
   - System checks permissions and role requirements
   - For data operations, ownership is also verified
   - Access is granted or denied based on these checks

3. **Dataset Security Flow**:
   - Regular users can only edit and export datasets they own
   - Analysts can view all datasets but only edit their own
   - Admins have full access to all datasets

## Audit Logging

Security events are logged for audit purposes:
- Login attempts (successful and failed)
- Feature access attempts
- Data modification events
- Dataset access

## Practical Examples

**Example 1: User editing their own dataset**
```python
# User attempting to edit a dataset
is_owner = check_dataset_ownership(dataset_name)
can_edit = (check_secure_feature_access("change_building_data", allowed_roles=["admin"]) or 
           (is_owner and check_feature_access("edit_own_dataset")))
```

**Example 2: User accessing export functionality**
```python
# User attempting to export data
can_export = (check_secure_feature_access("export_data", allowed_roles=["admin", "analyst"]) or
             (is_owner and check_feature_access("export_own_data")))
```
