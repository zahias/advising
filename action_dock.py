"""
Action Dock Component
Persistent right sidebar with common advising actions.
"""

import streamlit as st
from typing import Optional, Callable
from datetime import datetime


def render_action_dock(
    student_id: Optional[int] = None,
    on_save: Optional[Callable] = None,
    on_email: Optional[Callable] = None,
    show_exclusions: bool = False,
    on_toggle_exclusions: Optional[Callable] = None,
):
    """
    Render persistent action dock in right sidebar.
    
    Args:
        student_id: Current student ID
        on_save: Callback for save action
        on_email: Callback for email action
        show_exclusions: Whether to show exclusion toggle
        on_toggle_exclusions: Callback for exclusion toggle
    """
    st.markdown(
        """
        <style>
        .action-dock {
            background-color: #f8f9fa;
            border-left: 3px solid #667eea;
            padding: 1rem;
            border-radius: 8px;
            position: sticky;
            top: 1rem;
        }
        .action-title {
            font-size: 1.1rem;
            font-weight: 600;
            color: #333;
            margin-bottom: 1rem;
            padding-bottom: 0.5rem;
            border-bottom: 2px solid #e0e0e0;
        }
        .action-status {
            font-size: 0.8rem;
            color: #666;
            margin-top: 0.3rem;
            padding: 0.3rem;
            background-color: #fff;
            border-radius: 4px;
        }
        </style>
        """,
        unsafe_allow_html=True
    )
    
    st.markdown('<div class="action-dock">', unsafe_allow_html=True)
    st.markdown('<div class="action-title">⚡ Quick Actions</div>', unsafe_allow_html=True)
    
    if not student_id:
        st.info("Select a student to enable actions")
        st.markdown('</div>', unsafe_allow_html=True)
        return
    
    student_name = _get_student_name(student_id)
    st.caption(f"**Student:** {student_name}")
    st.caption(f"**ID:** {student_id}")
    st.markdown("---")
    
    last_save = _get_last_save_time(student_id)
    email_configured = _check_email_configured()
    has_email = _check_student_has_email(student_id)
    
    if on_save:
        if st.button("💾 Save Session", use_container_width=True, type="primary"):
            on_save()
            st.session_state[f"last_save_{student_id}"] = datetime.now()
            st.rerun()
        
        if last_save:
            time_ago = _format_time_ago(last_save)
            st.markdown(
                f'<div class="action-status">✓ Saved {time_ago}</div>',
                unsafe_allow_html=True
            )
    
    if on_email:
        email_disabled = not email_configured or not has_email
        email_label = "✉️ Email Student"
        
        if not email_configured:
            email_label += " (Email not configured)"
        elif not has_email:
            email_label += " (No email on file)"
        
        if st.button(
            email_label,
            use_container_width=True,
            disabled=email_disabled,
            help="Send advising sheet to student via email"
        ):
            on_email()
        
        if not email_configured:
            st.markdown(
                '<div class="action-status">⚠️ Configure email in sidebar</div>',
                unsafe_allow_html=True
            )
        elif not has_email:
            st.markdown(
                '<div class="action-status">⚠️ Upload email roster for this student</div>',
                unsafe_allow_html=True
            )
    
    if show_exclusions and on_toggle_exclusions:
        st.markdown("---")
        if st.button("🚫 Manage Exclusions", use_container_width=True):
            on_toggle_exclusions()
    
    st.markdown("---")
    
    advising_status = _get_advising_status(student_id)
    st.markdown(
        f'<div class="action-status">{advising_status}</div>',
        unsafe_allow_html=True
    )
    
    st.markdown('</div>', unsafe_allow_html=True)


def _get_student_name(student_id: int) -> str:
    """Get student name from progress_df."""
    if "progress_df" not in st.session_state:
        return "Unknown"
    
    df = st.session_state.progress_df
    row = df[df["ID"] == student_id]
    if row.empty:
        row = df[df["ID"].astype(str) == str(student_id)]
    
    if not row.empty:
        return str(row.iloc[0]["NAME"])
    return "Unknown"


def _get_last_save_time(student_id: int) -> Optional[datetime]:
    """Get last save timestamp for student."""
    return st.session_state.get(f"last_save_{student_id}")


def _check_email_configured() -> bool:
    """Check if email is configured."""
    try:
        if "email" in st.secrets:
            return bool(st.secrets["email"].get("address") and st.secrets["email"].get("password"))
    except:
        pass
    
    import os
    return bool(os.getenv("EMAIL_ADDRESS") and os.getenv("EMAIL_PASSWORD"))


def _check_student_has_email(student_id: int) -> bool:
    """Check if student has email in roster."""
    try:
        from email_manager import get_student_email
        email = get_student_email(student_id)
        return bool(email)
    except:
        return False


def _get_advising_status(student_id: int) -> str:
    """Get advising status for student."""
    selections = st.session_state.get("advising_selections", {})
    student_sel = selections.get(student_id, {})
    
    advised = student_sel.get("advised", [])
    optional = student_sel.get("optional", [])
    note = student_sel.get("note", "")
    
    if advised or optional or note:
        status_parts = []
        if advised:
            status_parts.append(f"{len(advised)} advised")
        if optional:
            status_parts.append(f"{len(optional)} optional")
        if note:
            status_parts.append("has notes")
        return "✅ " + ", ".join(status_parts)
    
    return "⏳ Not yet advised"


def _format_time_ago(dt: datetime) -> str:
    """Format datetime as 'X minutes/hours ago'."""
    now = datetime.now()
    diff = now - dt
    
    seconds = diff.total_seconds()
    
    if seconds < 60:
        return "just now"
    elif seconds < 3600:
        minutes = int(seconds / 60)
        return f"{minutes} min ago" if minutes == 1 else f"{minutes} mins ago"
    elif seconds < 86400:
        hours = int(seconds / 3600)
        return f"{hours} hour ago" if hours == 1 else f"{hours} hours ago"
    else:
        days = int(seconds / 86400)
        return f"{days} day ago" if days == 1 else f"{days} days ago"
