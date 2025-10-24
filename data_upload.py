# data_upload.py
# Auto-syncs uploads to Drive with per-major filenames (replaces existing files),
# and also writes a timestamped version for provenance/rollback.

from __future__ import annotations

import streamlit as st
import pandas as pd
from datetime import datetime

from google_drive import initialize_drive_service, sync_file_with_drive, GoogleAuthError
from utils import log_info, log_error, load_progress_excel


def _drive_service_or_none():
    try:
        return initialize_drive_service()
    except GoogleAuthError as e:
        # Clear message once in the sidebar; app still works locally
        st.sidebar.warning(
            "Google Drive sync unavailable: " + str(e) +
            "\n\nFix: Re-authorize and update google.refresh_token in your Streamlit Secrets."
        )
        log_error("Drive init failed", e)
        return None


def _timestamp() -> str:
    # e.g., 20251020-1435
    return datetime.now().strftime("%Y%m%d-%H%M")


def _sync_both_names(
    *,
    service,
    folder_id: str,
    major: str,
    base_name: str,          # "courses_table" OR "progress_report"
    content: bytes,
    mime: str = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
):
    """
    Write the 'latest alias' and the timestamped version.
      - {MAJOR}_{base_name}.xlsx
      - {MAJOR}_{base_name}_{YYYYMMDD-HHMM}.xlsx
    """
    if not service or not folder_id:
        return

    latest = f"{major}_{base_name}.xlsx"
    versioned = f"{major}_{base_name}_{_timestamp()}.xlsx"

    # 1) Replace-or-create the 'latest' alias
    sync_file_with_drive(
        service=service,
        file_content=content,
        drive_file_name=latest,
        mime_type=mime,
        parent_folder_id=folder_id,
    )

    # 2) Add a versioned snapshot (always create new)
    sync_file_with_drive(
        service=service,
        file_content=content,
        drive_file_name=versioned,
        mime_type=mime,
        parent_folder_id=folder_id,
    )


def upload_data():
    """
    Handle uploading of courses table, progress report, and advising selections
    for the CURRENT major. Automatically syncs to Drive (replace alias + add version).
    """
    st.sidebar.header("Upload Data")

    current_major = st.session_state.get("current_major")
    if not current_major:
        st.sidebar.warning("Select a major to upload files.")
        return

    # Try Drive (optional; local still works)
    import os
    service = _drive_service_or_none()
    try:
        folder_id = st.secrets.get("google", {}).get("folder_id", "") or os.getenv("GOOGLE_FOLDER_ID", "")
    except Exception:
        folder_id = os.getenv("GOOGLE_FOLDER_ID", "")

    # ---------- Upload Courses Table (per-major) ----------
    courses_file = st.sidebar.file_uploader(
        f"[{current_major}] Upload Courses Table ({current_major}_courses_table.xlsx)",
        type=["xlsx"],
        key=f"courses_upload_{current_major}",
    )
    if courses_file:
        try:
            courses_file.seek(0)
            # Read for the app (DataFrame)
            df = pd.read_excel(courses_file)
            st.session_state.courses_df = df
            st.session_state.majors[current_major]["courses_df"] = df
            st.sidebar.success("✅ Courses table loaded.")
            log_info(f"Courses table uploaded via sidebar ({current_major}).")

            # Auto-sync to Drive (alias + versioned)
            if service and folder_id:
                courses_file.seek(0)
                raw = courses_file.read()
                _sync_both_names(
                    service=service,
                    folder_id=folder_id,
                    major=current_major,
                    base_name="courses_table",
                    content=raw,
                )
                st.sidebar.info("☁️ Synced to Google Drive (latest + versioned).")
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

            # Auto-sync to Drive (alias + versioned)
            if service and folder_id:
                _sync_both_names(
                    service=service,
                    folder_id=folder_id,
                    major=current_major,
                    base_name="progress_report",
                    content=content,
                )
                st.sidebar.info("☁️ Synced to Google Drive (latest + versioned).")
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

    # ---------- Status ----------
    st.sidebar.markdown("---")
    st.sidebar.write(f"**Status for {current_major}**")
    st.sidebar.success("Courses table loaded.") if not st.session_state.courses_df.empty else st.sidebar.warning("Courses table not uploaded.")
    st.sidebar.success("Progress report loaded.") if not st.session_state.progress_df.empty else st.sidebar.warning("Progress report not uploaded.")
    st.sidebar.success("Advising selections loaded.") if st.session_state.get("advising_selections") else st.sidebar.info("Advising selections optional.")
