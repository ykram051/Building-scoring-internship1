"""
Dataset Explorer Interface

Provides UI components for browsing, querying, and managing flexible user datasets.
"""

import streamlit as st
import pandas as pd
import numpy as np
import json
import time
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
from typing import Dict, List, Optional

try:
    from .dataset_manager import dataset_manager
    from .secure_auth import get_current_user, check_permission
    from .logger import log_audit_event
except ImportError:
    # Fallback for direct execution
    from utils.dataset_manager import dataset_manager
    from utils.secure_auth import get_current_user, check_permission
    from utils.logger import log_audit_event

def display_dataset_explorer():
    """Main dataset explorer interface."""
    st.header("📊 Dataset Explorer")
    st.markdown("Explore and query your uploaded datasets with flexible schemas.")
    
    username = get_current_user()
    if not username:
        st.error("Please log in to access the dataset explorer.")
        return
    
    if not check_permission("view_datasets"):
        st.error("You don't have permission to view datasets.")
        return
    
    # Get user datasets
    datasets_df = dataset_manager.get_user_datasets(username)
    
    if datasets_df.empty:
        st.info("📁 No datasets found. Upload a dataset to get started!")
        return
    
    # Dataset selection
    st.subheader("🗂️ Your Datasets")
    
    # Display datasets in a nice format
    for idx, dataset in datasets_df.iterrows():
        with st.expander(f"📊 {dataset['display_name']} ({dataset['dataset_name']})"):
            col1, col2, col3 = st.columns([2, 1, 1])
            
            with col1:
                st.write(f"**Description:** {dataset['description'] or 'No description'}")
                st.write(f"**File:** {dataset['file_name']}")
                st.write(f"**Uploaded:** {dataset['upload_date'].strftime('%Y-%m-%d %H:%M')}")
                
            with col2:
                st.metric("Rows", f"{dataset['row_count']:,}")
                st.metric("Columns", dataset['column_count'])
                
            with col3:
                st.write(f"**Storage:** {dataset['storage_type']}")
                st.write(f"**Size:** {_format_file_size(dataset['file_size'])}")
                
                if dataset['tags']:
                    st.write("**Tags:**")
                    for tag in dataset['tags']:
                        st.badge(tag)
    
    st.divider()
    
    # Dataset operations
    st.subheader("🔍 Explore Dataset")
    
    dataset_names = datasets_df['dataset_name'].tolist()
    display_names = datasets_df['display_name'].tolist()
    
    selected_idx = st.selectbox(
        "Select a dataset to explore:",
        range(len(dataset_names)),
        format_func=lambda x: display_names[x]
    )
    
    if selected_idx is not None:
        selected_dataset = dataset_names[selected_idx]
        
        # Show dataset operations
        tab1, tab2, tab3, tab4 = st.tabs(["📋 Preview", "🔎 Query", "📈 Analyze", "⚙️ Manage"])
        
        with tab1:
            _display_dataset_preview(selected_dataset)
            
        with tab2:
            _display_dataset_query(selected_dataset)
            
        with tab3:
            _display_dataset_analysis(selected_dataset)
            
        with tab4:
            _display_dataset_management(selected_dataset, datasets_df.iloc[selected_idx])

def _display_dataset_preview(dataset_name: str):
    """Display dataset preview tab."""
    st.subheader("📋 Dataset Preview")
    
    # Preview settings
    col1, col2 = st.columns([1, 3])
    
    with col1:
        limit = st.number_input("Rows to show:", min_value=10, max_value=1000, value=100)
    
    if st.button("🔍 Load Preview"):
        with st.spinner("Loading data..."):
            success, preview_df, message = dataset_manager.get_dataset_preview(dataset_name, limit)
            
            if success and not preview_df.empty:
                st.success(f"✅ Showing {len(preview_df)} rows")
                
                # Show basic info
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Rows", len(preview_df))
                with col2:
                    st.metric("Columns", len(preview_df.columns))
                with col3:
                    st.metric("Memory", f"{preview_df.memory_usage(deep=True).sum() / 1024:.1f} KB")
                
                # Show data types
                st.subheader("📊 Column Information")
                dtypes_df = pd.DataFrame({
                    'Column': preview_df.columns,
                    'Type': preview_df.dtypes,
                    'Non-Null': preview_df.count(),
                    'Unique': preview_df.nunique()
                })
                st.dataframe(dtypes_df)
                
                # Show actual data
                st.subheader("📋 Data Preview")
                st.dataframe(preview_df)
                
                # Download option
                csv = preview_df.to_csv(index=False)
                st.download_button(
                    label="💾 Download Preview as CSV",
                    data=csv,
                    file_name=f"{dataset_name}_preview.csv",
                    mime="text/csv"
                )
                
            else:
                st.error(f"❌ Failed to load preview: {message}")

