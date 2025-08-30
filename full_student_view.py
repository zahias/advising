# full_student_view.py

import streamlit as st
import pandas as pd
from io import BytesIO
from utils import (
    check_course_completed,
    check_course_registered,
    is_course_offered,
    check_eligibility,
    get_student_standing,
    log_info,
    log_error
)
from reporting import apply_excel_formatting, add_summary_sheet
from google_drive import sync_file_with_drive, initialize_drive_service

def _credits_total(row: pd.Series) -> int:
    cc = row.get("# of Credits Completed", 0)
    cr = row.get("# Registered", 0)
    return int((cc if pd.notna(cc) else 0) + (cr if pd.notna(cr) else 0))

def full_student_view():
    if "progress_df" not in st.session_state or "courses_df" not in st.session_state:
        st.warning("Load data first.")
        return

    st.subheader("Full Student View")
    mode = st.radio("Mode", ["All Students", "Individual Student"], horizontal=True)

    # --- Sidebar course chooser ---
    default_course_cols = st.multiselect(
        "Select course columns to show",
        options=st.session_state.courses_df["Course Code"].tolist(),
        default=st.session_state.courses_df["Course Code"].tolist()[:10],
    )

    if mode == "All Students":
        df = st.session_state.progress_df.copy()
        df["Total Credits Completed"] = df.apply(_credits_total, axis=1)
        df["Standing"] = df["Total Credits Completed"].apply(get_student_standing)
        df["Advising Status"] = df["ID"].astype(str).apply(
            lambda sid: "Advised" if st.session_state.advising_selections.get(str(sid), {}).get("advised") else "Not Advised"
        )

        # Build wide status codes per selected course
        def status_code(student: pd.Series, course: str) -> str:
            sid = str(student["ID"])
            advised = st.session_state.advising_selections.get(sid, {}).get("advised", []) + \
                      st.session_state.advising_selections.get(sid, {}).get("optional", [])
            if check_course_completed(student, course):
                return "c"
            if check_course_registered(student, course):
                return "r"
            if course in advised:
                return "a"
            s, _ = check_eligibility(student, course, advised, st.session_state.courses_df)
            return "na" if s == "Eligible" else "ne"

        for c in default_course_cols:
            df[c] = df.apply(lambda row: status_code(row, c), axis=1)

        base_cols = ["ID", "NAME", "# of Credits Completed", "# Registered", "Total Credits Completed", "Standing", "Advising Status"]
        out_df = df[base_cols + default_course_cols].copy()

        # Color mapping for codes
        def color_status(val):
            if val == "c":
                return "background-color: lightgray"
            if val == "r":
                return "background-color: #BDD7EE"
            if val == "a":
                return "background-color: lightgreen"
            if val == "na":
                return "background-color: #E0FFE0"
            if val == "ne":
                return "background-color: lightcoral"
            return ""

        st.dataframe(out_df.style.applymap(color_status, subset=pd.IndexSlice[:, default_course_cols]), use_container_width=True)

        # Export full report
        st.subheader("Download Full Advising Report")
        output = BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            out_df.to_excel(writer, index=False, sheet_name="Full Report")
            # Add cohort summary sheet
            add_summary_sheet(writer, st.session_state.courses_df, st.session_state.advising_selections, st.session_state.progress_df)
        output.seek(0)
        st.download_button(
            "Download Full Advising Report",
            data=output.getvalue(),
            file_name="Full_Advising_Report.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    else:
        # Individual Student mode
        students = st.session_state.progress_df[["ID", "NAME"]].copy()
        students["label"] = students["ID"].astype(str) + " — " + students["NAME"].astype(str)
        selected = st.selectbox("Select a student", students["label"].tolist())
        sid = selected.split(" — ")[0]
        row = st.session_state.progress_df.loc[st.session_state.progress_df["ID"].astype(str) == sid].iloc[0]
        total = _credits_total(row)
        standing = get_student_standing(total)

        advised = st.session_state.advising_selections.get(sid, {}).get("advised", [])
        optional = st.session_state.advising_selections.get(sid, {}).get("optional", [])
        chosen_cols = st.multiselect("Course columns", options=st.session_state.courses_df["Course Code"].tolist(), default=default_course_cols)

        def status_and_text(course: str):
            if check_course_completed(row, course):
                return "c", "Completed"
            if check_course_registered(row, course):
                return "r", "Registered"
            if course in advised:
                return "a", "Advised"
            s, _ = check_eligibility(row, course, advised + optional, st.session_state.courses_df)
            return ("na", "Eligible not chosen") if s == "Eligible" else ("ne", "Not Eligible")

        records = []
        for c in chosen_cols:
            code, text = status_and_text(c)
            records.append({"Course Code": c, "Status Code": code, "Status": text})
        table = pd.DataFrame(records)

        def color_row(val):
            return {
                "c": "background-color: lightgray",
                "r": "background-color: #BDD7EE",
                "a": "background-color: lightgreen",
                "na": "background-color: #E0FFE0",
                "ne": "background-color: lightcoral",
            }.get(val, "")

        st.dataframe(table.style.applymap(color_row, subset=["Status Code"]), use_container_width=True)

        # Export per-student
        st.subheader("Download Individual Report")
        output = BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            table.to_excel(writer, index=False, sheet_name="Advising Report")
        # Use same headered formatting for consistency
        apply_excel_formatting(
            output,
            row["NAME"],
            row["ID"],
            total,
            standing,
            st.session_state.advising_selections.get(sid, {}).get("note", ""),
            0,
            0,
        )
        output.seek(0)
        st.download_button(
            "Download Individual Report",
            data=output.getvalue(),
            file_name=f'{row["NAME"].replace(" ", "_")}_Advising_Report.xlsx',
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
