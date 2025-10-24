# eligibility_view.py
from __future__ import annotations

import streamlit as st
import pandas as pd
from io import BytesIO
from typing import Dict, List, Any

from utils import (
    check_course_completed,
    check_course_registered,
    check_eligibility,
    build_requisites_str,
    style_df,
    get_student_standing,
    log_info,
    log_error,
)
from reporting import apply_excel_formatting
from course_exclusions import ensure_exclusions_loaded, get_for_student, set_for_student
from advising_history import save_session_for_student


# ---------- helpers ----------
def _norm_id(v: Any):
    """Prefer int IDs if possible, else fallback to string."""
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


# ---------- main view ----------
def student_eligibility_view():
    """Per-student advising & eligibility (autosaves explicitly for the selected student)."""
    if "courses_df" not in st.session_state or st.session_state.courses_df.empty:
        st.warning("Courses table not loaded.")
        return
    if "progress_df" not in st.session_state or st.session_state.progress_df.empty:
        st.warning("Progress report not loaded.")
        return
    if "advising_selections" not in st.session_state:
        st.session_state.advising_selections = {}

    ensure_exclusions_loaded()

    # --- Student picker (keys are per-student to avoid state bleed) ---
    students_df = st.session_state.progress_df.copy()
    students_df["DISPLAY"] = students_df["NAME"].astype(str) + " — " + students_df["ID"].astype(str)
    choice = st.selectbox("Select a student", students_df["DISPLAY"].tolist(), key="elig_select_student")
    selected_student_id = students_df.loc[students_df["DISPLAY"] == choice, "ID"].iloc[0]
    norm_sid = _norm_id(selected_student_id)

    # Keep other panels aware (safe; saving does NOT depend on this)
    st.session_state["current_student_id"] = norm_sid

    # Robust row lookup (handles int/str IDs)
    pdf = st.session_state.progress_df
    try:
        student_row = pdf.loc[pdf["ID"] == norm_sid].iloc[0]
    except Exception:
        student_row = pdf.loc[pdf["ID"].astype(str) == str(norm_sid)].iloc[0]

    # Load hidden courses for this student
    hidden_set = set(map(str, get_for_student(norm_sid)))

    # Ensure per-student advising slot under normalized key
    sels = st.session_state.advising_selections
    slot = sels.get(norm_sid)
    if slot is None:
        # Try migrating from string key if that exists
        alt_key = str(norm_sid)
        if alt_key in sels:
            slot = sels.pop(alt_key)
        else:
            slot = {"advised": [], "optional": [], "note": ""}
        sels[norm_sid] = slot

    # Header stats
    cr_comp = float(student_row.get("# of Credits Completed", 0) or 0)
    cr_reg = float(student_row.get("# Registered", 0) or 0)
    total_cr = cr_comp + cr_reg
    standing = get_student_standing(total_cr)

    st.write(
        f"**Name:** {student_row['NAME']}  |  **ID:** {norm_sid}  |  "
        f"**Credits:** {int(total_cr)}  |  **Standing:** {standing}"
    )

    # --- Eligibility map (skip hidden) ---
    status_by_course: Dict[str, str] = {}
    just_by_course: Dict[str, str] = {}
    for code in st.session_state.courses_df["Course Code"].astype(str):
        if code in hidden_set:
            continue
        status, just = check_eligibility(
            student_row, code, list(slot.get("advised", [])), st.session_state.courses_df
        )
        status_by_course[code] = status
        just_by_course[code] = just

    # --- Screen rows: Action shows ONLY Advised / Optional (per your request) ---
    rows: List[Dict[str, Any]] = []
    cdf = st.session_state.courses_df
    for _, info in cdf.iterrows():
        code = str(info["Course Code"])
        if code in hidden_set:
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
                "Eligibility Status": status_by_course.get(code, ""),
                "Justification": just_by_course.get(code, ""),
                "Offered": str(info.get("Offered", "")).strip().lower() == "yes",
                "Action": action,
            }
        )

    df_display = pd.DataFrame(rows)
    req_df = df_display[df_display["Type"].astype(str).str.lower() == "required"].copy()
    int_df = df_display[df_display["Type"].astype(str).str.lower() == "intensive"].copy()

    st.markdown("### Course Eligibility")
    if not req_df.empty:
        st.markdown("**Required Courses**")
        st.dataframe(style_df(req_df), use_container_width=True)
    if not int_df.empty:
        st.markdown("**Intensive Courses**")
        st.dataframe(style_df(int_df), use_container_width=True)

    # --- Eligible + offered options (not hidden / not completed / not registered) ---
    offered_yes = {
        str(c)
        for c in cdf.loc[cdf["Offered"].astype(str).str.lower() == "yes", "Course Code"].astype(str).tolist()
    }

    def _eligible_opts() -> List[str]:
        opts: List[str] = []
        for code in cdf["Course Code"].astype(str):
            if code in hidden_set:
                continue
            if code not in offered_yes:
                continue
            if check_course_completed(student_row, code) or check_course_registered(student_row, code):
                continue
            if status_by_course.get(code) == "Eligible":
                opts.append(code)
        return sorted(opts)

    eligible_options = _eligible_opts()
    optset = set(eligible_options)

    default_advised = [c for c in (slot.get("advised", []) or []) if c in optset]
    default_optional = [c for c in (slot.get("optional", []) or []) if c in optset and c not in default_advised]

    # --- Save form (EXPLICIT autosave for this student) ---
    with st.form(key=f"advise_form_{norm_sid}"):
        advised_selection = st.multiselect(
            "Advised Courses",
            options=eligible_options,
            default=default_advised,
            key=f"advised_ms_{norm_sid}",
        )
        optional_selection = st.multiselect(
            "Optional Courses",
            options=[c for c in eligible_options if c not in advised_selection],
            default=[c for c in default_optional if c not in advised_selection],
            key=f"optional_ms_{norm_sid}",
        )
        note_input = st.text_area(
            "Advisor Note (optional)",
            value=slot.get("note", ""),
            key=f"note_{norm_sid}",
        )

        submitted = st.form_submit_button("Save Selections")
        if submitted:
            st.session_state.advising_selections[norm_sid] = {
                "advised": advised_selection,
                "optional": optional_selection,
                "note": note_input,
            }

            # *** CRITICAL: save explicitly for THIS student (no global lookup) ***
            sid = save_session_for_student(norm_sid)
            if sid:
                st.toast(f"✅ Auto-saved session for {student_row['NAME']} ({norm_sid})", icon="💾")
            else:
                st.toast("⚠️ Saved picks, but autosave failed (see logs).", icon="⚠️")
            st.rerun()

    # --- Hidden courses manager (persisted) ---
    with st.expander("Hidden courses for this student"):
        all_codes = sorted(map(str, cdf["Course Code"].tolist()))
        def_hidden = [c for c in all_codes if c in hidden_set]
        new_hidden = st.multiselect(
            "Remove (hide) these courses",
            options=all_codes,
            default=def_hidden,
            key=f"hidden_ms_{norm_sid}",
            help="Hidden courses don't appear in tables or selection lists; persisted per student.",
        )
        if st.button("Save Hidden Courses", key=f"save_hidden_{norm_sid}"):
            set_for_student(norm_sid, new_hidden)
            st.success("Hidden courses saved.")
            st.rerun()

