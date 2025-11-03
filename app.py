# app.py

import os
import importlib
from io import BytesIO

import pandas as pd
import streamlit as st

from data_upload import upload_data
from eligibility_view import student_eligibility_view
from full_student_view import full_student_view
from dependency_tree_view import dependency_tree_view
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

# Choose major up-front
selected_major = st.selectbox("Major", MAJORS, key="current_major")

# ---------- Period Selection Gate ----------
# Check if period has been selected for this major
period_selected_key = f"period_selected_{selected_major}"
if period_selected_key not in st.session_state:
    st.session_state[period_selected_key] = False

# Get current period to check if one exists
current_period = get_current_period()
all_periods = get_all_periods()

# If period not yet selected, show selection interface
if not st.session_state[period_selected_key]:
    st.markdown("---")
    st.markdown("## 📅 Select Advising Period")
    st.markdown("Before accessing the advising dashboard, please select an advising period.")

    # Create two columns for the two options
    col_new, col_existing = st.columns(2)

    with col_new:
        st.markdown("### 🆕 Start New Period")
        with st.form("period_selection_new"):
            default_semester, default_year = _default_period_for_today()
            semester_options = ["Fall", "Spring", "Summer"]
            if "period_select_semester" not in st.session_state or st.session_state["period_select_semester"] not in semester_options:
                st.session_state["period_select_semester"] = default_semester
            if "period_select_year" not in st.session_state:
                st.session_state["period_select_year"] = default_year
            semester_index = semester_options.index(st.session_state["period_select_semester"])
            semester = st.selectbox(
                "Semester",
                semester_options,
                index=semester_index,
                key="period_select_semester",
            )
            year = st.number_input(
                "Year",
                min_value=2020,
                max_value=2099,
                value=st.session_state["period_select_year"],
                step=1,
                key="period_select_year",
            )
            advisor_name = st.text_input("Advisor Name", key="period_select_advisor")
            
            if st.form_submit_button("Start New Period", width="stretch", type="primary"):
                if not advisor_name:
                    st.error("Please enter advisor name")
                else:
                    # Clear all selections when starting new period
                    st.session_state.advising_selections = {}
                    st.session_state.majors[selected_major]["advising_selections"] = {}
                    for key in list(st.session_state.keys()):
                        if isinstance(key, str) and key.startswith("_autoloaded_"):
                            del st.session_state[key]
                    if "current_student_id" in st.session_state:
                        del st.session_state["current_student_id"]
                    
                    # Start new period
                    with st.spinner("Creating new period and saving to Drive..."):
                        new_period, drive_saved = start_new_period(semester, int(year), advisor_name)

                    st.session_state[period_selected_key] = True
                    if drive_saved:
                        st.success(f"✅ Started new period: {semester} {year} (saved to Drive)")
                    else:
                        st.warning(
                            f"⚠️ Started new period: {semester} {year} (WARNING: Not saved to Drive - period may not persist)"
                        )
                        st.info("Check your Google Drive connection and try again.")
                    st.rerun()
    
    with col_existing:
        st.markdown("### 📂 Use Existing Period")
        
        # Filter out default periods (those with empty advisor_name)
        real_periods = [p for p in all_periods if p.get('advisor_name', '').strip()]
        
        if real_periods:
            # Create dropdown of all real periods (excluding defaults)
            period_options = []
            period_map = {}
            for p in real_periods:
                label = f"{p.get('semester', '')} {p.get('year', '')} — {p.get('advisor_name', 'Unknown')}"
                period_options.append(label)
                period_map[label] = p
            
            with st.form("period_selection_existing"):
                selected_period_label = st.selectbox("Select Period", period_options, key="period_select_existing")
                
                if st.form_submit_button("Use This Period", width="stretch"):
                    selected_period = period_map[selected_period_label]
                    
                    # If selecting a different period than current, we need to switch to it
                    if selected_period.get("period_id") != current_period.get("period_id"):
                        # Set as current period
                        from advising_period import set_current_period
                        set_current_period(selected_period)
                        
                        # Clear selections
                        st.session_state.advising_selections = {}
                        st.session_state.majors[selected_major]["advising_selections"] = {}
                        for key in list(st.session_state.keys()):
                            if isinstance(key, str) and key.startswith("_autoloaded_"):
                                del st.session_state[key]
                        if "current_student_id" in st.session_state:
                            del st.session_state["current_student_id"]
                    
                    st.session_state[period_selected_key] = True
                    st.success(f"✅ Using period: {selected_period_label}")
                    st.rerun()
        else:
            st.info("No existing periods found. Please start a new period.")
    
    st.stop()  # Stop execution here until period is selected

