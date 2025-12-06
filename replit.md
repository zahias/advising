# Advising Dashboard

## Overview
The Advising Dashboard is a modern web application designed for Phoenix University academic advisors. It is being rebuilt from a Streamlit-based application to a Next.js application with a PostgreSQL database backend. The dashboard streamlines the academic advising process by providing tools for tracking student progress, checking course eligibility, managing advising sessions, and supporting multiple majors (PBHL, SPTH-New, SPTH-Old, NURS).

## Recent Changes
- **2025-12-06** (Wiring & Functionality):
  - **Advisor Courses Page**: Full CRUD operations with dialog-based forms
    - Add, edit, delete courses with validation
    - CSV export functionality
    - PUT/DELETE methods added to /api/courses
  - **Advisor Planner**: Wired to database with proper error handling
    - Saves/loads multi-semester plans to /api/plans
    - Race condition fix: waits for course catalog before hydrating plans
    - Proper API response checking before showing success/error
  - **Advisor Email Page**: Real email sending via nodemailer
    - Personalization tokens: {student_name}, {student_id}, {advisor_name}
    - Email history tracking with status badges
    - Template support for common messages

- **2025-12-06** (Audit & Fixes):
  - **Created Missing Pages**: All sidebar navigation now links to functional pages
    - Admin: /settings (demo UI for system configuration)
    - Advisor: /eligibility, /degree-map, /projections, /planner, /courses, /email
    - Student: /remaining (shows remaining courses by category)
  - **API Improvements**: 
    - /api/courses and /api/students now support filtering by major code (e.g., ?major=PBHL)
    - Both APIs still support majorId (UUID) for full flexibility
  - **UI Components**: Added Switch component for settings toggles
  - **Bug Fixes**:
    - Fixed eligibility page to use GET API with correct data structure
    - Fixed category mapping for "Eligible (Bypass)" and similar statuses
    - Fixed React setState error in LoginPage (moved router.push to useEffect)
    - Fixed student remaining page to use majorId from API response

- **2025-12-06** (Continued):
  - **Eligibility Engine**: Complete TypeScript port with:
    - Prerequisites, corequisites, concurrent requirements
    - Mutual concurrent pair detection (A requires B concurrent AND B requires A)
    - Standing requirements (Senior ≥60 credits, Junior ≥30 credits)
    - Bypass system with advisor name, note, and timestamp
    - Requirement parsing with "and" separator support
  - **API Routes**: Full REST API infrastructure:
    - /api/courses, /api/students, /api/majors, /api/sessions, /api/periods
    - /api/eligibility - Real-time eligibility checking
    - /api/import/courses, /api/import/students - Data import from Excel
    - /api/seed - Sample data for testing
  - **Advisor Session Page**: Functional with:
    - Student and period selection
    - Real-time eligibility checking with color-coded categories
    - Course selection for Advised/Optional/Repeat
    - Bypass granting with dialog
    - Session save functionality
  - **Student Portal**: Secure with proper authentication:
    - Matches student by email or stored ID
    - Shows error state if no match (no fallback to other students)
    - Progress tracking with completed/registered/remaining courses
    - Estimated graduation timeline

- **2025-12-06**:
  - **Major Rebuild**: Started migration from Streamlit to Next.js with TypeScript
  - Created new Next.js project with modern stack:
    - Next.js 15 with App Router
    - TypeScript for type safety
    - Tailwind CSS for styling
    - shadcn/ui component library
    - Drizzle ORM with PostgreSQL database
  - Implemented role-based authentication system (Admin, Advisor, Student)
  - Built comprehensive dashboard layouts

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
│   │   ├── api/
│   │   │   ├── courses/route.ts        # Courses CRUD API
│   │   │   ├── students/route.ts       # Students CRUD API
│   │   │   ├── majors/route.ts         # Majors API
│   │   │   ├── sessions/route.ts       # Advising sessions API
│   │   │   ├── periods/route.ts        # Advising periods API
│   │   │   ├── eligibility/route.ts    # Eligibility check API
│   │   │   ├── import/                 # Data import APIs
│   │   │   │   ├── courses/route.ts
│   │   │   │   └── students/route.ts
│   │   │   └── seed/route.ts           # Sample data seeding
│   │   └── (dashboard)/
│   │       ├── layout.tsx              # Dashboard layout with sidebar
│   │       ├── admin/                  # Admin pages
│   │       ├── advisor/                # Advisor pages
│   │       └── student/                # Student portal
│   ├── components/
│   │   ├── ui/                         # shadcn/ui components
│   │   └── layout/                     # Layout components
│   └── lib/
│       ├── auth/context.tsx            # Authentication context
│       ├── eligibility/                # Eligibility engine
│       │   ├── index.ts                # Main eligibility logic
│       │   └── types.ts                # TypeScript types
│       └── db/
│           ├── index.ts                # Drizzle database connection
│           └── schema.ts               # Database schema definitions
├── drizzle.config.ts                   # Drizzle configuration
└── package.json
```

#### Database Schema (PostgreSQL)
- **users**: User accounts (admins, advisors) with role and major assignments
- **majors**: Academic programs (PBHL, SPTH-New, SPTH-Old, NURS)
- **courses**: Course catalog with prerequisites, corequisites, concurrent, credits, type
- **students**: Student records with major, credits, standing, courseStatuses (JSON)
- **advising_sessions**: Session records with advisedCourses, optionalCourses, repeatCourses, bypasses
- **advising_periods**: Semester-based advising periods with start/end dates

#### Role Permissions
- **Administrator**: Full access to all majors, users, courses, and settings. Can view as Advisor or Student.
- **Advisor**: Access to assigned majors only. Can manage students and create advising sessions.
- **Student**: View-only access to personal progress, advised courses, and degree plan.

#### Eligibility Logic (Critical Thresholds)
- **Senior**: ≥60 credits
- **Junior**: ≥30 credits
- **Sophomore**: ≥15 credits
- **Freshman**: <15 credits

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
| Admin dashboard | - | ✅ | Complete (UI) |
| Course manager | ✅ | ✅ | Complete (UI + API) |
| Student manager | ✅ | ✅ | Complete (UI + API) |
| Advisor dashboard | ✅ | ✅ | Complete |
| Advising session | ✅ | ✅ | **Complete (functional)** |
| Eligibility check | ✅ | ✅ | **Complete** |
| Student portal | - | ✅ | **Complete (with auth)** |
| Data import | ✅ | ✅ | **Complete** |
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
