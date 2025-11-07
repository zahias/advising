# Advising Dashboard

## Overview
The Advising Dashboard is a Streamlit-based application designed for Phoenix University academic advisors. Its core purpose is to streamline the academic advising process by providing tools for tracking student progress, checking course eligibility, managing advising sessions, and syncing data with Google Drive. The dashboard supports multiple majors (PBHL, SPTH-New, SPTH-Old) and aims to offer a comprehensive, user-friendly platform for academic guidance, including advanced features like a Course Offering Planner for optimized course recommendations.

## Recent Changes
- **2025-11-07**: 
  - Replaced static REQUISITES and SUMMARY sections with clean tooltips on course column headers. Hovering over any course column now shows the course prerequisites and summary statistics (completion rates, registration counts).
  - Removed REQUISITES and SUMMARY rows from Excel exports for cleaner, student-data-only downloads.
  - Added **Degree Plan** tab to Full Student View showing all students' progress on the degree plan grid organized by suggested semester structure.
  - Implemented **Course Projection View** - a comprehensive semester-by-semester planning tool that projects when each student should take their remaining courses. The system:
    - Calculates earliest possible semester for each course based on prerequisite completion
    - Enforces credit limits (15-17 typical, 18 max per semester)
    - Prioritizes critical path courses (those that block other courses)
    - Identifies flexible courses (non-critical, can be taken in multiple semesters)
    - Displays semester credit summaries with warnings for overloaded semesters
    - Includes cycle detection and memoization for performance and safety
    - Provides Excel export for projection plans

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
- **Course Eligibility**: Automated checks against prerequisites, corequisites, concurrent requirements, and student standing.
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