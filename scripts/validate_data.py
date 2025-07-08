from pathlib import Path
from typing import List, Optional

import pandas as pd
import streamlit as st

# ──────────────────────────────────────────────────────────────
#  Imports for classification models
# ──────────────────────────────────────────────────────────────
from models.mahalanobis import classify_mahalanobis
from models.pca import classify_pca
from models.weighted import classify_weighted
from models.tree_classifier import classify_robust_tree
from models.cosine import classify_cosine
from models.topsis import classify_topsis


# ──────────────────────────────────────────────────────────────
#  Constants
# ──────────────────────────────────────────────────────────────
REQUIRED_COLUMNS = [
    "building_id", "latitude", "longitude",
    "CO2_Usage", "Water_Usage", "Energy_Consumption",
]
INTENSITY_COLUMNS = ["Energy_Intensity", "CO2_Intensity"]

# ──────────────────────────────────────────────────────────────
#  Validation / Pre‑processing
# ──────────────────────────────────────────────────────────────

def validate_and_preprocess_dataset(df: pd.DataFrame, scoring_basis: str) -> Optional[pd.DataFrame]:
    """Validate columns, coerce numerics & switch to intensity metrics when requested."""
    
    # Check if df is None
    if df is None:
        st.error("Cannot validate None dataframe")
        return None
        
    # Check if df has columns attribute (is a proper DataFrame)
    if not hasattr(df, 'columns'):
        st.error("Invalid dataframe object - missing columns attribute")
        return None
        
    # Check if df is empty
    if df.empty:
        st.warning("Empty dataframe provided for validation")
        return df.copy()  # Return empty copy

    # 1 ▸ Handle intensity‑based scoring toggle
    if scoring_basis == "Per m² (kWh/m²/year)":
        if set(INTENSITY_COLUMNS).issubset(df.columns):
            df = df.copy()
            df["Energy_Consumption"] = df["Energy_Intensity"]
            df["CO2_Usage"] = df["CO2_Intensity"]
        else:
            st.warning("Missing Energy_Intensity/CO2_Intensity columns for intensity‑based scoring. Using total values instead.")
            # No need to return None, we'll continue with the total values

    # 2 ▸ Check required cols and try to fix any missing columns
    df = df.copy()  # Ensure we're working with a copy
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    
    # Try to recover from missing columns
    if missing:
        # Check if we can fix some common issues
        if "building_id" in missing and "id" in df.columns:
            df["building_id"] = df["id"]
            missing.remove("building_id")
            
        # Handle coordinate columns
        coord_missing = set(["latitude", "longitude"]) & set(missing)
        if coord_missing and "address" in df.columns:
            st.warning("Missing coordinate columns. Will use placeholder values.")
            for col in coord_missing:
                df[col] = 45.0 if col == "latitude" else 5.0  # Default values for France
                missing.remove(col)
                
        # Handle required consumption/usage columns
        if "Energy_Consumption" in missing and "energy_usage" in df.columns:
            df["Energy_Consumption"] = df["energy_usage"]
            missing.remove("Energy_Consumption")
            
        if "CO2_Usage" in missing and "co2_emissions" in df.columns:
            df["CO2_Usage"] = df["co2_emissions"]
            missing.remove("CO2_Usage")
            
        if "Water_Usage" in missing and "water_consumption" in df.columns:
            df["Water_Usage"] = df["water_consumption"]
            missing.remove("Water_Usage")
            
        # If still missing required columns
        if missing:
            st.warning(f"Missing required columns and couldn't find alternatives: {missing}")
            
            # As a last resort, add missing columns with default values
            for col in missing:
                if col in ["CO2_Usage", "Water_Usage", "Energy_Consumption"]:
                    # For numeric columns, use reasonable defaults
                    default_val = 1000 if col == "Energy_Consumption" else 500
                    df[col] = default_val
                    st.warning(f"Added default values for {col}: {default_val}")
                elif col == "building_id":
                    # Create sequential IDs
                    df[col] = [f"gen_id_{i}" for i in range(len(df))]
                    st.warning("Generated sequential building IDs")
                elif col in ["latitude", "longitude"]:
                    # Default coordinates (Paris)
                    df[col] = 48.8566 if col == "latitude" else 2.3522
                    st.warning(f"Added default Paris coordinates for {col}")

    # 3 ▸ Coerce numerics & handle NA values in required cols
    numeric_cols = ["latitude", "longitude", "CO2_Usage", "Water_Usage", "Energy_Consumption"]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
            
    # Check for NaN values and try to fix them
    na_cols = [col for col in REQUIRED_COLUMNS if col in df.columns and df[col].isna().any()]
    if na_cols:
        st.warning(f"Found NaN values in columns: {na_cols}")
        
        # For each column with NaNs, fill with median or a default value
        for col in na_cols:
            # For numeric columns, use median
            if col in numeric_cols:
                median_val = df[col].median()
                # If median is also NaN (all values are NaN), use a default
                if pd.isna(median_val):
                    if col in ["latitude", "longitude"]:
                        default_val = 45.0 if col == "latitude" else 5.0  # France
                    else:
                        default_val = 1000 if col == "Energy_Consumption" else 500
                    df[col] = df[col].fillna(default_val)
                    st.warning(f"Filled NaN values in {col} with default: {default_val}")
                else:
                    df[col] = df[col].fillna(median_val)
                    st.warning(f"Filled NaN values in {col} with median: {median_val:.2f}")
            else:
                # For non-numeric columns, use a placeholder
                if col == "building_id":
                    # For building_id, generate random IDs
                    import uuid
                    for idx in df[df[col].isna()].index:
                        df.at[idx, col] = f"gen_{uuid.uuid4().hex[:8]}"
                    st.warning(f"Generated IDs for missing values in {col}")
    
    # Only drop rows that are still NA after filling attempts
    before_len = len(df)
    df = df.dropna(subset=REQUIRED_COLUMNS)
    if len(df) < before_len:
        st.warning(f"Removed {before_len - len(df)} rows with remaining NaN values")
        
    if df.empty:
        st.error("Dataset is empty after preprocessing.")
        return None

    return df

