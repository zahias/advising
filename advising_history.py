# advising_history.py
# Save/load advising sessions.
# Retrieval is now a simple, read-only list of advised/optional per student.
# Deletion (single/bulk) is supported. No other app behavior is changed.

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
    check_course_completed,   # used in snapshot builder (saving unchanged)
    check_course_registered,  # used in snapshot builder (saving unchanged)
    is_course_offered,        # used in snapshot builder (saving unchanged)
    check_eligibility,        # used in snapshot builder (saving unchanged)
    build_requisites_str,     # used in snapshot builder (saving unchanged)
    get_student_standing,     # used in snapshot builder (saving unchanged)
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
# (We still capture a full snapshot at save-time; it’s not used for the new simple view,
#  but keeping it ensures older sessions remain future-proof if you later want richer views.)

def _snapshot_courses_table() -> List[Dict[str, Any]]:
    courses_df = st.session_state.get("courses_df", pd.DataFrame())
    if courses_df.empty:
        return []
    cols = ["Course Code", "Type", "Offered", "Prerequisite", "Concurrent", "Corequisite"]
    if "Credits" in courses_df.columns:
        cols.append("Credits")
    cols = [c for c in cols if c in courses_df.columns]
    return courses_df[cols].fillna("").to_dict(orient="records")

def _snapshot_student_course_rows(student_row: pd.Series, advised: List[str], optional: List[str]) -> List[Dict[str, Any]]:
    courses_df = st.session_state.courses_df
    rows: List[Dict[str, Any]] = []
    for course_code in courses_df["Course Code"]:
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

    return {"courses_table": _snapshot_courses_table(), "students": students}


# ---------------------- Simple archived viewer (lists only) ----------------------

def _render_simple_session_view(selections: Dict[str, Any], meta: Dict[str, Any], snapshot: Dict[str, Any]) -> None:
    """
    Render a simple, read-only list of advised/optional courses per student
    from the saved 'selections'. Uses the snapshot only to map student IDs to names.
    """
    if not selections:
        st.info("This session does not have saved selections to display.")
        return

    # Build ID -> NAME map from snapshot (if available)
    id_to_name: Dict[int, str] = {}
    try:
        for s in (snapshot.get("students", []) if isinstance(snapshot, dict) else []):
            try:
                id_to_name[int(s.get("ID"))] = str(s.get("NAME", ""))
            except Exception:
                continue
    except Exception:
        pass

    st.markdown("### Archived Advising (read-only)")
    with st.container(border=True):
        st.write(
            f"**Advisor:** {meta.get('advisor','')}  |  "
            f"**Date:** {meta.get('session_date','')}  |  "
            f"**Semester:** {meta.get('semester','')}  |  "
            f"**Year:** {meta.get('year','')}"
        )

    # Sort students by name (fallback to ID if name missing)
    def _label_for(sid_str: str) -> str:
        try:
            sid_int = int(sid_str)
        except Exception:
            sid_int = sid_str  # type: ignore[assignment]
        name = id_to_name.get(sid_int, "")
        return f"{name} — {sid_str}" if name else f"Student {sid_str}"

    sorted_ids = sorted(selections.keys(), key=lambda k: _label_for(k).lower())

    # Quick filter (All / by student)
    label_options = ["All students"] + [_label_for(sid) for sid in sorted_ids]
    pick = st.selectbox("Show", options=label_options, index=0, key="simple_view_pick")

    def _render_student(sid_str: str):
        data = selections.get(sid_str, {})
        advised = [c for c in data.get("advised", []) if str(c).strip()]
        optional = [c for c in data.get("optional", []) if str(c).strip()]
        note = data.get("note", "")

        header = _label_for(sid_str)
        with st.expander(header, expanded=False):
            col_a, col_b = st.columns(2)
            with col_a:
                st.markdown("**Advised**")
                if advised:
                    st.markdown("- " + "\n- ".join(advised))
                else:
                    st.caption("— none —")
            with col_b:
                st.markdown("**Optional**")
                if optional:
                    st.markdown("- " + "\n- ".join(optional))
                else:
                    st.caption("— none —")
            if note:
                st.caption(f"Note: {note}")

    if pick == "All students":
        for sid in sorted_ids:
            _render_student(sid)
    else:
        # map pick back to sid
        if " — " in pick:
            sid_from_label = pick.split(" — ")[-1]
        else:
            # label like "Student <sid>"
            sid_from_label = pick.replace("Student ", "").strip()
        if sid_from_label in selections:
            _render_student(sid_from_label)
        else:
            # fallback: find by name match
            for sid in sorted_ids:
                if pick.endswith(sid):
                    _render_student(sid)
                    break


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


