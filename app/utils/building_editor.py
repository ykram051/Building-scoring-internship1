"""
Unified Building Editor Module

This module provides functionality for editing building data.
Supports both local DataFrame and PostgreSQL database as data sources.
"""

import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
from utils.db import execute_query
from utils.logger import log_data_change

def display_building_editor(df, building_id, dataset_name=None, data_source="file"):
    """
    Display a form for editing building data.
    Only admin users should have access to this functionality.

    Args:
        df: The full DataFrame containing building data
        building_id: The ID of the building to edit
        dataset_name: The name of the dataset being edited (for DB source)
        data_source: The data source ('file' or 'db')

    Returns:
        Updated DataFrame if changes were made, None otherwise
    """
    if building_id not in df["building_id"].values:
        st.error("Building not found")
        return None

    # Get the building data
    building = df[df["building_id"] == building_id].iloc[0]

    st.markdown("### ✏️ Edit Building Data")
    st.markdown(f"Editing building **{building_id}**")

    # Create a form for editing
    with st.form("building_edit_form"):
        # Show only editable numeric fields
        editable_fields = [
            "Energy_Consumption", 
            "CO2_Usage", 
            "Water_Usage"
        ]

        # Check which fields exist in the DataFrame
        valid_fields = [field for field in editable_fields if field in df.columns]

        # If intensity fields exist, add them too
        if "Energy_Intensity" in df.columns:
            valid_fields.append("Energy_Intensity")
        if "CO2_Intensity" in df.columns:
            valid_fields.append("CO2_Intensity")

        # Create input fields for each valid field
        updated_values = {}
        for field in valid_fields:
            updated_values[field] = st.number_input(
                label=field,
                value=building[field],
                step=0.01
            )

        # Submit button
        submitted = st.form_submit_button("Save Changes")

        if submitted:
            # Update the DataFrame or database
            for field, value in updated_values.items():
                df.loc[df["building_id"] == building_id, field] = value

            if data_source == "db" and dataset_name:
                try:
                    query = f"""
                    UPDATE building_data
                    SET {', '.join([f'{field} = :{field}' for field in updated_values.keys()])}
                    WHERE building_id = :building_id AND dataset_name = :dataset_name
                    """
                    params = {**updated_values, "building_id": building_id, "dataset_name": dataset_name}
                    execute_query(query, params)
                except Exception as e:
                    st.error(f"Failed to update database: {e}")
                    return None

            # Log the changes
            log_data_change("building_edit", st.session_state.get("username", "anonymous"), {
                "building_id": building_id,
                "changes": updated_values
            })

            st.success("Changes saved successfully!")
            return df

    return None

def display_edit_history():
    """Display the history of building edits"""
    if "change_log" not in st.session_state or not st.session_state["change_log"]:
        st.info("No edit history available")
        return
    
    st.markdown("### 📝 Edit History")
    
    for entry in reversed(st.session_state["change_log"]):
        with st.expander(f"{entry['timestamp']} - Building {entry['building_id']} by {entry['username']}"):
            st.write("Changes:")
            for field, value in entry['changes'].items():
                st.write(f"- {field}: {value}")

def save_building_changes(df, filepath):
    """
    Save updated building data back to CSV
    
    Args:
        df: Updated DataFrame
        filepath: Path to save the file
    """
    try:
        df.to_csv(filepath, index=False)
        
        # Log the save action
        username = st.session_state.get("username", "unknown")
        dataset_name = filepath.split("/")[-1].replace(".csv", "")
        
        log_data_change(
            action="save",
            username=username,
            dataset=dataset_name,
            entity_id=None,
            changes={"filepath": filepath}
        )
        
        st.success(f"Changes saved to {filepath}")
        return True
    except Exception as e:
        # Log the error
        username = st.session_state.get("username", "unknown")
        dataset_name = filepath.split("/")[-1].replace(".csv", "")
        
        log_data_change(
            action="save_error",
            username=username,
            dataset=dataset_name,
            entity_id=None,
            changes={"filepath": filepath, "error": str(e)}
        )
        
        st.error(f"Error saving changes: {str(e)}")
        return False
