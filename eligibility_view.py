# eligibility_view.py

import streamlit as st
import pandas as pd
from io import BytesIO
from datetime import date, datetime

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
from google_drive import initialize_drive_service, find_file_in_drive, download_file_from_drive, sync_file_with_drive

_HISTORY_FILENAME = "advising_history.xlsx"
_HISTORY_COLUMNS = [
    "ID", "NAME", "Advisor", "Session Date", "Semester", "Year",
    "Advised", "Optional", "Note", "Saved At"
]

def _ensure_history_df(df: pd.DataFrame | None) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame(columns=_HISTORY_COLUMNS)
    # Add any missing columns without disturbing existing data
    for c in _HISTORY_COLUMNS:
        if c not in df.columns:
            df[c] = None
    return df[_HISTORY_COLUMNS]

def _load_history_df_from_drive(service) -> pd.DataFrame:
    """Fetch advising history file if present, else empty DataFrame with schema."""
    try:
        file_id = find_file_in_drive(service, _HISTORY_FILENAME, st.secrets["google"]["folder_id"])
        if not file_id:
            return pd.DataFrame(columns=_HISTORY_COLUMNS)
        content = download_file_from_drive(service, file_id)
        df = pd.read_excel(BytesIO(content))
        return _ensure_history_df(df)
    except Exception as e:
        log_error("Failed to load advising history from Drive", e)
        return pd.DataFrame(columns=_HISTORY_COLUMNS)

def _save_history_df_to_drive(service, df: pd.DataFrame):
    """Write advising history to Drive (create or update)."""
    try:
        output = BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="History")
        sync_file_with_drive(
            service=service,
            file_content=output.getvalue(),
            drive_file_name=_HISTORY_FILENAME,
            mime_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            parent_folder_id=st.secrets["google"]["folder_id"],
        )
        st.success("✅ Advising session saved to Google Drive.")
        log_info("Advising session saved to Drive.")
    except Exception as e:
        st.error(f"❌ Failed to save advising session: {e}")
        log_error("Failed to save advising session", e)

