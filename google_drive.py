# google_drive.py
# Google Drive helpers with robust token refresh + update-or-create sync.

from __future__ import annotations

import io
from typing import Optional

import streamlit as st
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload, MediaIoBaseDownload
from googleapiclient.errors import HttpError
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request


GOOGLE_TOKEN_URI = "https://oauth2.googleapis.com/token"
DRIVE_SCOPE = ["https://www.googleapis.com/auth/drive.file"]  # access within app-folder


class GoogleAuthError(Exception):
    """Raised when Google auth/refresh fails (e.g. invalid_grant)."""


def _secrets() -> dict:
    try:
        return st.secrets["google"]
    except Exception:
        return {}


def _build_credentials() -> Credentials:
    s = _secrets()
    client_id = s.get("client_id")
    client_secret = s.get("client_secret")
    refresh_token = s.get("refresh_token")

    if not (client_id and client_secret and refresh_token):
        raise GoogleAuthError(
            "Missing Google credentials in secrets. "
            "Please set google.client_id, google.client_secret, google.refresh_token."
        )

    # Start with no access token; rely on refresh flow
    creds = Credentials(
        token=None,
        refresh_token=refresh_token,
        token_uri=GOOGLE_TOKEN_URI,
        client_id=client_id,
        client_secret=client_secret,
        scopes=DRIVE_SCOPE,
    )

    # Force refresh now; if refresh token is expired/revoked, this will raise
    try:
        creds.refresh(Request())
    except Exception as e:
        # Normalize common OAuth error
        msg = str(e)
        if "invalid_grant" in msg or "Token has been expired or revoked" in msg:
            raise GoogleAuthError(
                "Google token refresh failed: invalid_grant (token expired or revoked). "
                "Re-authorize and update google.refresh_token in Streamlit Secrets."
            ) from e
        raise GoogleAuthError(f"Google auth refresh failed: {e}") from e

    return creds


def initialize_drive_service():
    """Return an authenticated Drive service or raise GoogleAuthError."""
    creds = _build_credentials()
    try:
        service = build("drive", "v3", credentials=creds, cache_discovery=False)
        return service
    except Exception as e:
        raise GoogleAuthError(f"Failed to initialize Drive service: {e}") from e


def find_file_in_drive(service, filename: str, parent_folder_id: str) -> Optional[str]:
    """Return fileId for `filename` within `parent_folder_id`, else None."""
    try:
        q = "name = @name and '{}' in parents and trashed = false".format(parent_folder_id)
        resp = service.files().list(
            q=q,
            spaces="drive",
            fields="files(id, name)",
            pageSize=10,
            corpora="user",
            includeItemsFromAllDrives=False,
            supportsAllDrives=False,
            parameters={"name": filename},  # named parameter for @name
        ).execute()
        for f in resp.get("files", []):
            if f.get("name") == filename:
                return f.get("id")
        return None
    except HttpError as e:
        raise RuntimeError(f"Drive search failed: {e}")


def download_file_from_drive(service, file_id: str) -> bytes:
    """Download file content by id."""
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
            # Update existing
            updated = service.files().update(
                fileId=file_id,
                media_body=media,
                body={"name": drive_file_name},
                supportsAllDrives=False,
            ).execute()
            return updated.get("id", file_id)
        else:
            # Create new
            created = service.files().create(
                body=body,
                media_body=media,
                fields="id",
                supportsAllDrives=False,
            ).execute()
            return created.get("id")
    except HttpError as e:
        raise RuntimeError(f"Drive sync failed: {e}")
