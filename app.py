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
    """
    if "courses_df" not in st.session_state or st.session_state.courses_df.empty:
        st.warning("Courses table not loaded.")
        return
    if "progress_df" not in st.session_state or st.session_state.progress_df.empty:
        st.warning("Progress report not loaded.")
        return
    if "advising_selections" not in st.session_state:
        st.session_state.advising_selections = {}

    # ---- Student picker (compact header) ----
    students_df = st.session_state.progress_df.copy()
    students_df["DISPLAY"] = students_df["NAME"].astype(str) + " — " + students_df["ID"].astype(str)
    st.markdown("#### Select Student")
    choice = st.selectbox("", students_df["DISPLAY"].tolist(), label_visibility="collapsed")
    selected_student_id = int(students_df.loc[students_df["DISPLAY"] == choice, "ID"].iloc[0])
    student_row = students_df.loc[students_df["ID"] == selected_student_id].iloc[0]

    # Ensure selection bucket
    slot = st.session_state.advising_selections.setdefault(
        selected_student_id, {"advised": [], "optional": [], "note": ""}
    )

    # Header card
    credits_completed = float(student_row.get("# of Credits Completed", 0) or 0)
    credits_registered = float(student_row.get("# Registered", 0) or 0)
    total_credits = credits_completed + credits_registered
    standing = get_student_standing(total_credits)

    with st.container():
        st.markdown(
            f"""
            <div class="section-card">
              <div><strong>Name:</strong> {student_row['NAME']} &nbsp; | &nbsp;
              <strong>ID:</strong> {selected_student_id} &nbsp; | &nbsp;
              <strong>Credits:</strong> {int(total_credits)} &nbsp; | &nbsp;
              <strong>Standing:</strong> {standing}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("")  # small spacer

    # ---------- Build eligibility + justifications dicts ----------
    status_dict: dict[str, str] = {}
    justification_dict: dict[str, str] = {}

    current_advised_for_checks = list(slot.get("advised", []))  # for engine only

    for course_code in st.session_state.courses_df["Course Code"]:
        status, justification = check_eligibility(
            student_row, str(course_code), current_advised_for_checks, st.session_state.courses_df
        )
        status_dict[str(course_code)] = status
        justification_dict[str(course_code)] = justification

    # ---------- Build display dataframe ----------
    rows = []
    for course_code in st.session_state.courses_df["Course Code"]:
        code = str(course_code)
        info = st.session_state.courses_df.loc[
            st.session_state.courses_df["Course Code"] == course_code
        ].iloc[0]
        offered = "Yes" if is_course_offered(st.session_state.courses_df, code) else "No"
        status = status_dict.get(code, "")

        if check_course_completed(student_row, code):
            action = "Completed"; status = "Completed"
        elif check_course_registered(student_row, code):
            action = "Registered"
        elif code in (slot.get("advised", []) or []):
            action = "Advised"
        elif code in (slot.get("optional", []) or []):
            action = "Optional"
        elif status == "Not Eligible":
            action = "Not Eligible"
        else:
            action = "Eligible (not chosen)"

        rows.append(
            {
                "Course Code": code,
                "Type": info.get("Type", ""),
                "Requisites": build_requisites_str(info),
                "Eligibility Status": status,
                "Justification": justification_dict.get(code, ""),
                "Offered": offered,
                "Action": action,
            }
        )

    courses_display_df = pd.DataFrame(rows)
    req_df = courses_display_df[courses_display_df["Type"] == "Required"].copy()
    int_df = courses_display_df[courses_display_df["Type"] == "Intensive"].copy()

    # ---------- Two-column layout: left tables, right form ----------
    left, right = st.columns([7, 5], gap="large")

    with left:
        st.markdown("#### Course Eligibility")

        if not req_df.empty:
            with st.expander("Required Courses", expanded=True):
                st.dataframe(style_df(req_df), use_container_width=True)
        if not int_df.empty:
            with st.expander("Intensive Courses", expanded=False):
                st.dataframe(style_df(int_df), use_container_width=True)

    with right:
        st.markdown("#### Advising Selections")

        # Offered set
        offered_set = set(
            map(
                str,
                st.session_state.courses_df.loc[
                    st.session_state.courses_df["Offered"].astype(str).str.lower() == "yes",
                    "Course Code",
                ].tolist(),
            )
        )

        def _eligible_for_selection() -> list[str]:
            elig: list[str] = []
            for c in map(str, st.session_state.courses_df["Course Code"].tolist()):
                if c not in offered_set:
                    continue
                if check_course_completed(student_row, c) or check_course_registered(student_row, c):
                    continue
                if status_dict.get(c) == "Eligible":
                    elig.append(c)
            return sorted(elig)

        eligible_options: list[str] = _eligible_for_selection()
        opts_set = set(eligible_options)

        # Sanitize defaults
        saved_advised = [str(x) for x in (slot.get("advised", []) or [])]
        saved_optional = [str(x) for x in (slot.get("optional", []) or [])]

        default_advised = [c for c in saved_advised if c in opts_set]
        dropped_advised = sorted(set(saved_advised) - set(default_advised))

        opt_space_now = [c for c in eligible_options if c not in default_advised]
        opt_space_set = set(opt_space_now)
        default_optional = [c for c in saved_optional if c in opt_space_set]
        dropped_optional = sorted(set(saved_optional) - set(default_optional))

        with st.form(key=f"advise_form_{selected_student_id}"):
            advised_selection = st.multiselect(
                "Advised Courses",
                options=eligible_options,
                default=default_advised,
                key=f"advised_ms_{selected_student_id}",
            )
            opt_options_live = [c for c in eligible_options if c not in advised_selection]
            optional_selection = st.multiselect(
                "Optional Courses",
                options=opt_options_live,
                default=[c for c in default_optional if c in opt_options_live],
                key=f"optional_ms_{selected_student_id}",
            )
            note_input = st.text_area(
                "Advisor Note (optional)",
                value=slot.get("note", ""),
                key=f"note_{selected_student_id}",
                height=90,
            )

            if dropped_advised or dropped_optional:
                with st.expander("Some saved selections aren’t available this term"):
                    if dropped_advised:
                        st.write("**Advised (saved but unavailable now):** ", ", ".join(dropped_advised))
                    if dropped_optional:
                        st.write("**Optional (saved but unavailable now):** ", ", ".join(dropped_optional))
                    st.caption(
                        "Courses not shown could be not offered, already completed/registered, or removed from the current courses table."
                    )

            submitted = st.form_submit_button("Save Selections")
            if submitted:
                st.session_state.advising_selections[selected_student_id] = {
                    "advised": advised_selection,
                    "optional": optional_selection,
                    "note": note_input,
                }
                st.success("Selections saved.")
                log_info(f"Saved selections for {selected_student_id}")
                st.rerun()

        st.markdown("#### Download Report")
        if st.button("Download Student Report", use_container_width=True):
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
                    st.session_state.courses_df.set_index("Course Code")
                    .reindex(advised_selection)
                    .get("Credits", pd.Series(0))
                    .fillna(0)
                    .astype(float)
                    .sum()
                )
                if "Credits" in st.session_state.courses_df.columns
                else 0,
                optional_credits=int(
                    st.session_state.courses_df.set_index("Course Code")
                    .reindex(optional_selection)
                    .get("Credits", pd.Series(0))
                    .fillna(0)
                    .astype(float)
                    .sum()
                )
                if "Credits" in st.session_state.courses_df.columns
                else 0,
            )
            st.download_button(
                "Download Excel",
                data=output.getvalue(),
                file_name=f"Advising_{selected_student_id}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            )
