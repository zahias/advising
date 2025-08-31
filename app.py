# app.py

import streamlit as st
import pandas as pd
import os
from io import BytesIO

from data_upload import upload_data
from eligibility_view import student_eligibility_view
from full_student_view import full_student_view
import advising_history  # keep module import
from google_drive import (
    download_file_from_drive,
    sync_file_with_drive,
    initialize_drive_service,
    find_file_in_drive,
)
from utils import log_info, log_error, load_progress_excel

st.set_page_config(page_title="Advising Dashboard", layout="wide")

# ---------- Header / Logo ----------
if os.path.exists("pu_logo.png"):
    st.image("pu_logo.png", width=160)
st.title("Advising Dashboard")

# ---------- Init session state ----------
for key, default in [
    ("courses_df", pd.DataFrame()),
    ("progress_df", pd.DataFrame()),
    ("advising_selections", {}),
]:
    if key not in st.session_state:
        st.session_state[key] = default

# ---------- Google Drive bootstrap ----------
service = initialize_drive_service()

def _load_from_drive_safe(filename: str) -> bytes | None:
    try:
        file_id = find_file_in_drive(service, filename, st.secrets["google"]["folder_id"])
        if not file_id:
            return None
        return download_file_from_drive(service, file_id)
    except Exception as e:
        log_error(f"Drive load failed for {filename}", e)
        return None

# Courses table
if st.session_state.courses_df.empty:
    courses_bytes = _load_from_drive_safe("courses_table.xlsx")
    if courses_bytes:
        try:
            st.session_state.courses_df = pd.read_excel(BytesIO(courses_bytes))
            st.success("✅ Courses table loaded from Google Drive.")
            log_info("Courses table loaded from Drive.")
        except Exception as e:
            st.error(f"❌ Error loading courses table: {e}")
            log_error("Error loading courses table (Drive)", e)

# Progress report (merge sheets if present)
if st.session_state.progress_df.empty:
    prog_bytes = _load_from_drive_safe("progress_report.xlsx")
    if prog_bytes:
        try:
            st.session_state.progress_df = load_progress_excel(prog_bytes)
            st.success("✅ Progress report loaded from Google Drive (Required + Intensive merged).")
            log_info("Progress report loaded & merged from Drive.")
        except Exception as e:
            st.error(f"❌ Error loading progress report: {e}")
            log_error("Error loading progress report (Drive)", e)

# ---------- Sidebar Uploads ----------
upload_data()

# ---------- Main ----------
if not st.session_state.progress_df.empty and not st.session_state.courses_df.empty:
    tab1, tab2 = st.tabs(["Student Eligibility View", "Full Student View"])
    with tab1:
        student_eligibility_view()
    with tab2:
        full_student_view()

    # Advising Sessions panel (guarded so a panel error never blanks the page)
    try:
        advising_history.advising_history_panel()
    except Exception as e:
        st.error("Advising Sessions panel failed to load. The rest of the dashboard is available.")
        # Show the actual error so you can fix quickly (no behavior change elsewhere)
        st.exception(e)
        log_error("Advising Sessions panel error", e)

else:
    st.info("📝 Please upload both the progress report and courses table to continue.")
