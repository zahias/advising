# course_planning_view.py
from __future__ import annotations

import streamlit as st
import pandas as pd
from io import BytesIO
from typing import Dict, List

from course_planning import (
    analyze_course_eligibility_across_students,
    analyze_prerequisite_chains
)
from utils import log_info, log_error
from reporting import apply_excel_formatting


DEFAULT_COURSE_PLANNING_FILTERS = {
    "search_text": "",
    "priority_filter": [],
    "min_eligible": 0,
    "max_eligible": None,
    "min_one_away": 0,
    "max_one_away": None,
    "near_graduation_only": False,
    "critical_only": False,
    "min_credits": 0,
    "max_credits": None,
}


def course_planning_view():
    """
    Course Planning Dashboard - Suggests optimal course offerings each semester
    based on student eligibility, prerequisite chains, and proximity to graduation.
    """
    if "courses_df" not in st.session_state or st.session_state.courses_df.empty:
        st.warning("Courses table not loaded.")
        return
    if "progress_df" not in st.session_state or st.session_state.progress_df.empty:
        st.warning("Progress report not loaded.")
        return
    
    if "confirmed_courses_to_offer" not in st.session_state:
        existing_selection = st.session_state.get("selected_courses_to_offer", [])
        st.session_state.confirmed_courses_to_offer = list(existing_selection)

    if "pending_courses_to_offer" not in st.session_state:
        st.session_state.pending_courses_to_offer = list(st.session_state.confirmed_courses_to_offer)

    # Maintain legacy key for backward compatibility with other modules
    st.session_state.selected_courses_to_offer = list(st.session_state.confirmed_courses_to_offer)
    
    if "course_planning_filters" not in st.session_state:
        st.session_state.course_planning_filters = DEFAULT_COURSE_PLANNING_FILTERS.copy()
    
    st.markdown("## 📊 Course Planning & Optimization")
    st.markdown(
        """
        Plan optimal course offerings by analyzing student eligibility, prerequisite chains, and graduation proximity.
        """
    )
    
    try:
        analysis_df, prereq_analysis = _load_course_planning_analysis(
            st.session_state.courses_df,
            st.session_state.progress_df,
            tuple(st.session_state.confirmed_courses_to_offer),
        )
    except Exception as e:
        st.error(f"Error analyzing courses: {e}")
        log_error("Course planning analysis failed", e)
        return
    
    if analysis_df.empty:
        st.warning("No course data to analyze.")
        return
    
    # Summary Dashboard
    _render_summary_dashboard(analysis_df)
    
    # Main content area with sidebar
    col_main, col_sidebar = st.columns([3, 1])
    
    with col_sidebar:
        _render_filter_sidebar(analysis_df)
        _render_selected_courses_panel(analysis_df)
        _render_quick_actions()
    
    with col_main:
        # Tabs for organized content
        tabs = st.tabs([
            "📋 Course Selection",
            "🔗 Analysis & Insights",
            "📊 Visualizations",
            "💾 Export"
        ])
        
        with tabs[0]:
            _render_course_selection_table(analysis_df)
        
        with tabs[1]:
            _render_analysis_insights(analysis_df, prereq_analysis)
        
        with tabs[2]:
            _render_visualizations(analysis_df, prereq_analysis)
        
        with tabs[3]:
            _render_export_options(analysis_df, prereq_analysis)