# ---------------------- Panel (save, view-simple, delete) ----------------------

def advising_history_panel():
    """
    Advising Sessions panel:
      - Save current advising snapshot (unchanged)
      - Open a session -> show a simple list of advised/optional per student (read-only)
      - Delete saved sessions (single or ALL)
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
                        # We keep both the lightweight selections and the full snapshot
                        "selections": _serialize_current_selections(),
                        "snapshot": full_snapshot,
                    }
                    sessions = st.session_state.advising_sessions or []
                    sessions.append(snapshot)
                    _save_sessions_to_drive(sessions)
                    st.session_state.advising_sessions = sessions
                    st.success("✅ Advising session saved.")
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

            ids = [str(s.get("id", i)) for i, s in enumerate(sessions)]
            labels = [_label(s) for s in sessions]

            selected_label = st.selectbox(
                "Open / Delete a session",
                options=labels,
                key="adv_hist_select_label",
                index=len(labels) - 1,
            )
            selected_idx = labels.index(selected_label)
            selected_id = ids[selected_idx]
            chosen = sessions[selected_idx]

            # Action buttons
            bcol1, bcol2 = st.columns([1, 1])
            with bcol1:
                if st.button("📂 Open Selected Session (list view)", use_container_width=True, key="open_selected_session"):
                    st.session_state["advising_loaded_simple"] = {
                        "selections": chosen.get("selections", {}),
                        "snapshot": chosen.get("snapshot", {}),
                        "meta": {
                            "advisor": chosen.get("advisor",""),
                            "session_date": chosen.get("session_date",""),
                            "semester": chosen.get("semester",""),
                            "year": chosen.get("year",""),
                        },
                    }
                    st.success("Loaded archived session below (read-only list).")
            with bcol2:
                confirm_delete = st.checkbox("Confirm delete", key="confirm_delete_session", value=False)
                if st.button("🗑️ Delete Selected Session", use_container_width=True, disabled=not confirm_delete, key="delete_selected_session"):
                    ok = _delete_sessions_by_ids([selected_id])
                    if ok:
                        st.success("🗑️ Selected session deleted.")
                        st.session_state.pop("advising_loaded_simple", None)
                        st.rerun()

            # Bulk delete inside an expander with confirm text
            with st.expander("Danger zone: Delete ALL sessions"):
                confirm_text = st.text_input("Type DELETE to confirm", key="bulk_delete_confirm")
                if st.button("🧨 Delete ALL Sessions", use_container_width=True, disabled=(confirm_text.strip() != "DELETE"), key="bulk_delete_all"):
                    ok = _delete_sessions_by_ids(ids)
                    if ok:
                        st.success("🧨 All sessions deleted.")
                        st.session_state.pop("advising_loaded_simple", None)
                        st.rerun()

    # ---- Show the simple list if loaded ----
    if "advising_loaded_simple" in st.session_state:
        payload = st.session_state["advising_loaded_simple"]
        _render_simple_session_view(
            selections=payload.get("selections", {}),
            meta=payload.get("meta", {}),
            snapshot=payload.get("snapshot", {}),
        )
