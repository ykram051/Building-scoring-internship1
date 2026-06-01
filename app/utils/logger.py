"""
Enhanced Unified Logging Module

This module provides centralized logging for security and audit events.
Supports logging to both local files and PostgreSQL databases with enhanced security features.
"""

import logging
import os
import json
from datetime import datetime
from pathlib import Path

# Set up logging directory
LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

# Enhanced security configuration
class SecurityLogger:
    """Enhanced security logger with structured logging"""
    
    def __init__(self):
        # Configure security logger
        self.security_logger = logging.getLogger("security")
        self.security_logger.setLevel(logging.INFO)
        
        # Configure audit logger  
        self.audit_logger = logging.getLogger("audit")
        self.audit_logger.setLevel(logging.INFO)
        
        # Configure application logger
        self.app_logger = logging.getLogger("application")
        self.app_logger.setLevel(logging.INFO)
        
        self._setup_handlers()
    
    def _setup_handlers(self):
        """Set up file handlers with proper formatting"""
        # Security events handler
        security_file = LOG_DIR / "security.log"
        security_handler = logging.FileHandler(security_file, encoding='utf-8')
        security_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        security_handler.setFormatter(security_formatter)
        if not self.security_logger.handlers:
            self.security_logger.addHandler(security_handler)
        
        # Audit events handler
        audit_file = LOG_DIR / "audit.log"
        audit_handler = logging.FileHandler(audit_file, encoding='utf-8')
        audit_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        audit_handler.setFormatter(audit_formatter)
        if not self.audit_logger.handlers:
            self.audit_logger.addHandler(audit_handler)
        
        # Application handler
        app_file = LOG_DIR / "application.log"
        app_handler = logging.FileHandler(app_file, encoding='utf-8')
        app_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        app_handler.setFormatter(app_formatter)
        if not self.app_logger.handlers:
            self.app_logger.addHandler(app_handler)
    
    def get_client_info(self):
        """Get client information from session"""
        try:
            # Basic client info - can be enhanced with Streamlit session data
            client_info = {
                'session_id': 'unknown',
                'user_agent': 'unknown',
                'ip_address': 'unknown'
            }
            return client_info
        except:
            return {'session_id': 'unknown', 'user_agent': 'unknown', 'ip_address': 'unknown'}

# Global instance
security_logger_instance = SecurityLogger()

# Unified logging functions with enhanced security
def log_security_event(event_type, username, details=None, success=True, resource=None):
    """Log a security-related event with enhanced information."""
    try:
        timestamp = datetime.now()
        client_info = security_logger_instance.get_client_info()
        
        # Log to file
        status = "SUCCESS" if success else "FAILURE"
        message = f"[{event_type.upper()}] User: {username} | Status: {status} | Resource: {resource or 'N/A'} | Session: {client_info['session_id']}"
        
        if details:
            message += f" | Details: {json.dumps(details)}"
            
        security_logger_instance.security_logger.info(message)
        
        # Log to database if available
        try:
            from utils.db import execute_query
            query = """
                INSERT INTO security_logs (event_type, username, details, success, timestamp, resource, session_id)
                VALUES (:event_type, :username, :details, :success, :timestamp, :resource, :session_id)
            """
            params = {
                'event_type': event_type,
                'username': username,
                'details': json.dumps(details) if details else None,
                'success': success,
                'timestamp': timestamp,
                'resource': resource,
                'session_id': client_info['session_id']
            }
            execute_query(query, params)
        except Exception as db_error:
            security_logger_instance.security_logger.warning(
                f"Failed to log to database: {str(db_error)}"
            )
            
    except Exception as e:
        print(f"Security logging failed: {str(e)}")

def log_audit_event(event_type, username, resource, action, old_value=None, new_value=None, details=None):
    """Log an audit-related event with enhanced tracking."""
    try:
        timestamp = datetime.now()
        client_info = security_logger_instance.get_client_info()
        
        # Log to file
        message = f"[{event_type.upper()}] User: {username} | Action: {action} | Resource: {resource} | Session: {client_info['session_id']}"
        
        if old_value is not None or new_value is not None:
            message += f" | Change: {old_value} -> {new_value}"
            
        if details:
            message += f" | Details: {json.dumps(details)}"
            
        security_logger_instance.audit_logger.info(message)
        
        # Log to database if available
        try:
            from utils.db import execute_query
            query = """
                INSERT INTO audit_logs (event_type, username, resource, action, old_value, new_value, timestamp, session_id, details)
                VALUES (:event_type, :username, :resource, :action, :old_value, :new_value, :timestamp, :session_id, :details)
            """
            params = {
                'event_type': event_type,
                'username': username,
                'resource': resource,
                'action': action,
                'old_value': old_value,
                'new_value': new_value,
                'timestamp': timestamp,
                'session_id': client_info['session_id'],
                'details': json.dumps(details) if details else None
            }
            execute_query(query, params)
        except Exception as db_error:
            security_logger_instance.audit_logger.warning(
                f"Failed to log to database: {str(db_error)}"
            )
            
    except Exception as e:
        print(f"Audit logging failed: {str(e)}")

