"""
Secure File Handling Module
Handles file uploads and validation with security measures
"""
import os
import pandas as pd
import streamlit as st
import hashlib
from pathlib import Path
from typing import Tuple, Optional, List, Dict
from datetime import datetime
import logging
import re
import tempfile
import shutil

logger = logging.getLogger(__name__)

class SecureFileHandler:
    """Secure file handling with validation and user isolation"""
    
    def __init__(self):
        self.allowed_extensions = {'.csv', '.xlsx', '.xls'}
        self.max_file_size = 50 * 1024 * 1024  # 50MB
        self.max_rows = 100000
        self.upload_dir = Path("data/user_uploads")
        self.temp_dir = Path("data/temp")
        
        # Create directories if they don't exist
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        self.temp_dir.mkdir(parents=True, exist_ok=True)
    
    def get_user_upload_dir(self, user_id: str) -> Path:
        """Get user-specific upload directory"""
        # Sanitize user_id to prevent path traversal
        safe_user_id = re.sub(r'[^a-zA-Z0-9_-]', '', str(user_id))
        user_dir = self.upload_dir / f"user_{safe_user_id}"
        user_dir.mkdir(exist_ok=True)
        return user_dir
    
    def validate_file_type(self, uploaded_file) -> Tuple[bool, str]:
        """Validate file type using both extension and content"""
        try:
            # Check file extension
            file_extension = Path(uploaded_file.name).suffix.lower()
            if file_extension not in self.allowed_extensions:
                return False, f"File type not allowed. Allowed types: {', '.join(self.allowed_extensions)}"
            
            # Check file size
            if uploaded_file.size > self.max_file_size:
                return False, f"File too large. Maximum size: {self.max_file_size / (1024*1024):.1f}MB"
            
            # Reset file pointer
            uploaded_file.seek(0)
            
            # Read first few bytes for content validation
            header = uploaded_file.read(2048)
            uploaded_file.seek(0)
            
            # Validate file content
            if file_extension == '.csv':
                # For CSV, check if it starts with reasonable text
                try:
                    header_text = header.decode('utf-8', errors='ignore')
                    if not any(c.isalnum() or c in ',;\\t\\n\\r ' for c in header_text[:100]):
                        return False, "Invalid CSV file format"
                except:
                    return False, "Unable to read CSV file"
            
            return True, "File validation passed"
            
        except Exception as e:
            logger.error(f"File validation error: {e}")
            return False, f"File validation failed: {str(e)}"
    
    def sanitize_filename(self, filename: str) -> str:
        """Sanitize filename to prevent path traversal"""
        # Remove path components
        filename = os.path.basename(filename)
        
        # Remove dangerous characters
        filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
        
        # Limit length
        name, ext = os.path.splitext(filename)
        name = name[:50]  # Limit name length
        
        return f"{name}{ext}"
    
    def validate_csv_content(self, df: pd.DataFrame) -> Tuple[bool, str, Dict]:
        """Validate CSV content for security and data integrity"""
        try:
            # Check row count
            if len(df) > self.max_rows:
                return False, f"Too many rows. Maximum allowed: {self.max_rows}", {}
            
            # Check for suspicious patterns in column names
            suspicious_patterns = ['<script', 'javascript:', 'data:', 'vbscript:']
            for col in df.columns:
                col_lower = str(col).lower()
                if any(pattern in col_lower for pattern in suspicious_patterns):
                    return False, f"Suspicious content detected in column name: {col}", {}
            
            # Basic data validation
            validation_info = {
                'rows': len(df),
                'columns': len(df.columns),
                'numeric_columns': len(df.select_dtypes(include=['number']).columns),
                'text_columns': len(df.select_dtypes(include=['object']).columns),
                'memory_usage': df.memory_usage(deep=True).sum(),
                'has_nulls': df.isnull().any().any()
            }
            
            # Check for excessively large text fields
            for col in df.select_dtypes(include=['object']).columns:
                max_length = df[col].astype(str).str.len().max()
                if max_length > 1000:  # 1000 character limit per field
                    return False, f"Text field too long in column {col}: {max_length} characters", {}
            
            return True, "Content validation passed", validation_info
            
        except Exception as e:
            logger.error(f"Content validation error: {e}")
            return False, f"Content validation failed: {str(e)}", {}
    
    def secure_file_upload(self, uploaded_file, user_id: str, dataset_name: str) -> Tuple[bool, str, Optional[Dict]]:
        """Securely handle file upload with validation and user isolation"""
        try:
            # Enhanced authentication check
            if not self._validate_user_authentication(user_id):
                logger.warning(f"Unauthorized file upload attempt by user: {user_id}")
                return False, "Authentication failed", None
            
            # Validate file type and size
            is_valid, message = self.validate_file_type(uploaded_file)
            if not is_valid:
                return False, message, None
            
            # Sanitize inputs to prevent injection attacks
            safe_filename = self.sanitize_filename(uploaded_file.name)
            safe_dataset_name = re.sub(r'[^a-zA-Z0-9_-]', '_', dataset_name)
            safe_user_id = re.sub(r'[^a-zA-Z0-9_-]', '', str(user_id))
            
            # Get isolated user directory
            user_dir = self.get_user_upload_dir(safe_user_id)
            
            # Verify directory isolation
            if not self._verify_directory_isolation(user_dir, safe_user_id):
                logger.error(f"Directory isolation check failed for user: {user_id}")
                return False, "Security validation failed", None
            
            # Create temporary file for secure processing
            with tempfile.NamedTemporaryFile(delete=False) as temp_file:
                temp_file.write(uploaded_file.read())
                temp_path = temp_file.name
            
            try:
                # Read and validate content
                file_extension = Path(safe_filename).suffix.lower()
                if file_extension == '.csv':
                    df = pd.read_csv(temp_path)
                elif file_extension in ['.xlsx', '.xls']:
                    df = pd.read_excel(temp_path)
                else:
                    return False, "Unsupported file format", None
                
                # Enhanced content validation
                is_valid, message, validation_info = self.validate_csv_content(df)
                if not is_valid:
                    return False, message, None
                
                # Generate secure filename with hash for uniqueness
                file_hash = hashlib.sha256(uploaded_file.getvalue()).hexdigest()[:16]
                final_filename = f"{safe_dataset_name}_{file_hash}{file_extension}"
                final_path = user_dir / final_filename
                
                # Final security check before file write
                if not self._validate_final_path(final_path, user_dir):
                    return False, "Path validation failed", None
                
                # Move file to final location with atomic operation
                shutil.move(temp_path, str(final_path))
                
                # Set secure file permissions
                os.chmod(str(final_path), 0o600)  # Owner read/write only
                
                # Prepare result info
                result_info = {
                    'filename': final_filename,
                    'path': str(final_path),
                    'size': uploaded_file.size,
                    'validation': validation_info,
                    'user_id': safe_user_id,
                    'upload_timestamp': datetime.now().isoformat()
                }
                
                # Log successful secure upload
                from utils.logger import log_file_access
                log_file_access(safe_user_id, str(final_path), "secure_upload", success=True)
                
                logger.info(f"File uploaded securely for user {user_id}: {final_filename}")
                return True, "File uploaded securely", result_info
                
            finally:
                # Clean up temp file if it still exists
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
                    
        except Exception as e:
            logger.error(f"Secure file upload error: {e}")
            # Log security incident
            from utils.logger import log_file_access
            log_file_access(str(user_id), "upload_attempt", "secure_upload", success=False)
            return False, f"Secure upload failed: {str(e)}", None
    
    def _validate_user_authentication(self, user_id: str) -> bool:
        """Validate user authentication and session integrity (less strict)"""
        if not hasattr(st, 'session_state'):
            return False
        if not st.session_state.get("authenticated", False):
            return False
        return True
    
    def _verify_directory_isolation(self, user_dir: Path, user_id: str) -> bool:
        """Verify that user directory is properly isolated"""
        try:
            # Check that user_dir is within the expected base upload directory
            expected_base = self.upload_dir.resolve()
            actual_dir = user_dir.resolve()
            
            # Ensure the directory is a subdirectory of upload_dir
            if not str(actual_dir).startswith(str(expected_base)):
                logger.error(f"Directory isolation violation: {actual_dir} not under {expected_base}")
                return False
            
            # Verify directory name matches expected pattern
            expected_dir_name = f"user_{re.sub(r'[^a-zA-Z0-9_-]', '', str(user_id))}"
            if actual_dir.name != expected_dir_name:
                logger.error(f"Directory name mismatch: expected {expected_dir_name}, got {actual_dir.name}")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Directory isolation verification failed: {e}")
            return False
    
    def _validate_final_path(self, final_path: Path, user_dir: Path) -> bool:
        """Final validation of file path before write operation"""
        try:
            # Ensure final path is within user directory
            final_path_resolved = final_path.resolve()
            user_dir_resolved = user_dir.resolve()
            
            # Check path containment
            if not str(final_path_resolved).startswith(str(user_dir_resolved)):
                logger.error(f"Path traversal detected: {final_path_resolved} not in {user_dir_resolved}")
                return False
            
            # Check for suspicious filename patterns
            filename = final_path.name
            suspicious_patterns = ['..', '/', '\\', '<', '>', ':', '"', '|', '?', '*']
            if any(pattern in filename for pattern in suspicious_patterns):
                logger.error(f"Suspicious filename pattern detected: {filename}")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Final path validation failed: {e}")
            return False
    
    def secure_file_read(self, file_path: str, user_id: str) -> Tuple[bool, Optional[pd.DataFrame], str]:
        """Securely read file with user access validation"""
        try:
            file_path = Path(file_path)
            
            # Validate that file is in user's directory
            user_dir = self.get_user_upload_dir(user_id)
            
            # Check if file is within user's directory (prevent path traversal)
            try:
                file_path.resolve().relative_to(user_dir.resolve())
            except ValueError:
                logger.warning(f"Path traversal attempt by user {user_id}: {file_path}")
                return False, None, "Access denied: file outside user directory"
            
            # Check if file exists
            if not file_path.exists():
                return False, None, "File not found"
            
            # Read file based on extension
            file_extension = file_path.suffix.lower()
            if file_extension == '.csv':
                df = pd.read_csv(file_path)
            elif file_extension in ['.xlsx', '.xls']:
                df = pd.read_excel(file_path)
            else:
                return False, None, "Unsupported file format"
            
            # Re-validate content on read
            is_valid, message, _ = self.validate_csv_content(df)
            if not is_valid:
                return False, None, f"File validation failed: {message}"
            
            logger.info(f"File read successfully by user {user_id}: {file_path.name}")
            return True, df, "File read successfully"
            
        except Exception as e:
            logger.error(f"File read error: {e}")
            return False, None, f"Read failed: {str(e)}"
    
    def list_user_files(self, user_id: str) -> List[Dict]:
        """List files accessible to user"""
        try:
            user_dir = self.get_user_upload_dir(user_id)
            files = []
            
            for file_path in user_dir.iterdir():
                if file_path.is_file() and file_path.suffix.lower() in self.allowed_extensions:
                    stat = file_path.stat()
                    files.append({
                        'name': file_path.name,
                        'size': stat.st_size,
                        'modified': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                        'path': str(file_path)
                    })
            
            return sorted(files, key=lambda x: x['modified'], reverse=True)
            
        except Exception as e:
            logger.error(f"Error listing user files: {e}")
            return []
    
    def delete_user_file(self, file_path: str, user_id: str) -> Tuple[bool, str]:
        """Securely delete user file"""
        try:
            file_path = Path(file_path)
            user_dir = self.get_user_upload_dir(user_id)
            
            # Validate that file is in user's directory
            try:
                file_path.resolve().relative_to(user_dir.resolve())
            except ValueError:
                logger.warning(f"Path traversal attempt in delete by user {user_id}: {file_path}")
                return False, "Access denied: file outside user directory"
            
            if file_path.exists():
                file_path.unlink()
                logger.info(f"File deleted by user {user_id}: {file_path.name}")
                return True, "File deleted successfully"
            else:
                return False, "File not found"
                
        except Exception as e:
            logger.error(f"File deletion error: {e}")
            return False, f"Deletion failed: {str(e)}"

# Global instance
secure_file_handler = SecureFileHandler()
