import streamlit as st
import pandas as pd
from typing import List
from io import BytesIO

def _get_drive_module():
    """Lazy loader for google_drive module."""
    import google_drive as gd
    return gd

def render_workspace():
    """Render the Advisor Workspace with dual-pane layout."""
    
    progress_df = st.session_state.get("progress_df", pd.DataFrame())
    courses_df = st.session_state.get("courses_df", pd.DataFrame())
    
    if progress_df.empty or courses_df.empty:
        st.warning("Please upload data files in the Setup tab first.")
        return
    
    st.markdown("## Advisor Workspace")
    
    left_col, right_col = st.columns([1, 2])
    
    with left_col:
        _render_student_list(progress_df)
    
    with right_col:
        _render_student_details(progress_df, courses_df)

def _render_student_list(progress_df: pd.DataFrame):
    """Render the student list panel with search and filters."""
    
    st.markdown("### Students")
    
    search = st.text_input("Search", placeholder="Name or ID...", key="workspace_search")
    
    with st.expander("Filters", expanded=False):
        advising_selections = st.session_state.get("advising_selections", {})
        
        status_filter = st.radio(
            "Status",
            ["All", "Not Advised", "Advised"],
            horizontal=True,
            key="workspace_status_filter"
        )
        
        if "# Remaining" in progress_df.columns:
            remaining_col = "# Remaining"
        elif "Remaining Credits" in progress_df.columns:
            remaining_col = "Remaining Credits"
        else:
            remaining_col = None
        
        if remaining_col:
            remaining_vals = pd.to_numeric(progress_df[remaining_col], errors="coerce").fillna(0)
            min_r, max_r = int(remaining_vals.min()), int(remaining_vals.max())
            if min_r < max_r:
                credits_range = st.slider(
                    "Remaining Credits",
                    min_value=min_r,
                    max_value=max_r,
                    value=(min_r, max_r),
                    key="workspace_credits_filter"
                )
            else:
                credits_range = (min_r, max_r)
        else:
            credits_range = None
    
    filtered_df = progress_df.copy()
    
    if search:
        search_lower = search.lower()
        name_match = filtered_df["NAME"].astype(str).str.lower().str.contains(search_lower, na=False)
        id_match = filtered_df["ID"].astype(str).str.contains(search, na=False)
        filtered_df = filtered_df[name_match | id_match]
    
    if status_filter != "All":
        def is_advised(sid):
            sel = advising_selections.get(int(sid)) or advising_selections.get(str(int(sid))) or {}
            return bool(sel.get("advised") or sel.get("optional") or sel.get("note", "").strip())
        
        if status_filter == "Advised":
            filtered_df = filtered_df[filtered_df["ID"].apply(is_advised)]
        else:
            filtered_df = filtered_df[~filtered_df["ID"].apply(is_advised)]
    
    if remaining_col and credits_range:
        remaining_vals = pd.to_numeric(filtered_df[remaining_col], errors="coerce").fillna(0)
        filtered_df = filtered_df[(remaining_vals >= credits_range[0]) & (remaining_vals <= credits_range[1])]
    
    st.caption(f"{len(filtered_df)} students")
    
    current_sid = st.session_state.get("workspace_selected_student")
    
    for _, row in filtered_df.iterrows():
        sid = row.get("ID", 0)
        name = row.get("NAME", "Unknown")
        
        sel = advising_selections.get(int(sid)) or advising_selections.get(str(int(sid))) or {}
        is_advised = bool(sel.get("advised") or sel.get("optional") or sel.get("note", "").strip())
        
        status_icon = "✓" if is_advised else "○"
        
        remaining = ""
        if remaining_col and remaining_col in row:
            remaining = f" ({int(row[remaining_col])} cr)"
        
        is_selected = current_sid == sid
        btn_type = "primary" if is_selected else "secondary"
        
        if st.button(
            f"{status_icon} {name}{remaining}",
            key=f"student_btn_{sid}",
            type=btn_type
        ):
            st.session_state["workspace_selected_student"] = sid
            st.session_state["current_student_id"] = sid
            st.rerun()

def _render_student_details(progress_df: pd.DataFrame, courses_df: pd.DataFrame):
    """Render the student details panel."""
    
    sid = st.session_state.get("workspace_selected_student")
    
    if not sid:
        st.info("Select a student from the list to view details and make recommendations.")
        return
    
    student_rows = progress_df[progress_df["ID"] == sid]
    if student_rows.empty:
        student_rows = progress_df[progress_df["ID"] == str(sid)]
    
    if student_rows.empty:
        st.error("Student not found")
        return
    
    student_row = student_rows.iloc[0]
    
    _render_student_header(student_row)
    
    st.markdown("---")
    
    tabs = st.tabs(["Eligibility", "Advising", "Notes & Email"])
    
    with tabs[0]:
        _render_eligibility_tab(student_row, courses_df)
    
    with tabs[1]:
        _render_advising_tab(student_row, courses_df)
    
    with tabs[2]:
        _render_notes_tab(student_row)

