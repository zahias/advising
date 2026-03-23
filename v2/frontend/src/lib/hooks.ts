import { useQuery } from '@tanstack/react-query'
import { apiFetch, AppTemplate, AssignmentTypes, AuditEventRecord, BackupRun, CourseCatalogItem, CourseAssignment, CourseEquivalent, CurrentUser, DashboardMetrics, DatasetVersion, ExclusionSummary, Major, Period, ProgressReport, SessionSummary, StalenessInfo, StudentEligibility, StudentSearchItem, UserRecord } from './api'

export function useCurrentUser() {
  return useQuery({
    queryKey: ['me'],
    queryFn: () => apiFetch<CurrentUser>('/auth/me'),
    retry: false,
  })
}

export function useMajors() {
  return useQuery({ queryKey: ['majors'], queryFn: () => apiFetch<Major[]>('/majors') })
}

export function useDashboard(majorCode?: string) {
  return useQuery({
    queryKey: ['dashboard', majorCode],
    queryFn: () => apiFetch<DashboardMetrics>(`/insights/${majorCode}/dashboard`),
    enabled: Boolean(majorCode),
  })
}

export function useStudents(majorCode?: string, query?: string) {
  return useQuery({
    queryKey: ['students', majorCode, query],
    queryFn: () => apiFetch<StudentSearchItem[]>(`/students/${majorCode}/search${query ? `?query=${encodeURIComponent(query)}` : ''}`),
    enabled: Boolean(majorCode),
  })
}

export function useStudentEligibility(majorCode?: string, studentId?: string) {
  return useQuery({
    queryKey: ['student-eligibility', majorCode, studentId],
    queryFn: () => apiFetch<StudentEligibility>(`/students/${majorCode}/${studentId}`),
    enabled: Boolean(majorCode && studentId),
  })
}

export function useCourseCatalog(majorCode?: string) {
  return useQuery({
    queryKey: ['course-catalog', majorCode],
    queryFn: () => apiFetch<CourseCatalogItem[]>(`/students/${majorCode}/catalog`),
    enabled: Boolean(majorCode),
  })
}

export function useDatasetVersions(majorCode?: string) {
  return useQuery({
    queryKey: ['dataset-versions', majorCode],
    queryFn: () => apiFetch<DatasetVersion[]>(`/datasets/${majorCode}`),
    enabled: Boolean(majorCode),
  })
}

export function usePeriods(majorCode?: string) {
  return useQuery({
    queryKey: ['periods', majorCode],
    queryFn: () => apiFetch<Period[]>(`/periods/${majorCode}`),
    enabled: Boolean(majorCode),
  })
}

export function useTemplates(majorCode?: string) {
  return useQuery({
    queryKey: ['templates', majorCode],
    queryFn: () => apiFetch<AppTemplate[]>(`/templates${majorCode ? `?major_code=${encodeURIComponent(majorCode)}` : ''}`),
  })
}

export function useUsers() {
  return useQuery({ queryKey: ['users'], queryFn: () => apiFetch<UserRecord[]>('/users') })
}

export function useBackups() {
  return useQuery({ queryKey: ['backups'], queryFn: () => apiFetch<BackupRun[]>('/backups') })
}

export function useSessions(majorCode?: string, periodCode?: string, studentId?: string) {
  const params = new URLSearchParams()
  if (periodCode) params.set('period_code', periodCode)
  if (studentId) params.set('student_id', studentId)
  const query = params.toString()
  return useQuery({
    queryKey: ['sessions', majorCode, periodCode, studentId],
    queryFn: () => apiFetch<SessionSummary[]>(`/advising/sessions/${majorCode}${query ? `?${query}` : ''}`),
    enabled: Boolean(majorCode),
  })
}

export function useExclusions(majorCode?: string) {
  return useQuery({
    queryKey: ['exclusions', majorCode],
    queryFn: () => apiFetch<ExclusionSummary[]>(`/advising/exclusions/${majorCode}`),
    enabled: Boolean(majorCode),
  })
}

export function useAuditLog(eventType?: string) {
  const params = eventType ? `?event_type=${encodeURIComponent(eventType)}` : ''
  return useQuery({
    queryKey: ['audit-log', eventType],
    queryFn: () => apiFetch<AuditEventRecord[]>(`/audit-events${params}`),
  })
}

export function useStaleness(majorCode?: string) {
  return useQuery({
    queryKey: ['staleness', majorCode],
    queryFn: () => apiFetch<StalenessInfo>(`/progress/${majorCode}/staleness`),
    enabled: Boolean(majorCode),
  })
}

export function useCourseEquivalents(majorCode?: string) {
  return useQuery({
    queryKey: ['course-equivalents', majorCode],
    queryFn: () => apiFetch<CourseEquivalent[]>(`/course-config/${majorCode}/equivalents`),
    enabled: Boolean(majorCode),
  })
}

export function useCourseAssignments(majorCode?: string) {
  return useQuery({
    queryKey: ['course-assignments', majorCode],
    queryFn: () => apiFetch<CourseAssignment[]>(`/course-config/${majorCode}/assignments`),
    enabled: Boolean(majorCode),
  })
}

export function useAssignmentTypes(majorCode?: string) {
  return useQuery({
    queryKey: ['assignment-types', majorCode],
    queryFn: () => apiFetch<AssignmentTypes>(`/course-config/${majorCode}/assignment-types`),
    enabled: Boolean(majorCode),
  })
}

export function useProgressReport(majorCode?: string) {
  return useQuery({
    queryKey: ['progress-report', majorCode],
    queryFn: () => apiFetch<ProgressReport>(`/progress/${majorCode}/report`),
    enabled: Boolean(majorCode),
    staleTime: 60_000,
  })
}
