# advising_history.py
# Sessions are created AUTOMATICALLY when the advisor clicks "Save Selections"
# in the eligibility view. This panel only lists, opens (read-only), exports, and deletes.
# - Per-student snapshots only (no legacy "save all", no semester/year, no restore).
# - Title format: "YYYY-MM-DD HH:MM — NAME (ID)" in Asia/Beirut local time.
# - Index + per-session JSON on Drive. If Drive write fails, we still add to
#   in-memory index so the session appears immediately (best-effort).

from __future__ import annotations

import io
import json
from typing import Any, Dict, List, Optional, Tuple
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
    _LOCAL_TZ = None  # fallback to naive local time

__all__ = ["advising_history_panel", "autosave_current_student_session"]


# ----------------- Filenames (per major) -----------------

def _index_name() -> str:
    major = st.session_state.get("current_major", "DEFAULT")
    return f"advising_index_{major}.json"

def _session_filename(session_id: str) -> str:
    major = st.session_state.get("current_major", "DEFAULT")
    return f"advising_session_{major}_{session_id}.json"


# ----------------- Drive I/O -----------------

def _load_index() -> List[Dict[str, Any]]:
    try:
        service = initialize_drive_service()
        folder_id = st.secrets["google"]["folder_id"]
        fid = find_file_in_drive(service, _index_name(), folder_id)
        if not fid:
            return []
        payload = download_file_from_drive(service, fid)
        idx = json.loads(payload.decode("utf-8"))
        return idx if isinstance(idx, list) else []
    except Exception as e:
        log_error("Failed to load advising index", e)
        return []

def _save_index(index_items: List[Dict[str, Any]]) -> None:
    service = initialize_drive_service()
    folder_id = st.secrets["google"]["folder_id"]
    data = json.dumps(index_items, ensure_ascii=False, indent=2).encode("utf-8")
    sync_file_with_drive(service, data, _index_name(), "application/json", folder_id)
    log_info(f"Index saved: {_index_name()}")

def _save_session_payload(session_id: str, snapshot: Dict[str, Any], meta: Dict[str, Any]) -> None:
    service = initialize_drive_service()
    folder_id = st.secrets["google"]["folder_id"]
    payload = {"meta": meta, "snapshot": snapshot}
    data = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
    sync_file_with_drive(service, data, _session_filename(session_id), "application/json", folder_id)
    log_info(f"Session payload saved: {_session_filename(session_id)}")

def _load_session_payload_by_id(session_id: str) -> Optional[Dict[str, Any]]:
    try:
        service = initialize_drive_service()
        folder_id = st.secrets["google"]["folder_id"]
        fid = find_file_in_drive(service, _session_filename(session_id), folder_id)
        if not fid:
            return None
        data = download_file_from_drive(service, fid)
        return json.loads(data.decode("utf-8"))
    except Exception as e:
        log_error("Failed to load session payload", e)
        return None


# ----------------- Snapshot helpers -----------------

def _snapshot_courses_table() -> List[Dict[str, Any]]:
    """
    Store a light copy of the courses table to make old sessions resilient
    to future table/report changes.
    """
    if "courses_df" not in st.session_state or st.session_state.courses_df.empty:
        return []
    cols = [
        "Course Code", "Type", "Credits", "Offered",
        "Prerequisite", "Concurrent", "Corequisite"
    ]
    df = st.session_state.courses_df.copy()
    keep = [c for c in cols if c in df.columns]
    return df[keep].to_dict(orient="records")

def _snapshot_student_courses(student_row: pd.Series, advised: List[str], optional: List[str]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for _, info in st.session_state.courses_df.iterrows():
        code = str(info["Course Code"])
        offered = is_course_offered(st.session_state.courses_df, code)
        status, justification = check_eligibility(
            student_row, code, advised, st.session_state.courses_df
        )

        # Action (we save the **true** state in the snapshot for fidelity)
        if check_course_completed(student_row, code):
            action = "Completed"
            status = "Completed"
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
            "Requisites": build_requisites_str(info),
            "Offered": offered,
            "Eligibility Status": status,
            "Justification": justification,
            "Action": action,
        })
    return rows