def log_application_event(level, message, username=None, details=None):
    """Log general application events."""
    try:
        timestamp = datetime.now()
        client_info = security_logger_instance.get_client_info()
        
        # Format message
        formatted_message = f"{message}"
        if username:
            formatted_message += f" | User: {username}"
        if client_info['session_id'] != 'unknown':
            formatted_message += f" | Session: {client_info['session_id']}"
        if details:
            formatted_message += f" | Details: {json.dumps(details)}"
        
        # Log based on level
        logger_method = getattr(security_logger_instance.app_logger, level.lower(), None)
        if logger_method:
            logger_method(formatted_message)
        else:
            security_logger_instance.app_logger.info(formatted_message)
            
    except Exception as e:
        print(f"Application logging failed: {str(e)}")

# Enhanced security event shortcuts
def log_login_attempt(username, success, ip_address=None, details=None):
    """Log login attempt with enhanced security tracking"""
    event_details = details or {}
    if ip_address:
        event_details['ip_address'] = ip_address
    
    log_security_event(
        event_type='login_attempt',
        username=username,
        success=success,
        resource='authentication',
        details=event_details
    )

def log_logout(username, session_duration=None):
    """Log user logout with session information"""
    details = {}
    if session_duration:
        details['session_duration'] = session_duration
    
    log_security_event(
        event_type='logout',
        username=username,
        success=True,
        resource='authentication',
        details=details
    )

def log_permission_check(username, resource, permission, granted):
    """Log permission/access control checks"""
    log_security_event(
        event_type='permission_check',
        username=username,
        success=granted,
        resource=resource,
        details={'permission': permission}
    )

def log_file_access(username, file_path, action, success=True):
    """Log file access attempts"""
    log_audit_event(
        event_type='file_access',
        username=username,
        resource=file_path,
        action=action,
        details={'file_path': file_path}
    )

def log_data_modification(username, table, record_id, action, changes=None):
    """Log database modifications"""
    log_audit_event(
        event_type='data_modification',
        username=username,
        resource=f"{table}:{record_id}",
        action=action,
        details=changes or {}
    )

# Database table creation functions
def create_security_logs_table():
    """Create security logs table if it doesn't exist"""
    try:
        from utils.db import execute_query
        query = """
        CREATE TABLE IF NOT EXISTS security_logs (
            id SERIAL PRIMARY KEY,
            event_type VARCHAR(100) NOT NULL,
            username VARCHAR(100) NOT NULL,
            details TEXT,
            success BOOLEAN NOT NULL,
            timestamp TIMESTAMP NOT NULL,
            resource VARCHAR(255),
            session_id VARCHAR(255),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
        execute_query(query)
        
        # Create indexes for better performance
        execute_query("CREATE INDEX IF NOT EXISTS idx_security_logs_timestamp ON security_logs(timestamp)")
        execute_query("CREATE INDEX IF NOT EXISTS idx_security_logs_username ON security_logs(username)")
        execute_query("CREATE INDEX IF NOT EXISTS idx_security_logs_event_type ON security_logs(event_type)")
        
    except Exception as e:
        print(f"Failed to create security_logs table: {str(e)}")

def create_audit_logs_table():
    """Create audit logs table if it doesn't exist"""
    try:
        from utils.db import execute_query
        query = """
        CREATE TABLE IF NOT EXISTS audit_logs (
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
        )
        """
        execute_query(query)
        
        # Create indexes for better performance
        execute_query("CREATE INDEX IF NOT EXISTS idx_audit_logs_timestamp ON audit_logs(timestamp)")
        execute_query("CREATE INDEX IF NOT EXISTS idx_audit_logs_username ON audit_logs(username)")
        execute_query("CREATE INDEX IF NOT EXISTS idx_audit_logs_resource ON audit_logs(resource)")
        
    except Exception as e:
        print(f"Failed to create audit_logs table: {str(e)}")

def log_access_attempt(username, resource, success=True, details=None):
    """Log access attempts"""
    log_security_event(
        event_type='access_attempt',
        username=username,
        success=success,
        resource=resource,
        details=details
    )

def log_dataset_access(username, dataset=None, dataset_name=None, action='view', success=True, details=None, purpose=None):
    """Log dataset access events"""
    # Handle both 'dataset' and 'dataset_name' parameters for backward compatibility
    resource_name = dataset or dataset_name or 'unknown_dataset'
    
    # If purpose is provided, use it as action
    if purpose:
        action = purpose
    
    log_audit_event(
        event_type='dataset_access',
        username=username,
        resource=resource_name,
        action=action,
        details=details
    )

def log_data_change(username, dataset_name, change_type, old_value=None, new_value=None, details=None):
    """Log data modification events"""
    log_audit_event(
        event_type='data_change',
        username=username,
        resource=dataset_name,
        action=change_type,
        old_value=old_value,
        new_value=new_value,
        details=details
    )

# Export the main logger instance for direct access if needed
security_logger = security_logger_instance.security_logger
audit_logger = security_logger_instance.audit_logger
app_logger = security_logger_instance.app_logger
