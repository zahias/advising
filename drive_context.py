from __future__ import annotations

import os
import time
from typing import Any, Dict

import streamlit as st


def _get_drive_module():
    import google_drive as gd

    return gd


def get_root_folder_id() -> str:
    root_folder_id = ""
    try:
        if "google" in st.secrets:
            root_folder_id = st.secrets["google"].get("folder_id", "")
    except Exception:
        pass
    if not root_folder_id:
        root_folder_id = os.getenv("GOOGLE_FOLDER_ID", "")
    return root_folder_id


def get_drive_context(
    major: str,
    *,
    force_refresh: bool = False,
    ttl_seconds: int = 300,
) -> Dict[str, Any]:
    cache_key = f"_drive_ctx_{major}"
    now = time.time()
    cached = st.session_state.get(cache_key, {})

    if cached and not force_refresh and (now - float(cached.get("last_refresh_ts", 0))) < ttl_seconds:
        return cached

    ctx: Dict[str, Any] = {
        "major": major,
        "last_refresh_ts": now,
        "root_folder_id": get_root_folder_id(),
        "major_folder_id": "",
        "sessions_folder_id": "",
        "service": None,
    }

    if not ctx["root_folder_id"] or not major:
        st.session_state[cache_key] = ctx
        return ctx

    try:
        gd = _get_drive_module()
        service = gd.initialize_drive_service()
        major_folder_id = gd.get_major_folder_id(service, major, ctx["root_folder_id"])
        sessions_folder_id = gd.get_or_create_folder(service, "sessions", major_folder_id)

        ctx["service"] = service
        ctx["major_folder_id"] = major_folder_id
        ctx["sessions_folder_id"] = sessions_folder_id
    except Exception:
        pass

    st.session_state[cache_key] = ctx
    return ctx

