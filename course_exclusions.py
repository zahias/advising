# course_exclusions.py
# Per-student course exclusions (hidden courses), persisted per MAJOR to Google Drive.

from __future__ import annotations
import json
from typing import Dict, List

import streamlit as st
from google_drive import (
    initialize_drive_service,
    find_file_in_drive,
    download_file_from_drive,
    sync_file_with_drive,
)
from utils import log_error, log_info


def _filename() -> str:
    major = st.session_state.get("current_major", "DEFAULT")
    return f"course_exclusions_{major}.json"


def _load_from_drive() -> Dict[str, List[str]]:
    """Fetch exclusions map from Drive; returns {} if not found / any issue."""
    try:
        service = initialize_drive_service()
        folder_id = st.secrets["google"]["folder_id"]
        file_id = find_file_in_drive(service, _filename(), folder_id)
        if not file_id:
            return {}
        payload = download_file_from_drive(service, file_id)
        try:
            data = json.loads(payload.decode("utf-8"))
            # Normalize to {str(student_id): [codes...]}
            out: Dict[str, List[str]] = {}
            if isinstance(data, dict):
                for k, v in data.items():
                    key = str(k)
                    if isinstance(v, list):
                        out[key] = [str(c) for c in v]
            return out
        except Exception:
            return {}
    except Exception as e:
        log_error("Failed to load course exclusions from Drive", e)
        return {}


def _save_to_drive(ex_map: Dict[str, List[str]]) -> None:
    """Write exclusions map to Drive (overwrites the file)."""
    try:
        service = initialize_drive_service()
        folder_id = st.secrets["google"]["folder_id"]
        data_bytes = json.dumps(ex_map, ensure_ascii=False, indent=2).encode("utf-8")
        sync_file_with_drive(
            service=service,
            file_content=data_bytes,
            drive_file_name=_filename(),
            mime_type="application/json",
            parent_folder_id=folder_id,
        )
        log_info(f"Course exclusions saved to Drive ({_filename()}).")
    except Exception as e:
        log_error("Failed to save course exclusions to Drive", e)
        raise


def ensure_loaded() -> None:
    """
    Ensure exclusions live in session (and per-major bucket if present).
    Called at the start of any page that needs exclusions.
    """
    major = st.session_state.get("current_major", "DEFAULT")
    # If majors bucket exists, keep per-major storage there
    if "majors" in st.session_state:
        bucket = st.session_state.majors.setdefault(major, {})
        if "course_exclusions" not in bucket:
            bucket["course_exclusions"] = _load_from_drive()
        st.session_state.course_exclusions = bucket["course_exclusions"]
    else:
        if "course_exclusions" not in st.session_state:
            st.session_state.course_exclusions = _load_from_drive()


def _persist_to_bucket():
    """Keep majors bucket in sync with session copy."""
    major = st.session_state.get("current_major", "DEFAULT")
    if "majors" in st.session_state:
        st.session_state.majors.setdefault(major, {})
        st.session_state.majors[major]["course_exclusions"] = st.session_state.get("course_exclusions", {})


def get_for_student(student_id: int | str) -> List[str]:
    """Return list of hidden course codes for a student (strings)."""
    ensure_loaded()
    sid = str(student_id)
    ex_map: Dict[str, List[str]] = st.session_state.get("course_exclusions", {})
    return list(ex_map.get(sid, []))


def set_for_student(student_id: int | str, course_codes: List[str]) -> None:
    """
    Replace the hidden list for a student and sync to Drive.
    Accepts list of strings (course codes).
    """
    ensure_loaded()
    sid = str(student_id)
    ex_map: Dict[str, List[str]] = st.session_state.get("course_exclusions", {})
    ex_map[sid] = [str(c) for c in course_codes]
    st.session_state.course_exclusions = ex_map
    _persist_to_bucket()
    _save_to_drive(ex_map)
