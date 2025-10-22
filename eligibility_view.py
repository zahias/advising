# eligibility_view.py

from __future__ import annotations

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
    log_error,
)
from reporting import apply_excel_formatting
from course_exclusions import ensure_loaded as ensure_exclusions_loaded, get_for_student, set_for_student


def _get_limits_for_major(major: str) -> dict:
    try:
        conf = st.secrets.get("advising", {}).get("credit_limits", {})
        return dict(conf.get(major, {}))
    except Exception:
        return {}


def _sum_credits(codes: list[str], courses_df: pd.DataFrame) -> int:
    if courses_df is None or courses_df.empty or "Credits" not in courses_df.columns:
        return 0
    if not codes:
        return 0
    lookup = courses_df.set_index(courses_df["Course Code"].astype(str))["Credits"]
    total = 0.0
    for c in codes:
        try:
            val = float(lookup.get(str(c), 0) or 0)
            total += val
        except Exception:
            pass
    return int(total)


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

    # Load per-student exclusions
    ensure_exclusions_loaded()

    # ---------- Student picker ----------
    students_df = st.session_state.progress_df.copy()
    students_df["DISPLAY"] = students_df["NAME"].astype(str) + " — " + students_df["ID"].astype(str)
    choice = st.selectbox("Select a student", students_df["DISPLAY"].tolist())
    selected_student_id = int(students_df.loc[students_df["DISPLAY"] == choice, "ID"].iloc[0])
    student_row = students_df.loc[students_df["ID"] == selected_student_id].iloc[0]

    # Make selected student visible elsewhere (sessions list filter, autosave)
    st.session_state["current_student_id"] = selected_student_id

    hidden_for_student = set(map(str, get_for_student(selected_student_id)))

    slot = st.session_state.advising_selections.setdefault(
        selected_student_id, {"advised": [], "optional": [], "note": ""}
    )

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

    # ---------- Build display rows (Required / Intensive split) ----------
    rows = []
    for _, info in st.session_state.courses_df.iterrows():
        code = str(info["Course Code"])
        if code in hidden_for_student:
            continue

        offered = str(info.get("Offered", "")).strip().lower() == "yes"
        status = status_dict.get(code, "Not Eligible")

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
    offered_set = {
        str(c) for c in st.session_state.courses_df.loc[
            st.session_state.courses_df["Offered"].astype(str).str.lower() == "yes",
            "Course Code",
        ].tolist()
    }

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

    major = st.session_state.get("current_major", "")
    limits = _get_limits_for_major(major)

    with st.form(key=f"advise_form_{selected_student_id}"):
        advised_selection = st.multiselect(
            "Advised Courses",
            options=eligible_options,
            default=default_advised,
            key=f"advised_ms_{selected_student_id}",
        )
        optional_selection = st.multiselect(
            "Optional Courses",
            options=[c for c in eligible_options if c not in advised_selection],
            default=[c for c in default_optional if c not in advised_selection],
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

        # Live credit counters
        advised_credits = _sum_credits(advised_selection, st.session_state.courses_df)
        optional_credits = _sum_credits(optional_selection, st.session_state.courses_df)
        total_selected = advised_credits + optional_credits

        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric("Advised Credits", advised_credits)
            if limits.get("advised_max") and advised_credits > int(limits["advised_max"]):
                st.warning(f"Advised exceeds limit ({limits['advised_max']}).")
        with c2:
            st.metric("Optional Credits", optional_credits)
            if limits.get("optional_max") and optional_credits > int(limits["optional_max"]):
                st.warning(f"Optional exceeds limit ({limits['optional_max']}).")
        with c3:
            st.metric("Total Selected", total_selected)
            if limits.get("total_max") and total_selected > int(limits["total_max"]):
                st.error(f"Total exceeds limit ({limits['total_max']}).")

        submitted = st.form_submit_button("Save Selections")
        if submitted:
            # Persist current selection (includes NOTE)
            st.session_state.advising_selections[selected_student_id] = {
                "advised": advised_selection,
                "optional": optional_selection,
                "note": note_input,
            }
            log_info(f"Saved selections for {selected_student_id}")

            # Auto-save a per-student session (title = date/time + student)
            try:
                from advising_history import autosave_current_student_session
                session_id = autosave_current_student_session()
                if session_id:
                    st.toast("✅ Auto-saved advising session", icon="💾")
                else:
                    st.toast("Saved selections (session auto-save skipped)", icon="ℹ️")
            except Exception as e:
                st.toast("Saved selections (session auto-save failed)", icon="⚠️")
                log_error("Autosave advising session failed", e)

            st.success("Selections saved.")
            st.rerun()

    # ---------- Per-student hidden courses ----------
    with st.expander("Hidden courses for this student"):
        all_codes = sorted(map(str, st.session_state.courses_df["Course Code"].tolist()))
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

    # ---------- Download student report (keeps color formatting) ----------
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
            advised_credits=_sum_credits(slot.get("advised", []), st.session_state.courses_df),
            optional_credits=_sum_credits(slot.get("optional", []), st.session_state.courses_df),
        )
        st.download_button(
            "Download Excel",
            data=output.getvalue(),
            file_name=f"Advising_{selected_student_id}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
