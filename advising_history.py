# advising_history.py
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional, Union
from uuid import uuid4
from datetime import datetime
import numpy as np

import pandas as pd
import streamlit as st

from google_drive import (
    initialize_drive_service,
    find_file_in_drive,
    download_file_from_drive,
    sync_file_with_drive,
    get_major_folder_id,
    get_or_create_folder,
)
from utils import (
    log_info,
    log_error,
    check_course_completed,
    check_course_registered,
    is_course_offered,
    check_eligibility,
    build_requisites_str,
    get_student_standing,
    style_df,
)
from advising_period import get_current_period

try:
    from zoneinfo import ZoneInfo
    _LOCAL_TZ = ZoneInfo("Asia/Beirut")
except Exception:
    _LOCAL_TZ = None

__all__ = ["advising_history_panel", "autosave_current_student_session", "save_session_for_student", "_find_latest_session_for_student", "_load_session_and_apply"]


# ---------- internal helpers ----------

def _convert_to_json_serializable(obj: Any) -> Any:
    """Recursively convert numpy types to native Python types for JSON serialization."""
    if isinstance(obj, dict):
        return {k: _convert_to_json_serializable(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_convert_to_json_serializable(item) for item in obj]
    elif isinstance(obj, (np.integer, np.int64, np.int32)):
        return int(obj)
    elif isinstance(obj, (np.floating, np.float64, np.float32)):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif pd.isna(obj):
        return None
    else:
        return obj

def _now_beirut() -> datetime:
    return datetime.now(_LOCAL_TZ) if _LOCAL_TZ else datetime.now()

def _index_name() -> str:
    return "advising_index.json"

def _session_filename(session_id: str) -> str:
    return f"advising_session_{session_id}.json"


# ---------- index I/O ----------

def _get_major_folder_id() -> str:
    """Get major-specific folder ID. Returns major-specific folder inside root folder."""
    import os
    try:
        service = initialize_drive_service()
        major = st.session_state.get("current_major", "DEFAULT")
        
        # Get root folder ID
        root_folder_id = ""
        try:
            if "google" in st.secrets:
                root_folder_id = st.secrets["google"].get("folder_id", "")
        except:
            pass
        
        if not root_folder_id:
            root_folder_id = os.getenv("GOOGLE_FOLDER_ID", "")
        
        if not root_folder_id:
            return ""
        
        # Get or create major-specific folder
        return get_major_folder_id(service, major, root_folder_id)
    except Exception:
        return ""

def _get_sessions_folder_id() -> str:
    """Get sessions subfolder ID within the major folder. Creates it if it doesn't exist."""
    try:
        service = initialize_drive_service()
        major_folder_id = _get_major_folder_id()
        if not major_folder_id:
            return ""
        
        # Get or create 'sessions' subfolder within major folder
        sessions_folder_id = get_or_create_folder(service, "sessions", major_folder_id)
        return sessions_folder_id
    except Exception as e:
        log_error(f"Failed to get/create sessions folder", e)
        return ""

def _load_index() -> List[Dict[str, Any]]:
    try:
        service = initialize_drive_service()
        
        # Try sessions subfolder first
        folder_id = _get_sessions_folder_id()
        if folder_id:
            fid = find_file_in_drive(service, _index_name(), folder_id)
            if fid:
                payload = download_file_from_drive(service, fid)
                idx = json.loads(payload.decode("utf-8"))
                return idx if isinstance(idx, list) else []
        
        # Fall back to major folder root (backward compatibility for legacy sessions)
        folder_id = _get_major_folder_id()
        if folder_id:
            fid = find_file_in_drive(service, _index_name(), folder_id)
            if fid:
                payload = download_file_from_drive(service, fid)
                idx = json.loads(payload.decode("utf-8"))
                log_info("Loaded legacy advising index from major folder root (consider migrating to sessions/)")
                return idx if isinstance(idx, list) else []
        
        return []
    except Exception as e:
        log_error("Failed to load advising index", e)
        return []

def _save_index_local(index_items: List[Dict[str, Any]]) -> None:
    """Save index to session state immediately (local-first)."""
    st.session_state.advising_index = index_items

def _save_index(index_items: List[Dict[str, Any]]) -> None:
    """Save index to Drive asynchronously (background)."""
    # Save locally first
    _save_index_local(index_items)
    
    # Background save to Drive (best effort)
    try:
        service = initialize_drive_service()
        folder_id = _get_sessions_folder_id()
        if not folder_id:
            return
        # Convert numpy types to native Python types before JSON serialization
        serializable_items = _convert_to_json_serializable(index_items)
        data = json.dumps(serializable_items, ensure_ascii=False, indent=2).encode("utf-8")
        sync_file_with_drive(service, data, _index_name(), "application/json", folder_id)
        log_info(f"Index saved to Drive/sessions: {_index_name()}")
    except Exception as e:
        log_error("Failed to save advising index to Drive (local copy preserved)", e)


# ---------- session payload I/O ----------

def _save_session_payload_local(session_id: str, snapshot: Dict[str, Any], meta: Dict[str, Any]) -> None:
    """Save session payload to session state immediately (local-first)."""
    if "advising_sessions_cache" not in st.session_state:
        st.session_state.advising_sessions_cache = {}
    st.session_state.advising_sessions_cache[session_id] = {"meta": meta, "snapshot": snapshot}

def _save_session_payload(session_id: str, snapshot: Dict[str, Any], meta: Dict[str, Any]) -> None:
    """Save session payload with local-first approach."""
    # Save locally first (instant)
    _save_session_payload_local(session_id, snapshot, meta)
    
    # Background save to Drive (best effort, non-blocking)
    try:
        service = initialize_drive_service()
        folder_id = _get_sessions_folder_id()
        if not folder_id:
            log_info(f"Session saved locally only (no Drive folder configured): {session_id}")
            return
        # Convert numpy types to native Python types before JSON serialization
        payload = _convert_to_json_serializable({"meta": meta, "snapshot": snapshot})
        data = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
        sync_file_with_drive(service, data, _session_filename(session_id), "application/json", folder_id)
        log_info(f"Session payload synced to Drive/sessions: {_session_filename(session_id)}")
    except Exception as e:
        log_error(f"Failed to sync session to Drive (local copy preserved): {session_id}", e)

def _load_session_payload_by_id(session_id: str) -> Optional[Dict[str, Any]]:
    # Try local cache first
    if "advising_sessions_cache" in st.session_state:
        cached = st.session_state.advising_sessions_cache.get(session_id)
        if cached:
            return cached
    
    # Fall back to Drive
    try:
        service = initialize_drive_service()
        
        # Try sessions subfolder first
        folder_id = _get_sessions_folder_id()
        if folder_id:
            fid = find_file_in_drive(service, _session_filename(session_id), folder_id)
            if fid:
                data = download_file_from_drive(service, fid)
                payload = json.loads(data.decode("utf-8"))
                # Cache it locally for next time
                _save_session_payload_local(session_id, payload.get("snapshot", {}), payload.get("meta", {}))
                return payload
        
        # Fall back to major folder root (backward compatibility for legacy sessions)
        folder_id = _get_major_folder_id()
        if folder_id:
            fid = find_file_in_drive(service, _session_filename(session_id), folder_id)
            if fid:
                data = download_file_from_drive(service, fid)
                payload = json.loads(data.decode("utf-8"))
                log_info(f"Loaded legacy session {session_id} from major folder root")
                # Cache it locally for next time
                _save_session_payload_local(session_id, payload.get("snapshot", {}), payload.get("meta", {}))
                return payload
        
        return None
    except Exception as e:
        log_error("Failed to load session payload from Drive", e)
        return None


# ---------- snapshot builders ----------

def _snapshot_courses_table() -> List[Dict[str, Any]]:
    df = st.session_state.get("courses_df", pd.DataFrame())
    if df.empty:
        return []
    cols = [
        "Course Code", "Type", "Credits", "Offered",
        "Prerequisite", "Concurrent", "Corequisite",
        "Title", "Requisites",
    ]
    cols = [c for c in cols if c in df.columns]
    return df[cols].fillna("").to_dict(orient="records")

def _find_student_row(student_id: Union[int, str]) -> Optional[pd.Series]:
    pdf = st.session_state.get("progress_df", pd.DataFrame())
    if pdf.empty:
        return None
    row = pdf.loc[pdf["ID"] == student_id]
    if not row.empty:
        return row.iloc[0]
    try:
        row = pdf.loc[pdf["ID"] == int(student_id)]
        if not row.empty:
            return row.iloc[0]
    except Exception:
        pass
    try:
        row = pdf.loc[pdf["ID"].astype(str) == str(student_id)]
        if not row.empty:
            return row.iloc[0]
    except Exception:
        pass
    return None

def _snapshot_student_courses(student_row: pd.Series, advised: List[str], optional: List[str], repeat: List[str]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    cdf = st.session_state.courses_df
    for _, info in cdf.iterrows():
        code = str(info["Course Code"])
        offered = "Yes" if is_course_offered(cdf, code) else "No"
        status, justification = check_eligibility(student_row, code, advised, cdf)

        # Action column should ONLY show advisor selections
        if code in repeat:
            action = "Advised-Repeat"
        elif code in advised:
            action = "Advised"
        elif code in optional:
            action = "Optional"
        else:
            action = ""  # Empty for non-selected courses
        
        # Update status for completed/registered courses (for Eligibility Status column)
        if check_course_completed(student_row, code):
            status = "Completed"
        elif check_course_registered(student_row, code):
            status = "Registered"

        rows.append({
            "Course Code": code,
            "Type": info.get("Type", ""),
            "Title": info.get("Title", ""),
            "Requisites": build_requisites_str(info),
            "Offered": offered,
            "Eligibility Status": status,
            "Justification": justification,
            "Action": action,
        })
    return rows

def _build_single_student_snapshot(student_id: Union[int, str]) -> Dict[str, Any]:
    srow = _find_student_row(student_id)
    if srow is None:
        return {"courses_table": _snapshot_courses_table(), "students": []}

    selections = st.session_state.get("advising_selections", {}) or {}
    sel = (
        selections.get(student_id)
        or selections.get(str(student_id))
        or (selections.get(int(student_id)) if str(student_id).isdigit() else None)
        or {}
    )

    advised = [str(x) for x in sel.get("advised", [])]
    optional = [str(x) for x in sel.get("optional", [])]
    repeat = [str(x) for x in sel.get("repeat", [])]
    note = str(sel.get("note", "") or "")

    credits_completed = float(srow.get("# of Credits Completed", 0) or 0)
    credits_registered = float(srow.get("# Registered", 0) or 0)
    standing = get_student_standing(credits_completed + credits_registered)

    return {
        "courses_table": _snapshot_courses_table(),
        "students": [{
            "ID": srow["ID"],
            "NAME": str(srow.get("NAME")),
            "# of Credits Completed": credits_completed,
            "# Registered": credits_registered,
            "Standing": standing,
            "advised": advised,
            "optional": optional,
            "repeat": repeat,
            "note": note,
            "courses": _snapshot_student_courses(srow, advised, optional, repeat),
        }],
    }


# ---------- public save APIs ----------

def save_session_for_student(student_id: Union[int, str]) -> Optional[str]:
    """
    Build a snapshot for *this* student and persist it.
    Does NOT depend on st.session_state['current_student_id'].
    """
    try:
        snapshot = _build_single_student_snapshot(student_id)
        students = snapshot.get("students", [])
        if not students:
            log_error("save_session_for_student: no student row", Exception("student_not_found"))
            return None

        student_name = str(students[0].get("NAME", ""))
        now = _now_beirut()
        sid = str(uuid4())
        title = f"{now.strftime('%Y-%m-%d %H:%M')} — {student_name} ({student_id})"
        
        # Get current period information
        current_period = get_current_period()
        
        meta = {
            "id": sid,
            "title": title,
            "created_at": now.isoformat(),
            "major": st.session_state.get("current_major", ""),
            "student_id": students[0].get("ID", student_id),
            "student_name": student_name,
            "period_id": current_period.get("period_id", ""),
            "semester": current_period.get("semester", ""),
            "year": current_period.get("year", ""),
            "advisor_name": current_period.get("advisor_name", ""),
        }

        # best-effort payload save to Drive
        _save_session_payload(sid, snapshot, meta)

        # local index update so UI shows it immediately
        if "advising_index" not in st.session_state:
            st.session_state.advising_index = _load_index()
        st.session_state.advising_index.append({
            "id": sid,
            "title": title,
            "created_at": meta["created_at"],
            "student_id": meta["student_id"],
            "student_name": meta["student_name"],
            "major": meta["major"],
            "session_file": _session_filename(sid),
            "period_id": meta["period_id"],
            "semester": meta["semester"],
            "year": meta["year"],
            "advisor_name": meta["advisor_name"],
        })
        _save_index(st.session_state.advising_index)

        log_info(f"Auto-saved advising session for {student_id}: {title}")
        return sid
    except Exception as e:
        log_error("save_session_for_student failed", e)
        return None


def autosave_current_student_session() -> Optional[str]:
    """Legacy hook—kept for compatibility. Uses explicit saver if possible."""
    sid = st.session_state.get("current_student_id", None)
    if sid is None:
        log_error("autosave_current_student_session: no current_student_id", Exception("no_current_student"))
        return None
    return save_session_for_student(sid)


def _find_latest_session_for_student(student_id: Union[int, str], period_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Find the most recent advising session for a given student.
    If period_id is provided, only returns sessions from that period.
    If period_id is None, uses current period.
    Returns the session metadata if found, None otherwise.
    """
    if "advising_index" not in st.session_state:
        st.session_state.advising_index = _load_index()
    
    index = st.session_state.advising_index or []
    
    # Get period filter
    if period_id is None:
        current_period = get_current_period()
        period_id = current_period.get("period_id", "")
    
    # Filter sessions for this student in the specified period
    student_sessions = [
        r for r in index 
        if str(r.get("student_id", "")) == str(student_id)
        and r.get("period_id", "") == period_id
    ]
    
    if not student_sessions:
        return None
    
    # Sort by created_at (most recent first)
    student_sessions.sort(key=lambda r: r.get("created_at", ""), reverse=True)
    
    return student_sessions[0]


def _load_session_and_apply(student_id: Union[int, str]) -> bool:
    """
    Load the most recent advising session for a student and apply it to the current state.
    Returns True if a session was loaded, False otherwise.
    """
    latest_session = _find_latest_session_for_student(student_id)
    
    if not latest_session:
        return False
    
    session_id = latest_session.get("id")
    if not session_id:
        return False
    
    # Load the session payload
    payload = _load_session_payload_by_id(session_id)
    if not payload:
        return False
    
    snapshot = payload.get("snapshot", {})
    students = snapshot.get("students", [])
    
    if not students:
        return False
    
    student_data = students[0]
    
    # Apply to advising_selections
    if "advising_selections" not in st.session_state:
        st.session_state.advising_selections = {}
    
    st.session_state.advising_selections[student_id] = {
        "advised": student_data.get("advised", []),
        "optional": student_data.get("optional", []),
        "repeat": student_data.get("repeat", []),  # Support new repeat field
        "note": student_data.get("note", ""),
    }
    
    log_info(f"Auto-loaded most recent session for student {student_id}")
    return True


# ---------- panel UI ----------

from visual_theme import render_glass_card, render_status_badge

def advising_history_panel():
    st.markdown("---")
    st.subheader(f"Advising Sessions — {st.session_state.get('current_major','')}")
    if "advising_index" not in st.session_state:
        st.session_state.advising_index = _load_index()
    index = list(st.session_state.advising_index or [])

    current_sid = st.session_state.get("current_student_id", None)
    if current_sid is not None:
        index = [r for r in index if str(r.get("student_id","")) == str(current_sid)]

    c1, c2 = st.columns([2,1])
    with c1:
        q = st.text_input("Search", key="sess_search", placeholder="Title / student name / ID")
    with c2:
        sort_key = st.selectbox("Sort", ["Date desc", "Date asc", "Title"], index=0, key="sess_sort")

    if q:
        ql = q.lower()
        def _hit(r: Dict[str, Any]) -> bool:
            return (
                ql in str(r.get("title","")).lower()
                or ql in str(r.get("student_name","")).lower()
                or ql in str(r.get("student_id","")).lower()
            )
        index = [r for r in index if _hit(r)]

    if sort_key == "Date asc":
        index.sort(key=lambda r: r.get("created_at",""))
    elif sort_key == "Title":
        index.sort(key=lambda r: r.get("title",""))
    else:
        index.sort(key=lambda r: r.get("created_at",""), reverse=True)

    if not index:
        st.info("No sessions found for this student." if current_sid is not None else "No sessions found.")
        return

    # Layout: List of cards on the left (scrollable area effectively), Details on the right or below.
    # For simplicity in Streamlit, we'll list them. if many, maybe limit?
    
    st.caption(f"Showing {len(index)} sessions")
    
    # Session List Container
    with st.container():
        for i, session in enumerate(index):
            sid = str(session.get("id",""))
            date_str = session.get("created_at", "").replace("T", " ")[:16]
            student_name = session.get("student_name", "Unknown")
            advisor = session.get("advisor_name", "Unknown")
            period = f"{session.get('semester','')} {session.get('year','')}"
            
            # Card Content
            with st.container():
                col_info, col_action = st.columns([3, 1])
                with col_info:
                    st.markdown(f"**{date_str}** — {student_name}")
                    st.caption(f"Advisor: {advisor} | {period}")
                with col_action:
                    if st.button("View", key=f"view_{sid}"):
                        payload = _load_session_payload_by_id(sid)
                        if payload:
                            st.session_state["advising_loaded_payload"] = payload
                            st.rerun()
                st.markdown("---")


    # Details View (if loaded)
    payload = st.session_state.get("advising_loaded_payload")
    if payload:
        st.markdown("### 📄 Session Details")
        
        snapshot = payload.get("snapshot", {})
        students = snapshot.get("students", [])
        meta = payload.get("meta", {})
        
        # Add delete button for the currently viewed session
        col_del_1, col_del_2 = st.columns([3, 1])
        with col_del_2:
             if st.button("🗑️ Delete Session", key="del_from_view", type="secondary"):
                 current_view_id = meta.get("id")
                 if current_view_id:
                     st.session_state.advising_index = [r for r in st.session_state.advising_index if str(r.get("id","")) != current_view_id]
                     _save_index(st.session_state.advising_index)
                     st.session_state.pop("advising_loaded_payload", None)
                     st.success("Session deleted.")
                     st.rerun()

        if students:
            s = students[0]
            
            render_glass_card(
                title=f"Snapshot: {s.get('NAME','')}",
                subtitle=f"ID: {s.get('ID','')} | {meta.get('created_at','').replace('T',' ')[:16]}",
                content=f"""
                <div style="display: flex; gap: 2rem;">
                    <div><b>Credits:</b> {int((s.get('# of Credits Completed',0) or 0) + (s.get('# Registered',0) or 0))}</div>
                    <div><b>Standing:</b> {s.get('Standing','')}</div>
                </div>
                <div style="margin-top: 1rem; font-style: italic; color: var(--text-muted);">
                    "{s.get("note", "No advisor notes.")}"
                </div>
                """
            )

            df = pd.DataFrame(s.get("courses", []))
            if not df.empty:
                preferred = ["Course Code","Type","Requisites","Offered","Eligibility Status","Justification","Action"]
                cols = [c for c in preferred if c in df.columns] + [c for c in df.columns if c not in preferred]
                st.dataframe(style_df(df[cols]), width='stretch')
            else:
                st.info("No course rows stored in this snapshot.")
        else:
            st.warning("Snapshot data is empty or corrupted.")
