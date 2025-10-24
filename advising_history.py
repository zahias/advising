# advising_history.py
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional, Union
from uuid import uuid4
from datetime import datetime

import pandas as pd
import streamlit as st

from google_drive import (
    initialize_drive_service,
    find_file_in_drive,
    download_file_from_drive,
    sync_file_with_drive,
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

try:
    from zoneinfo import ZoneInfo
    _LOCAL_TZ = ZoneInfo("Asia/Beirut")
except Exception:
    _LOCAL_TZ = None

__all__ = ["advising_history_panel", "autosave_current_student_session", "save_session_for_student"]


# ---------- internal helpers ----------

def _now_beirut() -> datetime:
    return datetime.now(_LOCAL_TZ) if _LOCAL_TZ else datetime.now()

def _index_name() -> str:
    major = st.session_state.get("current_major", "DEFAULT")
    return f"advising_index_{major}.json"

def _session_filename(session_id: str) -> str:
    major = st.session_state.get("current_major", "DEFAULT")
    return f"advising_session_{major}_{session_id}.json"


# ---------- index I/O ----------

def _get_folder_id() -> str:
    """Get folder ID from secrets or env."""
    import os
    try:
        return st.secrets.get("google", {}).get("folder_id", "") or os.getenv("GOOGLE_FOLDER_ID", "")
    except Exception:
        return os.getenv("GOOGLE_FOLDER_ID", "")

def _load_index() -> List[Dict[str, Any]]:
    try:
        service = initialize_drive_service()
        folder_id = _get_folder_id()
        if not folder_id:
            return []
        fid = find_file_in_drive(service, _index_name(), folder_id)
        if not fid:
            return []
        payload = download_file_from_drive(service, fid)
        idx = json.loads(payload.decode("utf-8"))
        return idx if isinstance(idx, list) else []
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
        folder_id = _get_folder_id()
        if not folder_id:
            return
        data = json.dumps(index_items, ensure_ascii=False, indent=2).encode("utf-8")
        sync_file_with_drive(service, data, _index_name(), "application/json", folder_id)
        log_info(f"Index saved to Drive: {_index_name()}")
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
        folder_id = _get_folder_id()
        if not folder_id:
            log_info(f"Session saved locally only (no Drive folder configured): {session_id}")
            return
        data = json.dumps({"meta": meta, "snapshot": snapshot}, ensure_ascii=False, indent=2).encode("utf-8")
        sync_file_with_drive(service, data, _session_filename(session_id), "application/json", folder_id)
        log_info(f"Session payload synced to Drive: {_session_filename(session_id)}")
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
        folder_id = _get_folder_id()
        if not folder_id:
            return None
        fid = find_file_in_drive(service, _session_filename(session_id), folder_id)
        if not fid:
            return None
        data = download_file_from_drive(service, fid)
        payload = json.loads(data.decode("utf-8"))
        # Cache it locally for next time
        _save_session_payload_local(session_id, payload.get("snapshot", {}), payload.get("meta", {}))
        return payload
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

def _snapshot_student_courses(student_row: pd.Series, advised: List[str], optional: List[str]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    cdf = st.session_state.courses_df
    for _, info in cdf.iterrows():
        code = str(info["Course Code"])
        offered = "Yes" if is_course_offered(cdf, code) else "No"
        status, justification = check_eligibility(student_row, code, advised, cdf)

        if check_course_completed(student_row, code):
            action = "Completed"; status = "Completed"
        elif check_course_registered(student_row, code):
            action = "Registered"
        elif code in advised:
            action = "Advised"
        elif code in optional:
            action = "Optional"
        elif status == "Not Eligible":
            action = "Not Eligible"
        else:
            action = "Eligible (not chosen)"

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
            "note": note,
            "courses": _snapshot_student_courses(srow, advised, optional),
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
        meta = {
            "id": sid,
            "title": title,
            "created_at": now.isoformat(),
            "major": st.session_state.get("current_major", ""),
            "student_id": students[0].get("ID", student_id),
            "student_name": student_name,
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


# ---------- panel UI ----------

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

    labels = [r.get("title","(untitled)") for r in index]
    choice_idx = st.selectbox("Saved sessions", options=list(range(len(index))), format_func=lambda i: labels[i], key="sess_choice")
    chosen = index[choice_idx]
    sid = str(chosen.get("id",""))

    b1, b2 = st.columns([1,1])
    with b1:
        if st.button("📂 Open (view-only)", use_container_width=True, key="sess_open"):
            payload = _load_session_payload_by_id(sid)
            if payload:
                st.session_state["advising_loaded_payload"] = payload
                st.success("Loaded archived session below (read-only).")
    with b2:
        confirm = st.checkbox("Confirm delete (index only)", key="sess_del_confirm", value=False)
        if st.button("🗑️ Delete from index", use_container_width=True, disabled=not confirm, key="sess_del"):
            st.session_state.advising_index = [r for r in st.session_state.advising_index if str(r.get("id","")) != sid]
            _save_index(st.session_state.advising_index)
            st.session_state.pop("advising_loaded_payload", None)
            st.success("Deleted from index.")
            st.rerun()

    payload = st.session_state.get("advising_loaded_payload")
    if payload:
        snapshot = payload.get("snapshot", {})
        students = snapshot.get("students", [])
        if students:
            s = students[0]
            st.markdown("### Archived Session (read-only)")
            with st.container(border=True):
                st.write(
                    f"**Name:** {s.get('NAME','')}  |  **ID:** {s.get('ID','')}  |  "
                    f"**Credits:** {int((s.get('# of Credits Completed',0) or 0) + (s.get('# Registered',0) or 0))}  |  "
                    f"**Standing:** {s.get('Standing','')}"
                )
                if s.get("note"):
                    st.caption("Advisor Note:")
                    st.write(s["note"])
            df = pd.DataFrame(s.get("courses", []))
            if not df.empty:
                preferred = ["Course Code","Type","Requisites","Offered","Eligibility Status","Justification","Action"]
                cols = [c for c in preferred if c in df.columns] + [c for c in df.columns if c not in preferred]
                st.dataframe(style_df(df[cols]), use_container_width=True)
            else:
                st.info("No course rows stored in this snapshot.")
