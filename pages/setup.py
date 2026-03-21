import hashlib
import streamlit as st
import pandas as pd
from io import BytesIO
from datetime import datetime

def _get_drive_module():
    """Lazy loader for google_drive module."""
    import google_drive as gd
    return gd


def _sync_status_key(major: str, base_name: str) -> str:
    return f"_drive_sync_status_{major}_{base_name}"


def _pending_upload_key(major: str, base_name: str) -> str:
    return f"_pending_upload_{major}_{base_name}"


def _set_pending_upload(major: str, base_name: str, content: bytes, file_hash: str) -> None:
    st.session_state[_pending_upload_key(major, base_name)] = {
        "content": content,
        "hash": file_hash,
        "updated_at": datetime.now().isoformat(),
    }


def _clear_pending_upload(major: str, base_name: str) -> None:
    st.session_state.pop(_pending_upload_key(major, base_name), None)


def _get_pending_upload(major: str, base_name: str):
    return st.session_state.get(_pending_upload_key(major, base_name))


def _set_sync_status(major: str, base_name: str, *, synced: bool, file_hash: str = "", message: str = "") -> None:
    st.session_state[_sync_status_key(major, base_name)] = {
        "synced": synced,
        "hash": file_hash,
        "message": message,
        "updated_at": datetime.now().isoformat(),
    }


def _get_sync_status(major: str, base_name: str):
    return st.session_state.get(_sync_status_key(major, base_name), {})

def _sync_to_drive(major: str, base_name: str, content: bytes) -> bool:
    """
    Sync a file to the major-specific Drive folder.
    Returns True on success, False on failure.
    Stores a message in session state so the result survives st.rerun().
    """
    import os
    from advising_utils import log_error, log_info
    try:
        gd = _get_drive_module()
        service = gd.initialize_drive_service()
        root_folder_id = ""
        try:
            if "google" in st.secrets:
                root_folder_id = st.secrets["google"].get("folder_id", "")
        except Exception:
            pass
        if not root_folder_id:
            root_folder_id = os.getenv("GOOGLE_FOLDER_ID", "")
        if not root_folder_id:
            log_error("Drive sync skipped: folder ID not configured", Exception("no folder_id"))
            st.session_state["_drive_sync_msg"] = ("warning", "Drive sync skipped: folder ID not configured")
            return False
        major_folder_id = gd.get_major_folder_id(service, major, root_folder_id)
        mime = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        gd.sync_file_with_drive(
            service=service,
            file_content=content,
            drive_file_name=f"{base_name}.xlsx",
            mime_type=mime,
            parent_folder_id=major_folder_id,
        )
        log_info(f"Synced {base_name}.xlsx to Drive for major {major}")
        st.session_state["_drive_sync_msg"] = ("success", f"☁️ Synced {base_name}.xlsx to Drive")
        return True
    except Exception as e:
        log_error(f"Drive sync failed for {base_name}", e)
        st.session_state["_drive_sync_msg"] = ("error", f"Drive sync failed: {e}")
        return False

def render_setup():
    """Render the unified Setup page with data upload and period management."""
    
    st.markdown("## Setup")
    
    setup_tab1, setup_tab2 = st.tabs(["Data Files", "Period Management"])
    
    with setup_tab1:
        _render_data_upload()
    
    with setup_tab2:
        _render_period_management()

