# data_upload.py

import streamlit as st
import pandas as pd
from google_drive import initialize_drive_service
from io import BytesIO

def upload_data():
    """Handle uploading of courses table, progress report, and advising selections."""
    st.sidebar.header('Upload Data')

    service = initialize_drive_service()

    # Upload Courses Table
    courses_file = st.sidebar.file_uploader('Upload Courses Table (courses_table.xlsx)', type=['xlsx'], key='courses_upload')
    if courses_file:
        try:
            courses_df = pd.read_excel(courses_file)
            st.session_state.courses_df = courses_df
            st.session_state.data_uploaded = True  # Flag to save to Drive
            st.sidebar.success('Courses table uploaded successfully.')
        except Exception as e:
            st.sidebar.error(f'Error uploading courses table: {e}')

    # Upload Progress Report
    progress_file = st.sidebar.file_uploader('Upload Progress Report (progress_report.xlsx)', type=['xlsx'], key='progress_upload')
    if progress_file:
        try:
            progress_df = pd.read_excel(progress_file)
            st.session_state.progress_df = progress_df
            st.session_state.data_uploaded = True  # Flag to save to Drive
            st.sidebar.success('Progress report uploaded successfully.')
        except Exception as e:
            st.sidebar.error(f'Error uploading progress report: {e}')

    # Upload Advising Selections
    advising_file = st.sidebar.file_uploader('Upload Advising Selections (advising_selections.xlsx)', type=['xlsx'], key='advising_upload')
    if advising_file:
        try:
            advising_df = pd.read_excel(advising_file)
            advising_selections = {}
            for _, row in advising_df.iterrows():
                advising_selections[str(row['ID'])] = {
                    'advised': [course.strip() for course in row['Advised'].split(',')] if pd.notna(row['Advised']) and row['Advised'].strip() != '' else [],
                    'optional': [course.strip() for course in row['Optional'].split(',')] if pd.notna(row['Optional']) and row['Optional'].strip() != '' else [],
                    'note': row['Note'] if pd.notna(row['Note']) else ''
                }
            st.session_state.advising_selections = advising_selections
            st.session_state.data_uploaded = True  # Flag to save to Drive
            st.sidebar.success('Advising selections uploaded successfully.')
        except Exception as e:
            st.sidebar.error(f'Error uploading advising selections: {e}')

    # Display current data status
    if st.session_state.get('courses_df') is not None and not st.session_state.courses_df.empty:
        st.sidebar.success('Courses table is loaded.')
    else:
        st.sidebar.warning('Courses table not uploaded.')

    if st.session_state.get('progress_df') is not None and not st.session_state.progress_df.empty:
        st.sidebar.success('Progress report is loaded.')
    else:
        st.sidebar.warning('Progress report not uploaded.')

    if st.session_state.get('advising_selections') is not None and st.session_state.advising_selections:
        st.sidebar.success('Advising selections are loaded.')
    else:
        st.sidebar.warning('Advising selections not uploaded.')
