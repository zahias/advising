# full_student_view.py

import streamlit as st
import pandas as pd
from io import BytesIO
from utils import (
    check_course_completed,
    check_course_registered,
    check_eligibility,
    get_student_standing,
    style_df,          # kept (used elsewhere in app)
    log_info,
    log_error
)
from google_drive import sync_file_with_drive, initialize_drive_service
from reporting import add_summary_sheet, apply_full_report_formatting, apply_individual_compact_formatting

# -----------------------------
# Color map (aligned with Advising table)
# -----------------------------
_CODE_COLORS = {
    "c":  "#C6E0B4",   # Completed -> light green
    "r":  "#BDD7EE",   # Registered -> light blue
    "a":  "#FFF2CC",   # Advised -> light yellow
    "na": "#E1F0FF",   # Eligible not chosen -> light blue-tint
    "ne": "#F8CECC",   # Not Eligible -> light red
}

def _style_codes(df: pd.DataFrame, code_cols: list[str]) -> "pd.io.formats.style.Styler":
    """
    Return a Styler that colors the code columns based on _CODE_COLORS.
    Works for both All Students (many rows) and Individual Student (one row).
    """
    def _bg(v):
        col = _CODE_COLORS.get(str(v).strip().lower())
        return f"background-color: {col}" if col else ""
    styler = df.style
    if code_cols:
        styler = styler.applymap(_bg, subset=code_cols)
    return styler

def full_student_view():
    """
    Two modes:
      - All Students (wide table with compact status codes)
      - Individual Student (subset + export)
    """
    if "courses_df" not in st.session_state or st.session_state.courses_df.empty:
        st.warning("Courses table not loaded.")
        return
    if "progress_df" not in st.session_state or st.session_state.progress_df.empty:
        st.warning("Progress report not loaded.")
        return
    if "advising_selections" not in st.session_state:
        st.session_state.advising_selections = {}

    tab = st.tabs(["All Students", "Individual Student"])
    with tab[0]:
        _render_all_students()
    with tab[1]:
        _render_individual_student()

def _render_all_students():
    df = st.session_state.progress_df.copy()
    # Compute derived columns
    df["Total Credits Completed"] = df.get("# of Credits Completed", 0).fillna(0).astype(float) + \
                                    df.get("# Registered", 0).fillna(0).astype(float)
    df["Standing"] = df["Total Credits Completed"].apply(get_student_standing)
    df["Advising Status"] = df["ID"].apply(lambda sid: "Advised" if st.session_state.advising_selections.get(int(sid), {}).get("advised") else "Not Advised")

    available_courses = st.session_state.courses_df["Course Code"].tolist()
    selected_courses = st.multiselect("Select course columns", options=available_courses, default=available_courses)

    # Build compact status codes
    def status_code(row, course):
        if check_course_completed(row, course):
            return "c"
        if check_course_registered(row, course):
            return "r"
        sel = st.session_state.advising_selections.get(int(row["ID"]), {})
        advised = (sel.get("advised", []) or []) + (sel.get("optional", []) or [])
        if course in advised:
            return "a"
        stt, _ = check_eligibility(row, course, advised, st.session_state.courses_df)
        return "na" if stt == "Eligible" else "ne"

    for c in selected_courses:
        df[c] = df.apply(lambda r, cc=c: status_code(r, cc), axis=1)

    display_cols = ["ID", "NAME", "Total Credits Completed", "Standing", "Advising Status"] + selected_courses

    # Show table with legend (now color-coded)
    st.write("*Legend:* c=Completed, r=Registered, a=Advised, na=Eligible not chosen, ne=Not Eligible")
    styled = _style_codes(df[display_cols], selected_courses)
    st.dataframe(styled, use_container_width=True, height=600)

    # Export full advising report with summary + COLORS in Excel
    if st.button("Download Full Advising Report"):
        output = BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            df[display_cols].to_excel(writer, index=False, sheet_name="Full Report")
            add_summary_sheet(writer, df[display_cols], selected_courses)
        # Apply color formatting to code columns in the saved workbook
        apply_full_report_formatting(output=output, sheet_name="Full Report", course_cols=selected_courses)
        st.download_button(
            "Download Excel",
            data=output.getvalue(),
            file_name="Full_Advising_Report.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

def _render_individual_student():
    students_df = st.session_state.progress_df.copy()
    students_df["DISPLAY"] = students_df["NAME"].astype(str) + " — " + students_df["ID"].astype(str)
    choice = st.selectbox("Select a student", students_df["DISPLAY"].tolist(), key="full_single_select")
    sid = int(students_df.loc[students_df["DISPLAY"] == choice, "ID"].iloc[0])
    row = students_df.loc[students_df["ID"] == sid].iloc[0]

    # Expose selection for other panels (e.g. sessions default)
    st.session_state["current_student_id"] = sid

    available_courses = st.session_state.courses_df["Course Code"].tolist()
    selected_courses = st.multiselect("Select Courses", options=available_courses, default=available_courses, key="indiv_courses")

    # Build status codes for this student
    data = {"ID": [sid], "NAME": [row["NAME"]]}
    for c in selected_courses:
        if check_course_completed(row, c):
            data[c] = ["c"]
        elif check_course_registered(row, c):
            data[c] = ["r"]
        else:
            sel = st.session_state.advising_selections.get(sid, {})
            advised = (sel.get("advised", []) or []) + (sel.get("optional", []) or [])
            if c in advised:
                data[c] = ["a"]
            else:
                stt, _ = check_eligibility(row, c, advised, st.session_state.courses_df)
                data[c] = ["na" if stt == "Eligible" else "ne"]
    indiv_df = pd.DataFrame(data)

    st.write("*Legend:* c=Completed, r=Registered, a=Advised, na=Eligible not chosen, ne=Not Eligible")
    styled = _style_codes(indiv_df, selected_courses)
    st.dataframe(styled, use_container_width=True)

    # Download colored sheet for this student
    if st.button("Download Individual Report"):
        output = BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            indiv_df.to_excel(writer, index=False, sheet_name="Student")
        # Add colors to the code cells
        apply_individual_compact_formatting(output=output, sheet_name="Student", course_cols=selected_courses)
        st.download_button(
            "Download Excel",
            data=output.getvalue(),
            file_name=f"Student_{sid}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    # (The bulk download block remains as in your version; unchanged)