def _render_data_upload():
    """Render data upload section."""

    # Show Drive sync result from previous upload (survives st.rerun)
    if "_drive_sync_msg" in st.session_state:
        level, msg = st.session_state.pop("_drive_sync_msg")
        if level == "success":
            st.success(msg)
        elif level == "warning":
            st.warning(msg)
        else:
            st.error(msg)

    st.markdown("### Upload Data Files")

    major = st.session_state.get("current_major", "")
    
    courses_df = st.session_state.get("courses_df", pd.DataFrame())
    progress_df = st.session_state.get("progress_df", pd.DataFrame())
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### Courses Table")
        
        if not courses_df.empty:
            st.success(f"✓ Loaded: {len(courses_df)} courses")
        else:
            st.warning("Not loaded")
        
        courses_file = st.file_uploader(
            "Upload courses_table.xlsx",
            type=["xlsx"],
            key="setup_courses_upload",
            help="Excel file with course codes, titles, credits, prerequisites, etc."
        )
        
        if courses_file:
            try:
                courses_file.seek(0)
                raw = courses_file.read()
                file_hash = hashlib.md5(raw).hexdigest()
                processed_key = f"_courses_synced_{major}_{file_hash}"
                if processed_key not in st.session_state:
                    df = pd.read_excel(BytesIO(raw))
                    st.session_state.courses_df = df
                    st.session_state.majors[major]["courses_df"] = df
                    _set_pending_upload(major, "courses_table", raw, file_hash)
                    st.info(f"Loaded {len(df)} courses. Syncing to Drive...")
                    sync_ok = _sync_to_drive(major, "courses_table", raw)
                    if sync_ok:
                        _set_sync_status(
                            major,
                            "courses_table",
                            synced=True,
                            file_hash=file_hash,
                            message="Synced to Google Drive",
                        )
                        _clear_pending_upload(major, "courses_table")
                        st.session_state[processed_key] = True
                    else:
                        _set_sync_status(
                            major,
                            "courses_table",
                            synced=False,
                            file_hash=file_hash,
                            message="Local upload succeeded, but Google Drive still has the previous file.",
                        )
                    st.rerun()
            except Exception as e:
                st.error(f"Error loading file: {e}")
    
    with col2:
        st.markdown("#### Progress Report")
        
        if not progress_df.empty:
            st.success(f"✓ Loaded: {len(progress_df)} students")
        else:
            st.warning("Not loaded")

        progress_sync = _get_sync_status(major, "progress_report")
        if progress_sync and not progress_sync.get("synced", True):
            st.warning(progress_sync.get("message", "Progress report has local changes that are not synced to Google Drive."))
            if st.button("Retry Progress Report Sync", key="retry_progress_sync"):
                pending = _get_pending_upload(major, "progress_report")
                if not pending:
                    st.error("No pending progress report upload is available to retry.")
                else:
                    sync_ok = _sync_to_drive(major, "progress_report", pending["content"])
                    if sync_ok:
                        _set_sync_status(
                            major,
                            "progress_report",
                            synced=True,
                            file_hash=pending.get("hash", ""),
                            message="Synced to Google Drive",
                        )
                        _clear_pending_upload(major, "progress_report")
                        st.session_state[f"_progress_synced_{major}_{pending.get('hash', '')}"] = True
                    st.rerun()
        
        progress_file = st.file_uploader(
            "Upload progress_report.xlsx",
            type=["xlsx"],
            key="setup_progress_upload",
            help="Excel file with student IDs, names, completed courses, etc."
        )
        
        if progress_file:
            try:
                from advising_utils import load_progress_excel
                progress_file.seek(0)
                content = progress_file.read()
                file_hash = hashlib.md5(content).hexdigest()
                processed_key = f"_progress_synced_{major}_{file_hash}"
                if processed_key not in st.session_state:
                    df = load_progress_excel(content)
                    st.session_state.progress_df = df
                    st.session_state.majors[major]["progress_df"] = df
                    _set_pending_upload(major, "progress_report", content, file_hash)
                    st.info(f"Loaded {len(df)} students. Syncing to Drive...")
                    sync_ok = _sync_to_drive(major, "progress_report", content)
                    if sync_ok:
                        _set_sync_status(
                            major,
                            "progress_report",
                            synced=True,
                            file_hash=file_hash,
                            message="Synced to Google Drive",
                        )
                        _clear_pending_upload(major, "progress_report")
                        st.session_state[processed_key] = True
                    else:
                        _set_sync_status(
                            major,
                            "progress_report",
                            synced=False,
                            file_hash=file_hash,
                            message="New progress report loaded locally, but Drive sync failed. Refreshing the app will reload the older Drive copy until sync succeeds.",
                        )
                    st.rerun()
            except Exception as e:
                st.error(f"Error loading file: {e}")
    
    st.markdown("---")
    
    st.markdown("#### Email Roster (Optional)")
    
    email_file = st.file_uploader(
        "Upload email roster (Excel with ID and Email columns)",
        type=["xlsx"],
        key="setup_email_upload",
        help="Optional: Excel file with student IDs and email addresses for sending advising sheets"
    )
    
    if email_file:
        try:
            email_df = pd.read_excel(email_file)
            if "ID" in email_df.columns and "Email" in email_df.columns:
                roster_key = f"email_roster_{major}"
                st.session_state[roster_key] = email_df
                st.success(f"✓ Loaded {len(email_df)} email addresses")
            else:
                st.error("Email roster must have 'ID' and 'Email' columns")
        except Exception as e:
            st.error(f"Error loading email roster: {e}")
    
    st.markdown("---")
    
    st.markdown("#### Sync with Google Drive")
    
    col_sync1, col_sync2 = st.columns(2)
    
    with col_sync1:
        if st.button("Download from Drive"):
            _download_from_drive()
    
    with col_sync2:
        if st.button("Upload to Drive"):
            _upload_to_drive()

