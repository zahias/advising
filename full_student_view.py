# full_student_view.py

import streamlit as st
import pandas as pd
from io import BytesIO
from utils import (
    check_course_completed,
    check_course_registered,
    check_eligibility,
    get_student_standing,
    style_df,
    log_info,
    log_error
)
from google_drive import sync_file_with_drive, initialize_drive_service
from reporting import add_summary_sheet

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
        advised = sel.get("advised", []) + sel.get("optional", [])
        if course in advised:
            return "a"
        stt, _ = check_eligibility(row, course, advised, st.session_state.courses_df)
        return "na" if stt == "Eligible" else "ne"

    for c in selected_courses:
        df[c] = df.apply(lambda r, cc=c: status_code(r, cc), axis=1)

    # Show table with legend
    st.write("*Legend:* c=Completed, r=Registered, a=Advised, na=Eligible not chosen, ne=Not Eligible")
    st.dataframe(df[["ID", "NAME", "Total Credits Completed", "Standing", "Advising Status"] + selected_courses], use_container_width=True, height=600)

    # Export full advising report with summary
    if st.button("Download Full Advising Report"):
        output = BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="Full Report")
            add_summary_sheet(writer, df, selected_courses)
        st.download_button(
            "Download Excel",
            data=output.getvalue(),
            file_name="Full_Advising_Report.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

def _render_individual_student():
    students_df = st.session_state.progress_df
    students_df["DISPLAY"] = students_df["NAME"].astype(str) + " — " + students_df["ID"].astype(str)
    choice = st.selectbox("Select a student", students_df["DISPLAY"].tolist(), key="full_single_select")
    sid = int(students_df.loc[students_df["DISPLAY"] == choice, "ID"].iloc[0])
    row = students_df.loc[students_df["ID"] == sid].iloc[0]

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
            advised = sel.get("advised", []) + sel.get("optional", [])
            if c in advised:
                data[c] = ["a"]
            else:
                stt, _ = check_eligibility(row, c, advised, st.session_state.courses_df)
                data[c] = ["na" if stt == "Eligible" else "ne"]
    indiv_df = pd.DataFrame(data)
    st.write("*Legend:* c=Completed, r=Registered, a=Advised, na=Eligible not chosen, ne=Not Eligible")
    st.dataframe(indiv_df, use_container_width=True)

    if st.button("Download Individual Report"):
        output = BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            indiv_df.to_excel(writer, index=False, sheet_name="Student")
        st.download_button(
            "Download Excel",
            data=output.getvalue(),
            file_name=f"Student_{sid}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    # Download sheets for all advised students into one workbook + sync to Drive
    if st.button("Download All Advised Students Reports"):
        all_sel = [(int(k), v) for k, v in st.session_state.advising_selections.items() if v.get("advised")]
        if not all_sel:
            st.info("No advised students found.")
            return
        output = BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            for sid_, sel in all_sel:
                srow = st.session_state.progress_df.loc[st.session_state.progress_df["ID"] == sid_].iloc[0]
                data = {"Course Code": [], "Action": [], "Eligibility Status": [], "Justification": []}
                # Build same grid used in eligibility view for this student (compact)
                for cc in st.session_state.courses_df["Course Code"]:
                    status, just = check_eligibility(srow, cc, sel.get("advised", []), st.session_state.courses_df)
                    if check_course_completed(srow, cc):
                        action = "Completed"; status = "Completed"
                    elif check_course_registered(srow, cc):
                        action = "Registered"
                    elif cc in sel.get("advised", []):
                        action = "Advised"
                    else:
                        action = "Eligible not chosen" if status == "Eligible" else "Not Eligible"
                    data["Course Code"].append(cc)
                    data["Action"].append(action)
                    data["Eligibility Status"].append(status)
                    data["Justification"].append(just)
                pd.DataFrame(data).to_excel(writer, index=False, sheet_name=str(sid_))
            # Add an index sheet with names/IDs
            index_df = st.session_state.progress_df.loc[st.session_state.progress_df["ID"].isin([sid for sid,_ in all_sel]), ["ID", "NAME"]]
            index_df.to_excel(writer, index=False, sheet_name="Index")

        st.download_button(
            "Download All (Excel)",
            data=output.getvalue(),
            file_name="All_Advised_Students.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

        # Also sync to Drive (preserving original behavior)
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
