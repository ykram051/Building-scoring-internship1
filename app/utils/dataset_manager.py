"""
Dynamic Dataset Manager

Handles arbitrary user dataset uploads with flexible schema support.
Uses hybrid approach: JSONB for flexibility + metadata for performance.
"""

import pandas as pd
import numpy as np
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path
import hashlib
import uuid

from sqlalchemy import text, create_engine
from sqlalchemy.exc import SQLAlchemyError

try:
    from .db import execute_query, query_to_dataframe, get_connection
    from .secure_auth import get_current_user, check_permission, sanitize_input
    from .logger import log_audit_event, log_security_event
except ImportError:
    # Fallback for direct execution
    from utils.db import execute_query, query_to_dataframe, get_connection
    from utils.secure_auth import get_current_user, check_permission, sanitize_input
    from utils.logger import log_audit_event, log_security_event

logger = logging.getLogger(__name__)

class DatasetManager:
    """
    Manages dynamic user datasets with flexible schemas.
    
    Design:
    - user_datasets: Metadata table with schema information
    - dataset_data: JSONB storage for flexible data
    - Optional per-dataset tables for large datasets
    """
    
    def __init__(self):
        self.max_jsonb_rows = 10000  # Switch to dedicated table above this
        self.supported_formats = ['.csv', '.xlsx', '.xls']
        
    def initialize_schema(self):
        """Initialize the dynamic dataset schema."""
        try:
            # Create user_datasets metadata table
            execute_query(text("""
                CREATE TABLE IF NOT EXISTS user_datasets (
                    id SERIAL PRIMARY KEY,
                    dataset_name VARCHAR(100) NOT NULL,
                    owner VARCHAR(50) REFERENCES users(username) ON DELETE CASCADE,
                    display_name VARCHAR(200),
                    description TEXT,
                    file_name VARCHAR(255),
                    file_size BIGINT,
                    row_count INTEGER,
                    column_count INTEGER,
                    schema_info JSONB NOT NULL,
                    storage_type VARCHAR(20) DEFAULT 'jsonb',  -- 'jsonb' or 'table'
                    table_name VARCHAR(100),  -- For dedicated tables
                    upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_accessed TIMESTAMP,
                    is_public BOOLEAN DEFAULT FALSE,
                    tags TEXT[],
                    checksum VARCHAR(64),
                    UNIQUE(dataset_name, owner)
                );
            """))
            
            # Create dataset_data JSONB storage table
            execute_query(text("""
                CREATE TABLE IF NOT EXISTS dataset_data (
                    id SERIAL PRIMARY KEY,
                    dataset_id INTEGER REFERENCES user_datasets(id) ON DELETE CASCADE,
                    row_index INTEGER,
                    data JSONB NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """))
            
            # Create indexes for performance
            execute_query(text("""
                CREATE INDEX IF NOT EXISTS idx_user_datasets_owner 
                ON user_datasets(owner);
            """))
            
            execute_query(text("""
                CREATE INDEX IF NOT EXISTS idx_user_datasets_name_owner 
                ON user_datasets(dataset_name, owner);
            """))
            
            execute_query(text("""
                CREATE INDEX IF NOT EXISTS idx_dataset_data_dataset_id 
                ON dataset_data(dataset_id);
            """))
            
            execute_query(text("""
                CREATE INDEX IF NOT EXISTS idx_dataset_data_jsonb 
                ON dataset_data USING GIN (data);
            """))
            
            logger.info("Dynamic dataset schema initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize dataset schema: {e}")
            return False
    
    def upload_dataset(self, 
                      uploaded_file, 
                      dataset_name: str, 
                      display_name: str = None,
                      description: str = None,
                      tags: List[str] = None) -> Tuple[bool, str, Optional[int]]:
        """
        Upload and store a dataset with arbitrary schema.
        
        Args:
            uploaded_file: File object from Streamlit
            dataset_name: Unique name for the dataset
            display_name: Human-readable display name
            description: Optional description
            tags: Optional tags for categorization
            
        Returns:
            (success, message, dataset_id)
        """
        try:
            username = get_current_user()
            if not username:
                return False, "Authentication required", None
                
            # Validate permissions
            if not check_permission("upload_dataset"):
                log_security_event("dataset_upload_denied", username)
                return False, "Insufficient permissions", None
            
            # Sanitize inputs
            dataset_name = sanitize_input(dataset_name)
            display_name = sanitize_input(display_name or dataset_name)
            description = sanitize_input(description or "")
            
            # Validate file format
            file_ext = Path(uploaded_file.name).suffix.lower()
            if file_ext not in self.supported_formats:
                return False, f"Unsupported format. Use: {', '.join(self.supported_formats)}", None
            
            # Read the data
            df = self._read_file(uploaded_file)
            if df is None or df.empty:
                return False, "Failed to read file or file is empty", None
            
            # Validate dataset size
            if len(df) > 1000000:  # 1M rows limit
                return False, "Dataset too large. Maximum 1M rows allowed.", None
            
            # Generate schema information
            schema_info = self._generate_schema_info(df)
            
            # Calculate file metadata
            file_size = len(uploaded_file.getvalue()) if hasattr(uploaded_file, 'getvalue') else 0
            checksum = self._calculate_checksum(uploaded_file)
            
            # Check if dataset name already exists for this user
            existing = query_to_dataframe(
                "SELECT id FROM user_datasets WHERE dataset_name = :name AND owner = :owner",
                {"name": dataset_name, "owner": username}
            )
            
            if not existing.empty:
                return False, f"Dataset '{dataset_name}' already exists", None
            
            # Determine storage strategy
            storage_type = "jsonb" if len(df) <= self.max_jsonb_rows else "table"
            table_name = None
            
            if storage_type == "table":
                table_name = f"dataset_{username}_{dataset_name}".lower().replace('-', '_')
                table_name = ''.join(c for c in table_name if c.isalnum() or c == '_')
            
            # Insert dataset metadata
            dataset_id = execute_query(text("""
                INSERT INTO user_datasets (
                    dataset_name, owner, display_name, description, file_name,
                    file_size, row_count, column_count, schema_info, storage_type,
                    table_name, tags, checksum
                ) VALUES (
                    :dataset_name, :owner, :display_name, :description, :file_name,
                    :file_size, :row_count, :column_count, :schema_info, :storage_type,
                    :table_name, :tags, :checksum
                ) RETURNING id
            """), {
                "dataset_name": dataset_name,
                "owner": username,
                "display_name": display_name,
                "description": description,
                "file_name": uploaded_file.name,
                "file_size": file_size,
                "row_count": len(df),
                "column_count": len(df.columns),
                "schema_info": json.dumps(schema_info),
                "storage_type": storage_type,
                "table_name": table_name,
                "tags": tags or [],
                "checksum": checksum
            }, fetch_one=True)[0]
            
            # Store the actual data
            if storage_type == "jsonb":
                success = self._store_data_jsonb(dataset_id, df)
            else:
                success = self._store_data_table(table_name, df, schema_info)
            
            if not success:
                # Cleanup on failure
                execute_query("DELETE FROM user_datasets WHERE id = :id", {"id": dataset_id})
                return False, "Failed to store dataset data", None
            
            # Log successful upload
            log_audit_event(
                event_type="dataset_upload",
                username=username,
                resource=dataset_name,
                action="create",
                new_value=f"rows:{len(df)}, cols:{len(df.columns)}",
                details={"storage_type": storage_type, "file_size": file_size}
            )
            
            logger.info(f"Dataset {dataset_name} uploaded successfully by {username}")
            return True, f"Dataset uploaded successfully ({storage_type} storage)", dataset_id
            
        except Exception as e:
            logger.error(f"Dataset upload failed: {e}")
            return False, f"Upload failed: {str(e)}", None
    
    def _read_file(self, uploaded_file) -> Optional[pd.DataFrame]:
        """Read uploaded file into DataFrame."""
        try:
            file_ext = Path(uploaded_file.name).suffix.lower()
            
            if file_ext == '.csv':
                # Try different encodings
                for encoding in ['utf-8', 'latin-1', 'cp1252']:
                    try:
                        uploaded_file.seek(0)
                        return pd.read_csv(uploaded_file, encoding=encoding)
                    except UnicodeDecodeError:
                        continue
                        
            elif file_ext in ['.xlsx', '.xls']:
                uploaded_file.seek(0)
                return pd.read_excel(uploaded_file)
                
        except Exception as e:
            logger.error(f"Failed to read file: {e}")
            
        return None
    
    def _generate_schema_info(self, df: pd.DataFrame) -> Dict:
        """Generate schema information for the dataset."""
        schema = {
            "columns": {},
            "statistics": {},
            "sample_data": {}
        }
        
        for col in df.columns:
            col_data = df[col]
            
            # Basic column info
            schema["columns"][col] = {
                "dtype": str(col_data.dtype),
                "nullable": col_data.isnull().any(),
                "null_count": int(col_data.isnull().sum()),
                "unique_count": int(col_data.nunique())
            }
            
            # Type-specific statistics
            if col_data.dtype in ['int64', 'float64']:
                schema["statistics"][col] = {
                    "min": float(col_data.min()) if not col_data.isnull().all() else None,
                    "max": float(col_data.max()) if not col_data.isnull().all() else None,
                    "mean": float(col_data.mean()) if not col_data.isnull().all() else None,
                    "std": float(col_data.std()) if not col_data.isnull().all() else None
                }
            elif col_data.dtype == 'object':
                # Sample values for text columns
                sample_values = col_data.dropna().unique()[:5].tolist()
                schema["sample_data"][col] = [str(v) for v in sample_values]
        
        return schema
    
    def _calculate_checksum(self, uploaded_file) -> str:
        """Calculate file checksum for integrity verification."""
        try:
            uploaded_file.seek(0)
            content = uploaded_file.read()
            if isinstance(content, str):
                content = content.encode('utf-8')
            return hashlib.sha256(content).hexdigest()
        except:
            return str(uuid.uuid4())  # Fallback to UUID
    
    def _store_data_jsonb(self, dataset_id: int, df: pd.DataFrame) -> bool:
        """Store dataset in JSONB format."""
        try:
            # Convert DataFrame to records
            records = []
            for idx, row in df.iterrows():
                # Convert numpy types to native Python types
                record_data = {}
                for col, value in row.items():
                    if pd.isna(value):
                        record_data[col] = None
                    elif isinstance(value, (np.integer, np.floating)):
                        record_data[col] = float(value) if isinstance(value, np.floating) else int(value)
                    else:
                        record_data[col] = str(value)
                
                records.append({
                    "dataset_id": dataset_id,
                    "row_index": int(idx),
                    "data": json.dumps(record_data)
                })
            
            # Batch insert
            execute_query(text("""
                INSERT INTO dataset_data (dataset_id, row_index, data)
                VALUES (:dataset_id, :row_index, :data)
            """), records, batch=True)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to store JSONB data: {e}")
            return False
    
    def _store_data_table(self, table_name: str, df: pd.DataFrame, schema_info: Dict) -> bool:
        """Store large dataset in dedicated table."""
        try:
            # Create table dynamically
            columns_sql = []
            for col, info in schema_info["columns"].items():
                safe_col = self._safe_column_name(col)
                
                if 'int' in info["dtype"]:
                    col_type = "BIGINT"
                elif 'float' in info["dtype"]:
                    col_type = "DOUBLE PRECISION"
                elif 'bool' in info["dtype"]:
                    col_type = "BOOLEAN"
                else:
                    col_type = "TEXT"
                
                null_clause = "NULL" if info["nullable"] else "NOT NULL"
                columns_sql.append(f'"{safe_col}" {col_type} {null_clause}')
            
            create_table_sql = f"""
                CREATE TABLE "{table_name}" (
                    _row_id SERIAL PRIMARY KEY,
                    {', '.join(columns_sql)}
                )
            """
            
            execute_query(text(create_table_sql))
            
            # Insert data using pandas to_sql for efficiency
            with get_connection() as conn:
                # Rename columns to safe names
                df_safe = df.copy()
                df_safe.columns = [self._safe_column_name(col) for col in df.columns]
                
                df_safe.to_sql(
                    table_name, 
                    conn, 
                    if_exists='append', 
                    index=False,
                    method='multi',
                    chunksize=1000
                )
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to create dedicated table: {e}")
            return False
    
    def _safe_column_name(self, col_name: str) -> str:
        """Convert column name to safe SQL identifier."""
        # Replace special characters and spaces
        safe_name = ''.join(c if c.isalnum() else '_' for c in str(col_name))
        
        # Ensure it doesn't start with a number
        if safe_name and safe_name[0].isdigit():
            safe_name = 'col_' + safe_name
        
        # Limit length
        return safe_name[:63]  # PostgreSQL identifier limit
    
    def get_user_datasets(self, username: str = None) -> pd.DataFrame:
        """Get all datasets for a user."""
        try:
            if not username:
                username = get_current_user()
                
            if not username:
                return pd.DataFrame()
            
            # Check permissions
            if not check_permission("view_datasets"):
                return pd.DataFrame()
            
            query = """
                SELECT 
                    id, dataset_name, display_name, description,
                    file_name, file_size, row_count, column_count,
                    storage_type, upload_date, last_accessed,
                    is_public, tags
                FROM user_datasets 
                WHERE owner = :username OR is_public = true
                ORDER BY upload_date DESC
            """
            
            return query_to_dataframe(query, {"username": username})
            
        except Exception as e:
            logger.error(f"Failed to get user datasets: {e}")
            return pd.DataFrame()
    
    def get_dataset_preview(self, dataset_name: str, limit: int = 100) -> Tuple[bool, pd.DataFrame, str]:
        """Get preview of dataset data."""
        try:
            username = get_current_user()
            if not username:
                return False, pd.DataFrame(), "Authentication required"
            
            # Get dataset metadata
            metadata = query_to_dataframe("""
                SELECT id, storage_type, table_name, schema_info, owner
                FROM user_datasets 
                WHERE dataset_name = :name AND (owner = :username OR is_public = true)
            """, {"name": dataset_name, "username": username})
            
            if metadata.empty:
                return False, pd.DataFrame(), "Dataset not found or access denied"
            
            dataset_id = metadata.iloc[0]['id']
            storage_type = metadata.iloc[0]['storage_type']
            table_name = metadata.iloc[0]['table_name']
            owner = metadata.iloc[0]['owner']
            
            # Log access
            if owner != username:
                log_audit_event(
                    event_type="dataset_access",
                    username=username,
                    resource=dataset_name,
                    action="preview",
                    details={"owner": owner}
                )
            
            # Update last accessed
            execute_query(
                "UPDATE user_datasets SET last_accessed = CURRENT_TIMESTAMP WHERE id = :id",
                {"id": dataset_id}
            )
            
            # Fetch data based on storage type
            if storage_type == "jsonb":
                df = query_to_dataframe("""
                    SELECT data FROM dataset_data 
                    WHERE dataset_id = :dataset_id 
                    ORDER BY row_index 
                    LIMIT :limit
                """, {"dataset_id": dataset_id, "limit": limit})
                
                if not df.empty:
                    # Convert JSONB back to DataFrame
                    records = [json.loads(row['data']) for _, row in df.iterrows()]
                    result_df = pd.DataFrame(records)
                else:
                    result_df = pd.DataFrame()
                    
            else:  # table storage
                result_df = query_to_dataframe(f'SELECT * FROM "{table_name}" LIMIT :limit', {"limit": limit})
            
            return True, result_df, "Success"
            
        except Exception as e:
            logger.error(f"Failed to get dataset preview: {e}")
            return False, pd.DataFrame(), str(e)
    
    def query_dataset(self, 
                     dataset_name: str, 
                     filters: Dict = None,
                     columns: List[str] = None,
                     limit: int = 1000) -> Tuple[bool, pd.DataFrame, str]:
        """Query dataset with flexible filters."""
        try:
            username = get_current_user()
            if not username:
                return False, pd.DataFrame(), "Authentication required"
            
            # Get dataset metadata
            metadata = query_to_dataframe("""
                SELECT id, storage_type, table_name, schema_info, owner
                FROM user_datasets 
                WHERE dataset_name = :name AND (owner = :username OR is_public = true)
            """, {"name": dataset_name, "username": username})
            
            if metadata.empty:
                return False, pd.DataFrame(), "Dataset not found or access denied"
            
            dataset_id = metadata.iloc[0]['id']
            storage_type = metadata.iloc[0]['storage_type']
            table_name = metadata.iloc[0]['table_name']
            schema_info = json.loads(metadata.iloc[0]['schema_info'])
            
            if storage_type == "jsonb":
                return self._query_jsonb_dataset(dataset_id, schema_info, filters, columns, limit)
            else:
                return self._query_table_dataset(table_name, schema_info, filters, columns, limit)
                
        except Exception as e:
            logger.error(f"Failed to query dataset: {e}")
            return False, pd.DataFrame(), str(e)
    
    def _query_jsonb_dataset(self, 
                            dataset_id: int,
                            schema_info: Dict,
                            filters: Dict = None,
                            columns: List[str] = None,
                            limit: int = 1000) -> Tuple[bool, pd.DataFrame, str]:
        """Query JSONB-stored dataset."""
        try:
            # Build WHERE clause for JSONB
            where_conditions = []
            params = {"dataset_id": dataset_id, "limit": limit}
            
            if filters:
                for col, value in filters.items():
                    if col in schema_info["columns"]:
                        safe_col = sanitize_input(col)
                        param_name = f"filter_{len(params)}"
                        where_conditions.append(f"data->>'{safe_col}' = :{param_name}")
                        params[param_name] = str(value)
            
            where_clause = ""
            if where_conditions:
                where_clause = f"AND {' AND '.join(where_conditions)}"
            
            query = f"""
                SELECT data FROM dataset_data 
                WHERE dataset_id = :dataset_id {where_clause}
                ORDER BY row_index 
                LIMIT :limit
            """
            
            df = query_to_dataframe(query, params)
            
            if not df.empty:
                # Convert JSONB back to DataFrame
                records = [json.loads(row['data']) for _, row in df.iterrows()]
                result_df = pd.DataFrame(records)
                
                # Filter columns if specified
                if columns:
                    available_cols = [col for col in columns if col in result_df.columns]
                    result_df = result_df[available_cols]
            else:
                result_df = pd.DataFrame()
            
            return True, result_df, "Success"
            
        except Exception as e:
            logger.error(f"JSONB query failed: {e}")
            return False, pd.DataFrame(), str(e)
    
    def _query_table_dataset(self,
                           table_name: str,
                           schema_info: Dict,
                           filters: Dict = None,
                           columns: List[str] = None,
                           limit: int = 1000) -> Tuple[bool, pd.DataFrame, str]:
        """Query table-stored dataset."""
        try:
            # Build SELECT clause
            if columns:
                safe_columns = [f'"{self._safe_column_name(col)}"' for col in columns 
                              if col in schema_info["columns"]]
                select_clause = ", ".join(safe_columns) if safe_columns else "*"
            else:
                select_clause = "*"
            
            # Build WHERE clause
            where_conditions = []
            params = {"limit": limit}
            
            if filters:
                for col, value in filters.items():
                    if col in schema_info["columns"]:
                        safe_col = self._safe_column_name(col)
                        param_name = f"filter_{len(params)}"
                        where_conditions.append(f'"{safe_col}" = :{param_name}')
                        params[param_name] = value
            
            where_clause = ""
            if where_conditions:
                where_clause = f"WHERE {' AND '.join(where_conditions)}"
            
            query = f'SELECT {select_clause} FROM "{table_name}" {where_clause} LIMIT :limit'
            
            result_df = query_to_dataframe(query, params)
            return True, result_df, "Success"
            
        except Exception as e:
            logger.error(f"Table query failed: {e}")
            return False, pd.DataFrame(), str(e)
    
    def delete_dataset(self, dataset_name: str) -> Tuple[bool, str]:
        """Delete a dataset and all its data."""
        try:
            username = get_current_user()
            if not username:
                return False, "Authentication required"
            
            # Get dataset info
            metadata = query_to_dataframe("""
                SELECT id, storage_type, table_name, owner
                FROM user_datasets 
                WHERE dataset_name = :name AND owner = :username
            """, {"name": dataset_name, "username": username})
            
            if metadata.empty:
                return False, "Dataset not found or access denied"
            
            dataset_id = metadata.iloc[0]['id']
            storage_type = metadata.iloc[0]['storage_type']
            table_name = metadata.iloc[0]['table_name']
            
            # Delete data based on storage type
            if storage_type == "table" and table_name:
                execute_query(f'DROP TABLE IF EXISTS "{table_name}"')
            
            # Delete dataset record (will cascade to dataset_data)
            execute_query("DELETE FROM user_datasets WHERE id = :id", {"id": dataset_id})
            
            # Log deletion
            log_audit_event(
                event_type="dataset_delete",
                username=username,
                resource=dataset_name,
                action="delete",
                old_value="exists",
                new_value="deleted",
                details={"storage_type": storage_type}
            )
            
            return True, "Dataset deleted successfully"
            
        except Exception as e:
            logger.error(f"Failed to delete dataset: {e}")
            return False, str(e)

# Global instance
dataset_manager = DatasetManager()
