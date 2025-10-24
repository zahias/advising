# eligibility_view.py
from __future__ import annotations

import streamlit as st
import pandas as pd
from io import BytesIO
from typing import Dict, List, Any

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
from course_exclusions import (
    ensure_loaded as ensure_exclusions_loaded,
    get_for_student,
    set_for_student,
)
from advising_history import save_session_for_student
from student_search import render_student_search
from action_dock import render_action_dock
from notification_system import show_notification, show_action_feedback


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

    main_col, action_col = st.columns([3, 1])
    
    with main_col:
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
        student_row = row.iloc[0]

        hidden_for_student = set(map(str, get_for_student(norm_sid)))

        # per-student advising slot
        sels = st.session_state.advising_selections
        slot = sels.get(norm_sid)
        if slot is None:
            # migrate if a stray str/int key exists
            alt = sels.get(str(norm_sid)) if isinstance(norm_sid, int) else None
            if alt:
                slot = alt
                sels.pop(str(norm_sid))
            else:
                slot = {"advised": [], "optional": [], "note": ""}
            sels[norm_sid] = slot

        # header stats
        cr_comp = float(student_row.get("# of Credits Completed", 0) or 0)
        cr_reg = float(student_row.get("# Registered", 0) or 0)
        total_credits = cr_comp + cr_reg
        standing = get_student_standing(total_credits)

        st.markdown(f"### {student_row['NAME']}")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Credits", int(total_credits))
        with col2:
            st.metric("Standing", standing)
        with col3:
            advised_count = len(slot.get("advised", []) or [])
            st.metric("Advised Courses", advised_count)

        # ---------- Eligibility map (skip hidden) ----------
        status_dict: Dict[str, str] = {}
        justification_dict: Dict[str, str] = {}
        current_advised_for_checks = list(slot.get("advised", []))
        for course_code in st.session_state.courses_df["Course Code"]:
            code = str(course_code)
            if code in hidden_for_student:
                continue
            status, justification = check_eligibility(
                student_row, code, current_advised_for_checks, st.session_state.courses_df
            )
            status_dict[code] = status
            justification_dict[code] = justification

        # ---------- Build display rows (screen Action shows ONLY Advised / Optional) ----------
        rows = []
        for _, info in st.session_state.courses_df.iterrows():
            code = str(info["Course Code"])
            if code in hidden_for_student:
                continue
            if code in (slot.get("advised", []) or []):
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
            st.dataframe(style_df(req_df), width='stretch')
        if not int_df.empty:
            st.markdown("**Intensive Courses**")
            st.dataframe(style_df(int_df), width='stretch')

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
                if status_dict.get(c) == "Eligible":
                    opts.append(c)
            return sorted(opts)

        eligible_opts = _eligible_options()
        optset = set(eligible_opts)

        default_advised = [c for c in (slot.get("advised", []) or []) if c in optset]
        default_optional = [c for c in (slot.get("optional", []) or []) if c in optset and c not in default_advised]

        # ---------- Save form (explicit autosave for *this* student) ----------
        st.markdown("---")
        st.markdown("### Advising Recommendations")
        with st.form(key=f"advise_form_{norm_sid}"):
            advised_selection = st.multiselect(
                "Advised Courses", options=eligible_opts, default=default_advised, key=f"advised_ms_{norm_sid}"
            )
            optional_selection = st.multiselect(
                "Optional Courses",
                options=[c for c in eligible_opts if c not in advised_selection],
                default=[c for c in default_optional if c not in advised_selection],
                key=f"optional_ms_{norm_sid}",
            )
            note_input = st.text_area(
                "Advisor Note (optional)", value=slot.get("note", ""), key=f"note_{norm_sid}"
            )

            submitted = st.form_submit_button("💾 Save Selections", width='stretch', type="primary")
            if submitted:
                st.session_state.advising_selections[norm_sid] = {
                    "advised": advised_selection,
                    "optional": optional_selection,
                    "note": note_input,
                }

                # EXPLICIT autosave for this student (no reliance on globals)
                session_id = save_session_for_student(norm_sid)
                if session_id:
                    show_action_feedback("save", True, f"Session for {student_row['NAME']}")
                else:
                    show_action_feedback("save", False, "Check logs for details")

                # Option A: stay on this student (selected_student already persisted)
                st.rerun()

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

        # ---------- Download Report ----------
        if st.button("📥 Download Student Report", width='stretch'):
            export_df = display_df.copy()
            for col in ("Type", "Requisites"):
                if col in export_df.columns:
                    export_df.drop(columns=[col], inplace=True)

            output = BytesIO()
            with pd.ExcelWriter(output, engine="openpyxl") as writer:
                export_df.to_excel(writer, index=False, sheet_name="Advising")

            apply_excel_formatting(
                output=output,
                student_name=str(student_row["NAME"]),
                student_id=norm_sid,
                credits_completed=int(cr_comp),
                standing=standing,
                note=st.session_state.advising_selections[norm_sid].get("note", ""),
                advised_credits=_sum_credits(st.session_state.advising_selections[norm_sid].get("advised", [])),
                optional_credits=_sum_credits(st.session_state.advising_selections[norm_sid].get("optional", [])),
            )
            st.download_button(
                "Download Excel",
                data=output.getvalue(),
                file_name=f"Advising_{norm_sid}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                width='stretch',
            )
    
    # ---------- Action Dock (Right Sidebar) ----------
    with action_col:
        def _save_callback():
            slot = st.session_state.advising_selections.get(norm_sid, {})
            session_id = save_session_for_student(norm_sid)
            if session_id:
                show_action_feedback("save", True, "Session saved")
            else:
                show_action_feedback("save", False)
        
        def _email_callback():
            from email_manager import get_student_email, send_advising_email
            
            student_email = get_student_email(str(norm_sid))
            if not student_email:
                show_notification(
                    f"No email found for student {norm_sid}. Upload email roster first.",
                    "error",
                    persistent=True
                )
            else:
                slot = st.session_state.advising_selections.get(norm_sid, {})
                advised_list = slot.get("advised", []) or []
                optional_list = slot.get("optional", []) or []
                note = slot.get("note", "")
                
                success, message = send_advising_email(
                    to_email=student_email,
                    student_name=str(student_row["NAME"]),
                    student_id=str(norm_sid),
                    advised_courses=advised_list,
                    optional_courses=optional_list,
                    note=note,
                    courses_df=st.session_state.courses_df,
                )
                
                if success:
                    show_action_feedback("email", True, f"Sent to {student_email}")
                    log_info(f"Advising email sent to {student_email} for student {norm_sid}")
                else:
                    show_action_feedback("email", False, message)
        
        render_action_dock(
            student_id=norm_sid,
            on_save=_save_callback,
            on_email=_email_callback,
            show_exclusions=True,
            on_toggle_exclusions=None
        )