# ------------------------------------------------------------------
# Utility: ensure the chosen class columns exist
# ------------------------------------------------------------------
def ensure_classifications(df, features, weights):
    """Call add_classifications() only when at least one class_* column
    is missing.  Returns df unchanged if everything is already there."""
    # Check if df is None or doesn't have columns attribute
    if df is None:
        st.error("Cannot ensure classifications on None dataframe")
        return None
        
    if not hasattr(df, 'columns'):
        st.error("Invalid dataframe object - missing columns attribute")
        return None
        
    # Check if dataframe is empty
    if df.empty:
        st.warning("Empty dataframe, cannot add classifications")
        return df
        
    # Check if features exist in the dataframe
    missing_features = [f for f in features if f not in df.columns]
    if missing_features:
        st.warning(f"Missing features for classification: {missing_features}")
        
        # Try to add common features if they're missing
        if "Energy_Consumption" in features and "Energy_Consumption" not in df.columns:
            df = df.copy()
            df["Energy_Consumption"] = 1000  # Default value
            st.warning("Added default Energy_Consumption for classification")
        
        if "CO2_Usage" in features and "CO2_Usage" not in df.columns:
            df = df.copy()
            df["CO2_Usage"] = 500  # Default value
            st.warning("Added default CO2_Usage for classification")
            
        if "Water_Usage" in features and "Water_Usage" not in df.columns:
            df = df.copy()
            df["Water_Usage"] = 500  # Default value
            st.warning("Added default Water_Usage for classification")
        
        # Recheck features after adding defaults
        missing_features = [f for f in features if f not in df.columns]
        if missing_features:
            st.error(f"Still missing features for classification: {missing_features}")
            # Try a fallback classification with just the available features
            available_features = [f for f in features if f in df.columns]
            if len(available_features) >= 2:
                st.warning(f"Attempting classification with available features: {available_features}")
                features = available_features
            else:
                st.error("Not enough features available for classification")
                # Add class_label with default value 'C'
                df = df.copy()
                for class_col in ["class_cosine", "class_mahalanobis", "class_pca", 
                                   "class_weighted", "class_tree", "class_topsis"]:
                    df[class_col] = "C"
                df["class_label"] = "C"
                return df
        
    expected = {
        "class_cosine",
        "class_mahalanobis",
        "class_pca",
        "class_weighted",
        "class_tree",
        "class_topsis",
    }
    
    if expected.issubset(df.columns):
        if "class_label" not in df.columns:
            df = df.copy()
            df["class_label"] = df["class_cosine"]  # Use cosine as default
        return df          # nothing to do
        
    try:
        result = add_classifications(df, features=features, weights=weights)
        # Ensure class_label is set
        if "class_label" not in result.columns:
            result["class_label"] = result["class_cosine"]
        return result
    except Exception as e:
        st.error(f"Error adding classifications: {e}")
        # Add fallback classifications if the process failed
        df = df.copy()
        for class_col in ["class_cosine", "class_mahalanobis", "class_pca", 
                           "class_weighted", "class_tree", "class_topsis"]:
            if class_col not in df.columns:
                df[class_col] = "C"
        
        if "class_label" not in df.columns:
            df["class_label"] = "C"
            
        return df