def _render_summary_dashboard(analysis_df: pd.DataFrame):
    """Render summary dashboard with key metrics and insights."""
    st.markdown("### 📈 Overview")
    
    # Key metrics
    critical_count = len(analysis_df[analysis_df["Recommendation"].str.contains("🔴 Critical", na=False)])
    high_count = len(analysis_df[analysis_df["Recommendation"].str.contains("🟠 High", na=False)])
    medium_count = len(analysis_df[analysis_df["Recommendation"].str.contains("🟡 Medium", na=False)])
    total_eligible = analysis_df["Currently Eligible"].sum()
    
    # Calculate students near graduation who need courses
    # Keep a running total of students across courses so the metric reflects
    # the actual number of near-grad students rather than just the number of courses
    near_grad_student_total = 0
    for _, row in analysis_df.iterrows():
        eligible_students = row.get("Eligible Students", [])
        one_away = row.get("One Away Details", {})
        near_grad_count = sum(1 for s in eligible_students if s.get("remaining_credits", 999) <= 15)
        near_grad_count += sum(1 for s in one_away.values() if s.get("remaining_credits", 999) <= 15)
        if near_grad_count > 0:
            near_grad_student_total += near_grad_count
    
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric("Total Courses", len(analysis_df))
    with col2:
        st.metric("🔴 Critical", critical_count)
    with col3:
        st.metric("🟠 High Priority", high_count)
    with col4:
        st.metric("Total Eligible", int(total_eligible))
    with col5:
        st.metric("Near Grad Students", near_grad_student_total)
    
    # Simulation status
    confirmed_courses = st.session_state.confirmed_courses_to_offer
    pending_courses = st.session_state.pending_courses_to_offer

    if confirmed_courses:
        st.info(
            "🎯 **Simulating {count} course(s):** {courses}{ellipsis}".format(
                count=len(confirmed_courses),
                courses=", ".join(confirmed_courses[:5]),
                ellipsis="..." if len(confirmed_courses) > 5 else ""
            )
        )

    pending_differs = (
        len(pending_courses) != len(confirmed_courses)
        or set(pending_courses) != set(confirmed_courses)
    )

    if pending_differs:
        st.warning(
            "Pending selection changes not yet applied. Use **Apply Selection** to refresh the simulation results.",
            icon="⚠️",
        )


def _render_filter_sidebar(analysis_df: pd.DataFrame):
    """Render sidebar with filters and quick actions."""
    filters = st.session_state.course_planning_filters

    header_col, reset_col = st.columns([3, 1])
    with header_col:
        st.markdown("### 🔍 Filters")
    with reset_col:
        if st.button("↺ Reset", key="course_planning_reset_filters", help="Restore all filters to their defaults."):
            default_filters = DEFAULT_COURSE_PLANNING_FILTERS.copy()
            filters.clear()
            filters.update(default_filters)
            st.session_state.course_search_filter = default_filters["search_text"]
            st.session_state.priority_filter_select = default_filters["priority_filter"]
            st.rerun()

    # Search
    search_text = st.text_input(
        "Search Course",
        value=filters["search_text"],
        key="course_search_filter",
        placeholder="Course code or title..."
    )
    filters["search_text"] = search_text

    # Priority filter
    priority_options = ["🔴 Critical", "🟠 High Priority", "🟡 Medium Priority", "🟢 Standard", "⚪ Low Priority"]
    priority_filter = st.multiselect(
        "Priority Level",
        priority_options,
        default=filters["priority_filter"],
        key="priority_filter_select"
    )
    filters["priority_filter"] = priority_filter

    max_eligible_default = int(analysis_df["Currently Eligible"].max() or 100)
    max_eligible_default = max(max_eligible_default, filters["min_eligible"])
    max_one_away_default = int(analysis_df["One Course Away"].max() or 100)
    max_one_away_default = max(max_one_away_default, filters["min_one_away"])
    credit_max_from_data = int(analysis_df["Credits"].max() or 0)
    slider_max_value = max(credit_max_from_data, filters.get("max_credits") or credit_max_from_data, filters["min_credits"], 1)
    current_credit_upper = filters.get("max_credits") if filters.get("max_credits") is not None else slider_max_value
    current_credit_upper = max(current_credit_upper, filters["min_credits"])

    with st.expander("Advanced filters"):
        with st.form("advanced_course_filters"):
            st.markdown("**Eligibility Range**")
            col_min, col_max = st.columns(2)
            with col_min:
                min_eligible = st.number_input(
                    "Min Eligible",
                    min_value=0,
                    value=filters["min_eligible"],
                    step=1,
                )
            with col_max:
                max_eligible = st.number_input(
                    "Max Eligible",
                    min_value=0,
                    value=filters.get("max_eligible") or max_eligible_default,
                    step=1,
                )

            st.markdown("**One-Away Range**")
            col_min2, col_max2 = st.columns(2)
            with col_min2:
                min_one_away = st.number_input(
                    "Min One-Away",
                    min_value=0,
                    value=filters["min_one_away"],
                    step=1,
                )
            with col_max2:
                max_one_away = st.number_input(
                    "Max One-Away",
                    min_value=0,
                    value=filters.get("max_one_away") or max_one_away_default,
                    step=1,
                )

            st.markdown("**Student Filters**")
            near_grad_only = st.checkbox(
                "Only courses needed by students ≤15 credits from graduation",
                value=filters["near_graduation_only"],
            )
            critical_only = st.checkbox(
                "Only critical courses (students ≤9 credits)",
                value=filters["critical_only"],
            )

            st.markdown("**Course Credits**")
            credits_range = st.slider(
                "Credits Range",
                min_value=0,
                max_value=slider_max_value,
                value=(filters["min_credits"], current_credit_upper),
            )

            if st.form_submit_button("Apply filters"):
                filters["min_eligible"] = int(min_eligible)
                filters["max_eligible"] = int(max_eligible) if max_eligible > 0 else None
                filters["min_one_away"] = int(min_one_away)
                filters["max_one_away"] = int(max_one_away) if max_one_away > 0 else None
                filters["near_graduation_only"] = bool(near_grad_only)
                filters["critical_only"] = bool(critical_only)
                filters["min_credits"] = int(credits_range[0])
                max_credits_value = int(credits_range[1])
                filters["max_credits"] = None if max_credits_value >= slider_max_value else max_credits_value
                st.rerun()