def student_eligibility_view():
    """
    Per-student advising & eligibility page.
    Expects in st.session_state:
      - courses_df
      - progress_df
      - advising_selections (dict: ID -> {'advised':[],'optional':[],'note':str})
      - advising_history_df (DataFrame)  [optional but used if present]
    """
    if "courses_df" not in st.session_state or st.session_state.courses_df.empty:
        st.warning("Courses table not loaded.")
        return
    if "progress_df" not in st.session_state or st.session_state.progress_df.empty:
        st.warning("Progress report not loaded.")
        return
    if "advising_selections" not in st.session_state:
        st.session_state.advising_selections = {}
    if "advising_history_df" not in st.session_state:
        st.session_state.advising_history_df = pd.DataFrame(columns=_HISTORY_COLUMNS)

    # Student picker
    students_df = st.session_state.progress_df.copy()
    students_df["DISPLAY"] = students_df["NAME"].astype(str) + " — " + students_df["ID"].astype(str)
    choice = st.selectbox("Select a student", students_df["DISPLAY"].tolist())
    selected_student_id = int(students_df.loc[students_df["DISPLAY"] == choice, "ID"].iloc[0])
    student_row = students_df.loc[students_df["ID"] == selected_student_id].iloc[0]

    # Ensure selection bucket
    slot = st.session_state.advising_selections.setdefault(selected_student_id, {"advised": [], "optional": [], "note": ""})

    # Credits/Standing
    credits_completed = float(student_row.get("# of Credits Completed", 0))
    credits_registered = float(student_row.get("# Registered", 0))
    total_credits = credits_completed + credits_registered
    standing = get_student_standing(total_credits)

    st.write(f"**Name:** {student_row['NAME']}  |  **ID:** {selected_student_id}  |  **Credits:** {int(total_credits)}  |  **Standing:** {standing}")

    # ---- Advising selections form (Save -> rerun) ----
    offered_set = set(st.session_state.courses_df.loc[st.session_state.courses_df["Offered"].astype(str).str.lower() == "yes", "Course Code"])

    def _eligible_for_selection():
        elig = []
        for c in st.session_state.courses_df["Course Code"]:
            if c not in offered_set:
                continue
            if check_course_completed(student_row, c) or check_course_registered(student_row, c):
                continue
            status, _ = check_eligibility(student_row, c, slot.get("advised", []), st.session_state.courses_df)
            if status == "Eligible":
                elig.append(c)
        return elig

    with st.form(key="advise_form"):
        advised_selection = st.multiselect("Advised Courses", options=_eligible_for_selection(), default=slot.get("advised", []))
        opt_options = [c for c in _eligible_for_selection() if c not in advised_selection]
        optional_selection = st.multiselect("Optional Courses", options=opt_options, default=slot.get("optional", []))
        note_input = st.text_area("Advisor Note (optional)", value=slot.get("note", ""))

        submitted = st.form_submit_button("Save Selections")
        if submitted:
            st.session_state.advising_selections[selected_student_id] = {
                "advised": advised_selection,
                "optional": optional_selection,
                "note": note_input,
            }
            st.success("Selections saved.")
            log_info(f"Saved selections for {selected_student_id}")
            st.rerun()

    # ---- Build eligibility/status table (reflects latest state) ----
    status_dict = {}
    justification_dict = {}
    current_advised = st.session_state.advising_selections[selected_student_id].get("advised", [])
    current_optional = st.session_state.advising_selections[selected_student_id].get("optional", [])

    for course_code in st.session_state.courses_df["Course Code"]:
        status, justification = check_eligibility(student_row, course_code, current_advised, st.session_state.courses_df)
        status_dict[course_code] = status
        justification_dict[course_code] = justification

    rows = []
    for course_code in st.session_state.courses_df["Course Code"]:
        info = st.session_state.courses_df.loc[st.session_state.courses_df["Course Code"] == course_code].iloc[0]
        offered = "Yes" if is_course_offered(st.session_state.courses_df, course_code) else "No"
        status = status_dict[course_code]

        if check_course_completed(student_row, course_code):
            action = "Completed"
            status = "Completed"
        elif check_course_registered(student_row, course_code):
            action = "Registered"
        elif course_code in current_advised:
            action = "Advised"
        elif course_code in current_optional:
            action = "Optional"
        elif status == "Not Eligible":
            action = "Not Eligible"
        else:
            action = "Eligible (not chosen)"

        rows.append({
            "Course Code": course_code,
            "Type": info.get("Type", ""),
            "Requisites": build_requisites_str(info),
            "Eligibility Status": status,
            "Justification": justification_dict[course_code],
            "Offered": offered,
            "Action": action
        })

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

    # ---- Advising Session: ENTER / SAVE / PREVIOUS / RETRIEVE ----
    st.markdown("---")
    st.subheader("Advising Session")

    # Load or initialize history df
    st.session_state.advising_history_df = _ensure_history_df(st.session_state.get("advising_history_df"))
    service = initialize_drive_service()
    if st.session_state.advising_history_df.empty:
        # Try to pull from Drive once if empty locally
        st.session_state.advising_history_df = _load_history_df_from_drive(service)

    # Input fields (visible)
    col1, col2, col3, col4 = st.columns([2, 2, 2, 2])
    with col1:
        advisor_name = st.text_input("Advisor Name", value=st.session_state.get("advisor_name", ""))
    with col2:
        session_date = st.date_input("Session Date", value=st.session_state.get("session_date", date.today()))
    with col3:
        semester = st.selectbox(
            "Semester",
            options=["Fall", "Spring", "Summer"],
            index=["Fall", "Spring", "Summer"].index(st.session_state.get("semester", "Fall"))
            if st.session_state.get("semester") in ["Fall", "Spring", "Summer"] else 0
        )
    with col4:
        year_default = st.session_state.get("year", date.today().year)
        year = st.number_input("Year", value=int(year_default), min_value=2000, max_value=2100, step=1)

    # Persist quick inputs
    st.session_state["advisor_name"] = advisor_name
    st.session_state["session_date"] = session_date
    st.session_state["semester"] = semester
    st.session_state["year"] = year

    col_save, col_prev = st.columns([1, 3])

    # Save current session
    with col_save:
        if st.button("Save Advising Session"):
            payload = {
                "ID": int(selected_student_id),
                "NAME": str(student_row["NAME"]),
                "Advisor": advisor_name.strip(),
                "Session Date": session_date.isoformat() if isinstance(session_date, date) else str(session_date),
                "Semester": semester,
                "Year": int(year),
                "Advised": ", ".join(current_advised),
                "Optional": ", ".join(current_optional),
                "Note": st.session_state.advising_selections[selected_student_id].get("note", ""),
                "Saved At": datetime.now().isoformat(timespec="seconds"),
            }
            hist_df = _ensure_history_df(st.session_state.advising_history_df)
            new_hist_df = pd.concat([hist_df, pd.DataFrame([payload])], ignore_index=True)
            st.session_state.advising_history_df = new_hist_df[_HISTORY_COLUMNS]
            _save_history_df_to_drive(service, st.session_state.advising_history_df)
            st.rerun()

    # Previous sessions + retrieve
    with col_prev:
        st.markdown("**Previous Sessions for this student**")
        hist = _ensure_history_df(st.session_state.advising_history_df)
        student_hist = hist.loc[hist["ID"] == selected_student_id].copy()

        if not student_hist.empty:
            # order newest first
            student_hist["__order"] = pd.to_datetime(student_hist["Session Date"], errors="coerce")
            student_hist["__saved"] = pd.to_datetime(student_hist["Saved At"], errors="coerce")
            student_hist = student_hist.sort_values(by=["__order", "__saved"], ascending=[False, False])

            # Table preview
            st.dataframe(
                student_hist[["Session Date","Semester","Year","Advisor","Advised","Optional","Note","Saved At"]],
                use_container_width=True,
                height=240
            )

            # Retrieve selector
            labels = student_hist.apply(
                lambda r: f"{r['Session Date']} • {r['Semester']} {int(r['Year'])} • {r['Advisor']}".strip(),
                axis=1
            ).tolist()
            idx = st.selectbox("Retrieve a saved session", options=list(range(len(labels))), format_func=lambda i: labels[i])

            if st.button("Load Selected Session into Current Selections"):
                chosen = student_hist.iloc[int(idx)]
                # Parse advised/optional back into lists
                new_advised = [c.strip() for c in str(chosen["Advised"] or "").split(",") if c.strip()]
                new_optional = [c.strip() for c in str(chosen["Optional"] or "").split(",") if c.strip()]
                # Update current student's selection
                st.session_state.advising_selections[selected_student_id] = {
                    "advised": new_advised,
                    "optional": new_optional,
                    "note": str(chosen.get("Note") or ""),
                }
                st.success("Session loaded into current selections.")
                st.rerun()
        else:
            st.info("No previous sessions found for this student.")

    # ---- Download report ----
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
            advised_credits=int(
                st.session_state.courses_df.set_index("Course Code").reindex(current_advised).get("Credits", pd.Series(0)).fillna(0).astype(float).sum()
            ) if "Credits" in st.session_state.courses_df.columns else 0,
            optional_credits=int(
                st.session_state.courses_df.set_index("Course Code").reindex(current_optional).get("Credits", pd.Series(0)).fillna(0).astype(float).sum()
            ) if "Credits" in st.session_state.courses_df.columns else 0,
        )
        st.download_button(
            "Download Excel",
            data=output.getvalue(),
            file_name=f"Advising_{selected_student_id}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
