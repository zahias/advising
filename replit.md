# Advising Dashboard

## Overview
This Streamlit-based Advising Dashboard for Phoenix University assists academic advisors in tracking student progress and course eligibility across multiple majors (PBHL, SPTH-New, SPTH-Old). Its primary purpose is to enable advisors to view student course completion and registration status, check course eligibility based on prerequisites, manage advising sessions, and sync data with Google Drive for backup and collaboration. The project aims to streamline the advising process, providing a comprehensive and user-friendly tool for academic guidance.

## Recent Changes
- **2025-10-31**: Added interactive course selection to Course Planning feature. Users can now select courses to offer and see live eligibility updates assuming eligible students will take those courses. Added credits remaining slider (0-60, default 15) to filter critical path courses by graduation proximity. Fixed Clear Selection button to properly reset checkbox states.
- **2025-10-31**: Fixed critical eligibility calculation bug in full student view where registered courses weren't satisfying prerequisites. The bug was caused by overwriting course column data with status codes during loop processing. Now preserves original progress data using indexed lookups for accurate eligibility calculations.
- **2025-10-31**: Added Course Planning feature with comprehensive semester offering optimization. New "Course Planning" tab analyzes all courses across all students to suggest optimal offerings based on current eligibility, students 1-2 prerequisites away, graduation proximity (remaining credits), and prerequisite chain analysis. Includes priority scoring, bottleneck course identification, critical path analysis, and exportable Excel reports.
- **2025-10-31**: Fixed period persistence bug where sync_file_with_drive() was being called with incorrect parameter order, preventing periods from saving to Google Drive.
- **2025-10-30**: Added mandatory period selection gate. Users must now select or create an advising period before accessing the dashboard. Period selection screen appears immediately after major selection with two options: "Start New Period" or "Use Existing Period". Added "Change Advising Period" button in Advising Utilities for easy period switching. Added debug info panel and Drive save verification to troubleshoot period persistence issues.

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
The dashboard features a modern, accessible design with WCAG AA compliant colors, keyboard navigation, and mobile responsiveness. Before accessing any functionality, users must select or create an advising period via a mandatory selection gate. The dashboard uses a simple dropdown for student selection, a stepwise accordion-style data upload interface with inline validation, and a unified notification system with persistent and toast-style messages. The sidebar is minimized by default for more workspace, and inline action buttons are used for efficiency. A "Change Advising Period" button in Advising Utilities allows users to switch periods at any time.

### Technical Implementations
The application is built using Streamlit in Python 3.11. It utilizes Pandas for data manipulation, particularly with Excel files. Google Drive API is optionally integrated for cloud storage and synchronization. Email functionality is implemented using standard Python SMTP for Outlook/Office 365, supporting HTML email templates and per-major email rosters. The system supports multi-major data tracking, course eligibility checks, and persistent advising sessions.

### Feature Specifications
- **Multi-Major Support**: Handles data and configurations for PBHL, SPTH-New, SPTH-Old.
- **Course Eligibility**: Automated checking against prerequisites, corequisites, concurrent requirements, and student standing.
- **Student Views**: Provides both an "Eligibility view" (courses a student can take) and a "Full student view" (complete progress tracking).
- **Course Planning**: Comprehensive semester planning tool that analyzes optimal course offerings by calculating student eligibility status (currently eligible, 1 prerequisite away, 2+ away), prioritizing students close to graduation, identifying bottleneck courses that unlock many downstream courses, and flagging critical path courses needed to prevent delays. Includes exportable Excel reports with detailed recommendations.
- **Advising Sessions**: Records advisor recommendations and notes, persisting them across sessions and syncing to Drive.
- **Email Integration**: Sends formatted advising sheets directly to students via Outlook/Office 365.
- **Data Upload**: Stepwise, validated interface for `courses_table.xlsx`, `progress_report.xlsx`, and email rosters.
- **Student Selection**: Simple dropdown selector showing student name, ID, and standing.
- **Advising Periods**: Track advising cycles by semester/year/advisor. Starting a new period archives previous sessions and creates a clean slate.
- **Utility Buttons**: Clear All Selections (clears all current advising selections) and Restore Latest Sessions (loads most recent saved sessions from current period for all students).
- **Repeat Courses**: Functionality to mark courses for repeat, displayed as "Advised-Repeat".
- **Period History**: View previous advising periods and browse archived sessions from past semesters.

### System Design Choices
- **File Organization**: Google Drive uses a major-specific folder hierarchy (`{ROOT}/{MAJOR}/`) for all related files (e.g., `courses_table.xlsx`, `advising_index.json`). Sessions are stored in `{ROOT}/{MAJOR}/sessions/` subfolder.
- **Period Tracking**: Each advising period (semester/year/advisor) is tracked per major. Sessions are tagged with period_id. Current period stored in `current_period.json`, historical periods in `periods_history.json`.
- **Data Storage**: Advising sessions are saved locally first for responsiveness, then synced to Google Drive in the background. Each session includes period metadata.
- **Configuration**: Streamlit configuration (`.streamlit/config.toml`) sets server port, disables CORS for iframe compatibility, and minimizes the sidebar.
- **Security**: Sensitive credentials are managed via Replit Secrets, and `.gitignore` excludes them from version control.

## External Dependencies

- **Google Drive API**: Used for optional cloud backup, data synchronization, and major-specific file organization. Requires `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REFRESH_TOKEN`, and `GOOGLE_FOLDER_ID` configured as secrets.
- **Outlook/Office 365 SMTP**: Used for sending advising sheets to students via email. Requires `email.address` and `email.password` (app password) configured as secrets.
- **Streamlit**: Main web framework.
- **Pandas**: For data manipulation, especially with Excel files.
- **openpyxl**: For reading and writing Excel files.
- **Pillow**: For image handling (e.g., `pu_logo.png`).