def _download_from_drive():
    """Download data files from Google Drive."""
    major = st.session_state.get("current_major", "")
    
    try:
        gd = _get_drive_module()
        service = gd.initialize_drive_service()
        
        import os
        root_folder_id = ""
        try:
            if "google" in st.secrets:
                root_folder_id = st.secrets["google"].get("folder_id", "")
        except:
            pass
        if not root_folder_id:
            root_folder_id = os.getenv("GOOGLE_FOLDER_ID", "")
        
        if not root_folder_id:
            st.error("Google Drive folder ID not configured")
            return
        
        major_folder_id = gd.get_major_folder_id(service, major, root_folder_id)
        
        courses_id = gd.find_file_in_drive(service, "courses_table.xlsx", major_folder_id)
        if courses_id:
            data = gd.download_file_from_drive(service, courses_id)
            if data:
                df = pd.read_excel(BytesIO(data))
                st.session_state.courses_df = df
                st.session_state.majors[major]["courses_df"] = df
                st.success("✓ Downloaded courses table")
        
        progress_id = gd.find_file_in_drive(service, "progress_report.xlsx", major_folder_id)
        if progress_id:
            data = gd.download_file_from_drive(service, progress_id)
            if data:
                from advising_utils import load_progress_excel
                df = load_progress_excel(data)
                st.session_state.progress_df = df
                st.session_state.majors[major]["progress_df"] = df
                st.success("✓ Downloaded progress report")
        
        st.rerun()
    except Exception as e:
        st.error(f"Error downloading from Drive: {e}")

def _upload_to_drive():
    """Upload data files to Google Drive."""
    major = st.session_state.get("current_major", "")
    
    try:
        gd = _get_drive_module()
        service = gd.initialize_drive_service()
        
        import os
        root_folder_id = ""
        try:
            if "google" in st.secrets:
                root_folder_id = st.secrets["google"].get("folder_id", "")
        except:
            pass
        if not root_folder_id:
            root_folder_id = os.getenv("GOOGLE_FOLDER_ID", "")
        
        if not root_folder_id:
            st.error("Google Drive folder ID not configured")
            return
        
        major_folder_id = gd.get_major_folder_id(service, major, root_folder_id)
        mime = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        uploaded_any = False
        
        courses_df = st.session_state.get("courses_df", pd.DataFrame())
        if not courses_df.empty:
            pending_courses = _get_pending_upload(major, "courses_table")
            if pending_courses:
                content = pending_courses["content"]
                file_hash = pending_courses.get("hash", "")
            else:
                output = BytesIO()
                courses_df.to_excel(output, index=False)
                content = output.getvalue()
                file_hash = hashlib.md5(content).hexdigest()
            gd.sync_file_with_drive(
                service=service,
                file_content=content,
                drive_file_name="courses_table.xlsx",
                mime_type=mime,
                parent_folder_id=major_folder_id,
            )
            _set_sync_status(major, "courses_table", synced=True, file_hash=file_hash, message="Synced to Google Drive")
            _clear_pending_upload(major, "courses_table")
            st.session_state[f"_courses_synced_{major}_{file_hash}"] = True
            st.success("✓ Uploaded courses table")
            uploaded_any = True
        
        progress_df = st.session_state.get("progress_df", pd.DataFrame())
        if not progress_df.empty:
            pending_progress = _get_pending_upload(major, "progress_report")
            if pending_progress:
                content = pending_progress["content"]
                file_hash = pending_progress.get("hash", "")
            else:
                output = BytesIO()
                progress_df.to_excel(output, index=False)
                content = output.getvalue()
                file_hash = hashlib.md5(content).hexdigest()
            gd.sync_file_with_drive(
                service=service,
                file_content=content,
                drive_file_name="progress_report.xlsx",
                mime_type=mime,
                parent_folder_id=major_folder_id,
            )
            _set_sync_status(major, "progress_report", synced=True, file_hash=file_hash, message="Synced to Google Drive")
            _clear_pending_upload(major, "progress_report")
            st.session_state[f"_progress_synced_{major}_{file_hash}"] = True
            st.success("✓ Uploaded progress report")
            uploaded_any = True
        
        if not uploaded_any:
            st.warning("No data loaded to upload")
        
    except Exception as e:
        st.error(f"Error uploading to Drive: {e}")

