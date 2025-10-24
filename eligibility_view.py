# eligibility_view.py

import streamlit as st
import pandas as pd
from io import BytesIO
from typing import Dict, List

from utils import (
    check_eligibility,
    check_course_completed,
    check_course_registered,
    get_student_standing,
    log_info, log_error,
)
from reporting import apply_excel_formatting
from advising_history import autosave_current_student_session
from course_exclusions import ensure_exclusions_loaded, get_for_student

def student_eligibility_view():
    if "courses_df" not in st.session_state or st.session_state.courses_df.empty:
        st.warning("Courses table not loaded.")
        return
    if "progress_df" not in st.session_state or st.session_state.progress_df.empty:
        st.warning("Progress report not loaded.")
        return
    if "advising_selections" not in st.session_state:
        st.session_state.advising_selections = {}

    # Load per-student hidden courses
    ensure_exclusions_loaded()

    # ---------- Student picker ----------
    students_df = st.session_state.progress_df.copy()
    students_df["DISPLAY"] = students_df["NAME"].astype(str) + " — " + students_df["ID"].astype(str)
    choice = st.selectbox("Select a student", students_df["DISPLAY"].tolist(), key="elig_select_student")
    selected_student_id = int(students_df.loc[students_df["DISPLAY"] == choice, "ID"].iloc[0])
    student_row = students_df.loc[students_df["ID"] == selected_student_id].iloc[0]

    # Single source of truth for current student (used by autosave & sessions panel)
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
    status_dict: Dict[str, str] = {}
    justification_dict: Dict[str, str] = {}
    current_advised_for_checks = list(slot.get("advised", []))  # for eligibility engine

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
    rows_required: List[Dict] = []
    rows_intensive: List[Dict] = []

    def _row_for(code: str, title: str, ctype: str) -> Dict:
        # Screen table "Action" shows ONLY Advised / Optional (per your request)
        if code in (slot.get("advised") or []):
            action = "Advised"
        elif code in (slot.get("optional") or []):
            action = "Optional"
        else:
            action = ""

        return {
            "Course Code": code,
            "Title": title,
            "Credits": st.session_state.courses_df.set_index("Course Code").loc[code].get("Credits", ""),
            "Eligibility Status": status_dict.get(code, ""),
            "Justification": justification_dict.get(code, ""),
            "Action": action,
            "Type": ctype,                # kept only for screen; dropped in export below
            "Requisites": st.session_state.courses_df.set_index("Course Code").loc[code].get("Requisites", ""),
        }

    for _, info in st.session_state.courses_df.iterrows():
        code = str(info["Course Code"])
        if code in hidden_for_student:
            continue
        title = str(info.get("Title", ""))
        ctype = str(info.get("Type", "")).strip().lower()
        (rows_intensive if ctype == "intensive" else rows_required).append(_row_for(code, title, ctype))

    # ---------- UI: pick Advised / Optional (eligible only) + Notes ----------
    eligible_codes = [c for c, s in status_dict.items() if s == "Eligible" and c not in hidden_for_student]

    with st.form(key=f"advise_form_{selected_student_id}", clear_on_submit=False):
        advised_selection = st.multiselect(
            "Advised Courses", options=eligible_codes,
            default=[c for c in slot.get("advised", []) if c in eligible_codes],
            help="Only eligible courses can be advised."
        )
        optional_selection = st.multiselect(
            "Optional Courses", options=eligible_codes,
            default=[c for c in slot.get("optional", []) if c in eligible_codes],
            help="Only eligible courses can be optional."
        )
        note = st.text_area("Advisor Notes", value=slot.get("note", ""), placeholder="Notes for this student...")

        submitted = st.form_submit_button("Save Selections")

    if submitted:
        # Update in-memory selection for this student
        slot["advised"] = advised_selection
        slot["optional"] = optional_selection
        slot["note"] = note
        st.session_state.advising_selections[selected_student_id] = slot

        # AUTOSAVE: create a per-student advising session snapshot immediately
        sid = autosave_current_student_session()
        if sid:
            st.toast("💾 Autosaved advising session", icon="✅")
        else:
            st.toast("Autosave failed (see logs).", icon="⚠️")

        st.rerun()

    # ---------- Show tables ----------
    st.markdown("### Required Courses")
    st.dataframe(pd.DataFrame(rows_required), use_container_width=True)

    st.markdown("### Intensive Courses")
    st.dataframe(pd.DataFrame(rows_intensive), use_container_width=True)

    # ---------- Export single-student advising sheet (clean columns + formatting) ----------
    if st.button("Download Student Advising Sheet"):
        export_rows = rows_required + rows_intensive
        df_export = pd.DataFrame(export_rows)

        # Remove columns you asked to drop from the Excel file
        for col in ("Type", "Requisites"):
            if col in df_export.columns:
                df_export.drop(columns=[col], inplace=True)

        # Write base sheet then apply formatting (header, borders, colors for Action)
        output = BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            df_export.to_excel(writer, index=False, sheet_name="Advising")

        # Pretty formatting + color code (Action has only Advised / Optional now)
        apply_excel_formatting(
            output=output,
            student_name=str(student_row["NAME"]),
            student_id=int(selected_student_id),
            credits_completed=int(credits_completed),
            standing=standing,
            note=slot.get("note", ""),
            advised_credits=_sum_credits(slot.get("advised", [])),
            optional_credits=_sum_credits(slot.get("optional", [])),
        )

        st.download_button(
            "Download Excel",
            data=output.getvalue(),
            file_name=f"Advising_{selected_student_id}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

def _sum_credits(course_codes: List[str]) -> int:
    if not course_codes:
        return 0
    cdf = st.session_state.courses_df.set_index("Course Code")
    total = 0
    for c in course_codes:
        try:
            total += int(float(cdf.loc[c].get("Credits", 0) or 0))
        except Exception:
            pass
    return total
