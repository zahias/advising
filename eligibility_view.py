# eligibility_view.py

import streamlit as st
import pandas as pd
from io import BytesIO
from utils import (
    check_course_completed,
    check_course_registered,
    is_course_offered,
    check_eligibility,
    build_requisites_str,
    style_df,
    get_student_standing,
    log_info,
    log_error
)
from reporting import apply_excel_formatting

def student_eligibility_view():
    """
    Per-student advising & eligibility page.
    Expects in st.session_state:
      - courses_df
      - progress_df
      - advising_selections (dict: ID -> {'advised':[],'optional':[],'note':str})
    """
    if "courses_df" not in st.session_state or st.session_state.courses_df.empty:
        st.warning("Courses table not loaded.")
        return
    if "progress_df" not in st.session_state or st.session_state.progress_df.empty:
        st.warning("Progress report not loaded.")
        return
    if "advising_selections" not in st.session_state:
        st.session_state.advising_selections = {}

    # Student picker
    students_df = st.session_state.progress_df
    students_df["DISPLAY"] = students_df["NAME"].astype(str) + " — " + students_df["ID"].astype(str)
    choice = st.selectbox("Select a student", students_df["DISPLAY"].tolist())
    selected_student_id = int(students_df.loc[students_df["DISPLAY"] == choice, "ID"].iloc[0])
    student_row = students_df.loc[students_df["ID"] == selected_student_id].iloc[0]

    # Ensure selection bucket
    slot = st.session_state.advising_selections.setdefault(selected_student_id, {"advised": [], "optional": [], "note": ""})

    # Credits/Standing
    credits_completed = float(student_row.get("# of Credits Completed", 0))
    credits_registered = float(student_row.get("# Registered", 0))
    total_credits = credits_completed + credits_registered
    standing = get_student_standing(total_credits)

    st.write(f"**Name:** {student_row['NAME']}  |  **ID:** {selected_student_id}  |  **Credits:** {int(total_credits)}  |  **Standing:** {standing}")

    # Eligibility for each course
    status_dict = {}
    justification_dict = {}

    advised_selection = slot.get("advised", [])
    optional_selection = slot.get("optional", [])

    for course_code in st.session_state.courses_df["Course Code"]:
        status, justification = check_eligibility(student_row, course_code, advised_selection, st.session_state.courses_df)
        status_dict[course_code] = status
        justification_dict[course_code] = justification

    # Build display dataframe
    rows = []
    for course_code in st.session_state.courses_df["Course Code"]:
        info = st.session_state.courses_df.loc[st.session_state.courses_df["Course Code"] == course_code].iloc[0]
        offered = "Yes" if is_course_offered(st.session_state.courses_df, course_code) else "No"
        action = ""
        status = status_dict[course_code]
        if check_course_completed(student_row, course_code):
            action = "Completed"
            status = "Completed"
        elif check_course_registered(student_row, course_code):
            action = "Registered"
        elif course_code in advised_selection:
            action = "Advised"
        elif course_code in optional_selection:
            action = "Optional"
        elif status == "Not Eligible":
            action = "Not Eligible"
        else:
            action = "Eligible (not chosen)"

        rows.append({
            "Course Code": course_code,
            "Type": info.get("Type", ""),
            "Requisites": build_requisites_str(info),
            "Eligibility Status": status,
            "Justification": justification_dict[course_code],
            "Offered": offered,
            "Action": action
        })

    courses_display_df = pd.DataFrame(rows)

    # Split by Type
    req_df = courses_display_df[courses_display_df["Type"] == "Required"].copy()
    int_df = courses_display_df[courses_display_df["Type"] == "Intensive"].copy()

    st.markdown("### Course Eligibility")

    if not req_df.empty:
        st.markdown("**Required Courses**")
        st.dataframe(style_df(req_df), use_container_width=True)
    if not int_df.empty:
        st.markdown("**Intensive Courses**")
        st.dataframe(style_df(int_df), use_container_width=True)

    # Selection widgets (exclude completed/registered/not offered)
    offered_set = set(st.session_state.courses_df.loc[st.session_state.courses_df["Offered"].astype(str).str.lower() == "yes", "Course Code"])
    selectable = [c for c in st.session_state.courses_df["Course Code"]
                  if (c in offered_set) and not check_course_completed(student_row, c) and not check_course_registered(student_row, c)
                  and status_dict.get(c) == "Eligible"]

    with st.form(key="advise_form"):
        advised_selection = st.multiselect("Advised Courses", options=selectable, default=slot.get("advised", []))
        # Optional can be a subset too
        opt_options = [c for c in selectable if c not in advised_selection]
        optional_selection = st.multiselect("Optional Courses", options=opt_options, default=slot.get("optional", []))
        note_input = st.text_area("Advisor Note (optional)", value=slot.get("note", ""))

        submitted = st.form_submit_button("Save Selections")
        if submitted:
            st.session_state.advising_selections[selected_student_id] = {
                "advised": advised_selection,
                "optional": optional_selection,
                "note": note_input,
            }
            st.success("Selections saved.")
            log_info(f"Saved selections for {selected_student_id}")

    # Download report
    st.subheader("Download Advising Report")
    if st.button("Download Student Report"):
        report_df = courses_display_df.copy()
        output = BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            report_df.to_excel(writer, index=False, sheet_name="Advising")
        apply_excel_formatting(
            output=output,
            student_name=str(student_row["NAME"]),
            student_id=selected_student_id,
            credits_completed=int(credits_completed),
            standing=standing,
            note=st.session_state.advising_selections[selected_student_id].get("note", ""),
            advised_credits=int(
                st.session_state.courses_df.set_index("Course Code").reindex(advised_selection).get("Credits", pd.Series(0)).fillna(0).astype(float).sum()
            ) if "Credits" in st.session_state.courses_df.columns else 0,
            optional_credits=int(
                st.session_state.courses_df.set_index("Course Code").reindex(optional_selection).get("Credits", pd.Series(0)).fillna(0).astype(float).sum()
            ) if "Credits" in st.session_state.courses_df.columns else 0,
        )
        st.download_button(
            "Download Excel",
            data=output.getvalue(),
            file_name=f"Advising_{selected_student_id}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