def _build_single_student_snapshot(student_id: int) -> Dict[str, Any]:
    if "progress_df" not in st.session_state or st.session_state.progress_df.empty:
        return {"courses_table": [], "students": []}

    srow = st.session_state.progress_df.loc[st.session_state.progress_df["ID"] == int(student_id)]
    if srow.empty:
        return {"courses_table": [], "students": []}
    srow = srow.iloc[0]

    sel = st.session_state.advising_selections.get(int(student_id), {})
    advised = [str(x) for x in sel.get("advised", [])]
    optional = [str(x) for x in sel.get("optional", [])]
    note = str(sel.get("note", "") or "")

    credits_completed = float(srow.get("# of Credits Completed", 0) or 0)
    credits_registered = float(srow.get("# Registered", 0) or 0)
    standing = get_student_standing(credits_completed + credits_registered)

    course_rows = _snapshot_student_courses(srow, advised, optional)

    return {
        "courses_table": _snapshot_courses_table(),
        "students": [{
            "ID": int(student_id),
            "NAME": str(srow.get("NAME")),
            "# of Credits Completed": credits_completed,
            "# Registered": credits_registered,
            "Standing": standing,
            "advised": advised,
            "optional": optional,
            "note": note,  # NOTE is saved here
            "courses": course_rows,
        }],
    }


# ----------------- PUBLIC: Autosave on Save Selections -----------------

def _now_beirut() -> datetime:
    if _LOCAL_TZ:
        return datetime.now(_LOCAL_TZ)
    return datetime.now()

def autosave_current_student_session() -> Optional[str]:
    """
    Saves a per-student advising session with a human title:
      "YYYY-MM-DD HH:MM — NAME (ID)"
    Returns session_id (str) or None on failure.
    """
    try:
        current_sid = st.session_state.get("current_student_id", None)
        if current_sid is None:
            return None

        snapshot = _build_single_student_snapshot(int(current_sid))

        # Student name for title
        student_name = ""
        if "progress_df" in st.session_state and not st.session_state.progress_df.empty:
            try:
                student_name = str(
                    st.session_state.progress_df.loc[
                        st.session_state.progress_df["ID"] == int(current_sid)
                    ]["NAME"].iloc[0]
                )
            except Exception:
                student_name = ""

        now = _now_beirut()
        title = f"{now.strftime('%Y-%m-%d %H:%M')} — {student_name} ({int(current_sid)})"

        sid = str(uuid4())
        meta = {
            "id": sid,
            "title": title,
            "created_at": now.isoformat(),
            "major": st.session_state.get("current_major", ""),
            "student_id": int(current_sid),
            "student_name": student_name,
        }

        # Ensure local index is present
        if "advising_index" not in st.session_state:
            st.session_state.advising_index = _load_index()

        # Try Drive first; if it fails, still show session locally (best-effort)
        drive_ok = True
        try:
            _save_session_payload(sid, snapshot, meta)
        except Exception as e:
            drive_ok = False
            log_error("Drive save (payload) failed, keeping local only", e)

        # Update in-memory index
        index_row = {
            "id": sid,
            "title": title,
            "created_at": meta["created_at"],
            "student_id": meta["student_id"],
            "student_name": meta["student_name"],
            "major": meta["major"],
            "session_file": _session_filename(sid),
        }
        st.session_state.advising_index.append(index_row)

        # Try to persist the index to Drive
        try:
            _save_index(st.session_state.advising_index)
        except Exception as e:
            drive_ok = False
            log_error("Drive save (index) failed, keeping local only", e)

        if not drive_ok:
            st.warning("Saved session locally (Drive error). It will show here but may not be on Drive yet.")
        log_info(f"Auto-saved advising session: {title}")
        return sid

    except Exception as e:
        log_error("Auto-save advising session failed", e)
        return None


# ----------------- Panel UI: Sessions only -----------------

