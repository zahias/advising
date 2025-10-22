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
from reporting import add_summary_sheet, build_full_advising_workbook
from google_drive import sync_file_with_drive, initialize_drive_service
from openpyxl import Workbook

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

        full_report = st.session_state.progress_df[['ID', 'NAME', '# of Credits Completed']].copy()
        full_report['Standing'] = full_report['# of Credits Completed'].apply(get_student_standing)
        log_info("Computed 'Standing' for all students.")

        advising_statuses = []
        for _, student in st.session_state.progress_df.iterrows():
            sid = str(student['ID'])
            if sid in st.session_state.advising_selections and (st.session_state.advising_selections[sid].get('advised') or st.session_state.advising_selections[sid].get('optional')):
                advising_statuses.append('Advised')
            else:
                advising_statuses.append('Not Advised')
        full_report['Advising Status'] = advising_statuses

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

        cols = ['ID', 'NAME', '# of Credits Completed', 'Standing', 'Advising Status'] + list(st.session_state.courses_df['Course Code'])
        full_report = full_report[cols]

        st.write("*Legend:* c=Completed, a=Advised, o=Optional, na=Eligible not chosen, ne=Not Eligible")
        st.dataframe(full_report.style.set_properties(**{'text-align': 'left'}), height=600, use_container_width=True)

        service = initialize_drive_service()

        # ---------- Download Full Advising Report (formatted) ----------
        if st.button('Download Full Advising Report'):
            # Build per-student sheets from the same data you already compute in the "All Advised Students Reports"
            wb = Workbook()
            wb.remove(wb.active)  # clear default sheet

            student_tables = {}
            student_meta = {}

            for _, srow in st.session_state.progress_df.iterrows():
                sid = str(srow['ID'])
                selections = st.session_state.advising_selections.get(sid, {})
                advised = selections.get('advised', [])
                optional = selections.get('optional', [])
                note    = selections.get('note', '')

                credits_completed = srow.get('# of Credits Completed', 0)
                standing = get_student_standing(credits_completed)

                # Build eligibility/action table per student (same as earlier logic)
                rows = []
                for cc in st.session_state.courses_df['Course Code']:
                    offered = 'Yes' if is_course_offered(st.session_state.courses_df, cc) else 'No'
                    stt, just = check_eligibility(srow, cc, advised, st.session_state.courses_df)
                    action = 'Not Eligible'
                    if check_course_completed(srow, cc):
                        stt = 'Completed'
                        action = 'Completed'
                    elif cc in advised:
                        action = 'Advised'
                    elif cc in optional:
                        action = 'Optional'
                    elif stt == 'Eligible':
                        action = 'Eligible (not chosen)'

                    rows.append({
                        'Course Code': cc,
                        'Eligibility Status': stt,
                        'Justification': (just or 'All requirements met.') if stt == 'Eligible' else (just or ''),
                        'Offered': offered,
                        'Action': action
                    })
                df = pd.DataFrame(rows)

                # Compute credit sums if you have 'Credits' column
                if 'Credits' in st.session_state.courses_df.columns:
                    credits_map = dict(zip(st.session_state.courses_df['Course Code'], st.session_state.courses_df['Credits']))
                    advised_credits = sum(credits_map.get(c, 0) for c in advised)
                    optional_credits = sum(credits_map.get(c, 0) for c in optional)
                else:
                    advised_credits = 'N/A'
                    optional_credits = 'N/A'

                student_tables[sid] = df
                student_meta[sid] = {
                    'name': srow['NAME'],
                    'credits': credits_completed,
                    'standing': standing,
                    'advised_credits': advised_credits,
                    'optional_credits': optional_credits,
                    'note': note
                }

            wb = build_full_advising_workbook(wb, student_meta, student_tables)

            # Add summary sheet at the end using existing writer pattern
            output_full = BytesIO()
            wb.save(output_full)
            output_full.seek(0)

            # Reopen with pandas writer just to append the Summary sheet
            with pd.ExcelWriter(output_full, engine='openpyxl', mode='a') as writer:
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

        student_list = st.session_state.progress_df['ID'].astype(str) + ' - ' + st.session_state.progress_df['NAME']
        selected_student = st.selectbox('Select a Student', student_list, help="Select a student to view their full report.")

        selected_student_id = selected_student.split(' - ')[0]
        student_row = st.session_state.progress_df[st.session_state.progress_df['ID'] == int(selected_student_id)].iloc[0].to_dict()

        credits_completed = student_row.get('# of Credits Completed', 0)
        standing = get_student_standing(credits_completed)
        log_info(f"Computed 'Standing' for student ID {selected_student_id}: {standing}")

        # Build one student table (short)
        selections = st.session_state.advising_selections.get(selected_student_id, {})
        advised = selections.get('advised', [])
        optional = selections.get('optional', [])
        note    = selections.get('note', '')

        rows = []
        for cc in st.session_state.courses_df['Course Code']:
            offered = 'Yes' if is_course_offered(st.session_state.courses_df, cc) else 'No'
            stt, just = check_eligibility(student_row, cc, advised, st.session_state.courses_df)
            action = 'Not Eligible'
            if check_course_completed(student_row, cc):
                stt = 'Completed'
                action = 'Completed'
            elif cc in advised:
                action = 'Advised'
            elif cc in optional:
                action = 'Optional'
            elif stt == 'Eligible':
                action = 'Eligible (not chosen)'

            rows.append({
                'Course Code': cc,
                'Eligibility Status': stt,
                'Justification': (just or 'All requirements met.') if stt == 'Eligible' else (just or ''),
                'Offered': offered,
                'Action': action
            })
        df = pd.DataFrame(rows)

        st.write("*Legend:* c=Completed, a=Advised, o=Optional, na=Eligible not chosen, ne=Not Eligible")
        st.dataframe(df, height=600, use_container_width=True)

        service = initialize_drive_service()

        # ---------- Download Individual Advising Report (formatted) ----------
        if st.button('Download Individual Advising Report'):
            wb = Workbook()
            wb.remove(wb.active)
            student_tables = {selected_student_id: df}

            # credits
            if 'Credits' in st.session_state.courses_df.columns:
                credits_map = dict(zip(st.session_state.courses_df['Course Code'], st.session_state.courses_df['Credits']))
                advised_credits = sum(credits_map.get(c, 0) for c in advised)
                optional_credits = sum(credits_map.get(c, 0) for c in optional)
            else:
                advised_credits = 'N/A'
                optional_credits = 'N/A'

            student_meta = {
                selected_student_id: {
                    'name': student_row['NAME'],
                    'credits': credits_completed,
                    'standing': standing,
                    'advised_credits': advised_credits,
                    'optional_credits': optional_credits,
                    'note': note
                }
            }

            wb = build_full_advising_workbook(wb, student_meta, student_tables)

            output_individual = BytesIO()
            wb.save(output_individual)
            output_individual.seek(0)

            st.download_button(
                label='Download Individual Advising Report',
                data=output_individual.getvalue(),
                file_name=f'{student_row["NAME"].replace(" ", "_")}_Advising_Report.xlsx',
                mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )

            st.success('✅ Individual Advising Report is ready for download.')
            log_info(f"Individual Advising Report downloaded for student ID {selected_student_id}.")

    # (No changes to the Drive sync block for "Download All Advised Students Reports" – keep your existing flow)
