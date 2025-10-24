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


def _norm_id(v: Any):
    """Use int IDs when possible; else fallback to str."""
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


def student_eligibility_view():
    """Per-student advising & eligibility."""
    if "courses_df" not in st.session_state or st.session_state.courses_df.empty:
        st.warning("Courses table not loaded.")
        return
    if "progress_df" not in st.session_state or st.session_state.progress_df.empty:
        st.warning("Progress report not loaded.")
        return
    if "advising_selections" not in st.session_state:
        st.session_state.advising_selections = {}

    ensure_exclusions_loaded()

    # ---------- Student picker (explicit per-student keys) ----------
    students_df = st.session_state.progress_df.copy()
    students_df["DISPLAY"] = students_df["NAME"].astype(str) + " — " + students_df["ID"].astype(str)
    choice = st.selectbox("Select a student", students_df["DISPLAY"].tolist(), key="elig_select_student")
    selected_student_id = students_df.loc[students_df["DISPLAY"] == choice, "ID"].iloc[0]
    norm_sid = _norm_id(selected_student_id)

    # keep other panels aware (doesn't affect saving)
    st.session_state["current_student_id"] = norm_sid

    # find the row for this student, robust to id dtype
    try:
        student_row = st.session_state.progress_df.loc[st.session_state.progress_df["ID"] == norm_sid].iloc[0]
    except Exception:
        student_row = st.session_state.progress_df.loc[
            st.session_state.progress_df["ID"].astype(str) == str(norm_sid)
        ].iloc[0]

    hidden_for_student = set(map(str, get_for_student(norm_sid)))

    # ensure per-student advising slot uses the normalized key
    sels = st.session_state.advising_selections
    slot = sels.get(norm_sid)
    if slot is None:
        # migrate from alternate key if present
        alt_key = str(norm_sid) if isinstance(norm_sid, int) else None
        if alt_key is not None and alt_key in sels:
            slot = sels.pop(alt_key)
            sels[norm_sid] = slot
        else:
            slot = {"advised": [], "optional": [], "note": ""}
            sels[norm_sid] = slot

    # header stats
    cr_comp = float(student_row.get("# of Credits Completed", 0) or 0)
    cr_reg = float(student_row.get("# Registered", 0) or 0)
    total_credits = cr_comp + cr_reg
    standing = get_student_standing(total_credits)

    st.write(
        f"**Name:** {student_row['NAME']}  |  **ID:** {norm_sid}  |  "
        f"**Credits:** {int(total_credits)}  |  **Standing:** {standing}"
    )

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

    # ---------- Build display rows (screen shows ONLY Advised / Optional in Action) ----------
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

    st.markdown("### Course Eligibility")
    if not req_df.empty:
        st.markdown("**Required Courses**")
        st.dataframe(style_df(req_df), use_container_width=True)
    if not int_df.empty:
        st.markdown("**Intensive Courses**")
        st.dataframe(style_df(int_df), use_container_width=True)

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

    # ---------- Save form (EXPLICIT autosave for this student) ----------
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

        submitted = st.form_submit_button("Save Selections")
        if submitted:
            st.session_state.advising_selections[norm_sid] = {
                "advised": advised_selection,
                "optional": optional_selection,
                "note": note_input,
            }

            # EXPLICIT autosave for this student (no globals)
            session_id = save_session_for_student(norm_sid)
            if session_id:
                st.toast(f"✅ Auto-saved session for {student_row['NAME']} ({norm_sid})", icon="💾")
            else:
                st.toast("⚠️ Saved picks but autosave failed (see logs)", icon="⚠️")

            st.rerun()

    # ---------- Hidden courses manager (preserves existing behavior) ----------
    with st.expander("Hidden courses for this student"):
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
            st.success("Hidden courses saved.")
            st.rerun()

    # ---------- Download student report (drop Type/Requisites; keep Action) ----------
    if st.button("Download Student Report"):
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
        )
