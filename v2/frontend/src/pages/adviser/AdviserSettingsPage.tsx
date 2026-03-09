import { ChangeEvent, useEffect, useMemo, useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'

import { API_BASE_URL, TemplatePreview } from '../../lib/api'
import { useCourseCatalog, useExclusions, useMajors, usePeriods, useSessions, useStudents, useTemplates } from '../../lib/hooks'

function getSelectedValues(event: ChangeEvent<HTMLSelectElement>) {
  return Array.from(event.target.selectedOptions).map((option) => option.value)
}

async function authedFetch(path: string, init?: RequestInit) {
  const token = window.localStorage.getItem('advising_v2_token')
  return fetch(`${API_BASE_URL}/api${path}`, {
    ...init,
    headers: {
      ...(init?.headers || {}),
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
  })
}

export function AdviserSettingsPage() {
  const queryClient = useQueryClient()
  const [majorCode, setMajorCode] = useState('PBHL')
  const [studentQuery, setStudentQuery] = useState('')
  const [bulkStudentIds, setBulkStudentIds] = useState<string[]>([])
  const [exclusionStudentIds, setExclusionStudentIds] = useState<string[]>([])
  const [exclusionCourses, setExclusionCourses] = useState<string[]>([])
  const [previewStudentId, setPreviewStudentId] = useState('')
  const [templateKey, setTemplateKey] = useState('default')
  const [preview, setPreview] = useState<TemplatePreview | null>(null)
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null)

  const majors = useMajors()
  const periods = usePeriods(majorCode)
  const activePeriod = periods.data?.find((period) => period.is_active)
  const students = useStudents(majorCode, studentQuery)
  const allStudents = useStudents(majorCode, '')
  const exclusions = useExclusions(majorCode)
  const sessions = useSessions(majorCode, activePeriod?.period_code)
  const templates = useTemplates(majorCode)
  const catalog = useCourseCatalog(majorCode)

  useEffect(() => {
    if (!previewStudentId && allStudents.data?.length) {
      setPreviewStudentId(allStudents.data[0].student_id)
    }
  }, [allStudents.data, previewStudentId])

  useEffect(() => {
    if (templates.data?.length && !templates.data.some((item) => item.template_key === templateKey)) {
      setTemplateKey(templates.data[0].template_key)
    }
  }, [templateKey, templates.data])

  const intensiveCourses = useMemo(
    () => catalog.data?.filter((course) => course.course_type.toLowerCase() === 'intensive') ?? [],
    [catalog.data],
  )

  async function runJsonAction(path: string, init?: RequestInit) {
    const response = await authedFetch(path, init)
    const body = await response.text()
    if (!response.ok) {
      setMessage({ type: 'error', text: body || 'Request failed.' })
      return null
    }
    setMessage({
      type: 'success', text: body ? (() => {
        try {
          const parsed = JSON.parse(body)
          return parsed.message || 'Saved.'
        } catch {
          return 'Saved.'
        }
      })() : 'Saved.'
    })
    return body
  }

  async function handleClearSelections() {
    if (!activePeriod) return
    const response = await authedFetch(`/advising/selection/${majorCode}/${activePeriod.period_code}`, { method: 'DELETE' })
    const body = await response.json().catch(() => null)
    if (!response.ok) {
      setMessage({ type: 'error', text: body?.detail || body?.message || 'Clear failed.' })
      return
    }
    setMessage({ type: 'success', text: body?.message || 'Selections cleared.' })
    queryClient.invalidateQueries({ queryKey: ['sessions', majorCode, activePeriod.period_code] })
    queryClient.invalidateQueries({ queryKey: ['dashboard', majorCode] })
  }

  async function handleRestoreAll() {
    if (!activePeriod) return
    await runJsonAction('/advising/sessions/restore-all', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ major_code: majorCode, period_code: activePeriod.period_code }),
    })
    queryClient.invalidateQueries({ queryKey: ['sessions', majorCode, activePeriod.period_code] })
    queryClient.invalidateQueries({ queryKey: ['dashboard', majorCode] })
  }

  async function handleBulkRestore() {
    if (!activePeriod || !bulkStudentIds.length) return
    await runJsonAction('/advising/sessions/bulk-restore', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ major_code: majorCode, period_code: activePeriod.period_code, student_ids: bulkStudentIds }),
    })
    queryClient.invalidateQueries({ queryKey: ['sessions', majorCode, activePeriod.period_code] })
  }

  async function handleSaveExclusions() {
    if (!exclusionStudentIds.length || !exclusionCourses.length) return
    const response = await authedFetch('/advising/exclusions', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ major_code: majorCode, student_ids: exclusionStudentIds, course_codes: exclusionCourses }),
    })
    if (!response.ok) {
      setMessage({ type: 'error', text: await response.text() })
      return
    }
    setMessage({ type: 'success', text: 'Exclusions updated.' })
    queryClient.invalidateQueries({ queryKey: ['exclusions', majorCode] })
  }

  async function handlePreview() {
    if (!previewStudentId) return
    const response = await authedFetch(`/templates/preview?major_code=${encodeURIComponent(majorCode)}&student_id=${encodeURIComponent(previewStudentId)}&template_key=${encodeURIComponent(templateKey)}`)
    const body = await response.json().catch(() => null)
    if (!response.ok) {
      setMessage({ type: 'error', text: body?.detail || 'Preview failed.' })
      return
    }
    setPreview(body)
  }

  return (
    <section className="settings-container stack max-w-5xl mx-auto">
      <div className="page-header flex-between mb-4">
        <div>
          <div className="eyebrow text-muted">Admin & Configuration</div>
          <h2>Adviser Settings</h2>
        </div>
        <div className="header-actions">
          <label className="inline-select">
            <span className="text-muted">Master Program:</span>
            <select className="select-input" value={majorCode} onChange={(event) => setMajorCode(event.target.value)}>
              {majors.data?.map((major) => <option key={major.code}>{major.code}</option>)}
            </select>
          </label>
        </div>
      </div>
      {message && (
        <div className={`alert mb-4 ${message.type === 'error' ? 'alert-error' : 'alert-success'}`}>
          {message.text}
          <button type="button" className="close-btn" onClick={() => setMessage(null)}>&times;</button>
        </div>
      )}

      <div className="grid-3 mb-6">
        <div className="panel stack">
          <h3 className="mb-2">Session Management</h3>
          <p className="text-sm text-muted mb-4">Current period: <strong>{activePeriod ? `${activePeriod.semester} ${activePeriod.year} · ${activePeriod.advisor_name}` : 'No active period'}</strong></p>
          <div className="flex-gap-4 mb-2">
            <button type="button" className="btn-secondary w-full" onClick={handleClearSelections} disabled={!activePeriod}>Clear All Selections</button>
          </div>
          <div className="flex-gap-4">
            <button type="button" className="btn-secondary w-full" onClick={handleRestoreAll} disabled={!activePeriod}>Restore All Sessions</button>
          </div>
          <p className="text-xs text-muted mt-2 border-t pt-2 border-gray-100">Saved sessions in this period: {sessions.data?.length ?? 0}</p>
        </div>
        <div className="panel stack">
          <h3 className="mb-2">Bulk Restore</h3>
          <p className="text-sm text-muted mb-4">Restore prior advising selections for specific students.</p>
          <div className="form-group mb-4">
            <label className="text-muted font-semibold text-xs uppercase tracking-wider mb-2 block">Filter Directory</label>
            <input className="w-full" value={studentQuery} onChange={(event) => setStudentQuery(event.target.value)} placeholder="Name or ID" />
          </div>
          <div className="form-group mb-4">
            <label className="text-muted font-semibold text-xs uppercase tracking-wider mb-2 block">Select Profiles</label>
            <select className="select-input" multiple size={6} value={bulkStudentIds} onChange={(event) => setBulkStudentIds(getSelectedValues(event))}>
              {students.data?.map((student) => <option key={student.student_id} value={student.student_id}>{student.student_name} · {student.student_id}</option>)}
            </select>
          </div>
          <button type="button" className="btn-primary" onClick={handleBulkRestore} disabled={!activePeriod || !bulkStudentIds.length}>Restore Selected</button>
        </div>
        <div className="panel stack bg-gray-50 border border-gray-100">
          <h3 className="mb-2">Runtime Storage</h3>
          <div className="text-sm text-gray-600 space-y-4">
            <p>Drive sync is intentionally removed in the V2 runtime environment.</p>
            <p>Authoritative data lives exclusively in the app database and uploaded raw datasets.</p>
            <p>Legacy import tools remain an admin-only migration action via the CLI.</p>
          </div>
        </div>
      </div>
      <div className="grid-2">
        <div className="panel stack">
          <h3 className="mb-2">Intensive Course Exclusions</h3>
          <p className="text-sm text-muted mb-4">Prevent intensive courses from appearing in specific student templates.</p>
          <div className="grid-2 gap-4 mb-4">
            <div className="form-group">
              <label className="text-muted font-semibold text-xs uppercase tracking-wider mb-2 block">Intensive Courses</label>
              <select className="select-input" multiple size={8} value={exclusionCourses} onChange={(event) => setExclusionCourses(getSelectedValues(event))}>
                {intensiveCourses.map((course) => <option key={course.course_code} value={course.course_code}>{course.course_code} · {course.title}</option>)}
              </select>
            </div>
            <div className="form-group">
              <label className="text-muted font-semibold text-xs uppercase tracking-wider mb-2 block">Target Students</label>
              <select className="select-input" multiple size={8} value={exclusionStudentIds} onChange={(event) => setExclusionStudentIds(getSelectedValues(event))}>
                {allStudents.data?.map((student) => <option key={student.student_id} value={student.student_id}>{student.student_name} · {student.student_id}</option>)}
              </select>
            </div>
          </div>
          <button type="button" className="btn-secondary mb-4" onClick={handleSaveExclusions} disabled={!exclusionCourses.length || !exclusionStudentIds.length}>Save Exclusions</button>

          <div className="premium-table-wrapper max-h-64">
            <table className="premium-table">
              <thead className="sticky top-0 bg-white"><tr><th>Student Profile</th><th>Excluded Course List</th></tr></thead>
              <tbody>
                {exclusions.data?.length === 0 ? (
                  <tr><td colSpan={2} className="text-center p-4 text-muted">No exclusions configured.</td></tr>
                ) : (
                  exclusions.data?.map((item) => <tr key={item.student_id}><td className="font-medium">{item.student_name}</td><td className="text-sm text-muted font-mono">{item.course_codes.join(', ')}</td></tr>)
                )}
              </tbody>
            </table>
          </div>
        </div>
        <div className="panel stack">
          <h3 className="mb-2">Email Template Preview</h3>
          <p className="text-sm text-muted mb-4">Simulate how an advising email template resolves for a specific student.</p>
          <div className="grid-2 gap-4 mb-4">
            <div className="form-group">
              <label className="text-muted font-semibold text-xs uppercase tracking-wider mb-2 block">System Template</label>
              <select className="select-input h-auto p-2" value={templateKey} onChange={(event) => setTemplateKey(event.target.value)}>
                {templates.data?.map((template) => <option key={template.id} value={template.template_key}>{template.display_name}</option>)}
              </select>
            </div>
            <div className="form-group">
              <label className="text-muted font-semibold text-xs uppercase tracking-wider mb-2 block">Simulation Target</label>
              <select className="select-input h-auto p-2" value={previewStudentId} onChange={(event) => setPreviewStudentId(event.target.value)}>
                <option value="">Select student</option>
                {allStudents.data?.map((student) => <option key={student.student_id} value={student.student_id}>{student.student_name}</option>)}
              </select>
            </div>
          </div>
          <button type="button" className="btn-secondary mb-4" onClick={handlePreview} disabled={!previewStudentId}>Generate Preview Runtime</button>

          <div className="bg-gray-50 rounded-lg border p-4">
            {preview ? (
              <div className="stack">
                <div className="form-group">
                  <label className="text-muted font-semibold text-xs uppercase tracking-wider mb-1 block">Resolved Subject Line</label>
                  <input className="w-full font-medium" value={preview.subject} readOnly />
                </div>
                <div className="form-group mt-2">
                  <label className="text-muted font-semibold text-xs uppercase tracking-wider mb-1 block">Resolved HTML Body</label>
                  <div className="bg-white border rounded-lg p-4 font-mono text-sm whitespace-pre-wrap max-h-96 overflow-y-auto" dangerouslySetInnerHTML={{ __html: preview.preview_body }} />
                </div>
              </div>
            ) : <p className="text-muted text-sm text-center py-8">Select a student and template above to compile the preview.</p>}
          </div>
        </div>
      </div>
    </section>
  )
}
