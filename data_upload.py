# data_upload.py

import pandas as pd
import streamlit as st
from io import BytesIO

from google_drive import initialize_drive_service
from utils import load_progress_excel

def upload_data():
    """Sidebar uploads for courses, progress, advising selections."""
    st.sidebar.header("Upload Data")
    initialize_drive_service()  # ensures secrets are valid

    # Courses
    courses_file = st.sidebar.file_uploader(
        "Upload Courses Table (courses_table.xlsx)", type=["xlsx"], key="courses_upload"
    )
    if courses_file:
        try:
            st.session_state.courses_df = pd.read_excel(courses_file)
            st.session_state.data_uploaded = True
            st.sidebar.success("Courses table uploaded.")
        except Exception as e:
            st.sidebar.error(f"Error uploading courses table: {e}")

    # Progress (supports 2-sheet file)
    progress_file = st.sidebar.file_uploader(
        "Upload Progress Report (progress_report.xlsx)", type=["xlsx"], key="progress_upload"
    )
    if progress_file:
        try:
            content = progress_file.read()
            st.session_state.progress_df = load_progress_excel(content)
            st.session_state.data_uploaded = True
            st.sidebar.success("Progress report uploaded.")
        except Exception as e:
            st.sidebar.error(f"Error uploading progress report: {e}")

    # Advising selections
    advising_file = st.sidebar.file_uploader(
        "Upload Advising Selections (advising_selections.xlsx)", type=["xlsx"], key="advising_upload"
    )
    if advising_file:
        try:
            df = pd.read_excel(advising_file)
            sel = {}
            for _, r in df.iterrows():
                sel[str(r["ID"])] = {
                    "advised": [c.strip() for c in str(r.get("Advised", "")).split(",") if c and c.strip()],
                    "optional": [c.strip() for c in str(r.get("Optional", "")).split(",") if c and c.strip()],
                    "note": r.get("Note", "") if pd.notna(r.get("Note", "")) else "",
                }
            st.session_state.advising_selections = sel
            st.session_state.data_uploaded = True
            st.sidebar.success("Advising selections uploaded.")
        except Exception as e:
            st.sidebar.error(f"Error uploading advising selections: {e}")

    # Status pills
    st.sidebar.success("Courses table is loaded.") if (
        "courses_df" in st.session_state and not st.session_state.courses_df.empty
    ) else st.sidebar.warning("Courses table not uploaded.")

    st.sidebar.success("Progress report is loaded.") if (
        "progress_df" in st.session_state and not st.session_state.progress_df.empty
    ) else st.sidebar.warning("Progress report not uploaded.")

    st.sidebar.success("Advising selections are loaded.") if (
        "advising_selections" in st.session_state and st.session_state.advising_selections
    ) else st.sidebar.warning("Advising selections not uploaded.")
