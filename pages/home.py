import streamlit as st
import pandas as pd
from datetime import datetime

def render_home():
    """Render the Home dashboard with KPIs and quick actions."""
    
    st.markdown("## Dashboard Overview")
    
    progress_df = st.session_state.get("progress_df", pd.DataFrame())
    courses_df = st.session_state.get("courses_df", pd.DataFrame())
    advising_selections = st.session_state.get("advising_selections", {})
    
    has_data = not progress_df.empty and not courses_df.empty
    
    if not has_data:
        st.info("Upload your data files in the **Setup** tab to get started.")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Students", "—")
        with col2:
            st.metric("Courses", "—")
        with col3:
            st.metric("Advised", "—")
        return
    
    total_students = len(progress_df)
    total_courses = len(courses_df)
    
    advised_count = 0
    not_advised_count = 0
    for _, row in progress_df.iterrows():
        sid = row.get("ID", 0)
        sel = advising_selections.get(int(sid)) or advising_selections.get(str(int(sid))) or {}
        if sel.get("advised") or sel.get("optional") or sel.get("repeat") or sel.get("note", "").strip():
            advised_count += 1
        else:
            not_advised_count += 1
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Students", total_students)
    
    with col2:
        st.metric("Advised", advised_count, delta=f"{advised_count}/{total_students}")
    
    with col3:
        st.metric("Not Advised", not_advised_count)
    
    with col4:
        pct = int((advised_count / total_students * 100)) if total_students > 0 else 0
        st.metric("Progress", f"{pct}%")
    
    st.markdown("---")
    
    col_left, col_right = st.columns([2, 1])
    
    with col_left:
        st.markdown("### Quick Actions")
        
        action_col1, action_col2, action_col3 = st.columns(3)
        
        with action_col1:
            if st.button("Start Advising", type="primary"):
                st.session_state["nav_selection"] = "Workspace"
                st.rerun()
        
        with action_col2:
            if st.button("View All Students"):
                st.session_state["nav_selection"] = "Insights"
                st.rerun()
        
        with action_col3:
            if st.button("Course Planning"):
                st.session_state["nav_selection"] = "Insights"
                st.session_state["insights_tab"] = "Planner"
                st.rerun()
    
    with col_right:
        st.markdown("### Graduating Soon")
        
        if "# Remaining" in progress_df.columns or "Remaining Credits" in progress_df.columns:
            remaining_col = "Remaining Credits" if "Remaining Credits" in progress_df.columns else "# Remaining"
            graduating = progress_df[pd.to_numeric(progress_df[remaining_col], errors="coerce").fillna(999) <= 36]
            
            graduating_not_advised = []
            for _, row in graduating.iterrows():
                sid = row.get("ID", 0)
                sel = advising_selections.get(int(sid)) or advising_selections.get(str(int(sid))) or {}
                if not (sel.get("advised") or sel.get("optional") or sel.get("note", "").strip()):
                    graduating_not_advised.append(row.get("NAME", "Unknown"))
            
            if graduating_not_advised:
                st.warning(f"{len(graduating_not_advised)} graduating students need advising")
                for name in graduating_not_advised[:5]:
                    st.caption(f"• {name}")
                if len(graduating_not_advised) > 5:
                    st.caption(f"... and {len(graduating_not_advised) - 5} more")
            else:
                st.success("All graduating students advised!")
        else:
            st.info("No remaining credits data")
    
    st.markdown("---")
    
    st.markdown("### Recent Activity")
    
    recent_advised = []
    for sid, sel in advising_selections.items():
        if sel.get("advised"):
            try:
                student_row = progress_df[progress_df["ID"] == int(sid)]
                if not student_row.empty:
                    name = student_row.iloc[0].get("NAME", "Unknown")
                    recent_advised.append({
                        "name": name,
                        "courses": len(sel.get("advised", [])),
                        "optional": len(sel.get("optional", []))
                    })
            except:
                pass
    
    if recent_advised:
        for item in recent_advised[:5]:
            st.caption(f"• {item['name']}: {item['courses']} courses advised" + 
                      (f" (+{item['optional']} optional)" if item['optional'] else ""))
    else:
        st.caption("No advising activity yet this session")
