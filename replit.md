# Advising Dashboard

## Overview
The Advising Dashboard is a modern web application designed for Phoenix University academic advisors. It is being rebuilt from a Streamlit-based application to a Next.js application with a PostgreSQL database backend. The dashboard streamlines the academic advising process by providing tools for tracking student progress, checking course eligibility, managing advising sessions, and supporting multiple majors (PBHL, SPTH-New, SPTH-Old, NURS).

## Recent Changes
- **2025-12-06**:
  - **Major Rebuild**: Started migration from Streamlit to Next.js with TypeScript
  - Created new Next.js project with modern stack:
    - Next.js 15 with App Router
    - TypeScript for type safety
    - Tailwind CSS for styling
    - shadcn/ui component library
    - Drizzle ORM with PostgreSQL database
  - Implemented role-based authentication system (Admin, Advisor, Student)
  - Built comprehensive dashboard layouts:
    - **Admin Dashboard**: Overview stats, user management, course management, major management, student management
    - **Advisor Dashboard**: Student list, eligibility view, advising session interface with course selection
    - **Student Portal**: Progress tracking, advised courses, degree plan view
  - Created reusable UI components: sidebar navigation, header with major selector, role switcher

- **2025-12-04** (Legacy Streamlit):
  - Added Requisite Bypass Feature
  - Fixed circular import issues
  - Fixed mutual concurrent/corequisite pairs eligibility

## User Preferences
I prefer:
- Simple, direct language in explanations.
- Iterative development with clear communication at each stage.
- To be asked before any major changes are implemented.
- The agent to prioritize functional completeness over minor optimizations.
- Do not make changes to files outside of the core application logic.
- Do not modify the deployment configuration unless explicitly requested.

## System Architecture

### New Next.js Application (`advising-dashboard-next/`)

#### Tech Stack
- **Framework**: Next.js 15 with App Router and TypeScript
- **UI**: Tailwind CSS + shadcn/ui component library
- **Database**: PostgreSQL with Drizzle ORM
- **Authentication**: Role-based (Admin, Advisor, Student) - demo mode with planned Microsoft 365 SSO
- **Deployment Target**: A2 Hosting (future)

#### Directory Structure
```
advising-dashboard-next/
├── src/
│   ├── app/
│   │   ├── page.tsx                    # Login page with role selector
│   │   ├── layout.tsx                  # Root layout with AuthProvider
│   │   └── (dashboard)/
│   │       ├── layout.tsx              # Dashboard layout with sidebar
│   │       ├── admin/
│   │       │   ├── page.tsx            # Admin overview dashboard
│   │       │   ├── courses/page.tsx    # Course manager
│   │       │   ├── students/page.tsx   # Student manager
│   │       │   ├── users/page.tsx      # User/advisor manager
│   │       │   └── majors/page.tsx     # Major configuration
│   │       ├── advisor/
│   │       │   ├── page.tsx            # Advisor dashboard
│   │       │   ├── students/page.tsx   # Student list
│   │       │   └── session/page.tsx    # Advising session interface
│   │       └── student/
│   │           ├── page.tsx            # Student dashboard
│   │           ├── progress/page.tsx   # Progress tracking
│   │           ├── advised/page.tsx    # Advised courses history
│   │           └── degree-plan/page.tsx # Degree plan view
│   ├── components/
│   │   ├── ui/                         # shadcn/ui components
│   │   └── layout/
│   │       ├── app-sidebar.tsx         # Navigation sidebar
│   │       └── header.tsx              # Header with major selector
│   └── lib/
│       ├── auth/context.tsx            # Authentication context
│       └── db/
│           ├── index.ts                # Drizzle database connection
│           └── schema.ts               # Database schema definitions
├── drizzle.config.ts                   # Drizzle configuration
└── package.json
```

#### Database Schema (PostgreSQL)
- **users**: User accounts (admins, advisors) with role and major assignments
- **majors**: Academic programs (PBHL, SPTH-New, SPTH-Old, NURS)
- **courses**: Course catalog with prerequisites, credits, type
- **students**: Student records with major, credits, standing
- **student_courses**: Student-course relationships (completed, registered, etc.)
- **advising_sessions**: Advising session records with notes
- **advising_periods**: Semester-based advising periods

#### Role Permissions
- **Administrator**: Full access to all majors, users, courses, and settings. Can view as Advisor or Student.
- **Advisor**: Access to assigned majors only. Can manage students and create advising sessions.
- **Student**: View-only access to personal progress, advised courses, and degree plan.

### Legacy Streamlit Application (Python)
The original Streamlit application files remain in the root directory for reference during migration:
- `app.py` - Main Streamlit application
- `eligibility_utils.py` - Course eligibility logic
- `full_student_view.py` - Student progress views
- `course_projection_view.py` - Graduation projection
- `advising_history.py` - Session management

## Feature Migration Status

| Feature | Streamlit | Next.js | Status |
|---------|-----------|---------|--------|
| Role-based auth | - | ✅ | Complete (demo mode) |
| Admin dashboard | - | ✅ | Complete |
| Course manager | ✅ | ✅ | Complete (UI only) |
| Student manager | ✅ | ✅ | Complete (UI only) |
| Advisor dashboard | ✅ | ✅ | Complete |
| Advising session | ✅ | ✅ | Complete (UI only) |
| Student portal | - | ✅ | Complete |
| Eligibility check | ✅ | 🔄 | Pending migration |
| Degree map | ✅ | 🔄 | Planned redesign |
| Course projection | ✅ | 🔄 | Planned as Semester Timeline |
| Email integration | ✅ | 🔄 | Pending |
| Microsoft 365 SSO | - | 🔄 | Pending IT approval |

## External Dependencies

### New Application
- **PostgreSQL**: Replit-managed database (via DATABASE_URL)
- **Microsoft 365**: Planned for SSO authentication
- **SMTP**: Planned for email notifications

### Legacy Application
- **Google Drive API**: Cloud backup and sync (being deprecated)
- **Outlook/Office 365 SMTP**: Email functionality
- **Streamlit**: Python web framework
- **Pandas/openpyxl**: Excel file handling
