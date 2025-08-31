# app.py

import os
from io import BytesIO

import pandas as pd
import streamlit as st

from data_upload import upload_data
from eligibility_view import student_eligibility_view
from full_student_view import full_student_view
from google_drive import (
    download_file_from_drive,
    find_file_in_drive,
    initialize_drive_service,
    sync_file_with_drive,
)
from utils import load_progress_excel, log_error, log_info

st.set_page_config(layout="wide")

# ---- Header (unchanged except for logo path) ----
header_col1, header_col2 = st.columns([1, 6])
with header_col1:
    if os.path.exists("pu_logo.png"):
        st.image("pu_logo.png", width=120)
    else:
        st.write("Logo not found.")
with header_col2:
    st.markdown(
        """
        <h1 style="margin-bottom:0px;">Phoenicia University Advising System</h1>
        <p style="margin-top:0px;">Manage eligibility, advising, and reporting efficiently.</p>
        """,
        unsafe_allow_html=True,
    )
st.markdown("<small>System developed by Dr. Zahi Abdul Sater</small>", unsafe_allow_html=True)

# ---- Initialize Drive ----
service = initialize_drive_service()

# ---- Load from Drive (progress now supports 2 sheets) ----
def load_data_from_drive():
    # Courses
    cid = find_file_in_drive(service, "courses_table.xlsx", st.secrets["google"]["folder_id"])
    if cid:
        try:
            content = download_file_from_drive(service, cid)
            st.session_state.courses_df = pd.read_excel(BytesIO(content))
            st.success("✅ Courses table loaded from Google Drive.")
            log_info("Courses table loaded.")
        except Exception as e:
            st.session_state.courses_df = pd.DataFrame()
            st.error(f"❌ Error loading courses table: {e}")
            log_error("Error loading courses table", e)
    else:
        st.session_state.courses_df = pd.DataFrame()
        st.warning("⚠️ Courses table not found on Google Drive.")

    # Progress (supports 'Required Courses' + 'Intensive Courses')
    pid = find_file_in_drive(service, "progress_report.xlsx", st.secrets["google"]["folder_id"])
    if pid:
        try:
            content = download_file_from_drive(service, pid)
            st.session_state.progress_df = load_progress_excel(content)
            st.success("✅ Progress report loaded from Google Drive.")
            log_info("Progress report loaded.")
        except Exception as e:
            st.session_state.progress_df = pd.DataFrame()
            st.error(f"❌ Error loading progress report: {e}")
            log_error("Error loading progress report", e)
    else:
        st.session_state.progress_df = pd.DataFrame()
        st.warning("⚠️ Progress report not found on Google Drive.")

    # Advising selections (unchanged)
    aid = find_file_in_drive(service, "advising_selections.xlsx", st.secrets["google"]["folder_id"])
    if aid:
        try:
            content = download_file_from_drive(service, aid)
            df = pd.read_excel(BytesIO(content))
            sel = {}
            for _, r in df.iterrows():
                sel[str(r["ID"])] = {
                    "advised": [c.strip() for c in str(r.get("Advised", "")).split(",") if c and c.strip()],
                    "optional": [c.strip() for c in str(r.get("Optional", "")).split(",") if c and c.strip()],
                    "note": r.get("Note", "") if pd.notna(r.get("Note", "")) else "",
                }
            st.session_state.advising_selections = sel
            st.success("✅ Advising selections loaded from Google Drive.")
        except Exception as e:
            st.session_state.advising_selections = {}
            st.error(f"❌ Error loading advising selections: {e}")
            log_error("Error loading advising selections", e)
    else:
        st.session_state.advising_selections = {}

# ---- Persist to Drive (unchanged) ----
def save_data_to_drive():
    files = {
        "courses_table.xlsx": st.session_state.courses_df,
        "progress_report.xlsx": st.session_state.progress_df,
        "advising_selections.xlsx": pd.DataFrame(
            [
                {
                    "ID": sid,
                    "Advised": ", ".join(sel.get("advised", [])),
                    "Optional": ", ".join(sel.get("optional", [])),
                    "Note": sel.get("note", ""),
                }
                for sid, sel in st.session_state.advising_selections.items()
            ]
        ),
    }
    for name, df in files.items():
        if df is None or (isinstance(df, pd.DataFrame) and df.empty and name != "advising_selections.xlsx"):
            continue
        buf = BytesIO()
        df.to_excel(buf, index=False)
        sync_file_with_drive(
            service=service,
            file_content=buf.getvalue(),
            drive_file_name=name,
            mime_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            parent_folder_id=st.secrets["google"]["folder_id"],
        )
        st.toast(f"Synced {name} to Google Drive")

# ---- Initialize session state ----
if "courses_df" not in st.session_state:
    st.session_state.courses_df = pd.DataFrame()
if "progress_df" not in st.session_state:
    st.session_state.progress_df = pd.DataFrame()
if "advising_selections" not in st.session_state:
    st.session_state.advising_selections = {}
if "data_uploaded" not in st.session_state:
    st.session_state.data_uploaded = False

# ---- UI ----
load_data_from_drive()
upload_data()

if st.session_state.get("data_uploaded", False):
    save_data_to_drive()
    st.session_state.data_uploaded = False

if not st.session_state.progress_df.empty and not st.session_state.courses_df.empty:
    tab1, tab2 = st.tabs(["Student Eligibility View", "Full Student View"])
    with tab1:
        student_eligibility_view()
    with tab2:
        full_student_view()
else:
    st.info("📝 Please upload both the progress report and courses table to continue.")