def _render_quick_actions():
    """Render quick action buttons for bulk selection."""
    st.markdown("### ⚡ Quick Actions")
    
    if st.button("✅ Select All Critical", use_container_width=True):
        # This will be handled in the table rendering
        st.session_state["quick_select_critical"] = True
        st.rerun()
    
    if st.button("📊 Select Top 10 by Priority", use_container_width=True):
        st.session_state["quick_select_top10"] = True
        st.rerun()
    
    if st.button("👥 Select Courses (5+ Eligible)", use_container_width=True):
        st.session_state["quick_select_5plus"] = True
        st.rerun()

    if st.button("🔄 Clear All Selections", width="stretch"):
        st.session_state.pending_courses_to_offer = []
        st.session_state.pop("course_selection_editor", None)
        st.rerun()


def _render_selected_courses_panel(analysis_df: pd.DataFrame):
    """Render panel showing currently confirmed courses."""
    st.markdown("### ✅ Selected Courses")

    confirmed_courses = st.session_state.confirmed_courses_to_offer
    pending_courses = st.session_state.pending_courses_to_offer

    pending_differs = (
        len(pending_courses) != len(confirmed_courses)
        or set(pending_courses) != set(confirmed_courses)
    )

    if not confirmed_courses:
        st.info("No courses confirmed for simulation.")
        if pending_differs:
            st.warning(
                "Pending selection changes not yet applied. Use **Apply Selection** in the Course Selection tab to simulate them.",
                icon="⚠️",
            )
        return

    selected_df = analysis_df[
        analysis_df["Course Code"].isin(confirmed_courses)
    ].copy()

    if selected_df.empty:
        st.info("No courses confirmed for simulation.")
        if pending_differs:
            st.warning(
                "Pending selection changes not yet applied. Use **Apply Selection** in the Course Selection tab to simulate them.",
                icon="⚠️",
            )
        return

    # Aggregate student impact metrics
    unique_students: set[str] = set()
    near_grad_students: set[str] = set()

    for _, row in selected_df.iterrows():
        for student in row.get("Eligible Students", []) or []:
            student_id = str(student.get("id")) if student.get("id") is not None else None
            if student_id:
                unique_students.add(student_id)
                if student.get("remaining_credits", 999) <= 15:
                    near_grad_students.add(student_id)

        for student_id, info in (row.get("One Away Details", {}) or {}).items():
            if student_id:
                unique_students.add(str(student_id))
                if info.get("remaining_credits", 999) <= 15:
                    near_grad_students.add(str(student_id))

    total_courses = len(selected_df)
    total_unique_students = len(unique_students)
    total_near_grad = len(near_grad_students)

    col_courses, col_students, col_near_grad, col_clear = st.columns([1, 1, 1, 0.8])
    with col_courses:
        st.metric("Courses Confirmed", total_courses)
    with col_students:
        st.metric("Unique Students Served", total_unique_students)
    with col_near_grad:
        st.metric("Near-Grad Students", total_near_grad)
    with col_clear:
        if st.button("🧹 Clear All", width="stretch"):
            st.session_state.pending_courses_to_offer = []
            st.session_state.pop("course_selection_editor", None)
            st.rerun()

    table_rows = []

    def _priority_badge(rec_value: str) -> str:
        rec_str = str(rec_value)
        if "🔴" in rec_str:
            return "🔴 Critical"
        if "🟠" in rec_str:
            return "🟠 High"
        if "🟡" in rec_str:
            return "🟡 Medium"
        if "🟢" in rec_str:
            return "🟢 Standard"
        return "⚪ Low"

    for _, row in selected_df.iterrows():
        table_rows.append({
            "Course": row.get("Course Code", ""),
            "Priority": _priority_badge(row.get("Recommendation", "")),
            "Eligible": int(row.get("Currently Eligible", 0) or 0),
        })

    selection_table = pd.DataFrame(table_rows)

    st.dataframe(
        selection_table,
        hide_index=True,
        use_container_width=True,
        height=min(400, 100 + len(selection_table) * 35),
    )

    if pending_differs:
        st.warning(
            "Pending selection changes are not yet simulated. Use **Apply Selection** on the Course Selection tab to update the metrics.",
            icon="⚠️",
        )


