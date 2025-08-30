# google_drive.py
import streamlit as st
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
import io
from googleapiclient.http import MediaIoBaseUpload, MediaIoBaseDownload
from utils import log_info, log_error

# Scopes
SCOPES = ['https://www.googleapis.com/auth/drive']

def get_credentials():
    """Retrieve Google API credentials from Streamlit secrets."""
    client_id = st.secrets["google"]["client_id"]
    client_secret = st.secrets["google"]["client_secret"]
    refresh_token = st.secrets["google"]["refresh_token"]
    return Credentials(
        None,
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=client_id,
        client_secret=client_secret,
        scopes=SCOPES,
    )

def initialize_drive_service():
    """Build and return the Google Drive service client."""
    creds = get_credentials()
    service = build('drive', 'v3', credentials=creds, cache_discovery=False)
    return service

# -----------------------------
# Cached READ helpers
# -----------------------------
@st.cache_data(show_spinner=False)
def _cached_find_file(file_name: str, parent_folder_id: str):
    """Return the first file id that matches file_name under parent_folder_id (cached)."""
    try:
        service = initialize_drive_service()
        query = f"name = '{file_name}' and '{parent_folder_id}' in parents and trashed = false"
        results = service.files().list(q=query, pageSize=1, fields="files(id,name)").execute()
        items = results.get('files', [])
        return items[0]['id'] if items else None
    except Exception as e:
        log_error(f"find_file_in_drive failed for {file_name}", e)
        return None

def find_file_in_drive(service, file_name: str, parent_folder_id: str):
    """Compatibility wrapper that uses the cached finder regardless of the passed service."""
    return _cached_find_file(file_name, parent_folder_id)

@st.cache_data(show_spinner=False)
def _cached_download_file(file_id: str) -> bytes:
    """Download a Drive file by id and return raw bytes (cached)."""
    try:
        service = initialize_drive_service()
        request = service.files().get_media(fileId=file_id)
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while not done:
            status, done = downloader.next_chunk()
        fh.seek(0)
        return fh.read()
    except Exception as e:
        log_error(f"download_file_from_drive failed for file_id={file_id}", e)
        return b""  # Let callers handle empty content gracefully

def download_file_from_drive(service, file_id: str) -> bytes:
    """Compatibility wrapper that uses the cached downloader regardless of the passed service."""
    return _cached_download_file(file_id)

# -----------------------------
# WRITE helpers (not cached)
# -----------------------------
def upload_file_to_drive(service, file_content, file_name, mime_type, parent_folder_id):
    media = MediaIoBaseUpload(io.BytesIO(file_content), mimetype=mime_type)
    file_metadata = {'name': file_name, 'parents': [parent_folder_id]}
    service.files().create(body=file_metadata, media_body=media, fields='id').execute()

def sync_file_with_drive(service, file_content, drive_file_name, mime_type, parent_folder_id):
    """Update a file if it exists in Drive; otherwise upload it."""
    try:
        # Use the cached finder to look up the id
        file_id = _cached_find_file(drive_file_name, parent_folder_id)
    except Exception:
        file_id = None

    # When writing, do NOT cache. Also, bust the read cache for this file after write.
    if file_id:
        try:
            media = MediaIoBaseUpload(io.BytesIO(file_content), mimetype=mime_type, resumable=False)
            service.files().update(fileId=file_id, media_body=media).execute()
            st.write(f"✅ Updated existing file: {drive_file_name}")
            log_info(f"Updated existing file on Drive: {drive_file_name}")
        except Exception as e:
            st.error(f"❌ Failed to update {drive_file_name}: {e}")
            log_error(f"Failed to update {drive_file_name}", e)
    else:
        try:
            upload_file_to_drive(service, file_content, drive_file_name, mime_type, parent_folder_id)
            st.write(f"✅ Uploaded new file: {drive_file_name}")
            log_info(f"Uploaded new file to Drive: {drive_file_name}")
        except Exception as e:
            st.error(f"❌ Failed to upload {drive_file_name}: {e}")
            log_error(f"Failed to upload {drive_file_name}", e)

    # Invalidate the cache for this file (and for the name lookup) so next read fetches fresh
    try:
        _cached_download_file.clear()  # Clear all cached downloads
        _cached_find_file.clear()      # Clear all cached lookups
    except Exception:
        pass
