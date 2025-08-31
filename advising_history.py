# advising_history.py
# Save/load advising sessions. Retrieval is READ-ONLY from the frozen snapshot.
# Includes deletion of saved sessions. (Layout streamlined; functionality unchanged.)

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
    check_course_completed,
    check_course_registered,
    is_course_offered,
    check_eligibility,
    build_requisites_str,
    get_student_standing,
    style_df,
)

__all__ = ["advising_history_panel"]

_SESSIONS_FILENAME = "advising_sessions.json"


# ---------------------- Drive I/O ----------------------

def _load_sessions_from_drive() -> List[Dict[str, Any]]:
    try:
        service = initialize_drive_service()
        folder_id = st.secrets["google"]["folder_id"]
        file_id = find_file_in_drive(service, _SESSIONS_FILENAME, folder_id)
        if not file_id:
            return []
        payload = download_file_from_drive(service, file_id)
        sessions = json.loads(payload.decode("utf-8"))
        return sessions if isinstance(sessions, list) else []
    except Exception as e:
        log_error("Failed to load advising sessions from Drive", e)
        return []

def _save_sessions_to_drive(sessions: List[Dict[str, Any]]) -> None:
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


# ---------------------- Helpers ----------------------

def _ensure_sessions_loaded() -> None:
    if "advising_sessions" not in st.session_state:
        st.session_state.advising_sessions = _load_sessions_from_drive()

def _serialize_current_selections() -> Dict[str, Any]:
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

    return {
        "courses_table": _snapshot_courses_table(),
        "students": students,
    }

def _render_archived_session_view(snapshot: Dict[str, Any], meta: Dict[str, Any]) -> None:
    if not snapshot or "students" not in snapshot:
        st.info("This session doesn’t contain a full snapshot (older save).")
        return

    st.markdown("##### Archived Session (read-only)")
    with st.container():
        st.caption(
            f"Advisor: {meta.get('advisor','')}  •  Date: {meta.get('session_date','')}  •  "
            f"Semester: {meta.get('semester','')}  •  Year: {meta.get('year','')}"
        )

    students = snapshot.get("students", [])
    if not students:
        st.info("No students captured in this snapshot.")
        return

    labels = [f"{s.get('NAME','')} — {s.get('ID','')}" for s in students]
    idx = st.selectbox(
        "Student",
        options=list(range(len(students))),
        format_func=lambda i: labels[i],
        key="archived_view_student_idx",
    )
    s = students[idx]

    st.markdown("###### Student Summary")
    st.caption(
        f"Name: {s.get('NAME','')} • ID: {s.get('ID','')} • "
        f"Credits: {int((s.get('# of Credits Completed',0) or 0) + (s.get('# Registered',0) or 0))} • "
        f"Standing: {s.get('Standing','')}"
    )
    if s.get("note"):
        with st.expander("Advisor Note", expanded=False):
            st.write(s["note"])

    course_rows = s.get("courses", [])
    if not course_rows:
        st.info("No course rows were stored for this student in the snapshot.")
        return

    df = pd.DataFrame(course_rows)
    preferred = ["Course Code","Type","Requisites","Offered","Eligibility Status","Justification","Action"]
    cols = [c for c in preferred if c in df.columns] + [c for c in df.columns if c not in preferred]
    st.dataframe(style_df(df[cols]), use_container_width=True)


# ---------------------- Delete helpers ----------------------

def _delete_sessions_by_ids(ids: List[str]) -> bool:
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


# ---------------------- Panel (organized UI) ----------------------

def advising_history_panel():
    _ensure_sessions_loaded()

    # Two clear sections side-by-side
    left, right = st.columns([5, 7], gap="large")

    with left:
        st.markdown("#### Save Session")
        can_save = ("courses_df" in st.session_state and not st.session_state.courses_df.empty and
                    "progress_df" in st.session_state and not st.session_state.progress_df.empty)

        a, b = st.columns([1, 1])
        with a:
            advisor_name = st.text_input("Advisor", key="adv_hist_name")
            semester = st.selectbox("Semester", ["Fall", "Spring", "Summer"], key="adv_hist_sem")
        with b:
            session_date: date = st.date_input("Date", key="adv_hist_date")
            year = st.number_input("Year", min_value=2000, max_value=2100, value=datetime.now().year, step=1, key="adv_hist_year")

        disabled_msg = None
        if not can_save:
            disabled_msg = "Upload current Courses & Progress files to enable saving."
        st.button("💾 Save Advising Session", use_container_width=True, disabled=not can_save, key="save_session_btn")
        if st.session_state.get("save_session_btn"):
            if not advisor_name:
                st.error("Please enter Advisor.")
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
                    st.success("Session saved.")
                except Exception as e:
                    st.error(f"Failed to save session: {e}")
        if disabled_msg:
            st.caption(disabled_msg)

    with right:
        st.markdown("#### Browse & Delete Sessions")
        sessions = st.session_state.advising_sessions or []
        if not sessions:
            st.info("No saved sessions.")
            return

        def _label(s: Dict[str, Any]) -> str:
            return f"{s.get('session_date','')} — {s.get('semester','')} {s.get('year','')} — {s.get('advisor','')}"

        ids = [str(s.get("id", i)) for i, s in enumerate(sessions)]
        labels = [_label(s) for s in sessions]

        # Single row controls
        c1, c2 = st.columns([3, 1])
        with c1:
            selected_label = st.selectbox("Session", options=labels, index=len(labels)-1, key="adv_hist_select_label")
            selected_idx = labels.index(selected_label)
            selected_id = ids[selected_idx]
        with c2:
            # small space for actions
            st.markdown("&nbsp;", unsafe_allow_html=True)
            open_clicked = st.button("Open", use_container_width=True, key="open_selected_session")
            del_clicked = st.button("Delete", use_container_width=True, key="delete_selected_session")

        if open_clicked:
            chosen = sessions[selected_idx]
            st.session_state["advising_loaded_snapshot"] = chosen.get("snapshot", {})
            st.session_state["advising_loaded_meta"] = {
                "advisor": chosen.get("advisor",""),
                "session_date": chosen.get("session_date",""),
                "semester": chosen.get("semester",""),
                "year": chosen.get("year",""),
            }
            st.success("Loaded below.")

        if del_clicked:
            with st.popover("Confirm delete?"):
                st.caption("This will permanently delete the selected session.")
                if st.button("Yes, delete"):
                    if _delete_sessions_by_ids([selected_id]):
                        st.success("Deleted.")
                        st.session_state.pop("advising_loaded_snapshot", None)
                        st.session_state.pop("advising_loaded_meta", None)
                        st.rerun())

        # Bulk delete in a compact expander
        with st.expander("Danger zone"):
            confirm_text = st.text_input("Type DELETE to remove all sessions", key="bulk_delete_confirm")
            if st.button("Delete ALL", disabled=(confirm_text.strip() != "DELETE")):
                if _delete_sessions_by_ids(ids):
                    st.success("All sessions deleted.")
                    st.session_state.pop("advising_loaded_snapshot", None)
                    st.session_state.pop("advising_loaded_meta", None)
                    st.rerun()

    # Archived viewer (below, spans full width)
    if "advising_loaded_snapshot" in st.session_state:
        st.markdown("---")
        _render_archived_session_view(
            st.session_state.get("advising_loaded_snapshot", {}),
            st.session_state.get("advising_loaded_meta", {}),
        )
