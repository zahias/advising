# Advising Dashboard

## Overview
This is a **Streamlit-based Advising Dashboard** for Phoenix University that helps academic advisors track student progress and course eligibility across multiple majors (PBHL, SPTH-New, SPTH-Old).

**Purpose**: Enable advisors to:
- View student course completion and registration status
- Check course eligibility based on prerequisites and standing
- Manage advising sessions and recommendations per major
- Sync data with Google Drive for backup and collaboration

**Current State**: ✅ Fully functional and ready to use
- Python 3.11 environment configured
- All dependencies installed
- Streamlit running on port 5000
- Deployment configured for production

---

## Recent Changes

### 2025-10-24: Email Integration for Advising Sheets
- ✅ **Outlook/Office 365 SMTP**: Integrated email sending using university Outlook accounts via standard Python SMTP
- ✅ **Email Roster Management**: Upload Excel/CSV files with student IDs and emails, stored per major in Drive
- ✅ **Send Advising Sheets**: Email formatted advising sheets directly to students from both Eligibility and Full Student views
- ✅ **HTML Email Templates**: Professional HTML emails with course details, advisor notes, and plain text fallback
- ✅ **Portable Design**: Works on both Replit and Streamlit Cloud using environment variables/secrets
- ✅ **Per-Major Email Rosters**: Email rosters are isolated per major to prevent cross-major email errors

### 2025-10-24: Major-Specific Folder Structure
- ✅ **Folder Hierarchy**: Reorganized Google Drive to use major-specific folders (`{ROOT}/PBHL/`, `{ROOT}/SPTH-New/`, `{ROOT}/SPTH-Old/`)
- ✅ **File Organization**: Files now organized by folder instead of filename prefix (e.g., `PBHL/courses_table.xlsx` instead of `PBHL_courses_table.xlsx`)
- ✅ **No More Duplicates**: Removed versioned backups - uploads now replace existing files instead of creating timestamped duplicates
- ✅ **Persistent Sessions**: Advising sessions save to major-specific folders and persist across file uploads and page refreshes
- ✅ **Automated Folders**: Major folders are created automatically on first use

### 2025-10-24: Performance Optimizations & Bug Fixes
- ✅ **Drive Performance**: Implemented service caching and file download caching to eliminate redundant API calls
- ✅ **Autoload Fixed**: Files now automatically load from Drive when available for each major
- ✅ **SSL Retry Logic**: Added 3-attempt retry with 2-second delays for intermittent SSL errors during uploads
- ✅ **Secrets Safety**: Fixed crashes when Drive isn't configured - app now gracefully handles missing secrets
- ✅ **Local-First Sessions**: Advising sessions save instantly to local cache, then sync to Drive in background

### 2025-10-24: Initial Replit Setup
- ✅ Installed Python 3.11 and all required packages
- ✅ Configured Streamlit for Replit environment (0.0.0.0:5000, CORS disabled)
- ✅ Fixed Google secrets handling to be optional (app works without Drive)
- ✅ Updated .gitignore to preserve config while excluding secrets
- ✅ Configured autoscale deployment for production
- ✅ Verified app runs successfully with all features

---

## Project Architecture

### Technology Stack
- **Framework**: Streamlit (Python web framework for data apps)
- **Data**: Pandas, openpyxl for Excel file handling
- **Cloud Integration**: Google Drive API (optional)
- **Deployment**: Replit autoscale deployment

### File Structure
```
.
├── app.py                    # Main application entry point
├── advising_history.py       # Advising sessions management
├── course_exclusions.py      # Course exclusion logic
├── data_upload.py            # File upload and Drive sync
├── eligibility_view.py       # Student eligibility checking
├── email_manager.py          # Email roster and Outlook SMTP integration
├── full_student_view.py      # Complete student dashboard
├── get_refresh_token.py      # Google OAuth helper
├── google_drive.py           # Google Drive API integration
├── reporting.py              # Reporting utilities
├── utils.py                  # Shared utilities
├── requirements.txt          # Python dependencies
├── pu_logo.png              # University logo
├── .streamlit/
│   └── config.toml          # Streamlit configuration (port 5000, CORS settings)
└── .gitignore               # Git ignore rules
```

### Key Features
1. **Multi-Major Support**: Track data separately for PBHL, SPTH-New, SPTH-Old
2. **Course Eligibility**: Automatic checking based on prerequisites, corequisites, concurrent requirements, and student standing
3. **Google Drive Sync**: Optional cloud backup with major-specific folder organization
4. **Student Views**: 
   - Eligibility view (which courses students can take)
   - Full student view (complete progress tracking)
5. **Advising Sessions**: Track advisor recommendations and notes per student (persists across sessions)
6. **Email Integration**: Send formatted advising sheets to students via Outlook/Office 365 with HTML email templates

---

## Configuration

### Streamlit Configuration
Location: `.streamlit/config.toml`
- Server bound to `0.0.0.0:5000` (required for Replit)
- CORS and XSRF protection disabled for iframe compatibility
- Headless mode enabled

