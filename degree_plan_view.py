# degree_plan_view.py

import streamlit as st
import pandas as pd
from utils import check_eligibility


def degree_plan_view():
    """Render semester-by-semester degree plan with student progress tracking."""
    st.markdown("## 🎓 Degree Plan Progression")
    st.markdown("Semester-by-semester curriculum showing student progress")
    
    courses_df = st.session_state.courses_df
    progress_df = st.session_state.progress_df
    
    if courses_df.empty:
        st.warning("No course data available. Please upload courses table.")
        return
    
    if progress_df.empty:
        st.info("No student data available. Upload progress report to see student progression.")
        _render_empty_degree_plan(courses_df)
        return
    
    # Student selector
    st.markdown("### Select Student")
    students = progress_df["Student Name"].unique().tolist()
    
    if not students:
        st.warning("No students found in progress data.")
        _render_empty_degree_plan(courses_df)
        return
    
    selected_student = st.selectbox(
        "Student",
        options=students,
        key="degree_plan_student_selector"
    )
    
    # Get student progress
    student_data = progress_df[progress_df["Student Name"] == selected_student].iloc[0]
    
    # Display student info
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Student ID", student_data.get("Student ID", "N/A"))
    with col2:
        st.metric("Standing", student_data.get("Standing", "N/A"))
    with col3:
        remaining_credits = student_data.get("Remaining Credits", 0)
        st.metric("Credits Remaining", int(remaining_credits) if pd.notna(remaining_credits) else "N/A")
    
    st.markdown("---")
    
    # Render degree plan with student progress
    _render_degree_plan_with_progress(courses_df, student_data)


def _render_empty_degree_plan(courses_df):
    """Render degree plan structure without student progress."""
    st.markdown("### Degree Plan Structure")
    st.info("Upload student progress data to see individual progression through the degree plan.")
    
    # Get semester structure
    semesters = _get_semester_structure(courses_df)
    
    # Render each semester
    for semester_name in semesters.keys():
        with st.expander(f"**{semester_name}**", expanded=False):
            semester_courses = semesters[semester_name]
            if semester_courses:
                for course in semester_courses:
                    st.markdown(f"- **{course['code']}** - {course['title']} ({course['credits']} cr)")
            else:
                st.caption("No courses assigned to this semester")


def _render_degree_plan_with_progress(courses_df, student_data):
    """Render degree plan with student progress color coding."""
    
    # Get semester structure
    semesters = _get_semester_structure(courses_df)
    
    # Get student course statuses
    course_statuses = _get_student_course_statuses(student_data, courses_df)
    
    # Legend
    st.markdown("### Progress Legend")
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.markdown("🟢 **Completed**")
    with col2:
        st.markdown("🟡 **Registered**")
    with col3:
        st.markdown("🔵 **Available**")
    with col4:
        st.markdown("⚪ **Not Eligible**")
    with col5:
        st.markdown("🔴 **Failed/Repeat**")
    
    st.markdown("---")
    
    # Render semester grid
    st.markdown("### Semester-by-Semester Progression")
    
    # Group semesters by year for better layout
    year_groups = {
        "First Year": ["Fall 1", "Spring 1", "Summer 1"],
        "Second Year": ["Fall 2", "Spring 2", "Summer 2"],
        "Third Year": ["Fall 3", "Spring 3"]
    }
    
    for year_name, semester_list in year_groups.items():
        st.markdown(f"#### {year_name}")
        
        # Create columns for each semester in the year
        cols = st.columns(len(semester_list))
        
        for idx, semester_name in enumerate(semester_list):
            with cols[idx]:
                st.markdown(f"**{semester_name}**")
                
                semester_courses = semesters.get(semester_name, [])
                total_credits = sum(course['credits'] for course in semester_courses)
                st.caption(f"Total: {total_credits} credits")
                
                if semester_courses:
                    for course in semester_courses:
                        course_code = course['code']
                        status = course_statuses.get(course_code, 'not_eligible')
                        
                        # Get status icon and color
                        icon, color = _get_status_display(status)
                        
                        # Display course box
                        st.markdown(
                            f"{icon} **{course_code}**<br>"
                            f"<small>{course['title']}</small><br>"
                            f"<small>{course['credits']} cr</small>",
                            unsafe_allow_html=True
                        )
                        st.markdown("")  # Spacing
                else:
                    st.caption("No courses")
        
        st.markdown("---")


