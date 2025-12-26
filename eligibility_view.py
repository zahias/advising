# eligibility_view.py
from __future__ import annotations

import streamlit as st
import pandas as pd
from io import BytesIO
from typing import Dict, List, Any

from eligibility_utils import (
    check_course_completed,
    check_course_registered,
    is_course_offered,
    check_eligibility,
    build_requisites_str,
    get_student_standing,
    get_mutual_concurrent_pairs,
)
from utils import (
    style_df,
    log_info,
    log_error,
    get_student_selections,
    get_student_bypasses,
)
from reporting import apply_excel_formatting
from course_exclusions import (
    ensure_loaded as ensure_exclusions_loaded,
    get_for_student,
    set_for_student,
)
from advising_history import save_session_for_student, _load_session_and_apply
from student_search import render_student_search
from notification_system import show_notification, show_action_feedback
from advising_period import get_current_period


# ---------- helpers ----------

def _norm_id(v: Any):
    """Prefer int IDs; otherwise keep as str."""
    try:
        return int(v)
    except Exception:
        return str(v)


def _sum_credits(codes: List[str]) -> int:
    if not codes:
        return 0
    cdf = st.session_state.courses_df
    if cdf is None or cdf.empty or "Credits" not in cdf.columns:
        return 0
    lookup = cdf.set_index(cdf["Course Code"].astype(str))["Credits"]
    total = 0.0
    for c in codes:
        try:
            total += float(lookup.get(str(c), 0) or 0)
        except Exception:
            pass
    return int(total)


# ---------- main panel ----------

