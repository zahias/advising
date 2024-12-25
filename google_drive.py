# google_drive.py

import streamlit as st
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
import io
from googleapiclient.http import MediaIoBaseUpload, MediaIoBaseDownload
from utils import log_info, log_error  # Ensure logging functions are imported

# Define the scopes
SCOPES = ['https://www.googleapis.com/auth/drive']

def get_credentials():
    """Retrieve Google API credentials from Streamlit secrets."""
    client_id = st.secrets["google"]["client_id"]
    client_secret = st.secrets["google"]["client_secret"]
    refresh_token = st.secrets["google"]["refresh_token"]

    creds = Credentials(
        None,
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=client_id,
        client_secret=client_secret,
        scopes=SCOPES
    )
    return creds

def initialize_drive_service():
    """Initialize the Google Drive service."""
    creds = get_credentials()
    service = build('drive', 'v3', credentials=creds)
    return service

def upload_file_to_drive(service, file_content, file_name, mime_type, parent_folder_id=None):
    """Upload a file to Google Drive."""
    file_metadata = {'name': file_name}
    if parent_folder_id:
        file_metadata['parents'] = [parent_folder_id]
    media = MediaIoBaseUpload(io.BytesIO(file_content), mimetype=mime_type, resumable=True)
    file = service.files().create(body=file_metadata, media_body=media, fields='id').execute()
    log_info(f"Uploaded file '{file_name}' to Google Drive with ID: {file.get('id')}")
    return file.get('id')

def download_file_from_drive(service, file_id):
    """Download a file from Google Drive."""
    request = service.files().get_media(fileId=file_id)
    fh = io.BytesIO()
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while not done:
        status, done = downloader.next_chunk()
    fh.seek(0)
    log_info(f"Downloaded file from Google Drive with ID: {file_id}")
    return fh.read()

def find_file_in_drive(service, file_name, parent_folder_id=None):
    """Find a file in Google Drive by name."""
    query = f"name = '{file_name}' and trashed = false"
    if parent_folder_id:
        query += f" and '{parent_folder_id}' in parents"
    results = service.files().list(q=query, fields="files(id, name)").execute()
    items = results.get('files', [])
    if not items:
        log_info(f"File '{file_name}' not found in Google Drive.")
        return None
    else:
        log_info(f"Found file '{file_name}' in Google Drive with ID: {items[0]['id']}")
        return items[0]['id']

def sync_file_with_drive(service, file_content, drive_file_name, mime_type, parent_folder_id=None):
    """
    Sync a file with Google Drive.
    If the file exists, update it.
    Else, upload it.
    """
    file_id = find_file_in_drive(service, drive_file_name, parent_folder_id)
    if file_id:
        try:
            # Update existing file
            media = MediaIoBaseUpload(io.BytesIO(file_content), mimetype=mime_type, resumable=True)
            service.files().update(fileId=file_id, media_body=media).execute()
            st.write(f"✅ Updated existing file: {drive_file_name}")
            log_info(f"Updated existing file on Drive: {drive_file_name}")
        except Exception as e:
            st.error(f"❌ Failed to update {drive_file_name}: {e}")
            log_error(f"Failed to update {drive_file_name}", e)
    else:
        try:
            # Upload new file
            upload_file_to_drive(service, file_content, drive_file_name, mime_type, parent_folder_id)
            st.write(f"✅ Uploaded new file: {drive_file_name}")
            log_info(f"Uploaded new file to Drive: {drive_file_name}")
        except Exception as e:
            st.error(f"❌ Failed to upload {drive_file_name}: {e}")
            log_error(f"Failed to upload {drive_file_name}", e)
