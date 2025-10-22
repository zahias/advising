# advising_history.py
# Advising Sessions panel:
# - Save scope: Current student (default) or All students (legacy)
# - Stores small index + one JSON per session (fast listing & deletion)
# - Restore environment to the versioned files used at save time
# - Reuse selections in current advising (per-student or all)
# - Search / filter / sort; Excel export package
# Backward-compat: auto-imports legacy advising_sessions_{MAJOR}.json into the new layout.

from __future__ import annotations

import json
import re
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
    list_files_with_prefix,
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

__all__ = ["advising_history_panel"]


# ------------- Naming helpers -------------

def _index_name() -> str:
    major = st.session_state.get("current_major", "DEFAULT")
    return f"advising_index_{major}.json"

def _legacy_bundle_name() -> str:
    major = st.session_state.get("current_major", "DEFAULT")
    return f"advising_sessions_{major}.json"

def _session_filename(session_id: str) -> str:
    major = st.session_state.get("current_major", "DEFAULT")
    return f"advising_session_{major}_{session_id}.json"


# ------------- Drive I/O (index + per-session) -------------

def _load_index() -> List[Dict[str, Any]]:
    try:
        service = initialize_drive_service()
        folder_id = st.secrets["google"]["folder_id"]
        fid = find_file_in_drive(service, _index_name(), folder_id)
        if not fid:
            # Legacy migration path
            legacy = _load_legacy_bundle()
            if legacy:
                idx = _migrate_legacy_to_index_and_sessions(service, folder_id, legacy)
                return idx
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
        sync_file_with_drive(
            service, data, _index_name(), "application/json", folder_id
        )
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


# ------------- Legacy bundle migration -------------

def _load_legacy_bundle() -> List[Dict[str, Any]]:
    try:
        service = initialize_drive_service()
        folder_id = st.secrets["google"]["folder_id"]
        fid = find_file_in_drive(service, _legacy_bundle_name(), folder_id)
        if not fid:
            return []
        data = download_file_from_drive(service, fid)
        arr = json.loads(data.decode("utf-8"))
        return arr if isinstance(arr, list) else []
    except Exception:
        return []

def _migrate_legacy_to_index_and_sessions(service, folder_id, legacy: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    index: List[Dict[str, Any]] = []
    for item in legacy:
        sid = item.get("id") or str(uuid4())
        # try to derive minimal index row
        created = item.get("created_at") or datetime.utcnow().isoformat() + "Z"
        meta = {
            "advisor": item.get("advisor",""),
            "session_date": item.get("session_date",""),
            "semester": item.get("semester",""),
            "year": item.get("year",""),
            "scope": item.get("scope","all"),
            "student_id": item.get("student_id",""),
            "student_name": item.get("student_name",""),
            "created_at": created,
            "major": st.session_state.get("current_major",""),
            "courses_version": item.get("courses_version",""),
            "progress_version": item.get("progress_version",""),
        }
        # persist payload
        payload = {"meta": meta, "snapshot": item.get("snapshot") or item}
        data = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
        sync_file_with_drive(service, data, _session_filename(sid), "application/json", folder_id)

        # light index row
        index.append({
            "id": sid,
            "advisor": meta["advisor"],
            "session_date": meta["session_date"],
            "semester": meta["semester"],
            "year": meta["year"],
            "created_at": created,
            "major": meta["major"],
            "scope": meta["scope"],
            "student_id": meta["student_id"],
            "student_name": meta["student_name"],
            "session_file": _session_filename(sid),
            "students_count": len((item.get("snapshot") or {}).get("students", [])) if isinstance(item.get("snapshot"), dict) else None,
        })

    # save index
    idx_bytes = json.dumps(index, ensure_ascii=False, indent=2).encode("utf-8")
    sync_file_with_drive(service, idx_bytes, _index_name(), "application/json", folder_id)
    log_info("Migrated legacy advising_sessions to index + per-session payloads.")
    return index


# ------------- Build snapshots (respect hidden) -------------

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
            "note": note,
            "courses": course_rows,
        }],
    }