<<<<<<< HEAD
    # --- Export student report (drop Type/Requisites; keep Action = Advised/Optional) ---
    if st.button("Download Student Report"):
        export_df = df_display.copy()
        for col in ("Type", "Requisites"):
            if col in export_df.columns:
                export_df.drop(columns=[col], inplace=True)
=======
    # ---------- Download and Email student report ----------
    col1, col2 = st.columns([1, 1])
    
    with col1:
        if st.button("📥 Download Student Report"):
            export_df = display_df.copy()
            for col in ("Type", "Requisites"):
                if col in export_df.columns:
                    export_df.drop(columns=[col], inplace=True)
>>>>>>> b6378eea1124023c16183761cb2f19f63d279c8d

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
            )
    
    with col2:
        if st.button("📧 Email Advising Sheet", key=f"email_elig_{norm_sid}"):
            from email_manager import get_student_email, send_advising_email
            
            student_email = get_student_email(str(norm_sid))
            if not student_email:
                st.error(f"No email address found for student {norm_sid}. Please upload email roster first.")
            else:
                # Get advising selections
                advised_list = slot.get("advised", []) or []
                optional_list = slot.get("optional", []) or []
                note = slot.get("note", "")
                
                # Send email
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
                    st.success(f"✅ {message}")
                    log_info(f"Advising email sent to {student_email} for student {norm_sid}")
                else:
                    st.error(f"❌ {message}")