def student_eligibility_view():
    """Per-student advising & eligibility with modern UI."""
    if "courses_df" not in st.session_state or st.session_state.courses_df.empty:
        st.warning("Courses table not loaded.")
        return
    if "progress_df" not in st.session_state or st.session_state.progress_df.empty:
        st.warning("Progress report not loaded.")
        return
    if "advising_selections" not in st.session_state:
        st.session_state.advising_selections = {}

    ensure_exclusions_loaded()

    selected_student_id = render_student_search("eligibility")
    
    if selected_student_id is None:
        return
    
    norm_sid = _norm_id(selected_student_id)
    st.session_state["current_student_id"] = norm_sid

    # robust row fetch
    pdf = st.session_state.progress_df
    row = pdf.loc[pdf["ID"] == norm_sid]
    if row.empty:
        row = pdf.loc[pdf["ID"].astype(str) == str(norm_sid)]
    if row.empty:
        st.error(f"Student ID {norm_sid} not found in progress report. Please verify the ID or re-upload the progress report.")
        return
    student_row = row.iloc[0]

    hidden_for_student = set(map(str, get_for_student(norm_sid)))

    # per-student advising slot and bypasses
    slot = get_student_selections(norm_sid)
    st.session_state.advising_selections[norm_sid] = slot
    
    # Auto-load most recent advising session for this student
    # Only load if the slot is empty (all empty lists/strings)
    advised_list = slot.get("advised", [])
    optional_list = slot.get("optional", [])
    repeat_list = slot.get("repeat", [])
    note_val = slot.get("note", "")
    
    is_empty = not (advised_list or optional_list or repeat_list or note_val.strip())
    
    if is_empty and f"_autoloaded_{norm_sid}" not in st.session_state:
        _load_session_and_apply(norm_sid)
        st.session_state[f"_autoloaded_{norm_sid}"] = True

    major = st.session_state.get("current_major", "")
    student_bypasses = get_student_bypasses(norm_sid, major)

    # header stats
    cr_comp = float(student_row.get("# of Credits Completed", 0) or 0)
    cr_reg = float(student_row.get("# Registered", 0) or 0)
    cr_remaining = float(student_row.get("# Remaining", 0) or 0)
    total_credits = cr_comp + cr_reg
    standing = get_student_standing(total_credits)

    st.markdown(f"### {student_row['NAME']}")
    
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric("Total Credits", f"{int(total_credits)} / {int(cr_remaining)} rem")
    with col2:
        st.metric("Standing", standing)
    with col3:
        # Advised count includes repeat courses
        advised_list = slot.get("advised", []) or []
        repeat_list = slot.get("repeat", []) or []
        advised_count = len(advised_list) + len(repeat_list)
        advised_credits = _sum_credits(advised_list) + _sum_credits(repeat_list)
        st.metric("Advised Courses", f"{advised_count} ({advised_credits} cr)")
    with col4:
        optional_list = slot.get("optional", []) or []
        optional_count = len(optional_list)
        optional_credits = _sum_credits(optional_list)
        st.metric("Optional Courses", f"{optional_count} ({optional_credits} cr)")
    with col5:
        pass  # Empty column for spacing

    # ---------- Eligibility map (skip hidden) ----------
    status_dict: Dict[str, str] = {}
    justification_dict: Dict[str, str] = {}
    # Include both advised AND optional courses for concurrent/corequisite checks
    # Guard against None values from legacy sessions
    advised_list = slot.get("advised") or []
    optional_for_checks = slot.get("optional") or []
    current_advised_for_checks = list(advised_list) + list(optional_for_checks)
    
    # Compute mutual concurrent/corequisite pairs once for the courses table
    mutual_pairs = get_mutual_concurrent_pairs(st.session_state.courses_df)
    
    for course_code in st.session_state.courses_df["Course Code"]:
        code = str(course_code)
        if code in hidden_for_student:
            continue
        status, justification = check_eligibility(
            student_row, code, current_advised_for_checks, st.session_state.courses_df, 
            registered_courses=[], mutual_pairs=mutual_pairs, bypass_map=student_bypasses
        )
        status_dict[code] = status
        justification_dict[code] = justification

    # ---------- Build display rows (screen Action shows Advised / Optional / Advised-Repeat) ----------
    rows = []
    for _, info in st.session_state.courses_df.iterrows():
        code = str(info["Course Code"])
        if code in hidden_for_student:
            continue
        if code in (slot.get("repeat", []) or []):
            action = "Advised-Repeat"
        elif code in (slot.get("advised", []) or []):
            action = "Advised"
        elif code in (slot.get("optional", []) or []):
            action = "Optional"
        else:
            action = ""
        rows.append(
            {
                "Course Code": code,
                "Type": info.get("Type", ""),
                "Requisites": build_requisites_str(info),
                "Eligibility Status": status_dict.get(code, ""),
                "Justification": justification_dict.get(code, ""),
                "Offered": str(info.get("Offered", "")).strip().lower() == "yes",
                "Action": action,
            }
        )

    display_df = pd.DataFrame(rows)
    req_df = display_df[display_df["Type"].astype(str).str.lower() == "required"].copy()
    int_df = display_df[display_df["Type"].astype(str).str.lower() == "intensive"].copy()

    st.markdown("---")
    st.markdown("### Course Eligibility")
    if not req_df.empty:
        st.markdown("**Required Courses**")
        st.dataframe(style_df(req_df), width="stretch")
    if not int_df.empty:
        st.markdown("**Intensive Courses**")
        st.dataframe(style_df(int_df), width="stretch")

    # ---------- Selection options (eligible + offered, not hidden/completed/registered) ----------
    offered_yes = {
        str(c) for c in st.session_state.courses_df.loc[
            st.session_state.courses_df["Offered"].astype(str).str.lower() == "yes",
            "Course Code",
        ].tolist()
    }

    def _eligible_options() -> List[str]:
        opts: List[str] = []
        for c in map(str, st.session_state.courses_df["Course Code"].tolist()):
            if c in hidden_for_student:
                continue
            if c not in offered_yes:
                continue
            if check_course_completed(student_row, c) or check_course_registered(student_row, c):
                continue
            status = status_dict.get(c, "")
            if status in ("Eligible", "Eligible (Bypass)"):
                opts.append(c)
        return sorted(opts)

    eligible_opts = _eligible_options()
    optset = set(eligible_opts)

    # Options for repeat: completed or registered courses
    def _repeat_options() -> List[str]:
        opts: List[str] = []
        for c in map(str, st.session_state.courses_df["Course Code"].tolist()):
            if c in hidden_for_student:
                continue
            if check_course_completed(student_row, c) or check_course_registered(student_row, c):
                opts.append(c)
        return sorted(opts)
    
    repeat_opts = _repeat_options()

    default_advised = [c for c in (slot.get("advised", []) or []) if c in optset]
    default_repeat = [c for c in (slot.get("repeat", []) or []) if c in repeat_opts]
    default_optional = [c for c in (slot.get("optional", []) or []) if c in optset]

    # ---------- Save form (explicit autosave for *this* student) ----------
    st.markdown("---")
    st.markdown("### Advising Recommendations")
    
    def _persist_student_selections(
        advised_selection: List[str],
        repeat_selection: List[str],
        optional_selection: List[str],
        note_value: str,
    ) -> None:
        # Enforce mutual exclusivity: remove any courses from optional that are in advised
        advised_set = set(advised_selection)
        clean_optional = [c for c in optional_selection if c not in advised_set]
        
        st.session_state.advising_selections[norm_sid] = {
            "advised": list(advised_selection),
            "repeat": list(repeat_selection),
            "optional": clean_optional,
            "note": note_value,
        }

    def _build_student_download_bytes(
        advised_selection: List[str],
        repeat_selection: List[str],
        optional_selection: List[str],
        note_value: str,
    ) -> bytes:
        export_df = display_df.copy()
        for col in ("Type", "Requisites"):
            if col in export_df.columns:
                export_df.drop(columns=[col], inplace=True)

        output = BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            export_df.to_excel(writer, index=False, sheet_name="Advising")

        current_period = get_current_period()
        period_info = (
            f"Advising Period: {current_period.get('semester', '')} {current_period.get('year', '')} — "
            f"Advisor: {current_period.get('advisor_name', '')}"
        )

        apply_excel_formatting(
            output=output,
            student_name=str(student_row["NAME"]),
            student_id=norm_sid,
            credits_completed=int(cr_comp),
            standing=standing,
            note=note_value,
            advised_credits=_sum_credits(advised_selection),
            optional_credits=_sum_credits(optional_selection),
            period_info=period_info,
        )

        output.seek(0)
        return output.getvalue()

    # Remove mutual exclusivity - advised courses shouldn't appear in optional options
    # We handle this dynamically: options for optional exclude current advised, and vice versa
    advised_key = f"advised_ms_{norm_sid}"
    optional_key = f"optional_ms_{norm_sid}"
    
    # Get current selections from session state (for real-time mutual exclusivity)
    current_advised_sel = set(st.session_state.get(advised_key, default_advised))
    current_optional_sel = set(st.session_state.get(optional_key, default_optional))
    
    # Filter options: optional can't include advised, advised can't include optional
    optional_opts = [c for c in eligible_opts if c not in current_advised_sel]
    advised_opts_filtered = [c for c in eligible_opts if c not in current_optional_sel]
    
    with st.form(key=f"advise_form_{norm_sid}"):
        advised_selection = st.multiselect(
            "Advised Courses (Eligible, Not Yet Taken)", 
            options=advised_opts_filtered, 
            default=[c for c in default_advised if c in advised_opts_filtered], 
            key=advised_key,
            help="Primary course recommendations for this student"
        )
        optional_selection = st.multiselect(
            "Optional Courses",
            options=optional_opts,
            default=[c for c in default_optional if c in optional_opts],
            key=optional_key,
            help="Additional optional courses (cannot overlap with Advised)"
        )
        repeat_selection = st.multiselect(
            "Repeat Courses (Completed or Registered)", options=repeat_opts, default=default_repeat, key=f"repeat_ms_{norm_sid}",
            help="Select courses that the student should repeat to improve GPA"
        )
        note_input = st.text_area(
            "Advisor Note (optional)", value=slot.get("note", ""), key=f"note_{norm_sid}"
        )

        # Two buttons side by side
        btn_col1, btn_col2 = st.columns(2)

        with btn_col1:
            submitted = st.form_submit_button("💾 Save Selections", width="stretch", type="primary")

        with btn_col2:
            email_clicked = st.form_submit_button("✉️ Email Student", width="stretch")

        if submitted or email_clicked:
            _persist_student_selections(advised_selection, repeat_selection, optional_selection, note_input)

            if submitted:
                # EXPLICIT autosave for this student
                session_id = save_session_for_student(norm_sid)
                # Mark as autoloaded so we don't reload from Drive and overwrite
                st.session_state[f"_autoloaded_{norm_sid}"] = True
                if session_id:
                    show_action_feedback("save", True, f"Session for {student_row['NAME']}")
                else:
                    show_action_feedback("save", False, "Check logs for details")
                st.rerun()

            elif email_clicked:
                # Email student
                from email_manager import get_student_email, send_advising_email

                student_email = get_student_email(str(norm_sid))
                if not student_email:
                    show_notification(
                        f"No email found for student {norm_sid}. Upload email roster first.",
                        "error",
                        persistent=True
                    )
                    st.rerun()
                else:
                    # Get period info for email
                    current_period = get_current_period()
                    period_info = f"{current_period.get('semester', '')} {current_period.get('year', '')} — Advisor: {current_period.get('advisor_name', '')}"

                    success, message = send_advising_email(
                        to_email=student_email,
                        student_name=str(student_row["NAME"]),
                        student_id=str(norm_sid),
                        advised_courses=list(advised_selection),
                        repeat_courses=list(repeat_selection),
                        optional_courses=list(optional_selection),
                        note=note_input,
                        courses_df=st.session_state.courses_df,
                        remaining_credits=int(cr_remaining),
                        period_info=period_info,
                    )

                    if success:
                        show_action_feedback("email", True, f"Sent to {student_email}")
                        log_info(f"Advising email sent to {student_email} for student {norm_sid}")
                    else:
                        show_action_feedback("email", False, message)
                    st.rerun()

    # ---------- Download Report ----------
    current_advised = slot.get("advised", []) or []
    current_repeat = slot.get("repeat", []) or []
    current_optional = slot.get("optional", []) or []
    current_note = slot.get("note", "")
    
    st.download_button(
        "📥 Download Current Advising Report",
        data=_build_student_download_bytes(
            current_advised,
            current_repeat,
            current_optional,
            current_note,
        ),
        file_name=f"Advising_{norm_sid}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        type="secondary",
        width="stretch",
        key=f"download_advising_{norm_sid}",
    )

    # ---------- Requisite Bypass Manager ----------
    with st.expander("🔓 Requisite Bypasses", expanded=len(student_bypasses) > 0):
        st.markdown("Grant a bypass to allow a student to register for a course without meeting prerequisites.")
        
        # Get courses that are "Not Eligible" (excluding hidden/completed/registered)
        not_eligible_courses = [
            code for code, status in status_dict.items()
            if status == "Not Eligible" and code not in hidden_for_student
        ]
        
        # Show existing bypasses
        if student_bypasses:
            st.markdown("**Active Bypasses:**")
            for course_code, bypass_info in list(student_bypasses.items()):
                col1, col2, col3 = st.columns([3, 5, 2])
                with col1:
                    st.markdown(f"**{course_code}**")
                with col2:
                    bypass_note = bypass_info.get("note", "")
                    bypass_advisor = bypass_info.get("advisor", "")
                    display_text = f"By {bypass_advisor}" if bypass_advisor else ""
                    if bypass_note:
                        display_text += f": {bypass_note}" if display_text else bypass_note
                    st.caption(display_text or "No note")
                with col3:
                    if st.button("Remove", key=f"remove_bypass_{norm_sid}_{course_code}", type="secondary"):
                        del student_bypasses[course_code]
                        st.session_state[bypasses_key][norm_sid] = student_bypasses
                        save_session_for_student(norm_sid)
                        show_action_feedback("save", True, f"Bypass removed for {course_code}")
                        st.rerun()
            st.markdown("---")
        
        # Add new bypass
        if not_eligible_courses:
            st.markdown("**Grant New Bypass:**")
            bypass_course = st.selectbox(
                "Course to bypass",
                options=not_eligible_courses,
                key=f"bypass_course_{norm_sid}",
                help="Select a course that is currently 'Not Eligible'"
            )
            
            # Show why it's not eligible
            if bypass_course:
                reason = justification_dict.get(bypass_course, "")
                if reason:
                    st.caption(f"Currently not eligible: {reason}")
            
            bypass_note = st.text_input(
                "Bypass reason (optional)",
                key=f"bypass_note_{norm_sid}",
                placeholder="e.g., Department chair approved, Transfer credit pending"
            )
            
            current_period = get_current_period()
            advisor_name = current_period.get("advisor_name", "")
            
            if st.button("Grant Bypass", key=f"grant_bypass_{norm_sid}", type="primary"):
                from datetime import datetime
                student_bypasses[bypass_course] = {
                    "note": bypass_note,
                    "advisor": advisor_name,
                    "timestamp": datetime.now().isoformat()
                }
                st.session_state[bypasses_key][norm_sid] = student_bypasses
                save_session_for_student(norm_sid)
                show_action_feedback("save", True, f"Bypass granted for {bypass_course}")
                st.rerun()
        else:
            if not student_bypasses:
                st.info("No courses currently need a bypass. All courses are either eligible, completed, or registered.")

    # ---------- Hidden courses manager ----------
    with st.expander("🚫 Manage Hidden Courses"):
        all_codes = sorted(map(str, st.session_state.courses_df["Course Code"].tolist()))
        def_hidden = [c for c in all_codes if c in hidden_for_student]
        new_hidden = st.multiselect(
            "Remove (hide) these courses",
            options=all_codes,
            default=def_hidden,
            key=f"hidden_ms_{norm_sid}",
            help="Hidden courses don't appear in tables or selection lists; persisted per student.",
        )
        if st.button("Save Hidden Courses", key=f"save_hidden_{norm_sid}"):
            set_for_student(norm_sid, new_hidden)
            show_action_feedback("save", True, "Hidden courses updated")
            st.rerun()
