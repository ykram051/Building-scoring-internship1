# Comprehensive Security Implementation Guide

## Overview

This document outlines the comprehensive security measures implemented for the Building Analytics Dashboard to ensure secure multi-user operations, data protection, and audit compliance.

## Security Architecture

### Authentication & Authorization

#### Secure Password Management
- **SHA-256 with Salt**: All passwords are hashed using SHA-256 with cryptographically secure random salts
- **Password Strength Validation**: Enforced minimum requirements (8+ characters, mixed case, numbers, special characters)
- **Login Attempt Tracking**: Failed login attempts are logged and monitored for security analysis
- **Account Lockout**: Protection against brute force attacks (configurable thresholds)

#### Session Management
- **Secure Session Generation**: Cryptographically secure session tokens
- **Session Timeout**: Configurable automatic logout (default: 30 minutes of inactivity)
- **Session Validation**: Real-time session integrity checks
- **Secure Logout**: Complete session cleanup with secure token invalidation

#### Role-Based Access Control (RBAC)
- **Admin Role**: Full system access, user management, configuration changes
- **Analyst Role**: Data analysis, report generation, limited dataset access
- **User Role**: Basic dashboard access, personal data only
- **Permission Validation**: Every action checked against user permissions

### Data Security

#### Input Validation & Sanitization
- **XSS Prevention**: All user inputs sanitized and escaped
- **SQL Injection Prevention**: Parameterized queries throughout the application
- **File Upload Validation**: Type, size, and content validation for all uploads
- **Data Type Validation**: Strict typing and validation for all form inputs

#### Database Security
- **Parameterized Queries**: All database interactions use parameterized queries via SQLAlchemy
- **User Data Isolation**: Each user's data is isolated with proper access controls
- **Connection Security**: Encrypted database connections with SSL/TLS
- **Query Logging**: Database operations logged for audit purposes

#### File Security
- **User-Specific Directories**: Each user has isolated upload/data directories
- **File Type Restrictions**: Only approved file types (.csv, .json) allowed
- **Content Validation**: CSV files validated for structure and content before processing
- **Size Limitations**: Upload size limits to prevent DoS attacks
- **Secure File Paths**: Path traversal protection with secure path handling

### Audit & Logging

#### Security Event Logging
```python
# Security events tracked:
- login_attempt: User authentication attempts (success/failure)
- logout: User session termination
- permission_check: Access control validations
- session_timeout: Automatic session expiration
- password_change: Password modification events
- account_lockout: Security lockout events
```

#### Audit Trail
```python
# Audit events tracked:
- file_access: File upload/download/modification
- data_modification: Database record changes
- configuration_change: System setting modifications
- user_management: User creation/modification/deletion
- export_operations: Data export activities
```

#### Log Structure
- **Timestamp**: UTC timestamp for all events
- **User Context**: Username, session ID, IP address (when available)
- **Action Details**: Specific action performed
- **Resource Information**: Target resource/data affected
- **Success/Failure Status**: Operation outcome
- **Additional Metadata**: Relevant context information

### Production Security

#### Streamlit Configuration
```toml
[server]
enableXsrfProtection = true
enableWebsocketCompression = false
maxUploadSize = 50

[browser]
gatherUsageStats = false

[theme]
primaryColor = "#FF6B6B"
backgroundColor = "#FFFFFF"
secondaryBackgroundColor = "#F0F2F6"
textColor = "#262730"

[global]
showErrorDetails = false
developmentMode = false
```

#### Environment Security
- **Secret Management**: API keys and sensitive data in environment variables
- **Configuration Isolation**: Separate configs for development/production
- **Secure Defaults**: All security features enabled by default
- **Error Handling**: Generic error messages to prevent information leakage

#### Docker Security
```dockerfile
# Security measures in Docker configuration:
- Non-root user execution
- Minimal base images
- Dependency scanning
- Secret exclusion via .dockerignore
- Resource limitations
- Health checks
```

## Implementation Details

### Core Security Modules

#### 1. Secure Authentication (`utils/secure_auth.py`)
```python
class SecureAuth:
    """Comprehensive authentication and session management"""
    
    def hash_password(self, password: str) -> tuple:
        """Generate secure password hash with salt"""
        
    def verify_password(self, password: str, hash_password: str, salt: str) -> bool:
        """Verify password against stored hash"""
        
    def create_session(self, username: str) -> str:
        """Create secure session token"""
        
    def validate_session(self, session_token: str) -> dict:
        """Validate session and check timeout"""
```

#### 2. Secure File Handler (`utils/secure_file_handler.py`)
```python
class SecureFileHandler:
    """Secure file upload and validation"""
    
    def validate_file_type(self, file) -> bool:
        """Validate file type and extension"""
        
    def secure_file_upload(self, file, username: str) -> str:
        """Securely process and store uploaded files"""
        
    def get_user_upload_dir(self, username: str) -> Path:
        """Get user-specific upload directory"""
```