def _get_semester_structure(courses_df):
    """Parse semester structure from courses table."""
    
    # Define semester order
    semester_order = [
        "Fall 1", "Spring 1", "Summer 1",
        "Fall 2", "Spring 2", "Summer 2",
        "Fall 3", "Spring 3"
    ]
    
    # Initialize semester structure
    semesters = {sem: [] for sem in semester_order}
    
    # Check if courses table has suggested semester column
    # Explicitly prefer "Suggested Semester" to avoid grabbing "Semester Offered"
    semester_col = None
    for col in courses_df.columns:
        if 'suggested' in col.lower() and 'semester' in col.lower():
            semester_col = col
            break
    
    # Fallback: look for any semester-like column if no "suggested semester" found
    if not semester_col:
        for col in courses_df.columns:
            col_lower = col.lower()
            if 'semester' in col_lower and 'offered' not in col_lower:
                semester_col = col
                break
    
    if semester_col:
        # Use semester column from data
        for _, course_row in courses_df.iterrows():
            semester = str(course_row.get(semester_col, "")).strip()
            # Normalize semester value and check if it matches expected format
            if pd.notna(semester) and semester and semester in semesters:
                semesters[semester].append({
                    'code': course_row["Course Code"],
                    'title': course_row.get("Course Title", course_row.get("Title", "")),
                    'credits': course_row.get("Credits", 3)
                })
    else:
        # PBHL Curriculum from official degree plan (PDF pages 9-10)
        pbhl_curriculum = {
            "Fall 1": ["BIOL201", "ENGL201", "CHEM201", "CHEM209", "PBHL201", "CHEM210"],
            "Spring 1": ["ENGL202", "CIVL201", "CHEM202", "COMM201", "PBHL202"],
            "Summer 1": [],  # Free Elective
            "Fall 2": ["CIVL202", "CMPS202", "PBHL203", "PBHL204", "PBHL212"],
            "Spring 2": ["ARAB201", "STAT201", "ACCT201", "PBHL220", "COMM214", "PBHL270"],
            "Summer 2": ["PBHL282"],  # Professional Internship
            "Fall 3": ["MNGT201", "PBHL211", "PBHL206", "PBHL207", "PBHL208"],
            "Spring 3": ["SOCL210", "PBHL205", "PBHL213", "PBHL280", "PBHL281"]
        }
        
        # Map courses to semesters based on PBHL curriculum
        for semester, course_codes in pbhl_curriculum.items():
            for course_code in course_codes:
                course_row = courses_df[courses_df["Course Code"] == course_code]
                if not course_row.empty:
                    row = course_row.iloc[0]
                    semesters[semester].append({
                        'code': course_code,
                        'title': row.get("Course Title", row.get("Title", "")),
                        'credits': row.get("Credits", 3)
                    })
        
        # Add remaining courses not in PBHL curriculum (for other majors or electives)
        assigned_courses = set()
        for sem_courses in pbhl_curriculum.values():
            assigned_courses.update(sem_courses)
        
        for _, course_row in courses_df.iterrows():
            course_code = course_row["Course Code"]
            if course_code not in assigned_courses:
                # Assign by course level as fallback
                course_num = ''.join(filter(str.isdigit, course_code))
                if course_num:
                    level = int(course_num[0]) if len(course_num) >= 1 else 2
                    if level == 1:
                        semester = "Fall 1"
                    elif level == 2:
                        semester = "Spring 2"
                    else:
                        semester = "Fall 3"
                    
                    semesters[semester].append({
                        'code': course_code,
                        'title': course_row.get("Course Title", course_row.get("Title", "")),
                        'credits': course_row.get("Credits", 3)
                    })
    
    return semesters


def _get_student_course_statuses(student_data, courses_df):
    """Determine status of each course for the student."""
    
    statuses = {}
    
    for _, course_row in courses_df.iterrows():
        course_code = course_row["Course Code"]
        
        # Check if student has taken/is taking this course
        student_status = student_data.get(course_code, "")
        
        if pd.isna(student_status) or student_status == "":
            # Not taken - check if eligible
            is_eligible, _ = check_eligibility(
                course_row,
                student_data,
                courses_df,
                ignore_offered=True
            )
            statuses[course_code] = 'available' if is_eligible else 'not_eligible'
        elif student_status.lower() in ['c', 'completed', 'pass', 'p']:
            statuses[course_code] = 'completed'
        elif student_status.lower() in ['r', 'registered', 'current']:
            statuses[course_code] = 'registered'
        elif student_status.lower() in ['f', 'fail', 'failed']:
            statuses[course_code] = 'failed'
        else:
            # Other status (advised, etc.) - treat as available
            statuses[course_code] = 'available'
    
    return statuses


def _get_status_display(status):
    """Get display icon and color for course status."""
    
    status_map = {
        'completed': ('🟢', 'green'),
        'registered': ('🟡', 'yellow'),
        'available': ('🔵', 'blue'),
        'not_eligible': ('⚪', 'gray'),
        'failed': ('🔴', 'red')
    }
    
    return status_map.get(status, ('⚪', 'gray'))
