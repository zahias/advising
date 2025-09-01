# app.py

import os
from io import BytesIO
import importlib

import pandas as pd
import streamlit as st

from data_upload import upload_data
from eligibility_view import student_eligibility_view
from full_student_view import full_student_view
from google_drive import (
    download_file_from_drive,
    initialize_drive_service,
    find_file_in_drive,
)
from utils import log_info, log_error, load_progress_excel

st.set_page_config(page_title="Advising Dashboard", layout="wide")

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
except Exception as e:
    st.sidebar.warning("Google Drive not configured or unreachable. You can still upload files locally.")
    log_error("initialize_drive_service failed", e)

def _load_first_from_drive(filenames: list[str]) -> bytes | None:
    """
    Try a list of names and return the first file's bytes that exists in Drive.
    """
    if service is None:
        return None
    try:
        folder_id = st.secrets["google"]["folder_id"]
        for name in filenames:
            file_id = find_file_in_drive(service, name, folder_id)
            if file_id:
                return download_file_from_drive(service, file_id)
        return None
    except Exception as e:
        log_error(f"Drive load failed for {filenames}", e)
        return None

# ---------- Auto-load per-major files (with legacy fallbacks) ----------
# Per-major names
courses_name_major = f"{selected_major}_courses_table.xlsx"
progress_name_major = f"{selected_major}_progress_report.xlsx"
# Legacy names (fallbacks for backward compatibility)
courses_name_legacy = "courses_table.xlsx"
progress_name_legacy = "progress_report.xlsx"

if st.session_state.courses_df.empty:
    courses_bytes = _load_first_from_drive([courses_name_major, courses_name_legacy])
    if courses_bytes:
        try:
            st.session_state.courses_df = pd.read_excel(BytesIO(courses_bytes))
            if _load_first_from_drive([courses_name_major]) is not None:
                st.success(f"✅ Courses table loaded from Drive for {selected_major}.")
                log_info(f"Courses table loaded from Drive ({selected_major}).")
            else:
                st.info(f"Loaded legacy courses table ({courses_name_legacy}). Consider syncing as {courses_name_major}.")
                log_info(f"Courses table loaded from legacy filename for {selected_major}.")
        except Exception as e:
            st.error(f"❌ Error loading courses table: {e}")
            log_error("Error loading courses table (Drive)", e)

if st.session_state.progress_df.empty:
    prog_bytes = _load_first_from_drive([progress_name_major, progress_name_legacy])
    if prog_bytes:
        try:
            st.session_state.progress_df = load_progress_excel(prog_bytes)
            if _load_first_from_drive([progress_name_major]) is not None:
                st.success(f"✅ Progress report loaded from Drive for {selected_major} (Required + Intensive merged).")
                log_info(f"Progress report loaded & merged from Drive ({selected_major}).")
            else:
                st.info(f"Loaded legacy progress report ({progress_name_legacy}). Consider syncing as {progress_name_major}.")
                log_info(f"Progress report loaded from legacy filename for {selected_major}.")
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