def _render_course_selection_table(analysis_df: pd.DataFrame):
    """Render the main course selection table with filters applied."""
    st.markdown("### 📋 Course Selection")
    st.caption("Select rows to add/remove courses from your offering plan. Click column headers to sort.")

    # Apply filters
    filtered_df = _apply_filters(analysis_df)

    if filtered_df.empty:
        st.warning("No courses match the current filters. Adjust your filters to see more results.")
        return

    pending_courses = list(st.session_state.pending_courses_to_offer)
    confirmed_courses = st.session_state.confirmed_courses_to_offer

    # Handle quick actions
    if st.session_state.get("quick_select_critical", False):
        critical_courses = filtered_df[filtered_df["Recommendation"].str.contains("🔴 Critical", na=False)]["Course Code"].tolist()
        updated_pending = pending_courses.copy()
        for course in critical_courses:
            if course not in updated_pending:
                updated_pending.append(course)
        st.session_state.pending_courses_to_offer = updated_pending
        st.session_state["quick_select_critical"] = False
        st.rerun()

    if st.session_state.get("quick_select_top10", False):
        top10 = filtered_df.nlargest(10, "Priority Score")["Course Code"].tolist()
        updated_pending = pending_courses.copy()
        for course in top10:
            if course not in updated_pending:
                updated_pending.append(course)
        st.session_state.pending_courses_to_offer = updated_pending
        st.session_state["quick_select_top10"] = False
        st.rerun()

    if st.session_state.get("quick_select_5plus", False):
        five_plus = filtered_df[filtered_df["Currently Eligible"] >= 5]["Course Code"].tolist()
        updated_pending = pending_courses.copy()
        for course in five_plus:
            if course not in updated_pending:
                updated_pending.append(course)
        st.session_state.pending_courses_to_offer = updated_pending
        st.session_state["quick_select_5plus"] = False
        st.rerun()

    pending_courses = list(st.session_state.pending_courses_to_offer)

    # Prepare display dataframe
    display_df = filtered_df[[
        "Course Code",
        "Course Title",
        "Credits",
        "Currently Eligible",
        "One Course Away",
        "Two+ Courses Away",
        "Priority Score",
        "Impact Score",
        "Recommendation"
    ]].copy()
    
    # Sort by priority score
    display_df = display_df.sort_values("Priority Score", ascending=False)
    
    # Prepare display with selection column
    display_df["Select"] = display_df["Course Code"].isin(pending_courses)
    
    # Add priority emoji column for visual clarity
    def get_priority_emoji(rec):
        rec_str = str(rec)
        if "🔴 Critical" in rec_str:
            return "🔴"
        elif "🟠 High" in rec_str:
            return "🟠"
        elif "🟡 Medium" in rec_str:
            return "🟡"
        elif "🟢 Standard" in rec_str:
            return "🟢"
        return "⚪"
    
    display_df["Priority"] = display_df["Recommendation"].apply(get_priority_emoji)
    
    # Reorder columns
    cols_order = ["Select", "Priority", "Course Code", "Course Title", "Credits", 
                  "Currently Eligible", "One Course Away", "Two+ Courses Away", 
                  "Priority Score", "Impact Score", "Recommendation"]
    display_df = display_df[[c for c in cols_order if c in display_df.columns]]
    
    # Format for better readability
    display_df = display_df.rename(columns={
        "Course Code": "Code",
        "Course Title": "Title",
        "Currently Eligible": "Eligible",
        "One Course Away": "1-Away",
        "Two+ Courses Away": "2+-Away",
        "Priority Score": "Priority Score",
        "Impact Score": "Impact"
    })
    
    # Use data editor for selection
    edited_df = st.data_editor(
        display_df,
        use_container_width=True,
        height=600,
        hide_index=True,
        column_config={
            "Select": st.column_config.CheckboxColumn(
                "Select",
                help="Select courses to offer this semester",
                default=False,
            ),
            "Priority": st.column_config.TextColumn("Priority", width="small"),
            "Code": st.column_config.TextColumn("Code", width="small"),
            "Title": st.column_config.TextColumn("Title", width="medium"),
            "Credits": st.column_config.NumberColumn("Credits", width="small", format="%d"),
            "Eligible": st.column_config.NumberColumn("Eligible", width="small", format="%d"),
            "1-Away": st.column_config.NumberColumn("1-Away", width="small", format="%d"),
            "2+-Away": st.column_config.NumberColumn("2+-Away", width="small", format="%d"),
            "Priority Score": st.column_config.NumberColumn("Priority", width="small", format="%.1f"),
            "Impact": st.column_config.NumberColumn("Impact", width="small", format="%.1f"),
            "Recommendation": st.column_config.TextColumn("Recommendation", width="large"),
        },
        key="course_selection_editor"
    )

    if pending_differs:
        st.warning(
            "Selection changes are pending. Click **Apply Selection** to include them in the simulation metrics.",
            icon="⚠️",
        )

    # Course details expander
    if len(filtered_df) > 0:
        with st.expander("🔍 View Detailed Student Information"):
            selected_course = st.selectbox(
                "Select a course to see detailed student information",
                options=[""] + filtered_df["Course Code"].tolist(),
                key="course_detail_select"
            )
            
            if selected_course:
                course_data = filtered_df[filtered_df["Course Code"] == selected_course].iloc[0]
                _render_course_details(course_data)


