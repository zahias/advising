# data_upload.py

import streamlit as st
import pandas as pd
from io import BytesIO
from google_drive import initialize_drive_service, sync_file_with_drive
from utils import log_info, log_error, load_progress_excel

def upload_data():
    """Handle uploading of courses table, progress report, and advising selections."""
    st.sidebar.header("Upload Data")
    service = initialize_drive_service()

    # Upload Courses Table
    courses_file = st.sidebar.file_uploader(
        "Upload Courses Table (courses_table.xlsx)", type=["xlsx"], key="courses_upload"
    )
    if courses_file:
        try:
            st.session_state.courses_df = pd.read_excel(courses_file)
            st.sidebar.success("✅ Courses table loaded.")
            log_info("Courses table uploaded via sidebar.")
            # optional: sync to Drive in the app's folder
            if st.sidebar.checkbox("Sync courses_table.xlsx to Google Drive", value=False):
                courses_file.seek(0)
                sync_file_with_drive(
                    service=service,
                    file_content=courses_file.read(),
                    drive_file_name="courses_table.xlsx",
                    mime_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    parent_folder_id=st.secrets["google"]["folder_id"],
                )
                st.sidebar.success("Synced to Drive.")
        except Exception as e:
            st.session_state.courses_df = pd.DataFrame()
            st.sidebar.error(f"Error loading courses table: {e}")
            log_error("Error loading courses table", e)

    # Upload Progress Report (may contain 'Required Courses' + 'Intensive Courses')
    progress_file = st.sidebar.file_uploader(
        "Upload Progress Report (progress_report.xlsx)", type=["xlsx"], key="progress_upload"
    )
    if progress_file:
        try:
            progress_file.seek(0)
            content = progress_file.read()
            st.session_state.progress_df = load_progress_excel(content)
            st.sidebar.success("✅ Progress report loaded (Required + Intensive merged).")
            log_info("Progress report uploaded and merged via sidebar.")
            if st.sidebar.checkbox("Sync progress_report.xlsx to Google Drive", value=False):
                sync_file_with_drive(
                    service=service,
                    file_content=content,
                    drive_file_name="progress_report.xlsx",
                    mime_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    parent_folder_id=st.secrets["google"]["folder_id"],
                )
                st.sidebar.success("Synced to Drive.")
        except Exception as e:
            st.session_state.progress_df = pd.DataFrame()
            st.sidebar.error(f"Error loading progress report: {e}")
            log_error("Error loading progress report", e)

    # Upload Advising Selections (optional)
    sel_file = st.sidebar.file_uploader(
        "Upload Advising Selections (advising_selections.xlsx)", type=["xlsx"], key="sel_upload"
    )
    if sel_file:
        try:
            df = pd.read_excel(sel_file)
            selections = {}
            for _, r in df.iterrows():
                sid = int(r.get("ID"))
                advised = str(r.get("Advised") or "").split(",") if "Advised" in r else []
                optional = str(r.get("Optional") or "").split(",") if "Optional" in r else []
                note = r.get("Note") or ""
                selections[sid] = {
                    "advised": [c.strip() for c in advised if c.strip()],
                    "optional": [c.strip() for c in optional if c.strip()],
                    "note": note,
                }
            st.session_state.advising_selections = selections
            st.sidebar.success("✅ Advising selections loaded.")
            log_info("Advising selections uploaded via sidebar.")
        except Exception as e:
            st.sidebar.error(f"Error loading advising selections: {e}")
            log_error("Error loading advising selections", e)

    # Sidebar status badges
    st.sidebar.markdown("---")
    st.sidebar.write("**Status**")
    st.sidebar.success("Courses table loaded.") if st.session_state.get("courses_df") is not None and not st.session_state.courses_df.empty else st.sidebar.warning("Courses table not uploaded.")
    st.sidebar.success("Progress report loaded.") if st.session_state.get("progress_df") is not None and not st.session_state.progress_df.empty else st.sidebar.warning("Progress report not uploaded.")
    st.sidebar.success("Advising selections loaded.") if st.session_state.get("advising_selections") else st.sidebar.info("Advising selections optional.")
