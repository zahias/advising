# eligibility_view.py

import streamlit as st
import pandas as pd
from io import BytesIO
from typing import Dict, List

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
from advising_history import save_session_for_student

def student_eligibility_view():
    if "courses_df" not in st.session_state or st.session_state.courses_df.empty:
        st.warning("Courses table not loaded.")
        return
    if "progress_df" not in st.session_state or st.session_state.progress_df.empty:
        st.warning("Progress report not loaded.")
        return
    if "advising_selections" not in st.session_state:
        st.session_state.advising_selections = {}

    ensure_exclusions_loaded()

    # --- Student picker (explicit per-student keys) ---
    students_df = st.session_state.progress_df.copy()
    students_df["DISPLAY"] = students_df["NAME"].astype(str) + " — " + students_df["ID"].astype(str)
    choice = st.selectbox("Select a student", students_df["DISPLAY"].tolist(), key="elig_select_student")
    selected_student_id = students_df.loc[students_df["DISPLAY"] == choice, "ID"].iloc[0]
    st.session_state["current_student_id"] = selected_student_id  # keep other panels aware

    student_row = students_df.loc[students_df["ID"] == selected_student_id].iloc[0]
    hidden_for_student = set(map(str, get_for_student(selected_student_id)))

    # ensure per-student storage
    slot = st.session_state.advising_selections.setdefault(
        selected_student_id, {"advised": [], "optional": [], "note": ""}
    )

    # header stats
    credits_completed = float(student_row.get("# of Credits Completed", 0) or 0)
    credits_registered = float(student_row.get("# Registered", 0) or 0)
    total_credits = credits_completed + credits_registered
    standing = get_student_standing(total_credits)

    st.write(
        f"**Name:** {student_row['NAME']}  |  **ID:** {selected_student_id}  |  "
        f"**Credits:** {int(total_credits)}  |  **Standing:** {standing}"
    )

    # --- Eligibility map (once per student) ---
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

    # --- Display rows (Action shows ONLY Advised / Optional) ---
    rows = []
    for _, info in st.session_state.courses_df.iterrows():
        code = str(info["Course Code"])
        if code in hidden_for_student:
            continue
        status = status_dict.get(code, "Not Eligible")
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
                "Eligibility Status": status,
                "Justification": justification_dict.get(code, ""),
                "Offered": str(info.get("Offered","")).strip().lower() == "yes",
                "Action": action,
            }
        )

    display_df = pd.DataFrame(rows)
    req_df = display_df[display_df["Type"].str.lower() == "required"].copy() if "Type" in display_df.columns else display_df.copy()
    int_df = display_df[display_df["Type"].str.lower() == "intensive"].copy() if "Type" in display_df.columns else pd.DataFrame()

    st.markdown("### Course Eligibility")
    if not req_df.empty:
        st.markdown("**Required Courses**")
        st.dataframe(style_df(req_df), use_container_width=True)
    if not int_df.empty:
        st.markdown("**Intensive Courses**")
        st.dataframe(style_df(int_df), use_container_width=True)

    # --- Eligible options builder ---
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

    eligible_options = _eligible_for_selection()
    opts_set = set(eligible_options)

    saved_advised = [str(x) for x in (slot.get("advised", []) or []) if str(x) not in hidden_for_student]
    saved_optional = [str(x) for x in (slot.get("optional", []) or []) if str(x) not in hidden_for_student]
    default_advised = [c for c in saved_advised if c in opts_set]
    default_optional = [c for c in saved_optional if c in opts_set and c not in default_advised]

    # --- Save form (explicit per-student widget keys) ---
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

        submitted = st.form_submit_button("Save Selections")
        if submitted:
            # normalize key once (int if possible)
            try:
                norm_key = int(selected_student_id)
            except Exception:
                norm_key = str(selected_student_id)

            # update memory for this student
            st.session_state.advising_selections[norm_key] = {
                "advised": advised_selection,
                "optional": optional_selection,
                "note": note_input,
            }
            st.session_state["current_student_id"] = norm_key

            # *** CRITICAL CHANGE: autosave explicitly for THIS student (no globals) ***
            session_id = save_session_for_student(norm_key)
            if session_id:
                st.toast(f"✅ Auto-saved session for {student_row['NAME']} ({norm_key})", icon="💾")
            else:
                st.toast("⚠️ Saved picks, but autosave failed (see logs)", icon="⚠️")

            st.rerun()

    # --- Export single-student sheet (drops Type/Requisites; keeps Action = Advised/Optional) ---
    if st.button("Download Student Report"):
        report_df = display_df.copy()
        for col in ("Type", "Requisites"):
            if col in report_df.columns:
                report_df.drop(columns=[col], inplace=True)

        output = BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            report_df.to_excel(writer, index=False, sheet_name="Advising")

        apply_excel_formatting(
            output=output,
            student_name=str(student_row["NAME"]),
            student_id=int(selected_student_id) if str(selected_student_id).isdigit() else str(selected_student_id),
            credits_completed=int(credits_completed),
            standing=standing,
            note=st.session_state.advising_selections.get(norm_key, slot).get("note", ""),
            advised_credits=_sum_credits(st.session_state.advising_selections.get(norm_key, slot).get("advised", [])),
            optional_credits=_sum_credits(st.session_state.advising_selections.get(norm_key, slot).get("optional", [])),
        )
        st.download_button(
            "Download Excel",
            data=output.getvalue(),
            file_name=f"Advising_{selected_student_id}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

def _sum_credits(codes: List[str]) -> int:
    if not codes:
        return 0
    if "Credits" not in st.session_state.courses_df.columns:
        return 0
    lookup = st.session_state.courses_df.set_index(st.session_state.courses_df["Course Code"].astype(str))["Credits"]
    total = 0.0
    for c in codes:
        try:
            total += float(lookup.get(str(c), 0) or 0)
        except Exception:
            pass
    return int(total)
