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
    find_file_in_drive
)

from reporting import apply_excel_formatting, create_full_advising_report
from utils import initialize_session_state, log_info, log_error, style_df

# Set page configuration
st.set_page_config(layout='wide')

# Header: Logo and title side by side
header_col1, header_col2 = st.columns([0.15, 0.85])
with header_col1:
    if os.path.exists('pu_logo.png'):
        st.image('pu_logo.png', use_container_width=True)
    else:
        st.write('Logo not found.')

with header_col2:
    st.markdown("""
        <h2 style="margin-bottom:0">PU Academic Advising Tool</h2>
        <p style="margin-top:0;color:#666">Streamlined eligibility, advising, and reporting.</p>
    """, unsafe_allow_html=True)

st.markdown("<small>System developed by Dr. Zahi Abdul Sater</small>", unsafe_allow_html=True)

# --- Refresh from Drive (clears cached Drive reads) ---
with st.sidebar:
    if st.button("🔄 Refresh from Drive", help="Clear cached Drive files and reload"):
        # Clear Streamlit's cached Drive reads and local session dataframes
        st.cache_data.clear()
        for key in ("courses_df", "progress_df", "advising_selections_df"):
            st.session_state.pop(key, None)
        st.session_state.data_uploaded = False
        st.success("Cache cleared. Reloading from Drive…")
        st.rerun()

# Initialize Google Drive service
service = initialize_drive_service()

# Initialize session state containers (no behavior change)
initialize_session_state()

# ---------- Loaders (use Drive helpers; reads are now cached) ----------
def load_data_from_drive():
    # Load Courses Table
    courses_file_id = find_file_in_drive(service, 'courses_table.xlsx', st.secrets["google"]["folder_id"])
    if courses_file_id:
        try:
            courses_content = download_file_from_drive(service, courses_file_id)
            st.session_state.courses_df = pd.read_excel(BytesIO(courses_content))
            st.success('✅ Courses Table loaded from Google Drive')
            log_info("Courses Table loaded from Drive")
        except Exception as e:
            st.error(f'❌ Failed to load Courses Table from Drive: {e}')
            log_error("Failed to load Courses Table", e)

    # Load Progress Report
    progress_file_id = find_file_in_drive(service, 'progress_report.xlsx', st.secrets["google"]["folder_id"])
    if progress_file_id:
        try:
            progress_content = download_file_from_drive(service, progress_file_id)
            st.session_state.progress_df = pd.read_excel(BytesIO(progress_content))
            st.success('✅ Progress Report loaded from Google Drive')
            log_info("Progress Report loaded from Drive")
        except Exception as e:
            st.error(f'❌ Failed to load Progress Report from Drive: {e}')
            log_error("Failed to load Progress Report", e)

    # Load Advising Selections (optional – created if absent)
    advising_file_id = find_file_in_drive(service, 'advising_selections.xlsx', st.secrets["google"]["folder_id"])
    if advising_file_id:
        try:
            advising_content = download_file_from_drive(service, advising_file_id)
            st.session_state.advising_selections_df = pd.read_excel(BytesIO(advising_content))
            st.success('✅ Advising Selections loaded from Google Drive')
            log_info("Advising Selections loaded from Drive")
        except Exception as e:
            st.error(f'❌ Failed to load Advising Selections from Drive: {e}')
            log_error("Failed to load Advising Selections", e)

# Load once on start (cached reads)
if st.session_state.courses_df.empty or st.session_state.progress_df.empty:
    load_data_from_drive()

# ---------- Sidebar upload area (unchanged behavior) ----------
st.sidebar.header('Data')
with st.sidebar.expander("Upload / Replace data", expanded=False):
    upload_data()

# If user uploaded new data, sync back to Drive (unchanged)
def save_data_to_drive():
    try:
        folder_id = st.secrets["google"]["folder_id"]
        if not st.session_state.courses_df.empty:
            buf = BytesIO()
            st.session_state.courses_df.to_excel(buf, index=False)
            buf.seek(0)
            sync_file_with_drive(
                service,
                buf.getvalue(),
                'courses_table.xlsx',
                'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                folder_id,
            )

        if not st.session_state.progress_df.empty:
            buf = BytesIO()
            st.session_state.progress_df.to_excel(buf, index=False)
            buf.seek(0)
            sync_file_with_drive(
                service,
                buf.getvalue(),
                'progress_report.xlsx',
                'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                folder_id,
            )

        if st.session_state.get("advising_selections_df") is not None and not st.session_state.advising_selections_df.empty:
            buf = BytesIO()
            st.session_state.advising_selections_df.to_excel(buf, index=False)
            buf.seek(0)
            sync_file_with_drive(
                service,
                buf.getvalue(),
                'advising_selections.xlsx',
                'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                folder_id,
            )
    except Exception as e:
        st.error(f"❌ Failed saving files to Drive: {e}")
        log_error("Failed saving files to Drive", e)

if st.session_state.data_uploaded:
    save_data_to_drive()
    st.session_state.data_uploaded = False  # Reset the flag

# ---------- Main views (unchanged) ----------
if not st.session_state.progress_df.empty and not st.session_state.courses_df.empty:
    tab1, tab2 = st.tabs(['Student Eligibility View', 'Full Student View'])
    with tab1:
        student_eligibility_view()
    with tab2:
        full_student_view()
else:
    st.info('📝 Please upload both the progress report and courses table to continue.')
