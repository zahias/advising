# Advising Dashboard

## Overview
The Advising Dashboard is a Streamlit-based application designed for Phoenix University academic advisors. Its core purpose is to streamline the academic advising process by providing tools for tracking student progress, checking course eligibility, managing advising sessions, and syncing data with Google Drive. The dashboard supports multiple majors (PBHL, SPTH-New, SPTH-Old) and aims to offer a comprehensive, user-friendly platform for academic guidance, including advanced features like a Course Offering Planner for optimized course recommendations.

## Recent Changes
- **2025-12-04**:
  - Added **Requisite Bypass Feature** - Advisors can now grant bypasses to allow students to register for courses without meeting prerequisites:
    - Bypass UI in Student Eligibility View: Grant bypass with optional reason/note, see active bypasses, remove bypasses
    - Bypassed courses show as "Eligible (Bypass)" with purple highlighting
    - Bypasses persist with advising sessions (per-student, per-advising-period)
    - Full Student View shows `b` status code for bypassed courses
    - Excel exports include bypass information with advisor name and notes
    - Backward compatible: existing sessions without bypass data load correctly
  - Fixed **circular import / segmentation fault** on Streamlit Cloud (Python 3.13):
    - Created `eligibility_utils.py` module containing all eligibility logic (check_eligibility, get_mutual_concurrent_pairs) with no Streamlit dependencies
    - Refactored ALL modules to use lazy loading for Google Drive functions via `_get_drive_module()`, preventing import-time side effects:
      - `advising_history.py`, `app.py`, `full_student_view.py`, `course_exclusions.py`, `data_upload.py`, `email_manager.py`, `advising_period.py`
    - Updated `utils.py` to import from eligibility_utils for backward compatibility
    - Added `runtime.txt` with `python-3.11` to pin Python version on Streamlit Cloud
  - Fixed pandas `combine_first` FutureWarning by handling empty entries before concatenation
  - Fixed **mutual concurrent/corequisite pairs** eligibility issue. Previously, if Course A required Course B as concurrent AND Course B required Course A, both would show as "Not Eligible" (chicken-and-egg problem). Now the system:
    - Detects mutual concurrent/corequisite pairs automatically via `get_mutual_concurrent_pairs()`
    - Shows both courses as "Eligible" with note "Must be taken with: [paired course]"
    - Allows advisors to select and advise both courses together
- **2025-11-07**: 
  - Replaced static REQUISITES and SUMMARY sections with clean tooltips on course column headers. Hovering over any course column now shows the course prerequisites and summary statistics (completion rates, registration counts).
  - Removed REQUISITES and SUMMARY rows from Excel exports for cleaner, student-data-only downloads.
  - Added **Degree Plan** tab to Full Student View showing all students' progress on the degree plan grid organized by suggested semester structure.

- **2025-12-09**:
  - Removed Course Projection View feature to simplify codebase
  - **Major performance optimizations** to fix slow loading and crashes:
    - Added session-state caching for advising index (`_load_index()`) - now only downloads from Drive once per major per session
    - Added caching for period history (`get_all_periods()`) - eliminates redundant Drive calls on every page load
    - Save operations now update cache immediately without re-downloading
    - Updated Streamlit API across 6 files (22 occurrences) from deprecated `use_container_width=True` to `width="stretch"` for Streamlit >=1.40.0
    - Added `_get_fsv_cache()` helper to cache expensive Full Student View calculations (mutual_pairs, curriculum_years, coreq_concurrent_courses)
  - Added manual "Sync from Drive" button in Session Management section for force-refreshing data when modified elsewhere
  - Pinned Python to 3.10 in `runtime.txt` for deployment stability
  - Added automatic date/time stamps to advising period names (format: "Dec 04, 09:23")
  - **Fixed prerequisite logic**: Advised/optional courses now only satisfy concurrent and corequisite requirements, NOT prerequisites. This matches real academic rules where prerequisites must be completed before taking a course.
  - **Schedule Conflict Insights**: New section in Course Offering Planner that analyzes advised courses (excluding optional) across all students to identify course pairs that should not conflict in the schedule. Includes:
    - Automatic detection of course pairs being taken together by students
    - Filterable table with student counts and names per pair
    - Flags for corequisite/concurrent relationships
    - CSV export functionality
    - Automatic cache invalidation when advising data changes

