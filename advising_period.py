# advising_period.py
from __future__ import annotations

import json
from typing import Dict, Any, List, Optional
from datetime import datetime
import streamlit as st

from google_drive import (
    initialize_drive_service,
    find_file_in_drive,
    download_file_from_drive,
    sync_file_with_drive,
    get_major_folder_id,
)
from utils import log_info, log_error

__all__ = [
    "get_current_period",
    "start_new_period",
    "get_all_periods",
    "load_period_from_drive",
    "save_period_to_drive",
]


PERIOD_FILENAME = "current_period.json"
PERIODS_HISTORY_FILENAME = "periods_history.json"


def _get_major_folder_id() -> str:
    """Get major-specific folder ID."""
    import os
    try:
        service = initialize_drive_service()
        major = st.session_state.get("current_major", "DEFAULT")
        
        root_folder_id = ""
        try:
            if "google" in st.secrets:
                root_folder_id = st.secrets["google"].get("folder_id", "")
        except:
            pass
        
        if not root_folder_id:
            root_folder_id = os.getenv("GOOGLE_FOLDER_ID", "")
        
        if not root_folder_id:
            return ""
        
        return get_major_folder_id(service, major, root_folder_id)
    except Exception:
        return ""


def get_current_period() -> Dict[str, Any]:
    """
    Get current advising period for the selected major.
    Returns dict with semester, year, advisor_name, and period_id.
    Creates default if none exists.
    """
    major = st.session_state.get("current_major", "DEFAULT")
    
    # Check session state cache first
    if "current_periods" not in st.session_state:
        st.session_state.current_periods = {}
    
    if major in st.session_state.current_periods:
        return st.session_state.current_periods[major]
    
    # Try to load from Drive
    period = load_period_from_drive()
    
    # If no period found, create default
    if not period:
        current_year = datetime.now().year
        period = {
            "period_id": f"default_{current_year}",
            "semester": "Fall",
            "year": current_year,
            "advisor_name": "",
            "created_at": datetime.now().isoformat(),
        }
    
    st.session_state.current_periods[major] = period
    return period


def load_period_from_drive() -> Optional[Dict[str, Any]]:
    """Load current period from Drive for current major."""
    try:
        major = st.session_state.get("current_major", "DEFAULT")
        log_info(f"Attempting to load period from Drive for major {major}")
        
        service = initialize_drive_service()
        if not service:
            log_info("load_period_from_drive: Drive service not initialized")
            return None
        
        folder_id = _get_major_folder_id()
        
        if not folder_id:
            log_info("load_period_from_drive: no folder_id found")
            return None
        
        log_info(f"Looking for {PERIOD_FILENAME} in folder_id: {folder_id}")
        file_id = find_file_in_drive(service, PERIOD_FILENAME, folder_id)
        if not file_id:
            log_info(f"{PERIOD_FILENAME} not found in Drive")
            return None
        
        payload = download_file_from_drive(service, file_id)
        period = json.loads(payload.decode("utf-8"))
        
        log_info(f"✓ Successfully loaded period from Drive: {period.get('period_id', 'unknown')}")
        return period
    except Exception as e:
        log_error(f"Failed to load period from Drive", e)
        import traceback
        log_error(f"Traceback: {traceback.format_exc()}", Exception("Stack trace"))
        return None


def save_period_to_drive(period: Dict[str, Any]) -> bool:
    """Save current period to Drive for current major."""
    try:
        major = st.session_state.get("current_major", "DEFAULT")
        log_info(f"Attempting to save period to Drive for major {major}: {period.get('period_id', 'unknown')}")
        
        service = initialize_drive_service()
        if not service:
            log_error("save_period_to_drive: Drive service not initialized", Exception("No service"))
            return False
        
        folder_id = _get_major_folder_id()
        
        if not folder_id:
            log_error("save_period_to_drive: no folder_id", Exception("No folder ID"))
            return False
        
        log_info(f"Saving to folder_id: {folder_id}")
        payload = json.dumps(period, indent=2).encode("utf-8")
        sync_file_with_drive(service, payload, PERIOD_FILENAME, "application/json", folder_id)
        
        log_info(f"✓ Successfully saved period to Drive: {period.get('period_id', 'unknown')}")
        return True
    except Exception as e:
        log_error(f"Failed to save period to Drive", e)
        import traceback
        log_error(f"Traceback: {traceback.format_exc()}", Exception("Stack trace"))
        return False


def set_current_period(period: Dict[str, Any]) -> bool:
    """
    Set an existing period as the current period.
    
    Args:
        period: Period dict to set as current
    
    Returns:
        True if successful, False otherwise
    """
    major = st.session_state.get("current_major", "DEFAULT")
    
    # Save to session state
    if "current_periods" not in st.session_state:
        st.session_state.current_periods = {}
    st.session_state.current_periods[major] = period
    
    # Save to Drive
    success = save_period_to_drive(period)
    
    log_info(f"Set current period: {period.get('period_id', 'unknown')}")
    return success


