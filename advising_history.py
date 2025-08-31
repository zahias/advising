# advising_history.py
# Save/load advising sessions (full snapshots).
# Retrieval is READ-ONLY from the frozen snapshot.
# Includes delete (single & bulk).
# UI refined: two tabs (Save Session / Sessions), compact controls.

import json
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
            action = "Completed"; status  = "Completed"
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

    # Compact student picker
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
    remaining = [s for s in sessions if str(s.get("id", "")) not in set(ids)]
    try:
        _save_sessions_to_drive(remaining)
        st.session_state.advising_sessions = remaining
        return True
    except Exception as e:
        st.error(f"❌ Failed to delete session(s): {e}")
        log_error("Failed to delete advising sessions", e)
        return False


# ---------------------- Panel (two tabs; same functionality) ----------------------

def _format_label(s: Dict[str, Any]) -> str:
    date_s = s.get("session_date","")
    sem = s.get("semester","")
    yr = s.get("year","")
    adv = s.get("advisor","")
    return f"{date_s} — {sem} {yr} — {adv}"

def advising_history_panel():
    """
    Advising Sessions panel (clean UI):
      - Tab 1: Save Session (unchanged logic)
      - Tab 2: Sessions (retrieve view-only + delete / delete-all)
    """
    _ensure_sessions_loaded()

    st.markdown("---")
    st.subheader("Advising Sessions")

    tab_save, tab_sessions = st.tabs(["Save Session", "Sessions"])

    # ------------------ Tab: Save Session ------------------
    with tab_save:
        # Save enabled only if live data is present (unchanged)
        can_save = ("courses_df" in st.session_state and not st.session_state.courses_df.empty and
                    "progress_df" in st.session_state and not st.session_state.progress_df.empty)

        # Compact header row
        c1, c2, c3, c4 = st.columns([2, 2, 1.5, 1])
        with c1:
            advisor_name = st.text_input("Advisor Name", key="adv_hist_name")
        with c2:
            session_date: date = st.date_input("Session Date", key="adv_hist_date")
        with c3:
            semester = st.selectbox("Semester", ["Fall", "Spring", "Summer"], key="adv_hist_sem")
        with c4:
            year = st.number_input("Year", min_value=2000, max_value=2100, value=datetime.now().year, step=1, key="adv_hist_year")

        st.markdown("")  # small spacing
        save_button_col = st.columns([1, 6, 1])[1]
        with save_button_col:
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

        if not can_save:
            st.caption("Upload current Courses & Progress files to enable saving.")

    # ------------------ Tab: Sessions (retrieve + delete) ------------------
    with tab_sessions:
        sessions = st.session_state.advising_sessions or []
        if not sessions:
            st.info("No saved advising sessions found.")
            return

        # Build stable ids and labels
        ids = [str(s.get("id", i)) for i, s in enumerate(sessions)]
        labels = [_format_label(s) for s in sessions]

        # Selection row
        s1, s2 = st.columns([3, 2])
        with s1:
            selected_label = st.selectbox(
                "Saved sessions",
                options=labels,
                index=len(labels) - 1,
                key="adv_hist_select_label",
            )
        selected_idx = labels.index(selected_label)
        selected_id = ids[selected_idx]
        chosen = sessions[selected_idx]

        # Action buttons row (centered)
        ab1, ab2, ab3 = st.columns([2, 2, 2])
        with ab1:
            if st.button("📂 Open (view-only)", use_container_width=True, key="open_selected_session"):
                st.session_state["advising_loaded_snapshot"] = chosen.get("snapshot", {})
                st.session_state["advising_loaded_meta"] = {
                    "advisor": chosen.get("advisor",""),
                    "session_date": chosen.get("session_date",""),
                    "semester": chosen.get("semester",""),
                    "year": chosen.get("year",""),
                }
                st.success("Loaded archived session below (read-only).")
        with ab2:
            # Compact confirm inline; keeps UI tidy
            confirm = st.checkbox("Confirm", key="confirm_delete_session", value=False)
            if st.button("🗑️ Delete selected", use_container_width=True, disabled=not confirm, key="delete_selected_session"):
                ok = _delete_sessions_by_ids([selected_id])
                if ok:
                    st.success("🗑️ Selected session deleted.")
                    st.session_state.pop("advising_loaded_snapshot", None)
                    st.session_state.pop("advising_loaded_meta", None)
                    st.rerun()

        # Danger zone (bulk delete) — tucked away
        with st.expander("Danger zone: Delete ALL sessions"):
            dz1, dz2 = st.columns([3, 1.2])
            with dz1:
                confirm_text = st.text_input("Type DELETE to confirm", key="bulk_delete_confirm")
            with dz2:
                if st.button("🧨 Delete ALL", use_container_width=True, disabled=(confirm_text.strip() != "DELETE"), key="bulk_delete_all"):
                    ok = _delete_sessions_by_ids(ids)
                    if ok:
                        st.success("🧨 All sessions deleted.")
                        st.session_state.pop("advising_loaded_snapshot", None)
                        st.session_state.pop("advising_loaded_meta", None)
                        st.rerun()

        # Archived viewer (appears only when loaded)
        if "advising_loaded_snapshot" in st.session_state:
            _render_archived_session_view(
                st.session_state.get("advising_loaded_snapshot", {}),
                st.session_state.get("advising_loaded_meta", {}),
            )