def _render_student_header(student_row: pd.Series):
    """Render student info header with key stats."""
    
    name = student_row.get("NAME", "Unknown")
    sid = student_row.get("ID", 0)
    
    st.markdown(f"### {name}")
    st.caption(f"ID: {sid}")
    
    cols = st.columns(4)
    
    with cols[0]:
        completed = student_row.get("# of Credits Completed", 0)
        registered = student_row.get("# Registered", 0)
        total = int(float(completed or 0) + float(registered or 0))
        st.metric("Credits Completed", total)
    
    with cols[1]:
        remaining = student_row.get("# Remaining", student_row.get("Remaining Credits", 0))
        st.metric("Remaining", int(float(remaining or 0)))
    
    with cols[2]:
        from utils import get_student_standing
        standing = get_student_standing(int(float(completed or 0) + float(registered or 0)))
        st.metric("Standing", standing)
    
    with cols[3]:
        advising_selections = st.session_state.get("advising_selections", {})
        sel = advising_selections.get(int(sid)) or advising_selections.get(str(int(sid))) or {}
        advised_count = len(sel.get("advised", []))
        st.metric("Courses Advised", advised_count)

def _render_eligibility_tab(student_row: pd.Series, courses_df: pd.DataFrame):
    """Render course eligibility for this student."""
    from utils import check_course_completed, check_course_registered, check_eligibility, get_mutual_concurrent_pairs
    
    st.markdown("#### Course Eligibility")
    
    sid = student_row.get("ID", 0)
    major = st.session_state.get("current_major", "")
    
    bypasses_key = f"bypasses_{major}"
    all_bypasses = st.session_state.get(bypasses_key, {})
    student_bypasses = all_bypasses.get(sid) or all_bypasses.get(str(sid)) or {}
    
    mutual_pairs = get_mutual_concurrent_pairs(courses_df)
    
    advising_selections = st.session_state.get("advising_selections", {})
    sel = advising_selections.get(int(sid)) or advising_selections.get(str(int(sid))) or {}
    advised_list = sel.get("advised", []) or []
    
    eligible_courses = []
    completed_courses = []
    registered_courses = []
    not_eligible_courses = []
    
    for _, course_row in courses_df.iterrows():
        code = course_row.get("Course Code", "")
        title = course_row.get("Course Title", course_row.get("Title", ""))
        credits = course_row.get("Credits", 3)
        
        if check_course_completed(student_row, code):
            completed_courses.append({"code": code, "title": title, "credits": credits})
        elif check_course_registered(student_row, code):
            registered_courses.append({"code": code, "title": title, "credits": credits})
        else:
            status, note = check_eligibility(
                student_row, code, advised_list, courses_df,
                ignore_offered=True, mutual_pairs=mutual_pairs, bypass_map=student_bypasses
            )
            if status in ("Eligible", "Eligible (Bypass)"):
                eligible_courses.append({
                    "code": code, "title": title, "credits": credits,
                    "status": status, "note": note
                })
            else:
                not_eligible_courses.append({
                    "code": code, "title": title, "credits": credits,
                    "note": note
                })
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Eligible", len(eligible_courses))
    with col2:
        st.metric("Completed", len(completed_courses))
    with col3:
        st.metric("Registered", len(registered_courses))
    with col4:
        st.metric("Not Eligible", len(not_eligible_courses))
    
    st.markdown("##### Eligible Courses")
    
    if eligible_courses:
        for course in eligible_courses:
            bypass_badge = " 🟣" if course["status"] == "Eligible (Bypass)" else ""
            note_text = f" — {course['note']}" if course.get("note") else ""
            st.markdown(f"• **{course['code']}** {course['title']} ({course['credits']} cr){bypass_badge}{note_text}")
    else:
        st.info("No eligible courses found")
    
    with st.expander("View Completed & Registered", expanded=False):
        st.markdown("**Completed:**")
        for c in completed_courses:
            st.caption(f"✓ {c['code']} - {c['title']}")
        
        st.markdown("**Registered:**")
        for c in registered_courses:
            st.caption(f"📝 {c['code']} - {c['title']}")

