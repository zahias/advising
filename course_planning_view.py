# course_planning_view.py
from __future__ import annotations

import streamlit as st
import pandas as pd
from io import BytesIO

from course_planning import (
    analyze_course_eligibility_across_students,
    analyze_prerequisite_chains
)
from utils import log_info, log_error
from reporting import apply_excel_formatting


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
    
    if "selected_courses_to_offer" not in st.session_state:
        st.session_state.selected_courses_to_offer = []
    
    st.markdown("## 📊 Course Planning & Optimization")
    st.markdown(
        """
        This tool helps you plan optimal course offerings for the semester by analyzing:
        - **Current student eligibility** for each course
        - **Students who are 1-2 prerequisites away** from becoming eligible
        - **Graduation proximity** - prioritizing students close to degree completion
        - **Prerequisite chains** - identifying bottleneck and critical path courses
        - **Interactive simulation** - Select courses to offer and see live eligibility updates
        """
    )
    
    st.markdown("#### 🎯 Course Selection Simulator")
    if st.session_state.selected_courses_to_offer:
        st.info(f"**Simulating {len(st.session_state.selected_courses_to_offer)} selected course(s):** {', '.join(st.session_state.selected_courses_to_offer)}")
        st.caption("_Assuming all eligible students will take these courses, eligibility for other courses updates automatically._")
    else:
        st.caption("_Select courses below to simulate their impact on student eligibility for other courses._")
    
    col_reset, col_spacer = st.columns([1, 3])
    with col_reset:
        if st.button("🔄 Clear Selection", width="stretch"):
            for course_code in st.session_state.selected_courses_to_offer:
                checkbox_key = f"offer_{course_code}"
                if checkbox_key in st.session_state:
                    del st.session_state[checkbox_key]
            st.session_state.selected_courses_to_offer = []
            st.rerun()
    
    with st.spinner("Analyzing course eligibility across all students..."):
        log_info("Running course eligibility analysis")
        try:
            analysis_df = analyze_course_eligibility_across_students(
                st.session_state.courses_df,
                st.session_state.progress_df,
                st.session_state.selected_courses_to_offer
            )
            
            prereq_analysis = analyze_prerequisite_chains(
                st.session_state.courses_df,
                st.session_state.progress_df
            )
        except Exception as e:
            st.error(f"Error analyzing courses: {e}")
            log_error("Course planning analysis failed", e)
            return
    
    if analysis_df.empty:
        st.warning("No course data to analyze.")
        return
    
    st.success(f"✅ Analyzed {len(analysis_df)} courses across {len(st.session_state.progress_df)} students")
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        critical_count = len(analysis_df[analysis_df["Recommendation"].str.contains("🔴 Critical")])
        st.metric("🔴 Critical Priority", critical_count)
    with col2:
        high_count = len(analysis_df[analysis_df["Recommendation"].str.contains("🟠 High")])
        st.metric("🟠 High Priority", high_count)
    with col3:
        medium_count = len(analysis_df[analysis_df["Recommendation"].str.contains("🟡 Medium")])
        st.metric("🟡 Medium Priority", medium_count)
    with col4:
        total_eligible = analysis_df["Currently Eligible"].sum()
        st.metric("Total Eligible Students", int(total_eligible))
    
    st.markdown("---")
    
    tabs = st.tabs([
        "📋 Course Analysis Table",
        "🔗 Prerequisite Chains",
        "📈 Priority Courses",
        "💾 Export Report"
    ])
    
    with tabs[0]:
        _render_course_analysis_table(analysis_df)
    
    with tabs[1]:
        _render_prerequisite_chains(prereq_analysis)
    
    with tabs[2]:
        _render_priority_courses(analysis_df)
    
    with tabs[3]:
        _render_export_options(analysis_df, prereq_analysis)


