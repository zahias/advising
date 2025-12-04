# full_student_view.py

import streamlit as st
import pandas as pd
from io import BytesIO
from utils import (
    check_course_completed,
    check_course_registered,
    check_eligibility,
    get_student_standing,
    build_requisites_str,
    get_corequisite_and_concurrent_courses,
    get_mutual_concurrent_pairs,
    calculate_course_curriculum_years,
    calculate_student_curriculum_year,
    style_df,          # kept (used elsewhere in app)
    log_info,
    log_error
)
from reporting import add_summary_sheet, apply_full_report_formatting, apply_individual_compact_formatting
from advising_history import load_all_sessions_for_period

def _get_drive_module():
    """Lazy loader for google_drive module to avoid import-time side effects."""
    import google_drive as gd
    return gd

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
    "b":  "#D5A6E6",   # Bypass -> light purple
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

def _get_semester_structure(courses_df):
    """Parse semester structure from courses table.
    
    Expects a 'Suggested Semester' column with format: 'Fall-1', 'Spring-2', 'Summer-3', etc.
    Returns dict mapping semester keys to list of course info dicts.
    """
    semester_col = None
    for col in courses_df.columns:
        if 'suggested' in col.lower() and 'semester' in col.lower():
            semester_col = col
            break
    
    if not semester_col:
        return {}
    
    semesters = {}
    
    for _, course_row in courses_df.iterrows():
        semester_value = str(course_row.get(semester_col, "")).strip()
        
        if not semester_value or pd.isna(semester_value) or semester_value == 'nan':
            continue
        
        # Parse format like "Fall-1", "Spring-2", "Summer-3"
        if '-' in semester_value:
            parts = semester_value.split('-')
            if len(parts) == 2:
                semester_name = parts[0].strip()
                year_num = parts[1].strip()
                
                semester_key = f"{semester_name}-{year_num}"
                
                if semester_key not in semesters:
                    semesters[semester_key] = []
                
                semesters[semester_key].append({
                    'code': course_row["Course Code"],
                    'title': course_row.get("Course Title", course_row.get("Title", "")),
                    'credits': course_row.get("Credits", 3),
                    'semester': semester_name,
                    'year': year_num
                })
    
    return semesters

