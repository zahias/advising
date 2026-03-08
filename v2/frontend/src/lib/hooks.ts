import { useQuery } from '@tanstack/react-query'
import { apiFetch, AppTemplate, BackupRun, CurrentUser, DashboardMetrics, DatasetVersion, Major, Period, StudentEligibility, StudentSearchItem, UserRecord } from './api'

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
