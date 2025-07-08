"""
Unified Logging Module

This module provides centralized logging for security and audit events.
Supports logging to both local files and PostgreSQL databases.
"""

import logging
import os
import json
from datetime import datetime
from pathlib import Path
from utils.db import execute_query

# Set up logging directory
LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

# Configure security logger
security_logger = logging.getLogger("security")
security_logger.setLevel(logging.INFO)

# Configure audit logger
audit_logger = logging.getLogger("audit")
audit_logger.setLevel(logging.INFO)

# Create file handlers for fallback logging
security_file = LOG_DIR / "security.log"
security_handler = logging.FileHandler(security_file)
security_handler.setFormatter(
    logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
)
security_logger.addHandler(security_handler)

audit_file = LOG_DIR / "audit.log"
audit_handler = logging.FileHandler(audit_file)
audit_handler.setFormatter(
    logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
)
audit_logger.addHandler(audit_handler)

# Unified logging functions
def log_security_event(event_type, username, details=None, success=True, destination="file"):
    """
    Log a security-related event.

    Args:
        event_type (str): Type of security event (login, logout, access_attempt, etc.)
        username (str): Username associated with the event
        details (dict, optional): Additional details about the event
        success (bool, optional): Whether the event was successful
        destination (str): Logging destination ('file' or 'db')
    """
    log_entry = {
        "event_type": event_type,
        "username": username,
        "details": details or {},
        "success": success,
        "timestamp": datetime.now().isoformat()
    }

    if destination == "db":
        try:
            query = """
            INSERT INTO security_logs (event_type, username, details, success, timestamp)
            VALUES (:event_type, :username, :details, :success, :timestamp)
            """
            execute_query(query, log_entry)
        except Exception as e:
            security_logger.error(f"Failed to log security event to DB: {e}")
    else:
        security_logger.info(json.dumps(log_entry))

def log_audit_event(event_type, username, details=None, destination="file"):
    """
    Log an audit-related event.

    Args:
        event_type (str): Type of audit event (data_change, access, etc.)
        username (str): Username associated with the event
        details (dict, optional): Additional details about the event
        destination (str): Logging destination ('file' or 'db')
    """
    log_entry = {
        "event_type": event_type,
        "username": username,
        "details": details or {},
        "timestamp": datetime.now().isoformat()
    }

    if destination == "db":
        try:
            query = """
            INSERT INTO audit_logs (event_type, username, details, timestamp)
            VALUES (:event_type, :username, :details, :timestamp)
            """
            execute_query(query, log_entry)
        except Exception as e:
            audit_logger.error(f"Failed to log audit event to DB: {e}")
    else:
        audit_logger.info(json.dumps(log_entry))

def log_data_change(username, dataset, entity_id, action, changes=None, destination="file"):
    """
    Log a data change event (create, update, delete).

    Args:
        username (str): Username who made the change
        dataset (str): Dataset affected (e.g., city name)
        entity_id (str): ID of the entity changed (e.g., building ID)
        action (str): Type of change (create, update, delete)
        changes (dict, optional): Details of what was changed
        destination (str): Logging destination ('file' or 'db')
    """
    details = {
        "dataset": dataset,
        "entity_id": entity_id,
        "action": action,
        "changes": changes or {}
    }

    if destination == "db":
        try:
            query = """
            INSERT INTO audit_logs (event_type, username, dataset, entity_id, action, changes, timestamp)
            VALUES ('data_change', :username, :dataset, :entity_id, :action, :changes, :timestamp)
            """
            execute_query(query, {
                "username": username,
                "dataset": dataset,
                "entity_id": entity_id,
                "action": action,
                "changes": json.dumps(changes) if changes else None,
                "timestamp": datetime.now().isoformat()
            })
        except Exception as e:
            audit_logger.error(f"Failed to log data change to DB: {e}")
    else:
        log_entry = {
            "event_type": "data_change",
            "username": username,
            "details": details,
            "timestamp": datetime.now().isoformat()
        }
        audit_logger.info(json.dumps(log_entry))

def log_dataset_access(username, dataset, purpose=None, destination="file"):
    """
    Log dataset access events.

    Args:
        username (str): Username accessing the dataset
        dataset (str): Dataset being accessed
        purpose (str, optional): Purpose of the access
        destination (str): Logging destination ('file' or 'db')
    """
    details = {
        "dataset": dataset,
        "purpose": purpose or "view"
    }

    if destination == "db":
        try:
            query = """
            INSERT INTO audit_logs (event_type, username, dataset, action, details, timestamp)
            VALUES ('access', :username, :dataset, 'view', :details, :timestamp)
            """
            execute_query(query, {
                "username": username,
                "dataset": dataset,
                "details": json.dumps(details),
                "timestamp": datetime.now().isoformat()
            })
        except Exception as e:
            audit_logger.error(f"Failed to log dataset access to DB: {e}")
    else:
        log_entry = {
            "event_type": "dataset_access",
            "username": username,
            "details": details,
            "timestamp": datetime.now().isoformat()
        }
        audit_logger.info(json.dumps(log_entry))

def log_access_attempt(username, resource=None, success=None, feature=None, allowed=None, details=None, destination="file"):
    """
    Log an access attempt to a secured resource.
    
    Args:
        username (str): Username attempting access
        resource (str, optional): Resource being accessed (legacy parameter)
        success (bool, optional): Whether access was granted (legacy parameter)
        feature (str, optional): Feature being accessed (new parameter)
        allowed (bool, optional): Whether access was allowed (new parameter)
        details (dict, optional): Additional details
        destination (str): Logging destination ('file' or 'db')
    """
    # Handle parameter compatibility - map feature to resource and allowed to success
    if feature is not None and resource is None:
        resource = feature
    if allowed is not None and success is None:
        success = allowed
        
    log_entry = {
        "event_type": "access_attempt",
        "username": username,
        "resource": resource,
        "success": success,
        "details": details or {},
        "timestamp": datetime.now().isoformat()
    }

    if destination == "db":
        try:
            query = """
            INSERT INTO security_logs (event_type, username, resource, success, details, timestamp)
            VALUES ('access_attempt', :username, :resource, :success, :details, :timestamp)
            """
            execute_query(query, {
                "username": username,
                "resource": resource,
                "success": success,
                "details": json.dumps(details) if details else None,
                "timestamp": datetime.now().isoformat()
            })
        except Exception as e:
            security_logger.error(f"Failed to log access attempt to DB: {e}")
    else:
        security_logger.info(json.dumps(log_entry))
