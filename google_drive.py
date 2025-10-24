# google_drive.py
# Google Drive helpers with robust token refresh + update-or-create sync.
# Scope-agnostic refresh (avoids invalid_scope) and corrected files().list query.
# Added helpers: list_files_with_prefix, download_file_by_name, delete_file_by_name.

from __future__ import annotations

import io
from typing import Optional, List, Dict

import streamlit as st
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload, MediaIoBaseDownload
from googleapiclient.errors import HttpError
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request


GOOGLE_TOKEN_URI = "https://oauth2.googleapis.com/token"

class GoogleAuthError(Exception):
    """Raised when Google auth/refresh fails (e.g. invalid_grant, invalid_scope)."""


def _secrets() -> dict:
    try:
        return st.secrets["google"]
    except Exception:
        return {}


def _get_credentials_hash() -> str:
    """Generate a hash of credentials for cache key."""
    import os
    import hashlib
    
    s = _secrets()
    client_id = s.get("client_id") or os.getenv("GOOGLE_CLIENT_ID") or ""
    client_secret = s.get("client_secret") or os.getenv("GOOGLE_CLIENT_SECRET") or ""
    refresh_token = s.get("refresh_token") or os.getenv("GOOGLE_REFRESH_TOKEN") or ""
    
    cred_string = f"{client_id}:{client_secret}:{refresh_token}"
    return hashlib.md5(cred_string.encode()).hexdigest()


def _build_credentials() -> Credentials:
    import os
    
    s = _secrets()
    client_id = s.get("client_id") or os.getenv("GOOGLE_CLIENT_ID")
    client_secret = s.get("client_secret") or os.getenv("GOOGLE_CLIENT_SECRET")
    refresh_token = s.get("refresh_token") or os.getenv("GOOGLE_REFRESH_TOKEN")

    if not (client_id and client_secret and refresh_token):
        raise GoogleAuthError(
            "Missing Google credentials in secrets. "
            "Please set GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_REFRESH_TOKEN in Replit Secrets."
        )

    # Do NOT pin scopes here; let the refresh token carry the granted scopes.
    creds = Credentials(
        token=None,
        refresh_token=refresh_token,
        token_uri=GOOGLE_TOKEN_URI,
        client_id=client_id,
        client_secret=client_secret,
    )

    # Force refresh now; normalize common errors.
    try:
        creds.refresh(Request())
    except Exception as e:
        msg = str(e)
        if "invalid_grant" in msg or "Token has been expired or revoked" in msg:
            raise GoogleAuthError(
                "Google token refresh failed: invalid_grant (token expired or revoked). "
                "Re-authorize and update google.refresh_token in Streamlit Secrets."
            ) from e
        if "invalid_scope" in msg:
            raise GoogleAuthError(
                "Google token refresh failed: invalid_scope. "
                "Re-mint the refresh token using the SAME client_id/client_secret in Streamlit Secrets "
                "and grant Drive access (e.g., drive.file) — then paste the new refresh_token."
            ) from e
        raise GoogleAuthError(f"Google auth refresh failed: {e}") from e

    return creds


@st.cache_resource(ttl=3600)
def _get_cached_drive_service(_cred_hash: str):
    """Cached Drive service - only recreates if credentials change or after 1 hour."""
    creds = _build_credentials()
    try:
        service = build("drive", "v3", credentials=creds, cache_discovery=False)
        return service
    except Exception as e:
        raise GoogleAuthError(f"Failed to initialize Drive service: {e}") from e


def initialize_drive_service():
    """Return a cached authenticated Drive service or raise GoogleAuthError."""
    cred_hash = _get_credentials_hash()
    return _get_cached_drive_service(cred_hash)


def find_file_in_drive(service, filename: str, parent_folder_id: str) -> Optional[str]:
    """Return fileId for `filename` inside `parent_folder_id`, else None."""
    try:
        query = f"name = '{filename}' and '{parent_folder_id}' in parents and trashed = false"
        resp = service.files().list(
            q=query,
            spaces="drive",
            fields="files(id, name)",
            pageSize=10,
            includeItemsFromAllDrives=False,
            supportsAllDrives=False,
        ).execute()
        for f in resp.get("files", []):
            if f.get("name") == filename:
                return f.get("id")
        return None
    except HttpError as e:
        raise RuntimeError(f"Drive search failed: {e}")


def download_file_from_drive(service, file_id: str) -> bytes:
    """Download file content by id."""
    # Note: Removed caching here because Drive service object cannot be hashed.
    # Caching is now handled at the application level for specific files.
    try:
        req = service.files().get_media(fileId=file_id)
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, req)
        done = False
        while not done:
            _, done = downloader.next_chunk()
        return fh.getvalue()
    except HttpError as e:
        raise RuntimeError(f"Drive download failed: {e}")


def sync_file_with_drive(
    service,
    file_content: bytes,
    drive_file_name: str,
    mime_type: str,
    parent_folder_id: str,
) -> str:
    """
    Create or replace a file by name inside `parent_folder_id`.
    Returns the fileId.
    """
    media = MediaIoBaseUpload(io.BytesIO(file_content), mimetype=mime_type, resumable=False)
    body = {"name": drive_file_name, "parents": [parent_folder_id]}

    try:
        file_id = find_file_in_drive(service, drive_file_name, parent_folder_id)
        if file_id:
            updated = service.files().update(
                fileId=file_id,
                media_body=media,
                body={"name": drive_file_name},
                supportsAllDrives=False,
            ).execute()
            return updated.get("id", file_id)
        else:
            created = service.files().create(
                body=body,
                media_body=media,
                fields="id",
                supportsAllDrives=False,
            ).execute()
            return created.get("id")
    except HttpError as e:
        raise RuntimeError(f"Drive sync failed: {e}")


# ----------------- New small helpers -----------------

def list_files_with_prefix(service, parent_folder_id: str, prefix: str, page_size: int = 100) -> List[Dict]:
    """
    List files in folder whose name contains `prefix`, newest first.
    Returns list of dicts with keys: id, name, modifiedTime.
    """
    try:
        query = f"name contains '{prefix}' and '{parent_folder_id}' in parents and trashed = false"
        resp = service.files().list(
            q=query,
            spaces="drive",
            fields="files(id, name, modifiedTime)",
            pageSize=page_size,
            orderBy="modifiedTime desc",
            includeItemsFromAllDrives=False,
            supportsAllDrives=False,
        ).execute()
        return resp.get("files", [])
    except HttpError as e:
        raise RuntimeError(f"Drive list failed: {e}")


def download_file_by_name(service, parent_folder_id: str, filename: str) -> Optional[bytes]:
    """Find by exact name in folder and download."""
    fid = find_file_in_drive(service, filename, parent_folder_id)
    if not fid:
        return None
    return download_file_from_drive(service, fid)


def delete_file_by_name(service, parent_folder_id: str, filename: str) -> bool:
    """Delete a file by name if it exists. Returns True if deleted or not present."""
    try:
        fid = find_file_in_drive(service, filename, parent_folder_id)
        if not fid:
            return True
        service.files().delete(fileId=fid).execute()
        return True
    except HttpError:
        return False
