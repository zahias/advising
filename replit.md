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
3. **Google Drive Sync**: Optional cloud backup with versioning
4. **Student Views**: 
   - Eligibility view (which courses students can take)
   - Full student view (complete progress tracking)
5. **Advising Sessions**: Track advisor recommendations and notes per student

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
4. **Add to Replit Secrets** (use the Secrets tab in Replit sidebar):
   ```toml
   [google]
   client_id = "your-client-id"
   client_secret = "your-client-secret"
   refresh_token = "your-refresh-token"
   folder_id = "your-drive-folder-id"
   ```

**Important**: The app works perfectly without Google Drive - you can upload files directly through the sidebar.

---

## How to Use

### Running Locally
The app starts automatically via the Streamlit workflow. Access it through the web preview.

### Uploading Data
1. **Select a major** from the dropdown (PBHL, SPTH-New, SPTH-Old)
2. **Upload files** via the sidebar:
   - Courses Table: `{MAJOR}_courses_table.xlsx`
   - Progress Report: `{MAJOR}_progress_report.xlsx` (can have Required + Intensive sheets)
   - Advising Selections: Optional CSV/XLSX with advisor recommendations

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
- Verify the major-specific filenames (e.g., `PBHL_courses_table.xlsx`)
