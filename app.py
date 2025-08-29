# app.py

import streamlit as st
import pandas as pd
import os
from io import BytesIO

from data_upload import upload_data
from eligibility_view import student_eligibility_view
from full_student_view import full_student_view
from google_drive import (
    download_file_from_drive,
    sync_file_with_drive,
    initialize_drive_service,
    find_file_in_drive,
)
from utils import log_info, log_error

# ---------------------------------
# App setup
# ---------------------------------
st.set_page_config(layout="wide", page_title="Advising Toolkit")
st.title("Advising Toolkit")

# (Optional) logo at app root
if os.path.exists("pu_logo.png"):
    st.image("pu_logo.png", width=140)

# ---------------------------------
# Cached loaders from Google Drive
# ---------------------------------

@st.cache_data(show_spinner=True)
def _load_excel_from_drive_cached(drive_name: str) -> bytes:
    """Return raw bytes of an xlsx from Drive (cached)."""
    service = initialize_drive_service()
    file_id = find_file_in_drive(service, drive_name)
    if not file_id:
        return b""
    return download_file_from_drive(service, file_id)

def _load_df_from_drive(drive_name: str) -> pd.DataFrame:
    raw = _load_excel_from_drive_cached(drive_name)
    if not raw:
        return pd.DataFrame()
    return pd.read_excel(BytesIO(raw), engine="openpyxl")

def _load_advising_selections(drive_name: str) -> dict:
    raw = _load_excel_from_drive_cached(drive_name)
    if not raw:
        return {}
    df = pd.read_excel(BytesIO(raw), engine="openpyxl")
    selections = {}
    for _, r in df.iterrows():
        sid = r.get('ID')
        if pd.isna(sid):
            continue
        advised = [c.strip() for c in str(r.get('Advised', '')).split(',') if c and c.strip()]
        optional = [c.strip() for c in str(r.get('Optional', '')).split(',') if c and c.strip()]
        selections[sid] = {'advised': advised, 'optional': optional, 'note': str(r.get('Note', '') or '')}
    return selections

# ---------------------------------
# Sidebar: data management
# ---------------------------------

st.sidebar.header("Data")
refresh = st.sidebar.button("🔄 Refresh from Drive", help="Clear cache and reload all Drive files")
if refresh:
    st.cache_data.clear()
    st.experimental_rerun()

upload_data()  # keeps your current upload UX; if anything is uploaded we’ll overwrite below

# Initialize session state containers
for key, default in (('courses_df', pd.DataFrame()),
                     ('progress_df', pd.DataFrame()),
                     ('advising_selections', {}),
                     ('data_uploaded', False)):
    if key not in st.session_state:
        st.session_state[key] = default

# Load from Drive if not present or after upload
COURSES_XLSX = "courses_table.xlsx"
PROGRESS_XLSX = "progress_report.xlsx"
SELECTIONS_XLSX = "advising_selections.xlsx"

if st.session_state.get('data_uploaded'):
    # New uploads exist -> clear cache to force fresh reads next time
    st.cache_data.clear()
    st.session_state.data_uploaded = False

# Read (cached)
if st.session_state.courses_df.empty:
    st.session_state.courses_df = _load_df_from_drive(COURSES_XLSX)
if st.session_state.progress_df.empty:
    st.session_state.progress_df = _load_df_from_drive(PROGRESS_XLSX)
if not st.session_state.advising_selections:
    st.session_state.advising_selections = _load_advising_selections(SELECTIONS_XLSX)

# Status indicators
def _status_badge(ok: bool) -> str:
    return "✅" if ok else "⚠️"

st.sidebar.write(f"{_status_badge(not st.session_state.courses_df.empty)} Courses table")
st.sidebar.write(f"{_status_badge(not st.session_state.progress_df.empty)} Progress report")
st.sidebar.write(f"{_status_badge(bool(st.session_state.advising_selections))} Advising selections")

# ---------------------------------
# Main tabs
# ---------------------------------
if not st.session_state.progress_df.empty and not st.session_state.courses_df.empty:
    tab1, tab2 = st.tabs(['Student Eligibility View', 'Full Student View'])
    with tab1:
        student_eligibility_view()
    with tab2:
        full_student_view()
else:
    st.info('📝 Please upload both the progress report and courses table to continue.')
