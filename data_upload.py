# data_upload.py
# Auto-syncs uploads to Drive with per-major filenames (replaces existing files),
# and also writes a timestamped version for provenance/rollback.

from __future__ import annotations

import streamlit as st
import pandas as pd
from datetime import datetime

from google_drive import initialize_drive_service, sync_file_with_drive, GoogleAuthError, get_major_folder_id
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


def _get_root_folder_id() -> str:
    """Get root folder ID from secrets or env."""
    import os
    folder_id = ""
    try:
        if "google" in st.secrets:
            folder_id = st.secrets["google"].get("folder_id", "")
    except:
        pass
    
    if not folder_id:
        folder_id = os.getenv("GOOGLE_FOLDER_ID", "")
    
    return folder_id


def _sync_to_major_folder(
    *,
    service,
    major: str,
    base_name: str,          # "courses_table" OR "progress_report"
    content: bytes,
    mime: str = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
):
    """
    Sync file to major-specific folder in Drive, replacing if exists.
    File will be named: {base_name}.xlsx (e.g., courses_table.xlsx)
    Stored in folder: {ROOT_FOLDER}/{MAJOR}/ (e.g., {ROOT}/PBHL/)
    """
    if not service:
        return

    root_folder_id = _get_root_folder_id()
    if not root_folder_id:
        return
    
    # Get or create major-specific folder
    major_folder_id = get_major_folder_id(service, major, root_folder_id)
    
    # Sync file (replaces if exists)
    filename = f"{base_name}.xlsx"
    sync_file_with_drive(
        service=service,
        file_content=content,
        drive_file_name=filename,
        mime_type=mime,
        parent_folder_id=major_folder_id,
    )


def upload_data():
    """
    Handle uploading of courses table, progress report, and advising selections
    for the CURRENT major. Automatically syncs to major-specific folder in Drive.
    """
    st.sidebar.header("Upload Data")

    current_major = st.session_state.get("current_major")
    if not current_major:
        st.sidebar.warning("Select a major to upload files.")
        return

    # Try Drive (optional; local still works)
    service = _drive_service_or_none()

    # ---------- Upload Courses Table (per-major) ----------
    courses_file = st.sidebar.file_uploader(
        f"[{current_major}] Upload Courses Table",
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

            # Auto-sync to Drive in major-specific folder
            if service:
                courses_file.seek(0)
                raw = courses_file.read()
                _sync_to_major_folder(
                    service=service,
                    major=current_major,
                    base_name="courses_table",
                    content=raw,
                )
                st.sidebar.info(f"☁️ Synced to Drive: {current_major}/courses_table.xlsx")
        except Exception as e:
            st.session_state.courses_df = pd.DataFrame()
            st.session_state.majors[current_major]["courses_df"] = pd.DataFrame()
            st.sidebar.error(f"Error loading courses table: {e}")
            log_error("Error loading courses table", e)

    # ---------- Upload Progress Report (per-major; merges Required + Intensive) ----------
    progress_file = st.sidebar.file_uploader(
        f"[{current_major}] Upload Progress Report",
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

            # Auto-sync to Drive in major-specific folder
            if service:
                _sync_to_major_folder(
                    service=service,
                    major=current_major,
                    base_name="progress_report",
                    content=content,
                )
                st.sidebar.info(f"☁️ Synced to Drive: {current_major}/progress_report.xlsx")
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

    # ---------- Upload Email Roster (per-major) ----------
    st.sidebar.markdown("---")
    st.sidebar.subheader("📧 Email Roster")
    
    email_file = st.sidebar.file_uploader(
        f"[{current_major}] Upload Email Roster (Excel/CSV with ID and Email columns)",
        type=["xlsx", "csv"],
        key=f"email_upload_{current_major}",
        help="Upload a file with student IDs and email addresses. Expected columns: 'ID' and 'Email'"
    )
    if email_file:
        from email_manager import upload_email_roster_from_file
        count_added, errors = upload_email_roster_from_file(email_file)
        
        if count_added > 0:
            st.sidebar.success(f"✅ Added/updated {count_added} email(s) for {current_major}")
            log_info(f"Email roster uploaded: {count_added} emails for {current_major}")
        
        if errors:
            with st.sidebar.expander("⚠️ See errors", expanded=False):
                for err in errors:
                    st.write(f"• {err}")
    
    # Show email roster status
    from email_manager import load_email_roster
    roster = load_email_roster()
    if roster:
        st.sidebar.info(f"📧 {len(roster)} student email(s) on file for {current_major}")
    else:
        st.sidebar.warning("No email roster uploaded for {current_major}")
    
    # ---------- Status ----------
    st.sidebar.markdown("---")
    st.sidebar.write(f"**Status for {current_major}**")
    st.sidebar.success("Courses table loaded.") if not st.session_state.courses_df.empty else st.sidebar.warning("Courses table not uploaded.")
    st.sidebar.success("Progress report loaded.") if not st.session_state.progress_df.empty else st.sidebar.warning("Progress report not uploaded.")
    st.sidebar.success("Advising selections loaded.") if st.session_state.get("advising_selections") else st.sidebar.info("Advising selections optional.")
    
    # ---------- Email Settings ----------
    st.sidebar.markdown("---")
    with st.sidebar.expander("⚙️ Email Settings", expanded=False):
        from email_manager import get_email_credentials
        
        email_addr, email_pass = get_email_credentials()
        
        if email_addr and email_pass:
            st.success(f"✅ Email configured: {email_addr}")
            st.info("Email credentials are stored in Replit/Streamlit secrets.")
        else:
            st.warning("⚠️ Email not configured")
            st.write("To enable email sending, add these secrets:")
            st.code("""
[email]
address = "your-email@outlook.com"
password = "your-app-password"
            """, language="toml")
            st.caption("**For Outlook/Office 365:**")
            st.caption("• Use your full university email address")
            st.caption("• Use app password (not regular password)")
            st.caption("• [Generate app password](https://support.microsoft.com/en-us/account-billing/using-app-passwords-with-apps-that-don-t-support-two-step-verification-5896ed9b-4263-e681-128a-a6f2979a7944)")
            st.caption("**On Streamlit Cloud:** Add to Secrets in Settings")
            st.caption("**On Replit:** Add to Secrets in Tools sidebar")
