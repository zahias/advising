import streamlit as st
import pandas as pd
from io import BytesIO
from datetime import datetime
from advising_utils import load_progress_excel, load_courses_excel

def _get_drive_module():
    """Lazy loader for google_drive module."""
    import google_drive as gd
    return gd

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
                df = load_courses_excel(courses_file.read())
                st.session_state.courses_df = df
                st.session_state.majors[major]["courses_df"] = df
                st.success(f"✓ Loaded {len(df)} courses")
                st.rerun()
            except Exception as e:
                st.error(f"Error loading file: {e}")
    
    with col2:
        st.markdown("#### Progress Report")
        
        if not progress_df.empty:
            st.success(f"✓ Loaded: {len(progress_df)} students")
        else:
            st.warning("Not loaded")
        
        progress_file = st.file_uploader(
            "Upload progress_report.xlsx",
            type=["xlsx"],
            key="setup_progress_upload",
            help="Excel file with student IDs, names, completed courses, etc."
        )
        
        if progress_file:
            try:
                df = load_progress_excel(progress_file.read())
                st.session_state.progress_df = df
                st.session_state.majors[major]["progress_df"] = df
                st.success(f"✓ Loaded {len(df)} students")
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
                df = load_courses_excel(data)
                st.session_state.courses_df = df
                st.session_state.majors[major]["courses_df"] = df
                st.success("✓ Downloaded courses table")
        
        progress_id = gd.find_file_in_drive(service, "progress_report.xlsx", major_folder_id)
        if progress_id:
            data = gd.download_file_from_drive(service, progress_id)
            if data:
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
        
        courses_df = st.session_state.get("courses_df", pd.DataFrame())
        if not courses_df.empty:
            output = BytesIO()
            courses_df.to_excel(output, index=False)
            output.seek(0)
            gd.upload_file_to_drive(service, "courses_table.xlsx", output.getvalue(), major_folder_id)
            st.success("✓ Uploaded courses table")
        
        progress_df = st.session_state.get("progress_df", pd.DataFrame())
        if not progress_df.empty:
            output = BytesIO()
            progress_df.to_excel(output, index=False)
            output.seek(0)
            gd.upload_file_to_drive(service, "progress_report.xlsx", output.getvalue(), major_folder_id)
            st.success("✓ Uploaded progress report")
        
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
                st.success(f"Switched to: {selected}")
                st.rerun()
    else:
        st.info("No previous periods available")
