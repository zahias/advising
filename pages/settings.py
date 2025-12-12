import streamlit as st
import pandas as pd

def _get_drive_module():
    """Lazy loader for google_drive module."""
    import google_drive as gd
    return gd

def render_settings():
    """Render the Settings page with session management, exclusions, and sync."""
    
    st.markdown("## Settings")
    
    tabs = st.tabs(["Sessions", "Exclusions", "Sync"])
    
    with tabs[0]:
        _render_session_management()
    
    with tabs[1]:
        _render_exclusions()
    
    with tabs[2]:
        _render_sync_settings()

def _render_session_management():
    """Render session management section."""
    from advising_period import get_current_period
    from advising_history import _load_session_and_apply
    
    st.markdown("### Session Management")
    
    major = st.session_state.get("current_major", "")
    current_period = get_current_period()
    
    st.markdown(f"**Current Period:** {current_period.get('semester', '')} {current_period.get('year', '')} — {current_period.get('advisor_name', '')}")
    
    st.markdown("---")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### Clear Sessions")
        
        if st.button("Clear All Selections", type="secondary"):
            st.session_state.advising_selections = {}
            st.session_state.majors[major]["advising_selections"] = {}
            
            for key in list(st.session_state.keys()):
                if isinstance(key, str) and key.startswith("_autoloaded_"):
                    del st.session_state[key]
            
            if "current_student_id" in st.session_state:
                del st.session_state["current_student_id"]
            if "workspace_selected_student" in st.session_state:
                del st.session_state["workspace_selected_student"]
            
            st.success("Cleared all selections")
            st.rerun()
        
        st.caption("Clears current advising selections. Does not affect saved sessions.")
    
    with col2:
        st.markdown("#### Restore Sessions")
        
        if st.button("Restore All Sessions", type="primary"):
            progress_df = st.session_state.get("progress_df", pd.DataFrame())
            
            if not progress_df.empty and "ID" in progress_df.columns:
                student_ids = progress_df["ID"].unique()
                loaded_count = 0
                
                for sid in student_ids:
                    if f"_autoloaded_{sid}" in st.session_state:
                        del st.session_state[f"_autoloaded_{sid}"]
                    if _load_session_and_apply(sid):
                        loaded_count += 1
                
                st.session_state.majors[major]["advising_selections"] = st.session_state.advising_selections.copy()
                st.success(f"Restored sessions for {loaded_count} students")
                st.rerun()
            else:
                st.warning("No students found. Upload progress report first.")
        
        st.caption("Loads the most recent session for each student.")
    
    st.markdown("---")
    
    st.markdown("#### Bulk Restore")
    
    with st.expander("Select Students to Restore", expanded=False):
        try:
            import advising_history as ah
            if hasattr(ah, "bulk_restore_panel"):
                ah.bulk_restore_panel()
            else:
                st.info("Bulk restore not available")
        except Exception as e:
            st.error(f"Error: {e}")

def _render_exclusions():
    """Render course exclusions management."""
    
    st.markdown("### Course Exclusions")
    st.caption("Hide specific courses from individual students' eligibility views")
    
    progress_df = st.session_state.get("progress_df", pd.DataFrame())
    courses_df = st.session_state.get("courses_df", pd.DataFrame())
    major = st.session_state.get("current_major", "")
    
    if progress_df.empty or courses_df.empty:
        st.info("Upload data files to manage exclusions.")
        return
    
    exclusions_key = f"course_exclusions_{major}"
    if exclusions_key not in st.session_state:
        st.session_state[exclusions_key] = {}
    
    exclusions = st.session_state[exclusions_key]
    
    student_options = [f"{row['NAME']} ({row['ID']})" for _, row in progress_df.iterrows()]
    course_options = courses_df["Course Code"].tolist()
    
    with st.form("add_exclusion"):
        col1, col2 = st.columns(2)
        
        with col1:
            selected_student = st.selectbox("Student", student_options)
        
        with col2:
            selected_courses = st.multiselect("Courses to Exclude", course_options)
        
        if st.form_submit_button("Add Exclusion"):
            if selected_student and selected_courses:
                sid = selected_student.split("(")[-1].rstrip(")")
                if sid not in exclusions:
                    exclusions[sid] = []
                exclusions[sid].extend(selected_courses)
                exclusions[sid] = list(set(exclusions[sid]))
                st.session_state[exclusions_key] = exclusions
                st.success(f"Added exclusions for {selected_student}")
                st.rerun()
    
    if exclusions:
        st.markdown("#### Current Exclusions")
        
        for sid, courses in exclusions.items():
            if courses:
                student_row = progress_df[progress_df["ID"].astype(str) == str(sid)]
                name = student_row.iloc[0]["NAME"] if not student_row.empty else sid
                
                with st.expander(f"{name} — {len(courses)} exclusions"):
                    for course in courses:
                        col1, col2 = st.columns([4, 1])
                        with col1:
                            st.write(course)
                        with col2:
                            if st.button("Remove", key=f"remove_{sid}_{course}"):
                                exclusions[sid].remove(course)
                                st.session_state[exclusions_key] = exclusions
                                st.rerun()

def _render_sync_settings():
    """Render Google Drive sync settings."""
    
    st.markdown("### Google Drive Sync")
    
    major = st.session_state.get("current_major", "")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### Refresh Data")
        
        if st.button("Sync from Drive", type="primary"):
            if "period_history_cache" in st.session_state:
                st.session_state.period_history_cache.pop(major, None)
            
            cache_key = f"_advising_index_cache_{major}"
            if cache_key in st.session_state:
                del st.session_state[cache_key]
            
            for key in list(st.session_state.keys()):
                if key.startswith("_fsv_sessions_loaded_"):
                    del st.session_state[key]
            
            st.success("Cache cleared - data will refresh from Drive")
            st.rerun()
        
        st.caption("Refreshes data from Google Drive")
    
    with col2:
        st.markdown("#### Connection Status")
        
        try:
            gd = _get_drive_module()
            service = gd.initialize_drive_service()
            if service:
                st.success("✓ Connected to Google Drive")
            else:
                st.warning("Not connected")
        except Exception as e:
            st.error(f"Connection error: {str(e)[:50]}")
    
    st.markdown("---")
    
    st.markdown("#### Drive Folder Configuration")
    
    import os
    
    folder_id = ""
    try:
        if "google" in st.secrets:
            folder_id = st.secrets["google"].get("folder_id", "")
    except:
        pass
    if not folder_id:
        folder_id = os.getenv("GOOGLE_FOLDER_ID", "")
    
    if folder_id:
        st.text_input("Root Folder ID", value=folder_id, disabled=True)
        st.caption(f"Files are organized in: {folder_id}/{major}/")
    else:
        st.warning("No Google Drive folder configured")
        st.caption("Set GOOGLE_FOLDER_ID in your environment or secrets")
