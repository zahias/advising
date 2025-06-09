# eligibility_view.py

import streamlit as st
import pandas as pd
from io import BytesIO
from utils import (
    check_course_completed,
    is_course_offered,
    check_eligibility,
    build_requisites_str,
    style_df,
    get_student_standing,
    log_info,
    log_error
)
from reporting import apply_excel_formatting

def student_eligibility_view():
    """Render the Student Eligibility View tab."""
    st.header('Student Eligibility View')

    # Select a student
    student_list = (
        st.session_state.progress_df['ID'].astype(str)
        + ' - '
        + st.session_state.progress_df['NAME']
    )
    selected_student = st.selectbox(
        'Select a Student',
        student_list,
        help="Select a student to review."
    )

    selected_student_id = selected_student.split(' - ')[0]
    student_row = (
        st.session_state.progress_df[
            st.session_state.progress_df['ID'] == int(selected_student_id)
        ]
        .iloc[0]
        .to_dict()
    )

    # Initialize advising selections if not present
    if selected_student_id not in st.session_state.advising_selections:
        st.session_state.advising_selections[selected_student_id] = {
            'advised': [],
            'optional': [],
            'note': ''
        }

    current_advised = st.session_state.advising_selections[selected_student_id]['advised']
    current_optional = st.session_state.advising_selections[selected_student_id]['optional']
    current_note = st.session_state.advising_selections[selected_student_id]['note']

    # Determine academic standing based on "# of Credits Completed" + "# Registered"
    credits_completed_field = student_row.get('# of Credits Completed', 0)
    credits_registered_field = student_row.get('# Registered', 0)
    credits_completed = (
        (credits_completed_field if pd.notna(credits_completed_field) else 0)
        + (credits_registered_field if pd.notna(credits_registered_field) else 0)
    )
    standing = get_student_standing(credits_completed)
    log_info(f"Computed standing for student ID {selected_student_id}: {standing}")

    # Determine eligibility for each course
    eligibility_dict = {}
    justification_dict = {}
    for course_code in st.session_state.courses_df['Course Code']:
        status, justification = check_eligibility(
            student_row,
            course_code,
            current_advised,
            st.session_state.courses_df
        )
        eligibility_dict[course_code] = status
        justification_dict[course_code] = justification

    # Determine which courses should appear in the multiselects
    eligible_for_selection = [
        c for c in st.session_state.courses_df['Course Code']
        if eligibility_dict[c] == 'Eligible'
        or c in current_advised
        or c in current_optional
    ]

    # --- COURSE SELECTION FORM ---
    with st.form('course_selection_form'):
        st.subheader('Select Courses')

        # 1) Advised multiselect
        filtered_advised_options = [
            c for c in eligible_for_selection
            if eligibility_dict[c] == 'Eligible'
        ]
        # Only keep defaults that still exist in options
        default_advised = [c for c in current_advised if c in filtered_advised_options]

        advised_selection = st.multiselect(
            'Advised Courses',
            options=filtered_advised_options,
            default=default_advised,
            key='advised_selection',
            help="Select strongly recommended courses."
        )

        # 2) Optional multiselect
        filtered_optional_options = [
            c for c in eligible_for_selection
            if eligibility_dict[c] == 'Eligible'
            and c not in advised_selection
        ]
        default_optional = [c for c in current_optional if c in filtered_optional_options]

        optional_selection = st.multiselect(
            'Optional Courses',
            options=filtered_optional_options,
            default=default_optional,
            key='optional_selection',
            help="Select additional optional courses."
        )

        # 3) Note field
        note_input = st.text_area(
            'Advisor Note (Optional)',
            value=current_note,
            key='note_field',
            help="Additional guidance for the student."
        )

        # 4) Submit button (always present)
        submitted = st.form_submit_button('Submit Selections')
        if submitted:
            st.session_state.advising_selections[selected_student_id]['advised'] = sorted(advised_selection)
            st.session_state.advising_selections[selected_student_id]['optional'] = sorted(optional_selection)
            st.session_state.advising_selections[selected_student_id]['note'] = note_input.strip()

            st.success('✅ Selections updated.')
            log_info(f"Updated advising selections for student ID {selected_student_id}.")

            # Trigger data save to Drive and rerun to refresh
            st.session_state.data_uploaded = True
            st.rerun()

    # --- CALCULATE CREDIT TOTALS ---
    if 'Credits' not in st.session_state.courses_df.columns:
        st.warning("⚠️ The 'Credits' column is missing. Cannot compute credit totals.")
        advised_credits = optional_credits = 'N/A'
        log_error("Credits column missing", "Cannot calculate advised/optional credits.")
    else:
        advised_credits = st.session_state.courses_df.loc[
            st.session_state.courses_df['Course Code'].isin(
                st.session_state.advising_selections[selected_student_id]['advised']
            ),
            'Credits'
        ].sum()

        optional_credits = st.session_state.courses_df.loc[
            st.session_state.courses_df['Course Code'].isin(
                st.session_state.advising_selections[selected_student_id]['optional']
            ),
            'Credits'
        ].sum()
        log_info(f"Credits advised: {advised_credits}, Credits optional: {optional_credits}")

    # --- DISPLAY STUDENT INFO ---
    st.markdown("### Student Information")
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.markdown(f"**Name:** {student_row['NAME']}")
    col2.markdown(f"**Credits Completed:** {credits_completed}")
    col3.markdown(f"**Standing:** {standing}")
    col4.markdown(f"**Credits Advised:** {advised_credits}")
    col5.markdown(f"**Credits Optional:** {optional_credits}")

    # --- PREPARE AND SHOW ELIGIBILITY TABLE ---
    courses_data = []
    for course_code in st.session_state.courses_df['Course Code']:
        status = eligibility_dict.get(course_code, 'Not Eligible')
        justification = justification_dict.get(course_code, '')
        course_info = st.session_state.courses_df.loc[
            st.session_state.courses_df['Course Code'] == course_code
        ].iloc[0]
        offered = 'Yes' if is_course_offered(st.session_state.courses_df, course_code) else 'No'
        ctype = course_info['Type']
        requisites = build_requisites_str(course_info)

        # Determine Action label
        if check_course_completed(student_row, course_code):
            action = 'Completed'
            status = 'Completed'
        elif course_code in advised_selection:
            action = 'Advised'
        elif course_code in optional_selection:
            action = 'Optional'
        else:
            action = 'Eligible (not chosen)' if status == 'Eligible' else 'Not Eligible'

        # Provide a default justification
        if status == 'Eligible' and not justification:
            justification = 'All requirements met.'

        courses_data.append({
            'Course Code': course_code,
            'Type': ctype,
            'Requisites': requisites,
            'Eligibility Status': status,
            'Justification': justification,
            'Offered': offered,
            'Action': action
        })

    display_df = pd.DataFrame(courses_data)
    required_df = display_df[display_df['Type'] == 'Required'].copy()
    intensive_df = display_df[display_df['Type'] == 'Intensive'].copy()

    st.markdown("### Course Eligibility")
    if not required_df.empty:
        st.markdown("**Required Courses**")
        st.dataframe(style_df(required_df), use_container_width=True)
    if not intensive_df.empty:
        st.markdown("**Intensive Courses**")
        st.dataframe(style_df(intensive_df), use_container_width=True)

    # --- DOWNLOAD INDIVIDUAL ADVISING REPORT ---
    st.subheader('Download Advising Report')
    if st.button('Download Student Report'):
        combined_df = pd.concat([required_df, intensive_df], ignore_index=True)
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            combined_df.to_excel(writer, sheet_name='Advising Report', index=False)

        formatted = apply_excel_formatting(
            output,
            student_row['NAME'],
            student_row['ID'],
            credits_completed,
            standing,
            st.session_state.advising_selections[selected_student_id]['note'],
            advised_credits,
            optional_credits
        )

        st.download_button(
            label='Download Advising Report',
            data=formatted.getvalue(),
            file_name=f"{student_row['NAME'].replace(' ', '_')}_Advising_Report.xlsx",
            mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        log_info(f"Advising report downloaded for student ID {selected_student_id}.")