def _render_period_management():
    """Render period management section."""
    from advising_period import get_current_period, start_new_period, get_all_periods, set_current_period
    from datetime import datetime
    
    def _format_academic_year(year):
        """Convert year to academic year format. E.g., 2024 -> 2024/2025"""
        try:
            year_int = int(year)
            return f"{year_int}/{year_int + 1}"
        except (ValueError, TypeError):
            return str(year)
    
    st.markdown("### Current Period")
    
    current_period = get_current_period()
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Semester", current_period.get("semester", "Not set"))
    with col2:
        year = current_period.get("year", "")
        academic_year = _format_academic_year(year) if year else "—"
        st.metric("Academic Year", academic_year)
    with col3:
        created = current_period.get("created_at", "")
        if created:
            created_date = created.split("T")[0] if "T" in created else created
            st.metric("Created", created_date)
        else:
            st.metric("Created", "—")
    with col4:
        st.metric("Advisor", current_period.get("advisor_name", "Not set"))
    
    st.markdown("---")
    
    st.markdown("### Start New Period")
    
    def _default_period_for_today():
        today = datetime.now()
        month = today.month
        year = today.year
        if month == 1:
            return "Fall", year - 1
        if 2 <= month <= 6:
            return "Spring", year
        if 7 <= month <= 9:
            return "Summer", year
        return "Fall", year
    
    with st.form("new_period_form"):
        default_semester, default_year = _default_period_for_today()
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            semester = st.selectbox("Semester", ["Fall", "Spring", "Summer"], 
                                   index=["Fall", "Spring", "Summer"].index(default_semester))
        with col2:
            year = st.number_input("Year", min_value=2020, max_value=2099, value=default_year)
        with col3:
            advisor = st.text_input("Advisor Name")
        
        # Show academic year preview
        academic_year_preview = _format_academic_year(year)
        st.caption(f"📅 Academic Year: {academic_year_preview} | Created: {datetime.now().strftime('%Y-%m-%d')}")
        
        if st.form_submit_button("Create New Period", type="primary"):
            if not advisor:
                st.error("Please enter advisor name")
            else:
                major = st.session_state.get("current_major", "")
                st.session_state.advising_selections = {}
                st.session_state.majors[major]["advising_selections"] = {}
                
                new_period, drive_saved = start_new_period(semester, int(year), advisor)
                
                if drive_saved:
                    st.success(f"✓ Created period: {semester} {academic_year_preview}")
                else:
                    st.warning(f"Created period locally (Drive sync failed)")
                st.rerun()
    
    st.markdown("---")
    
    st.markdown("### Switch Period")
    
    all_periods = get_all_periods()
    real_periods = [p for p in all_periods if p.get("advisor_name", "").strip()]
    
    if real_periods:
        period_options = []
        period_map = {}
        for p in real_periods:
            year = p.get('year', '')
            academic_year = _format_academic_year(year) if year else year
            label = f"{p.get('semester', '')} {academic_year} — {p.get('advisor_name', '')}"
            period_options.append(label)
            period_map[label] = p
        
        selected = st.selectbox("Select Period", period_options)
        
        if st.button("Switch to This Period"):
            selected_period = period_map[selected]
            if selected_period.get("period_id") != current_period.get("period_id"):
                set_current_period(selected_period)
                major = st.session_state.get("current_major", "")
                st.session_state.advising_selections = {}
                st.session_state.majors[major]["advising_selections"] = {}
                bypasses_key = f"bypasses_{major}"
                if bypasses_key in st.session_state:
                    st.session_state[bypasses_key] = {}
                # Delete local selections cache so stale data isn't reloaded
                try:
                    from advising_history import _get_local_selections_path
                    import os
                    sel_file = _get_local_selections_path(major)
                    if os.path.exists(sel_file):
                        os.remove(sel_file)
                except Exception:
                    pass
                # Clear session-loaded flags so new period loads fresh
                for key in list(st.session_state.keys()):
                    if isinstance(key, str) and (
                        key.startswith("_fsv_sessions_loaded_") or
                        key.startswith("_sessions_loaded_") or
                        key.startswith("_fsv_cache_")
                    ):
                        del st.session_state[key]
                st.success(f"Switched to: {selected}")
                st.rerun()
    else:
        st.info("No previous periods available")
