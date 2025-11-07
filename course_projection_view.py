# course_projection_view.py

import streamlit as st
import pandas as pd
from io import BytesIO
from utils import (
    check_course_completed,
    check_course_registered,
    check_eligibility,
    get_student_standing,
    parse_requirements,
    log_info,
    log_error
)
from reporting import add_summary_sheet, apply_full_report_formatting

_CODE_COLORS = {
    "c":  "#C6E0B4",   # Completed -> light green
    "r":  "#BDD7EE",   # Registered -> light blue
    "a":  "#FFF2CC",   # Advised -> light yellow
    "1":  "#FFE6F0",   # Next semester -> light pink
    "2":  "#FFF4E6",   # 2 semesters out -> light orange
    "3":  "#F0F0FF",   # 3 semesters out -> light purple
    "4":  "#E6F7FF",   # 4+ semesters out -> light blue
    "flex": "#F5F5F5", # Flexible (1/2/3) -> light gray
}

def _style_projection_codes(df: pd.DataFrame, code_cols: list[str]) -> "pd.io.formats.style.Styler":
    """Color the projection table based on status codes."""
    def _bg(v):
        v_str = str(v).strip().lower()
        
        # Check for flexible courses (contains /)
        if "/" in v_str:
            return f"background-color: {_CODE_COLORS['flex']}"
        
        # Check specific codes
        col = _CODE_COLORS.get(v_str)
        if col:
            return f"background-color: {col}"
        
        # Check for semester numbers >= 4
        if v_str.isdigit() and int(v_str) >= 4:
            return f"background-color: {_CODE_COLORS['4']}"
        
        return ""
    
    styler = df.style
    if code_cols:
        styler = styler.map(_bg, subset=code_cols)
    return styler


def calculate_earliest_semester(student_row, course_code, courses_df, advised_courses, memo=None, visiting=None):
    """
    Calculate the earliest semester a student can take a course based on prerequisites.
    
    Returns integer representing semester number (1 = next semester, 2 = after that, etc.)
    or special values: "c" (completed), "r" (registered), "a" (advised), "-" (not applicable)
    """
    if memo is None:
        memo = {}
    if visiting is None:
        visiting = set()
    
    # Check if already completed or registered
    if check_course_completed(student_row, course_code):
        return "c"
    if check_course_registered(student_row, course_code):
        return "r"
    if course_code in advised_courses:
        return "a"
    
    # Check memoization
    if course_code in memo:
        return memo[course_code]
    
    # Detect circular dependencies
    if course_code in visiting:
        # Circular dependency detected - return semester 1 as safe fallback
        log_info(f"Circular dependency detected for {course_code}, using fallback")
        return 1
    
    # Mark as currently visiting
    visiting.add(course_code)
    
    try:
        # Get course info
        course_info = courses_df[courses_df["Course Code"] == course_code]
        if course_info.empty:
            return "-"
        
        # Parse prerequisites
        prereqs = parse_requirements(course_info.iloc[0].get("Prerequisite", ""))
        
        # Calculate earliest semester based on prerequisites
        max_prereq_semester = 0
        
        for prereq in prereqs:
            if "standing" in prereq.lower():
                # Handle standing requirements
                if "senior" in prereq.lower():
                    # Assume senior standing (60 credits) takes ~4 semesters
                    max_prereq_semester = max(max_prereq_semester, 4)
                elif "junior" in prereq.lower():
                    # Assume junior standing (30 credits) takes ~2 semesters
                    max_prereq_semester = max(max_prereq_semester, 2)
                continue
            
            # Recursive call for course prerequisites
            prereq_sem = calculate_earliest_semester(student_row, prereq, courses_df, advised_courses, memo, visiting)
            
            if prereq_sem == "c" or prereq_sem == "r" or prereq_sem == "a":
                # Prerequisite already satisfied
                continue
            elif prereq_sem == "-":
                # Prerequisite doesn't exist - skip
                continue
            elif isinstance(prereq_sem, int):
                max_prereq_semester = max(max_prereq_semester, prereq_sem)
        
        # This course can be taken in the semester after all prerequisites
        earliest = max_prereq_semester + 1 if max_prereq_semester > 0 else 1
        memo[course_code] = earliest
        return earliest
    finally:
        # Remove from visiting set when done
        visiting.discard(course_code)


