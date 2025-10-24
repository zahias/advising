# app.py

import os
from io import BytesIO
import importlib

import pandas as pd
import streamlit as st

from data_upload import upload_data
from eligibility_view import student_eligibility_view
from full_student_view import full_student_view
from workflow_header import render_workflow_header
from visual_theme import apply_visual_theme
from google_drive import (
    download_file_from_drive,
    initialize_drive_service,
    find_file_in_drive,
    get_major_folder_id,
    GoogleAuthError,  # <-- add this import
)
from utils import log_info, log_error, load_progress_excel

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

# ---------- Workflow Header ----------
render_workflow_header()

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

# ---------- Main ----------
if not st.session_state.progress_df.empty and not st.session_state.courses_df.empty:
    tab1, tab2 = st.tabs(["Student Eligibility View", "Full Student View"])
    with tab1:
        student_eligibility_view()
    with tab2:
        full_student_view()

    # Advising Sessions (per major)
    _render_advising_panel_safely()
else:
    st.info(f"📝 Please upload both the progress report and courses table for **{selected_major}** to continue.")