def start_new_period(semester: str, year: int, advisor_name: str) -> Dict[str, Any]:
    """
    Start a new advising period. Archives current period to history.
    
    Args:
        semester: Fall, Spring, or Summer
        year: Year of the period
        advisor_name: Name of the advisor
    
    Returns:
        New period dict
    """
    major = st.session_state.get("current_major", "DEFAULT")
    
    # Get current period to archive
    current_period = get_current_period()
    
    # Add to history
    _archive_period_to_history(current_period)
    
    # Create new period
    period_id = f"{semester}_{year}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    new_period = {
        "period_id": period_id,
        "semester": semester,
        "year": year,
        "advisor_name": advisor_name,
        "created_at": datetime.now().isoformat(),
    }
    
    # Save to session state and Drive
    if "current_periods" not in st.session_state:
        st.session_state.current_periods = {}
    st.session_state.current_periods[major] = new_period
    
    save_period_to_drive(new_period)
    
    log_info(f"Started new period: {period_id}")
    return new_period


def _archive_period_to_history(period: Dict[str, Any]) -> None:
    """Archive a period to the history file in Drive."""
    try:
        service = initialize_drive_service()
        folder_id = _get_major_folder_id()
        major = st.session_state.get("current_major", "DEFAULT")

        if not folder_id:
            return

        # Load existing history
        history = []
        file_id = find_file_in_drive(service, PERIODS_HISTORY_FILENAME, folder_id)
        if file_id:
            try:
                payload = download_file_from_drive(service, file_id)
                history = json.loads(payload.decode("utf-8"))
                if not isinstance(history, list):
                    history = []
            except:
                history = []
        
        # Add current period to history (avoid duplicates)
        period_id = period.get("period_id", "")
        if period_id and not any(p.get("period_id") == period_id for p in history):
            period_copy = period.copy()
            period_copy["archived_at"] = datetime.now().isoformat()
            history.append(period_copy)
        
        # Save updated history
        payload = json.dumps(history, indent=2).encode("utf-8")
        sync_file_with_drive(service, payload, PERIODS_HISTORY_FILENAME, "application/json", folder_id)

        if "period_history_cache" not in st.session_state:
            st.session_state.period_history_cache = {}
        st.session_state.period_history_cache[major] = history

        log_info(f"Archived period to history: {period_id}")
    except Exception as e:
        log_error(f"Failed to archive period to history", e)


def _merge_period_entries(existing: Dict[str, Any], new_entry: Dict[str, Any]) -> Dict[str, Any]:
    """Merge two period records, preserving archived metadata when available."""

    merged = existing.copy()
    merged.update({k: v for k, v in new_entry.items()})

    archived_at = new_entry.get("archived_at") or existing.get("archived_at")
    if archived_at:
        merged["archived_at"] = archived_at

    # Ensure we keep the latest created_at timestamp if both exist
    created_existing = existing.get("created_at", "")
    created_new = new_entry.get("created_at", "")
    if created_new and created_new > created_existing:
        merged["created_at"] = created_new
    elif created_existing and not created_new:
        merged["created_at"] = created_existing

    return merged


def get_all_periods() -> List[Dict[str, Any]]:
    """
    Get all periods (current + history) for the current major.
    Returns list sorted by creation date (newest first).
    """

    major = st.session_state.get("current_major", "DEFAULT")

    if "period_history_cache" not in st.session_state:
        st.session_state.period_history_cache = {}

    cached_history: List[Dict[str, Any]] = st.session_state.period_history_cache.get(major, [])
    history: List[Dict[str, Any]] = []
    history_loaded = False

    try:
        service = initialize_drive_service()
        folder_id = _get_major_folder_id()

        if service and folder_id:
            file_id = find_file_in_drive(service, PERIODS_HISTORY_FILENAME, folder_id)
            if file_id:
                payload = download_file_from_drive(service, file_id)
                history_payload = json.loads(payload.decode("utf-8"))
                if isinstance(history_payload, list):
                    history = history_payload
                    history_loaded = True
    except Exception as e:
        log_error(f"Failed to load period history", e)

    if history_loaded:
        st.session_state.period_history_cache[major] = history
    else:
        history = cached_history

    combined_periods: List[Dict[str, Any]] = []

    current = get_current_period()
    if current:
        combined_periods.append(current)

    combined_periods.extend(history)

    unique_periods: Dict[str, Dict[str, Any]] = {}
    order: List[str] = []

    for period in combined_periods:
        period_id = period.get("period_id")
        if not period_id:
            # If there is no period_id, treat as unique by object id to avoid collisions
            period_id = f"__unnamed__{id(period)}"

        if period_id in unique_periods:
            unique_periods[period_id] = _merge_period_entries(unique_periods[period_id], period)
        else:
            unique_periods[period_id] = period.copy()
            order.append(period_id)

    deduped_periods = [unique_periods[pid] for pid in order]
    deduped_periods.sort(key=lambda p: p.get("created_at", ""), reverse=True)

    return deduped_periods