def count_dependent_courses(course_code, courses_df, memo=None, visiting=None):
    """
    Count how many other courses depend on this course (directly or indirectly).
    Uses memoization and cycle detection for efficiency and safety.
    """
    if memo is None:
        memo = {}
    if visiting is None:
        visiting = set()
    
    # Check memoization
    if course_code in memo:
        return memo[course_code]
    
    # Detect circular dependencies
    if course_code in visiting:
        return 0  # Circular dependency - return 0 to break cycle
    
    visiting.add(course_code)
    
    try:
        dependents = 0
        for _, row in courses_df.iterrows():
            prereqs = parse_requirements(row.get("Prerequisite", ""))
            # Filter out standing requirements
            prereqs = [p for p in prereqs if "standing" not in p.lower()]
            
            if course_code in prereqs:
                dependents += 1
                # Add transitive dependencies
                dependents += count_dependent_courses(row["Course Code"], courses_df, memo, visiting)
        
        memo[course_code] = dependents
        return dependents
    finally:
        visiting.discard(course_code)


def build_projection_schedule(student_row, courses_df, advised_courses, credit_limit_typical=15, credit_limit_max=18):
    """
    Build a complete course projection schedule for a student.
    Distributes courses across semesters respecting:
    1. Prerequisites (earliest possible semester)
    2. Credit limits (15-17 typical, 18 max)
    3. Critical path (courses that block others scheduled first)
    
    Returns dict mapping course_code -> projected_semester_string
    """
    projection = {}
    memo = {}
    
    # Get all courses
    all_courses = courses_df["Course Code"].tolist()
    
    # Step 1: Calculate earliest semester for each course
    earliest_semesters = {}
    for course_code in all_courses:
        result = calculate_earliest_semester(student_row, course_code, courses_df, advised_courses, memo)
        if result in ["c", "r", "a", "-"]:
            projection[course_code] = result
        else:
            earliest_semesters[course_code] = result
    
    # Step 2: Group remaining courses by earliest semester
    # Pre-calculate dependent counts with shared memo for efficiency
    dependency_memo = {}
    semester_buckets = {}
    for course_code, sem_num in earliest_semesters.items():
        if sem_num not in semester_buckets:
            semester_buckets[sem_num] = []
        
        # Get course info
        course_info = courses_df[courses_df["Course Code"] == course_code]
        if course_info.empty:
            continue
        
        credits = int(course_info.iloc[0].get("Credits", 3))
        critical_score = count_dependent_courses(course_code, courses_df, dependency_memo)
        
        semester_buckets[sem_num].append({
            "code": course_code,
            "credits": credits,
            "critical_score": critical_score,
            "earliest_sem": sem_num
        })
    
    # Step 3: Schedule courses with credit limits
    # Sort each semester's courses by critical score (descending)
    for sem_num in semester_buckets:
        semester_buckets[sem_num].sort(key=lambda x: x["critical_score"], reverse=True)
    
    # Assign courses to semesters
    for sem_num in sorted(semester_buckets.keys()):
        courses_this_sem = semester_buckets[sem_num]
        current_sem_credits = 0
        deferred = []
        
        for course_data in courses_this_sem:
            course_code = course_data["code"]
            credits = course_data["credits"]
            
            # Try to fit in this semester
            if current_sem_credits + credits <= credit_limit_max:
                projection[course_code] = str(sem_num)
                current_sem_credits += credits
            else:
                # Defer to later semester
                deferred.append(course_data)
        
        # Handle deferred courses - add to next available semester
        if deferred:
            for course_data in deferred:
                # Find next semester with capacity
                placed = False
                for future_sem in range(sem_num + 1, sem_num + 10):  # Look ahead up to 10 semesters
                    if future_sem not in semester_buckets:
                        semester_buckets[future_sem] = []
                    
                    # Check if this semester has capacity
                    future_sem_credits = sum(
                        c["credits"] for c in semester_buckets[future_sem] 
                        if c["code"] in projection and projection[c["code"]] == str(future_sem)
                    )
                    
                    if future_sem_credits + course_data["credits"] <= credit_limit_typical:
                        projection[course_data["code"]] = str(future_sem)
                        semester_buckets[future_sem].append(course_data)
                        placed = True
                        break
                
                if not placed:
                    # If still can't place, mark as flexible
                    earliest = course_data["earliest_sem"]
                    projection[course_data["code"]] = f"{earliest}/{earliest+1}/{earliest+2}"
    
    # Step 4: Mark truly flexible courses (no/minimal dependencies, non-critical path)
    for course_code, sem_str in list(projection.items()):
        if isinstance(sem_str, str) and sem_str.isdigit():
            critical_score = dependency_memo.get(course_code)
            if critical_score is None:
                critical_score = count_dependent_courses(course_code, courses_df, dependency_memo)
            
            if critical_score == 0:
                # Non-critical course - mark as flexible
                sem_num = int(sem_str)
                projection[course_code] = f"{sem_num}/{sem_num+1}/{sem_num+2}"
    
    return projection