def _build_full_snapshot() -> Dict[str, Any]:
    progress_df = st.session_state.get("progress_df", pd.DataFrame())
    if progress_df.empty:
        return {"courses_table": [], "students": []}

    selections = st.session_state.get("advising_selections", {}) or {}
    students: List[Dict[str, Any]] = []
    for _, srow in progress_df.iterrows():
        sid = int(srow.get("ID"))
        sel = selections.get(sid, {})
        advised = list(sel.get("advised", []))
        optional = list(sel.get("optional", []))
        note = sel.get("note", "")

        credits_completed = float(srow.get("# of Credits Completed", 0) or 0)
        credits_registered = float(srow.get("# Registered", 0) or 0)
        standing = get_student_standing(credits_completed + credits_registered)

        students.append({
            "ID": sid,
            "NAME": str(srow.get("NAME")),
            "# of Credits Completed": credits_completed,
            "# Registered": credits_registered,
            "Standing": standing,
            "advised": advised,
            "optional": optional,
            "note": note,
            "courses": _snapshot_student_courses(srow, advised, optional),
        })

    return {"courses_table": _snapshot_courses_table(), "students": students}


# ------------- Versioned file detection & restore -------------

_VERSION_RE = re.compile(r"_(\d{8}-\d{4})\.xlsx$", re.IGNORECASE)

def _latest_versioned_names(major: str) -> Tuple[Optional[str], Optional[str]]:
    """Return latest versioned names for courses & progress for this major, based on Drive listing."""
    try:
        service = initialize_drive_service()
        folder_id = st.secrets["google"]["folder_id"]

        # Look for e.g., PBHL_courses_table_YYYYMMDD-HHMM.xlsx
        courses_list = list_files_with_prefix(service, folder_id, f"{major}_courses_table_")
        progress_list = list_files_with_prefix(service, folder_id, f"{major}_progress_report_")

        courses_name = courses_list[0]["name"] if courses_list else None
        progress_name = progress_list[0]["name"] if progress_list else None
        return courses_name, progress_name
    except Exception as e:
        log_error("Latest versioned name lookup failed", e)
        return None, None


def _restore_environment_from_versioned(courses_name: Optional[str], progress_name: Optional[str]) -> bool:
    """Load given versioned files into session_state; return True if both loaded."""
    ok_any = False
    try:
        service = initialize_drive_service()
        folder_id = st.secrets["google"]["folder_id"]
        major = st.session_state.get("current_major", "")

        if progress_name:
            content = download_file_by_name(service, folder_id, progress_name)
            if content:
                st.session_state.progress_df = load_progress_excel(content)
                st.session_state.majors[major]["progress_df"] = st.session_state.progress_df
                ok_any = True

        if courses_name:
            content = download_file_by_name(service, folder_id, courses_name)
            if content:
                df = pd.read_excel(io.BytesIO(content))  # type: ignore[name-defined]
                st.session_state.courses_df = df
                st.session_state.majors[major]["courses_df"] = df
                ok_any = True

        return bool(ok_any)
    except Exception as e:
        log_error("Restore environment failed", e)
        return False


# ------------- Utility: sums for index preview -------------

def _course_credit_lookup() -> Dict[str, float]:
    df = st.session_state.get("courses_df", pd.DataFrame())
    if df.empty or "Course Code" not in df.columns or "Credits" not in df.columns:
        return {}
    ser = df.set_index(df["Course Code"].astype(str))["Credits"]
    out: Dict[str, float] = {}
    for k, v in ser.items():
        try:
            out[str(k)] = float(v or 0)
        except Exception:
            pass
    return out

def _sum_selections_credits(snapshot: Dict[str, Any]) -> Tuple[int, int]:
    """Return (advised_sum, optional_sum) across students using current courses_df for credits."""
    lookup = _course_credit_lookup()
    a = 0.0; o = 0.0
    for s in snapshot.get("students", []):
        for code in (s.get("advised") or []):
            a += lookup.get(str(code), 0.0)
        for code in (s.get("optional") or []):
            o += lookup.get(str(code), 0.0)
    return int(a), int(o)


# ------------- Panel UI -------------

