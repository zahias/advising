# advising_history.py
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional, Union
from datetime import datetime
import pandas as pd
import streamlit as st
from uuid import uuid4

# Import eligibility functions from standalone module
from eligibility_utils import check_course_completed

# Import logging
from utils import log_info, log_error

# Lazy import
_drive_module = None

def _get_drive_module():
    global _drive_module
    if _drive_module is None:
        import google_drive as gd
        _drive_module = gd
    return _drive_module

def _now_iso() -> str:
    return datetime.now().isoformat()

# ---------- Database Logic (Consolidated Storage) ----------

class AdvisingDatabase:
    """
    Manages a single JSON file per Major+Period containing all advising data.
    File format: advising_data_{major}_{period_id}.json
    """
    
    @staticmethod
    def _get_filename(major: str, period_id: str) -> str:
        # Sanitize
        safe_major = "".join(c for c in major if c.isalnum() or c in ('-', '_'))
        safe_period = "".join(c for c in period_id if c.isalnum() or c in ('-', '_'))
        return f"advising_data_{safe_major}_{safe_period}.json"

    @staticmethod
    def load(major: str, period_id: str) -> Dict[str, Any]:
        """
        Load the database for the given major and period.
        Returns a dict of student_id -> session_data.
        """
        if not major or not period_id:
            return {}

        log_info(f"Loading DB for {major} - {period_id}")

        try:
            gd = _get_drive_module()
            service = gd.initialize_drive_service()
            
            # Get major folder
            root_folder_id = ""
            try:
                if "google" in st.secrets:
                    root_folder_id = st.secrets["google"].get("folder_id", "")
            except:
                pass
            import os
            if not root_folder_id:
                root_folder_id = os.getenv("GOOGLE_FOLDER_ID", "")

            if not root_folder_id:
                return {} # effectively local mode

            major_folder_id = gd.get_major_folder_id(service, major, root_folder_id)
            if not major_folder_id:
                return {}

            filename = AdvisingDatabase._get_filename(major, period_id)
            file_id = gd.find_file_in_drive(service, filename, major_folder_id)
            
            if file_id:
                content = gd.download_file_from_drive(service, file_id)
                data = json.loads(content.decode("utf-8"))
                return data.get("sessions", {})
            else:
                return {} # No DB exists yet
        except Exception as e:
            log_error(f"Failed to load DB {major}/{period_id}", e)
            return {}

    @staticmethod
    def save(major: str, period_id: str, sessions: Dict[str, Any]):
        """
        Save the entire sessions dict to Drive.
        """
        if not major or not period_id:
            return

        try:
            gd = _get_drive_module()
            service = gd.initialize_drive_service()
            
            # Get major folder
            root_folder_id = ""
            try:
                if "google" in st.secrets:
                    root_folder_id = st.secrets["google"].get("folder_id", "")
            except:
                pass
            import os
            if not root_folder_id:
                root_folder_id = os.getenv("GOOGLE_FOLDER_ID", "")
            
            if not root_folder_id:
                return

            major_folder_id = gd.get_major_folder_id(service, major, root_folder_id)
            
            payload = {
                "major": major,
                "period_id": period_id,
                "last_updated": _now_iso(),
                "sessions": sessions
            }
            
            filename = AdvisingDatabase._get_filename(major, period_id)
            content = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
            
            gd.sync_file_with_drive(service, content, filename, "application/json", major_folder_id)
            log_info(f"Saved DB {filename}")
        except Exception as e:
            log_error(f"Failed to save DB {major}/{period_id}", e)

# ---------- Public API (Compatible with existing calls) ----------

def load_all_sessions_for_period(period_id: Optional[str] = None) -> int:
    """
    Load the monolithic DB file and populate advising_selections.
    Returns count of loaded students.
    """
    from advising_period import get_current_period
    
    if period_id is None:
        current_period = get_current_period()
        period_id = current_period.get("period_id", "")
        
    major = st.session_state.get("current_major", "")
    if not major or not period_id:
        return 0
        
    # Check if we need to migrate legacy data first
    # We do this by checking if DB exists. If not, check for index.
    # This is a one-time check per session ideally.
    if f"_db_checked_{major}_{period_id}" not in st.session_state:
        _ensure_migration(major, period_id)
        st.session_state[f"_db_checked_{major}_{period_id}"] = True

    # Load from DB
    sessions = AdvisingDatabase.load(major, period_id)
    
    if "advising_selections" not in st.session_state:
        st.session_state.advising_selections = {}
        
    count = 0
    # Merge into session state
    for sid, data in sessions.items():
        # normalize ID
        try:
            norm_sid = int(sid)
        except:
            norm_sid = sid
            
        st.session_state.advising_selections[norm_sid] = data
        
        # Restore bypasses if present
        if "bypasses" in data:
            bypasses_key = f"bypasses_{major}"
            if bypasses_key not in st.session_state:
                st.session_state[bypasses_key] = {}
            st.session_state[bypasses_key][norm_sid] = data["bypasses"]
            
        count += 1
        
    return count