def course_projection_view():
    """
    Display course projections for all students - showing when they should take remaining courses.
    """
    st.title("📅 Course Projection View")
    st.markdown("""
    This view shows a **semester-by-semester projection** for when each student should take their remaining courses.
    The projection respects prerequisites, credit limits, and advised courses.
    """)
    
    if "courses_df" not in st.session_state or st.session_state.courses_df is None:
        st.warning("⚠️ Please upload the courses table first.")
        return
    
    if "progress_df" not in st.session_state or st.session_state.progress_df is None:
        st.warning("⚠️ Please upload the progress report first.")
        return
    
    courses_df = st.session_state.courses_df
    progress_df = st.session_state.progress_df.copy()
    
    # Prepare progress data
    progress_df["ID"] = pd.to_numeric(progress_df["ID"], errors="coerce")
    progress_df = progress_df.dropna(subset=["ID"])
    progress_df["ID"] = progress_df["ID"].astype(int)
    
    # Filters
    st.markdown("### 🔍 Filters")
    col1, col2 = st.columns(2)
    
    with col1:
        # Remaining credits filter
        remaining_credits_series = pd.to_numeric(progress_df.get("# Remaining", 0), errors="coerce").fillna(0).astype(int)
        progress_df["Remaining Credits"] = remaining_credits_series
        min_remaining = int(remaining_credits_series.min()) if not remaining_credits_series.empty else 0
        max_remaining = int(remaining_credits_series.max()) if not remaining_credits_series.empty else 0
        
        if min_remaining == max_remaining:
            remaining_range = (min_remaining, max_remaining)
            st.caption(f"All students have {min_remaining} remaining credits.")
        else:
            remaining_range = st.slider(
                "Filter by remaining credits",
                min_value=min_remaining,
                max_value=max_remaining,
                value=(min_remaining, max_remaining)
            )
            progress_df = progress_df[
                (progress_df["Remaining Credits"] >= remaining_range[0]) &
                (progress_df["Remaining Credits"] <= remaining_range[1])
            ]
    
    with col2:
        # Course type filter
        type_filter = st.selectbox(
            "Course Type",
            options=["All Courses", "Required Only", "Intensive Only"],
            help="Filter which courses to show in the projection"
        )
    
    st.markdown("---")
    
    # Build projection table
    st.markdown("### 📊 Projection Table")
    st.markdown("""
    **Legend:**  
    - **c** = Completed  
    - **r** = Registered  
    - **a** = Advised  
    - **1** = Next semester  
    - **2** = 2 semesters out  
    - **3** = 3 semesters out  
    - **1/2/3** = Flexible (can be taken in multiple semesters)  
    - **-** = Not applicable
    """)
    
    # Filter courses by type
    if type_filter == "Required Only":
        filtered_courses = courses_df[courses_df.get("Type", "").str.lower() == "required"]["Course Code"].tolist()
    elif type_filter == "Intensive Only":
        filtered_courses = courses_df[courses_df.get("Type", "").str.lower() == "intensive"]["Course Code"].tolist()
    else:
        filtered_courses = courses_df["Course Code"].tolist()
    
    # Build table data
    table_data = []
    semester_summaries = {}  # student_id -> {sem_num: credits}
    
    for _, student_row in progress_df.iterrows():
        student_id = int(student_row["ID"])
        advised_list = st.session_state.advising_selections.get(student_id, {}).get("advised", []) or []
        
        # Build projection
        projection = build_projection_schedule(student_row, courses_df, advised_list)
        
        row = {
            "Student Name": student_row.get("NAME", ""),
            "ID": student_id,
            "Remaining Credits": student_row.get("Remaining Credits", 0),
        }
        
        # Calculate semester credit summaries
        sem_credits = {}
        for course_code in filtered_courses:
            proj_val = projection.get(course_code, "-")
            row[course_code] = proj_val
            
            # Count credits for projected semesters
            if proj_val and proj_val not in ["c", "r", "a", "-"]:
                course_info = courses_df[courses_df["Course Code"] == course_code]
                if not course_info.empty:
                    credits = int(course_info.iloc[0].get("Credits", 3))
                    
                    if "/" not in proj_val and proj_val.isdigit():
                        sem_num = int(proj_val)
                        sem_credits[sem_num] = sem_credits.get(sem_num, 0) + credits
        
        semester_summaries[student_id] = sem_credits
        
        # Add semester credit columns
        for sem_num in sorted(sem_credits.keys()):
            row[f"Sem {sem_num} Credits"] = sem_credits[sem_num]
        
        table_data.append(row)
    
    if not table_data:
        st.info("No students match the current filters.")
        return
    
    projection_df = pd.DataFrame(table_data)
    
    # Display table with styling
    styled = _style_projection_codes(projection_df, filtered_courses)
    st.dataframe(styled, width="stretch", height=600)
    
    # Display semester credit summaries
    st.markdown("---")
    st.markdown("### 📊 Semester Credit Summary")
    
    for student_id, sem_credits in semester_summaries.items():
        student_name = projection_df[projection_df["ID"] == student_id]["Student Name"].iloc[0] if not projection_df[projection_df["ID"] == student_id].empty else f"Student {student_id}"
        
        if sem_credits:
            summary_text = " | ".join([f"**Sem {sem}:** {credits} credits" for sem, credits in sorted(sem_credits.items())])
            
            # Add warnings for overloaded semesters
            warnings = []
            for sem, credits in sem_credits.items():
                if credits > 18:
                    warnings.append(f"⚠️ Semester {sem} exceeds max (18 credits)")
                elif credits > 17:
                    warnings.append(f"⚠️ Semester {sem} is heavy (>17 credits)")
            
            with st.expander(f"👤 {student_name} (ID: {student_id})", expanded=bool(warnings)):
                st.markdown(summary_text)
                if warnings:
                    for warning in warnings:
                        st.warning(warning)
    
    # Export functionality
    st.markdown("---")
    st.markdown("### 📥 Export")
    
    def _build_export_bytes() -> bytes:
        output = BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            projection_df.to_excel(writer, index=False, sheet_name="Course Projections")
        output.seek(0)
        return output.getvalue()
    
    export_bytes = _build_export_bytes()
    st.download_button(
        label="📥 Download Projection Plan",
        data=export_bytes,
        file_name=f"course_projections_{st.session_state.selected_major}_{st.session_state.selected_period}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