def _render_course_analysis_table(analysis_df: pd.DataFrame):
    """Render the main course analysis table with filters and sorting."""
    st.markdown("### 📋 Interactive Course Offering Analysis")
    st.markdown("Select courses to offer and watch eligibility update in real-time. Click column headers to sort.")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        priority_filter = st.multiselect(
            "Filter by Priority",
            ["🔴 Critical", "🟠 High Priority", "🟡 Medium Priority", "🟢 Standard", "⚪ Low Priority"],
            default=[]
        )
    
    with col2:
        min_eligible = st.number_input("Min Currently Eligible", min_value=0, value=0, step=1)
    
    with col3:
        min_one_away = st.number_input("Min One Course Away", min_value=0, value=0, step=1)
    
    filtered_df = analysis_df.copy()
    
    if priority_filter:
        filtered_df = filtered_df[filtered_df["Recommendation"].apply(
            lambda x: any(p in x for p in priority_filter)
        )]
    
    if min_eligible > 0:
        filtered_df = filtered_df[filtered_df["Currently Eligible"] >= min_eligible]
    
    if min_one_away > 0:
        filtered_df = filtered_df[filtered_df["One Course Away"] >= min_one_away]
    
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
    
    display_df = display_df.sort_values("Priority Score", ascending=False)
    
    st.markdown("#### Select Courses to Offer")
    st.caption("Check courses you plan to offer this semester. Eligibility will update assuming all eligible students take these courses.")
    
    for idx, row in display_df.iterrows():
        course_code = row["Course Code"]
        col_check, col_info = st.columns([0.5, 9.5])
        
        with col_check:
            is_selected = course_code in st.session_state.selected_courses_to_offer
            if st.checkbox(f"Offer {course_code}", value=is_selected, key=f"offer_{course_code}", label_visibility="collapsed"):
                if course_code not in st.session_state.selected_courses_to_offer:
                    st.session_state.selected_courses_to_offer.append(course_code)
                    st.rerun()
            else:
                if course_code in st.session_state.selected_courses_to_offer:
                    st.session_state.selected_courses_to_offer.remove(course_code)
                    st.rerun()
        
        with col_info:
            badge = "✅ SELECTED" if is_selected else ""
            st.markdown(
                f"**{course_code}** - {row['Course Title']} ({row['Credits']} cr) {badge}  \n"
                f"📊 Eligible: **{row['Currently Eligible']}** | 1-Away: **{row['One Course Away']}** | "
                f"2+ Away: **{row['Two+ Courses Away']}** | Priority: **{row['Priority Score']:.1f}**  \n"
                f"{row['Recommendation']}"
            )
            st.markdown("---")
    
    with st.expander("🔍 View Detailed Student Information"):
        selected_course = st.selectbox(
            "Select a course to see detailed student information",
            options=filtered_df["Course Code"].tolist(),
            key="course_detail_select"
        )
        
        if selected_course:
            course_data = filtered_df[filtered_df["Course Code"] == selected_course].iloc[0]
            
            st.markdown(f"### {selected_course}: {course_data['Course Title']}")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("#### ✅ Currently Eligible Students")
                eligible_students = course_data["Eligible Students"]
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
                one_away = course_data["One Away Details"]
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


def _render_prerequisite_chains(prereq_analysis: dict):
    """Render prerequisite chain analysis."""
    st.markdown("### Prerequisite Chain Analysis")
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
                width="stretch",
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
            help="Only show courses needed by students with this many or fewer credits remaining"
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
                    width="stretch",
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
                    width="stretch",
                    hide_index=True,
                    height=400
                )
            else:
                st.info("No critical path courses identified")


def _render_priority_courses(analysis_df: pd.DataFrame):
    """Render prioritized course recommendations."""
    st.markdown("### 🎯 Priority Course Recommendations")
    st.markdown("Top courses to offer this semester, ranked by priority score.")
    
    top_courses = analysis_df.sort_values("Priority Score", ascending=False).head(20)
    
    for idx, row in top_courses.iterrows():
        priority_icon = "🔴" if "Critical" in row["Recommendation"] else \
                       "🟠" if "High" in row["Recommendation"] else \
                       "🟡" if "Medium" in row["Recommendation"] else \
                       "🟢" if "Standard" in row["Recommendation"] else "⚪"
        
        with st.expander(f"{priority_icon} **{row['Course Code']}: {row['Course Title']}** (Priority: {row['Priority Score']})"):
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Currently Eligible", int(row["Currently Eligible"]))
            with col2:
                st.metric("One Course Away", int(row["One Course Away"]))
            with col3:
                st.metric("Impact Score", row["Impact Score"])
            
            st.markdown(f"**Recommendation:** {row['Recommendation']}")
            
            eligible_count = int(row["Currently Eligible"])
            one_away_count = int(row["One Course Away"])
            
            if eligible_count > 0:
                st.success(f"✅ {eligible_count} students can take this course now")
            if one_away_count > 0:
                st.info(f"⏳ {one_away_count} students would become eligible if prerequisites are offered")


def _render_export_options(analysis_df: pd.DataFrame, prereq_analysis: dict):
    """Render export options for the analysis."""
    st.markdown("### 💾 Export Course Planning Report")
    st.markdown("Download the complete analysis as an Excel file for sharing and record-keeping.")
    
    if st.button("📥 Generate Excel Report", width="stretch", type="primary"):
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
                width="stretch"
            )
            
            st.success("✅ Report generated successfully!")
            
        except Exception as e:
            st.error(f"Error generating report: {e}")
            log_error("Course planning export failed", e)