def _render_advising_tab(student_row: pd.Series, courses_df: pd.DataFrame):
    """Render advising form for this student."""
    from utils import check_course_completed, check_course_registered, check_eligibility, get_mutual_concurrent_pairs
    from advising_history import save_session_for_student
    
    st.markdown("#### Course Recommendations")
    
    sid = student_row.get("ID", 0)
    major = st.session_state.get("current_major", "")
    
    bypasses_key = f"bypasses_{major}"
    all_bypasses = st.session_state.get(bypasses_key, {})
    student_bypasses = all_bypasses.get(sid) or all_bypasses.get(str(sid)) or {}
    
    mutual_pairs = get_mutual_concurrent_pairs(courses_df)
    
    advising_selections = st.session_state.get("advising_selections", {})
    sel = advising_selections.get(int(sid)) or advising_selections.get(str(int(sid))) or {}
    
    current_advised = sel.get("advised", []) or []
    current_optional = sel.get("optional", []) or []
    current_repeat = sel.get("repeat", []) or []
    
    eligible_courses = []
    repeat_options = []
    
    for _, course_row in courses_df.iterrows():
        code = course_row.get("Course Code", "")
        
        if check_course_completed(student_row, code) or check_course_registered(student_row, code):
            repeat_options.append(code)
        else:
            status, _ = check_eligibility(
                student_row, code, current_advised, courses_df,
                ignore_offered=True, mutual_pairs=mutual_pairs, bypass_map=student_bypasses
            )
            if status in ("Eligible", "Eligible (Bypass)"):
                eligible_courses.append(code)
    
    with st.form(key=f"advising_form_{sid}"):
        advised = st.multiselect(
            "Advised Courses",
            options=eligible_courses,
            default=[c for c in current_advised if c in eligible_courses],
            help="Courses to recommend for this student"
        )
        
        optional = st.multiselect(
            "Optional Courses",
            options=eligible_courses,
            default=[c for c in current_optional if c in eligible_courses],
            help="Additional optional recommendations"
        )
        
        if repeat_options:
            repeat = st.multiselect(
                "Repeat Courses",
                options=repeat_options,
                default=[c for c in current_repeat if c in repeat_options],
                help="Courses to repeat"
            )
        else:
            repeat = []
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.form_submit_button("Save Recommendations", type="primary"):
                norm_sid = int(sid)
                st.session_state.advising_selections[norm_sid] = {
                    "advised": list(advised),
                    "optional": list(optional),
                    "repeat": list(repeat),
                    "note": sel.get("note", "")
                }
                st.session_state.majors[major]["advising_selections"] = st.session_state.advising_selections.copy()
                
                save_session_for_student(norm_sid)
                st.success("Saved!")
                st.rerun()
        
        with col2:
            credits_lookup = {}
            for _, r in courses_df.iterrows():
                credits_lookup[r.get("Course Code", "")] = float(r.get("Credits", 3) or 3)
            
            total_credits = sum(credits_lookup.get(c, 3) for c in advised)
            optional_credits = sum(credits_lookup.get(c, 3) for c in optional)
            
            st.metric("Total Credits", f"{int(total_credits)} + {int(optional_credits)} optional")

def _render_notes_tab(student_row: pd.Series):
    """Render notes and email section."""
    from advising_history import save_session_for_student
    
    st.markdown("#### Notes")
    
    sid = student_row.get("ID", 0)
    major = st.session_state.get("current_major", "")
    
    advising_selections = st.session_state.get("advising_selections", {})
    sel = advising_selections.get(int(sid)) or advising_selections.get(str(int(sid))) or {}
    
    current_note = sel.get("note", "")
    
    note = st.text_area(
        "Advising Notes",
        value=current_note,
        height=150,
        key=f"note_input_{sid}",
        placeholder="Enter notes about this advising session..."
    )
    
    if st.button("Save Note"):
        norm_sid = int(sid)
        if norm_sid not in st.session_state.advising_selections:
            st.session_state.advising_selections[norm_sid] = {}
        st.session_state.advising_selections[norm_sid]["note"] = note
        st.session_state.majors[major]["advising_selections"] = st.session_state.advising_selections.copy()
        save_session_for_student(norm_sid)
        st.success("Note saved!")
    
    st.markdown("---")
    
    st.markdown("#### Email Advising Sheet")
    
    roster_key = f"email_roster_{major}"
    email_roster = st.session_state.get(roster_key, pd.DataFrame())
    
    if email_roster.empty:
        st.info("Upload an email roster in Setup to enable email functionality.")
    else:
        student_email_row = email_roster[email_roster["ID"] == sid]
        if student_email_row.empty:
            student_email_row = email_roster[email_roster["ID"] == str(sid)]
        
        if not student_email_row.empty:
            email = student_email_row.iloc[0].get("Email", "")
            st.text_input("Email", value=email, disabled=True)
            
            if st.button("Send Advising Sheet", type="primary"):
                st.info("Email functionality will be connected here")
        else:
            st.warning("No email found for this student in the roster")
