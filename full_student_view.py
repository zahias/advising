# full_student_view.py

import streamlit as st
import pandas as pd
from io import BytesIO
from utils import (
    check_course_completed,
    is_course_offered,
    check_eligibility,
    get_student_standing,
    log_info,
    log_error
)
from reporting import apply_full_report_formatting, add_summary_sheet
from google_drive import initialize_drive_service
from openpyxl.styles import Font, PatternFill

def full_student_view():
    """Render the Full Student View tab."""
    st.header("Full Student View")
    view_option = st.radio("View Options", ["All Students", "Individual Student"])

    if view_option == "All Students":
        st.subheader("All Students Report")
        if st.session_state.progress_df.empty:
            st.warning("⚠️ Progress report is not loaded.")
            return

        st.sidebar.header("Filters")
        available_courses = st.session_state.courses_df["Course Code"].tolist()
        selected_courses = st.sidebar.multiselect("Select Courses to Display", options=available_courses, default=available_courses)
        min_credits = int(st.session_state.progress_df[["# of Credits Completed", "# Registered"]].fillna(0).sum(axis=1).min())
        max_credits = int(st.session_state.progress_df[["# of Credits Completed", "# Registered"]].fillna(0).sum(axis=1).max())
        credit_range = st.sidebar.slider("Select Total Credits Completed Range", min_value=min_credits, max_value=max_credits, value=(min_credits, max_credits), step=1)

        filtered_df = st.session_state.progress_df.copy()
        filtered_df["Total Credits Completed"] = filtered_df.apply(
            lambda row: (row.get("# of Credits Completed", 0) if pd.notna(row.get("# of Credits Completed", 0)) else 0)
                        + (row.get("# Registered", 0) if pd.notna(row.get("# Registered", 0)) else 0),
            axis=1,
        )
        filtered_df = filtered_df[
            (filtered_df["Total Credits Completed"] >= credit_range[0])
            & (filtered_df["Total Credits Completed"] <= credit_range[1])
        ]
        filtered_df["Standing"] = filtered_df["Total Credits Completed"].apply(get_student_standing)
        log_info("Computed 'Standing' for all filtered students.")

        advising_statuses = []
        for _, student in filtered_df.iterrows():
            sid = str(student["ID"])
            if sid in st.session_state.advising_selections and (
                st.session_state.advising_selections[sid].get("advised") or st.session_state.advising_selections[sid].get("optional")
            ):
                advising_statuses.append("Advised")
            else:
                advising_statuses.append("Not Advised")
        filtered_df["Advising Status"] = advising_statuses

        for course_code in selected_courses:
            statuses = []
            for _, student in filtered_df.iterrows():
                sid = str(student["ID"])
                course_status = "ne"
                if check_course_completed(student, course_code):
                    course_status = "c"
                else:
                    advised_for_student = st.session_state.advising_selections.get(sid, {}).get("advised", [])
                    eligibility_status, _ = check_eligibility(student, course_code, advised_for_student, st.session_state.courses_df)
                    if course_code in advised_for_student:
                        course_status = "a"
                    elif eligibility_status == "Eligible":
                        course_status = "na"
                    else:
                        course_status = "ne"
                statuses.append(course_status)
            filtered_df[course_code] = statuses

        base_cols = ["ID", "NAME", "# of Credits Completed", "# Registered", "Total Credits Completed", "Standing", "Advising Status"]
        full_columns = base_cols + selected_courses
        full_report = filtered_df[full_columns].copy()

        # Use the new formatting function for the full report.
        # Base columns count is 7 (the first 7 columns are base info)
        output_buffer = BytesIO()
        with pd.ExcelWriter(output_buffer, engine="openpyxl") as writer:
            full_report.to_excel(writer, index=False, sheet_name="Full Report")
            add_summary_sheet(writer, st.session_state.courses_df, st.session_state.advising_selections, st.session_state.progress_df)
        output_buffer.seek(0)
        # Now apply full report formatting (base_cols_count = 7)
        formatted_output = apply_full_report_formatting(output_buffer, base_cols_count=7)

        st.write("*Legend:* c=Completed, a=Advised, na=Eligible not chosen, ne=Not Eligible")
        st.dataframe(full_report.style.applymap(lambda v: 
            "background-color: lightgray" if v=="c" else
            "background-color: lightgreen" if v=="a" else
            "background-color: #E0FFE0" if v=="na" else
            "background-color: lightcoral" if v=="ne" else "",
            subset=selected_courses
        ), height=600, use_container_width=True)

        if st.button("Download Full Advising Report"):
            st.download_button(
                label="Download Full Advising Report",
                data=formatted_output.getvalue(),
                file_name="Full_Advising_Report.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
            st.success("✅ Full Advising Report is ready for download.")
            log_info("Full Advising Report downloaded for all students.")

    elif view_option == "Individual Student":
        st.subheader("Individual Student Report")
        if st.session_state.progress_df.empty:
            st.warning("⚠️ Progress report is not loaded.")
            return

        student_list = st.session_state.progress_df["ID"].astype(str) + " - " + st.session_state.progress_df["NAME"]
        selected_student = st.selectbox("Select a Student", student_list, help="Select a student to view their full report.")
        selected_student_id = selected_student.split(" - ")[0]
        student_row = st.session_state.progress_df[st.session_state.progress_df["ID"] == int(selected_student_id)].iloc[0].to_dict()

        credits_completed_field = student_row.get("# of Credits Completed", 0)
        credits_registered_field = student_row.get("# Registered", 0)
        credits_completed = (credits_completed_field if pd.notna(credits_completed_field) else 0) + (credits_registered_field if pd.notna(credits_registered_field) else 0)
        standing = get_student_standing(credits_completed)
        log_info(f"Computed 'Standing' for student ID {selected_student_id}: {standing}")

        full_report = pd.DataFrame({
            "ID": [student_row["ID"]],
            "NAME": [student_row["NAME"]],
            "# of Credits Completed": [student_row["# of Credits Completed"]],
            "# Registered": [student_row["# Registered"]],
            "Total Credits Completed": [credits_completed],
            "Standing": [standing]
        })

        if selected_student_id in st.session_state.advising_selections and (
            st.session_state.advising_selections[selected_student_id].get("advised") or st.session_state.advising_selections[selected_student_id].get("optional")
        ):
            advising_status = "Advised"
        else:
            advising_status = "Not Advised"
        full_report["Advising Status"] = advising_status

        available_courses = st.session_state.courses_df["Course Code"].tolist()
        selected_courses = st.multiselect("Select Courses to Display", options=available_courses, default=available_courses)

        for course_code in selected_courses:
            course_status = "ne"
            if check_course_completed(student_row, course_code):
                course_status = "c"
            else:
                advised_for_student = st.session_state.advising_selections.get(selected_student_id, {}).get("advised", [])
                eligibility_status, _ = check_eligibility(student_row, course_code, advised_for_student, st.session_state.courses_df)
                if course_code in advised_for_student:
                    course_status = "a"
                elif eligibility_status == "Eligible":
                    course_status = "na"
                else:
                    course_status = "ne"
            full_report[course_code] = course_status

        base_cols = ["ID", "NAME", "# of Credits Completed", "# Registered", "Total Credits Completed", "Standing", "Advising Status"]
        full_columns = base_cols + selected_courses
        full_report = full_report[full_columns].copy()

        def color_status(val):
            if val == "c":
                return "background-color: lightgray"
            elif val == "a":
                return "background-color: lightgreen"
            elif val == "na":
                return "background-color: #E0FFE0"
            elif val == "ne":
                return "background-color: lightcoral"
            return ""

        styled_report = full_report.style.applymap(color_status, subset=selected_courses)
        st.write("*Legend:* c=Completed, a=Advised, na=Eligible not chosen, ne=Not Eligible")
        st.dataframe(styled_report, height=600, use_container_width=True)

        service = initialize_drive_service()
        if st.button("Download Individual Advising Report"):
            output_individual = BytesIO()
            with pd.ExcelWriter(output_individual, engine="openpyxl") as writer:
                full_report.to_excel(writer, index=False, sheet_name="Individual Report")
                add_summary_sheet(writer, st.session_state.courses_df, st.session_state.advising_selections, st.session_state.progress_df)
                wb = writer.book
                for sheet in wb.worksheets:
                    sheet.sheet_state = "visible"
                wb.active = 0
            output_individual.seek(0)
            # For individual report, we also apply formatting similar to the full report.
            formatted_individual = apply_full_report_formatting(output_individual, base_cols_count=7)
            st.download_button(
                label="Download Individual Advising Report",
                data=formatted_individual.getvalue(),
                file_name=f'{student_row["NAME"].replace(" ", "_")}_Advising_Report.xlsx',
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
            st.success("✅ Individual Advising Report is ready for download.")
            log_info(f"Individual Advising Report downloaded for student ID {selected_student_id}.")
