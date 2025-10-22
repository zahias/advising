# advising_history.py
# Sessions are now created AUTOMATICALLY when the advisor clicks "Save Selections"
# in the eligibility view. This panel only lists, opens (read-only), exports, and deletes.
# - Per-student snapshots only (no legacy, no semester/year, no restore/use-in-current).
# - Title format: "YYYY-MM-DD HH:MM — NAME (ID)" in Asia/Beirut local time.
# - Index + per-session JSON on Drive for speed & reliability.

from __future__ import annotations

import io
import json
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4
from datetime import datetime, date

import pandas as pd
import streamlit as st

from google_drive import (
    initialize_drive_service,
    find_file_in_drive,
    download_file_from_drive,
    sync_file_with_drive,
    download_file_by_name,
    delete_file_by_name,
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
    load_progress_excel,
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
        log_error("Failed to load index", e)
        return []

def _save_index(index_items: List[Dict[str, Any]]) -> None:
    try:
        service = initialize_drive_service()
        folder_id = st.secrets["google"]["folder_id"]
        data = json.dumps(index_items, ensure_ascii=False, indent=2).encode("utf-8")
        sync_file_with_drive(service, data, _index_name(), "application/json", folder_id)
        log_info(f"Index saved: {_index_name()}")
    except Exception as e:
        log_error("Failed to save index", e)
        raise

def _save_session_payload(session_id: str, snapshot: Dict[str, Any], meta: Dict[str, Any]) -> None:
    try:
        service = initialize_drive_service()
        folder_id = st.secrets["google"]["folder_id"]
        payload = {"meta": meta, "snapshot": snapshot}
        data = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
        sync_file_with_drive(service, data, _session_filename(session_id), "application/json", folder_id)
        log_info(f"Session payload saved: {_session_filename(session_id)}")
    except Exception as e:
        log_error("Failed to save session payload", e)
        raise

def _load_session_payload_by_id(session_id: str) -> Optional[Dict[str, Any]]:
    try:
        service = initialize_drive_service()
        folder_id = st.secrets["google"]["folder_id"]
        data = download_file_by_name(service, folder_id, _session_filename(session_id))
        return json.loads(data.decode("utf-8")) if data else None
    except Exception as e:
        log_error("Failed to load session payload", e)
        return None

def _delete_session_payload_by_id(session_id: str) -> bool:
    try:
        service = initialize_drive_service()
        folder_id = st.secrets["google"]["folder_id"]
        return delete_file_by_name(service, folder_id, _session_filename(session_id))
    except Exception:
        return False


# ----------------- Build snapshots (per-student) -----------------

def _snapshot_courses_table() -> List[Dict[str, Any]]:
    courses_df = st.session_state.get("courses_df", pd.DataFrame())
    if courses_df.empty:
        return []
    cols = ["Course Code", "Type", "Offered", "Prerequisite", "Concurrent", "Corequisite"]
    if "Credits" in courses_df.columns:
        cols.append("Credits")
    cols = [c for c in cols if c in courses_df.columns]
    return courses_df[cols].fillna("").to_dict(orient="records")


def _snapshot_student_courses(student_row: pd.Series, advised: List[str], optional: List[str]) -> List[Dict[str, Any]]:
    # Respect hidden courses
    from course_exclusions import get_for_student, ensure_loaded
    ensure_loaded()
    hidden = set(map(str, get_for_student(int(student_row.get("ID")))))

    courses_df = st.session_state.courses_df
    rows: List[Dict[str, Any]] = []

    for course_code in courses_df["Course Code"]:
        code = str(course_code)
        if code in hidden:
            continue
        info = courses_df.loc[courses_df["Course Code"] == course_code].iloc[0]
        offered = "Yes" if is_course_offered(courses_df, course_code) else "No"
        status, justification = check_eligibility(student_row, course_code, advised, courses_df)

        if check_course_completed(student_row, course_code):
            action = "Completed"; status = "Completed"
        elif check_course_registered(student_row, course_code):
            action = "Registered"
        elif course_code in advised:
            action = "Advised"
        elif course_code in optional:
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
    progress_df = st.session_state.get("progress_df", pd.DataFrame())
    if progress_df.empty:
        return {"courses_table": [], "students": []}

    row = progress_df.loc[progress_df["ID"] == int(student_id)]
    if row.empty:
        return {"courses_table": [], "students": []}
    srow = row.iloc[0]

    selections = st.session_state.get("advising_selections", {}) or {}
    sel = selections.get(int(student_id), {})
    advised = list(sel.get("advised", []))
    optional = list(sel.get("optional", []))
    note = sel.get("note", "")

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
            "note": note,                       # NOTE is saved here
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

        # Build snapshot (contains NOTE)
        snapshot = _build_single_student_snapshot(int(current_sid))
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

        # Title
        now = _now_beirut()
        title = f"{now.strftime('%Y-%m-%d %H:%M')} — {student_name} ({int(current_sid)})"

        # Persist: payload + index
        sid = str(uuid4())
        meta = {
            "id": sid,
            "title": title,
            "created_at": now.isoformat(),
            "major": st.session_state.get("current_major", ""),
            "student_id": int(current_sid),
            "student_name": student_name,
        }

        # Ensure index in session
        if "advising_index" not in st.session_state:
            st.session_state.advising_index = _load_index()

        _save_session_payload(sid, snapshot, meta)

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
        _save_index(st.session_state.advising_index)

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

    # Default: show only current student's sessions (if a student is selected)
    current_sid = st.session_state.get("current_student_id", None)
    if current_sid is not None:
        index = [r for r in index if int(r.get("student_id", -1)) == int(current_sid)]

    # Search + Sort only
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
    choice_idx = st.selectbox("Saved sessions", options=list(range(len(index))), format_func=lambda i: labels[i], key="sess_choice")
    chosen = index[choice_idx]
    sid = str(chosen.get("id",""))

    b1, b2 = st.columns([1.2, 1.0])
    with b1:
        if st.button("📂 Open (view-only)", use_container_width=True, key="sess_open"):
            payload = _load_session_payload_by_id(sid)
            if payload:
                st.session_state["advising_loaded_payload"] = payload
                st.success("Loaded archived session below (read-only).")
    with b2:
        if st.button("⬇️ Export Excel", use_container_width=True, key="sess_export"):
            payload = _load_session_payload_by_id(sid)
            if payload:
                data = _make_excel_package(payload)
                st.download_button(
                    "Download session.xlsx",
                    data=data,
                    file_name=f"{chosen.get('title','session').replace(':','-')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key="sess_export_dl",
                )

    with st.expander("Danger zone"):
        col_del, _ = st.columns([1, 3])
        with col_del:
            confirm_text = st.text_input("Type DELETE to remove this session", key="sess_del_confirm")
            if st.button("🗑️ Delete", use_container_width=True, disabled=(confirm_text.strip() != "DELETE"), key="sess_del"):
                ok1 = _delete_session_payload_by_id(sid)
                rest = [r for r in st.session_state.advising_index if str(r.get("id","")) != sid]
                try:
                    _save_index(rest)
                    st.session_state.advising_index = rest
                    if ok1:
                        st.success("Session deleted.")
                    else:
                        st.warning("Index updated, but session file might still exist.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Failed to update index: {e}")

    # Show archived view (read-only)
    if "advising_loaded_payload" in st.session_state:
        _render_archived_view(st.session_state["advising_loaded_payload"])


# ----------------- Archived viewer & Excel export -----------------

def _render_archived_view(payload: Dict[str, Any]) -> None:
    meta = payload.get("meta", {})
    snap = payload.get("snapshot", {})
    students = snap.get("students", [])

    st.markdown("### Archived Session (read-only)")
    with st.container(border=True):
        st.write(f"**Title:** {meta.get('title','')}")
        st.caption(f"Saved: {meta.get('created_at','')}  |  Student: {meta.get('student_name','')} ({meta.get('student_id','')})")

    if not students:
        st.info("This snapshot has no students.")
        return

    s = students[0]  # per-student snapshot by design
    st.write(
        f"**Name:** {s.get('NAME','')}  |  **ID:** {s.get('ID','')}  |  "
        f"**Credits:** {int((s.get('# of Credits Completed',0) or 0) + (s.get('# Registered',0) or 0))}  |  "
        f"**Standing:** {s.get('Standing','')}"
    )
    if s.get("note"):
        with st.expander("Advisor Note"):
            st.write(s.get("note",""))

    df = pd.DataFrame(s.get("courses", []))
    if df.empty:
        st.info("No course rows stored in snapshot.")
        return
    preferred = ["Course Code","Type","Requisites","Offered","Eligibility Status","Justification","Action"]
    cols = [c for c in preferred if c in df.columns] + [c for c in df.columns if c not in preferred]
    st.dataframe(style_df(df[cols]), use_container_width=True)


def _make_excel_package(payload: Dict[str, Any]) -> bytes:
    """Return an .xlsx (bytes) with a Summary + student sheet (with NOTE included as a column)."""
    import io
    meta = payload.get("meta", {})
    snap = payload.get("snapshot", {})
    students = snap.get("students", [])
    courses_table = snap.get("courses_table", [])

    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as w:
        # Summary
        s = students[0] if students else {}
        pd.DataFrame([{
            "Title": meta.get("title",""),
            "Saved at": meta.get("created_at",""),
            "Student": f"{meta.get('student_name','')} ({meta.get('student_id','')})",
            "Standing": s.get("Standing",""),
            "Note": s.get("note",""),
        }]).to_excel(w, index=False, sheet_name="Summary")

        # Student sheet with NOTE included as a column
        if s and s.get("courses"):
            df = pd.DataFrame(s["courses"])
            df.insert(0, "Note", s.get("note",""))
            df.to_excel(w, index=False, sheet_name="Student")
        else:
            pd.DataFrame([{"Info": "No courses captured"}]).to_excel(w, index=False, sheet_name="Student")

        # Optional: raw courses table snapshot
        if courses_table:
            pd.DataFrame(courses_table).to_excel(w, index=False, sheet_name="CoursesTable")

    # We keep formatting simple here; the detailed color formatting is handled in reporting.py
    return buf.getvalue()
