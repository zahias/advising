# advising_history.py
# Save/load advising sessions.
# Retrieval is READ-ONLY from the frozen snapshot.
# Now includes deletion of saved sessions (single and bulk).

import json
from typing import Any, Dict, List, Optional
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
    check_course_completed,    # used in snapshot builder
    check_course_registered,   # used in snapshot builder
    is_course_offered,         # used in snapshot builder
    check_eligibility,         # used in snapshot builder
    build_requisites_str,      # used in snapshot builder
    get_student_standing,      # used in snapshot builder
    style_df,                  # used to style archived per-course grid
)

__all__ = ["advising_history_panel"]

_SESSIONS_FILENAME = "advising_sessions.json"


# ---------------------- Drive I/O ----------------------

def _load_sessions_from_drive() -> List[Dict[str, Any]]:
    """Load sessions list from Google Drive; returns [] if file missing or invalid."""
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
    """Ensure st.session_state.advising_sessions exists."""
    if "advising_sessions" not in st.session_state:
        st.session_state.advising_sessions = _load_sessions_from_drive()

def _serialize_current_selections() -> Dict[str, Any]:
    """
    Current advising selections -> JSON-safe dict (keys become strings).
    {
      "12345": {"advised": [...], "optional": [...], "note": "..."},
      ...
    }
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


# ---------------------- Full snapshot builder (unchanged) ----------------------

def _snapshot_courses_table() -> List[Dict[str, Any]]:
    """Minimal but complete copy of the courses table to preserve context."""
    courses_df = st.session_state.get("courses_df", pd.DataFrame())
    if courses_df.empty:
        return []
    cols = ["Course Code", "Type", "Offered", "Prerequisite", "Concurrent", "Corequisite"]
    if "Credits" in courses_df.columns:
        cols.append("Credits")
    cols = [c for c in cols if c in courses_df.columns]
    return courses_df[cols].fillna("").to_dict(orient="records")

def _snapshot_student_course_rows(
    student_row: pd.Series,
    advised: List[str],
    optional: List[str],
) -> List[Dict[str, Any]]:
    """
    For each course, capture:
      Course Code, Type, Requisites, Offered, Eligibility Status, Justification, Action
    """
    courses_df = st.session_state.courses_df
    rows: List[Dict[str, Any]] = []
    for course_code in courses_df["Course Code"]:
        info = courses_df.loc[courses_df["Course Code"] == course_code].iloc[0]
        offered = "Yes" if is_course_offered(courses_df, course_code) else "No"

        status, justification = check_eligibility(student_row, course_code, advised, courses_df)

        # Derive Action exactly like the UI
        if check_course_completed(student_row, course_code):
            action = "Completed"
            status  = "Completed"
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
            "Course Code": str(course_code),
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
    Self-contained snapshot:
      - courses_table: minimal copy
      - students: full per-student + per-course advising state
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


# ---------------------- Archived viewer (read-only) ----------------------

def _render_archived_session_view(snapshot: Dict[str, Any], meta: Dict[str, Any]) -> None:
    """Render the archived session from its own snapshot only (no dependency on current files)."""
    if not snapshot or "students" not in snapshot:
        st.info("This session doesn’t contain a full snapshot (older save).")
        return

    st.markdown("### Archived Session (read-only)")
    with st.container(border=True):
        st.write(
            f"**Advisor:** {meta.get('advisor','')}  |  "
            f"**Date:** {meta.get('session_date','')}  |  "
            f"**Semester:** {meta.get('semester','')}  |  "
            f"**Year:** {meta.get('year','')}"
        )

    students = snapshot.get("students", [])
    if not students:
        st.info("No students captured in this snapshot.")
        return

    # Build a small picker from the archived list
    labels = [f"{s.get('NAME','')} — {s.get('ID','')}" for s in students]
    idx = st.selectbox(
        "View student",
        options=list(range(len(students))),
        format_func=lambda i: labels[i],
        key="archived_view_student_idx",
    )
    s = students[idx]

    # Student header
    st.write(
        f"**Name:** {s.get('NAME','')}  |  **ID:** {s.get('ID','')}  |  "
        f"**Credits:** {int((s.get('# of Credits Completed',0) or 0) + (s.get('# Registered',0) or 0))}  |  "
        f"**Standing:** {s.get('Standing','')}"
    )
    if s.get("note"):
        with st.expander("Advisor Note"):
            st.write(s["note"])

    # Per-course grid exactly as saved
    course_rows = s.get("courses", [])
    if not course_rows:
        st.info("No course rows were stored for this student in the snapshot.")
        return

    df = pd.DataFrame(course_rows)
    preferred_cols = ["Course Code","Type","Requisites","Offered","Eligibility Status","Justification","Action"]
    cols = [c for c in preferred_cols if c in df.columns] + [c for c in df.columns if c not in preferred_cols]
    df = df[cols]
    st.dataframe(style_df(df), use_container_width=True)


# ---------------------- Delete helpers ----------------------

def _delete_sessions_by_ids(ids: List[str]) -> bool:
    """Delete sessions with matching 'id' fields; return True if saved successfully."""
    sessions = st.session_state.advising_sessions or []
    # Fallback: if any session lacks an id, allow deletion by keeping those not selected
    remaining = [s for s in sessions if str(s.get("id", "")) not in set(ids)]
    try:
        _save_sessions_to_drive(remaining)
        st.session_state.advising_sessions = remaining
        return True
    except Exception as e:
        st.error(f"❌ Failed to delete session(s): {e}")
        log_error("Failed to delete advising sessions", e)
        return False


# ---------------------- Panel (save, view, delete) ----------------------

def advising_history_panel():
    """
    Advising Sessions panel:
      - Save current advising snapshot (full snapshot is embedded)
      - Retrieve a session -> VIEW ONLY from the frozen snapshot (no edits; does not touch live selections)
      - Delete saved sessions (single or bulk)
    """
    _ensure_sessions_loaded()

    st.markdown("---")
    st.subheader("Advising Sessions")

    # ---- Save block (enabled only if live data is present) ----
    can_save = ("courses_df" in st.session_state and not st.session_state.courses_df.empty and
                "progress_df" in st.session_state and not st.session_state.progress_df.empty)

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

    with save_col:
        disabled_msg = None
        if not can_save:
            disabled_msg = "Upload current Courses & Progress files to enable saving."
        if st.button("💾 Save Advising Session", use_container_width=True, disabled=not can_save):
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
                        # Maintain lightweight selections & full snapshot
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
        if disabled_msg:
            st.caption(disabled_msg)

    # ---- Retrieve & Delete block ----
    with load_col:
        sessions = st.session_state.advising_sessions or []
        if not sessions:
            st.info("No saved advising sessions found.")
        else:
            def _label(s: Dict[str, Any]) -> str:
                date_s = s.get("session_date","")
                sem = s.get("semester","")
                yr = s.get("year","")
                adv = s.get("advisor","")
                return f"{date_s} — {sem} {yr} — {adv}"

            # Build a stable map of ID -> label; fall back to index if id missing
            ids = [str(s.get("id", i)) for i, s in enumerate(sessions)]
            labels = [_label(s) for s in sessions]
            id_to_label = dict(zip(ids, labels))

            # Select ONE to open/delete
            selected_label = st.selectbox(
                "Retrieve / Delete a session",
                options=labels,
                key="adv_hist_select_label",
                index=len(labels) - 1,
            )
            # Resolve back to id
            selected_idx = labels.index(selected_label)
            selected_id = ids[selected_idx]

            # Action buttons side by side
            bcol1, bcol2 = st.columns([1, 1])
            with bcol1:
                if st.button("📂 Open Selected Session (view-only)", use_container_width=True, key="open_selected_session"):
                    chosen = sessions[selected_idx]
                    st.session_state["advising_loaded_snapshot"] = chosen.get("snapshot", {})
                    st.session_state["advising_loaded_meta"] = {
                        "advisor": chosen.get("advisor",""),
                        "session_date": chosen.get("session_date",""),
                        "semester": chosen.get("semester",""),
                        "year": chosen.get("year",""),
                    }
                    st.success("Loaded archived session below (read-only).")
            with bcol2:
                confirm_delete = st.checkbox("Confirm delete", key="confirm_delete_session", value=False)
                if st.button("🗑️ Delete Selected Session", use_container_width=True, disabled=not confirm_delete, key="delete_selected_session"):
                    ok = _delete_sessions_by_ids([selected_id])
                    if ok:
                        st.success("🗑️ Selected session deleted.")
                        # Clear any loaded snapshot that might reference the deleted id
                        st.session_state.pop("advising_loaded_snapshot", None)
                        st.session_state.pop("advising_loaded_meta", None)
                        st.rerun()

            # Bulk delete (optional) inside an expander with strong confirmation
            with st.expander("Danger zone: Delete ALL sessions"):
                confirm_text = st.text_input("Type DELETE to confirm", key="bulk_delete_confirm")
                if st.button("🧨 Delete ALL Sessions", use_container_width=True, disabled=(confirm_text.strip() != "DELETE"), key="bulk_delete_all"):
                    ok = _delete_sessions_by_ids(ids)  # delete by all known ids
                    if ok:
                        st.success("🧨 All sessions deleted.")
                        st.session_state.pop("advising_loaded_snapshot", None)
                        st.session_state.pop("advising_loaded_meta", None)
                        st.rerun()

    # ---- Archived viewer (if any snapshot is loaded) ----
    if "advising_loaded_snapshot" in st.session_state:
        _render_archived_session_view(
            st.session_state.get("advising_loaded_snapshot", {}),
            st.session_state.get("advising_loaded_meta", {}),
        )
