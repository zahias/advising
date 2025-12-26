# pages/master_plan.py

import streamlit as st
import pandas as pd
from demand_forecaster import DemandForecaster
from curriculum_engine import CurriculumGraph

def render_master_plan():
    st.markdown("## 🌐 Global Master Plan & Curriculum Optimizer")
    st.markdown("Strategic forecasting of graduation paths and cohort-based demand.")
    
    if "courses_df" not in st.session_state or st.session_state.courses_df.empty:
        st.warning("⚠️ Please upload the Courses Table on the Home page first.")
        return
    
    if "progress_df" not in st.session_state or st.session_state.progress_df.empty:
        st.warning("⚠️ Please upload the Student Progress Report on the Home page first.")
        return

    courses_df = st.session_state.courses_df
    progress_df = st.session_state.progress_df
    
    # Sidebar-style controls in the main area for planning
    with st.expander("🛠️ Simulation Configuration", expanded=False):
        col1, col2 = st.columns(2)
        with col1:
            max_credits = st.slider("Max Credits per Semester", 12, 21, 18)
        with col2:
            forecast_semesters = st.slider("Forecast Horizon (Semesters)", 2, 8, 4)

    # Core engine initialization
    with st.spinner("🔮 Running cohort simulations..."):
        forecaster = DemandForecaster(courses_df, progress_df, max_credits_per_sem=max_credits)
        forecaster.run_simulation(semesters_to_forecast=forecast_semesters)
        summary_df = forecaster.get_summary_matrix()
        graph = forecaster.graph

    # Metrics Row
    st.markdown("### 📊 Cohort Health")
    col1, col2, col3 = st.columns(3)
    
    avg_rem = progress_df["# Remaining"].astype(float).mean() if "# Remaining" in progress_df.columns else 0
    top_bottleneck = graph.get_top_bottlenecks(1)[0] if graph.get_top_bottlenecks(1) else ("N/A", 0)
    
    with col1:
        st.metric("Avg. Credits Remaining", f"{avg_rem:.1f}")
        st.caption("Lower is closer to graduation")
    with col2:
        st.metric("Primary Bottleneck", top_bottleneck[0])
        st.caption(f"Unlocks {top_bottleneck[1]:.0f} downstream credits")
    with col3:
        total_students = len(progress_df)
        st.metric("Total Cohort Size", total_students)
        st.caption("Active students analyzed")

    st.markdown("---")

    # Heatmap Section
    st.markdown("### 🗓️ Future Demand Heatmap")
    st.caption("Projected number of students needing each course in future semesters based on prerequisite chains.")
    
    if not summary_df.empty:
        # Style the dataframe like a heatmap
        def style_heatmap(val):
            if val == 0: return ""
            # Higher demand gets darker color
            opacity = min(0.1 + (val / total_students) * 0.9, 0.9)
            return f"background-color: rgba(65, 105, 225, {opacity}); color: {'white' if opacity > 0.5 else 'black'}"

        styled_df = summary_df.style.map(style_heatmap)
        st.dataframe(styled_df, width="stretch", height=500)
    else:
        st.info("No future demand projected. All students might be finished or prerequisites are missing.")

    # Strategic Action Section
    st.markdown("---")
    colA, colB = st.columns([1, 1])
    
    with colA:
        st.markdown("### 🚀 Strategic Bottlenecks")
        st.caption("Courses with high 'Unlock Weight'. Offering these clears the most graduation barriers.")
        bottlenecks = graph.get_top_bottlenecks(10)
        
        bn_data = []
        for code, weight in bottlenecks:
            course_info = courses_df[courses_df["Course Code"] == code]
            if not course_info.empty:
                row = course_info.iloc[0]
                title = row.get("Course Title", row.get("Title", "Unknown"))
            else:
                title = "Unknown"
            bn_data.append(
                {"Course": code, "Impact Score": f"{weight:.0f}", "Description": title}
            )
        
        st.table(bn_data)

    with colB:
        st.markdown("### 💡 Recommended Next Offerings")
        st.caption("Highest demand courses for next semester (Sem +1).")
        
        if 1 in forecaster.demand_projection:
            next_sem = forecaster.demand_projection[1]
            sorted_next = sorted(next_sem.items(), key=lambda x: x[1], reverse=True)
            
            rec_data = []
            for code, count in sorted_next[:10]:
                rec_data.append({"Course": code, "Projected Demand": count, "Priority": "🔥 High" if count > total_students * 0.5 else "✅ Normal"})
            
            st.table(rec_data)
        else:
            st.info("No recommendations available.")

    st.markdown("---")
    with st.expander("ℹ️ How this Optimizer works"):
        st.markdown("""
        1. **Dependency Analysis**: Builds a graph of prerequisites from your Courses table.
        2. **Greedy Pathfinding**: For every student, it pretends they register for up to their credit limit in the *next* semester, always picking the courses that unlock the most downstream content first.
        3. **Simulation**: It repeats this until the student graduates or the horizon is reached.
        4. **Aggregation**: It sums up these "virtual registrations" to predict institutional demand.
        """)
