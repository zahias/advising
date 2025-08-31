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
from utils import (
    log_info,
    log_error,
    check_course_completed,
    check_course_registered,
    is_course_offered,
    check_eligibility,
    build_requisites_str,
    get_student_standing,
)

_SESSIONS_FILENAME = "advising_sessions.json"


# ---------------------- Drive I/O ----------------------

def _load_sessions_from_drive() -> List[Dict[str, Any]]:
    """Load sessions list from Google Drive; returns [] if none or invalid."""
    try:
        service = initialize_drive_service()
        folder_id = st.secrets["google"]["folder_id"]
        file_id = find_file_in_drive(service, _SESSIONS_FILENAME, folder_id)
        if not file_id:
            return []
        payload = download_file_from_drive(service, file_id)  # bytes
        try:
            sessions = json.loads(payload.decode("utf-8"))
            return sessions if isinstance(sessions, list) else []
        except Exception:
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


# ---------------------- Session state helpers ----------------------

def _ensure_sessions_loaded() -> None:
    """Ensure st.session_state.advising_sessions is present."""
    if "advising_sessions" not in st.session_state:
        st.session_state.advising_sessions = _load_sessions_from_drive()

def _serialize_current_selections() -> Dict[str, Any]:
    """
    Take current advising selections (dict keyed by student ID) and
    convert keys to strings for stable JSON.
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
    Replace current advising selections with a saved snapshot.
    Keys are strings in storage; convert to int where possible.
    """
    restored: Dict[int, Dict[str, Any]] = {}
    for sid_str, payload in (saved_obj or {}).items():
        try:
            sid = int(sid_str)
        except Exception:
            # keep original key if non-numeric
            sid = sid_str  # type: ignore[assignment]
        restored[sid] = {
            "advised": list(payload.get("advised", [])),
            "optional": list(payload.get("optional", [])),
            "note": payload.get("note", ""),
        }
    st.session_state.advising_selections = restored


# ---------------------- Full snapshot builder ----------------------

def _snapshot_courses_table() -> List[Dict[str, Any]]:
    """
    Serialize the courses table minimally but fully enough to reproduce per-course info later.
    """
    courses_df = st.session_state.get("courses_df", pd.DataFrame())
    if courses_df.empty:
        return []
    cols = ["Course Code", "Type", "Offered", "Prerequisite", "Concurrent", "Corequisite"]
    # include Credits if present
    if "Credits" in courses_df.columns:
        cols.append("Credits")
    # keep only existing cols
    cols = [c for c in cols if c in courses_df.columns]
    return courses_df[cols].fillna("").to_dict(orient="records")

def _snapshot_student_course_rows(student_row: pd.Series, advised: List[str], optional: List[str]) -> List[Dict[str, Any]]:
    """
    Build a row per course with all details, using current logic:
      - Eligibility Status + Justification
      - Action (Completed/Registered/Advised/Optional/Eligible (not chosen)/Not Eligible)
      - Type, Offered, Requisites (built string)
    """
    courses_df = st.session_state.courses_df
    rows: List[Dict[str, Any]] = []
    for course_code in courses_df["Course Code"]:
        info = courses_df.loc[courses_df["Course Code"] == course_code].iloc[0]
        offered = "Yes" if is_course_offered(courses_df, course_code) else "No"

        status, justification = check_eligibility(student_row, course_code, advised, courses_df)

        # Derive Action to mirror the UI/export
        if check_course_completed(student_row, course_code):
            action = "Completed"
            status = "Completed"
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
            "Course Code": course_code,
            "Type": info.get("Type", ""),
            "Requisites": build_requisites_str(info),
            "Offered": offered,
            "Eligibility Status": status,
            "Justification": justification,
            "Action": action,
        })
    return rows

