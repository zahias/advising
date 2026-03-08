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
    setMessage({ type: 'success', text: body ? (() => {
      try {
        const parsed = JSON.parse(body)
        return parsed.message || 'Saved.'
      } catch {
        return 'Saved.'
      }
    })() : 'Saved.' })
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
    <section className="stack">
      <div className="page-header">
        <div>
          <div className="eyebrow">Adviser Interface</div>
          <h2>Settings</h2>
        </div>
        <label>
          <span>Major</span>
          <select value={majorCode} onChange={(event) => setMajorCode(event.target.value)}>
            {majors.data?.map((major) => <option key={major.code}>{major.code}</option>)}
          </select>
        </label>
      </div>
      {message ? <div className={`alert ${message.type === 'error' ? 'error' : ''}`}>{message.text}</div> : null}
      <div className="field-row three-col-layout">
        <div className="panel stack compact-panel">
          <h3>Session management</h3>
          <p>Current period: {activePeriod ? `${activePeriod.semester} ${activePeriod.year} · ${activePeriod.advisor_name}` : 'No active period'}</p>
          <div className="button-row wrap-row">
            <button type="button" onClick={handleClearSelections} disabled={!activePeriod}>Clear all selections</button>
            <button type="button" onClick={handleRestoreAll} disabled={!activePeriod}>Restore all sessions</button>
          </div>
          <p>Saved sessions in this period: {sessions.data?.length ?? 0}</p>
        </div>
        <div className="panel stack compact-panel">
          <h3>Bulk restore</h3>
          <label><span>Filter students</span><input value={studentQuery} onChange={(event) => setStudentQuery(event.target.value)} placeholder="Name or ID" /></label>
          <label>
            <span>Select students to restore</span>
            <select multiple size={10} value={bulkStudentIds} onChange={(event) => setBulkStudentIds(getSelectedValues(event))}>
              {students.data?.map((student) => <option key={student.student_id} value={student.student_id}>{student.student_name} · {student.student_id}</option>)}
            </select>
          </label>
          <button type="button" onClick={handleBulkRestore} disabled={!activePeriod || !bulkStudentIds.length}>Restore selected students</button>
        </div>
        <div className="panel stack compact-panel">
          <h3>Runtime storage</h3>
          <p>Drive sync is intentionally removed in v2 runtime.</p>
          <p>Authoritative data lives in the app database and uploaded datasets.</p>
          <p>Legacy import remains an admin-only migration action.</p>
        </div>
      </div>
      <div className="two-column settings-layout">
        <div className="panel stack">
          <h3>Intensive-course exclusions</h3>
          <div className="field-row">
            <label>
              <span>Courses</span>
              <select multiple size={8} value={exclusionCourses} onChange={(event) => setExclusionCourses(getSelectedValues(event))}>
                {intensiveCourses.map((course) => <option key={course.course_code} value={course.course_code}>{course.course_code} · {course.title}</option>)}
              </select>
            </label>
            <label>
              <span>Students</span>
              <select multiple size={8} value={exclusionStudentIds} onChange={(event) => setExclusionStudentIds(getSelectedValues(event))}>
                {allStudents.data?.map((student) => <option key={student.student_id} value={student.student_id}>{student.student_name} · {student.student_id}</option>)}
              </select>
            </label>
          </div>
          <button type="button" onClick={handleSaveExclusions} disabled={!exclusionCourses.length || !exclusionStudentIds.length}>Save exclusions</button>
          <div className="scroll-table">
            <table>
              <thead><tr><th>Student</th><th>Excluded courses</th></tr></thead>
              <tbody>
                {exclusions.data?.map((item) => <tr key={item.student_id}><td>{item.student_name}</td><td>{item.course_codes.join(', ')}</td></tr>)}
              </tbody>
            </table>
          </div>
        </div>
        <div className="panel stack">
          <h3>Email template preview</h3>
          <div className="field-row">
            <label>
              <span>Template</span>
              <select value={templateKey} onChange={(event) => setTemplateKey(event.target.value)}>
                {templates.data?.map((template) => <option key={template.id} value={template.template_key}>{template.display_name}</option>)}
              </select>
            </label>
            <label>
              <span>Student</span>
              <select value={previewStudentId} onChange={(event) => setPreviewStudentId(event.target.value)}>
                <option value="">Select student</option>
                {allStudents.data?.map((student) => <option key={student.student_id} value={student.student_id}>{student.student_name}</option>)}
              </select>
            </label>
          </div>
          <button type="button" onClick={handlePreview} disabled={!previewStudentId}>Refresh preview</button>
          {preview ? (
            <>
              <label><span>Subject</span><input value={preview.subject} readOnly /></label>
              <div className="code-block">{preview.preview_body}</div>
            </>
          ) : <p>Choose a student and template to preview the outgoing email.</p>}
        </div>
      </div>
    </section>
  )
}
