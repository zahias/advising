# pages/master_plan.py

import streamlit as st
import pandas as pd
from demand_forecaster import DemandForecaster
from curriculum_engine import CurriculumGraph

def render_master_plan():
    st.markdown("## 🌐 Global Master Plan & Curriculum Optimizer")
    st.caption("v2.1.0 - What-If Simulator & Visualizer Active")
    st.markdown("Strategic forecasting of graduation paths and cohort-based demand.")
    
    if "courses_df" not in st.session_state or st.session_state.courses_df.empty:
        st.warning("⚠️ Please upload the Courses Table on the Home page first.")
        return
    
    if "progress_df" not in st.session_state or st.session_state.progress_df.empty:
        st.warning("⚠️ Please upload the Student Progress Report on the Home page first.")
        return

    # Use a copy to avoid mutating session state accidentally
    courses_df = st.session_state.courses_df.copy()
    progress_df = st.session_state.progress_df.copy()
    
    # --- ULTRA-ROBUST COLUMN NORMALIZATION ---
    # We normalize column names to be exactly what the engine expects
    col_map = {str(col).lower().strip(): col for col in courses_df.columns}
    
    # 1. Course Code
    if "course code" not in col_map:
        if "code" in col_map:
            courses_df = courses_df.rename(columns={col_map["code"]: "Course Code"})
        elif "course" in col_map:
             courses_df = courses_df.rename(columns={col_map["course"]: "Course Code"})
             
    # 2. Course Title
    if "course title" not in col_map:
        if "title" in col_map:
            courses_df = courses_df.rename(columns={col_map["title"]: "Course Title"})
        elif "course_title" in col_map:
            courses_df = courses_df.rename(columns={col_map["course_title"]: "Course Title"})

    # 3. Credits
    if "credits" not in col_map and "cr" in col_map:
        courses_df = courses_df.rename(columns={col_map["cr"]: "Credits"})

    # Re-verify critical columns
    if "Course Code" not in courses_df.columns:
        st.error("❌ 'Course Code' column not found in courses table. Please ensure your Excel has a code column.")
        return
    # ----------------------------------------

    # Sidebar-style controls in the main area for planning
    with st.expander("🛠️ Simulation & What-If Configuration", expanded=True):
        col1, col2 = st.columns(2)
        with col1:
            max_credits = st.slider("Max Credits per Semester", 12, 21, 18, help="Capacity limit for simulated students.")
            forecast_semesters = st.slider("Forecast Horizon (Semesters)", 2, 8, 4)
        with col2:
            all_codes = sorted(courses_df["Course Code"].unique())
            unavailable_next = st.multiselect(
                "🚫 Temporarily Cancelled Courses (Next Semester)",
                options=all_codes,
                help="Simulate the impact of NOT offering these courses in the immediate next semester."
            )
            
    # Prepare unavailability dict
    # For now, we only allow cancelling for the immediate next semester (index 1)
    unavail_dict = {1: set(unavailable_next)}

    # Core engine initialization
    with st.spinner("🔮 Running cohort simulations..."):
        forecaster = DemandForecaster(courses_df, progress_df, max_credits_per_sem=max_credits)
        forecaster.run_simulation(semesters_to_forecast=forecast_semesters, unavailable_courses=unavail_dict)
        summary_df = forecaster.get_summary_matrix()
        graph = forecaster.graph

    # Metrics Row
    st.markdown("### 📊 Cohort Health")
    col1, col2, col3 = st.columns(3)
    
    avg_rem = progress_df["# Remaining"].astype(float).mean() if "# Remaining" in progress_df.columns else 0
    bottlenecks = graph.get_top_bottlenecks(10)
    top_bottleneck = bottlenecks[0] if bottlenecks else ("N/A", 0)
    
    with col1:
        st.metric("Avg. Credits Remaining", f"{avg_rem:.1f}")
        st.caption("Institutional baseline")
    with col2:
        st.metric("Primary Bottleneck", top_bottleneck[0])
        st.caption(f"Unlocks {top_bottleneck[1]:.0f} downstream credits")
    with col3:
        total_students = len(progress_df)
        st.metric("Total Cohort Size", total_students)
        st.caption("Active students analyzed")

    st.markdown("---")

    # Dual Column for Heatmap and Visualizer
    col_left, col_right = st.columns([3, 2])

    with col_left:
        st.markdown("### 🗓️ Future Demand Heatmap")
        st.caption("Projected number of students needing each course in future semesters.")
        
        if not summary_df.empty:
            # Style the dataframe like a heatmap
            def style_heatmap(val):
                if val == 0: return ""
                opacity = min(0.1 + (val / total_students) * 0.9, 0.9)
                return f"background-color: rgba(65, 105, 225, {opacity}); color: {'white' if opacity > 0.5 else 'black'}"

            styled_df = summary_df.style.map(style_heatmap)
            st.table(styled_df)
        else:
            st.info("No future demand projected.")

    with col_right:
        st.markdown("### 🕸️ Dependency visualizer")
        st.caption(f"Unlocking path for **{top_bottleneck[0]}**")
        
        if top_bottleneck[0] != "N/A":
            mermaid_code = graph.generate_mermaid_graph(top_bottleneck[0])
            import streamlit.components.v1 as components
            
            # Simple Mermaid rendering via CDN if st.mermaid isn't available
            # Note: We'll use the built-in st.html with mermaid.js for a premium look
            html_code = f"""
            <div class="mermaid" style="display: flex; justify-content: center;">
            {mermaid_code}
            </div>
            <script type="module">
                import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs';
                mermaid.initialize({{ startOnLoad: true, theme: 'neutral' }});
            </script>
            """
            st.components.v1.html(html_code, height=450, scrolling=True)
        else:
            st.info("Select a bottleneck to visualize.")

    # Strategic Action Section
    st.markdown("---")
    colA, colB = st.columns([1, 1])
    
    with colA:
        st.markdown("### 🚀 Strategic Bottlenecks")
        st.caption("Offering these clears the most total graduation barriers.")
        
        bn_data = []
        for code, weight in bottlenecks:
            course_info = courses_df[courses_df["Course Code"] == code]
            title = "Unknown"
            if not course_info.empty:
                row = course_info.iloc[0]
                title = row.get("Course Title", row.get("Title", "Unknown"))
            
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
                status = "✅ High" if count > total_students * 0.4 else "🔹 Normal"
                if code in unavailable_next:
                    status = "🚫 CANCELLED"
                
                rec_data.append({
                    "Course": code, 
                    "Demand": count, 
                    "Status": status
                })
            
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
        5. **What-If Logic**: If you cancel a course, the simulator forces students to pick the next best available course, potentially delaying their graduation.
        """)
