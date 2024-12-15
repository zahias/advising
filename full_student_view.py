# full_student_view.py

import streamlit as st
import pandas as pd
from io import BytesIO
from utils import (
    check_course_completed,
    is_course_offered,
    check_eligibility,
    get_student_standing,
    log_info,
    log_error
)
from reporting import apply_excel_formatting, add_summary_sheet
from google_drive import sync_file_with_drive, initialize_drive_service
from openpyxl.styles import Font, PatternFill

def full_student_view():
    """Render the Full Student View tab."""
    st.header('Full Student View')

    # Select All Students or a Specific Student
    view_option = st.radio("View Options", ['All Students', 'Individual Student'])

    if view_option == 'All Students':
        st.subheader('All Students Report')

        if st.session_state.progress_df.empty:
            st.warning("⚠️ Progress report is not loaded.")
            return

        # Compute 'Standing' for each student
        full_report = st.session_state.progress_df[['ID', 'NAME', '# of Credits Completed']].copy()
        full_report['Standing'] = full_report['# of Credits Completed'].apply(get_student_standing)
        log_info("Computed 'Standing' for all students.")

        # Add Advising Status
        advising_statuses = []
        for _, student in st.session_state.progress_df.iterrows():
            sid = str(student['ID'])
            if sid in st.session_state.advising_selections and (st.session_state.advising_selections[sid].get('advised') or st.session_state.advising_selections[sid].get('optional')):
                advising_statuses.append('Advised')
            else:
                advising_statuses.append('Not Advised')
        full_report['Advising Status'] = advising_statuses

        # Add course status columns
        for course_code in st.session_state.courses_df['Course Code']:
            statuses = []
            for _, student in st.session_state.progress_df.iterrows():
                sid = str(student['ID'])
                course_status = 'ne'
                if check_course_completed(student, course_code):
                    course_status = 'c'
                else:
                    advised_for_student = st.session_state.advising_selections.get(sid, {}).get('advised', [])
                    optional_for_student = st.session_state.advising_selections.get(sid, {}).get('optional', [])
                    eligibility_status, _ = check_eligibility(student, course_code, advised_for_student, st.session_state.courses_df)
                    if course_code in advised_for_student:
                        course_status = 'a'
                    elif course_code in optional_for_student:
                        course_status = 'o'
                    elif eligibility_status == 'Eligible':
                        course_status = 'na'
                    else:
                        course_status = 'ne'
                statuses.append(course_status)
            full_report[course_code] = statuses

        # Reorder columns
        cols = ['ID', 'NAME', '# of Credits Completed', 'Standing', 'Advising Status'] + list(st.session_state.courses_df['Course Code'])
        full_report = full_report[cols]

        st.write("*Legend:* c=Completed, a=Advised, o=Optional, na=Eligible not chosen, ne=Not Eligible")
        st.dataframe(full_report.style.set_properties(**{'text-align': 'left'}), height=600, use_container_width=True)

        # Initialize Google Drive service
        service = initialize_drive_service()

        # Download Full Advising Report
        if st.button('Download Full Advising Report'):
            output_full = BytesIO()
            with pd.ExcelWriter(output_full, engine='openpyxl') as writer:
                full_report.to_excel(writer, index=False, sheet_name='Full Report')
                # After writing the main report, add the summary sheet
                add_summary_sheet(writer, st.session_state.courses_df, st.session_state.advising_selections, st.session_state.progress_df)
            output_full.seek(0)
            st.download_button(
                label='Download Full Advising Report',
                data=output_full.getvalue(),
                file_name='Full_Advising_Report.xlsx',
                mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )

            st.success('✅ Full Advising Report is ready for download.')
            log_info("Full Advising Report downloaded.")

    elif view_option == 'Individual Student':
        st.subheader('Individual Student Report')

        if st.session_state.progress_df.empty:
            st.warning("⚠️ Progress report is not loaded.")
            return

        # Select a student
        student_list = st.session_state.progress_df['ID'].astype(str) + ' - ' + st.session_state.progress_df['NAME']
        selected_student = st.selectbox('Select a Student', student_list, help="Select a student to view their full report.")

        selected_student_id = selected_student.split(' - ')[0]
        student_row = st.session_state.progress_df[st.session_state.progress_df['ID'] == int(selected_student_id)].iloc[0].to_dict()

        # Compute 'Standing' for the selected student
        credits_completed = student_row.get('# of Credits Completed', 0)
        standing = get_student_standing(credits_completed)
        log_info(f"Computed 'Standing' for student ID {selected_student_id}: {standing}")

        # Prepare full report for the selected student
        full_report = pd.DataFrame({
            'ID': [student_row['ID']],
            'NAME': [student_row['NAME']],
            '# of Credits Completed': [credits_completed],
            'Standing': [standing]
        })

        # Add Advising Status
        if selected_student_id in st.session_state.advising_selections and (st.session_state.advising_selections[selected_student_id].get('advised') or st.session_state.advising_selections[selected_student_id].get('optional')):
            advising_status = 'Advised'
        else:
            advising_status = 'Not Advised'
        full_report['Advising Status'] = advising_status

        # Add course status columns
        for course_code in st.session_state.courses_df['Course Code']:
            course_status = 'ne'
            if check_course_completed(student_row, course_code):
                course_status = 'c'
            else:
                advised_for_student = st.session_state.advising_selections.get(selected_student_id, {}).get('advised', [])
                optional_for_student = st.session_state.advising_selections.get(selected_student_id, {}).get('optional', [])
                eligibility_status, _ = check_eligibility(student_row, course_code, advised_for_student, st.session_state.courses_df)
                if course_code in advised_for_student:
                    course_status = 'a'
                elif course_code in optional_for_student:
                    course_status = 'o'
                elif eligibility_status == 'Eligible':
                    course_status = 'na'
                else:
                    course_status = 'ne'
            full_report[course_code] = course_status

        # Reorder columns
        cols = ['ID', 'NAME', '# of Credits Completed', 'Standing', 'Advising Status'] + list(st.session_state.courses_df['Course Code'])
        full_report = full_report[cols]

        st.write("*Legend:* c=Completed, a=Advised, o=Optional, na=Eligible not chosen, ne=Not Eligible")
        st.dataframe(full_report.style.set_properties(**{'text-align': 'left'}), height=600, use_container_width=True)

        # Initialize Google Drive service
        service = initialize_drive_service()

        # Download Individual Advising Report
        if st.button('Download Individual Advising Report'):
            output_individual = BytesIO()
            with pd.ExcelWriter(output_individual, engine='openpyxl') as writer:
                full_report.to_excel(writer, index=False, sheet_name='Individual Report')
                # After writing the main report, add the summary sheet
                add_summary_sheet(writer, st.session_state.courses_df, st.session_state.advising_selections, st.session_state.progress_df)
            output_individual.seek(0)
            st.download_button(
                label='Download Individual Advising Report',
                data=output_individual.getvalue(),
                file_name=f'{student_row["NAME"].replace(" ", "_")}_Advising_Report.xlsx',
                mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )

            st.success('✅ Individual Advising Report is ready for download.')
            log_info(f"Individual Advising Report downloaded for student ID {selected_student_id}.")

    # Download Advising Reports for All Advised Students
    if st.button('Download All Advised Students Reports'):
        advised_students = {sid: sel for sid, sel in st.session_state.advising_selections.items() if sel.get('advised') or sel.get('optional')}
        if not advised_students:
            st.warning("⚠️ No students have been advised yet.")
            log_info("Attempted to download reports, but no students have been advised.")
        else:
            multi_output = BytesIO()
            with pd.ExcelWriter(multi_output, engine='openpyxl') as writer:
                for sid, sel in advised_students.items():
                    # Fetch student row
                    srow = st.session_state.progress_df[st.session_state.progress_df['ID'] == int(sid)].iloc[0].to_dict()
                    credits = srow['# of Credits Completed']
                    standing = get_student_standing(credits)
                    log_info(f"Computed 'Standing' for student ID {sid}: {standing}")

                    eligibility_dict = {}
                    justification_dict = {}
                    for cc in st.session_state.courses_df['Course Code']:
                        stt, just = check_eligibility(
                            srow,
                            cc,
                            sel.get('advised', []),
                            st.session_state.courses_df
                        )
                        eligibility_dict[cc] = stt
                        justification_dict[cc] = just

                    def build_reqs(ci):
                        """Build a requisites string from course info."""
                        pieces = []
                        for key, prefix in [('Prerequisite', 'Prereq'), ('Concurrent', 'Conc'), ('Corequisite', 'Coreq')]:
                            value = ci.get(key, '')
                            if pd.isna(value):
                                continue
                            value = str(value).strip()
                            if value.upper() != 'N/A' and value != '':
                                pieces.append(f"{prefix}: {value}")
                        return "; ".join(pieces) if pieces else "None"

                    courses_data = []
                    for cc in st.session_state.courses_df['Course Code']:
                        stt = eligibility_dict[cc]
                        just = justification_dict[cc]
                        offered = 'Yes' if is_course_offered(st.session_state.courses_df, cc) else 'No'
                        cinfo = st.session_state.courses_df[st.session_state.courses_df['Course Code'] == cc].iloc[0]
                        ctype = cinfo['Type']
                        req_str = build_reqs(cinfo)

                        if check_course_completed(srow, cc):
                            action = 'Completed'
                            stt = 'Completed'
                        elif cc in sel.get('advised', []):
                            action = 'Advised'
                        elif cc in sel.get('optional', []):
                            action = 'Optional'
                        else:
                            if stt == 'Not Eligible':
                                action = 'Not Eligible'
                            elif stt == 'Eligible':
                                action = 'Eligible (not chosen)'

                        # For eligible courses without justification
                        if stt == 'Eligible' and just == '':
                            just = 'All requirements met.'

                        courses_data.append({
                            'Course Code': cc,
                            'Type': ctype,
                            'Requisites': req_str,
                            'Eligibility Status': stt,
                            'Justification': just,
                            'Offered': offered,
                            'Action': action
                        })
                    student_df = pd.DataFrame(courses_data)

                    # Calculate Credits Advised and Optional
                    if 'Credits' in st.session_state.courses_df.columns:
                        advised_credits = st.session_state.courses_df.loc[
                            st.session_state.courses_df['Course Code'].isin(sel.get('advised', [])),
                            'Credits'
                        ].sum()

                        optional_credits = st.session_state.courses_df.loc[
                            st.session_state.courses_df['Course Code'].isin(sel.get('optional', [])),
                            'Credits'
                        ].sum()
                    else:
                        advised_credits = 'N/A'
                        optional_credits = 'N/A'

                    # Write to Excel with student info at the top
                    sheet_name = f"{srow['NAME'][:25]}"
                    student_info = pd.DataFrame({
                        'A': ['Student Name:', 'Student ID:', '# of Credits Completed:', 'Standing:', 'Credits Advised:', 'Credits Optional:', 'Note:'],
                        'B': [srow['NAME'], srow['ID'], credits, standing, advised_credits, optional_credits, sel.get('note', '')]
                    })
                    student_info.to_excel(writer, sheet_name=sheet_name, index=False, header=False)
                    student_df.to_excel(writer, sheet_name=sheet_name, index=False, startrow=7)

                    # Apply formatting
                    ws = writer.sheets[sheet_name]
                    for cell in ws[8]:  # Header row is now at row 8
                        cell.font = Font(bold=True)

                    # Find 'Action' column
                    action_col = None
                    for idx, cell in enumerate(ws[8], start=1):
                        if cell.value == 'Action':
                            action_col = idx
                            break

                    # Apply color fills based on Action
                    if action_col:
                        for row in ws.iter_rows(min_row=9, max_row=ws.max_row, min_col=1, max_col=ws.max_column):
                            action_val = row[action_col-1].value
                            if action_val:
                                fill = None
                                if 'Completed' in action_val:
                                    fill = PatternFill(start_color='D3D3D3', end_color='D3D3D3', fill_type='solid')
                                elif 'Advised' in action_val:
                                    fill = PatternFill(start_color='90EE90', end_color='90EE90', fill_type='solid')
                                elif 'Optional' in action_val:
                                    fill = PatternFill(start_color='FFFACD', end_color='FFFACD', fill_type='solid')
                                elif 'Eligible (not chosen)' in action_val:
                                    fill = PatternFill(start_color='E0FFE0', end_color='E0FFE0', fill_type='solid')
                                elif 'Not Eligible' in action_val:
                                    fill = PatternFill(start_color='F08080', end_color='F08080', fill_type='solid')
                                if fill:
                                    for c in row:
                                        c.fill = fill

                    # Auto-adjust column widths
                    for column in ws.columns:
                        max_length = 0
                        column_letter = column[0].column_letter
                        for cell in column:
                            try:
                                cell_length = len(str(cell.value))
                                if cell_length > max_length:
                                    max_length = cell_length
                            except:
                                pass
                        adjusted_width = (max_length + 2)
                        ws.column_dimensions[column_letter].width = adjusted_width

            multi_output.seek(0)
            st.download_button(
                label='Download All Advised Students Reports',
                data=multi_output.getvalue(),
                file_name='All_Advised_Students.xlsx',
                mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )

            # Save to local file
            with open('All_Advised_Students.xlsx', 'wb') as f:
                f.write(multi_output.getvalue())

            # Sync with Google Drive
            try:
                sync_file_with_drive(
                    service=service,
                    file_content=multi_output.getvalue(),
                    drive_file_name='All_Advised_Students.xlsx',
                    mime_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                    parent_folder_id=st.secrets["google"]["folder_id"]
                )
                st.success('✅ All Advised Students Reports synced with Google Drive successfully!')
                log_info("All Advised Students Reports synced with Google Drive successfully.")
            except Exception as e:
                st.error(f'❌ Error syncing All Advised Students Reports: {e}')
                log_error('Error syncing All Advised Students Reports', e)
