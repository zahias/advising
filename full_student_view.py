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
    "o":  "#FFE699",   # Optional -> light orange
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
    df["Advising Status"] = df["ID"].apply(
        lambda sid: "Advised" if st.session_state.advising_selections.get(int(sid), {}).get("advised") else "Not Advised"
    )

    available_courses = st.session_state.courses_df["Course Code"].tolist()
    selected_courses = st.multiselect("Select course columns", options=available_courses, default=available_courses)

    # Build compact status codes (includes Optional = 'o')
    def status_code(row, course):
        sid = int(row["ID"])
        sel = st.session_state.advising_selections.get(sid, {})
        advised_list = sel.get("advised", []) or []
        optional_list = sel.get("optional", []) or []

        if check_course_completed(row, course):
            return "c"
        if check_course_registered(row, course):
            return "r"
        if course in optional_list:
            return "o"
        if course in advised_list:
            return "a"

        stt, _ = check_eligibility(row, course, advised_list, st.session_state.courses_df)
        return "na" if stt == "Eligible" else "ne"

    for c in selected_courses:
        df[c] = df.apply(lambda r, cc=c: status_code(r, cc), axis=1)

    display_cols = ["ID", "NAME", "Total Credits Completed", "Standing", "Advising Status"] + selected_courses

    # Show table (color-coded)
    st.write("*Legend:* c=Completed, r=Registered, a=Advised, o=Optional, na=Eligible not chosen, ne=Not Eligible")
    styled = _style_codes(df[display_cols], selected_courses)
    st.dataframe(styled, use_container_width=True, height=600)

    # Export full advising report with summary + COLORS in Excel
    if st.button("Download Full Advising Report"):
        output = BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            df[display_cols].to_excel(writer, index=False, sheet_name="Full Report")
            add_summary_sheet(writer, df[display_cols], selected_courses)  # includes Optional (o)
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

    # IMPORTANT: do NOT overwrite st.session_state["current_student_id"] here.
    # Eligibility view is the single source of truth for the "current student"
    # used by autosave and the sessions panel.

    available_courses = st.session_state.courses_df["Course Code"].tolist()
    selected_courses = st.multiselect("Select Courses", options=available_courses, default=available_courses, key="indiv_courses")

    # Build status codes for this student (includes Optional = 'o')
    data = {"ID": [sid], "NAME": [row["NAME"]]}
    sel = st.session_state.advising_selections.get(sid, {})
    advised_list = sel.get("advised", []) or []
    optional_list = sel.get("optional", []) or []

    for c in selected_courses:
        if check_course_completed(row, c):
            data[c] = ["c"]
        elif check_course_registered(row, c):
            data[c] = ["r"]
        elif c in optional_list:
            data[c] = ["o"]
        elif c in advised_list:
            data[c] = ["a"]
        else:
            stt, _ = check_eligibility(row, c, advised_list, st.session_state.courses_df)
            data[c] = ["na" if stt == "Eligible" else "ne"]

    indiv_df = pd.DataFrame(data)
    st.write("*Legend:* c=Completed, r=Registered, a=Advised, o=Optional, na=Eligible not chosen, ne=Not Eligible")
    styled = _style_codes(indiv_df, selected_courses)
    st.dataframe(styled, use_container_width=True)

    # Download colored sheet for this student (compact codes)
    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("Download Individual Report"):
            output = BytesIO()
            with pd.ExcelWriter(output, engine="openpyxl") as writer:
                indiv_df.to_excel(writer, index=False, sheet_name="Student")
            apply_individual_compact_formatting(output=output, sheet_name="Student", course_cols=selected_courses)
            st.download_button(
                "Download Excel",
                data=output.getvalue(),
                file_name=f"Student_{sid}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
    
    with col2:
        # Email advising sheet to student
        if st.button("📧 Email Advising Sheet", key=f"email_indiv_{sid}"):
            from email_manager import get_student_email, send_advising_email
            
            student_email = get_student_email(str(sid))
            if not student_email:
                st.error(f"No email address found for student {sid}. Please upload email roster first.")
            else:
                # Get selection data
                note = sel.get("note", "")
                
                # Send email
                success, message = send_advising_email(
                    to_email=student_email,
                    student_name=str(row["NAME"]),
                    student_id=str(sid),
                    advised_courses=advised_list,
                    optional_courses=optional_list,
                    note=note,
                    courses_df=st.session_state.courses_df,
                )
                
                if success:
                    st.success(f"✅ {message}")
                else:
                    st.error(f"❌ {message}")

    # Download sheets for all advised students into one workbook + sync to Drive (unchanged)
    if st.button("Download All Advised Students Reports"):
        all_sel = [(int(k), v) for k, v in st.session_state.advising_selections.items() if v.get("advised")]
        if not all_sel:
            st.info("No advised students found.")
            return
        output = BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            for sid_, sel_ in all_sel:
                srow = st.session_state.progress_df.loc[st.session_state.progress_df["ID"] == sid_].iloc[0]
                data_rows = {"Course Code": [], "Action": [], "Eligibility Status": [], "Justification": []}
                for cc in st.session_state.courses_df["Course Code"]:
                    status, just = check_eligibility(srow, cc, sel_.get("advised", []), st.session_state.courses_df)
                    if check_course_completed(srow, cc):
                        action = "Completed"; status = "Completed"
                    elif check_course_registered(srow, cc):
                        action = "Registered"
                    elif cc in sel_.get("advised", []):
                        action = "Advised"
                    else:
                        action = "Eligible not chosen" if status == "Eligible" else "Not Eligible"
                    data_rows["Course Code"].append(cc)
                    data_rows["Action"].append(action)
                    data_rows["Eligibility Status"].append(status)
                    data_rows["Justification"].append(just)
                pd.DataFrame(data_rows).to_excel(writer, index=False, sheet_name=str(sid_))
            # Add an index sheet
            index_df = st.session_state.progress_df.loc[
                st.session_state.progress_df["ID"].isin([sid for sid,_ in all_sel]),
                ["ID", "NAME"]
            ]
            index_df.to_excel(writer, index=False, sheet_name="Index")

        st.download_button(
            "Download All (Excel)",
            data=output.getvalue(),
            file_name="All_Advised_Students.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

        # Drive sync preserved
        try:
            service = initialize_drive_service()
            sync_file_with_drive(
                service=service,
                file_content=output.getvalue(),
                drive_file_name="All_Advised_Students.xlsx",
                mime_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                parent_folder_id=st.secrets["google"]["folder_id"],
            )
            st.success("✅ All Advised Students Reports synced with Google Drive successfully!")
            log_info("All Advised Students Reports synced with Google Drive successfully.")
        except Exception as e:
            st.error(f"❌ Error syncing All Advised Students Reports: {e}")
            log_error("Error syncing All Advised Students Reports", e)
