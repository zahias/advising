# full_student_view.py

import streamlit as st
import pandas as pd
from io import BytesIO
from utils import (
    check_course_completed,
    is_course_offered,
    check_eligibility,
    get_student_standing,
    style_df,
    ACTION_LABELS,
    STATUS_CODES,
    COLOR_MAP,
    log_info,
    log_error,
)
from reporting import apply_excel_formatting, add_summary_sheet
from google_drive import sync_file_with_drive, initialize_drive_service


def _safe_defaults(options, defaults):
    """Return (valid_defaults, dropped_defaults) ensuring defaults ⊆ options."""
    defaults = defaults or []
    optset = set(options or [])
    valid = [d for d in defaults if d in optset]
    dropped = [d for d in defaults if d not in optset]
    return valid, dropped


def full_student_view():
    """Render the Full Student View tab."""
    st.header('Full Student View')

    mode = st.radio("Mode", ["All Students", "Individual Student"], horizontal=True)

    df_progress = st.session_state.progress_df
    courses_df = st.session_state.courses_df

    # Compute Standing for filters
    df = df_progress.copy()
    df['Total Credits Completed'] = df['# of Credits Completed'] + df['# Registered']
    df['Standing'] = df['Total Credits Completed'].apply(get_student_standing)

    if mode == "All Students":
        st.subheader("All Students")
        # Choose which course columns to show
        course_options = list(courses_df['Course Code'])
        # Ensure defaults ⊆ options (defensive; normally identical)
        default_courses, _ = _safe_defaults(course_options, course_options)

        course_cols = st.multiselect(
            "Choose course columns to include",
            options=course_options,
            default=default_courses,
        )

        # Slider filter for credits
        min_c, max_c = int(df['Total Credits Completed'].min()), int(df['Total Credits Completed'].max())
        sel_range = st.slider("Filter by Total Credits Completed", min_c, max_c, (min_c, max_c), step=1)
        mask = (df['Total Credits Completed'] >= sel_range[0]) & (df['Total Credits Completed'] <= sel_range[1])
        df_filtered = df[mask].copy()

        # Advising status column (has advised entries?)
        df_filtered['Advising Status'] = df_filtered['ID'].apply(
            lambda sid: "Advised" if st.session_state.advising_selections.get(sid, {}).get('advised') else "—"
        )

        # Build course status columns using centralized codes
        def per_course_marker(student_row, course_code):
            if check_course_completed(student_row, course_code):
                return STATUS_CODES["COMPLETED"]
            sel = st.session_state.advising_selections.get(student_row['ID'], {})
            if course_code in (sel.get('advised') or []):
                return STATUS_CODES["ADVISED"]
            # eligibility engine
            standing = get_student_standing(student_row['# of Credits Completed'] + student_row['# Registered'])
            cinfo = courses_df[courses_df['Course Code'] == course_code].iloc[0]
            status, _ = check_eligibility(student_row, cinfo, standing)
            if status == "Eligible":
                return STATUS_CODES["ELIGIBLE_NOT_CHOSEN"]
            return STATUS_CODES["NOT_ELIGIBLE"]

        for cc in course_cols:
            df_filtered[cc] = df_filtered.apply(lambda r: per_course_marker(r, cc), axis=1)

        # Display
        st.dataframe(
            df_filtered[['ID', 'NAME', 'Total Credits Completed', 'Standing', 'Advising Status'] + course_cols],
            use_container_width=True
        )

        # Download full advising report
        if st.button("Download Full Advising Report"):
            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df_filtered[['ID', 'NAME', 'Total Credits Completed', 'Standing', 'Advising Status'] + course_cols].to_excel(
                    writer, sheet_name='Advising', index=False
                )
                add_summary_sheet(writer, df_filtered, course_cols)
            output.seek(0)
            st.download_button(
                "Download",
                data=output.getvalue(),
                file_name="Full_Advising_Report.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
            # Drive sync (best-effort)
            try:
                service = initialize_drive_service()
                sync_file_with_drive(service, output, "Full_Advising_Report.xlsx",
                                     mime_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
            except Exception as e:
                log_error("Drive sync of full report failed", e)

    else:
        st.subheader("Individual Student")
        student_names = st.session_state.progress_df['NAME'].tolist()
        name = st.selectbox("Select student", student_names)
        srow = st.session_state.progress_df[st.session_state.progress_df['NAME'] == name].iloc[0]
        sid = srow['ID']

        standing = get_student_standing(srow['# of Credits Completed'] + srow['# Registered'])

        # Precompute eligibility/justification
        eligibility_dict, justification_dict = {}, {}
        for _, cinfo in courses_df.iterrows():
            code = cinfo['Course Code']
            status, just = check_eligibility(srow, cinfo, standing)
            eligibility_dict[code] = status
            justification_dict[code] = just

        sel = st.session_state.advising_selections.get(sid, {'advised': [], 'optional': [], 'note': ''})

        # Build rows
        def build_row(cinfo):
            code = cinfo['Course Code']
            ctype = cinfo['Type']
            reqs = " | ".join(
                f"{label}: {str(cinfo.get(key, '') or '').strip()}"
                for key, label in (('Prerequisite', 'Pre'), ('Concurrent', 'Con'), ('Corequisite', 'Co'))
                if str(cinfo.get(key, '') or '').strip()
            )
            offered = 'Yes' if is_course_offered(courses_df, code) else 'No'
            stt = eligibility_dict[code]
            just = justification_dict[code]

            if check_course_completed(srow, code):
                action = ACTION_LABELS["COMPLETED"]
                stt = "Completed"
            elif code in (sel.get('advised') or []):
                action = ACTION_LABELS["ADVISED"]
            elif code in (sel.get('optional') or []):
                action = ACTION_LABELS["OPTIONAL"]
            elif stt == "Eligible":
                action = ACTION_LABELS["ELIGIBLE_NOT_CHOSEN"]
            else:
                action = ACTION_LABELS["NOT_ELIGIBLE"]

            return {
                'Course Code': code,
                'Type': ctype,
                'Requisites': reqs,
                'Eligibility Status': stt,
                'Justification': just,
                'Offered': offered,
                'Action': action,
            }

        rows = [build_row(r) for _, r in courses_df.iterrows()]
        df_view = pd.DataFrame(rows)
        st.dataframe(style_df(df_view), use_container_width=True)

        # Eligible codes for pickers
        eligible_codes = [r['Course Code'] for r in rows if r['Eligibility Status'] == 'Eligible' and r['Action'] != ACTION_LABELS["COMPLETED"]]

        # --- Safe defaults for multiselects (prevents StreamlitAPIException) ---
        valid_advised, dropped_advised = _safe_defaults(eligible_codes, sel.get('advised'))
        valid_optional, dropped_optional = _safe_defaults(eligible_codes, sel.get('optional'))

        if dropped_advised or dropped_optional:
            with st.expander("Previously selected but not currently eligible"):
                if dropped_advised:
                    st.caption(f"Advised (kept in memory, not selectable now): {', '.join(dropped_advised)}")
                if dropped_optional:
                    st.caption(f"Optional (kept in memory, not selectable now): {', '.join(dropped_optional)}")

        advised = st.multiselect("Advised courses", options=eligible_codes, default=valid_advised)
        optional = st.multiselect("Optional courses", options=eligible_codes, default=valid_optional)
        note = st.text_input("Note", value=sel.get('note') or "")
        st.session_state.advising_selections[sid] = {'advised': advised, 'optional': optional, 'note': note}

        # Download single-student advising report
        if st.button("Download Student Report"):
            df_out = df_view.copy()
            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df_out.to_excel(writer, sheet_name='Advising', index=False)

            advised_credits = optional_credits = None
            if 'Credits' in courses_df.columns:
                credits_map = dict(zip(courses_df['Course Code'], courses_df['Credits']))
                advised_credits = sum(credits_map.get(c, 0) for c in advised)
                optional_credits = sum(credits_map.get(c, 0) for c in optional)

            apply_excel_formatting(
                output,
                srow['NAME'],
                srow['ID'],
                srow['# of Credits Completed'],
                standing,
                note,
                advised_credits,
                optional_credits,
            )
            st.download_button(
                label='Download',
                data=output.getvalue(),
                file_name=f'{srow["NAME"].replace(" ", "_")}_Advising_Report.xlsx',
                mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            )