# ---------- Current Advising Period Display ----------
st.markdown(f"**Current Advising Period:** {current_period.get('semester', '')} {current_period.get('year', '')} — Advisor: {current_period.get('advisor_name', 'Not set')}")

# Utility buttons for advising selections
with st.expander("⚙️ Advising Utilities"):
    st.markdown("### Advising Period Management")
    
    # Add button to change period
    if st.button("🔄 Change Advising Period", help="Switch to a different advising period", width="stretch"):
        st.session_state[period_selected_key] = False
        st.rerun()
    
    # Start New Period
    with st.form("new_period_form"):
        st.markdown("**Start New Advising Period**")
        col_sem, col_year, col_advisor = st.columns(3)

        with col_sem:
            default_semester, default_year = _default_period_for_today()
            semester_options = ["Fall", "Spring", "Summer"]
            if "new_period_semester" not in st.session_state or st.session_state["new_period_semester"] not in semester_options:
                st.session_state["new_period_semester"] = default_semester
            semester_index = semester_options.index(st.session_state["new_period_semester"])
            semester = st.selectbox(
                "Semester",
                semester_options,
                index=semester_index,
                key="new_period_semester",
            )

        with col_year:
            if "new_period_year" not in st.session_state:
                st.session_state["new_period_year"] = default_year
            year = st.number_input(
                "Year",
                min_value=2020,
                max_value=2099,
                value=st.session_state["new_period_year"],
                step=1,
                key="new_period_year",
            )
        
        with col_advisor:
            advisor_name = st.text_input("Advisor Name", key="new_period_advisor")
        
        if st.form_submit_button("🆕 Start New Period", width="stretch", type="primary"):
            if not advisor_name:
                st.error("Please enter advisor name")
            else:
                # Clear all selections when starting new period
                st.session_state.advising_selections = {}
                st.session_state.majors[selected_major]["advising_selections"] = {}
                for key in list(st.session_state.keys()):
                    if isinstance(key, str) and key.startswith("_autoloaded_"):
                        del st.session_state[key]
                if "current_student_id" in st.session_state:
                    del st.session_state["current_student_id"]
                
                # Start new period
                new_period, drive_saved = start_new_period(semester, int(year), advisor_name)
                if drive_saved:
                    st.success(f"✅ Started new period: {semester} {year}")
                else:
                    st.warning(
                        f"⚠️ Started new period: {semester} {year} (Drive sync failed — working offline, period cached only)"
                    )
                st.rerun()
    
    st.markdown("---")
    st.markdown("### Session Management")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🗑️ Clear All Selections", help="Clear current advising selections for all students (does not affect saved sessions)", width="stretch"):
            # Clear advising selections for all students in current major
            st.session_state.advising_selections = {}
            # Clear the per-major bucket so it persists across reruns
            st.session_state.majors[selected_major]["advising_selections"] = {}
            # Clear all autoload flags and student search state
            for key in list(st.session_state.keys()):
                if isinstance(key, str):
                    if key.startswith("_autoloaded_"):
                        del st.session_state[key]
                    # Clear student search selections and queries to return to search view
                    elif key.startswith("student_search_") or key.startswith("student_select_") or key.startswith("student_selectbox_"):
                        del st.session_state[key]
            # Clear the current student ID to deselect any loaded student
            if "current_student_id" in st.session_state:
                del st.session_state["current_student_id"]
            st.success(f"✅ Cleared all advising selections for {selected_major}")
            st.rerun()
    
    with col2:
        if st.button("📥 Restore Latest Sessions", help="Load most recent advising session for all students from current period", width="stretch"):
            # Get all unique student IDs from progress report
            if not st.session_state.progress_df.empty and "ID" in st.session_state.progress_df.columns:
                student_ids = st.session_state.progress_df["ID"].unique()
                loaded_count = 0
                for sid in student_ids:
                    # Clear autoload flag so it will load
                    if f"_autoloaded_{sid}" in st.session_state:
                        del st.session_state[f"_autoloaded_{sid}"]
                    # Load session
                    if _load_session_and_apply(sid):
                        loaded_count += 1
                # Sync the restored selections to the per-major bucket
                st.session_state.majors[selected_major]["advising_selections"] = st.session_state.advising_selections.copy()
                st.success(f"✅ Restored latest sessions for {loaded_count} students in {current_period.get('semester', '')} {current_period.get('year', '')}")
                st.rerun()
            else:
                st.warning("No students found in progress report. Upload progress report first.")
    
    st.markdown("---")
    st.markdown("### View Previous Periods")
    
    all_periods = get_all_periods()
    if len(all_periods) > 1:
        # Create dropdown of periods (excluding current)
        period_options = []
        period_map = {}
        for p in all_periods:
            if p.get("period_id") != current_period.get("period_id"):
                label = f"{p.get('semester', '')} {p.get('year', '')} — {p.get('advisor_name', 'Unknown')}"
                period_options.append(label)
                period_map[label] = p
        
        if period_options:
            selected_period_label = st.selectbox("Select Previous Period", ["Select a period..."] + period_options, key="view_previous_period")
            
            if selected_period_label != "Select a period...":
                selected_period = period_map[selected_period_label]
                st.info(f"📅 Viewing: {selected_period_label}")
                st.caption(f"Created: {selected_period.get('created_at', 'Unknown')}")
                st.caption("Note: View archived sessions for this period in the Advising History tab.")
        else:
            st.info("No previous periods found. Start a new period to archive the current one.")
    else:
        st.info("No previous periods found. Start a new period to archive the current one.")

