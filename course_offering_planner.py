# course_offering_planner.py

import streamlit as st
import pandas as pd
from typing import Dict, List, Tuple, Set
from io import BytesIO
from utils import (
    check_course_completed,
    check_course_registered,
    check_eligibility,
    get_mutual_concurrent_pairs,
    parse_requirements,
    build_requisites_str,
)


def course_offering_planner():
    """
    Course Offering Planner - Smart recommendation engine for semester course planning.
    Analyzes graduating students, bottlenecks, eligible counts, and cascading eligibility.
    """
    if "courses_df" not in st.session_state or st.session_state.courses_df.empty:
        st.warning("Courses table not loaded.")
        return
    if "progress_df" not in st.session_state or st.session_state.progress_df.empty:
        st.warning("Progress report not loaded.")
        return

    with st.expander("Course Offering Planner", expanded=False):
        st.markdown(
            "Data-driven recommendations for which courses to offer based on "
            "graduating students, bottleneck analysis, and cascading eligibility effects."
        )
        _render_course_offering_planner_content()
    
    schedule_conflict_insights()


def _render_course_offering_planner_content():
    """Internal function to render the Course Offering Planner content."""
    courses_df = st.session_state.courses_df
    progress_df = st.session_state.progress_df.copy()

    # Prepare student data
    progress_df["ID"] = pd.to_numeric(progress_df["ID"], errors="coerce")
    progress_df = progress_df.dropna(subset=["ID"])
    progress_df["ID"] = progress_df["ID"].astype(int)

    # Calculate remaining credits
    progress_df["Remaining Credits"] = pd.to_numeric(
        progress_df.get("# Remaining", 0), errors="coerce"
    ).fillna(0).astype(int)

    # Get all courses
    all_courses = courses_df["Course Code"].dropna().unique().tolist()

    # --- Analysis Parameters ---
    col_params1, col_params2 = st.columns(2)
    with col_params1:
        graduation_threshold = st.slider(
            "🎓 Graduating Soon Threshold (Remaining Credits)",
            min_value=0,
            max_value=60,
            value=30,
            step=5,
            help="Students with this many or fewer remaining credits are considered 'graduating soon'"
        )
    
    with col_params2:
        min_eligible_students = st.slider(
            "👥 Minimum Eligible Students",
            min_value=1,
            max_value=20,
            value=3,
            help="Only recommend courses with at least this many eligible students"
        )

    st.markdown("---")

    # --- Core Analysis ---
    with st.spinner("Analyzing course recommendations..."):
        recommendations = _analyze_course_recommendations(
            courses_df,
            progress_df,
            all_courses,
            graduation_threshold,
            min_eligible_students
        )

    if not recommendations:
        st.info("No course recommendations found with current parameters. Try adjusting the filters.")
        return

    # Sort by priority score
    sorted_recs = sorted(recommendations, key=lambda x: x["priority_score"], reverse=True)

    # --- Top Recommendations ---
    st.markdown("### 🏆 Top 10 Recommended Courses")
    
    top_10 = sorted_recs[:10]
    for idx, rec in enumerate(top_10, 1):
        _render_course_card(rec, idx)

    st.markdown("---")

    # --- All Recommendations Table ---
    st.markdown("### 📊 All Course Recommendations")
    
    # Build summary table
    summary_data = []
    for rec in sorted_recs:
        summary_data.append({
            "Rank": rec["rank"],
            "Course": rec["course"],
            "Priority Score": f"{rec['priority_score']:.1f}",
            "Currently Eligible": rec["currently_eligible"],
            "Graduating Students": rec["graduating_students"],
            "Bottleneck Score": rec["bottleneck_score"],
            "Cascading Eligible": rec["cascading_eligible"],
            "Reason": rec["reason"]
        })
    
    summary_df = pd.DataFrame(summary_data)
    st.dataframe(summary_df, width="stretch", height=400)

    # --- Course Selection ---
    st.markdown("---")
    st.markdown("### ✅ Select Courses to Offer")
    
    if "selected_offerings" not in st.session_state:
        st.session_state.selected_offerings = []
    
    course_options = [rec["course"] for rec in sorted_recs]
    
    selected = st.multiselect(
        "Choose courses for this semester",
        options=course_options,
        default=st.session_state.selected_offerings,
        help="Select the courses you plan to offer based on the recommendations above"
    )
    
    if st.button("💾 Save Course Offerings", type="primary"):
        st.session_state.selected_offerings = selected
        st.success(f"✅ Saved {len(selected)} courses for offering: {', '.join(selected)}")
        
        # Show impact summary
        total_eligible = sum(rec["currently_eligible"] for rec in sorted_recs if rec["course"] in selected)
        total_graduating = sum(rec["graduating_students"] for rec in sorted_recs if rec["course"] in selected)
        
        st.info(
            f"**Impact Summary:** This offering will directly serve {total_eligible} currently eligible students, "
            f"including {total_graduating} students who are graduating soon."
        )


