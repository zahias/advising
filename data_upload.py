# data_upload.py

import streamlit as st
import pandas as pd

from google_drive import initialize_drive_service, sync_file_with_drive
from utils import log_info, log_error, load_progress_excel

def upload_data():
    """
    Handle uploading of courses table, progress report, and advising selections
    for the CURRENT major. Syncs to Drive using major-specific filenames.
    """
    st.sidebar.header("Upload Data")

    current_major = st.session_state.get("current_major")
    if not current_major:
        st.sidebar.warning("Select a major to upload files.")
        return

    # Drive optional
    service = None
    try:
        service = initialize_drive_service()
    except Exception as e:
        st.sidebar.info("Drive sync disabled. Local uploads still work.")
        log_error("initialize_drive_service failed in upload_data", e)

    # ---------- Upload Courses Table (per-major) ----------
    courses_file = st.sidebar.file_uploader(
        f"[{current_major}] Upload Courses Table ({current_major}_courses_table.xlsx)",
        type=["xlsx"],
        key=f"courses_upload_{current_major}",
    )
    if courses_file:
        try:
            courses_file.seek(0)
            df = pd.read_excel(courses_file)
            st.session_state.courses_df = df
            # write back to bucket for current major
            st.session_state.majors[current_major]["courses_df"] = df
            st.sidebar.success("✅ Courses table loaded.")
            log_info(f"Courses table uploaded via sidebar ({current_major}).")

            # Optional Drive sync with major-specific name
            if service and st.sidebar.checkbox(
                f"Sync to Drive as {current_major}_courses_table.xlsx",
                value=False,
                key=f"sync_courses_{current_major}",
            ):
                courses_file.seek(0)
                sync_file_with_drive(
                    service=service,
                    file_content=courses_file.read(),
                    drive_file_name=f"{current_major}_courses_table.xlsx",
                    mime_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    parent_folder_id=st.secrets["google"]["folder_id"],
                )
                st.sidebar.success("Synced to Drive.")
        except Exception as e:
            st.session_state.courses_df = pd.DataFrame()
            st.session_state.majors[current_major]["courses_df"] = pd.DataFrame()
            st.sidebar.error(f"Error loading courses table: {e}")
            log_error("Error loading courses table", e)

    # ---------- Upload Progress Report (per-major; merges Required + Intensive) ----------
    progress_file = st.sidebar.file_uploader(
        f"[{current_major}] Upload Progress Report ({current_major}_progress_report.xlsx)",
        type=["xlsx"],
        key=f"progress_upload_{current_major}",
    )
    if progress_file:
        try:
            progress_file.seek(0)
            content = progress_file.read()
            df = load_progress_excel(content)
            st.session_state.progress_df = df
            st.session_state.majors[current_major]["progress_df"] = df
            st.sidebar.success("✅ Progress report loaded (Required + Intensive merged).")
            log_info(f"Progress report uploaded and merged via sidebar ({current_major}).")

            # Optional Drive sync with major-specific name
            if service and st.sidebar.checkbox(
                f"Sync to Drive as {current_major}_progress_report.xlsx",
                value=False,
                key=f"sync_progress_{current_major}",
            ):
                sync_file_with_drive(
                    service=service,
                    file_content=content,
                    drive_file_name=f"{current_major}_progress_report.xlsx",
                    mime_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    parent_folder_id=st.secrets["google"]["folder_id"],
                )
                st.sidebar.success("Synced to Drive.")
        except Exception as e:
            st.session_state.progress_df = pd.DataFrame()
            st.session_state.majors[current_major]["progress_df"] = pd.DataFrame()
            st.sidebar.error(f"Error loading progress report: {e}")
            log_error("Error loading progress report", e)

    # ---------- Upload Advising Selections (optional, per-major) ----------
    sel_file = st.sidebar.file_uploader(
        f"[{current_major}] Upload Advising Selections (CSV/XLSX; columns: ID, Advised, Optional, Note)",
        type=["xlsx", "csv"],
        key=f"sel_upload_{current_major}",
    )
    if sel_file:
        try:
            if sel_file.name.lower().endswith(".csv"):
                df = pd.read_csv(sel_file)
            else:
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
            st.session_state.majors[current_major]["advising_selections"] = selections
            st.sidebar.success("✅ Advising selections loaded.")
            log_info(f"Advising selections uploaded via sidebar ({current_major}).")
        except Exception as e:
            st.sidebar.error(f"Error loading advising selections: {e}")
            log_error("Error loading advising selections", e)

    # ---------- Sidebar status badges ----------
    st.sidebar.markdown("---")
    st.sidebar.write(f"**Status for {current_major}**")
    st.sidebar.success("Courses table loaded.") if not st.session_state.courses_df.empty else st.sidebar.warning("Courses table not uploaded.")
    st.sidebar.success("Progress report loaded.") if not st.session_state.progress_df.empty else st.sidebar.warning("Progress report not uploaded.")
    st.sidebar.success("Advising selections loaded.") if st.session_state.get("advising_selections") else st.sidebar.info("Advising selections optional.")
