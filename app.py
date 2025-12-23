# app.py - Advising Dashboard with Modern UI

import os
import pandas as pd
import streamlit as st
from datetime import datetime

# Import views and utilities
from visual_theme import apply_visual_theme
from utils import log_info, log_error, load_progress_excel
import data_upload  # Explicit import to avoid NameError
from eligibility_view import student_eligibility_view
from full_student_view import full_student_view
from course_offering_planner import course_offering_planner
from advising_history import advising_history_panel

# Lazy loader for drive if needed
def _get_drive_module():
    import google_drive as gd
    return gd

st.set_page_config(
    page_title="Advising Dashboard",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Apply visual theme
apply_visual_theme()

# ---------- Majors ----------
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

# ---------- State Management Helpers ----------

def _sync_bucket_from_globals():
    """Save current globals back to the major-specific bucket."""
    m = st.session_state.get("current_major")
    if m and m in st.session_state.majors:
        st.session_state.majors[m]["courses_df"] = st.session_state.get("courses_df", pd.DataFrame())
        st.session_state.majors[m]["progress_df"] = st.session_state.get("progress_df", pd.DataFrame())
        st.session_state.majors[m]["advising_selections"] = st.session_state.get("advising_selections", {})

def _load_bucket_to_globals(major: str):
    """Load data from major-specific bucket into globals."""
    if major in st.session_state.majors:
        bucket = st.session_state.majors[major]
        st.session_state.courses_df = bucket["courses_df"]
        st.session_state.progress_df = bucket["progress_df"]
        st.session_state.advising_selections = bucket["advising_selections"]
    else:
        # Should not happen, but safe fallback
        st.session_state.courses_df = pd.DataFrame()
        st.session_state.progress_df = pd.DataFrame()
        st.session_state.advising_selections = {}

from io import BytesIO

def _attempt_auto_load_from_drive(major: str):
    """Attempt to load data from Drive if not present in memory."""
    if major not in st.session_state.majors:
        return

    # If already loaded, skip
    bucket = st.session_state.majors[major]
    if not bucket["courses_df"].empty and not bucket["progress_df"].empty:
        return

    try:
        # Import here to avoid early failures if Drive not set up
        from google_drive import initialize_drive_service, get_major_folder_id, download_file_by_name, GoogleAuthError
        
        try:
            service = initialize_drive_service()
        except GoogleAuthError:
            # Drive not available/configured, skip silently (user will see warning in dashboard)
            return

        # Get root folder
        root_id = ""
        if "google" in st.secrets:
            root_id = st.secrets["google"].get("folder_id", "")
        if not root_id:
            root_id = os.getenv("GOOGLE_FOLDER_ID", "")
        
        if not root_id:
            return

        major_folder_id = get_major_folder_id(service, major, root_id)
        
        # Load Courses
        if bucket["courses_df"].empty:
            content = download_file_by_name(service, major_folder_id, "courses_table.xlsx")
            if content:
                df = pd.read_excel(BytesIO(content))
                st.session_state.majors[major]["courses_df"] = df
                st.toast(f"✅ Loaded courses for {major}")

        # Load Progress
        if bucket["progress_df"].empty:
            content = download_file_by_name(service, major_folder_id, "progress_report.xlsx")
            if content:
                df = load_progress_excel(content)
                st.session_state.majors[major]["progress_df"] = df
                st.toast(f"✅ Loaded progress for {major}")

    except Exception as e:
        log_error(f"Auto-load from Drive failed for {major}", e)
        # Don't show error to user user, just log it. They will see "Data not loaded" in UI.

# ---------- Sidebar Navigation & Layout ----------

# Initialize navigation state
if "nav_selection" not in st.session_state:
    st.session_state["nav_selection"] = "Dashboard"

with st.sidebar:
    if os.path.exists("pu_logo.png"):
        st.image("pu_logo.png", width=120) 
    
    st.title("Advising Portal")
    
    # Major Selection
    # We must handle the change *before* rendering the rest of the app for consistency
    previous_major = st.session_state.get("current_major", MAJORS[0])
    selected_major = st.selectbox("Current Major", MAJORS, index=MAJORS.index(previous_major) if previous_major in MAJORS else 0, key="major_selector")
    
    # Logic to handle major switch
    if selected_major != previous_major:
        pass # Streamlit reruns on change, so checking state below is enough

    # Update global current_major
    if "current_major" not in st.session_state or st.session_state["current_major"] != selected_major:
        # Save old data if needed (optional, assuming auto-save happened at end of last run)
        # Load new data
        _attempt_auto_load_from_drive(selected_major)
        _load_bucket_to_globals(selected_major)
        st.session_state["current_major"] = selected_major
        st.rerun()

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
        data_upload.upload_data()

# ---------- Main Content Area ----------

# Import dashboard view here to avoid circular logic (though less of an issue now)
from dashboard_view import dashboard_view

# Check if data is loaded
data_loaded = not st.session_state.get("progress_df", pd.DataFrame()).empty and not st.session_state.get("courses_df", pd.DataFrame()).empty

if not data_loaded:
    if st.session_state["nav_selection"] == "Dashboard":
        dashboard_view()
        st.warning(f"⚠️ Data not fully loaded for **{selected_major}**. Please upload Progress Report and Courses Table in the sidebar.")
    else:
        dashboard_view() # Show dashboard anyway as fallback
        st.info(f"📝 Please upload both the progress report and courses table for **{selected_major}** to continue.")
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
        course_offering_planner()
        
    elif view == "Advising History":
        advising_history_panel()

# Sync buckets at end of run to ensure any edits to DF are captured
_sync_bucket_from_globals()