def _analyze_course_recommendations(
    courses_df: pd.DataFrame,
    progress_df: pd.DataFrame,
    all_courses: List[str],
    graduation_threshold: int,
    min_eligible: int
) -> List[Dict]:
    """
    Analyze all courses and return prioritized recommendations.
    """
    recommendations = []
    
    # Build prerequisite dependency map (what courses unlock)
    prereq_map = _build_prerequisite_map(courses_df)
    
    # Calculate mutual pairs once for efficiency
    mutual_pairs = get_mutual_concurrent_pairs(courses_df)
    
    for course in all_courses:
        course_info = courses_df.loc[courses_df["Course Code"] == course]
        if course_info.empty:
            continue
        
        course_row = course_info.iloc[0]
        
        # Skip if already offered everywhere
        # (You might want to adjust this logic based on your needs)
        
        # Count eligible students
        eligible_students = []
        graduating_students = []
        
        for _, student in progress_df.iterrows():
            sid = int(student["ID"])
            remaining = student.get("Remaining Credits", 999)
            
            # Check if already completed or registered
            if check_course_completed(student, course) or check_course_registered(student, course):
                continue
            
            # Check eligibility
            status, _ = check_eligibility(
                student,
                course,
                [],  # No advised courses for this analysis
                courses_df,
                registered_courses=[],
                ignore_offered=True,
                mutual_pairs=mutual_pairs
            )
            
            if status == "Eligible":
                eligible_students.append(sid)
                if remaining <= graduation_threshold:
                    graduating_students.append(sid)
        
        currently_eligible = len(eligible_students)
        
        # Skip if below minimum threshold
        if currently_eligible < min_eligible:
            continue
        
        # Calculate bottleneck score (how many downstream courses this unlocks)
        bottleneck_score = len(prereq_map.get(course, []))
        
        # Calculate cascading eligibility (students who would become eligible for other courses)
        cascading_eligible = _calculate_cascading_eligibility(
            course,
            eligible_students,
            progress_df,
            courses_df,
            prereq_map
        )
        
        # Calculate priority score
        priority_score = (
            (currently_eligible * 1.0) +              # Base: number of eligible students
            (len(graduating_students) * 3.0) +        # 3x weight for graduating students
            (bottleneck_score * 2.0) +                # 2x weight for bottleneck courses
            (cascading_eligible * 1.5)                # 1.5x weight for cascading effects
        )
        
        # Build recommendation reason
        reason_parts = []
        if len(graduating_students) > 0:
            reason_parts.append(f"{len(graduating_students)} graduating")
        if bottleneck_score > 0:
            reason_parts.append(f"unlocks {bottleneck_score} courses")
        if cascading_eligible > 0:
            reason_parts.append(f"+{cascading_eligible} cascading eligible")
        
        reason = "; ".join(reason_parts) if reason_parts else "General progression"
        
        recommendations.append({
            "course": course,
            "priority_score": priority_score,
            "currently_eligible": currently_eligible,
            "graduating_students": len(graduating_students),
            "bottleneck_score": bottleneck_score,
            "cascading_eligible": cascading_eligible,
            "reason": reason,
            "requisites": build_requisites_str(course_row)
        })
    
    # Add rank
    sorted_recs = sorted(recommendations, key=lambda x: x["priority_score"], reverse=True)
    for idx, rec in enumerate(sorted_recs, 1):
        rec["rank"] = idx
    
    return sorted_recs


