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

# ---------- Init session state ----------
for key, default in [
    ("courses_df", pd.DataFrame()),
    ("progress_df", pd.DataFrame()),
    ("advising_selections", {}),
]:
    if key not in st.session_state:
        st.session_state[key] = default

# ---------- Google Drive bootstrap (optional) ----------
service = None
try:
    service = initialize_drive_service()
except Exception as e:
    # Don’t block the app — continue in local-only mode
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

# ---------- Preload from Drive when possible ----------
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

# ---------- Sidebar Uploads (always available) ----------
upload_data()

# ---------- Safe loader for Advising Sessions panel ----------
def _render_advising_panel_safely():
    """
    Try to load and render the Advising Sessions panel without ever breaking the page.
    Works whether advising_history is a module or a package.
    """
    try:
        mod = importlib.import_module("advising_history")
        mod = importlib.reload(mod)
        panel = getattr(mod, "advising_history_panel", None)
        if panel is None:
            try:
                sub = importlib.import_module("advising_history.advising_history")
                sub = importlib.reload(sub)
                panel = getattr(sub, "advising_history_panel", None)
            except Exception:
                panel = None
        if callable(panel):
            panel()
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

    # Advising Sessions panel (robust import & never blocks page)
    _render_advising_panel_safely()
else:
    st.info("📝 Please upload both the progress report and courses table to continue.")