def render_degree_plan_table(courses_df, progress_df):
    """Render degree plan view for all students."""
    st.markdown("### 🎓 Degree Plan View - All Students")
    st.caption("Shows student progress organized by the curriculum's suggested semester structure")
    
    # Get semester structure
    semesters = _get_semester_structure(courses_df)
    
    if not semesters:
        st.warning("⚠️ No 'Suggested Semester' column found in courses table. Please add a column with format like 'Fall-1', 'Spring-2', etc.")
        return None
    
    # Build ordered list of courses by semester
    semester_order = sorted(semesters.keys(), key=lambda x: (int(x.split('-')[1]), {'fall': 0, 'spring': 1, 'summer': 2}.get(x.split('-')[0].lower(), 99)))
    all_courses = []
    for sem_key in semester_order:
        all_courses.extend([c['code'] for c in semesters[sem_key]])
    
    # Calculate curriculum years
    course_curriculum_years = calculate_course_curriculum_years(courses_df)
    
    # Calculate mutual pairs once for efficiency
    mutual_pairs = get_mutual_concurrent_pairs(courses_df)
    
    # Get bypasses for this major
    major = st.session_state.get("current_major", "")
    bypasses_key = f"bypasses_{major}"
    all_bypasses = st.session_state.get(bypasses_key, {})
    
    # Build table
    table_data = []
    for _, student in progress_df.iterrows():
        student_id = student.get("ID", "")
        
        # Get bypasses for this student
        student_bypasses = (
            all_bypasses.get(student_id)
            or all_bypasses.get(str(student_id))
            or {}
        )
        
        row = {
            "NAME": student.get("NAME", ""),
            "ID": student_id,
            "Total Credits Completed": student.get("Total Credits Completed", 0),
            "Remaining Credits": student.get("Remaining Credits", 0),
            "Standing": student.get("Standing", ""),
            "Curriculum Year": student.get("Curriculum Year", calculate_student_curriculum_year(student, courses_df, course_curriculum_years)),
        }
        
        # Add course statuses
        for course_code in all_courses:
            status_val = student.get(course_code, "")
            
            if pd.isna(status_val) or status_val == "":
                # Check eligibility
                is_eligible_status, _ = check_eligibility(
                    student,
                    course_code,
                    [],
                    courses_df,
                    ignore_offered=True,
                    mutual_pairs=mutual_pairs,
                    bypass_map=student_bypasses
                )
                # Map check_eligibility status to display codes
                status_map = {
                    "Completed": "c",
                    "Registered": "r",
                    "Eligible": "na",
                    "Eligible (Bypass)": "b",
                    "Not Eligible": "ne"
                }
                row[course_code] = status_map.get(is_eligible_status, "ne")
            else:
                row[course_code] = str(status_val).strip().lower()
        
        table_data.append(row)
    
    table_df = pd.DataFrame(table_data)
    
    # Display legend
    legend_md = """
    **Legend**: `c` = Completed | `r` = Registered | `s` = Simulated | `a` = Advised | `ar` = Advised Repeat | 
    `o` = Optional | `na` = Eligible | `b` = Bypass | `ne` = Not Eligible | `f` = Failed
    """
    
    st.write(legend_md)
    
    # Display table with styling
    display_df = table_df.set_index("NAME")
    display_df.index.name = "Student"
    
    styled = _style_codes(display_df, all_courses)
    st.dataframe(styled, width="stretch", height=600)
    
    # Show semester headers as info
    with st.expander("📅 Semester Structure"):
        for sem_key in semester_order:
            courses_in_sem = [c['code'] for c in semesters[sem_key]]
            total_credits = sum(c['credits'] for c in semesters[sem_key])
            st.markdown(f"**{sem_key}** ({total_credits} cr): {', '.join(courses_in_sem)}")
    
    return table_df

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
    
    major = st.session_state.get("current_major", "")
    from advising_period import get_current_period
    current_period = get_current_period()
    period_id = current_period.get("period_id", "")
    sessions_loaded_key = f"_fsv_sessions_loaded_{major}_{period_id}"
    if sessions_loaded_key not in st.session_state:
        load_all_sessions_for_period()
        st.session_state[sessions_loaded_key] = True

    tab = st.tabs(["All Students", "Individual Student"])
    with tab[0]:
        _render_all_students()
    with tab[1]:
        _render_individual_student()

