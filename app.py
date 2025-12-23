# app.py - Advising Dashboard with Modern UI

import os
import pandas as pd
import streamlit as st
from datetime import datetime

from visual_theme import apply_visual_theme
from utils import log_info, log_error, load_progress_excel

def _get_drive_module():
    """Lazy loader for google_drive module to avoid import-time side effects."""
    import google_drive as gd
    return gd

st.set_page_config(
    page_title="Advising Dashboard",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="collapsed"
)

apply_visual_theme()

MAJORS = ["PBHL", "SPTH-New", "SPTH-Old", "NURS"]

if "majors" not in st.session_state:
    st.session_state.majors = {
        m: {
            "courses_df": pd.DataFrame(),
            "progress_df": pd.DataFrame(),
            "advising_selections": {},
        }
        for m in MAJORS
    }

# ---------- Sidebar Navigation & Layout ----------

# Initialize navigation state
if "nav_selection" not in st.session_state:
    st.session_state["nav_selection"] = "Dashboard"

with st.sidebar:
    st.image("pu_logo.png", width=120) if os.path.exists("pu_logo.png") else None
    
    st.title("Advising Portal")
    
    # Major Selection (moved to sidebar)
    selected_major = st.selectbox("Current Major", MAJORS, key="current_major")
    
    st.markdown("---")
    
    # Navigation Menu
    nav_options = [
        "Dashboard", 
        "Student Eligibility", 
        "Full Student View", 
        "Course Planning",
        "Advising History"
    ]
    
    # Sync state with sidebar widget
    selection = st.radio(
        "Navigation", 
        nav_options, 
        index=nav_options.index(st.session_state["nav_selection"]) if st.session_state["nav_selection"] in nav_options else 0,
        key="nav_radio"
    )
    
    # Update state if changed
    if selection != st.session_state["nav_selection"]:
        st.session_state["nav_selection"] = selection
        st.rerun()

    st.markdown("---")
    
    # Data Management Section
    with st.expander("📂 Data Management", expanded=False):
        upload_data()

# ---------- Main Content Area ----------

# Import dashboard view here to avoid circular dependencies
from dashboard_view import dashboard_view

# Check if data is loaded (dashboard can be shown even without full data, but others need it)
data_loaded = not st.session_state.progress_df.empty and not st.session_state.courses_df.empty

if not data_loaded:
    if st.session_state["nav_selection"] == "Dashboard":
        dashboard_view()
        st.warning(f"⚠️ Data not fully loaded for **{selected_major}**. Please upload Progress Report and Courses Table in the sidebar.")
    else:
        st.info(f"📝 Please upload both the progress report and courses table for **{selected_major}** to continue.")
        st.stop()
else:
    # Router
    view = st.session_state["nav_selection"]
    
    if view == "Dashboard":
        dashboard_view()
        
    elif view == "Student Eligibility":
        st.header("🎓 Student Eligibility View")
        student_eligibility_view()
        
    elif view == "Full Student View":
        st.header("👤 Full Student Profile")
        full_student_view()
        
    elif view == "Course Planning":
        st.header("📊 Course Planning & Optimization")
        course_planning_view()
        
    elif view == "Advising History":
        _render_advising_panel_safely()

# Sync buckets at end of run
_sync_bucket_from_globals()