def _build_prerequisite_map(courses_df: pd.DataFrame) -> Dict[str, List[str]]:
    """
    Build a map of course -> list of courses it is a prerequisite for.
    This helps identify bottleneck courses.
    """
    prereq_map = {}
    
    for _, course_row in courses_df.iterrows():
        course_code = course_row.get("Course Code")
        if pd.isna(course_code):
            continue
        
        # Check what this course is a prerequisite for
        prereqs = parse_requirements(course_row.get("Prerequisite", ""))
        concurrent = parse_requirements(course_row.get("Concurrent", ""))
        coreqs = parse_requirements(course_row.get("Corequisite", ""))
        
        all_reqs = set(prereqs + concurrent + coreqs)
        
        for req_course in all_reqs:
            if req_course not in prereq_map:
                prereq_map[req_course] = []
            prereq_map[req_course].append(course_code)
    
    return prereq_map


def _calculate_cascading_eligibility(
    course: str,
    eligible_student_ids: List[int],
    progress_df: pd.DataFrame,
    courses_df: pd.DataFrame,
    prereq_map: Dict[str, List[str]]
) -> int:
    """
    Calculate how many additional students would become eligible for OTHER courses
    if the eligible students take this course.
    """
    # Get courses that have this course as a prerequisite/concurrent/corequisite
    downstream_courses = prereq_map.get(course, [])
    
    if not downstream_courses:
        return 0
    
    cascading_count = 0
    mutual_pairs = get_mutual_concurrent_pairs(courses_df)
    
    for downstream_course in downstream_courses:
        for sid in eligible_student_ids:
            student_row = progress_df.loc[progress_df["ID"] == sid]
            if student_row.empty:
                continue
            
            student_row = student_row.iloc[0]
            
            # Check if they'd be eligible for downstream course AFTER taking this course
            # This is a simplified check - in reality you'd simulate completion
            status_before, _ = check_eligibility(
                student_row,
                downstream_course,
                [],
                courses_df,
                registered_courses=[],
                ignore_offered=True,
                mutual_pairs=mutual_pairs
            )
            
            status_after, _ = check_eligibility(
                student_row,
                downstream_course,
                [],
                courses_df,
                registered_courses=[course],  # Simulate having taken the prerequisite
                ignore_offered=True,
                mutual_pairs=mutual_pairs
            )
            
            # If they weren't eligible before but are now, count it
            if status_before != "Eligible" and status_after == "Eligible":
                cascading_count += 1
    
    return cascading_count


def _render_course_card(rec: Dict, rank: int):
    """
    Render a visually appealing card for a course recommendation.
    """
    # Determine color based on priority
    if rank <= 3:
        border_color = "#28a745"  # Green for top 3
    elif rank <= 7:
        border_color = "#ffc107"  # Yellow for 4-7
    else:
        border_color = "#6c757d"  # Gray for rest
    
    st.markdown(
        f"""
        <div style="border-left: 5px solid {border_color}; padding: 15px; margin-bottom: 15px; background-color: #f8f9fa; border-radius: 5px;">
            <h4 style="margin: 0 0 10px 0;">#{rank} - {rec['course']}</h4>
            <p style="margin: 5px 0; color: #666;"><strong>Priority Score:</strong> {rec['priority_score']:.1f}</p>
            <p style="margin: 5px 0;"><strong>Reason:</strong> {rec['reason']}</p>
        </div>
        """,
        unsafe_allow_html=True
    )
    
    # Metrics in columns
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Currently Eligible", rec["currently_eligible"])
    with col2:
        st.metric("Graduating Students", rec["graduating_students"])
    with col3:
        st.metric("Unlocks Courses", rec["bottleneck_score"])
    with col4:
        st.metric("Cascading Impact", rec["cascading_eligible"])
    
    # Show requisites
    if rec["requisites"]:
        st.caption(f"📋 {rec['requisites']}")


def _get_student_name(student_id, progress_df) -> str:
    """Helper to get student name from progress_df."""
    try:
        sid_int = int(student_id)
        student_rows = progress_df.loc[progress_df["ID"] == sid_int]
        if student_rows.empty:
            return str(student_id)
        else:
            first_name = str(student_rows.iloc[0].get("First Name", ""))
            last_name = str(student_rows.iloc[0].get("Last Name", ""))
            return f"{first_name} {last_name}".strip() or str(student_id)
    except (ValueError, TypeError):
        return str(student_id)


