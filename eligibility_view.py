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

    # ---- Advising selections form (Save -> rerun) ----
    # Build selectable set (exclude completed/registered/not offered; must be Eligible)
    offered_set = set(st.session_state.courses_df.loc[st.session_state.courses_df["Offered"].astype(str).str.lower() == "yes", "Course Code"])

    # We'll compute status per course below, but to build the selectable list we temporarily mark all;
    # The final table will be recomputed after Save + rerun, so this list stays consistent.
    def _eligible_for_selection():
        elig = []
        for c in st.session_state.courses_df["Course Code"]:
            if c not in offered_set:
                continue
            if check_course_completed(student_row, c) or check_course_registered(student_row, c):
                continue
            status, _ = check_eligibility(student_row, c, slot.get("advised", []), st.session_state.courses_df)
            if status == "Eligible":
                elig.append(c)
        return elig

    with st.form(key="advise_form"):
        advised_selection = st.multiselect("Advised Courses", options=_eligible_for_selection(), default=slot.get("advised", []))
        opt_options = [c for c in _eligible_for_selection() if c not in advised_selection]
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
            # IMPORTANT: immediately rebuild the tables with the new selections
            st.rerun()

    # ---- Build eligibility/status table (reflects latest state) ----
    status_dict = {}
    justification_dict = {}
    current_advised = st.session_state.advising_selections[selected_student_id].get("advised", [])
    current_optional = st.session_state.advising_selections[selected_student_id].get("optional", [])

    for course_code in st.session_state.courses_df["Course Code"]:
        status, justification = check_eligibility(student_row, course_code, current_advised, st.session_state.courses_df)
        status_dict[course_code] = status
        justification_dict[course_code] = justification

    rows = []
    for course_code in st.session_state.courses_df["Course Code"]:
        info = st.session_state.courses_df.loc[st.session_state.courses_df["Course Code"] == course_code].iloc[0]
        offered = "Yes" if is_course_offered(st.session_state.courses_df, course_code) else "No"
        status = status_dict[course_code]

        if check_course_completed(student_row, course_code):
            action = "Completed"
            status = "Completed"
        elif check_course_registered(student_row, course_code):
            action = "Registered"
        elif course_code in current_advised:
            action = "Advised"
        elif course_code in current_optional:
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

    # ---- Download report ----
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
                st.session_state.courses_df.set_index("Course Code").reindex(current_advised).get("Credits", pd.Series(0)).fillna(0).astype(float).sum()
            ) if "Credits" in st.session_state.courses_df.columns else 0,
            optional_credits=int(
                st.session_state.courses_df.set_index("Course Code").reindex(current_optional).get("Credits", pd.Series(0)).fillna(0).astype(float).sum()
            ) if "Credits" in st.session_state.courses_df.columns else 0,
        )
        st.download_button(
            "Download Excel",
            data=output.getvalue(),
            file_name=f"Advising_{selected_student_id}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
