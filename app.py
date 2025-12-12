# app.py - Advising Dashboard with Modern UI

import os
import pandas as pd
import streamlit as st
from datetime import datetime

from visual_theme import apply_visual_theme
from utils import log_info, log_error, load_progress_excel

def _get_drive_module():
    """Lazy loader for google_drive module to avoid import-time side effects."""
    import google_drive as gd
    return gd

st.set_page_config(
    page_title="Advising Dashboard",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="collapsed"
)

apply_visual_theme()

MAJORS = ["PBHL", "SPTH-New", "SPTH-Old", "NURS"]

if "majors" not in st.session_state:
    st.session_state.majors = {
        m: {
            "courses_df": pd.DataFrame(),
            "progress_df": pd.DataFrame(),
            "advising_selections": {},
        }
        for m in MAJORS
    }

def _sync_globals_from_bucket(major: str):
    """Sync global session state from major bucket."""
    bucket = st.session_state.majors.get(major, {})
    st.session_state.courses_df = bucket.get("courses_df", pd.DataFrame())
    st.session_state.progress_df = bucket.get("progress_df", pd.DataFrame())
    st.session_state.advising_selections = bucket.get("advising_selections", {})

def _sync_bucket_from_globals(major: str):
    """Sync major bucket from global session state."""
    if major not in st.session_state.majors:
        st.session_state.majors[major] = {}
    bucket = st.session_state.majors[major]
    bucket["courses_df"] = st.session_state.get("courses_df", pd.DataFrame())
    bucket["progress_df"] = st.session_state.get("progress_df", pd.DataFrame())
    bucket["advising_selections"] = st.session_state.get("advising_selections", {})

def _default_period_for_today() -> tuple:
    """Return default semester and year based on current date."""
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

def _render_header():
    """Render the persistent header with major/period selection."""
    from advising_period import get_current_period
    
    header_cols = st.columns([1, 2, 3, 2])
    
    with header_cols[0]:
        if os.path.exists("pu_logo.png"):
            st.image("pu_logo.png", width=80)
    
    with header_cols[1]:
        major_options = ["Select major..."] + MAJORS
        current = st.session_state.get("current_major", "Select major...")
        if current not in major_options:
            current = "Select major..."
        
        selected_major = st.selectbox(
            "Major",
            major_options,
            index=major_options.index(current),
            key="header_major_select",
            label_visibility="collapsed"
        )
        
        if selected_major != st.session_state.get("current_major"):
            st.session_state["current_major"] = selected_major
            if selected_major in MAJORS:
                _sync_globals_from_bucket(selected_major)
            st.rerun()
    
    with header_cols[2]:
        if st.session_state.get("current_major") in MAJORS:
            current_period = get_current_period()
            period_text = f"📅 {current_period.get('semester', 'No period')} {current_period.get('year', '')} — {current_period.get('advisor_name', 'Not set')}"
            st.markdown(f"**{period_text}**")
        else:
            st.markdown("*Select a major to begin*")
    
    with header_cols[3]:
        if st.session_state.get("current_major") in MAJORS:
            progress_df = st.session_state.get("progress_df", pd.DataFrame())
            advising_selections = st.session_state.get("advising_selections", {})
            
            if not progress_df.empty:
                total = len(progress_df)
                advised = sum(
                    1 for _, row in progress_df.iterrows()
                    if (advising_selections.get(int(row.get("ID", 0))) or 
                        advising_selections.get(str(int(row.get("ID", 0)))) or {}).get("advised")
                )
                pct = int(advised / total * 100) if total > 0 else 0
                st.markdown(f"**Progress:** {advised}/{total} ({pct}%)")

def _render_navigation():
    """Render the main navigation tabs."""
    
    nav_options = ["Home", "Setup", "Workspace", "Insights", "Settings"]
    
    if "nav_selection" not in st.session_state:
        st.session_state["nav_selection"] = "Home"
    
    cols = st.columns(len(nav_options))
    
    for i, option in enumerate(nav_options):
        with cols[i]:
            is_active = st.session_state.get("nav_selection") == option
            btn_type = "primary" if is_active else "secondary"
            
            icons = {"Home": "🏠", "Setup": "⚙️", "Workspace": "👤", "Insights": "📊", "Settings": "🔧"}
            
            if st.button(
                f"{icons.get(option, '')} {option}",
                key=f"nav_{option}",
                type=btn_type
            ):
                st.session_state["nav_selection"] = option
                st.rerun()
    
    return st.session_state.get("nav_selection", "Home")

