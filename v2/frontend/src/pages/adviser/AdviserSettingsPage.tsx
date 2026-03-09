import { ChangeEvent, useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'

import { API_BASE_URL, TemplatePreview } from '../../lib/api'
import { useMajors, usePeriods, useSessions, useStudents, useTemplates } from '../../lib/hooks'
import { Tooltip } from '../../components/Tooltip'

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
  const [previewStudentId, setPreviewStudentId] = useState('')
  const [templateKey, setTemplateKey] = useState('default')
  const [preview, setPreview] = useState<TemplatePreview | null>(null)
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null)
  const [expandedStudents, setExpandedStudents] = useState<Set<string>>(new Set())

  const majors = useMajors()
  const periods = usePeriods(majorCode)
  const activePeriod = periods.data?.find((period) => period.is_active)
  const students = useStudents(majorCode, studentQuery)
  const sessions = useSessions(majorCode, activePeriod?.period_code)
  const templates = useTemplates(majorCode)

  // Group sessions by student for the sessions browser
  const sessionsByStudent = sessions.data?.reduce((acc, session) => {
    if (!acc[session.student_id]) {
      acc[session.student_id] = { name: session.student_name, sessions: [] }
    }
    acc[session.student_id].sessions.push(session)
    return acc
  }, {} as Record<string, { name: string; sessions: typeof sessions.data }>) ?? {}

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

  async function handleRestoreSession(_sessionId: number, studentId: string) {
    if (!activePeriod) return
    const response = await authedFetch(`/advising/sessions/${majorCode}/${activePeriod.period_code}/${studentId}/restore`, { method: 'POST' })
    if (!response.ok) {
      setMessage({ type: 'error', text: await response.text() })
      return
    }
    setMessage({ type: 'success', text: 'Session restored.' })
    queryClient.invalidateQueries({ queryKey: ['sessions', majorCode, activePeriod.period_code] })
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

      <div className="grid-2 mb-6">
        {/* Session Management */}
        <div className="panel stack">
          <div className="flex-between mb-2">
            <h3 style={{ margin: 0 }}>Session Management</h3>
          </div>
          <p className="text-sm text-muted mb-4">Active period: <strong>{activePeriod ? `${activePeriod.semester} ${activePeriod.year} · ${activePeriod.advisor_name}` : 'No active period'}</strong></p>
          <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '0.75rem' }}>
            <button type="button" className="btn-secondary" style={{ flex: 1 }} onClick={handleClearSelections} disabled={!activePeriod} title="Remove all saved course selections for all students in the active period">Clear All Selections</button>
            <button type="button" className="btn-secondary" style={{ flex: 1 }} onClick={handleRestoreAll} disabled={!activePeriod} title="Restore everyone's last saved session for the active period">Restore All Sessions</button>
          </div>
          <div style={{ borderTop: '1px solid var(--line)', paddingTop: '0.75rem' }}>
            <div className="form-group mb-3">
              <label className="text-muted font-semibold text-xs uppercase tracking-wider mb-2 block" style={{ display: 'block', marginBottom: '0.5rem' }}>Bulk Restore — Filter Students</label>
              <input className="w-full" value={studentQuery} onChange={(event) => setStudentQuery(event.target.value)} placeholder="Name or ID" />
            </div>
            <div className="form-group mb-3">
              <select className="select-input" multiple size={5} value={bulkStudentIds} onChange={(event) => setBulkStudentIds(getSelectedValues(event))}>
                {students.data?.map((student) => <option key={student.student_id} value={student.student_id}>{student.student_name} · {student.student_id}</option>)}
              </select>
            </div>
            <button type="button" className="btn-primary btn-sm" onClick={handleBulkRestore} disabled={!activePeriod || !bulkStudentIds.length} title="Restore the most recent session for each selected student">Restore Selected ({bulkStudentIds.length})</button>
          </div>
        </div>

        {/* Sessions Browser */}
        <div className="panel stack">
          <div className="flex-between mb-2">
            <h3 style={{ margin: 0 }}>Session History <Tooltip text="All saved advising sessions for the active period. Expand a student to view or restore individual sessions." /></h3>
            <span className="badge badge-info">{sessions.data?.length ?? 0} sessions</span>
          </div>
          <p className="text-sm text-muted mb-3">All saved advising sessions for the active period, organized by student. Click a student to expand their sessions, or restore a specific one.</p>
          {Object.keys(sessionsByStudent).length === 0 ? (
            <p className="text-muted text-sm" style={{ textAlign: 'center', padding: '2rem' }}>No sessions saved yet for the active period.</p>
          ) : (
            <div className="sessions-browser">
              {Object.entries(sessionsByStudent).map(([studentId, group]) => (
                <div key={studentId} className="session-student-group">
                  <button
                    type="button"
                    className="session-student-header"
                    onClick={() => setExpandedStudents(prev => {
                      const next = new Set(prev)
                      next.has(studentId) ? next.delete(studentId) : next.add(studentId)
                      return next
                    })}
                  >
                    <span>{group!.name} <span className="text-muted" style={{ fontWeight: 400, fontSize: '0.8rem' }}>&middot; {group!.sessions!.length} session{group!.sessions!.length !== 1 ? 's' : ''}</span></span>
                    <span style={{ fontSize: '0.75rem', color: 'var(--muted)' }}>{expandedStudents.has(studentId) ? '▲' : '▼'}</span>
                  </button>
                  {expandedStudents.has(studentId) && (
                    <div className="session-student-body">
                      {group!.sessions!.map((session) => (
                        <div key={session.id} className="session-entry">
                          <div className="session-entry-info">
                            <span className="session-entry-title">{session.title}</span>
                            <span className="session-entry-meta">
                              {new Date(session.created_at).toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })}
                              {session.summary && typeof session.summary === 'object' && (
                                <> &middot; {(session.summary as any).advised?.length ?? 0} advised, {(session.summary as any).optional?.length ?? 0} optional</>
                              )}
                            </span>
                          </div>
                          <button type="button" className="btn-sm btn-secondary" onClick={() => handleRestoreSession(session.id, studentId)} title="Restore this specific session for the student">Restore</button>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
      <div className="grid-2">
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
                {students.data?.map((student: { student_id: string; student_name: string }) => <option key={student.student_id} value={student.student_id}>{student.student_name}</option>)}
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