def _display_dataset_query(dataset_name: str):
    """Display dataset query tab."""
    st.subheader("🔎 Query Dataset")
    
    # Get schema info for building queries
    datasets_df = dataset_manager.get_user_datasets()
    dataset_info = datasets_df[datasets_df['dataset_name'] == dataset_name].iloc[0]
    schema_info = json.loads(dataset_info['schema_info'])
    
    st.subheader("📊 Available Columns")
    columns_df = pd.DataFrame.from_dict(schema_info['columns'], orient='index').reset_index()
    columns_df.columns = ['Column', 'Type', 'Nullable', 'Null Count', 'Unique Count']
    st.dataframe(columns_df)
    
    # Query builder
    st.subheader("🛠️ Query Builder")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Column selection
        available_columns = list(schema_info['columns'].keys())
        selected_columns = st.multiselect(
            "Select columns (leave empty for all):",
            available_columns,
            default=[]
        )
    
    with col2:
        # Limit
        limit = st.number_input("Result limit:", min_value=1, max_value=10000, value=1000)
    
    # Filters
    st.subheader("🔧 Filters")
    
    num_filters = st.number_input("Number of filters:", min_value=0, max_value=5, value=0)
    
    filters = {}
    for i in range(num_filters):
        col1, col2, col3 = st.columns([1, 1, 2])
        
        with col1:
            filter_col = st.selectbox(f"Column {i+1}:", available_columns, key=f"filter_col_{i}")
            
        with col2:
            operator = st.selectbox("Operator:", ["=", "!=", "LIKE"], key=f"filter_op_{i}")
            
        with col3:
            filter_value = st.text_input(f"Value:", key=f"filter_val_{i}")
            
            if filter_col and filter_value:
                if operator == "=":
                    filters[filter_col] = filter_value
                # Note: For LIKE and != operators, we'd need to extend the query interface
    
    # Execute query
    if st.button("🚀 Execute Query"):
        with st.spinner("Executing query..."):
            success, result_df, message = dataset_manager.query_dataset(
                dataset_name=dataset_name,
                filters=filters,
                columns=selected_columns if selected_columns else None,
                limit=limit
            )
            
            if success and not result_df.empty:
                st.success(f"✅ Query returned {len(result_df)} rows")
                
                # Show results
                st.dataframe(result_df)
                
                # Download option
                csv = result_df.to_csv(index=False)
                st.download_button(
                    label="💾 Download Results as CSV",
                    data=csv,
                    file_name=f"{dataset_name}_query_results.csv",
                    mime="text/csv"
                )
                
            else:
                st.error(f"❌ Query failed: {message}")