def _apply_filters(analysis_df: pd.DataFrame) -> pd.DataFrame:
    """Apply all filters to the analysis dataframe."""
    filters = st.session_state.course_planning_filters
    filtered_df = analysis_df.copy()
    
    # Search filter
    if filters["search_text"]:
        search_lower = filters["search_text"].lower()
        filtered_df = filtered_df[
            filtered_df["Course Code"].str.lower().str.contains(search_lower, na=False) |
            filtered_df["Course Title"].str.lower().str.contains(search_lower, na=False)
        ]
    
    # Priority filter
    if filters["priority_filter"]:
        filtered_df = filtered_df[filtered_df["Recommendation"].apply(
            lambda x: any(p in str(x) for p in filters["priority_filter"])
        )]
    
    # Eligibility range
    if filters["min_eligible"] > 0:
        filtered_df = filtered_df[filtered_df["Currently Eligible"] >= filters["min_eligible"]]
    if filters["max_eligible"]:
        filtered_df = filtered_df[filtered_df["Currently Eligible"] <= filters["max_eligible"]]
    
    # One-away range
    if filters["min_one_away"] > 0:
        filtered_df = filtered_df[filtered_df["One Course Away"] >= filters["min_one_away"]]
    if filters["max_one_away"]:
        filtered_df = filtered_df[filtered_df["One Course Away"] <= filters["max_one_away"]]
    
    # Credits range
    if filters["min_credits"] > 0:
        filtered_df = filtered_df[filtered_df["Credits"] >= filters["min_credits"]]
    if filters["max_credits"]:
        filtered_df = filtered_df[filtered_df["Credits"] <= filters["max_credits"]]
    
    # Student proximity filters
    if filters["near_graduation_only"]:
        def has_near_grad_students(row):
            eligible = row.get("Eligible Students", [])
            one_away = row.get("One Away Details", {})
            near_grad_eligible = any(s.get("remaining_credits", 999) <= 15 for s in eligible)
            near_grad_one_away = any(s.get("remaining_credits", 999) <= 15 for s in one_away.values())
            return near_grad_eligible or near_grad_one_away
        
        filtered_df = filtered_df[filtered_df.apply(has_near_grad_students, axis=1)]
    
    if filters["critical_only"]:
        def has_critical_students(row):
            eligible = row.get("Eligible Students", [])
            one_away = row.get("One Away Details", {})
            critical_eligible = any(s.get("remaining_credits", 999) <= 9 for s in eligible)
            critical_one_away = any(s.get("remaining_credits", 999) <= 9 for s in one_away.values())
            return critical_eligible or critical_one_away
        
        filtered_df = filtered_df[filtered_df.apply(has_critical_students, axis=1)]
    
    return filtered_df


