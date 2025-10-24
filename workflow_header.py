"""
Workflow Progress Header
Shows data readiness status and current workflow step for advisors.
"""

import streamlit as st
import pandas as pd


def render_workflow_header():
    """
    Render a persistent workflow status bar showing:
    - Data loading status
    - Current workflow step
    - Quick stats (students loaded, Drive sync status)
    """
    current_major = st.session_state.get("current_major", "")
    
    courses_loaded = not st.session_state.get("courses_df", pd.DataFrame()).empty
    progress_loaded = not st.session_state.get("progress_df", pd.DataFrame()).empty
    num_students = len(st.session_state.get("progress_df", pd.DataFrame()))
    
    drive_synced = _check_drive_status()
    email_configured = _check_email_status()
    
    data_ready = courses_loaded and progress_loaded
    
    st.markdown(
        """
        <style>
        .workflow-header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 1rem;
            border-radius: 8px;
            margin-bottom: 1.5rem;
            color: white;
        }
        .workflow-step {
            display: inline-block;
            padding: 0.4rem 0.8rem;
            margin: 0.3rem;
            border-radius: 20px;
            font-size: 0.9rem;
            font-weight: 500;
        }
        .step-complete {
            background-color: rgba(76, 175, 80, 0.3);
            border: 2px solid #4CAF50;
        }
        .step-active {
            background-color: rgba(255, 193, 7, 0.3);
            border: 2px solid #FFC107;
        }
        .step-pending {
            background-color: rgba(158, 158, 158, 0.2);
            border: 2px solid #9E9E9E;
        }
        .workflow-stats {
            margin-top: 0.8rem;
            font-size: 0.85rem;
            opacity: 0.95;
        }
        .stat-badge {
            display: inline-block;
            padding: 0.2rem 0.6rem;
            margin-right: 0.5rem;
            background-color: rgba(255, 255, 255, 0.2);
            border-radius: 12px;
        }
        </style>
        """,
        unsafe_allow_html=True
    )
    
    step1_class = "step-complete" if data_ready else "step-active"
    step2_class = "step-complete" if data_ready else "step-pending"
    step3_class = "step-active" if data_ready else "step-pending"
    step4_class = "step-pending"
    
    step1_icon = "✅" if data_ready else "⏳"
    step2_icon = "✅" if data_ready else "⏸️"
    step3_icon = "📝" if data_ready else "⏸️"
    step4_icon = "⏸️"
    
    stats_html = ""
    if data_ready:
        stats_html = f"""
        <div class="workflow-stats">
            <span class="stat-badge">📊 {num_students} students loaded</span>
            <span class="stat-badge">{'☁️ Drive synced' if drive_synced else '💾 Local only'}</span>
            <span class="stat-badge">{'✉️ Email ready' if email_configured else '📧 Email not configured'}</span>
        </div>
        """
    
    html = f"""
    <div class="workflow-header">
        <div style="font-size: 1.1rem; font-weight: 600; margin-bottom: 0.8rem;">
            {current_major} Advising Workflow
        </div>
        <div>
            <span class="workflow-step {step1_class}">{step1_icon} Load Data</span>
            <span style="color: rgba(255,255,255,0.5);">→</span>
            <span class="workflow-step {step2_class}">{step2_icon} Review Eligibility</span>
            <span style="color: rgba(255,255,255,0.5);">→</span>
            <span class="workflow-step {step3_class}">{step3_icon} Document Session</span>
            <span style="color: rgba(255,255,255,0.5);">→</span>
            <span class="workflow-step {step4_class}">{step4_icon} Follow-up Email</span>
        </div>
        {stats_html}
    </div>
    """
    
    st.markdown(html, unsafe_allow_html=True)
    
    if not data_ready:
        if not courses_loaded and not progress_loaded:
            st.warning(f"⚠️ **Action Required:** Upload both courses table and progress report for {current_major} to begin advising.")
        elif not courses_loaded:
            st.warning(f"⚠️ **Action Required:** Upload courses table for {current_major}.")
        elif not progress_loaded:
            st.warning(f"⚠️ **Action Required:** Upload progress report for {current_major}.")


def _check_drive_status() -> bool:
    """Check if Google Drive is configured and synced."""
    try:
        import os
        from google_drive import initialize_drive_service
        
        folder_id = ""
        try:
            if "google" in st.secrets:
                folder_id = st.secrets["google"].get("folder_id", "")
        except:
            pass
        
        if not folder_id:
            folder_id = os.getenv("GOOGLE_FOLDER_ID", "")
        
        if folder_id:
            service = initialize_drive_service()
            return service is not None
    except:
        pass
    return False


def _check_email_status() -> bool:
    """Check if email is configured."""
    try:
        if "email" in st.secrets:
            return bool(st.secrets["email"].get("address") and st.secrets["email"].get("password"))
    except:
        pass
    
    import os
    return bool(os.getenv("EMAIL_ADDRESS") and os.getenv("EMAIL_PASSWORD"))