def _display_dataset_analysis(dataset_name: str):
    """Display dataset analysis tab."""
    st.subheader("📈 Dataset Analysis")
    
    # Get a sample of data for analysis
    success, sample_df, message = dataset_manager.get_dataset_preview(dataset_name, 1000)
    
    if not success or sample_df.empty:
        st.error(f"❌ Cannot load data for analysis: {message}")
        return
    
    # Basic statistics
    st.subheader("📊 Basic Statistics")
    
    # Numeric columns analysis
    numeric_cols = sample_df.select_dtypes(include=[np.number]).columns.tolist()
    
    if numeric_cols:
        st.write("**Numeric Columns:**")
        stats_df = sample_df[numeric_cols].describe()
        st.dataframe(stats_df)
        
        # Distribution plots
        if len(numeric_cols) > 0:
            st.subheader("📈 Distribution Plots")
            
            selected_col = st.selectbox("Select column for distribution:", numeric_cols)
            
            if selected_col:
                col1, col2 = st.columns(2)
                
                with col1:
                    # Histogram
                    fig_hist = px.histogram(
                        sample_df, 
                        x=selected_col,
                        title=f"Distribution of {selected_col}"
                    )
                    st.plotly_chart(fig_hist, use_container_width=True)
                
                with col2:
                    # Box plot
                    fig_box = px.box(
                        sample_df,
                        y=selected_col,
                        title=f"Box Plot of {selected_col}"
                    )
                    st.plotly_chart(fig_box, use_container_width=True)
    
    # Text columns analysis
    text_cols = sample_df.select_dtypes(include=['object']).columns.tolist()
    
    if text_cols:
        st.subheader("📝 Text Columns Analysis")
        
        selected_text_col = st.selectbox("Select text column:", text_cols)
        
        if selected_text_col:
            value_counts = sample_df[selected_text_col].value_counts().head(10)
            
            if not value_counts.empty:
                fig_bar = px.bar(
                    x=value_counts.values,
                    y=value_counts.index,
                    orientation='h',
                    title=f"Top 10 Values in {selected_text_col}"
                )
                fig_bar.update_layout(yaxis={'categoryorder':'total ascending'})
                st.plotly_chart(fig_bar, use_container_width=True)

def _display_dataset_management(dataset_name: str, dataset_info):
    """Display dataset management tab."""
    st.subheader("⚙️ Dataset Management")
    
    # Dataset information
    st.subheader("ℹ️ Dataset Information")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.write(f"**Name:** {dataset_info['dataset_name']}")
        st.write(f"**Display Name:** {dataset_info['display_name']}")
        st.write(f"**Storage Type:** {dataset_info['storage_type']}")
        st.write(f"**Upload Date:** {dataset_info['upload_date']}")
        
    with col2:
        st.write(f"**File Size:** {_format_file_size(dataset_info['file_size'])}")
        st.write(f"**Rows:** {dataset_info['row_count']:,}")
        st.write(f"**Columns:** {dataset_info['column_count']}")
        st.write(f"**Last Accessed:** {dataset_info['last_accessed'] or 'Never'}")
    
    if dataset_info['tags']:
        st.write("**Tags:**")
        st.write(", ".join(dataset_info['tags']))
    
    # Management actions
    st.subheader("🔧 Actions")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Export dataset
        if st.button("📤 Export Dataset"):
            success, export_df, message = dataset_manager.get_dataset_preview(dataset_name, 100000)  # Large limit for export
            
            if success and not export_df.empty:
                csv = export_df.to_csv(index=False)
                st.download_button(
                    label="💾 Download Full Dataset",
                    data=csv,
                    file_name=f"{dataset_name}_full_export.csv",
                    mime="text/csv"
                )
            else:
                st.error(f"❌ Export failed: {message}")
    
    with col2:
        # Delete dataset
        st.write("**⚠️ Danger Zone**")
        if st.button("🗑️ Delete Dataset", type="secondary"):
            st.warning("⚠️ This action cannot be undone!")
            
            col_confirm1, col_confirm2 = st.columns(2)
            
            with col_confirm1:
                if st.button("✅ Confirm Delete", type="primary"):
                    success, message = dataset_manager.delete_dataset(dataset_name)
                    
                    if success:
                        st.success("✅ Dataset deleted successfully!")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error(f"❌ Delete failed: {message}")
            
            with col_confirm2:
                if st.button("❌ Cancel"):
                    st.info("Delete cancelled")

def _format_file_size(size_bytes: int) -> str:
    """Format file size in human readable format."""
    if size_bytes == 0:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB"]
    i = 0
    size = size_bytes
    
    while size >= 1024 and i < len(size_names) - 1:
        size /= 1024.0
        i += 1
    
    return f"{size:.1f} {size_names[i]}"