# Helpers to map between the current major bucket and the global aliases used elsewhere
def _sync_globals_from_bucket():
    bucket = st.session_state.majors[selected_major]
    st.session_state.courses_df = bucket.get("courses_df", pd.DataFrame())
    st.session_state.progress_df = bucket.get("progress_df", pd.DataFrame())
    st.session_state.advising_selections = bucket.get("advising_selections", {})

def _sync_bucket_from_globals():
    bucket = st.session_state.majors[selected_major]
    bucket["courses_df"] = st.session_state.get("courses_df", pd.DataFrame())
    bucket["progress_df"] = st.session_state.get("progress_df", pd.DataFrame())
    bucket["advising_selections"] = st.session_state.get("advising_selections", {})

# Initialize aliases on each run (so switching majors swaps the active data)
_sync_globals_from_bucket()

# ---------- Google Drive bootstrap (optional) ----------
service = None
try:
    service = initialize_drive_service()
except GoogleAuthError as e:  # <-- show precise auth cause
    st.sidebar.warning("Google Drive not configured or unreachable. You can still upload files locally.")
    st.sidebar.error(str(e))
    log_error("initialize_drive_service failed", e)
except Exception as e:
    st.sidebar.warning("Google Drive not configured or unreachable. You can still upload files locally.")
    log_error("initialize_drive_service failed", e)

@st.cache_data(ttl=600)
def _load_file_from_major_folder(filename: str, major: str, root_folder_id: str) -> bytes | None:
    """
    Load a file from the major-specific folder. 
    Looks in {ROOT_FOLDER}/{MAJOR}/{filename}
    """
    try:
        if not service or not root_folder_id:
            return None
        major_folder_id = get_major_folder_id(service, major, root_folder_id)
        file_id = find_file_in_drive(service, filename, major_folder_id)
        if file_id:
            return download_file_from_drive(service, file_id)
        return None
    except Exception as e:
        log_error(f"Drive download failed for {filename} in {major}/", e)
        return None

# ---------- Auto-load per-major files from major-specific folders ----------
# Use a session state key to track if we've already loaded for this major
load_key = f"_loaded_{selected_major}"
if load_key not in st.session_state:
    st.session_state[load_key] = False

