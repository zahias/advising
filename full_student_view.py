# full_student_view.py

import pandas as pd
import streamlit as st
from io import BytesIO

from google_drive import initialize_drive_service, sync_file_with_drive
from reporting import add_summary_sheet
from utils import (
    check_course_completed,
    check_course_registered,
    check_eligibility,
    get_student_standing,
)

def full_student_view():
    if "courses_df" not in st.session_state or st.session_state.courses_df.empty:
        st.warning("Courses table not loaded.")
        return
    if "progress_df" not in st.session_state or st.session_state.progress_df.empty:
        st.warning("Progress report not loaded.")
        return
    if "advising_selections" not in st.session_state:
        st.session_state.advising_selections = {}

    tab_all, tab_one = st.tabs(["All Students", "Individual Student"])
    with tab_all:
        _render_all_students()
    with tab_one:
        _render_individual_student()

def _render_all_students():
    df = st.session_state.progress_df.copy()
    df["Total Credits Completed"] = df[["# of Credits Completed", "# Registered"]].fillna(0).sum(axis=1)
    df["Standing"] = df["Total Credits Completed"].apply(get_student_standing)
    df["Advising Status"] = df["ID"].astype(str).apply(
        lambda sid: "Advised" if st.session_state.advising_selections.get(sid, {}).get("advised") else "Not Advised"
    )

    available_courses = st.session_state.courses_df["Course Code"].tolist()
    selected_courses = st.multiselect("Select course columns", options=available_courses, default=available_courses)

    def status_code(row, course):
        if check_course_completed(row, course):
            return "c"
        if check_course_registered(row, course):
            return "r"
        sel = st.session_state.advising_selections.get(str(row["ID"]), {})
        advised = (sel.get("advised", []) or []) + (sel.get("optional", []) or [])
        if course in advised:
            return "a"
        stt, _ = check_eligibility(row, course, advised, st.session_state.courses_df)
        return "na" if stt == "Eligible" else "ne"

    for c in selected_courses:
        df[c] = df.apply(lambda r, cc=c: status_code(r, cc), axis=1)

    st.write("*Legend:* c=Completed, r=Registered, a=Advised, na=Eligible not chosen, ne=Not Eligible")
    st.dataframe(df[["ID", "NAME", "Total Credits Completed", "Standing", "Advising Status"] + selected_courses],
                 use_container_width=True, height=600)

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
    students = st.session_state.progress_df
    students["DISPLAY"] = students["ID"].astype(str) + " - " + students["NAME"].astype(str)
    choice = st.selectbox("Select a Student", students["DISPLAY"].tolist())
    sid = int(choice.split(" - ")[0])
    row = st.session_state.progress_df.loc[st.session_state.progress_df["ID"] == sid].iloc[0]

    available_courses = st.session_state.courses_df["Course Code"].tolist()
    selected_courses = st.multiselect("Select Courses", options=available_courses, default=available_courses, key="indiv_courses")

    data = {"ID": [sid], "NAME": [row["NAME"]]}
    for c in selected_courses:
        if check_course_completed(row, c):
            data[c] = ["c"]
        elif check_course_registered(row, c):
            data[c] = ["r"]
        else:
            sel = st.session_state.advising_selections.get(str(sid), {})
            advised = (sel.get("advised", []) or []) + (sel.get("optional", []) or [])
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

    if st.button("Download All Advised Students Reports"):
        sel_all = [(int(k), v) for k, v in st.session_state.advising_selections.items() if v.get("advised")]
        if not sel_all:
            st.info("No advised students found.")
            return
        output = BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            for sid_, sel in sel_all:
                srow = st.session_state.progress_df.loc[st.session_state.progress_df["ID"] == sid_].iloc[0]
                # small compact sheet per student
                data = {"Course Code": [], "Action": [], "Eligibility Status": [], "Justification": []}
                for cc in st.session_state.courses_df["Course Code"]:
                    stt, just = check_eligibility(srow, cc, sel.get("advised", []), st.session_state.courses_df)
                    if check_course_completed(srow, cc):
                        action = "Completed"; stt = "Completed"
                    elif check_course_registered(srow, cc):
                        action = "Registered"
                    elif cc in sel.get("advised", []):
                        action = "Advised"
                    else:
                        action = "Eligible not chosen" if stt == "Eligible" else "Not Eligible"
                    data["Course Code"].append(cc)
                    data["Action"].append(action)
                    data["Eligibility Status"].append(stt)
                    data["Justification"].append(just)
                pd.DataFrame(data).to_excel(writer, index=False, sheet_name=str(sid_))
            st.session_state.progress_df.loc[
                st.session_state.progress_df["ID"].isin([sid for sid, _ in sel_all]), ["ID", "NAME"]
            ].to_excel(writer, index=False, sheet_name="Index")

        st.download_button(
            "Download All (Excel)",
            data=output.getvalue(),
            file_name="All_Advised_Students.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        # optional: sync to Drive is kept in your original app; call it there if needed