#### 3. Enhanced Logging (`utils/logger.py`)
```python
def log_security_event(event_type, username, details=None, success=True, resource=None):
    """Log security events with enhanced tracking"""
    
def log_audit_event(event_type, username, resource, action, old_value=None, new_value=None):
    """Log audit events with change tracking"""
```

### Database Security Schema

#### Security Logs Table
```sql
CREATE TABLE security_logs (
    id SERIAL PRIMARY KEY,
    event_type VARCHAR(100) NOT NULL,
    username VARCHAR(100) NOT NULL,
    details TEXT,
    success BOOLEAN NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    resource VARCHAR(255),
    session_id VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### Audit Logs Table
```sql
CREATE TABLE audit_logs (
    id SERIAL PRIMARY KEY,
    event_type VARCHAR(100) NOT NULL,
    username VARCHAR(100) NOT NULL,
    resource VARCHAR(255) NOT NULL,
    action VARCHAR(100) NOT NULL,
    old_value TEXT,
    new_value TEXT,
    timestamp TIMESTAMP NOT NULL,
    session_id VARCHAR(255),
    details TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## Security Configuration

### Environment Variables
```bash
# Required security environment variables
DATABASE_URL=postgresql://user:pass@localhost/dbname
SECRET_KEY=your-cryptographically-secure-secret-key
GEMINI_API_KEY=your-gemini-api-key
SESSION_TIMEOUT=1800  # 30 minutes in seconds
MAX_LOGIN_ATTEMPTS=5
LOCKOUT_DURATION=900  # 15 minutes in seconds
```

### File Structure Security
```
app/
├── data/
│   └── user_datasets/
│       ├── admin/
│       ├── analyst1/
│       └── user1/
├── logs/
│   ├── security.log
│   ├── audit.log
│   └── application.log
└── utils/
    ├── secure_auth.py
    ├── secure_file_handler.py
    └── logger.py
```

## Security Best Practices

### For Developers
1. **Never hardcode secrets** - Always use environment variables
2. **Validate all inputs** - Assume all user input is malicious
3. **Use parameterized queries** - Prevent SQL injection
4. **Log security events** - Maintain comprehensive audit trails
5. **Test security features** - Regular security testing and validation

### For Administrators
1. **Regular secret rotation** - Change API keys and secrets periodically
2. **Monitor logs** - Review security and audit logs regularly
3. **User access review** - Regularly audit user permissions
4. **Backup security** - Ensure secure backup procedures
5. **Update dependencies** - Keep all dependencies current

### For Users
1. **Strong passwords** - Use complex, unique passwords
2. **Regular logout** - Don't leave sessions open
3. **Report suspicious activity** - Contact administrators immediately
4. **Data handling** - Follow data classification guidelines

## Compliance & Standards

### Security Standards Alignment
- **OWASP Top 10**: Addresses all major web application security risks
- **Data Protection**: User data isolation and privacy protection
- **Audit Requirements**: Comprehensive logging for compliance
- **Access Controls**: Role-based access with principle of least privilege

### Regular Security Tasks
- [ ] Monthly security log review
- [ ] Quarterly user access audit
- [ ] Semi-annual password policy review
- [ ] Annual security architecture review
- [ ] Continuous dependency vulnerability scanning

## Incident Response

### Security Event Classification
1. **Critical**: Data breach, unauthorized admin access
2. **High**: Failed authentication spikes, privilege escalation attempts
3. **Medium**: Suspicious file uploads, unusual access patterns
4. **Low**: Individual failed logins, minor validation errors

### Response Procedures
1. **Immediate**: Secure the system, preserve evidence
2. **Assessment**: Determine scope and impact
3. **Containment**: Limit damage and prevent spread
4. **Recovery**: Restore normal operations securely
5. **Lessons Learned**: Update security measures

## Legacy Security Features (Previously Implemented)

### Role-Based Access Control (RBAC)
- Different permission sets for admin, analyst, and regular users
- Granular control of feature access based on roles

### Data Ownership Controls
- Users can only edit datasets they've uploaded
- Admins have global access to all datasets
- Analysts can view all data but only modify their own datasets

### Previous Security Logging
- Authentication events (login/logout)
- Access control decisions
- Data modifications
- Export and report generation events

## Key Security Functions

- `check_secure_feature_access()`: Validates both permission and role requirements
- `check_dataset_ownership()`: Verifies user's ownership rights to a dataset
- Logging functions for audit and security events

## Testing the Security Implementation

1. Run the test script to verify security controls:
   ```
   streamlit run app/test_auth.py
   ```

2. Check generated logs in the `logs` directory:
   - `security.log`: Contains authentication and access control events
   - `audit.log`: Contains data modification events

## Security Documentation

See the full security model documentation in `app/docs/security_model.md`