def advising_history_panel():
    st.markdown("---")
    st.subheader(f"Advising Sessions — {st.session_state.get('current_major','')}")

    # Load index (and migrate legacy if needed)
    if "advising_index" not in st.session_state:
        st.session_state.advising_index = _load_index()

    tab_save, tab_sessions = st.tabs(["Save Session", "Sessions"])

    # ---------- SAVE ----------
    with tab_save:
        can_save = ("courses_df" in st.session_state and not st.session_state.courses_df.empty and
                    "progress_df" in st.session_state and not st.session_state.progress_df.empty)

        c1, c2, c3, c4 = st.columns([2, 2, 1.5, 1])
        with c1:
            advisor_name = st.text_input("Advisor Name", key="adv_idx_name")
        with c2:
            session_date: date = st.date_input("Session Date", key="adv_idx_date")
        with c3:
            semester = st.selectbox("Semester", ["Fall", "Spring", "Summer"], key="adv_idx_sem")
        with c4:
            year = st.number_input("Year", min_value=2000, max_value=2100, value=datetime.now().year, step=1, key="adv_idx_year")

        scope = st.radio(
            "Save scope",
            options=["Current student only", "All students (legacy)"],
            index=0,
            horizontal=True,
            key="adv_idx_scope",
        )

        # resolve current student
        current_sid = st.session_state.get("current_student_id", None)
        current_sname = None
        if current_sid is not None and "progress_df" in st.session_state and not st.session_state.progress_df.empty:
            try:
                current_sname = str(st.session_state.progress_df.loc[st.session_state.progress_df["ID"] == int(current_sid)]["NAME"].iloc[0])
            except Exception:
                current_sname = None

        # detect the latest versioned files (for provenance)
        major = st.session_state.get("current_major", "")
        latest_courses, latest_progress = _latest_versioned_names(major)

        save_col = st.columns([1, 6, 1])[1]
        with save_col:
            if st.button("💾 Save Advising Session", use_container_width=True, disabled=not can_save):
                if not advisor_name:
                    st.error("Please enter Advisor Name.")
                else:
                    try:
                        if scope == "Current student only":
                            if current_sid is None:
                                st.error("No student selected. Pick a student in the Student Eligibility View.")
                                st.stop()
                            snapshot = _build_single_student_snapshot(int(current_sid))
                            scope_meta = {"scope": "single", "student_id": int(current_sid), "student_name": current_sname or ""}
                        else:
                            snapshot = _build_full_snapshot()
                            scope_meta = {"scope": "all"}

                        # compute quick totals for index preview
                        advised_sum, optional_sum = _sum_selections_credits(snapshot)

                        sid = str(uuid4())
                        meta = {
                            "advisor": advisor_name,
                            "session_date": session_date.isoformat() if isinstance(session_date, date) else str(session_date),
                            "semester": semester,
                            "year": int(year),
                            "created_at": datetime.utcnow().isoformat() + "Z",
                            "major": major,
                            "courses_version": latest_courses or "",
                            "progress_version": latest_progress or "",
                            **scope_meta,
                        }

                        # save payload + index row
                        _save_session_payload(sid, snapshot, meta)

                        index_row = {
                            "id": sid,
                            "advisor": meta["advisor"],
                            "session_date": meta["session_date"],
                            "semester": meta["semester"],
                            "year": meta["year"],
                            "created_at": meta["created_at"],
                            "major": meta["major"],
                            "scope": meta.get("scope","all"),
                            "student_id": meta.get("student_id",""),
                            "student_name": meta.get("student_name",""),
                            "session_file": _session_filename(sid),
                            "students_count": len(snapshot.get("students", [])),
                            "advised_sum": advised_sum,
                            "optional_sum": optional_sum,
                            "courses_version": meta.get("courses_version",""),
                            "progress_version": meta.get("progress_version",""),
                        }
                        st.session_state.advising_index.append(index_row)
                        _save_index(st.session_state.advising_index)

                        if scope_meta.get("scope") == "single":
                            st.success(f"✅ Saved for {scope_meta.get('student_name','student')} ({scope_meta.get('student_id','')}).")
                        else:
                            st.success("✅ Saved session for all students (legacy).")
                    except Exception as e:
                        st.error(f"❌ Failed to save advising session: {e}")

    # ---------- SESSIONS ----------
    with tab_sessions:
        index = st.session_state.advising_index or []
        if not index:
            st.info("No saved sessions found for this major.")
            return

        # filters
        cols = st.columns([2, 1.5, 1, 1])
        with cols[0]:
            q = st.text_input("Search (advisor/title/student)", key="adv_idx_search", placeholder="e.g., Zahi, 2025, 12345, Nour")
        with cols[1]:
            semf = st.selectbox("Semester", ["All", "Fall", "Spring", "Summer"], index=0, key="adv_idx_f_sem")
        with cols[2]:
            yf = st.selectbox("Year", ["All"] + sorted({str(i.get("year","")) for i in index if i.get("year")}, reverse=True), index=0, key="adv_idx_f_year")
        with cols[3]:
            sort_key = st.selectbox("Sort by", ["Date desc","Date asc","Students","Advised credits"], index=0, key="adv_idx_sort")

        # optionally focus current student’s sessions
        current_sid = st.session_state.get("current_student_id", None)
        show_current_only = False
        if current_sid is not None:
            show_current_only = st.checkbox(f"Only current student ({current_sid})", value=False, key="adv_idx_only_current")

        filtered = index
        if show_current_only:
            filtered = [r for r in filtered if (r.get("scope") == "single" and int(r.get("student_id", -1)) == int(current_sid)) or r.get("scope") == "all"]
        if semf != "All":
            filtered = [r for r in filtered if r.get("semester") == semf]
        if yf != "All":
            filtered = [r for r in filtered if str(r.get("year","")) == yf]
        if q:
            ql = q.lower()
            def _hit(r):
                return (
                    ql in str(r.get("advisor","")).lower()
                    or ql in str(r.get("student_name","")).lower()
                    or ql in str(r.get("student_id","")).lower()
                    or ql in str(r.get("session_date","")).lower()
                )
            filtered = [r for r in filtered if _hit(r)]

        # sorting
        if sort_key == "Date asc":
            filtered = sorted(filtered, key=lambda r: r.get("session_date",""))
        elif sort_key == "Students":
            filtered = sorted(filtered, key=lambda r: r.get("students_count",0), reverse=True)
        elif sort_key == "Advised credits":
            filtered = sorted(filtered, key=lambda r: r.get("advised_sum",0), reverse=True)
        else:  # Date desc
            filtered = sorted(filtered, key=lambda r: r.get("session_date",""), reverse=True)

        if not filtered:
            st.info("No sessions match your filters.")
            return

        labels = [
            f"{r.get('session_date','')} — {r.get('semester','')} {r.get('year','')} — {r.get('advisor','')}"
            + (f" — {r.get('student_name','')} ({r.get('student_id','')})" if r.get("scope") == "single" else "")
            for r in filtered
        ]
        chosen_idx = st.selectbox("Saved sessions", options=list(range(len(filtered))), format_func=lambda i: labels[i], key="adv_idx_select")
        chosen = filtered[chosen_idx]
        sid = str(chosen.get("id",""))

        b1, b2, b3, b4 = st.columns([1.3, 1.5, 1.6, 1.2])
        with b1:
            if st.button("📂 Open (view-only)", use_container_width=True, key="adv_idx_open"):
                payload = _load_session_payload_by_id(sid)
                if payload:
                    st.session_state["advising_loaded_payload"] = payload
                    st.success("Loaded archived session below (read-only).")
        with b2:
            if st.button("🧩 Use selections in current advising", use_container_width=True, key="adv_idx_use"):
                payload = _load_session_payload_by_id(sid)
                if payload:
                    snap = payload.get("snapshot", {})
                    for s in snap.get("students", []):
                        sid0 = int(s.get("ID"))
                        st.session_state.advising_selections.setdefault(sid0, {})
                        st.session_state.advising_selections[sid0]["advised"] = list(map(str, s.get("advised") or []))
                        st.session_state.advising_selections[sid0]["optional"] = list(map(str, s.get("optional") or []))
                        st.session_state.advising_selections[sid0]["note"] = s.get("note","")
                    st.success("Selections copied into current advising.")
                    st.rerun()
        with b3:
            if st.button("🧰 Restore environment (files)", use_container_width=True, key="adv_idx_restore"):
                courses_ver = chosen.get("courses_version") or ""
                progress_ver = chosen.get("progress_version") or ""
                ok = False
                if courses_ver or progress_ver:
                    ok = _restore_environment_from_versioned(courses_ver or None, progress_ver or None)
                if ok:
                    st.success("Environment restored to session’s files.")
                    st.rerun()
                else:
                    st.warning("Couldn’t find the versioned files recorded with this session. You can still open the snapshot below.")
        with b4:
            if st.button("⬇️ Export Excel", use_container_width=True, key="adv_idx_export"):
                payload = _load_session_payload_by_id(sid)
                if payload:
                    df_bytes = _make_excel_package(payload)
                    st.download_button(
                        "Download session.xlsx",
                        data=df_bytes,
                        file_name=f"advising_session_{sid}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        key="adv_idx_download_btn",
                    )

        # delete row
        with st.expander("Danger zone: Delete this session"):
            cdel1, cdel2 = st.columns([3, 1])
            with cdel1:
                confirm_text = st.text_input("Type DELETE to confirm", key="adv_idx_del_confirm")
            with cdel2:
                if st.button("🗑️ Delete", use_container_width=True, disabled=(confirm_text.strip() != "DELETE"), key="adv_idx_delete"):
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

        # archived viewer pane (if loaded)
        if "advising_loaded_payload" in st.session_state:
            _render_archived_view(st.session_state["advising_loaded_payload"])


