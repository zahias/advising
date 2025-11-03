# full_student_view.py

import streamlit as st
import pandas as pd
from io import BytesIO
from utils import (
    check_course_completed,
    check_course_registered,
    check_eligibility,
    get_student_standing,
    style_df,          # kept (used elsewhere in app)
    log_info,
    log_error
)
from google_drive import sync_file_with_drive, initialize_drive_service
from reporting import add_summary_sheet, apply_full_report_formatting, apply_individual_compact_formatting

# -----------------------------
# Color map (aligned with Advising table)
# -----------------------------
_CODE_COLORS = {
    "c":  "#C6E0B4",   # Completed -> light green
    "r":  "#BDD7EE",   # Registered -> light blue
    "s":  "#D9E1F2",   # Simulated (will register) -> light purple/blue
    "a":  "#FFF2CC",   # Advised -> light yellow
    "ar": "#FFD966",   # Advised-Repeat -> darker yellow/orange
    "o":  "#FFE699",   # Optional -> light orange
    "na": "#E1F0FF",   # Eligible not chosen -> light blue-tint
    "ne": "#F8CECC",   # Not Eligible -> light red
}

def _style_codes(df: pd.DataFrame, code_cols: list[str]) -> "pd.io.formats.style.Styler":
    """
    Return a Styler that colors the code columns based on _CODE_COLORS.
    Works for both All Students (many rows) and Individual Student (one row).
    """
    def _bg(v):
        col = _CODE_COLORS.get(str(v).strip().lower())
        return f"background-color: {col}" if col else ""
    styler = df.style
    if code_cols:
        styler = styler.map(_bg, subset=code_cols)
    return styler

def full_student_view():
    """
    Two modes:
      - All Students (wide table with compact status codes)
      - Individual Student (subset + export)
    """
    if "courses_df" not in st.session_state or st.session_state.courses_df.empty:
        st.warning("Courses table not loaded.")
        return
    if "progress_df" not in st.session_state or st.session_state.progress_df.empty:
        st.warning("Progress report not loaded.")
        return
    if "advising_selections" not in st.session_state:
        st.session_state.advising_selections = {}

    tab = st.tabs(["All Students", "Individual Student"])
    with tab[0]:
        _render_all_students()
    with tab[1]:
        _render_individual_student()

