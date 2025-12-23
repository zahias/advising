# app.py

import os
import importlib
from io import BytesIO

import pandas as pd
import streamlit as st

from data_upload import upload_data
from eligibility_view import student_eligibility_view
from full_student_view import full_student_view
from course_planning_view import course_planning_view
from visual_theme import apply_visual_theme
from google_drive import (
    download_file_from_drive,
    initialize_drive_service,
    find_file_in_drive,
    get_major_folder_id,
    GoogleAuthError,
)
from utils import log_info, log_error, load_progress_excel
from advising_history import _load_session_and_apply
from advising_period import get_current_period, start_new_period, get_all_periods
from datetime import datetime


def _default_period_for_today(today: datetime | None = None) -> tuple[str, int]:
    """Return the default semester and year based on the current date."""
    today = today or datetime.now()
    month = today.month
    year = today.year

    if month == 1:
        # January belongs to the Fall term of the prior calendar year
        return "Fall", year - 1
    if 2 <= month <= 6:
        return "Spring", year
    if 7 <= month <= 9:
        return "Summer", year
    # October-December (and any remaining months) map to Fall of the current year
    return "Fall", year

st.set_page_config(page_title="Advising Dashboard", layout="wide")

# Apply visual theme and accessibility improvements
apply_visual_theme()

# ---------- Header / Logo ----------
if os.path.exists("pu_logo.png"):
    st.image("pu_logo.png", width=160)
st.title("Advising Dashboard")

# ---------- Majors ----------
MAJORS = ["PBHL", "SPTH-New", "SPTH-Old"]

# Per-major buckets persisted in session_state
if "majors" not in st.session_state:
    st.session_state.majors = {
        m: {
            "courses_df": pd.DataFrame(),
            "progress_df": pd.DataFrame(),
            "advising_selections": {},
            # advising_sessions are handled by advising_history; bucket is kept in sync there
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

