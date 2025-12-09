# course_offering_planner.py

import streamlit as st
import pandas as pd
from itertools import combinations
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

    st.markdown("## 🎯 Course Offering Planner")
    st.markdown(
        "Data-driven recommendations for which courses to offer based on "
        "graduating students, bottleneck analysis, and cascading eligibility effects."
    )

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
    
    schedule_conflict_insights()


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


def _build_non_conflict_pairs() -> Tuple[List[Dict], Dict[Tuple[str, str], List[str]]]:
    """
    Analyze advised courses (excluding optional) across all students to find
    course pairs that shouldn't conflict in schedule.
    
    Returns:
        - List of pair dicts with counts and flags
        - Dict mapping course pairs to student names
    """
    advising_selections = st.session_state.get("advising_selections", {})
    progress_df = st.session_state.get("progress_df", pd.DataFrame())
    courses_df = st.session_state.get("courses_df", pd.DataFrame())
    
    if progress_df.empty or not advising_selections:
        return [], {}
    
    mutual_pairs = get_mutual_concurrent_pairs(courses_df) if not courses_df.empty else set()
    
    pair_counts: Dict[Tuple[str, str], int] = {}
    pair_students: Dict[Tuple[str, str], List[str]] = {}
    
    for student_id, selections in advising_selections.items():
        advised = selections.get("advised", [])
        optional = selections.get("optional", [])
        
        advised_only = [c for c in advised if c not in optional]
        
        if len(advised_only) < 2:
            continue
        
        try:
            sid_int = int(student_id)
            student_rows = progress_df.loc[progress_df["ID"] == sid_int]
            if student_rows.empty:
                student_name = str(student_id)
            else:
                first_name = str(student_rows.iloc[0].get("First Name", ""))
                last_name = str(student_rows.iloc[0].get("Last Name", ""))
                student_name = f"{first_name} {last_name}".strip() or str(student_id)
        except (ValueError, TypeError):
            student_name = str(student_id)
        
        for course_a, course_b in combinations(sorted(advised_only), 2):
            pair_key = (course_a, course_b)
            pair_counts[pair_key] = pair_counts.get(pair_key, 0) + 1
            if pair_key not in pair_students:
                pair_students[pair_key] = []
            pair_students[pair_key].append(student_name)
    
    results = []
    for pair_key, count in sorted(pair_counts.items(), key=lambda x: -x[1]):
        course_a, course_b = pair_key
        
        is_mutual = pair_key in mutual_pairs or (course_b, course_a) in mutual_pairs
        
        results.append({
            "Course A": course_a,
            "Course B": course_b,
            "# Students": count,
            "Students": ", ".join(pair_students[pair_key]),
            "Coreq/Concurrent": "Yes" if is_mutual else "",
        })
    
    return results, pair_students


def schedule_conflict_insights():
    """
    Render Schedule Conflict Insights section showing course pairs that shouldn't
    conflict based on advised courses (not optional).
    """
    st.markdown("---")
    st.markdown("### 📅 Schedule Conflict Insights")
    st.markdown(
        "Based on advised courses (excluding optional), these course pairs are being taken together "
        "by students and **should not conflict** in the schedule."
    )
    
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
    cache_key = f"_conflict_pairs_cache_{major}"
    
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
    
    if not cache_valid:
        pair_data, pair_students = _build_non_conflict_pairs()
        st.session_state[cache_key] = {"pairs": pair_data, "students": pair_students}
        st.session_state[version_key] = version_hash
    
    cached = st.session_state[cache_key]
    pair_data = cached["pairs"]
    
    if not pair_data:
        st.info("No course pairs found. Students need to be advised for 2+ courses to see pairs.")
        return
    
    col_filter, col_refresh = st.columns([3, 1])
    with col_filter:
        min_students = st.slider(
            "Minimum students per pair",
            min_value=1,
            max_value=max(p["# Students"] for p in pair_data),
            value=1,
            help="Filter to show only pairs advised for at least this many students"
        )
    with col_refresh:
        if st.button("🔄 Refresh Data", key="refresh_conflict_pairs"):
            pair_data, pair_students = _build_non_conflict_pairs()
            st.session_state[cache_key] = {"pairs": pair_data, "students": pair_students}
            st.session_state[version_key] = version_hash
            st.rerun()
    
    filtered_pairs = [p for p in pair_data if p["# Students"] >= min_students]
    
    if not filtered_pairs:
        st.info(f"No pairs meet the minimum of {min_students} students.")
        return
    
    st.markdown(f"**{len(filtered_pairs)} course pairs** should not conflict:")
    
    display_df = pd.DataFrame(filtered_pairs)
    st.dataframe(display_df, width="stretch", height=min(400, 50 + len(filtered_pairs) * 35))
    
    def _build_csv() -> bytes:
        output = BytesIO()
        df_export = pd.DataFrame(filtered_pairs)
        df_export.to_csv(output, index=False)
        return output.getvalue()
    
    st.download_button(
        label="📥 Download CSV",
        data=_build_csv(),
        file_name=f"schedule_conflict_pairs_{major}.csv",
        mime="text/csv",
        key="download_conflict_pairs"
    )
