# app.py

import streamlit as st
import pandas as pd
import os
from io import BytesIO

from data_upload import upload_data
from eligibility_view import student_eligibility_view
from full_student_view import full_student_view
from google_drive import (
    download_file_from_drive,
    sync_file_with_drive,
    initialize_drive_service,
    find_file_in_drive
)
from utils import log_info, log_error  # Ensure these are correctly implemented

# Set page configuration
st.set_page_config(layout='wide')

# Header: Logo and title side by side
header_col1, header_col2 = st.columns([0.15, 0.85])
with header_col1:
    if os.path.exists('pu_logo.png'):
        st.image('pu_logo.png', width=100)
    else:
        st.write("Logo not found.")

with header_col2:
    st.markdown("""
    <h1 style="margin-bottom:0px;">Phoenicia University Advising System</h1>
    <p style="margin-top:0px;">Manage eligibility, advising, and reporting efficiently.</p>
    """, unsafe_allow_html=True)

st.markdown("<small>System developed by Dr. Zahi Abdul Sater</small>", unsafe_allow_html=True)

# Initialize Google Drive service
service = initialize_drive_service()

# Function to load data from Google Drive
def load_data_from_drive():
    # Load Courses Table
    courses_file_id = find_file_in_drive(service, 'courses_table.xlsx', st.secrets["google"]["folder_id"])
    if courses_file_id:
        try:
            courses_content = download_file_from_drive(service, courses_file_id)
            st.session_state.courses_df = pd.read_excel(BytesIO(courses_content))
            st.success('✅ Courses table loaded from Google Drive.')
            log_info('Courses table loaded successfully.')
        except Exception as e:
            st.session_state.courses_df = pd.DataFrame()
            st.error(f'❌ Error loading courses table: {e}')
            log_error('Error loading courses table', e)
    else:
        st.session_state.courses_df = pd.DataFrame()
        st.warning('⚠️ Courses table not found on Google Drive.')
        log_error('Courses table not found on Google Drive.', 'File does not exist.')

    # Load Progress Report
    progress_file_id = find_file_in_drive(service, 'progress_report.xlsx', st.secrets["google"]["folder_id"])
    if progress_file_id:
        try:
            progress_content = download_file_from_drive(service, progress_file_id)
            st.session_state.progress_df = pd.read_excel(BytesIO(progress_content))
            st.success('✅ Progress report loaded from Google Drive.')
            log_info('Progress report loaded successfully.')
        except Exception as e:
            st.session_state.progress_df = pd.DataFrame()
            st.error(f'❌ Error loading progress report: {e}')
            log_error('Error loading progress report', e)
    else:
        st.session_state.progress_df = pd.DataFrame()
        st.warning('⚠️ Progress report not found on Google Drive.')
        log_error('Progress report not found on Google Drive.', 'File does not exist.')

    # Load Advising Selections
    advising_file_id = find_file_in_drive(service, 'advising_selections.xlsx', st.secrets["google"]["folder_id"])
    if advising_file_id:
        try:
            advising_content = download_file_from_drive(service, advising_file_id)
            advising_df = pd.read_excel(BytesIO(advising_content))
            # Convert the DataFrame into a dictionary
            advising_selections = {}
            for _, row in advising_df.iterrows():
                advising_selections[str(row['ID'])] = {
                    'advised': [course.strip() for course in row['Advised'].split(',')] if pd.notna(row['Advised']) and row['Advised'].strip() != '' else [],
                    'optional': [course.strip() for course in row['Optional'].split(',')] if pd.notna(row['Optional']) and row['Optional'].strip() != '' else [],
                    'note': row['Note'] if pd.notna(row['Note']) else ''
                }
            st.session_state.advising_selections = advising_selections
            st.success('✅ Advising selections loaded from Google Drive.')
            log_info('Advising selections loaded successfully.')
        except Exception as e:
            st.session_state.advising_selections = {}
            st.error(f'❌ Error loading advising selections: {e}')
            log_error('Error loading advising selections', e)
    else:
        st.session_state.advising_selections = {}
        st.warning('⚠️ Advising selections not found on Google Drive. Initializing a new one.')
        log_info('Advising selections not found on Google Drive. Initializing a new one.')
        # Initialize empty advising_selections.xlsx
        empty_df = pd.DataFrame(columns=['ID', 'Advised', 'Optional', 'Note'])
        advising_content = BytesIO()
        empty_df.to_excel(advising_content, index=False)
        try:
            sync_file_with_drive(
                service,
                advising_content.getvalue(),
                'advising_selections.xlsx',
                'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                st.secrets["google"]["folder_id"]
            )
            st.success('✅ Initialized empty advising_selections.xlsx on Google Drive.')
            log_info('Initialized empty advising_selections.xlsx on Google Drive.')
        except Exception as e:
            st.error(f'❌ Error initializing advising selections on Google Drive: {e}')
            log_error('Error initializing advising selections on Google Drive', e)

# Function to save data to Google Drive
def save_data_to_drive():
    # Define the mapping of DataFrames to Drive file names
    files_to_sync = {
        'courses_table.xlsx': st.session_state.courses_df,
        'progress_report.xlsx': st.session_state.progress_df,
        'advising_selections.xlsx': pd.DataFrame([
            {
                'ID': sid,
                'Advised': ', '.join(sel.get('advised', [])),
                'Optional': ', '.join(sel.get('optional', [])),
                'Note': sel.get('note', '')
            }
            for sid, sel in st.session_state.advising_selections.items()
        ])
    }

    for drive_file_name, df in files_to_sync.items():
        if df.empty and drive_file_name != 'advising_selections.xlsx':
            st.warning(f"The DataFrame for {drive_file_name} is empty. Skipping upload.")
            log_info(f"Skipped uploading {drive_file_name} because the DataFrame is empty.")
            continue
        try:
            # Convert DataFrame to Excel bytes
            excel_buffer = BytesIO()
            df.to_excel(excel_buffer, index=False)
            excel_buffer.seek(0)
            file_content = excel_buffer.getvalue()

            # Sync the file with Google Drive
            sync_file_with_drive(
                service,
                file_content,
                drive_file_name,
                'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                st.secrets["google"]["folder_id"]
            )

            st.success(f'✅ {drive_file_name} synced with Google Drive successfully.')
            log_info(f'{drive_file_name} synced with Google Drive successfully.')
        except Exception as e:
            st.error(f'❌ Error syncing {drive_file_name} to Google Drive: {e}')
            log_error(f'Error syncing {drive_file_name} to Google Drive', e)

# Load data from Drive on startup
if 'courses_df' not in st.session_state or 'progress_df' not in st.session_state or 'advising_selections' not in st.session_state:
    load_data_from_drive()

# Ensure that session_state variables exist
if 'courses_df' not in st.session_state:
    st.session_state.courses_df = pd.DataFrame()

if 'progress_df' not in st.session_state:
    st.session_state.progress_df = pd.DataFrame()

if 'advising_selections' not in st.session_state:
    st.session_state.advising_selections = {}

# Sidebar: Upload Data
upload_data()

# After uploading data, save it to Drive
if st.session_state.get('data_uploaded', False):
    save_data_to_drive()
    st.session_state.data_uploaded = False  # Reset the flag

# Main Area: Check if data is loaded
if not st.session_state.progress_df.empty and not st.session_state.courses_df.empty:
    tab1, tab2 = st.tabs(['Student Eligibility View', 'Full Student View'])

    with tab1:
        student_eligibility_view()

    with tab2:
        full_student_view()

else:
    st.info('📝 Please upload both the progress report and courses table to continue.')
