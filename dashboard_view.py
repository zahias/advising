import streamlit as st
import pandas as pd
from datetime import datetime
from visual_theme import render_glass_card, render_status_badge

def dashboard_view():
    """
    Render the main dashboard home view with high-level stats and quick actions.
    """
    # Get context data
    current_major = st.session_state.get("current_major", "Unknown Major")
    current_period = st.session_state.get("current_period", {})
    advisor_name = current_period.get("advisor_name", "Advisor")
    semester = current_period.get("semester", "")
    year = current_period.get("year", "")
    
    # Get DataFrames
    courses_df = st.session_state.get("courses_df", pd.DataFrame())
    progress_df = st.session_state.get("progress_df", pd.DataFrame())
    
    # Calculate Stats
    total_students = len(progress_df) if not progress_df.empty else 0
    total_courses = len(courses_df) if not courses_df.empty else 0
    
    # Calculate Near Graduation (<= 15 credits ideally, but checking data availability)
    near_grad_count = 0
    if not progress_df.empty and "remaining_credits" in progress_df.columns:
        near_grad_count = len(progress_df[progress_df["remaining_credits"] <= 15])
    
    # Determine Greeting
    hour = datetime.now().hour
    greeting = "Good morning" if hour < 12 else "Good afternoon" if hour < 18 else "Good evening"

    # --- Header Section ---
    st.markdown(f"## {greeting}, {advisor_name.split()[0]} 👋")
    st.caption(f"Here's what's happening in **{current_major}** for **{semester} {year}**.")
    st.markdown("---")

    # --- Top Stats Grid ---
    c1, c2, c3, c4 = st.columns(4)
    
    with c1:
        st.metric("Total Students", total_students, delta=None)
    with c2:
        st.metric("Courses Offered", total_courses, delta=None)
    with c3:
        st.metric("Near Graduation", near_grad_count, help="Students with ≤ 15 credits remaining")
    with c4:
        # Placeholder for sessions today
        st.metric("Advising Sessions", "0", help="Sessions conducted this period (placeholder)")

    st.markdown("### 🚀 Quick Actions")
    
    # --- Quick Actions Row ---
    col_a, col_b, col_c = st.columns(3)
    
    with col_a:
        with st.container():
            st.markdown("#### 🎓 Student Eligibility")
            st.caption("Check course eligibility for all students.")
            if st.button("Check Eligibility", use_container_width=True, key="dash_btn_eligibility"):
                st.session_state["nav_selection"] = "Student Eligibility"
                st.rerun()

    with col_b:
        with st.container():
            st.markdown("#### 🔍 Find Student")
            st.caption("Search and view detailed student profiles.")
            if st.button("Search Students", use_container_width=True, key="dash_btn_search"):
                st.session_state["nav_selection"] = "Full Student View"
                st.rerun()

    with col_c:
        with st.container():
            st.markdown("#### 📊 Course Planning")
            st.caption("Optimize course offerings for the semester.")
            if st.button("Plan Courses", use_container_width=True, key="dash_btn_planning"):
                st.session_state["nav_selection"] = "Course Planning"
                st.rerun()

    # --- Recent Activity / Insights Section ---
    st.markdown("### 📌 Insights")
    
    col_left, col_right = st.columns([2, 1])
    
    with col_left:
        render_glass_card(
            title="System Status",
            subtitle="Data Connectivity",
            content=f"""
            <div style="display: flex; gap: 1rem; align-items: center;">
                <div>
                    <b>Major:</b> {current_major}
                </div>
                <div>
                    <b>Period:</b> {semester} {year}
                </div>
            </div>
            """
        )
    
    with col_right:
         render_glass_card(
            title="Need Help?",
            content="Use the sidebar to navigate or contact support if you encounter issues."
        )