def advising_history_panel():
    st.markdown("---")
    st.subheader(f"Advising Sessions — {st.session_state.get('current_major','')}")

    if "advising_index" not in st.session_state:
        st.session_state.advising_index = _load_index()

    index = st.session_state.advising_index or []

    # Show only current student's sessions by default (if selected)
    current_sid = st.session_state.get("current_student_id", None)
    if current_sid is not None:
        try:
            index = [r for r in index if int(r.get("student_id", -1)) == int(current_sid)]
        except Exception:
            pass

    # Search + Sort only (no semester/year filters)
    c1, c2 = st.columns([2, 1])
    with c1:
        q = st.text_input("Search", key="sess_search", placeholder="Type part of title or student name/ID")
    with c2:
        sort_key = st.selectbox("Sort", ["Date desc", "Date asc", "Title"], index=0, key="sess_sort")

    # Apply search
    if q:
        ql = q.lower()
        def _hit(r: Dict[str, Any]) -> bool:
            return (
                ql in str(r.get("title","")).lower()
                or ql in str(r.get("student_name","")).lower()
                or ql in str(r.get("student_id","")).lower()
            )
        index = [r for r in index if _hit(r)]

    # Sort
    if sort_key == "Date asc":
        index = sorted(index, key=lambda r: r.get("created_at",""))
    elif sort_key == "Title":
        index = sorted(index, key=lambda r: r.get("title",""))
    else:  # Date desc
        index = sorted(index, key=lambda r: r.get("created_at",""), reverse=True)

    if not index:
        st.info("No sessions found for this student." if current_sid is not None else "No sessions found.")
        return

    labels = [r.get("title","(untitled)") for r in index]
    choice_idx = st.selectbox(
        "Saved sessions",
        options=list(range(len(index))),
        format_func=lambda i: labels[i],
        key="sess_choice",
    )
    chosen = index[choice_idx]
    sid = str(chosen.get("id",""))

    b1, b2, b3 = st.columns([1.2, 1.0, 1.0])
    with b1:
        if st.button("📂 Open (view-only)", use_container_width=True, key="sess_open"):
            payload = _load_session_payload_by_id(sid)
            if payload:
                st.session_state["advising_loaded_payload"] = payload
                st.success("Loaded archived session below (read-only).")

    with b2:
        confirm = st.checkbox("Confirm delete", key="confirm_delete_session", value=False)
        if st.button("🗑️ Delete selected", use_container_width=True, disabled=not confirm, key="delete_selected_session"):
            # Remove from index + Drive
            try:
                # remove from local index
                st.session_state.advising_index = [r for r in st.session_state.advising_index if str(r.get("id","")) != sid]
                _save_index(st.session_state.advising_index)
                st.success("🗑️ Selected session deleted.")
                st.session_state.pop("advising_loaded_payload", None)
                st.rerun()
            except Exception as e:
                st.error(f"❌ Failed to delete session: {e}")

    with b3:
        # Delete all for this student
        confirm_all = st.checkbox("Confirm delete all for this student", key="confirm_delete_all_student", value=False)
        if st.button("🗑️ Delete ALL for this student", use_container_width=True, disabled=not confirm_all, key="delete_all_for_student"):
            try:
                sid_int = int(chosen.get("student_id", -1))
            except Exception:
                sid_int = None
            if sid_int is None:
                st.warning("Cannot determine student id for bulk delete.")
            else:
                st.session_state.advising_index = [r for r in st.session_state.advising_index if int(r.get("student_id",-1)) != sid_int]
                try:
                    _save_index(st.session_state.advising_index)
                except Exception as e:
                    log_error("Failed saving index after bulk delete", e)
                st.success("🗑️ All sessions for this student deleted from index.")
                st.session_state.pop("advising_loaded_payload", None)
                st.rerun()

    # Render archived snapshot (if any)
    payload = st.session_state.get("advising_loaded_payload")
    if payload:
        snapshot = payload.get("snapshot", {})
        students = snapshot.get("students", [])
        if students:
            s = students[0]  # one student snapshot per session
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
