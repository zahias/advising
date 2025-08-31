# eligibility_view.py

import pandas as pd
import streamlit as st
from io import BytesIO

from reporting import apply_excel_formatting
from utils import (
    build_requisites_str,
    check_course_completed,
    check_course_registered,
    check_eligibility,
    get_student_standing,
    is_course_offered,
    log_info,
    log_error,
    style_df,
)

def student_eligibility_view():
    if "courses_df" not in st.session_state or st.session_state.courses_df.empty:
        st.warning("Courses table not loaded.")
        return
    if "progress_df" not in st.session_state or st.session_state.progress_df.empty:
        st.warning("Progress report not loaded.")
        return
    if "advising_selections" not in st.session_state:
        st.session_state.advising_selections = {}

    # pick student
    students_df = st.session_state.progress_df.copy()
    students_df["DISPLAY"] = students_df["NAME"].astype(str) + " — " + students_df["ID"].astype(str)
    choice = st.selectbox("Select a student", students_df["DISPLAY"].tolist())
    sid = int(students_df.loc[students_df["DISPLAY"] == choice, "ID"].iloc[0])
    srow = students_df.loc[students_df["ID"] == sid].iloc[0]

    slot = st.session_state.advising_selections.setdefault(sid, {"advised": [], "optional": [], "note": ""})
    advised_selection = slot.get("advised", [])
    optional_selection = slot.get("optional", [])

    # standing
    completed = srow.get("# of Credits Completed", 0)
    registered = srow.get("# Registered", 0)
    total = (completed if pd.notna(completed) else 0) + (registered if pd.notna(registered) else 0)
    standing = get_student_standing(total)
    st.write(f"**Name:** {srow['NAME']}  |  **ID:** {sid}  |  **Credits:** {int(total)}  |  **Standing:** {standing}")

    # compute eligibility
    status_map, just_map = {}, {}
    for code in st.session_state.courses_df["Course Code"]:
        stt, just = check_eligibility(srow, code, advised_selection, st.session_state.courses_df)
        status_map[code] = stt
        just_map[code] = just

    # display rows
    rows = []
    for code in st.session_state.courses_df["Course Code"]:
        info = st.session_state.courses_df.loc[st.session_state.courses_df["Course Code"] == code].iloc[0]
        offered = "Yes" if is_course_offered(st.session_state.courses_df, code) else "No"

        # Action column (Registered is shown & excluded from pickers)
        if check_course_completed(srow, code):
            action = "Completed"; status = "Completed"
        elif check_course_registered(srow, code):
            action = "Registered"; status = status_map[code]
        elif code in advised_selection:
            action = "Advised"; status = status_map[code]
        elif code in optional_selection:
            action = "Optional"; status = status_map[code]
        elif status_map[code] == "Eligible":
            action = "Eligible (not chosen)"; status = "Eligible"
        else:
            action = "Not Eligible"; status = "Not Eligible"

        rows.append({
            "Course Code": code,
            "Type": info.get("Type", ""),
            "Requisites": build_requisites_str(info),
            "Eligibility Status": status,
            "Justification": just_map[code],
            "Offered": offered,
            "Action": action,
        })

    df = pd.DataFrame(rows)
    req_df = df[df["Type"] == "Required"].copy()
    int_df = df[df["Type"] == "Intensive"].copy()

    st.markdown("### Course Eligibility")
    if not req_df.empty:
        st.markdown("**Required Courses**")
        st.dataframe(style_df(req_df), use_container_width=True)
    if not int_df.empty:
        st.markdown("**Intensive Courses**")
        st.dataframe(style_df(int_df), use_container_width=True)

    # selection widgets: exclude completed/registered/not-offered
    offered_set = set(
        st.session_state.courses_df.loc[
            st.session_state.courses_df["Offered"].astype(str).str.lower() == "yes", "Course Code"
        ]
    )
    selectable = [
        c
        for c in st.session_state.courses_df["Course Code"]
        if (c in offered_set)
        and not check_course_completed(srow, c)
        and not check_course_registered(srow, c)
        and status_map.get(c) == "Eligible"
    ]

    with st.form("advise_form"):
        advised_selection = st.multiselect("Advised Courses", options=selectable, default=slot.get("advised", []))
        optional_selection = st.multiselect(
            "Optional Courses", options=[c for c in selectable if c not in advised_selection], default=slot.get("optional", [])
        )
        note_input = st.text_area("Advisor Note (optional)", value=slot.get("note", ""))

        if st.form_submit_button("Save Selections"):
            st.session_state.advising_selections[sid] = {
                "advised": advised_selection,
                "optional": optional_selection,
                "note": note_input,
            }
            st.success("Selections saved.")

    # export single-student
    st.subheader("Download Advising Report")
    if st.button("Download Student Report"):
        output = BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="Advising")
        from reporting import apply_excel_formatting
        apply_excel_formatting(
            output=output,
            student_name=str(srow["NAME"]),
            student_id=int(srow["ID"]),
            credits_completed=int(completed if pd.notna(completed) else 0) + int(registered if pd.notna(registered) else 0),
            standing=standing,
            note=st.session_state.advising_selections[sid].get("note", ""),
            advised_credits=int(
                st.session_state.courses_df.set_index("Course Code").reindex(advised_selection).get("Credits", pd.Series(0)).fillna(0).astype(float).sum()
            ) if "Credits" in st.session_state.courses_df.columns else 0,
            optional_credits=int(
                st.session_state.courses_df.set_index("Course Code").reindex(optional_selection).get("Credits", pd.Series(0)).fillna(0).astype(float).sum()
            ) if "Credits" in st.session_state.courses_df.columns else 0,
        )
        st.download_button(
            "Download Excel",
            data=output.getvalue(),
            file_name=f"Advising_{sid}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