# ──────────────────────────────────────────────────────────────
#  Classification helper
# ──────────────────────────────────────────────────────────────

def add_classifications(
    df: pd.DataFrame,
    features: List[str],
    weights: Optional[List[float]] = None,
) -> pd.DataFrame:
    """Run *all* classifiers (Mahalanobis, PCA, Weighted, tree_classifier,
    cosine, TOPSIS) and append their `class_*` columns.
    """

    if len(features) < 2:
        st.error("Need at least two features for classification.")
        return df

    out = df.copy()

    # –– Mahalanobis ––
    try:
        mah = classify_mahalanobis(out, features=features, return_distance=True)
        out["class_mahalanobis"] = mah["class_label"]
        if "Mahalanobis_Distance" in mah:
            out["Mahalanobis_Distance"] = mah["Mahalanobis_Distance"]
    except Exception as e:
        st.warning(f"Mahalanobis failed: {e}")
        out["class_mahalanobis"] = "C"

    # –– PCA ––
    try:
        out["class_pca"] = classify_pca(out, features=features)["class_label"]
    except Exception as e:
        st.warning(f"PCA failed: {e}")
        out["class_pca"] = "C"

    # –– Weighted ––
    try:
        if weights is None:
            weights = [1.0] * len(features)
        out["class_weighted"] = classify_weighted(out, features=features, weights=weights)["class_label"]
    except Exception as e:
        st.warning(f"Weighted failed: {e}")
        out["class_weighted"] = "C"

    # –– tree_classifier ––
    try:
        tree = classify_robust_tree(out, numeric_features=features)  # Note: tree classifier uses numeric_features
        out["class_tree"] = tree["class_tree"]
    except Exception as e:
        st.warning(f"tree classifier failed: {e}")
        out["class_tree"] = "C"

    # –– cosine ––
    try:
        out["class_cosine"] = classify_cosine(out, features=features)["class_label"]
    except Exception as e:
        st.warning(f"cosine failed: {e}")
        out["class_cosine"] = "C"

    # –– TOPSIS ––
    try:
        out["class_topsis"] = classify_topsis(out, features=features, weights=weights)["class_topsis"]
        out["topsis_score"] = classify_topsis(out, features=features, weights=weights)["topsis_score"]
    except Exception as e:
        st.warning(f"TOPSIS failed: {e}")
        out["class_topsis"] = "C"

    return out