def _build_full_session_snapshot() -> Dict[str, Any]:
    """
    Build a self-contained snapshot:
      - courses_table (minimal copy)
      - students: list[{id,name,credits completed, registered, standing, advised, optional, note, courses:[...]}]
    """
    progress_df = st.session_state.get("progress_df", pd.DataFrame())
    courses_df = st.session_state.get("courses_df", pd.DataFrame())
    selections = st.session_state.get("advising_selections", {}) or {}

    if progress_df.empty or courses_df.empty:
        return {"courses_table": [], "students": []}

    students: List[Dict[str, Any]] = []
    for _, srow in progress_df.iterrows():
        sid = int(srow.get("ID"))
        sname = str(srow.get("NAME"))
        credits_completed = float(srow.get("# of Credits Completed", 0) or 0)
        credits_registered = float(srow.get("# Registered", 0) or 0)
        standing = get_student_standing(credits_completed + credits_registered)

        sel = selections.get(sid, {})
        advised = list(sel.get("advised", []))
        optional = list(sel.get("optional", []))
        note = sel.get("note", "")

        course_rows = _snapshot_student_course_rows(srow, advised, optional)

        students.append({
            "ID": sid,
            "NAME": sname,
            "# of Credits Completed": credits_completed,
            "# Registered": credits_registered,
            "Standing": standing,
            "advised": advised,
            "optional": optional,
            "note": note,
            "courses": course_rows,
        })

    return {
        "courses_table": _snapshot_courses_table(),
        "students": students,
    }


# ---------------------- Panel (UI) ----------------------

def advising_history_panel():
    """
    Advising Sessions panel at the end of the dashboard:
      - Advisor name, session date, semester, year
      - Save current advising snapshot (now includes FULL info)
      - Retrieve previously saved sessions (restores selections)
    """
    if "courses_df" not in st.session_state or st.session_state.courses_df.empty:
        return
    if "progress_df" not in st.session_state or st.session_state.progress_df.empty:
        return

    # lazy load existing sessions
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

    save_col, load_col = st.columns([1, 2])

    # -------- Save button: store selections + FULL snapshot --------
    with save_col:
        if st.button("💾 Save Advising Session", use_container_width=True):
            if not advisor_name:
                st.error("Please enter Advisor Name.")
            else:
                try:
                    full_snapshot = _build_full_session_snapshot()
                    snapshot = {
                        "id": str(uuid4()),
                        "advisor": advisor_name,
                        "session_date": session_date.isoformat() if isinstance(session_date, date) else str(session_date),
                        "semester": semester,
                        "year": int(year),
                        "created_at": datetime.utcnow().isoformat() + "Z",
                        # Keep existing lightweight selections for backward-compat,
                        # AND store a full, self-contained snapshot.
                        "selections": _serialize_current_selections(),
                        "snapshot": full_snapshot,
                    }
                    sessions = st.session_state.advising_sessions or []
                    sessions.append(snapshot)
                    _save_sessions_to_drive(sessions)
                    st.session_state.advising_sessions = sessions
                    st.success("✅ Advising session saved (full snapshot).")
                except Exception as e:
                    st.error(f"❌ Failed to save advising session: {e}")

    # -------- Retrieval: restore selections (unchanged behavior) --------
    with load_col:
        sessions = st.session_state.advising_sessions or []
        if not sessions:
            st.info("No saved advising sessions found.")
            return

        def _label(s: Dict[str, Any]) -> str:
            return f"{s.get('session_date','')} — {s.get('semester','')} {s.get('year','')} — {s.get('advisor','')}"

        idx = st.selectbox(
            "Retrieve a previous session",
            options=list(range(len(sessions))),
            format_func=lambda i: _label(sessions[i]),
            key="adv_hist_select",
            index=len(sessions) - 1,
        )
        if st.button("↩️ Load Selected Session", use_container_width=True):
            try:
                chosen = sessions[idx]
                # Restore only the selections into the live dashboard (as before)
                _restore_selections(chosen.get("selections", {}))
                # Also keep the full snapshot in memory for downstream use (read-only).
                st.session_state["advising_loaded_snapshot"] = chosen.get("snapshot", {})
                st.success("✅ Advising session loaded. The dashboard will refresh.")
                st.rerun()
            except Exception as e:
                st.error(f"❌ Failed to load advising session: {e}")
