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

def _require_state_keys():
    keys = ["progress_df", "courses_df", "advising_selections", "drive_service"]
    missing = [k for k in keys if k not in st.session_state]
    if missing:
        st.error(f"Missing session state: {missing}")
        return False
    return True

def _credits_total(student_row: pd.Series) -> int:
    cc = student_row.get("# of Credits Completed", 0)
    cr = student_row.get("# Registered", 0)
    return int((cc if pd.notna(cc) else 0) + (cr if pd.notna(cr) else 0))

def student_eligibility_view():
    if not _require_state_keys():
        return

    st.subheader("Student Eligibility View")

    # --- Student selector ---
    students = st.session_state.progress_df[["ID", "NAME"]].copy()
    students["label"] = students["ID"].astype(str) + " — " + students["NAME"].astype(str)
    selected_label = st.selectbox("Select a student", students["label"].tolist())
    selected_id = selected_label.split(" — ")[0]
    student_row = st.session_state.progress_df.loc[st.session_state.progress_df["ID"].astype(str) == selected_id].iloc[0]

    # Ensure advising bucket exists
    if selected_id not in st.session_state.advising_selections:
        st.session_state.advising_selections[selected_id] = {"advised": [], "optional": [], "note": ""}

    advised_list = list(st.session_state.advising_selections[selected_id].get("advised", []))
    optional_list = list(st.session_state.advising_selections[selected_id].get("optional", []))
    note = st.session_state.advising_selections[selected_id].get("note", "")

    # Standing
    total_credits = _credits_total(student_row)
    standing = get_student_standing(total_credits)

    st.markdown(
        f"**{student_row['NAME']}** · **ID:** {selected_id} · **Total Credits:** {total_credits} · **Standing:** {standing}"
    )

    # --- Build per-course table ---
    rows = []
    eligibility_dict = {}
    for _, course in st.session_state.courses_df.iterrows():
        code = course["Course Code"]
        ctype = course.get("Type", "")
        offered = "Yes" if is_course_offered(st.session_state.courses_df, code) else "No"
        status, justification = check_eligibility(student_row, code, advised_list, st.session_state.courses_df)
        eligibility_dict[code] = status

        # Action resolution
        if check_course_completed(student_row, code):
            action = "Completed"
        elif check_course_registered(student_row, code):
            action = "Registered"
        elif code in advised_list:
            action = "Advised"
        elif code in optional_list:
            action = "Optional"
        elif status == "Eligible":
            action = "Eligible (not chosen)"
        else:
            action = "Not Eligible"

        rows.append(
            {
                "Course Code": code,
                "Type": ctype,
                "Requisites": build_requisites_str(course),
                "Eligibility Status": status,
                "Justification": justification,
                "Offered": offered,
                "Action": action,
            }
        )

    courses_display_df = pd.DataFrame(rows)

    # --- Selection widgets ---
    with st.form("advising_form"):
        # Only allow selecting truly eligible courses; exclude completed/registered
        selectable = [
            c for c in st.session_state.courses_df["Course Code"].tolist()
            if eligibility_dict.get(c) == "Eligible"
            and not check_course_completed(student_row, c)
            and not check_course_registered(student_row, c)
            and is_course_offered(st.session_state.courses_df, c)
        ]

        advised_selection = st.multiselect(
            "Advised Courses",
            options=selectable,
            default=[c for c in advised_list if c in selectable],
            help="Courses the student should register for now.",
        )

        # Optional: may include advised_selection + other eligible (but still exclude completed/registered)
        optional_options = [c for c in selectable if c not in advised_selection]
        optional_selection = st.multiselect(
            "Optional Courses",
            options=optional_options,
            default=[c for c in optional_list if c in optional_options],
            help="Backup choices if primary courses are unavailable.",
        )

        note_input = st.text_area("Advisor Note (optional)", value=note)

        if st.form_submit_button("Save Selections"):
            st.session_state.advising_selections[selected_id] = {
                "advised": advised_selection,
                "optional": optional_selection,
                "note": note_input,
            }
            st.success("Selections saved.")
            log_info(f"Saved advising selections for student {selected_id}")

    # Refresh the table's Action column based on possibly updated selections
    advised_list = st.session_state.advising_selections[selected_id]["advised"]
    optional_list = st.session_state.advising_selections[selected_id]["optional"]
    courses_display_df["Action"] = courses_display_df["Course Code"].apply(
        lambda code: (
            "Completed" if check_course_completed(student_row, code)
            else "Registered" if check_course_registered(student_row, code)
            else "Advised" if code in advised_list
            else "Optional" if code in optional_list
            else "Eligible (not chosen)" if eligibility_dict.get(code) == "Eligible"
            else "Not Eligible"
        )
    )

    # Split & show
    st.markdown("### Course Eligibility")
    req_df = courses_display_df[courses_display_df["Type"] == "Required"].copy()
    int_df = courses_display_df[courses_display_df["Type"] == "Intensive"].copy()
    if not req_df.empty:
        st.markdown("**Required Courses**")
        st.dataframe(style_df(req_df), use_container_width=True)
    if not int_df.empty:
        st.markdown("**Intensive Courses**")
        st.dataframe(style_df(int_df), use_container_width=True)

    # --- Download per-student report ---
    st.subheader("Download Advising Report")
    # Calculate credits advised/optional if 'Credits' column exists
    credits_map = {}
    if "Credits" in st.session_state.courses_df.columns:
        credits_map = dict(zip(st.session_state.courses_df["Course Code"], st.session_state.courses_df["Credits"]))
    def _sum_credits(course_list):
        return int(sum([int(credits_map.get(c, 0)) for c in course_list])) if course_list else 0
    advised_credits = _sum_credits(advised_list)
    optional_credits = _sum_credits(optional_list)

    # Compose Excel
    out = BytesIO()
    with pd.ExcelWriter(out, engine="openpyxl") as writer:
        courses_display_df.to_excel(writer, index=False, sheet_name="Advising Report")
    apply_excel_formatting(
        out,
        student_row["NAME"],
        student_row["ID"],
        total_credits,
        standing,
        st.session_state.advising_selections[selected_id]["note"],
        advised_credits,
        optional_credits,
    )
    st.download_button(
        "Download Advising Report",
        data=out.getvalue(),
        file_name=f'{student_row["NAME"].replace(" ", "_")}_Advising_Report.xlsx',
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