### Google Drive Integration (Optional)
The app can sync with Google Drive for data backup and collaboration. To enable:

1. **Create Google Cloud Project** with Drive API enabled
2. **Generate OAuth credentials** (client_id, client_secret)
3. **Get refresh token** using `get_refresh_token.py`
4. **Add to Replit Secrets** (use the Secrets tab 🔒 in Replit sidebar):
   - `GOOGLE_CLIENT_ID` = your-client-id
   - `GOOGLE_CLIENT_SECRET` = your-client-secret
   - `GOOGLE_REFRESH_TOKEN` = your-refresh-token
   - `GOOGLE_FOLDER_ID` = your-root-drive-folder-id

**Folder Structure**: The app automatically creates major-specific subfolders:
```
{ROOT_FOLDER}/
├── PBHL/
│   ├── courses_table.xlsx
│   ├── progress_report.xlsx
│   ├── exclusions.json
│   ├── advising_index.json
│   └── advising_session_{id}.json
├── SPTH-New/
│   └── (same structure)
└── SPTH-Old/
    └── (same structure)
```

**Important**: 
- The app works perfectly without Google Drive - you can upload files directly through the sidebar
- Files uploaded to Drive replace existing versions (no duplicates or backups)
- Advising sessions are automatically saved to major-specific folders

### Email Integration (Optional)
The app can send advising sheets to students via Outlook/Office 365 SMTP. To enable:

1. **Generate App Password** for your university Outlook account:
   - Go to [Microsoft Account Security](https://account.microsoft.com/security)
   - Select "App passwords" under "Additional security options"
   - Generate a new app password for "Advising Dashboard"
   
2. **Add to Secrets** (works on both Replit and Streamlit Cloud):
   ```toml
   [email]
   address = "your-email@university.edu"
   password = "your-app-password"
   ```
   - **On Replit**: Add to Secrets in Tools sidebar (🔒)
   - **On Streamlit Cloud**: Add to Secrets in app Settings

3. **Upload Email Roster** for each major:
   - Prepare Excel/CSV file with columns: `ID` and `Email`
   - Upload via sidebar under "📧 Email Roster"
   - Rosters are stored per major in Drive (e.g., `PBHL/email_roster.json`)

**Features:**
- Send formatted advising sheets with course recommendations
- Professional HTML emails with plain text fallback
- Per-major email rosters (prevents cross-major email errors)
- Email directly from Eligibility View or Full Student View

**Important**:
- Use Outlook/Office 365 app password, NOT your regular password
- Email rosters are isolated per major for data safety
- App works without email - it's completely optional

---

## How to Use

### Running Locally
The app starts automatically via the Streamlit workflow. Access it through the web preview.

### Uploading Data
1. **Select a major** from the dropdown (PBHL, SPTH-New, SPTH-Old)
2. **Upload files** via the sidebar:
   - Courses Table: `courses_table.xlsx`
   - Progress Report: `progress_report.xlsx` (can have Required + Intensive sheets)
   - Advising Selections: Optional CSV/XLSX with advisor recommendations

**Note**: Files are stored in major-specific folders on Google Drive (e.g., `PBHL/courses_table.xlsx`). When you upload a new file, it replaces the existing version - no duplicates are created.

### Data Format Requirements
**Courses Table** should include columns:
- Course Code
- Offered (Yes/No)
- Prerequisite
- Concurrent
- Corequisite

**Progress Report** should include:
- ID, NAME
- Course code columns (values: 'c' = completed, 'nc' = not completed, blank = registered)
- # of Credits Completed
- # Registered
- # Remaining
- Total Credits

---

## Dependencies
See `requirements.txt` for full list:
- streamlit
- pandas
- openpyxl (Excel support)
- pillow (image handling)
- google-auth, google-auth-oauthlib, google-api-python-client (Drive integration)

---

## Deployment
Configured for **autoscale deployment** - the app scales automatically based on traffic.

To publish:
1. Click the "Deploy" button in Replit
2. Your app will be available at a public URL
3. Configure secrets in the deployment settings if using Google Drive

---

## Security Notes
- ✅ Secrets stored in Replit Secrets (not in code)
- ✅ `.gitignore` configured to exclude sensitive files
- ✅ Google credentials never exposed in logs or UI
- ⚠️ **Never share API credentials in chat or commit them to git**

---

## Support & Troubleshooting

### App won't start
- Check that all Python packages are installed: `pip install -r requirements.txt`
- Verify workflow is running in the Replit sidebar

### Google Drive not working
- App still works without Drive - you can upload files locally
- If you want Drive sync, check that all 4 secrets are configured correctly
- Run `get_refresh_token.py` to regenerate refresh token if expired

### Data not loading
- Ensure Excel files match the expected format and column names
- Check for file upload errors in the sidebar messages
- Verify files are uploaded with the correct base names (`courses_table.xlsx`, `progress_report.xlsx`)
- If using Google Drive, check that the major-specific folders were created correctly