def _build_all_course_combinations() -> Tuple[List[Dict], int]:
    """
    Analyze advised courses (excluding optional) across all students to find
    all unique course combinations (2+ courses) that shouldn't conflict in schedule.
    
    Merges subset combinations into their smallest superset:
    - If student A has [X,Y,Z] and student B has [X,Y], B counts toward [X,Y,Z]
    - Only shows "maximal" sets (sets that aren't subsets of other sets)
    
    Returns:
        - List of dicts with courses, course count, student count, student names, and coreq flag
        - Total number of students processed
    """
    major = st.session_state.get("current_major", "")
    if major and "majors" in st.session_state and major in st.session_state.majors:
        advising_selections = st.session_state.majors[major].get("advising_selections", {})
    else:
        advising_selections = st.session_state.get("advising_selections", {})
    progress_df = st.session_state.get("progress_df", pd.DataFrame())
    courses_df = st.session_state.get("courses_df", pd.DataFrame())
    
    if progress_df.empty or not advising_selections:
        return [], 0
    
    mutual_pairs = get_mutual_concurrent_pairs(courses_df) if not courses_df.empty else set()
    
    raw_combinations: Dict[Tuple[str, ...], List[str]] = {}
    students_processed = 0
    
    for student_id, selections in advising_selections.items():
        advised = selections.get("advised", [])
        optional = selections.get("optional", [])
        
        advised_only = sorted([c for c in advised if c not in optional])
        
        if len(advised_only) < 2:
            continue
        
        students_processed += 1
        student_name = _get_student_name(student_id, progress_df)
        
        combo_key = tuple(advised_only)
        if combo_key not in raw_combinations:
            raw_combinations[combo_key] = []
        raw_combinations[combo_key].append(student_name)
    
    if not raw_combinations:
        return [], students_processed
    
    all_combos = list(raw_combinations.keys())
    
    superset_map: Dict[Tuple[str, ...], Tuple[str, ...]] = {}
    
    for combo in all_combos:
        combo_set = set(combo)
        supersets_at_min_size = []
        min_size = float('inf')
        
        for other in all_combos:
            if other == combo:
                continue
            other_set = set(other)
            if combo_set.issubset(other_set):
                if len(other) < min_size:
                    min_size = len(other)
                    supersets_at_min_size = [other]
                elif len(other) == min_size:
                    supersets_at_min_size.append(other)
        
        if len(supersets_at_min_size) == 1:
            superset_map[combo] = supersets_at_min_size[0]
    
    def find_final_target(combo: Tuple[str, ...]) -> Tuple[str, ...]:
        visited = set()
        current = combo
        while current in superset_map and current not in visited:
            visited.add(current)
            current = superset_map[current]
        return current
    
    merged_data: Dict[Tuple[str, ...], List[str]] = {}
    
    for combo, students in raw_combinations.items():
        target = find_final_target(combo)
        if target not in merged_data:
            merged_data[target] = []
        merged_data[target].extend(students)
    
    results = []
    for combo_key, students in sorted(merged_data.items(), key=lambda x: (-len(x[1]), -len(x[0]))):
        courses_list = list(combo_key)
        has_coreq = False
        for i, c1 in enumerate(courses_list):
            for c2 in courses_list[i+1:]:
                if (c1, c2) in mutual_pairs or (c2, c1) in mutual_pairs:
                    has_coreq = True
                    break
            if has_coreq:
                break
        
        results.append({
            "Courses": ", ".join(combo_key),
            "# Courses": len(combo_key),
            "# Students": len(students),
            "Students": ", ".join(students),
            "Has Coreq": "Yes" if has_coreq else "",
        })
    
    return results, students_processed


def schedule_conflict_insights():
    """
    Render Schedule Conflict Insights section showing all course combinations
    that shouldn't conflict based on advised courses (not optional).
    """
    st.markdown("---")
    with st.expander("Schedule Conflict Insights", expanded=False):
        st.markdown(
            "Based on advised courses (excluding optional), these course combinations are being taken together "
            "by students and **should not conflict** in the schedule."
        )
        _render_schedule_conflict_content()