def _render_course_details(course_data: pd.Series):
    """Render detailed student information for a selected course."""
    st.markdown(f"### {course_data['Course Code']}: {course_data['Course Title']}")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### ✅ Currently Eligible Students")
        eligible_students = course_data.get("Eligible Students", [])
        if eligible_students:
            eligible_students_sorted = sorted(
                eligible_students,
                key=lambda x: x.get("remaining_credits", 999)
            )
            for student in eligible_students_sorted:
                remaining = student.get("remaining_credits", "?")
                icon = "🔴" if remaining <= 9 else "🟡" if remaining <= 15 else "🟢"
                st.markdown(f"{icon} **{student['name']}** (ID: {student['id']}) — {remaining} credits remaining")
        else:
            st.info("No students currently eligible")
    
    with col2:
        st.markdown("#### ⏳ One Prerequisite Away")
        one_away = course_data.get("One Away Details", {})
        if one_away:
            for student_id, info in sorted(
                one_away.items(),
                key=lambda x: x[1].get("remaining_credits", 999)
            ):
                remaining = info.get("remaining_credits", "?")
                missing = info.get("missing_prereq", "?")
                icon = "🔴" if remaining <= 9 else "🟡" if remaining <= 15 else "🟢"
                st.markdown(f"{icon} **{info['name']}** (ID: {student_id}) — {remaining} credits remaining")
                st.caption(f"   ↳ Needs: {missing}")
        else:
            st.info("No students one course away")


