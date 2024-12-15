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

    # Initialize reset flags in session_state if they don't exist
    if 'reset_student_flag' not in st.session_state:
        st.session_state.reset_student_flag = False
    if 'reset_all_flag' not in st.session_state:
        st.session_state.reset_all_flag = False

    # Select a student
    student_list = st.session_state.progress_df['ID'].astype(str) + ' - ' + st.session_state.progress_df['NAME']
    selected_student = st.selectbox('Select a Student', student_list, help="Select a student to review.")

    selected_student_id = selected_student.split(' - ')[0]
    student_row = st.session_state.progress_df[st.session_state.progress_df['ID'] == int(selected_student_id)].iloc[0].to_dict()

    # Initialize advising selections if not present
    if selected_student_id not in st.session_state.advising_selections:
        st.session_state.advising_selections[selected_student_id] = {'advised': [], 'optional': [], 'note': ''}

    current_advised = st.session_state.advising_selections[selected_student_id].get('advised', [])
    current_optional = st.session_state.advising_selections[selected_student_id].get('optional', [])
    current_note = st.session_state.advising_selections[selected_student_id].get('note', '')

    # Determine academic standing based on credits
    credits_completed = student_row.get('# of Credits Completed', 0)
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

    # Determine eligible courses for selection (Exclude 'Completed')
    eligible_for_selection = [
        c for c in st.session_state.courses_df['Course Code']
        if eligibility_dict[c] == 'Eligible' or c in current_advised or c in current_optional
    ]

    # Begin Form
    with st.form('course_selection_form'):
        st.subheader('Select Courses')

        # Filter advised options to exclude 'Completed' and 'Not Eligible'
        filtered_advised_options = [
            c for c in eligible_for_selection
            if eligibility_dict[c] == 'Eligible'
        ]

        advised_selection = st.multiselect(
            'Advised Courses',
            options=filtered_advised_options,
            default=current_advised,
            key='advised_selection',
            help="Select strongly recommended courses."
        )

        # Filter optional options to exclude 'Completed', 'Not Eligible', and already advised courses
        filtered_optional_options = [
            c for c in eligible_for_selection
            if eligibility_dict[c] == 'Eligible' and c not in advised_selection
        ]

        optional_selection = st.multiselect(
            'Optional Courses',
            options=filtered_optional_options,
            default=current_optional,
            key='optional_selection',
            help="Select additional optional courses."
        )

        note_input = st.text_area('Advisor Note (Optional)', value=current_note, key='note_field', help="Additional guidance for the student.")

        submitted = st.form_submit_button('Submit Selections')

    # Handle Submit Selections
    if submitted:
        # Overwrite advised and optional courses with current selections
        st.session_state.advising_selections[selected_student_id]['advised'] = sorted(advised_selection)
        st.session_state.advising_selections[selected_student_id]['optional'] = sorted(optional_selection)
        st.session_state.advising_selections[selected_student_id]['note'] = note_input.strip()

        st.success('✅ Selections updated.')
        log_info(f"Updated advising selections for student ID {selected_student_id}.")

        # Trigger data save to Drive
        st.session_state.data_uploaded = True

        # Properly rerun the app to reflect changes and trigger save
        st.rerun()

    # Add Reset Buttons beside Submit Selections
    reset_col1, reset_col2 = st.columns(2)
    with reset_col1:
        if st.button('Reset Selections for This Student', key='reset_student'):
            st.session_state.reset_student_flag = True
    with reset_col2:
        if st.button('Reset Selections for All Students', key='reset_all'):
            st.session_state.reset_all_flag = True

    # Handle Reset Selections for This Student
    if st.session_state.reset_student_flag:
        with st.expander("⚠️ Confirm Reset for This Student"):
            confirm_reset_student = st.checkbox("Are you sure you want to reset selections for this student?", key='confirm_reset_student')
            if confirm_reset_student:
                with st.spinner('Resetting selections for this student...'):
                    st.session_state.advising_selections[selected_student_id] = {'advised': [], 'optional': [], 'note': ''}
                    st.session_state.reset_student_flag = False
                    st.session_state.data_uploaded = True  # Trigger save to Drive
                    st.success(f'✅ Advising selections reset for student ID {selected_student_id}.')
                    log_info(f"Reset advising selections for student ID {selected_student_id}.")

                    # Rerun to update the UI
                    st.rerun()
            elif st.button("Cancel"):
                st.session_state.reset_student_flag = False
                st.warning("⚠️ Reset for this student canceled.")

    # Handle Reset Selections for All Students
    if st.session_state.reset_all_flag:
        with st.expander("⚠️ Confirm Reset for All Students"):
            confirm_reset_all = st.checkbox("⚠️ Are you sure you want to reset selections for ALL students?", key='confirm_reset_all')
            if confirm_reset_all:
                with st.spinner('Resetting selections for all students...'):
                    for sid in st.session_state.advising_selections.keys():
                        st.session_state.advising_selections[sid] = {'advised': [], 'optional': [], 'note': ''}
                    st.session_state.reset_all_flag = False
                    st.session_state.data_uploaded = True  # Trigger save to Drive
                    st.success('✅ Advising selections reset for all students.')
                    log_info("Reset advising selections for all students.")

                    # Rerun to update the UI
                    st.rerun()
            elif st.button("Cancel"):
                st.session_state.reset_all_flag = False
                st.warning("⚠️ Reset for all students canceled.")

    # Calculate Credits Advised and Optional
    # Ensure 'Credits' column exists
    if 'Credits' not in st.session_state.courses_df.columns:
        st.warning("⚠️ The 'Credits' column is missing in the Courses Table. Please add it to calculate credit totals.")
        advised_credits = 'N/A'
        optional_credits = 'N/A'
        log_error("Credits column missing", "Cannot calculate advised and optional credits.")
    else:
        # Fetch credits for advised and optional courses
        advised_credits = st.session_state.courses_df.loc[
            st.session_state.courses_df['Course Code'].isin(st.session_state.advising_selections[selected_student_id]['advised']),
            'Credits'
        ].sum()

        optional_credits = st.session_state.courses_df.loc[
            st.session_state.courses_df['Course Code'].isin(st.session_state.advising_selections[selected_student_id]['optional']),
            'Credits'
        ].sum()
        log_info(f"Credits advised: {advised_credits}, Credits optional: {optional_credits}")

    # Display student info with improved styling
    st.markdown("### Student Information")
    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        st.markdown(f"**Name:** {student_row['NAME']}")

    with col2:
        st.markdown(f"**Credits Completed:** {credits_completed}")

    with col3:
        st.markdown(f"**Standing:** {standing}")

    with col4:
        st.markdown(f"**Credits Advised:** {advised_credits}")

    with col5:
        st.markdown(f"**Credits Optional:** {optional_credits}")

    # Prepare course data for display
    courses_data = []
    for course_code in st.session_state.courses_df['Course Code']:
        status = eligibility_dict.get(course_code, 'Not Eligible')
        justification = justification_dict.get(course_code, '')
        course_info = st.session_state.courses_df[st.session_state.courses_df['Course Code'] == course_code].iloc[0]
        offered = 'Yes' if is_course_offered(st.session_state.courses_df, course_code) else 'No'
        ctype = course_info['Type']
        requisites = build_requisites_str(course_info)

        if check_course_completed(student_row, course_code):
            action = 'Completed'
            status = 'Completed'
        elif course_code in advised_selection:
            action = 'Advised'
        elif course_code in optional_selection:
            action = 'Optional'
        else:
            if status == 'Not Eligible':
                action = 'Not Eligible'
            elif status == 'Eligible':
                action = 'Eligible (not chosen)'

        # For eligible courses, add justification if not 'Not Eligible'
        if status == 'Eligible' and justification == '':
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

    courses_display_df = pd.DataFrame(courses_data)

    # Separate Required and Intensive courses
    required_df = courses_display_df[courses_display_df['Type'] == 'Required'].copy()
    intensive_df = courses_display_df[courses_display_df['Type'] == 'Intensive'].copy()

    st.markdown("### Course Eligibility")

    if not required_df.empty:
        st.markdown("**Required Courses**")
        st.dataframe(style_df(required_df), use_container_width=True)

    if not intensive_df.empty:
        st.markdown("**Intensive Courses**")
        st.dataframe(style_df(intensive_df), use_container_width=True)

    # Download Individual Advising Report
    st.subheader('Download Advising Report')
    if st.button('Download Student Report'):
        combined_df = pd.concat([required_df, intensive_df], ignore_index=True)
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            combined_df.to_excel(writer, sheet_name='Advising Report', index=False)
        # Pass the credits counts to the formatting function
        output = apply_excel_formatting(
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
            data=output.getvalue(),
            file_name=f'{student_row["NAME"].replace(" ", "_")}_Advising_Report.xlsx',
            mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        log_info(f"Advising report downloaded for student ID {selected_student_id}.")
