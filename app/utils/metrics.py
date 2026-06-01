import pandas as pd
import streamlit as st
import plotly.graph_objects as go

def calculate_average_metrics(df: pd.DataFrame) -> dict:
    """
    Calculates average metrics for CO2 Usage, Water Usage, and Energy Consumption.

    Args:
        df (pd.DataFrame): The DataFrame containing the metrics.

    Returns:
        dict: A dictionary of average metrics.
    """
    if df.empty:
        return {}

    return {
        "Average CO2 Usage": df["CO2_Usage"].mean(),
        "Average Water Usage": df["Water_Usage"].mean(),
        "Average Energy Consumption": df["Energy_Consumption"].mean(),
        "Most Common Class": df["class_label"].mode().iloc[0]
    }


def display_metrics_overview(df: pd.DataFrame) -> None:
    """
    Displays an overview of metrics in a Streamlit app.

    Args:
        df (pd.DataFrame): The DataFrame containing the metrics.
    """
    if df.empty:
        st.warning("No data to display metrics.")
        return

    st.subheader("Metrics Overview")
    metrics = calculate_average_metrics(df)

    col1, col2 = st.columns(2)
    with col1:
        st.metric("Average CO₂ Usage", f"{metrics['Average CO2 Usage']:.1f} kg")
        st.metric("Average Water Usage", f"{metrics['Average Water Usage']:.0f} L")
    with col2:
        st.metric("Average Energy", f"{metrics['Average Energy Consumption']:.0f} kWh")
        st.metric("Class Distribution", f"{metrics['Most Common Class']} (most common)")