# ------------- Archived viewer & Excel export -------------

def _render_archived_view(payload: Dict[str, Any]) -> None:
    meta = payload.get("meta", {})
    snap = payload.get("snapshot", {})
    students = snap.get("students", [])

    st.markdown("### Archived Session (read-only)")
    with st.container(border=True):
        extra = ""
        if meta.get("scope") == "single":
            extra = f"  |  **Student:** {meta.get('student_name','')} ({meta.get('student_id','')})"
        st.write(
            f"**Advisor:** {meta.get('advisor','')}  |  "
            f"**Date:** {meta.get('session_date','')}  |  "
            f"**Semester:** {meta.get('semester','')}  |  "
            f"**Year:** {meta.get('year','')}{extra}"
        )
        cv = meta.get("courses_version","")
        pv = meta.get("progress_version","")
        if cv or pv:
            st.caption(f"Files used: {cv or '—'}  |  {pv or '—'}")

    if not students:
        st.info("This snapshot has no students.")
        return

    if meta.get("scope") == "single" and len(students) == 1:
        s = students[0]
    else:
        lbls = [f"{s.get('NAME','')} — {s.get('ID','')}" for s in students]
        idx = st.selectbox("View student", options=list(range(len(students))), format_func=lambda i: lbls[i], key="archived_view_pick")
        s = students[idx]

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
    """Return an .xlsx (bytes) with Summary + per-student sheets."""
    import io
    from openpyxl.utils import get_column_letter
    meta = payload.get("meta", {})
    snap = payload.get("snapshot", {})
    students = snap.get("students", [])
    courses_table = snap.get("courses_table", [])

    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as w:
        # Summary
        summary_rows = [{
            "Advisor": meta.get("advisor",""),
            "Date": meta.get("session_date",""),
            "Semester": meta.get("semester",""),
            "Year": meta.get("year",""),
            "Scope": meta.get("scope",""),
            "Student": f"{meta.get('student_name','')} ({meta.get('student_id','')})" if meta.get("scope")=="single" else "",
            "Courses file": meta.get("courses_version",""),
            "Progress file": meta.get("progress_version",""),
            "Students in snapshot": len(students),
        }]
        pd.DataFrame(summary_rows).to_excel(w, index=False, sheet_name="Summary")

        # Courses table snapshot (optional)
        if courses_table:
            pd.DataFrame(courses_table).to_excel(w, index=False, sheet_name="CoursesTable")

        # One sheet per student
        for s in students:
            df = pd.DataFrame(s.get("courses", [])) if s.get("courses") else pd.DataFrame()
            name = str(s.get("NAME",""))[:20].strip() or "Student"
            sid = str(s.get("ID",""))
            sheet = f"{name}_{sid}"[:31]  # Excel sheet name limit
            if df.empty:
                # minimal sheet
                pd.DataFrame([{
                    "ID": sid, "NAME": name, "Standing": s.get("Standing",""),
                    "Note": s.get("note",""), "Advised": ",".join(map(str, s.get("advised") or [])),
                    "Optional": ",".join(map(str, s.get("optional") or [])),
                }]).to_excel(w, index=False, sheet_name=sheet)
            else:
                df.to_excel(w, index=False, sheet_name=sheet)
    return buf.getvalue()
