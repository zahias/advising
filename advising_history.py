# advising_history.py

import json
from io import BytesIO
from typing import Any, Dict, List
from uuid import uuid4
from datetime import datetime, date

import pandas as pd
import streamlit as st

from google_drive import (
    initialize_drive_service,
    find_file_in_drive,
    download_file_from_drive,
    sync_file_with_drive,
)
from utils import log_info, log_error

_SESSIONS_FILENAME = "advising_sessions.json"

def _load_sessions_from_drive() -> List[Dict[str, Any]]:
    """Load sessions list from Google Drive; returns [] if none."""
    try:
        service = initialize_drive_service()
        folder_id = st.secrets["google"]["folder_id"]
        file_id = find_file_in_drive(service, _SESSIONS_FILENAME, folder_id)
        if not file_id:
            return []
        payload = download_file_from_drive(service, file_id)  # bytes
        try:
            sessions = json.loads(payload.decode("utf-8"))
            if isinstance(sessions, list):
                return sessions
        except Exception:
            pass
        return []
    except Exception as e:
        log_error("Failed to load advising sessions from Drive", e)
        return []

def _save_sessions_to_drive(sessions: List[Dict[str, Any]]) -> None:
    """Overwrite the sessions file in Google Drive with provided list."""
    try:
        service = initialize_drive_service()
        folder_id = st.secrets["google"]["folder_id"]
        data_bytes = json.dumps(sessions, ensure_ascii=False, indent=2).encode("utf-8")
        sync_file_with_drive(
            service=service,
            file_content=data_bytes,
            drive_file_name=_SESSIONS_FILENAME,
            mime_type="application/json",
            parent_folder_id=folder_id,
        )
        log_info("Advising sessions saved to Drive.")
    except Exception as e:
        log_error("Failed to save advising sessions to Drive", e)
        raise

def _ensure_sessions_loaded() -> None:
    """Ensure st.session_state.advising_sessions is a list (loaded once)."""
    if "advising_sessions" not in st.session_state:
        st.session_state.advising_sessions = _load_sessions_from_drive()

def _serialize_current_selections() -> Dict[str, Any]:
    """
    Take the current advising selections (dict keyed by student ID) and
    convert keys to strings so the JSON is stable.
    """
    selections = st.session_state.get("advising_selections", {}) or {}
    out: Dict[str, Any] = {}
    for sid, payload in selections.items():
        key = str(sid)
        out[key] = {
            "advised": list(payload.get("advised", [])),
            "optional": list(payload.get("optional", [])),
            "note": payload.get("note", ""),
        }
    return out

def _restore_selections(saved_obj: Dict[str, Any]) -> None:
    """
    Replace the current advising selections with a saved snapshot.
    Keys are strings in storage; convert to int where possible.
    """
    restored: Dict[int, Dict[str, Any]] = {}
    for sid_str, payload in (saved_obj or {}).items():
        try:
            sid = int(sid_str)
        except Exception:
            # keep original if cannot parse
            sid = sid_str  # type: ignore[assignment]
        restored[sid] = {
            "advised": list(payload.get("advised", [])),
            "optional": list(payload.get("optional", [])),
            "note": payload.get("note", ""),
        }
    st.session_state.advising_selections = restored

def advising_history_panel():
    """
    Renders the Advising Sessions panel:
      - Advisor name, session date, semester, year
      - Save current advising snapshot
      - Retrieve a previously saved snapshot
    """
    _ensure_sessions_loaded()

    st.markdown("---")
    st.subheader("Advising Sessions")

    col1, col2, col3, col4 = st.columns([2, 2, 2, 2])
    with col1:
        advisor_name = st.text_input("Advisor Name", key="adv_hist_name")
    with col2:
        session_date: date = st.date_input("Session Date", key="adv_hist_date")
    with col3:
        semester = st.selectbox("Semester", ["Fall", "Spring", "Summer"], key="adv_hist_sem")
    with col4:
        year = st.number_input("Year", min_value=2000, max_value=2100, value=datetime.now().year, step=1, key="adv_hist_year")

    # Save session snapshot
    save_col, load_col = st.columns([1, 2])

    with save_col:
        if st.button("💾 Save Advising Session", use_container_width=True):
            if not advisor_name:
                st.error("Please enter Advisor Name.")
            else:
                try:
                    snapshot = {
                        "id": str(uuid4()),
                        "advisor": advisor_name,
                        "session_date": session_date.isoformat() if isinstance(session_date, date) else str(session_date),
                        "semester": semester,
                        "year": int(year),
                        "created_at": datetime.utcnow().isoformat() + "Z",
                        "selections": _serialize_current_selections(),
                    }
                    sessions = st.session_state.advising_sessions or []
                    sessions.append(snapshot)
                    _save_sessions_to_drive(sessions)
                    st.session_state.advising_sessions = sessions
                    st.success("✅ Advising session saved.")
                except Exception as e:
                    st.error(f"❌ Failed to save advising session: {e}")

    # Retrieval UI
    with load_col:
        sessions = st.session_state.advising_sessions or []
        if not sessions:
            st.info("No saved advising sessions found.")
            return

        # Build readable labels
        def _label(s: Dict[str, Any]) -> str:
            return f"{s.get('session_date','')} — {s.get('semester','')} {s.get('year','')} — {s.get('advisor','')}"

        labels = [_label(s) for s in sessions]
        idx = st.selectbox("Retrieve a previous session", options=list(range(len(labels))), format_func=lambda i: labels[i], key="adv_hist_select", index=len(labels)-1)
        if st.button("↩️ Load Selected Session", use_container_width=True):
            try:
                chosen = sessions[idx]
                _restore_selections(chosen.get("selections", {}))
                st.success("✅ Advising session loaded. The dashboard will refresh.")
                st.rerun()
            except Exception as e:
                st.error(f"❌ Failed to load advising session: {e}")
