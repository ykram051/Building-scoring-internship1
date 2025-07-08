import streamlit as st
from pathlib import Path

def load_css(css_file_path):
    """
    Load CSS from a file and inject it into the Streamlit app
    
    Args:
        css_file_path (str): Path to the CSS file
    """
    # Try multiple possible locations for the CSS file
    possible_paths = [
        css_file_path,
        f"app/{css_file_path}",
        Path(__file__).parent.parent / css_file_path,
        Path(__file__).parent.parent / css_file_path.replace('app/', ''),
        Path(__file__).parent.parent.parent / css_file_path,
        Path(".") / css_file_path,
        Path(".") / "app" / "styles.css",
        Path("styles.css")
    ]
    
    # Only log on first attempt (use session state to track)
    show_logs = 'css_loaded' not in st.session_state
    
    if show_logs:
        print(f"Looking for CSS file at these locations:")
        for i, path in enumerate(possible_paths):
            print(f"  {i+1}. {path}")
    
    for path in possible_paths:
        try:
            with open(path, "r") as f:
                css = f.read()
                st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)
                if show_logs:
                    print(f"✅ CSS file found and loaded from: {path}")
                st.session_state.css_loaded = True
                return  # Successfully loaded CSS
        except FileNotFoundError:
            continue
    
    # If we get here, no CSS file was found
    if show_logs:
        st.warning(f"CSS file not found: {css_file_path}")
        print(f"❌ CSS file not found at any of the attempted locations")
    # Continue without CSS rather than failing