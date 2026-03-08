const rawBase = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'
export const API_BASE_URL = rawBase.startsWith('http') ? rawBase : `https://${rawBase}`

export type CurrentUser = {
  id: number
  email: string
  full_name: string
  role: 'admin' | 'adviser'
  major_codes: string[]
}

export type Major = {
  id: number
  code: string
  name: string
  is_active: boolean
}

export type DashboardMetrics = {
  total_students: number
  advised_students: number
  not_advised_students: number
  progress_percent: number
  graduating_soon_unadvised: string[]
  recent_activity: { student_name: string; created_at: string }[]
}

export type CourseOfferingRecommendation = {
  course: string
  priority_score: number
  currently_eligible: number
  graduating_students: number
  bottleneck_score: number
  cascading_eligible: number
  reason: string
}

export type StudentSearchItem = {
  student_id: string
  student_name: string
  standing: string
  total_credits: number
  remaining_credits: number
}

export type CourseCatalogItem = {
  course_code: string
  title: string
  course_type: string
  credits: number
  offered: boolean
}

export type SelectionPayload = {
  advised: string[]
  optional: string[]
  repeat: string[]
  note: string
}

export type EligibilityCourse = {
  course_code: string
  title: string
  course_type: string
  requisites: string
  eligibility_status: string
  justification: string
  offered: boolean
  completed: boolean
  registered: boolean
  action: string
}

export type StudentEligibility = {
  student_id: string
  student_name: string
  standing: string
  credits_completed: number
  credits_registered: number
  credits_remaining: number
  advised_credits: number
  optional_credits: number
  repeat_credits: number
  eligibility: EligibilityCourse[]
  selection: SelectionPayload
  bypasses: Record<string, { note: string; advisor: string }>
  hidden_courses: string[]
  excluded_courses: string[]
}

export type DatasetVersion = {
  id: number
  major_id: number
  dataset_type: string
  version_label: string
  original_filename: string | null
  is_active: boolean
  metadata_json: Record<string, unknown>
  created_at: string
}

export type Period = {
  id: number
  major_id: number
  period_code: string
  semester: string
  year: number
  advisor_name: string
  is_active: boolean
}

export type AppTemplate = {
  id: number
  major_id: number | null
  template_key: string
  display_name: string
  description: string
  subject_template: string
  body_template: string
  include_summary: boolean
}

export type SessionSummary = {
  id: number
  title: string
  student_id: string
  student_name: string
  created_at: string
  summary: Record<string, unknown>
}

export type ExclusionSummary = {
  student_id: string
  student_name: string
  course_codes: string[]
}

export type TemplatePreview = {
  template_key: string
  subject: string
  preview_body: string
  variables: Record<string, string | null>
}

export type UserRecord = {
  id: number
  email: string
  full_name: string
  role: string
  is_active: boolean
  created_at: string
}

export type BackupRun = {
  id: number
  status: string
  storage_key: string | null
  manifest: Record<string, unknown>
  notes: string | null
  created_at: string
}

export type AllStudentsRow = {
  student_id: string
  student_name: string
  standing: string
  total_credits: number
  remaining_credits: number
  advising_status: string
  courses: Record<string, string>
}

export type AllStudentsCourseMeta = {
  course_code: string
  title: string
  course_type: string
  credits: number
  requisites: string
  suggested_semester: string
}

export type AllStudentsInsightsResponse = {
  rows: AllStudentsRow[]
  required_courses: string[]
  intensive_courses: string[]
  course_metadata: Record<string, AllStudentsCourseMeta>
  simulation_options: string[]
  semester_options: string[]
  legend: { code: string; label: string }[]
  remaining_range: { min: number; max: number }
  simulated_courses: string[]
}

export type IndividualStudentInsight = {
  student_id: string
  student_name: string
  selected_courses: string[]
  statuses: Record<string, string>
  advised: string[]
  optional: string[]
  repeat: string[]
  note: string
}

export type QAARow = {
  course_code: string
  course_name: string
  eligibility: number
  advised: number
  optional: number
  not_advised: number
  skipped_advising: number
  attended_graduating: number
  skipped_graduating: number
}

export type ScheduleConflictRow = {
  group_name: string
  student_count: number
  course_count: number
  courses: string[]
  student_ids: string[]
  students_processed: number
}

export type DegreePlanCourse = {
  code: string
  title: string
  credits: number
  semester: string
  year: string
  status: string
}

export type DegreePlanSemester = {
  semester_key: string
  total_credits: number
  courses: DegreePlanCourse[]
}

export type DegreePlanYear = {
  year_name: string
  semesters: DegreePlanSemester[]
}

export type DegreePlanResponse = {
  student: {
    student_id: string
    student_name: string
    standing: string
    remaining_credits: number
  } | null
  legend: { status: string; label: string; icon: string }[]
  years: DegreePlanYear[]
}

export type PlannerSelectionState = {
  selected_courses: string[]
  graduation_threshold: number
  min_eligible_students: number
  total_eligible: number
  total_graduating: number
  saved_at: string | null
}

export async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const token = window.localStorage.getItem('advising_v2_token')
  const response = await fetch(`${API_BASE_URL}/api${path}`, {
    ...init,
    headers: {
      ...(init?.headers || {}),
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
  })
  if (!response.ok) {
    const text = await response.text()
    throw new Error(text || `Request failed: ${response.status}`)
  }
  const contentType = response.headers.get('content-type') || ''
  if (contentType.includes('application/json')) {
    return (await response.json()) as T
  }
  return (await response.blob()) as T
}

export async function login(email: string, password: string) {
  return apiFetch<{ access_token: string }>('/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  })
}
