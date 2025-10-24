"""
Smart Student Search Component
Replaces dropdown with searchable interface, fuzzy matching, filters, and recent students.
"""

import streamlit as st
import pandas as pd
from typing import Optional, List, Tuple
from difflib import SequenceMatcher


def render_student_search(view_key: str = "default") -> Optional[int]:
    """
    Render smart student search bar with fuzzy search, filters, and recents.
    
    Args:
        view_key: Unique key to differentiate between views (e.g., "eligibility", "full_view")
    
    Returns:
        Selected student ID (int) or None if no student selected
    """
    if "progress_df" not in st.session_state or st.session_state.progress_df.empty:
        st.warning("No student data loaded.")
        return None
    
    _initialize_recent_students()
    
    students_df = st.session_state.progress_df.copy()
    
    students_df["Total Credits"] = (
        students_df.get("# of Credits Completed", 0).fillna(0).astype(float) +
        students_df.get("# Registered", 0).fillna(0).astype(float)
    )
    
    from utils import get_student_standing
    students_df["Standing"] = students_df["Total Credits"].apply(get_student_standing)
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        search_query = st.text_input(
            "🔍 Search student by name or ID",
            placeholder="Start typing to search...",
            key=f"student_search_{view_key}",
            help="Type student name or ID to filter results"
        )
    
    with col2:
        standing_filter = st.multiselect(
            "Filter by Standing",
            options=["Freshman", "Sophomore", "Junior", "Senior"],
            key=f"standing_filter_{view_key}",
            help="Filter students by academic standing"
        )
    
    filtered_df = students_df.copy()
    
    if search_query:
        query_lower = search_query.lower()
        
        def fuzzy_score(row) -> float:
            """
            Calculate fuzzy match score for a student.
            Returns score from 0-1, where 1 is perfect match.
            Uses SequenceMatcher for fuzzy matching.
            """
            name = str(row["NAME"]).lower()
            student_id = str(row["ID"]).lower()
            
            name_ratio = SequenceMatcher(None, query_lower, name).ratio()
            
            name_contains = query_lower in name
            id_contains = query_lower in student_id
            id_exact = query_lower == student_id
            
            if id_exact:
                return 1.0
            elif id_contains:
                return 0.95
            elif name_contains:
                return 0.9
            elif name_ratio > 0.6:
                return name_ratio
            else:
                return 0.0
        
        filtered_df["_fuzzy_score"] = filtered_df.apply(fuzzy_score, axis=1)
        
        filtered_df = filtered_df[filtered_df["_fuzzy_score"] > 0.5]
        
        filtered_df = filtered_df.sort_values("_fuzzy_score", ascending=False)
        
        filtered_df = filtered_df.drop(columns=["_fuzzy_score"])
    
    if standing_filter:
        filtered_df = filtered_df[filtered_df["Standing"].isin(standing_filter)]
    
    if filtered_df.empty:
        st.info("No students match your search criteria.")
        return None
    
    recent_students = st.session_state.get("recent_students", [])
    
    if recent_students and not search_query and not standing_filter:
        st.markdown("**Recently Viewed:**")
        recent_cols = st.columns(min(len(recent_students), 5))
        for idx, recent_id in enumerate(recent_students[:5]):
            recent_row = students_df[students_df["ID"] == recent_id]
            if not recent_row.empty:
                recent_name = recent_row.iloc[0]["NAME"]
                with recent_cols[idx]:
                    if st.button(
                        f"{recent_name}",
                        key=f"recent_{recent_id}_{view_key}",
                        use_container_width=True
                    ):
                        _update_recent_students(recent_id)
                        return recent_id
        
        st.markdown("---")
    
    filtered_df["DISPLAY"] = (
        filtered_df["NAME"].astype(str) + 
        " — ID: " + 
        filtered_df["ID"].astype(str) + 
        " (" + 
        filtered_df["Standing"].astype(str) + 
        ")"
    )
    
    if len(filtered_df) <= 10 or search_query:
        st.markdown(f"**{len(filtered_df)} student(s) found:**")
        
        for _, row in filtered_df.iterrows():
            col_btn, col_info = st.columns([2, 1])
            with col_btn:
                if st.button(
                    f"👤 {row['DISPLAY']}",
                    key=f"select_{row['ID']}_{view_key}",
                    use_container_width=True
                ):
                    _update_recent_students(row['ID'])
                    return int(row['ID'])
            with col_info:
                advised = st.session_state.advising_selections.get(int(row['ID']), {}).get("advised", [])
                status = "✅ Advised" if advised else "⏳ Not Advised"
                st.caption(status)
        
        return None
    else:
        options = filtered_df["DISPLAY"].tolist()
        
        selection_key = f"student_select_{view_key}"
        if selection_key not in st.session_state:
            st.session_state[selection_key] = options[0] if options else ""
        
        if st.session_state[selection_key] not in options:
            st.session_state[selection_key] = options[0] if options else ""
        
        selected = st.selectbox(
            f"Select from {len(filtered_df)} students",
            options=options,
            index=options.index(st.session_state[selection_key]) if st.session_state[selection_key] in options else 0,
            key=f"student_selectbox_{view_key}",
        )
        
        st.session_state[selection_key] = selected
        
        selected_id = int(filtered_df.loc[filtered_df["DISPLAY"] == selected, "ID"].iloc[0])
        _update_recent_students(selected_id)
        
        return selected_id


def _initialize_recent_students():
    """Initialize recent students list in session state."""
    if "recent_students" not in st.session_state:
        st.session_state.recent_students = []


def _update_recent_students(student_id: int):
    """Add student to recent list (max 10)."""
    if "recent_students" not in st.session_state:
        st.session_state.recent_students = []
    
    recent = st.session_state.recent_students
    
    if student_id in recent:
        recent.remove(student_id)
    
    recent.insert(0, student_id)
    
    st.session_state.recent_students = recent[:10]
