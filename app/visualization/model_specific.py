import plotly.express as px
import streamlit as st
import pandas as pd
import numpy as np

def display_model_visualization(df: pd.DataFrame, classification_method: str, dataset_name: str = None) -> None:
    """
    Display model-specific visualizations based on classification method.
    Includes ownership and access control validation.
    
    Args:
        df (pd.DataFrame): DataFrame with building data and classifications
        classification_method (str): Selected classification method
        dataset_name (str): Name of the dataset being visualized
    """
    # Import here to avoid circular import issues
    import logging
    from utils.auth_db import check_dataset_ownership
    
    logger = logging.getLogger(__name__)
    
    # Validate access control if dataset name is provided
    if dataset_name and not check_dataset_ownership(dataset_name):
        from utils.auth_db import handle_unauthorized_access
        handle_unauthorized_access(dataset_name, action_type="model analysis")
        return
        
    st.markdown(f"#### {classification_method} Visualization")
    
    # Validate required columns
    required_columns = ["Energy_Consumption", "CO2_Usage", "Water_Usage", "class_label"]
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        st.error(f"Missing required columns: {', '.join(missing_columns)}")
        return
    
    # Validate data types and values
    df = df.copy()
    for col in required_columns[:3]:  # Check numeric columns
        if not pd.api.types.is_numeric_dtype(df[col]):
            st.error(f"Column '{col}' contains non-numeric data.")
            return
        if df[col].isna().any() or np.isinf(df[col]).any():
            st.warning(f"Column '{col}' contains NaN or infinite values. Removing invalid rows.")
            df = df[df[col].notna() & ~np.isinf(df[col])]
    
    # Validate class_label - handle non-standard class values
    valid_classes = ['A', 'B', 'C', 'D', 'E', 'F', 'G']  # Added G which is present in Ciry_le_noble
    
    # First check if class_label column exists
    if "class_label" not in df.columns:
        st.error("Missing class_label column in dataset")
        # Try to recover by using one of the classification columns
        for class_col in ["class_cosine", "class_mahalanobis", "class_pca", "class_weighted", "class_topsis"]:
            if class_col in df.columns:
                st.info(f"Using {class_col} as fallback for class_label")
                df["class_label"] = df[class_col]
                break
        else:
            # If no classification column is found, create a default one
            st.warning("Creating default class_label column as 'C'")
            df["class_label"] = "C"
    
    # Now validate the class values
    if not df["class_label"].isin(valid_classes).all():
        st.warning(f"Note: Some class labels contain non-standard values: {df['class_label'].unique()}")
        # Don't return, still try to display visualization
    
    # If DataFrame is empty after cleaning
    if df.empty:
        st.warning("No valid data available for visualization after cleaning.")
        return
    
    # Define hover data based on classification method
    hover_data = ["building_id", "class_label"]
    if classification_method == "Mahalanobis Distance" and "Mahalanobis_Distance" in df.columns:
        hover_data.append("Mahalanobis_Distance")
    elif classification_method == "Bayesian Classification" and "Bayesian_Certainty" in df.columns:
        hover_data.append("Bayesian_Certainty")
    elif classification_method.startswith("TOPSIS") and "topsis_score" in df.columns:
        hover_data.append("topsis_score")
    else:
        hover_data.append("Energy_Consumption")  # Fallback hover data
    
    # Create 3D scatter plot
    try:
        # Make sure we have valid numeric data for all required columns
        for col in ["Energy_Consumption", "CO2_Usage", "Water_Usage"]:
            # Convert to numeric if needed
            df[col] = pd.to_numeric(df[col], errors='coerce')
            
            # Fill NaN with median values to avoid plot errors
            if df[col].isna().any():
                median_value = df[col].median()
                if pd.isna(median_value):  # If median is also NaN, use a default
                    median_value = 1000 if col == "Energy_Consumption" else 500
                st.warning(f"Replacing NaN values in {col} with median value: {median_value}")
                df[col] = df[col].fillna(median_value)
        
        # Define color sequence with one more color for 'G' class
        color_sequence = [
            '#28a745',  # A - Green
            '#5cb85c',  # B - Light green
            '#ffc107',  # C - Yellow 
            '#fd7e14',  # D - Orange
            '#dc3545',  # E - Red
            '#6c757d',  # F - Gray
            '#17a2b8',  # G - Blue
            '#6610f2'   # Other - Purple
        ]
            
        fig = px.scatter_3d(
            df,
            x="Energy_Consumption",
            y="CO2_Usage",
            z="Water_Usage",
            color="class_label",
            color_discrete_sequence=color_sequence,
            hover_data=hover_data,
            labels={
                "Energy_Consumption": "Energy (kWh)",
                "CO2_Usage": "CO₂ (kg)",
                "Water_Usage": "Water (L)",
                "class_label": "Class"
            }
        )
        
        # Avoid division by zero or other errors by checking for valid ranges
        x_min = df["Energy_Consumption"].min()
        x_max = df["Energy_Consumption"].max()
        y_min = df["CO2_Usage"].min()
        y_max = df["CO2_Usage"].max()
        z_min = df["Water_Usage"].min()
        z_max = df["Water_Usage"].max()
        
        # Ensure ranges are valid
        if x_min == x_max:
            x_min, x_max = x_min * 0.9, x_min * 1.1
        if y_min == y_max:
            y_min, y_max = y_min * 0.9, y_min * 1.1
        if z_min == z_max:
            z_min, z_max = z_min * 0.9, z_min * 1.1
            
        fig.update_layout(
            scene=dict(
                xaxis_title="Energy (kWh)",
                yaxis_title="CO₂ (kg)",
                zaxis_title="Water (L)",
                xaxis=dict(range=[x_min, x_max]),
                yaxis=dict(range=[y_min, y_max]),
                zaxis=dict(range=[z_min, z_max])
            ),
            height=600,
            template="plotly_white"
        )
        
        st.plotly_chart(fig, use_container_width=True, config={'scrollZoom': True})
    
    except Exception as e:
        st.error(f"Error rendering 3D scatter plot: {str(e)}")
        st.write("Debug information:")
        st.write(f"DataFrame shape: {df.shape}")
        st.write("Column data types:")
        st.write(df.dtypes)
        st.write("First few rows:")
        st.write(df.head(3))