def _render_all_students():
    if "simulated_courses" not in st.session_state:
        st.session_state.simulated_courses = []
    
    # Cache co-requisite and concurrent courses in session state
    if "coreq_concurrent_courses" not in st.session_state:
        st.session_state.coreq_concurrent_courses = get_corequisite_and_concurrent_courses(st.session_state.courses_df)
    
    st.markdown("### 🎯 Course Offering Simulation")
    st.caption("Select co-requisite or concurrent courses you plan to offer. The table will show eligibility assuming eligible students register for these courses.")
    
    with st.form("simulation_form"):
        col_select, col_actions = st.columns([3, 1])
        
        with col_select:
            # Only show co-requisite and concurrent courses for simulation
            available_courses = st.session_state.coreq_concurrent_courses
            
            if not available_courses:
                st.info("ℹ️ No co-requisite or concurrent courses found in the courses table. Simulation only supports courses that are required alongside other courses.")
            
            selected_sim_courses = st.multiselect(
                "Select co-requisite/concurrent courses to simulate",
                options=available_courses,
                default=[c for c in st.session_state.simulated_courses if c in available_courses],
                help="Only co-requisite and concurrent courses are shown since prerequisite courses would already be completed."
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

    # Get courses_df from session state first
    courses_df = st.session_state.courses_df
    
    # Calculate curriculum years for all courses
    course_curriculum_years = calculate_course_curriculum_years(courses_df)
    
    # Compute derived columns
    df["Total Credits Completed"] = (df.get("# of Credits Completed", 0).fillna(0).astype(float) + \
                                     df.get("# Registered", 0).fillna(0).astype(float)).astype(int)
    df["Standing"] = df["Total Credits Completed"].apply(get_student_standing)
    df["Curriculum Year"] = df.apply(
        lambda row: calculate_student_curriculum_year(row, courses_df, course_curriculum_years), axis=1
    )
    def _get_advising_status(sid):
        sels = st.session_state.advising_selections
        slot = sels.get(int(sid)) or sels.get(str(int(sid))) or {}
        return "Advised" if slot.get("advised") else "Not Advised"
    
    df["Advising Status"] = df["ID"].apply(_get_advising_status)

    # Normalize remaining credits for filtering and display
    remaining_credits_series = pd.to_numeric(df.get("# Remaining", 0), errors="coerce").fillna(0).astype(int)
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

    # Curriculum year filter
    all_curriculum_years = sorted(df["Curriculum Year"].unique().tolist())
    if len(all_curriculum_years) > 1:
        curriculum_year_filter = st.multiselect(
            "📚 Filter by Curriculum Year",
            options=all_curriculum_years,
            default=all_curriculum_years,
            help="Show students in specific curriculum years. Years are calculated based on prerequisite chain completion."
        )
        if curriculum_year_filter:
            df = df[df["Curriculum Year"].isin(curriculum_year_filter)]
    else:
        st.caption(f"All students are currently in Curriculum Year {all_curriculum_years[0] if all_curriculum_years else 'N/A'}.")

    type_series = courses_df.get("Type", pd.Series(dtype=str))
    
    # Build semester filter options
    if "Suggested Semester" in courses_df.columns:
        all_semesters = courses_df["Suggested Semester"].dropna().unique().tolist()
        all_semesters = [str(s).strip() for s in all_semesters if str(s).strip() and str(s).lower() not in ["nan", "none"]]
        
        # Extract unique semester types (Fall, Spring, Summer)
        semester_types = set()
        for sem in all_semesters:
            parts = sem.split("-")
            if len(parts) == 2:
                semester_types.add(parts[0])
        
        # Build filter options
        filter_options = ["All Courses"]
        filter_options.extend(sorted(semester_types))  # All Fall, All Spring, etc.
        filter_options.extend(sorted(all_semesters))   # Fall-1, Spring-2, etc.
        
        semester_filter = st.selectbox(
            "📅 Filter by Semester",
            options=filter_options,
            help="Show all courses or filter by specific semester (Fall-1, Spring-2) or semester type (Fall, Spring, Summer)"
        )
    else:
        semester_filter = "All Courses"
    
    required_courses = courses_df.loc[
        type_series.astype(str).str.lower() == "required",
        "Course Code",
    ].dropna().tolist()
    intensive_courses = courses_df.loc[
        type_series.astype(str).str.lower() == "intensive",
        "Course Code",
    ].dropna().tolist()
    
    # Filter courses by semester if a filter is active
    def filter_courses_by_semester(course_list, semester_filter_val):
        if semester_filter_val == "All Courses" or "Suggested Semester" not in courses_df.columns:
            return course_list
        
        filtered = []
        for course in course_list:
            course_info = courses_df.loc[courses_df["Course Code"] == course]
            if not course_info.empty:
                suggested_sem = str(course_info.iloc[0].get("Suggested Semester", "")).strip()
                if not suggested_sem or suggested_sem.lower() in ["nan", "none"]:
                    continue
                
                # Check if matches: exact match for specific semesters or semester type prefix
                if suggested_sem == semester_filter_val:  # Exact match (e.g., "Fall-1" == "Fall-1")
                    filtered.append(course)
                elif "-" not in semester_filter_val and suggested_sem.startswith(semester_filter_val + "-"):
                    # Semester type filter (e.g., "Fall" matches "Fall-1", "Fall-2", etc.)
                    filtered.append(course)
        return filtered
    
    if semester_filter != "All Courses":
        required_courses = filter_courses_by_semester(required_courses, semester_filter)
        intensive_courses = filter_courses_by_semester(intensive_courses, semester_filter)

    base_display_cols = [
        "NAME",
        "ID",
        "Total Credits Completed",
        "Remaining Credits",
        "Standing",
        "Curriculum Year",
        "Advising Status",
    ]
    legend_md = "*Legend:* c=Completed, r=Registered, s=Simulated (will register), a=Advised, ar=Advised-Repeat, o=Optional, na=Eligible not chosen, ne=Not Eligible"
    
    simulated_courses = st.session_state.simulated_courses
    simulated_completions = {}
    
    # Calculate mutual pairs once for efficiency
    mutual_pairs = get_mutual_concurrent_pairs(st.session_state.courses_df)
    
    # Get bypasses for this major
    major = st.session_state.get("current_major", "")
    bypasses_key = f"bypasses_{major}"
    all_bypasses = st.session_state.get(bypasses_key, {})
    
    if simulated_courses:
        for sid in df["ID"].astype(int).tolist():
            row_original = original_rows.get(int(sid))
            if row_original is None:
                continue
            
            # Get bypasses for this student
            student_bypasses = all_bypasses.get(sid) or all_bypasses.get(str(sid)) or {}
            
            simulated_completions[sid] = []
            advised_list = st.session_state.advising_selections.get(int(sid), {}).get("advised", []) or []
            
            max_iterations = len(simulated_courses)
            for iteration in range(max_iterations):
                added_this_iteration = False
                for sim_course in simulated_courses:
                    if sim_course in simulated_completions[sid]:
                        continue
                    
                    stt, _ = check_eligibility(row_original, sim_course, advised_list, st.session_state.courses_df, registered_courses=simulated_completions[sid], ignore_offered=True, mutual_pairs=mutual_pairs, bypass_map=student_bypasses)
                    if stt in ("Eligible", "Eligible (Bypass)"):
                        simulated_completions[sid].append(sim_course)
                        added_this_iteration = True
                
                if not added_this_iteration:
                    break

    def status_code(row_original: pd.Series, student_id: int, course: str, simulated_for_student: list) -> str:
        sel = st.session_state.advising_selections.get(int(student_id), {})
        advised_list = sel.get("advised", []) or []
        optional_list = sel.get("optional", []) or []
        repeat_list = sel.get("repeat", []) or []
        
        # Get bypasses for this student
        student_bypasses = all_bypasses.get(student_id) or all_bypasses.get(str(student_id)) or {}

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

        stt, _ = check_eligibility(row_original, course, advised_list, st.session_state.courses_df, registered_courses=simulated_for_student, ignore_offered=True, mutual_pairs=mutual_pairs, bypass_map=student_bypasses)
        if stt == "Eligible (Bypass)":
            return "b"
        return "na" if stt == "Eligible" else "ne"

    def render_course_table(label: str, course_codes: list[str], key_suffix: str):
        if not course_codes:
            st.info(f"No {label.lower()} courses available.")
            return None, []

        # Use session state to store confirmed selections
        confirmed_key = f"confirmed_{key_suffix}_courses"
        if confirmed_key not in st.session_state:
            st.session_state[confirmed_key] = course_codes
        
        # Ensure confirmed selections are valid for current course_codes (filter may have changed)
        valid_confirmed = [c for c in st.session_state[confirmed_key] if c in course_codes]
        if not valid_confirmed:
            valid_confirmed = course_codes
        
        with st.expander(f"Select {label.lower()} course columns", expanded=False):
            with st.form(key=f"course_selection_form_{key_suffix}"):
                temp_selected = st.multiselect(
                    f"{label} course columns",
                    options=course_codes,
                    default=valid_confirmed,
                    key=f"temp_{key_suffix}_course_columns",
                )
                
                col1, col2 = st.columns([1, 5])
                with col1:
                    confirm = st.form_submit_button("✓ Confirm", use_container_width=True)
                with col2:
                    st.caption("Select courses then click Confirm to update the table")
                
                if confirm:
                    st.session_state[confirmed_key] = temp_selected
                    st.rerun()
        
        selected = valid_confirmed
        
        if not selected:
            st.info("Select at least one course column to display student eligibility statuses.")
            return None, []

        table_df = df[base_display_cols].copy()
        student_ids = table_df["ID"].astype(int).tolist()

        # Track statuses for summary calculation
        course_status_data = {}
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
            course_status_data[course] = statuses

        # Build requisites and summary data
        requisites_data = {}
        summary_data = {}
        for course in selected:
            course_info = courses_df.loc[courses_df["Course Code"] == course]
            if not course_info.empty:
                requisites_data[course] = build_requisites_str(course_info.iloc[0])
            else:
                requisites_data[course] = ""
            
            # Calculate summary statistics
            statuses = course_status_data[course]
            total_students = len([s for s in statuses if s])
            c_count = statuses.count("c")
            r_count = statuses.count("r")
            s_count = statuses.count("s")
            na_count = statuses.count("na")
            ne_count = statuses.count("ne")
            completion_rate = f"{(c_count / total_students * 100):.0f}%" if total_students > 0 else "0%"
            summary_data[course] = f"c:{c_count} | r:{r_count} | s:{s_count} | na:{na_count} | ne:{ne_count} | {completion_rate}"

        # Show semester header if filtering
        if semester_filter != "All Courses":
            st.markdown(f"### 📅 {semester_filter}")
            st.write("")
        
        # Use only the student data table (no requisites/summary rows)
        display_df = table_df.set_index("NAME")
        display_df.index.name = "Student"
        
        # Build column config with tooltips for course columns
        column_config = {}
        for course in selected:
            req_str = requisites_data[course] if requisites_data[course] else "None"
            help_text = f"📋 {req_str}\n\n📊 {summary_data[course]}"
            column_config[course] = st.column_config.TextColumn(
                course,
                help=help_text,
                width="small"
            )
        
        # For export, use only student data (no requisites/summary rows)
        export_df = table_df.copy()

        st.write(legend_md)
        styled = _style_codes(display_df, selected)
        st.dataframe(styled, width="stretch", height=600, column_config=column_config)
        return export_df, selected

    required_tab, intensive_tab, degree_plan_tab = st.tabs(["Required Courses", "Intensive Courses", "Degree Plan"])

    required_display_df = None
    required_selected = []
    intensive_display_df = None
    intensive_selected = []
    degree_plan_display_df = None

    with required_tab:
        required_display_df, required_selected = render_course_table("Required", required_courses, "required")

    with intensive_tab:
        intensive_display_df, intensive_selected = render_course_table("Intensive", intensive_courses, "intensive")
    
    with degree_plan_tab:
        degree_plan_display_df = render_degree_plan_table(courses_df, df)

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
    
    # Get bypasses for this student
    major = st.session_state.get("current_major", "")
    bypasses_key = f"bypasses_{major}"
    all_bypasses = st.session_state.get(bypasses_key, {})
    student_bypasses = all_bypasses.get(sid) or all_bypasses.get(str(sid)) or {}

    mutual_pairs = get_mutual_concurrent_pairs(st.session_state.courses_df)
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
            stt, _ = check_eligibility(row_original, c, advised_list, st.session_state.courses_df, registered_courses=[], mutual_pairs=mutual_pairs, bypass_map=student_bypasses)
            if stt == "Eligible (Bypass)":
                data[c] = ["b"]
            else:
                data[c] = ["na" if stt == "Eligible" else "ne"]

    indiv_df = pd.DataFrame(data)
    st.write("*Legend:* c=Completed, r=Registered, a=Advised, ar=Advised-Repeat, o=Optional, b=Bypass, na=Eligible not chosen, ne=Not Eligible")
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
        mutual_pairs = get_mutual_concurrent_pairs(st.session_state.courses_df)
        
        # Get bypasses for this major
        major = st.session_state.get("current_major", "")
        bypasses_key = f"bypasses_{major}"
        all_bypasses = st.session_state.get(bypasses_key, {})
        
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            for sid_, sel_ in all_sel:
                srow = st.session_state.progress_df.loc[st.session_state.progress_df["ID"] == sid_].iloc[0]
                
                # Get bypasses for this student
                student_bypasses = all_bypasses.get(sid_) or all_bypasses.get(str(sid_)) or {}
                
                data_rows = {"Course Code": [], "Action": [], "Eligibility Status": [], "Justification": [], "Bypass": []}
                for cc in st.session_state.courses_df["Course Code"]:
                    status, just = check_eligibility(srow, cc, sel_.get("advised", []), st.session_state.courses_df, registered_courses=[], mutual_pairs=mutual_pairs, bypass_map=student_bypasses)
                    bypass_note = ""
                    if check_course_completed(srow, cc):
                        action = "Completed"; status = "Completed"
                    elif check_course_registered(srow, cc):
                        action = "Registered"
                    elif cc in sel_.get("advised", []):
                        action = "Advised"
                    elif status == "Eligible (Bypass)":
                        action = "Eligible (Bypass)"
                        bypass_info = student_bypasses.get(cc, {})
                        bypass_note = bypass_info.get("note", "")
                        if bypass_info.get("advisor"):
                            bypass_note = f"By {bypass_info['advisor']}: {bypass_note}" if bypass_note else f"By {bypass_info['advisor']}"
                    else:
                        action = "Eligible not chosen" if status == "Eligible" else "Not Eligible"
                    data_rows["Course Code"].append(cc)
                    data_rows["Action"].append(action)
                    data_rows["Eligibility Status"].append(status)
                    data_rows["Justification"].append(just)
                    data_rows["Bypass"].append(bypass_note)
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
            gd = _get_drive_module()
            service = gd.initialize_drive_service()
            gd.sync_file_with_drive(
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