if not st.session_state[load_key] and st.session_state.courses_df.empty:
    # Get root folder ID
    root_folder_id = ""
    try:
        if "google" in st.secrets:
            root_folder_id = st.secrets["google"].get("folder_id", "")
    except:
        pass
    
    if not root_folder_id:
        root_folder_id = os.getenv("GOOGLE_FOLDER_ID", "")
    
    if root_folder_id and service:
        # Load from {MAJOR}/courses_table.xlsx
        courses_bytes = _load_file_from_major_folder("courses_table.xlsx", selected_major, root_folder_id)
        if courses_bytes:
            try:
                st.session_state.courses_df = pd.read_excel(BytesIO(courses_bytes))
                st.success(f"✅ Courses table loaded from Drive: {selected_major}/courses_table.xlsx")
                log_info(f"Courses table loaded from Drive ({selected_major}).")
            except Exception as e:
                st.error(f"❌ Error loading courses table: {e}")
                log_error("Error loading courses table (Drive)", e)

if not st.session_state[load_key] and st.session_state.progress_df.empty:
    # Get root folder ID (same logic as above)
    root_folder_id = ""
    try:
        if "google" in st.secrets:
            root_folder_id = st.secrets["google"].get("folder_id", "")
    except:
        pass
    
    if not root_folder_id:
        root_folder_id = os.getenv("GOOGLE_FOLDER_ID", "")
    
    if root_folder_id and service:
        # Load from {MAJOR}/progress_report.xlsx
        prog_bytes = _load_file_from_major_folder("progress_report.xlsx", selected_major, root_folder_id)
        if prog_bytes:
            try:
                st.session_state.progress_df = load_progress_excel(prog_bytes)
                st.success(f"✅ Progress report loaded from Drive: {selected_major}/progress_report.xlsx")
                log_info(f"Progress report loaded & merged from Drive ({selected_major}).")
                st.session_state[load_key] = True
            except Exception as e:
                st.error(f"❌ Error loading progress report: {e}")
                log_error("Error loading progress report (Drive)", e)

# ---------- Sidebar Uploads (always available, per-major) ----------
upload_data()             # writes back to the current major's bucket and (optionally) Drive
_sync_bucket_from_globals()


# ---------- Safe loader for Advising Sessions panel ----------
def _render_advising_panel_safely():
    try:
        mod = importlib.import_module("advising_history")
        mod = importlib.reload(mod)
        panel = getattr(mod, "advising_history_panel", None)
        if callable(panel):
            panel()  # panel is already per-major aware
        else:
            st.warning("Advising Sessions panel not found. The rest of the dashboard is available.")
    except Exception as e:
        st.error("Advising Sessions panel failed to load. The rest of the dashboard is available.")
        st.exception(e)
        log_error("Advising Sessions panel error", e)

# ---------- Navigation (always available) ----------
# Initialize active view in session state if not set
if "active_view" not in st.session_state:
    st.session_state.active_view = "Student Eligibility View"

# View selector in sidebar (always shown, but disabled when no data)
has_data = not st.session_state.progress_df.empty and not st.session_state.courses_df.empty

with st.sidebar:
    st.markdown("---")
    st.markdown("### 📑 Navigation")
    view_options = ["Student Eligibility View", "Full Student View", "Dependency Tree"]
    
    if has_data:
        st.session_state.active_view = st.radio(
            "Select View",
            options=view_options,
            index=view_options.index(st.session_state.active_view) if st.session_state.active_view in view_options else 0,
            key="view_selector",
            label_visibility="collapsed"
        )
    else:
        st.radio(
            "Select View",
            options=view_options,
            index=0,
            key="view_selector_disabled",
            label_visibility="collapsed",
            disabled=True
        )
        st.caption("Upload data to enable navigation")

# ---------- Main ----------
if has_data:
    # Render selected view
    if st.session_state.active_view == "Student Eligibility View":
        student_eligibility_view()
    elif st.session_state.active_view == "Full Student View":
        full_student_view()
    elif st.session_state.active_view == "Dependency Tree":
        dependency_tree_view()

    # Advising Sessions (per major)
    _render_advising_panel_safely()
else:
    st.info(f"📝 Please upload both the progress report and courses table for **{selected_major}** to continue.")
