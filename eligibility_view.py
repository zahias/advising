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
      - advising_selections (dict: ID -> {'advised':[],'optional':[],'excluded':[],'note':str})
    """
    if "courses_df" not in st.session_state or st.session_state.courses_df.empty:
        st.warning("Courses table not loaded.")
        return
    if "progress_df" not in st.session_state or st.session_state.progress_df.empty:
        st.warning("Progress report not loaded.")
        return
    if "advising_selections" not in st.session_state:
        st.session_state.advising_selections = {}

    # ---------- Student picker ----------
    students_df = st.session_state.progress_df.copy()
    students_df["DISPLAY"] = students_df["NAME"].astype(str) + " — " + students_df["ID"].astype(str)
    choice = st.selectbox("Select a student", students_df["DISPLAY"].tolist())
    selected_student_id = int(students_df.loc[students_df["DISPLAY"] == choice, "ID"].iloc[0])
    student_row = students_df.loc[students_df["ID"] == selected_student_id].iloc[0]

    # Ensure selection bucket (backward-compatible default keys)
    slot = st.session_state.advising_selections.setdefault(
        selected_student_id, {"advised": [], "optional": [], "excluded": [], "note": ""}
    )
    if "excluded" not in slot:
        slot["excluded"] = []

    # Credits/Standing
    credits_completed = float(student_row.get("# of Credits Completed", 0) or 0)
    credits_registered = float(student_row.get("# Registered", 0) or 0)
    total_credits = credits_completed + credits_registered
    standing = get_student_standing(total_credits)

    st.write(
        f"**Name:** {student_row['NAME']}  |  **ID:** {selected_student_id}  |  "
        f"**Credits:** {int(total_credits)}  |  **Standing:** {standing}"
    )

    # Convenience: course code lists
    all_course_codes = [str(c) for c in st.session_state.courses_df["Course Code"].tolist()]
    excluded_set = set([str(x) for x in (slot.get("excluded") or [])])

    # ---------- Build eligibility + justifications dicts (for non-excluded only) ----------
    status_dict: dict[str, str] = {}
    justification_dict: dict[str, str] = {}

    current_advised_for_checks = list(slot.get("advised", []))  # used only for eligibility engine

    for course_code in st.session_state.courses_df["Course Code"]:
        code = str(course_code)
        if code in excluded_set:
            continue
        status, justification = check_eligibility(
            student_row, code, current_advised_for_checks, st.session_state.courses_df
        )
        status_dict[code] = status
        justification_dict[code] = justification

    # ---------- Build display dataframe (skip excluded) ----------
    rows = []
    for course_code in st.session_state.courses_df["Course Code"]:
        code = str(course_code)
        if code in excluded_set:
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

    # ---------- Advising selections form (advised / optional / excluded) ----------
    # Offered set from the current courses table
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
        # Must be offered, not completed, not registered, eligible, and NOT excluded
        elig: list[str] = []
        for c in map(str, st.session_state.courses_df["Course Code"].tolist()):
            if c in excluded_set:
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

    # Sanitize saved defaults -> ensure list[str], intersect with current options
    saved_advised = [str(x) for x in (slot.get("advised", []) or []) if str(x) not in excluded_set]
    saved_optional = [str(x) for x in (slot.get("optional", []) or []) if str(x) not in excluded_set]

    default_advised = [c for c in saved_advised if c in opts_set]
    dropped_advised = sorted(set(saved_advised) - set(default_advised))

    # optional options are those not chosen as advised
    opt_space_now = [c for c in eligible_options if c not in default_advised]
    opt_space_set = set(opt_space_now)
    default_optional = [c for c in saved_optional if c in opt_space_set]
    dropped_optional = sorted(set(saved_optional) - set(default_optional))

    # Excluded multiselect (options = all course codes)
    saved_excluded = [str(x) for x in (slot.get("excluded", []) or [])]
    all_codes_sorted = sorted(all_course_codes)
    default_excluded = [c for c in saved_excluded if c in all_codes_sorted]
    dropped_excluded = sorted(set(saved_excluded) - set(default_excluded))

    with st.form(key=f"advise_form_{selected_student_id}"):
        # Advised / Optional
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

        # Excluded (hidden-from-view) — under an expander to keep UI tidy
        with st.expander("Courses not required for this student (Excluded)"):
            excluded_selection = st.multiselect(
                "Exclude courses (they will not appear in this student's tables or reports)",
                options=all_codes_sorted,
                default=default_excluded,
                key=f"excluded_ms_{selected_student_id}",
            )
            st.caption("Tip: use search to find courses fast. Exclusions persist in saved sessions.")

        note_input = st.text_area(
            "Advisor Note (optional)",
            value=slot.get("note", ""),
            key=f"note_{selected_student_id}",
        )

        # Non-blocking notice if anything was dropped from defaults
        if dropped_advised or dropped_optional or dropped_excluded:
            with st.expander("Some saved items aren’t available now"):
                if dropped_advised:
                    st.write("**Advised (no longer eligible/available):** ", ", ".join(dropped_advised))
                if dropped_optional:
                    st.write("**Optional (no longer eligible/available):** ", ", ".join(dropped_optional))
                if dropped_excluded:
                    st.write("**Excluded (not found in current course list):** ", ", ".join(dropped_excluded))
                st.caption(
                    "This can happen if the course list changed or the course is not present this term. "
                    "Your saved session remains intact."
                )

        submitted = st.form_submit_button("Save Selections")
        if submitted:
            st.session_state.advising_selections[selected_student_id] = {
                "advised": advised_selection,
                "optional": optional_selection,
                "excluded": excluded_selection,
                "note": note_input,
            }
            st.success("Selections saved.")
            log_info(f"Saved selections for {selected_student_id}")
            st.rerun()

    # ---------- Download report (already respects exclusions via courses_display_df) ----------
    st.subheader("Download Advising Report")
    if st.button("Download Student Report"):
        report_df = courses_display_df.copy()
        output = BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            report_df.to_excel(writer, index=False, sheet_name="Advising")
        # credits computation uses only advised/optional shown (excluded already filtered from selects)
        advised_selection = st.session_state.advising_selections[selected_student_id].get("advised", [])
        optional_selection = st.session_state.advising_selections[selected_student_id].get("optional", [])

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
        )
