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
from course_exclusions import ensure_loaded as ensure_exclusions_loaded, get_for_student, set_for_student


def student_eligibility_view():
    """
    Per-student advising & eligibility page.
    Expects in st.session_state:
      - courses_df
      - progress_df
      - advising_selections (dict: ID -> {'advised':[],'optional':[],'note':str})
      - course_exclusions handled via course_exclusions.ensure_loaded()
    """
    if "courses_df" not in st.session_state or st.session_state.courses_df.empty:
        st.warning("Courses table not loaded.")
        return
    if "progress_df" not in st.session_state or st.session_state.progress_df.empty:
        st.warning("Progress report not loaded.")
        return
    if "advising_selections" not in st.session_state:
        st.session_state.advising_selections = {}

    # Load per-student exclusions (from Drive if first time this major)
    ensure_exclusions_loaded()

    # ---------- Student picker ----------
    students_df = st.session_state.progress_df.copy()
    students_df["DISPLAY"] = students_df["NAME"].astype(str) + " — " + students_df["ID"].astype(str)
    choice = st.selectbox("Select a student", students_df["DISPLAY"].tolist())
    selected_student_id = int(students_df.loc[students_df["DISPLAY"] == choice, "ID"].iloc[0])
    student_row = students_df.loc[students_df["ID"] == selected_student_id].iloc[0]

    # Current hidden courses for this student
    hidden_for_student = set(map(str, get_for_student(selected_student_id)))

    # Ensure selection bucket
    slot = st.session_state.advising_selections.setdefault(
        selected_student_id, {"advised": [], "optional": [], "note": ""}
    )

    # Credits/Standing
    credits_completed = float(student_row.get("# of Credits Completed", 0) or 0)
    credits_registered = float(student_row.get("# Registered", 0) or 0)
    total_credits = credits_completed + credits_registered
    standing = get_student_standing(total_credits)

    st.write(
        f"**Name:** {student_row['NAME']}  |  **ID:** {selected_student_id}  |  "
        f"**Credits:** {int(total_credits)}  |  **Standing:** {standing}"
    )

    # ---------- Build eligibility + justifications dicts (skip hidden) ----------
    status_dict: dict[str, str] = {}
    justification_dict: dict[str, str] = {}

    current_advised_for_checks = list(slot.get("advised", []))  # used only for eligibility engine

    for course_code in st.session_state.courses_df["Course Code"]:
        code = str(course_code)
        if code in hidden_for_student:
            continue
        status, justification = check_eligibility(
            student_row, code, current_advised_for_checks, st.session_state.courses_df
        )
        status_dict[code] = status
        justification_dict[code] = justification

    # ---------- Build display dataframe (skip hidden) ----------
    rows = []
    for course_code in st.session_state.courses_df["Course Code"]:
        code = str(course_code)
        if code in hidden_for_student:
            continue
        info = st.session_state.courses_df.loc[
            st.session_state.courses_df["Course Code"] == course_code
        ].iloc[0]
        offered = "Yes" if is_course_offered(st.session_state.courses_df, code) else "No"
        status = status_dict.get(code, "")

        if check_course_completed(student_row, code):
            action = "Completed"
            status = "Completed"
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

    # ---------- Advising selections form (robust defaults; skip hidden) ----------
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
            if c in hidden_for_student:
                continue
            if c not in offered_set:
                continue
            if check_course_completed(student_row, c) or check_course_registered(student_row, c):
                continue
            if status_dict.get(c) == "Eligible":
                elig.append(c)
        return sorted(elig)

    eligible_options: list[str] = _eligible_for_selection()
    opts_set = set(eligible_options)

    saved_advised = [str(x) for x in (slot.get("advised", []) or []) if str(x) not in hidden_for_student]
    saved_optional = [str(x) for x in (slot.get("optional", []) or []) if str(x) not in hidden_for_student]

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
        )

        if dropped_advised or dropped_optional:
            with st.expander("Some saved selections aren’t available this term"):
                if dropped_advised:
                    st.write("**Advised (previously saved but not available now):** ", ", ".join(dropped_advised))
                if dropped_optional:
                    st.write("**Optional (previously saved but not available now):** ", ", ".join(dropped_optional))
                st.caption(
                    "Courses not shown could be hidden, not offered, already completed/registered, "
                    "or removed from the current courses table."
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

    # ---------- NEW: per-student hidden courses (persisted to Drive) ----------
    with st.expander("Hidden courses for this student"):
        all_codes = sorted(map(str, st.session_state.courses_df["Course Code"].tolist()))
        # Only show codes that still exist in the current table as options;
        # previously hidden codes that no longer exist remain persisted but are not shown
        default_hidden = [c for c in all_codes if c in hidden_for_student]
        new_hidden = st.multiselect(
            "Remove (hide) these courses for this student",
            options=all_codes,
            default=default_hidden,
            key=f"hidden_ms_{selected_student_id}",
            help="Hidden courses will not appear in tables or selection lists, and this choice is saved to Drive.",
        )
        if st.button("Save Hidden Courses", key=f"save_hidden_{selected_student_id}"):
            set_for_student(selected_student_id, new_hidden)
            st.success("Hidden courses saved for this student.")
            st.rerun()

    # ---------- Download report ----------
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
                st.session_state.courses_df.set_index("Course Code")
                .reindex([c for c in slot.get("advised", []) if c not in hidden_for_student])
                .get("Credits", pd.Series(0))
                .fillna(0)
                .astype(float)
                .sum()
            )
            if "Credits" in st.session_state.courses_df.columns
            else 0,
            optional_credits=int(
                st.session_state.courses_df.set_index("Course Code")
                .reindex([c for c in slot.get("optional", []) if c not in hidden_for_student])
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
        )