def _render_period_gate():
    """Render period selection gate for first-time setup."""
    from advising_period import get_current_period, start_new_period, get_all_periods, set_current_period
    
    current_period = get_current_period()
    all_periods = get_all_periods()
    major = st.session_state.get("current_major", "")
    
    if current_period.get("advisor_name", "").strip():
        return True
    
    st.markdown("## Welcome! Let's set up your advising period.")
    st.markdown("Before you begin, please select or create an advising period.")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### Create New Period")
        
        with st.form("new_period_gate"):
            default_semester, default_year = _default_period_for_today()
            
            semester = st.selectbox("Semester", ["Fall", "Spring", "Summer"],
                                   index=["Fall", "Spring", "Summer"].index(default_semester))
            year = st.number_input("Year", min_value=2020, max_value=2099, value=default_year)
            advisor = st.text_input("Your Name")
            
            if st.form_submit_button("Start Period", type="primary"):
                if not advisor:
                    st.error("Please enter your name")
                else:
                    st.session_state.advising_selections = {}
                    st.session_state.majors[major]["advising_selections"] = {}
                    
                    new_period, saved = start_new_period(semester, int(year), advisor)
                    st.success(f"Created: {semester} {year}")
                    st.rerun()
    
    with col2:
        st.markdown("### Use Existing Period")
        
        real_periods = [p for p in all_periods if p.get("advisor_name", "").strip()]
        
        if real_periods:
            period_options = []
            period_map = {}
            for p in real_periods:
                label = f"{p.get('semester', '')} {p.get('year', '')} — {p.get('advisor_name', '')}"
                period_options.append(label)
                period_map[label] = p
            
            selected = st.selectbox("Select Period", period_options)
            
            if st.button("Use This Period"):
                selected_period = period_map[selected]
                set_current_period(selected_period)
                st.session_state.advising_selections = {}
                st.session_state.majors[major]["advising_selections"] = {}
                st.success(f"Using: {selected}")
                st.rerun()
        else:
            st.info("No existing periods. Create a new one to get started.")
    
    return False

def _auto_load_from_drive(major: str):
    """Auto-load data files from Google Drive for the selected major."""
    from io import BytesIO
    
    load_key = f"_loaded_{major}"
    if st.session_state.get(load_key):
        return
    
    if not st.session_state.courses_df.empty and not st.session_state.progress_df.empty:
        st.session_state[load_key] = True
        return
    
    root_folder_id = ""
    try:
        if "google" in st.secrets:
            root_folder_id = st.secrets["google"].get("folder_id", "")
    except:
        pass
    if not root_folder_id:
        root_folder_id = os.getenv("GOOGLE_FOLDER_ID", "")
    
    if not root_folder_id:
        return
    
    try:
        gd = _get_drive_module()
        service = gd.initialize_drive_service()
        if not service:
            return
        
        major_folder_id = gd.get_major_folder_id(service, major, root_folder_id)
        
        if st.session_state.courses_df.empty:
            file_id = gd.find_file_in_drive(service, "courses_table.xlsx", major_folder_id)
            if file_id:
                data = gd.download_file_from_drive(service, file_id)
                if data:
                    st.session_state.courses_df = pd.read_excel(BytesIO(data))
                    st.session_state.majors[major]["courses_df"] = st.session_state.courses_df
                    log_info(f"Loaded courses from Drive for {major}")
        
        if st.session_state.progress_df.empty:
            file_id = gd.find_file_in_drive(service, "progress_report.xlsx", major_folder_id)
            if file_id:
                data = gd.download_file_from_drive(service, file_id)
                if data:
                    st.session_state.progress_df = load_progress_excel(data)
                    st.session_state.majors[major]["progress_df"] = st.session_state.progress_df
                    log_info(f"Loaded progress from Drive for {major}")
        
        st.session_state[load_key] = True
    except Exception as e:
        log_error(f"Auto-load from Drive failed for {major}", e)

def main():
    """Main application entry point."""
    
    _render_header()
    
    st.markdown("---")
    
    selected_major = st.session_state.get("current_major", "Select major...")
    
    if selected_major not in MAJORS:
        st.markdown("## 🎓 Advising Dashboard")
        st.info("👆 Please select a major from the dropdown above to get started.")
        
        st.markdown("### Quick Start")
        st.markdown("""
        1. **Select a major** from the dropdown above
        2. **Set up your advising period** (semester, year, your name)  
        3. **Upload data files** (courses table and progress report)
        4. **Start advising** students in the Workspace
        """)
        return
    
    _sync_globals_from_bucket(selected_major)
    
    _auto_load_from_drive(selected_major)
    
    if not _render_period_gate():
        return
    
    active_nav = _render_navigation()
    
    st.markdown("---")
    
    if active_nav == "Home":
        from pages.home import render_home
        render_home()
    
    elif active_nav == "Setup":
        from pages.setup import render_setup
        render_setup()
    
    elif active_nav == "Workspace":
        from pages.workspace import render_workspace
        render_workspace()
    
    elif active_nav == "Insights":
        from pages.insights import render_insights
        render_insights()
    
    elif active_nav == "Settings":
        from pages.settings import render_settings
        render_settings()
    
    _sync_bucket_from_globals(selected_major)

if __name__ == "__main__":
    main()