## User Preferences
I prefer:
- Simple, direct language in explanations.
- Iterative development with clear communication at each stage.
- To be asked before any major changes are implemented.
- The agent to prioritize functional completeness over minor optimizations.
- Do not make changes to files outside of the core application logic (e.g., `get_refresh_token.py`, `.streamlit/config.toml`).
- Do not modify the deployment configuration unless explicitly requested.

## System Architecture

### UI/UX Decisions
The dashboard features a modern, accessible design adhering to WCAG AA standards, including keyboard navigation and mobile responsiveness. A mandatory advising period selection gate precedes all functionality. The interface includes a simple student selection dropdown, a stepwise accordion-style data upload with inline validation, and a unified notification system. The sidebar is minimized by default, and inline action buttons are used for efficiency.

### Technical Implementations
Built with Streamlit in Python 3.11, the application leverages Pandas for data manipulation, especially with Excel files. It integrates with the Google Drive API for optional cloud storage and synchronization, and uses standard Python SMTP for Outlook/Office 365 email functionality, including HTML templates and per-major rosters. The system supports multi-major data tracking, automated course eligibility checks, and persistent advising sessions.

### Feature Specifications
- **Multi-Major Support**: Manages data and configurations for PBHL, SPTH-New, SPTH-Old.
- **Course Eligibility**: Automated checks against prerequisites, corequisites, concurrent requirements, and student standing. Includes **Requisite Bypass** feature allowing advisors to grant exceptions for individual students.
- **Student Views**: Offers "Student Eligibility View" (courses a student can take) and "Full Student View" (complete progress tracking with semester filtering and course requisites display).
- **Course Offering Planner**: A smart recommendation engine that prioritizes courses based on graduating students (remaining credits), bottleneck analysis, currently eligible students, and cascading eligibility effects. It uses a weighted priority scoring system and provides Top 10 recommendations with visual indicators, interactive selection, and impact summaries.
- **Advising Sessions**: Records and persists advisor recommendations and notes, synchronized with Google Drive.
- **Email Integration**: Sends formatted advising sheets directly to students via Outlook/Office 365.
- **Data Upload**: A validated, stepwise interface for `courses_table.xlsx`, `progress_report.xlsx`, and email rosters, with integrated template download buttons.
- **Advising Periods**: Tracks advising cycles per major, allowing for archiving of past sessions and creating new periods.
- **Degree Plan View**: Displays a semester-by-semester curriculum grid based on the official degree plan, color-coding student progress (completed, registered, available, not eligible, failed).

### System Design Choices
- **File Organization**: Google Drive uses a major-specific folder hierarchy (`{ROOT}/{MAJOR}/`) for all related files, with sessions stored in `{ROOT}/{MAJOR}/sessions/`.
- **Period Tracking**: Advising periods are tracked per major, with current period metadata in `current_period.json` and historical data in `periods_history.json`.
- **Data Storage**: Advising sessions are saved locally for responsiveness, then asynchronously synced to Google Drive.
- **Security**: Sensitive credentials are managed via Replit Secrets and excluded from version control.

## External Dependencies

- **Google Drive API**: Used for cloud backup, data synchronization, and major-specific file organization. Configured via secrets (`GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REFRESH_TOKEN`, `GOOGLE_FOLDER_ID`).
- **Outlook/Office 365 SMTP**: Used for sending advising emails. Configured via secrets (`email.address`, `email.password`).
- **Streamlit**: The primary web framework.
- **Pandas**: Used for data manipulation, especially with Excel files.
- **openpyxl**: Used for reading and writing Excel files.
- **Pillow**: Used for image handling (e.g., `pu_logo.png`).