def _render_analysis_insights(analysis_df: pd.DataFrame, prereq_analysis: dict):
    """Render analysis and insights tab."""
    st.markdown("### 🔗 Prerequisite Chain Analysis")
    st.markdown("Identifies bottleneck courses that unlock many downstream courses and critical path courses needed to prevent delays.")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### 🔓 Bottleneck Courses")
        st.caption("These courses unlock the most downstream courses")
        
        bottlenecks = prereq_analysis.get("bottleneck_courses", [])
        if bottlenecks:
            bottleneck_data = []
            for course_code, downstream_count in bottlenecks[:15]:
                bottleneck_data.append({
                    "Course": course_code,
                    "Unlocks Courses": downstream_count
                })
            st.dataframe(
                pd.DataFrame(bottleneck_data),
                use_container_width=True,
                hide_index=True,
                height=400
            )
        else:
            st.info("No bottleneck courses identified")
    
    with col2:
        st.markdown("#### ⚠️ Critical Path Courses")
        st.caption("Required to prevent delays for students near graduation")
        
        credits_threshold = st.slider(
            "Credits Remaining Threshold",
            min_value=0,
            max_value=60,
            value=15,
            step=3,
            help="Only show courses needed by students with this many or fewer credits remaining",
            key="critical_path_threshold"
        )
        
        critical_paths_raw = prereq_analysis.get("critical_path_courses_detail", [])
        
        if critical_paths_raw:
            filtered_critical = []
            for course_code, students_list in critical_paths_raw:
                filtered_students = [s for s in students_list if s.get("remaining_credits", 999) <= credits_threshold]
                if filtered_students:
                    filtered_critical.append((course_code, len(filtered_students)))
            
            filtered_critical = sorted(filtered_critical, key=lambda x: x[1], reverse=True)
            
            if filtered_critical:
                critical_data = []
                for course_code, student_count in filtered_critical[:15]:
                    critical_data.append({
                        "Course": course_code,
                        f"Students (≤{credits_threshold} cr)": student_count
                    })
                st.dataframe(
                    pd.DataFrame(critical_data),
                    use_container_width=True,
                    hide_index=True,
                    height=400
                )
            else:
                st.info(f"No critical path courses for students with ≤{credits_threshold} credits remaining")
        else:
            critical_paths = prereq_analysis.get("critical_path_courses", [])
            if critical_paths:
                critical_data = []
                for course_code, student_count in critical_paths[:15]:
                    critical_data.append({
                        "Course": course_code,
                        "Students Affected": student_count
                    })
                st.dataframe(
                    pd.DataFrame(critical_data),
                    use_container_width=True,
                    hide_index=True,
                    height=400
                )
            else:
                st.info("No critical path courses identified")
    
    # Top priority courses cards
    st.markdown("---")
    st.markdown("### 🎯 Top Priority Course Recommendations")
    top_courses = analysis_df.sort_values("Priority Score", ascending=False).head(12)
    
    # Display as cards in grid
    cols_per_row = 3
    for i in range(0, len(top_courses), cols_per_row):
        cols = st.columns(cols_per_row)
        for j, (idx, row) in enumerate(top_courses.iloc[i:i+cols_per_row].iterrows()):
            with cols[j]:
                priority_icon = "🔴" if "Critical" in row["Recommendation"] else \
                               "🟠" if "High" in row["Recommendation"] else \
                               "🟡" if "Medium" in row["Recommendation"] else \
                               "🟢" if "Standard" in row["Recommendation"] else "⚪"
                
                with st.container():
                    st.markdown(f"#### {priority_icon} {row['Course Code']}")
                    st.caption(row['Course Title'])
                    st.metric("Eligible", int(row["Currently Eligible"]))
                    st.metric("One-Away", int(row["One Course Away"]))
                    st.caption(f"Priority: {row['Priority Score']:.1f}")
                    
                    course_code = row["Course Code"]
                    pending_courses = st.session_state.pending_courses_to_offer
                    confirmed_courses = st.session_state.confirmed_courses_to_offer

                    if course_code not in pending_courses:
                        if st.button("➕ Add", key=f"quick_add_{course_code}", width="stretch"):
                            updated_pending = pending_courses + [course_code]
                            # Deduplicate while preserving order
                            seen = set()
                            ordered_unique = []
                            for code in updated_pending:
                                if code not in seen:
                                    seen.add(code)
                                    ordered_unique.append(code)
                            st.session_state.pending_courses_to_offer = ordered_unique
                            st.session_state.pop("course_selection_editor", None)
                            st.rerun()
                    else:
                        if course_code in confirmed_courses:
                            st.success("✅ Confirmed")
                        else:
                            st.info("⏳ Pending Apply")


