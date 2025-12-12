import streamlit as st
import pandas as pd

def render_insights():
    """Render the Insights Hub combining Full Student View, QAA, Schedule Conflict, and Planner."""
    
    progress_df = st.session_state.get("progress_df", pd.DataFrame())
    courses_df = st.session_state.get("courses_df", pd.DataFrame())
    
    if progress_df.empty or courses_df.empty:
        st.warning("Please upload data files in the Setup tab first.")
        return
    
    st.markdown("## Insights Hub")
    
    default_tab = st.session_state.get("insights_tab", "All Students")
    tab_options = ["All Students", "Course Analytics", "Schedule Analysis", "Course Planner"]
    
    tabs = st.tabs(tab_options)
    
    with tabs[0]:
        _render_all_students()
    
    with tabs[1]:
        _render_course_analytics()
    
    with tabs[2]:
        _render_schedule_analysis()
    
    with tabs[3]:
        _render_course_planner()

def _render_all_students():
    """Render All Students grid view."""
    from full_student_view import full_student_view
    
    full_student_view()

def _render_course_analytics():
    """Render Course Analytics (QAA Sheet)."""
    
    st.markdown("### Course Analytics (QAA)")
    st.caption("Quality assurance metrics showing eligibility and advising coverage per course")
    
    progress_df = st.session_state.get("progress_df", pd.DataFrame())
    courses_df = st.session_state.get("courses_df", pd.DataFrame())
    advising_selections = st.session_state.get("advising_selections", {})
    
    from utils import check_course_completed, check_course_registered, check_eligibility, get_mutual_concurrent_pairs
    
    major = st.session_state.get("current_major", "")
    bypasses_key = f"bypasses_{major}"
    all_bypasses = st.session_state.get(bypasses_key, {})
    mutual_pairs = get_mutual_concurrent_pairs(courses_df)
    
    graduating_threshold = st.slider(
        "Graduating Threshold (Remaining Credits)",
        min_value=12,
        max_value=60,
        value=36,
        help="Students with remaining credits at or below this threshold are considered 'graduating soon'"
    )
    
    qaa_data = []
    
    for _, course_row in courses_df.iterrows():
        code = course_row.get("Course Code", "")
        title = course_row.get("Course Title", course_row.get("Title", ""))
        
        eligible_count = 0
        advised_count = 0
        optional_count = 0
        not_advised_count = 0
        skipped_advising_count = 0
        attended_graduating = 0
        skipped_graduating = 0
        
        for _, student in progress_df.iterrows():
            sid = student.get("ID", 0)
            
            student_bypasses = all_bypasses.get(sid) or all_bypasses.get(str(sid)) or {}
            sel = advising_selections.get(int(sid)) or advising_selections.get(str(int(sid))) or {}
            advised_list = sel.get("advised", []) or []
            optional_list = sel.get("optional", []) or []
            
            is_advised_student = bool(advised_list or optional_list or sel.get("note", "").strip())
            
            remaining = pd.to_numeric(student.get("# Remaining", student.get("Remaining Credits", 999)), errors="coerce") or 999
            is_graduating = remaining <= graduating_threshold
            
            if check_course_completed(student, code) or check_course_registered(student, code):
                continue
            
            status, _ = check_eligibility(
                student, code, advised_list, courses_df,
                ignore_offered=True, mutual_pairs=mutual_pairs, bypass_map=student_bypasses
            )
            
            if status in ("Eligible", "Eligible (Bypass)"):
                eligible_count += 1
                
                if code in advised_list:
                    advised_count += 1
                    if is_graduating:
                        attended_graduating += 1
                elif code in optional_list:
                    optional_count += 1
                elif is_advised_student:
                    not_advised_count += 1
                else:
                    skipped_advising_count += 1
                    if is_graduating:
                        skipped_graduating += 1
        
        qaa_data.append({
            "Course Code": code,
            "Course Name": title,
            "Eligible": eligible_count,
            "Advised": advised_count,
            "Optional": optional_count,
            "Not Advised": not_advised_count,
            "Skipped Advising": skipped_advising_count,
            "Attended + Graduating": attended_graduating,
            "Skipped + Graduating": skipped_graduating
        })
    
    qaa_df = pd.DataFrame(qaa_data)
    
    qaa_df = qaa_df.sort_values("Eligible", ascending=False)
    
    st.dataframe(qaa_df, use_container_width=True, height=500)
    
    from io import BytesIO
    output = BytesIO()
    qaa_df.to_excel(output, index=False)
    output.seek(0)
    
    st.download_button(
        "Download QAA Report",
        data=output.getvalue(),
        file_name="qaa_report.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

def _render_schedule_analysis():
    """Render Schedule Conflict Analysis."""
    
    st.markdown("### Schedule Conflict Analysis")
    st.caption("Identifies course combinations taken together by students to avoid scheduling conflicts")
    
    progress_df = st.session_state.get("progress_df", pd.DataFrame())
    courses_df = st.session_state.get("courses_df", pd.DataFrame())
    advising_selections = st.session_state.get("advising_selections", {})
    
    min_students = st.slider("Minimum Students", min_value=1, max_value=10, value=2)
    min_courses = st.slider("Minimum Courses per Group", min_value=2, max_value=5, value=2)
    
    from collections import defaultdict
    from itertools import combinations
    
    student_courses = {}
    
    for _, student in progress_df.iterrows():
        sid = student.get("ID", 0)
        sel = advising_selections.get(int(sid)) or advising_selections.get(str(int(sid))) or {}
        advised = sel.get("advised", []) or []
        
        if len(advised) >= min_courses:
            student_courses[sid] = set(advised)
    
    if not student_courses:
        st.info("No students with enough advised courses to analyze.")
        return
    
    st.metric("Students Analyzed", len(student_courses))
    
    combo_students = defaultdict(set)
    
    for sid, courses in student_courses.items():
        for r in range(min_courses, len(courses) + 1):
            for combo in combinations(sorted(courses), r):
                combo_students[combo].add(sid)
    
    filtered_combos = [
        (combo, sids) for combo, sids in combo_students.items()
        if len(sids) >= min_students
    ]
    
    filtered_combos.sort(key=lambda x: (-len(x[1]), -len(x[0])))
    
    if not filtered_combos:
        st.info("No course combinations meet the criteria.")
        return
    
    conflict_data = []
    for combo, sids in filtered_combos[:100]:
        student_names = []
        for sid in sids:
            student_row = progress_df[progress_df["ID"] == sid]
            if student_row.empty:
                student_row = progress_df[progress_df["ID"] == str(sid)]
            if not student_row.empty:
                student_names.append(student_row.iloc[0].get("NAME", str(sid)))
        
        conflict_data.append({
            "Courses": ", ".join(combo),
            "# Courses": len(combo),
            "# Students": len(sids),
            "Students": ", ".join(student_names[:5]) + ("..." if len(student_names) > 5 else "")
        })
    
    conflict_df = pd.DataFrame(conflict_data)
    st.dataframe(conflict_df, use_container_width=True, height=400)
    
    from io import BytesIO
    output = BytesIO()
    conflict_df.to_excel(output, index=False)
    output.seek(0)
    
    st.download_button(
        "Download Schedule Analysis",
        data=output.getvalue(),
        file_name="schedule_conflict_analysis.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

def _render_course_planner():
    """Render Course Offering Planner."""
    from course_offering_planner import course_offering_planner
    
    course_offering_planner()