def _render_schedule_conflict_content():
    """Internal function to render Schedule Conflict Insights content."""
    
    major = st.session_state.get("current_major", "")
    if major and "majors" in st.session_state and major in st.session_state.majors:
        advising_selections = st.session_state.majors[major].get("advising_selections", {})
    else:
        advising_selections = st.session_state.get("advising_selections", {})
    if not advising_selections:
        st.info("No advising sessions found. Advise students first to see schedule conflict insights.")
        return
    
    def _count_non_optional_advised(sel: dict) -> int:
        advised = sel.get("advised", [])
        optional = sel.get("optional", [])
        return len([c for c in advised if c not in optional])
    
    students_with_advised = sum(
        1 for sel in advising_selections.values() 
        if _count_non_optional_advised(sel) >= 2
    )
    
    if students_with_advised == 0:
        st.info("No students have been advised for 2+ non-optional courses yet. Schedule conflict data requires students with multiple advised courses (excluding optional).")
        return
    
    major = st.session_state.get("current_major", "")
    cache_key = f"_conflict_combos_cache_{major}"
    
    all_advised_courses = []
    for sid, sel in sorted(advising_selections.items(), key=lambda x: str(x[0])):
        advised = sel.get("advised", [])
        optional = sel.get("optional", [])
        advised_only = sorted([c for c in advised if c not in optional])
        all_advised_courses.append(f"{sid}:{','.join(advised_only)}")
    version_hash = hash(tuple(all_advised_courses))
    
    version_key = f"{cache_key}_version"
    
    cache_valid = (
        cache_key in st.session_state
        and st.session_state.get(version_key) == version_hash
    )
    
    students_processed_key = f"{cache_key}_students_processed"
    
    if not cache_valid:
        combo_data, students_processed = _build_all_course_combinations()
        st.session_state[cache_key] = combo_data
        st.session_state[students_processed_key] = students_processed
        st.session_state[version_key] = version_hash
    
    combo_data = st.session_state[cache_key]
    students_processed = st.session_state.get(students_processed_key, 0)
    
    st.caption(f"Students processed (with 2+ non-optional advised courses): **{students_processed}**")
    
    if not combo_data:
        st.info("No course combinations found. Students need to be advised for 2+ non-optional courses.")
        return
    
    max_students = max(c["# Students"] for c in combo_data) if combo_data else 1
    max_courses = max(c["# Courses"] for c in combo_data) if combo_data else 2
    
    col_filter1, col_filter2, col_refresh = st.columns([2, 2, 1])
    with col_filter1:
        min_students = st.slider(
            "Minimum students",
            min_value=1,
            max_value=max_students,
            value=1,
            help="Filter to show only combinations with at least this many students",
            key="min_students_combos"
        )
    with col_filter2:
        min_courses = st.slider(
            "Minimum courses",
            min_value=2,
            max_value=max_courses,
            value=2,
            help="Filter to show only combinations with at least this many courses",
            key="min_courses_combos"
        )
    with col_refresh:
        st.write("")
        if st.button("Refresh", key="refresh_conflict_combos"):
            combo_data, students_processed = _build_all_course_combinations()
            st.session_state[cache_key] = combo_data
            st.session_state[students_processed_key] = students_processed
            st.session_state[version_key] = version_hash
            st.rerun()
    
    filtered = [
        c for c in combo_data 
        if c["# Students"] >= min_students and c["# Courses"] >= min_courses
    ]
    
    if not filtered:
        st.info(f"No combinations meet the minimum of {min_students} students and {min_courses} courses.")
    else:
        st.markdown(f"**{len(filtered)} course combinations** should not conflict:")
        
        display_df = pd.DataFrame(filtered)
        st.dataframe(
            display_df, 
            width="stretch", 
            height=min(400, 50 + len(filtered) * 35),
            column_config={
                "Courses": st.column_config.TextColumn("Courses", width="large"),
            }
        )
        
        def _build_csv() -> bytes:
            output = BytesIO()
            df_export = pd.DataFrame(filtered)
            df_export.to_csv(output, index=False)
            return output.getvalue()
        
        st.download_button(
            label="Download CSV",
            data=_build_csv(),
            file_name=f"schedule_conflict_combinations_{major}.csv",
            mime="text/csv",
            key="download_conflict_combos"
        )