def _render_all_students():
    if "simulated_courses" not in st.session_state:
        st.session_state.simulated_courses = []
    
    st.markdown("### 🎯 Course Offering Simulation")
    st.caption("Select courses you plan to offer. The table below will update to show eligibility assuming all eligible students register for selected courses.")
    
    with st.form("simulation_form"):
        col_select, col_actions = st.columns([3, 1])
        
        with col_select:
            available_courses = st.session_state.courses_df["Course Code"].tolist()
            selected_sim_courses = st.multiselect(
                "Select courses to simulate",
                options=available_courses,
                default=st.session_state.simulated_courses,
                help="Choose courses that will be offered. Eligible students will be assumed to register for these courses."
            )
        
        with col_actions:
            st.write("")
            st.write("")
            col_apply, col_clear = st.columns(2)
            with col_apply:
                apply_clicked = st.form_submit_button("✅ Apply", type="primary", use_container_width=True)
            with col_clear:
                clear_clicked = st.form_submit_button("🔄 Clear", use_container_width=True)
        
        if apply_clicked:
            st.session_state.simulated_courses = selected_sim_courses
            st.rerun()
        if clear_clicked:
            st.session_state.simulated_courses = []
            st.rerun()
    
    if st.session_state.simulated_courses:
        st.info(f"🎬 **Simulation Active:** {len(st.session_state.simulated_courses)} course(s) selected - {', '.join(st.session_state.simulated_courses[:5])}{' ...' if len(st.session_state.simulated_courses) > 5 else ''}")
    
    st.markdown("---")
    
    df = st.session_state.progress_df.copy()
    df["ID"] = pd.to_numeric(df["ID"], errors="coerce")
    df = df.dropna(subset=["ID"])
    df["ID"] = df["ID"].astype(int)

    progress_df_original = df.copy().set_index("ID")
    original_rows = {int(idx): row for idx, row in progress_df_original.iterrows()}

    # Compute derived columns
    df["Total Credits Completed"] = df.get("# of Credits Completed", 0).fillna(0).astype(float) + \
                                    df.get("# Registered", 0).fillna(0).astype(float)
    df["Standing"] = df["Total Credits Completed"].apply(get_student_standing)
    df["Advising Status"] = df["ID"].apply(
        lambda sid: "Advised" if st.session_state.advising_selections.get(int(sid), {}).get("advised") else "Not Advised"
    )

    # Normalize remaining credits for filtering and display
    remaining_credits_series = pd.to_numeric(df.get("# Remaining", 0), errors="coerce").fillna(0)
    df["Remaining Credits"] = remaining_credits_series
    min_remaining = int(remaining_credits_series.min()) if not remaining_credits_series.empty else 0
    max_remaining = int(remaining_credits_series.max()) if not remaining_credits_series.empty else 0

    if min_remaining == max_remaining:
        remaining_range = (min_remaining, max_remaining)
        st.caption(
            f"All students currently have {min_remaining} remaining credits."
        )
    else:
        remaining_range = st.slider(
            "Filter by remaining credits",
            min_value=min_remaining,
            max_value=max_remaining,
            value=(min_remaining, max_remaining),
            help="Narrow the table to students within the selected remaining-credit range.",
        )

    if min_remaining != max_remaining:
        df = df[
            (df["Remaining Credits"] >= remaining_range[0])
            & (df["Remaining Credits"] <= remaining_range[1])
        ]

    courses_df = st.session_state.courses_df
    type_series = courses_df.get("Type", pd.Series(dtype=str))
    required_courses = courses_df.loc[
        type_series.astype(str).str.lower() == "required",
        "Course Code",
    ].dropna().tolist()
    intensive_courses = courses_df.loc[
        type_series.astype(str).str.lower() == "intensive",
        "Course Code",
    ].dropna().tolist()

    base_display_cols = [
        "NAME",
        "ID",
        "Total Credits Completed",
        "Remaining Credits",
        "Standing",
        "Advising Status",
    ]
    legend_md = "*Legend:* c=Completed, r=Registered, s=Simulated (will register), a=Advised, ar=Advised-Repeat, o=Optional, na=Eligible not chosen, ne=Not Eligible"
    
    simulated_courses = st.session_state.simulated_courses
    simulated_completions = {}
    
    if simulated_courses:
        for sid in df["ID"].astype(int).tolist():
            row_original = original_rows.get(int(sid))
            if row_original is None:
                continue
            
            simulated_completions[sid] = []
            advised_list = st.session_state.advising_selections.get(int(sid), {}).get("advised", []) or []
            
            max_iterations = len(simulated_courses)
            for iteration in range(max_iterations):
                added_this_iteration = False
                for sim_course in simulated_courses:
                    if sim_course in simulated_completions[sid]:
                        continue
                    
                    stt, _ = check_eligibility(row_original, sim_course, advised_list + simulated_completions[sid], st.session_state.courses_df)
                    if stt == "Eligible":
                        simulated_completions[sid].append(sim_course)
                        added_this_iteration = True
                
                if not added_this_iteration:
                    break

    def status_code(row_original: pd.Series, student_id: int, course: str, simulated_for_student: list) -> str:
        sel = st.session_state.advising_selections.get(int(student_id), {})
        advised_list = sel.get("advised", []) or []
        optional_list = sel.get("optional", []) or []
        repeat_list = sel.get("repeat", []) or []

        if course in repeat_list:
            return "ar"
        if check_course_completed(row_original, course):
            return "c"
        if check_course_registered(row_original, course):
            return "r"
        if course in simulated_for_student:
            return "s"
        if course in optional_list:
            return "o"
        if course in advised_list:
            return "a"

        stt, _ = check_eligibility(row_original, course, advised_list + simulated_for_student, st.session_state.courses_df)
        return "na" if stt == "Eligible" else "ne"

    def render_course_table(label: str, course_codes: list[str], key_suffix: str):
        if not course_codes:
            st.info(f"No {label.lower()} courses available.")
            return None, []

        with st.expander(f"Select {label.lower()} course columns", expanded=False):
            selected = st.multiselect(
                f"{label} course columns",
                options=course_codes,
                default=course_codes,
                key=f"all_students_{key_suffix}_course_columns",
            )

        if not selected:
            st.info("Select at least one course column to display student eligibility statuses.")
            return None, []

        table_df = df[base_display_cols].copy()
        student_ids = table_df["ID"].astype(int).tolist()

        for course in selected:
            statuses = []
            for sid in student_ids:
                row_original = original_rows.get(int(sid))
                if row_original is None:
                    statuses.append("")
                    continue
                student_simulated = simulated_completions.get(sid, [])
                statuses.append(status_code(row_original, sid, course, student_simulated))
            table_df[course] = statuses

        export_df = table_df.copy()
        display_df = export_df.set_index("NAME")
        display_df.index.name = "Student"

        st.write(legend_md)
        styled = _style_codes(display_df, selected)
        st.dataframe(styled, width="stretch", height=600)
        return export_df, selected

    required_tab, intensive_tab = st.tabs(["Required Courses", "Intensive Courses"])

    required_display_df = None
    required_selected = []
    intensive_display_df = None
    intensive_selected = []

    with required_tab:
        required_display_df, required_selected = render_course_table("Required", required_courses, "required")

    with intensive_tab:
        intensive_display_df, intensive_selected = render_course_table("Intensive", intensive_courses, "intensive")

    has_required = required_display_df is not None and len(required_selected) > 0
    has_intensive = intensive_display_df is not None and len(intensive_selected) > 0

    if not has_required and not has_intensive:
        return

    if has_required or has_intensive:
        def _build_full_report_bytes() -> bytes:
            output = BytesIO()
            with pd.ExcelWriter(output, engine="openpyxl") as writer:
                if has_required:
                    required_display_df.to_excel(writer, index=False, sheet_name="Required Courses")
                if has_intensive:
                    intensive_display_df.to_excel(writer, index=False, sheet_name="Intensive Courses")

                summary_frames = []
                summary_courses: list[str] = []
                if has_required:
                    summary_frames.append(required_display_df)
                    summary_courses.extend(required_selected)
                if has_intensive:
                    summary_frames.append(intensive_display_df)
                    summary_courses.extend(intensive_selected)

                if summary_frames and summary_courses:
                    summary_input = pd.concat(summary_frames, ignore_index=True)
                    add_summary_sheet(writer, summary_input, summary_courses)

                if has_required:
                    apply_full_report_formatting(
                        writer.book, sheet_name="Required Courses", course_cols=required_selected
                    )
                if has_intensive:
                    apply_full_report_formatting(
                        writer.book, sheet_name="Intensive Courses", course_cols=intensive_selected
                    )

            output.seek(0)
            return output.getvalue()

        full_report_bytes = _build_full_report_bytes()
        st.download_button(
            "Download Full Advising Report",
            data=full_report_bytes,
            file_name="Full_Advising_Report.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            type="primary",
        )