def _render_visualizations(analysis_df: pd.DataFrame, prereq_analysis: dict):
    """Render visualizations tab."""
    st.markdown("### 📊 Visualizations")
    
    # Priority distribution chart
    st.markdown("#### Priority Distribution")
    priority_counts = {
        "Critical": len(analysis_df[analysis_df["Recommendation"].str.contains("🔴 Critical", na=False)]),
        "High": len(analysis_df[analysis_df["Recommendation"].str.contains("🟠 High", na=False)]),
        "Medium": len(analysis_df[analysis_df["Recommendation"].str.contains("🟡 Medium", na=False)]),
        "Standard": len(analysis_df[analysis_df["Recommendation"].str.contains("🟢 Standard", na=False)]),
        "Low": len(analysis_df[analysis_df["Recommendation"].str.contains("⚪ Low", na=False)])
    }
    
    priority_df = pd.DataFrame(list(priority_counts.items()), columns=["Priority", "Count"])
    st.bar_chart(priority_df.set_index("Priority"), use_container_width=True)
    
    # Top courses by priority score
    st.markdown("---")
    st.markdown("#### Top 20 Courses by Priority Score")
    top20 = analysis_df.nlargest(20, "Priority Score")[["Course Code", "Priority Score", "Currently Eligible", "One Course Away"]]
    top20 = top20.set_index("Course Code")
    st.bar_chart(top20[["Priority Score"]], use_container_width=True)
    
    # Eligible vs One-Away scatter
    st.markdown("---")
    st.markdown("#### Eligible Students vs One Course Away")
    scatter_df = analysis_df[["Course Code", "Currently Eligible", "One Course Away", "Priority Score"]].copy()
    scatter_df["Size"] = scatter_df["Priority Score"] * 10  # Scale for visibility
    
    st.scatter_chart(
        scatter_df,
        x="Currently Eligible",
        y="One Course Away",
        size="Size",
        color="Priority Score",
        use_container_width=True
    )
    
    # Bottleneck courses visualization
    st.markdown("---")
    st.markdown("#### Bottleneck Courses (Unlock Count)")
    bottlenecks = prereq_analysis.get("bottleneck_courses", [])
    if bottlenecks:
        bottleneck_df = pd.DataFrame(bottlenecks[:15], columns=["Course", "Unlocks"])
        bottleneck_df = bottleneck_df.set_index("Course")
        st.bar_chart(bottleneck_df, use_container_width=True)


def _render_export_options(analysis_df: pd.DataFrame, prereq_analysis: dict):
    """Render export options for the analysis."""
    st.markdown("### 💾 Export Course Planning Report")
    st.markdown("Download the complete analysis as an Excel file for sharing and record-keeping.")
    
    if st.button("📥 Generate Excel Report", use_container_width=True, type="primary"):
        try:
            output = BytesIO()
            
            export_df = analysis_df[[
                "Course Code",
                "Course Title",
                "Credits",
                "Currently Eligible",
                "One Course Away",
                "Two+ Courses Away",
                "Priority Score",
                "Impact Score",
                "Recommendation"
            ]].copy()
            
            export_df = export_df.sort_values("Priority Score", ascending=False)
            
            with pd.ExcelWriter(output, engine="openpyxl") as writer:
                export_df.to_excel(writer, sheet_name="Course Analysis", index=False)
                
                bottlenecks = prereq_analysis.get("bottleneck_courses", [])
                if bottlenecks:
                    bottleneck_df = pd.DataFrame([
                        {"Course": code, "Unlocks Courses": count}
                        for code, count in bottlenecks
                    ])
                    bottleneck_df.to_excel(writer, sheet_name="Bottleneck Courses", index=False)
                
                critical_paths = prereq_analysis.get("critical_path_courses", [])
                if critical_paths:
                    critical_df = pd.DataFrame([
                        {"Course": code, "Students Affected": count}
                        for code, count in critical_paths
                    ])
                    critical_df.to_excel(writer, sheet_name="Critical Path Courses", index=False)
            
            excel_bytes = output.getvalue()
            
            from advising_period import get_current_period
            current_period = get_current_period()
            semester = current_period.get("semester", "")
            year = current_period.get("year", "")
            major = st.session_state.get("current_major", "")
            filename = f"Course_Planning_{major}_{semester}_{year}.xlsx"
            
            st.download_button(
                label=f"⬇️ Download {filename}",
                data=excel_bytes,
                file_name=filename,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
            
            st.success("✅ Report generated successfully!")
            
        except Exception as e:
            st.error(f"Error generating report: {e}")
            log_error("Course planning export failed", e)
