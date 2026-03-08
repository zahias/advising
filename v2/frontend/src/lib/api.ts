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

export type StudentSearchItem = {
  student_id: string
  student_name: string
  standing: string
  total_credits: number
  remaining_credits: number
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