def save_session_for_student(student_id: Union[int, str]) -> Optional[str]:
    """
    Save current student selection to the monolithic DB.
    """
    from advising_period import get_current_period
    
    current_period = get_current_period()
    period_id = current_period.get("period_id", "")
    major = st.session_state.get("current_major", "")
    
    if not major or not period_id:
        return None
        
    # Get current data from session state
    try:
        norm_sid = int(student_id)
    except:
        norm_sid = str(student_id)
        
    sel = st.session_state.advising_selections.get(norm_sid, {})
    if not sel:
        return None

    # Get bypasses
    bypasses_key = f"bypasses_{major}"
    all_bypasses = st.session_state.get(bypasses_key, {})
    student_bypasses = all_bypasses.get(norm_sid) or all_bypasses.get(str(norm_sid)) or {}

    # Construct clean session object
    session_data = {
        "advised": sel.get("advised", []),
        "optional": sel.get("optional", []),
        "repeat": sel.get("repeat", []),
        "note": sel.get("note", ""),
        "bypasses": student_bypasses,
        "last_updated": _now_iso(),
        "advisor": current_period.get("advisor_name", "")
    }

    # We need to save the ENTIRE DB for this period
    # st.session_state.advising_selections IS the current state of the DB.
    
    full_db = {}
    for sid, data in st.session_state.advising_selections.items():
        # clean up specific keys to save
        full_db[str(sid)] = {
            "advised": data.get("advised", []),
            "optional": data.get("optional", []),
            "repeat": data.get("repeat", []),
            "note": data.get("note", ""),
            "bypasses": st.session_state.get(bypasses_key, {}).get(sid, {}),
            "last_updated": data.get("last_updated", _now_iso()),
            "advisor": data.get("advisor", current_period.get("advisor_name", ""))
        }
        
    # Update current student explicitly
    full_db[str(norm_sid)] = session_data
    
    # Save to Drive
    AdvisingDatabase.save(major, period_id, full_db)
    
    return "saved"

def autosave_current_student_session():
    sid = st.session_state.get("current_student_id")
    if sid:
        save_session_for_student(sid)

def _load_session_and_apply(student_id: Union[int, str]) -> bool:
    # No-op since we load everything at start now. 
    # But for compatibility, just return True if data exists.
    try:
        norm_sid = int(student_id)
    except:
        norm_sid = str(student_id)
    return norm_sid in st.session_state.get("advising_selections", {})


# ---------- Migration Helpers ----------

def _ensure_migration(major: str, period_id: str):
    """
    Check if DB exists. If not, and we have legacy files, migrate them.
    """
    existing_db = AdvisingDatabase.load(major, period_id)
    if existing_db:
        return # DB exists, we are good.

    # No DB. Check for legacy index.
    log_info("Checking for legacy data to migrate...")
    
    # We need to look for advising_index.json (legacy)
    gd = _get_drive_module()
    service = gd.initialize_drive_service()
    
    # Get major folder
    root_folder_id = ""
    try:
        if "google" in st.secrets:
            root_folder_id = st.secrets["google"].get("folder_id", "")
    except:
        pass
    import os
    if not root_folder_id:
        root_folder_id = os.getenv("GOOGLE_FOLDER_ID", "")

    if not root_folder_id:
        return

    major_folder_id = gd.get_major_folder_id(service, major, root_folder_id)
    
    # Using specific legacy filename for index
    index_name = "advising_index.json"
    
    # Try finding in sessions subfolder first
    sessions_folder_id = ""
    try:
        q = f"name = 'sessions' and '{major_folder_id}' in parents and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
        res = service.files().list(q=q, spaces='drive', fields='files(id, name)').execute()
        files = res.get('files', [])
        if files:
            sessions_folder_id = files[0].get('id')
    except:
        pass

    search_folder_id = sessions_folder_id if sessions_folder_id else major_folder_id
    
    idx_id = gd.find_file_in_drive(service, index_name, search_folder_id)
    if not idx_id:
        return # No legacy data
        
    # Download index
    content = gd.download_file_from_drive(service, idx_id)
    index = json.loads(content.decode("utf-8"))
    
    # Filter for current period
    period_sessions = [r for r in index if r.get("period_id", "") == period_id]
    
    if not period_sessions:
        return
        
    log_info(f"Migrating {len(period_sessions)} legacy sessions to consolidated DB...")
    
    new_db = {}
    
    # Download each session payload
    for item in period_sessions:
        sid = item.get("id") # session file id (part of filename)
        student_id = str(item.get("student_id"))
        
        filename = f"advising_session_{sid}.json"
        
        # Try download
        fid = gd.find_file_in_drive(service, filename, search_folder_id)
        if fid:
            s_content = gd.download_file_from_drive(service, fid)
            s_data = json.loads(s_content.decode("utf-8"))
            
            snapshot = s_data.get("snapshot", {})
            students = snapshot.get("students", [])
            if students:
                stu = students[0]
                new_db[student_id] = {
                    "advised": stu.get("advised", []),
                    "optional": stu.get("optional", []),
                    "repeat": stu.get("repeat", []),
                    "note": stu.get("note", ""),
                    "bypasses": stu.get("bypasses", {}),
                    "last_updated": item.get("created_at", _now_iso()),
                    "advisor": item.get("advisor_name", "")
                }
    
    # Save the new DB
    AdvisingDatabase.save(major, period_id, new_db)
    
    # Rename legacy index?
    try:
        service.files().update(
            fileId=idx_id,
            body={"name": f"legacy_{index_name}"}
        ).execute()
        log_info("Renamed legacy index to prevent re-migration.")
    except:
        pass
        
    log_info("Migration complete.")