def _render_individual_student():
    students_df = st.session_state.progress_df.copy()
    students_df["DISPLAY"] = students_df["NAME"].astype(str) + " — " + students_df["ID"].astype(str)
    choice = st.selectbox("Select a student", students_df["DISPLAY"].tolist(), key="full_single_select")
    sid = int(students_df.loc[students_df["DISPLAY"] == choice, "ID"].iloc[0])
    row_original = st.session_state.progress_df.loc[st.session_state.progress_df["ID"] == sid].iloc[0]
    row = students_df.loc[students_df["ID"] == sid].iloc[0]

    # IMPORTANT: do NOT overwrite st.session_state["current_student_id"] here.
    # Eligibility view is the single source of truth for the "current student"
    # used by autosave and the sessions panel.

    available_courses = st.session_state.courses_df["Course Code"].tolist()
    selected_courses = st.multiselect("Select Courses", options=available_courses, default=available_courses, key="indiv_courses")

    # Build status codes for this student (includes Optional = 'o' and Repeat = 'ar')
    data = {"ID": [sid], "NAME": [row["NAME"]]}
    sel = st.session_state.advising_selections.get(sid, {})
    advised_list = sel.get("advised", []) or []
    optional_list = sel.get("optional", []) or []
    repeat_list = sel.get("repeat", []) or []

    for c in selected_courses:
        if c in repeat_list:
            data[c] = ["ar"]
        elif check_course_completed(row_original, c):
            data[c] = ["c"]
        elif check_course_registered(row_original, c):
            data[c] = ["r"]
        elif c in optional_list:
            data[c] = ["o"]
        elif c in advised_list:
            data[c] = ["a"]
        else:
            stt, _ = check_eligibility(row_original, c, advised_list, st.session_state.courses_df)
            data[c] = ["na" if stt == "Eligible" else "ne"]

    indiv_df = pd.DataFrame(data)
    st.write("*Legend:* c=Completed, r=Registered, a=Advised, ar=Advised-Repeat, o=Optional, na=Eligible not chosen, ne=Not Eligible")
    styled = _style_codes(indiv_df, selected_courses)
    st.dataframe(styled, width='stretch')

    # Download colored sheet for this student (compact codes)
    col1, col2 = st.columns([1, 1])
    with col1:
        def _build_individual_report_bytes() -> bytes:
            output = BytesIO()
            with pd.ExcelWriter(output, engine="openpyxl") as writer:
                indiv_df.to_excel(writer, index=False, sheet_name="Student")
            apply_individual_compact_formatting(output=output, sheet_name="Student", course_cols=selected_courses)
            output.seek(0)
            return output.getvalue()

        st.download_button(
            "Download Individual Report",
            data=_build_individual_report_bytes(),
            file_name=f"Student_{sid}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            type="primary",
        )
    
    with col2:
        # Email advising sheet to student
        if st.button("📧 Email Advising Sheet", key=f"email_indiv_{sid}"):
            from email_manager import get_student_email, send_advising_email
            
            student_email = get_student_email(str(sid))
            if not student_email:
                st.error(f"No email address found for student {sid}. Please upload email roster first.")
            else:
                # Get selection data
                note = sel.get("note", "")
                remaining_credits = float(row.get("# Remaining", 0) or 0)
                
                # Send email
                success, message = send_advising_email(
                    to_email=student_email,
                    student_name=str(row["NAME"]),
                    student_id=str(sid),
                    advised_courses=advised_list,
                    repeat_courses=repeat_list,
                    optional_courses=optional_list,
                    note=note,
                    courses_df=st.session_state.courses_df,
                    remaining_credits=int(remaining_credits),
                )
                
                if success:
                    st.success(f"✅ {message}")
                else:
                    st.error(f"❌ {message}")

    # Download sheets for all advised students into one workbook + sync to Drive (unchanged)
    all_sel = [(int(k), v) for k, v in st.session_state.advising_selections.items() if v.get("advised")]
    if not all_sel:
        st.info("No advised students found.")
        st.download_button(
            "Download All Advised Students Reports",
            data=b"",
            file_name="All_Advised_Students.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            type="primary",
            disabled=True,
            help="Advise at least one student to enable the export.",
        )
        return

    def _build_all_advised_bytes() -> bytes:
        output = BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            for sid_, sel_ in all_sel:
                srow = st.session_state.progress_df.loc[st.session_state.progress_df["ID"] == sid_].iloc[0]
                data_rows = {"Course Code": [], "Action": [], "Eligibility Status": [], "Justification": []}
                for cc in st.session_state.courses_df["Course Code"]:
                    status, just = check_eligibility(srow, cc, sel_.get("advised", []), st.session_state.courses_df)
                    if check_course_completed(srow, cc):
                        action = "Completed"; status = "Completed"
                    elif check_course_registered(srow, cc):
                        action = "Registered"
                    elif cc in sel_.get("advised", []):
                        action = "Advised"
                    else:
                        action = "Eligible not chosen" if status == "Eligible" else "Not Eligible"
                    data_rows["Course Code"].append(cc)
                    data_rows["Action"].append(action)
                    data_rows["Eligibility Status"].append(status)
                    data_rows["Justification"].append(just)
                pd.DataFrame(data_rows).to_excel(writer, index=False, sheet_name=str(sid_))
            index_df = st.session_state.progress_df.loc[
                st.session_state.progress_df["ID"].isin([sid for sid, _ in all_sel]),
                ["ID", "NAME"]
            ]
            index_df.to_excel(writer, index=False, sheet_name="Index")

        output.seek(0)
        return output.getvalue()

    all_reports_bytes = _build_all_advised_bytes()
    download_clicked = st.download_button(
        "Download All Advised Students Reports",
        data=all_reports_bytes,
        file_name="All_Advised_Students.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        type="primary",
    )

    if download_clicked:
        try:
            service = initialize_drive_service()
            sync_file_with_drive(
                service=service,
                file_content=all_reports_bytes,
                drive_file_name="All_Advised_Students.xlsx",
                mime_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                parent_folder_id=st.secrets["google"]["folder_id"],
            )
            st.success("✅ All Advised Students Reports synced with Google Drive successfully!")
            log_info("All Advised Students Reports synced with Google Drive successfully.")
        except Exception as e:
            st.error(f"❌ Error syncing All Advised Students Reports: {e}")
            log_error("Error syncing All Advised Students Reports", e)
