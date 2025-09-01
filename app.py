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

# bucket structure per major: {'courses_df': df, 'progress_df': df, 'advising_selections': {}, 'advising_sessions': []}
if "majors" not in st.session_state:
    st.session_state.majors = {m: {"courses_df": pd.DataFrame(),
                                   "progress_df": pd.DataFrame(),
                                   "advising_selections": {},
                                   "advising_sessions": []}
                               for m in MAJORS}

# pick major at the very beginning
selected_major = st.selectbox("Major", MAJORS, key="current_major")

# expose the current major bucket to the rest of the app (global aliases)
def _sync_globals_from_bucket():
    bucket = st.session_state.majors[selected_major]
    st.session_state.courses_df = bucket["courses_df"]
    st.session_state.progress_df = bucket["progress_df"]
    st.session_state.advising_selections = bucket["advising_selections"]
    # advising_sessions is handled inside advising_history; no need to alias here

def _sync_bucket_from_globals():
    bucket = st.session_state.majors[selected_major]
    bucket["courses_df"] = st.session_state.get("courses_df", pd.DataFrame())
    bucket["progress_df"] = st.session_state.get("progress_df", pd.DataFrame())
    bucket["advising_selections"] = st.session_state.get("advising_selections", {})

# initialize aliases on each run
_sync_globals_from_bucket()

# ---------- Google Drive bootstrap (optional) ----------
service = None
try:
    service = initialize_drive_service()
except Exception as e:
    st.sidebar.warning("Google Drive not configured or unreachable. You can still upload files locally.")
    log_error("initialize_drive_service failed", e)

def _load_from_drive_safe(filename: str) -> bytes | None:
    if service is None:
        return None
    try:
        file_id = find_file_in_drive(service, filename, st.secrets["google"]["folder_id"])
        if not file_id:
            return None
        return download_file_from_drive(service, file_id)
    except Exception as e:
        log_error(f"Drive load failed for {filename}", e)
        return None

# Preload (per-major filenames)
courses_name = f"{selected_major}_courses_table.xlsx"
progress_name = f"{selected_major}_progress_report.xlsx"

if st.session_state.courses_df.empty:
    courses_bytes = _load_from_drive_safe(courses_name)
    if courses_bytes:
        try:
            st.session_state.courses_df = pd.read_excel(BytesIO(courses_bytes))
            st.success(f"✅ Courses table loaded from Google Drive for {selected_major}.")
            log_info(f"Courses table loaded from Drive ({selected_major}).")
        except Exception as e:
            st.error(f"❌ Error loading courses table: {e}")
            log_error("Error loading courses table (Drive)", e)

if st.session_state.progress_df.empty:
    prog_bytes = _load_from_drive_safe(progress_name)
    if prog_bytes:
        try:
            st.session_state.progress_df = load_progress_excel(prog_bytes)
            st.success(f"✅ Progress report loaded from Google Drive for {selected_major} (Required + Intensive merged).")
            log_info(f"Progress report loaded & merged from Drive ({selected_major}).")
        except Exception as e:
            st.error(f"❌ Error loading progress report: {e}")
            log_error("Error loading progress report (Drive)", e)

# ---------- Sidebar Uploads (always available, per-major) ----------
upload_data()             # writes back to the current major's bucket too
_sync_bucket_from_globals()

# ---------- Safe loader for Advising Sessions panel ----------
def _render_advising_panel_safely():
    """
    Load and render Advising Sessions panel without breaking the page.
    """
    try:
        mod = importlib.import_module("advising_history")
        mod = importlib.reload(mod)
        panel = getattr(mod, "advising_history_panel", None)
        if callable(panel):
            panel()  # panel handles per-major filenames internally
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
