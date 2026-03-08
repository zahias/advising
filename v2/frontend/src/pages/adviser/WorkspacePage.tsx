import { FormEvent, useEffect, useMemo, useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'

import { API_BASE_URL, apiFetch } from '../../lib/api'
import { useCourseCatalog, useMajors, usePeriods, useSessions, useStudentEligibility, useStudents, useTemplates } from '../../lib/hooks'

// New modular components
import { StudentProfileHeader } from '../../components/workspace/StudentProfileHeader'
import { CourseSelectionBuilder } from '../../components/workspace/CourseSelectionBuilder'
import { EligibilityTables } from '../../components/workspace/EligibilityTables'
import { ExceptionManagement } from '../../components/workspace/ExceptionManagement'

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

export function WorkspacePage() {
  const queryClient = useQueryClient()
  const [majorCode, setMajorCode] = useState('PBHL')
  const [query, setQuery] = useState('')
  const [selectedStudentId, setSelectedStudentId] = useState<string | undefined>()
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null)

  // Tabs: 'schedule', 'academic', 'exceptions'
  const [activeTab, setActiveTab] = useState<'schedule' | 'academic' | 'exceptions'>('schedule')

  const [templateKey, setTemplateKey] = useState('default')
  const [bypassCourse, setBypassCourse] = useState('')
  const [bypassNote, setBypassNote] = useState('')
  const [hiddenCourses, setHiddenCourses] = useState<string[]>([])
  const [formState, setFormState] = useState({ advised: [] as string[], optional: [] as string[], repeat: [] as string[], note: '' })

  const majors = useMajors()
  const periods = usePeriods(majorCode)
  const students = useStudents(majorCode, query)
  const courseCatalog = useCourseCatalog(majorCode)
  const student = useStudentEligibility(majorCode, selectedStudentId)
  const sessions = useSessions(majorCode, periods.data?.find((period) => period.is_active)?.period_code, selectedStudentId)
  const templates = useTemplates(majorCode)
  const activePeriod = periods.data?.find((period) => period.is_active)

  useEffect(() => {
    if (!student.data) return
    setFormState({
      advised: student.data.selection.advised,
      optional: student.data.selection.optional,
      repeat: student.data.selection.repeat,
      note: student.data.selection.note,
    })
    setHiddenCourses(student.data.hidden_courses)
    // Reset tab on student change
    setActiveTab('schedule')
  }, [student.data])

  useEffect(() => {
    if (templates.data?.length && !templates.data.some((item) => item.template_key === templateKey)) {
      setTemplateKey(templates.data[0].template_key)
    }
  }, [templateKey, templates.data])


  const requiredCourses = useMemo(
    () => student.data?.eligibility.filter((course) => course.course_type.toLowerCase() === 'required') ?? [],
    [student.data],
  )
  const intensiveCourses = useMemo(
    () => student.data?.eligibility.filter((course) => course.course_type.toLowerCase() === 'intensive') ?? [],
    [student.data],
  )

  const hiddenCourseOptions = useMemo(
    () => courseCatalog.data?.map((course) => course.course_code) ?? [],
    [courseCatalog.data],
  )

  async function handleSaveSelection() {
    if (!student.data || !activePeriod) return
    const response = await authedFetch('/advising/selection', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        major_code: majorCode,
        period_code: activePeriod.period_code,
        student_id: student.data.student_id,
        student_name: student.data.student_name,
        selection: formState,
      }),
    })
    if (!response.ok) {
      setMessage({ type: 'error', text: await response.text() })
      return
    }
    setMessage({ type: 'success', text: 'Schedule saved.' })
    queryClient.invalidateQueries({ queryKey: ['student-eligibility', majorCode, selectedStudentId] })
    queryClient.invalidateQueries({ queryKey: ['sessions', majorCode, activePeriod.period_code, selectedStudentId] })
    queryClient.invalidateQueries({ queryKey: ['dashboard', majorCode] })
  }

  async function handleRestoreLatest() {
    if (!selectedStudentId || !activePeriod) return
    const response = await authedFetch(`/advising/sessions/${majorCode}/${activePeriod.period_code}/${selectedStudentId}/restore`, { method: 'POST' })
    if (!response.ok) {
      setMessage({ type: 'error', text: await response.text() })
      return
    }
    setMessage({ type: 'success', text: 'Latest session restored.' })
    queryClient.invalidateQueries({ queryKey: ['student-eligibility', majorCode, selectedStudentId] })
  }

  async function handleRecommend() {
    if (!selectedStudentId) return
    const response = await apiFetch<{ courses: string[] }>(`/advising/recommendations/${majorCode}/${selectedStudentId}`)
    if (!response.courses.length) {
      setMessage({ type: 'success', text: 'All available courses are already selected.' })
      return
    }
    setFormState((current) => ({
      ...current,
      advised: Array.from(new Set([...current.advised, ...response.courses])),
      optional: current.optional.filter((course) => !response.courses.includes(course)),
      repeat: current.repeat.filter((course) => !response.courses.includes(course)),
    }))
    setMessage({ type: 'success', text: `Recommended ${response.courses.length} courses.` })
  }

  async function handleDownloadReport() {
    if (!selectedStudentId) return
    const response = await authedFetch(`/reports/${majorCode}/student/${selectedStudentId}`)
    if (!response.ok) {
      setMessage({ type: 'error', text: await response.text() })
      return
    }
    const blob = await response.blob()
    const url = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `Advising_${selectedStudentId}.xlsx`
    document.body.appendChild(link)
    link.click()
    link.remove()
    window.URL.revokeObjectURL(url)
  }

  async function handleSendEmail() {
    if (!selectedStudentId) return
    const response = await authedFetch(`/emails/${majorCode}/${selectedStudentId}?template_key=${encodeURIComponent(templateKey)}`, { method: 'POST' })
    const body = await response.json().catch(() => null)
    if (!response.ok) {
      setMessage({ type: 'error', text: body?.detail || body?.message || 'Email failed.' })
      return
    }
    setMessage({ type: 'success', text: body?.message || 'Email sent.' })
  }

  async function handleHiddenCoursesSave() {
    if (!selectedStudentId) return
    const response = await authedFetch('/advising/hidden-courses', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ major_code: majorCode, student_id: selectedStudentId, course_codes: hiddenCourses }),
    })
    if (!response.ok) {
      setMessage({ type: 'error', text: await response.text() })
      return
    }
    setMessage({ type: 'success', text: 'Hidden courses updated.' })
    queryClient.invalidateQueries({ queryKey: ['student-eligibility', majorCode, selectedStudentId] })
  }

  async function handleBypassSave() {
    if (!selectedStudentId || !bypassCourse) return
    const response = await authedFetch('/advising/bypasses', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ major_code: majorCode, student_id: selectedStudentId, course_code: bypassCourse, note: bypassNote, advisor_name: activePeriod?.advisor_name || '' }),
    })
    if (!response.ok) {
      setMessage({ type: 'error', text: await response.text() })
      return
    }
    setBypassCourse('')
    setBypassNote('')
    setMessage({ type: 'success', text: 'Bypass saved.' })
    queryClient.invalidateQueries({ queryKey: ['student-eligibility', majorCode, selectedStudentId] })
  }

  async function handleBypassDelete(courseCode: string) {
    if (!selectedStudentId) return
    const response = await authedFetch(`/advising/bypasses/${majorCode}/${selectedStudentId}/${courseCode}`, { method: 'DELETE' })
    if (!response.ok) {
      setMessage({ type: 'error', text: await response.text() })
      return
    }
    setMessage({ type: 'success', text: 'Bypass removed.' })
    queryClient.invalidateQueries({ queryKey: ['student-eligibility', majorCode, selectedStudentId] })
  }

  return (
    <section className="workspace-container stack">
      <div className="page-header flex-between">
        <div>
          <div className="eyebrow text-muted">Adviser Interface</div>
          <h2>Advising Workspace</h2>
        </div>
        <div className="header-actions">
          <label className="inline-select">
            <span className="text-muted">Master Program:</span>
            <select className="select-input" value={majorCode} onChange={(event) => { setMajorCode(event.target.value); setSelectedStudentId(undefined); setMessage(null) }}>
              {majors.data?.map((major) => <option key={major.code}>{major.code}</option>)}
            </select>
          </label>
        </div>
      </div>

      {message && (
        <div className={`alert ${message.type === 'error' ? 'alert-error' : 'alert-success'}`}>
          {message.text}
          <button type="button" className="close-btn" onClick={() => setMessage(null)}>&times;</button>
        </div>
      )}

      <div className="workspace-layout">
        <aside className="workspace-sidebar stack">
          <div className="student-search-panel panel stack">
            <div className="search-box">
              <svg className="search-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="11" cy="11" r="8" /><path d="m21 21-4.3-4.3" /></svg>
              <input
                type="search"
                className="search-input"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Search students..."
              />
            </div>
            <div className="student-list scrollable">
              {students.data?.map((item) => (
                <button
                  type="button"
                  key={item.student_id}
                  className={`student-nav-item ${selectedStudentId === item.student_id ? 'active' : ''}`}
                  onClick={() => setSelectedStudentId(item.student_id)}
                >
                  <span className="student-name">{item.student_name}</span>
                  <span className="student-id mono text-muted">{item.student_id}</span>
                </button>
              ))}
            </div>
          </div>

          {student.data && sessions.data && sessions.data.length > 0 && (
            <div className="sessions-panel panel stack compact-panel">
              <h4 className="panel-title text-muted">Recent Sessions</h4>
              <div className="session-history list-minimal">
                {sessions.data.slice(0, 5).map((item) => (
                  <div key={item.id} className="history-item">
                    <span className="history-title">{item.title}</span>
                    <span className="history-time text-muted">{new Date(item.created_at).toLocaleDateString()}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </aside>

        <main className="workspace-main">
          {!student.data ? (
            <div className="blank-slate-panel panel">
              <div className="blank-slate-content">
                <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1" className="text-muted"><path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2" /><circle cx="9" cy="7" r="4" /><path d="M22 21v-2a4 4 0 0 0-3-3.87" /><path d="M16 3.13a4 4 0 0 1 0 7.75" /></svg>
                <h3>Select a Student</h3>
                <p className="text-muted">Search and select a student from the sidebar to begin advising, view their eligibility, or manage course exceptions.</p>
              </div>
            </div>
          ) : (
            <div className="student-workspace stack">

              <StudentProfileHeader
                student={student.data}
                activePeriod={activePeriod}
                templateKey={templateKey}
                templates={templates.data || []}
                onTemplateChange={setTemplateKey}
                onEmail={handleSendEmail}
                onRestoreLatest={handleRestoreLatest}
                onRecommend={handleRecommend}
                onDownloadReport={handleDownloadReport}
              />

              <div className="workspace-tabs-nav">
                <button
                  type="button"
                  className={`tab-btn ${activeTab === 'schedule' ? 'active' : ''}`}
                  onClick={() => setActiveTab('schedule')}
                >
                  Schedule Builder
                </button>
                <button
                  type="button"
                  className={`tab-btn ${activeTab === 'academic' ? 'active' : ''}`}
                  onClick={() => setActiveTab('academic')}
                >
                  Academic Record
                </button>
                <button
                  type="button"
                  className={`tab-btn ${activeTab === 'exceptions' ? 'active' : ''}`}
                  onClick={() => setActiveTab('exceptions')}
                >
                  Exceptions & Overrides
                </button>
              </div>

              <div className="workspace-tab-content">
                {activeTab === 'schedule' && (
                  <CourseSelectionBuilder
                    eligibility={student.data.eligibility}
                    formState={formState}
                    onChange={setFormState}
                    onSave={handleSaveSelection}
                  />
                )}

                {activeTab === 'academic' && (
                  <EligibilityTables
                    requiredCourses={requiredCourses}
                    intensiveCourses={intensiveCourses}
                  />
                )}

                {activeTab === 'exceptions' && (
                  <ExceptionManagement
                    student={student.data}
                    eligibility={student.data.eligibility}
                    hiddenCourseOptions={hiddenCourseOptions}
                    bypassCourse={bypassCourse}
                    setBypassCourse={setBypassCourse}
                    bypassNote={bypassNote}
                    setBypassNote={setBypassNote}
                    onBypassSave={handleBypassSave}
                    onBypassDelete={handleBypassDelete}
                    hiddenCourses={hiddenCourses}
                    setHiddenCourses={setHiddenCourses}
                    onHiddenCoursesSave={handleHiddenCoursesSave}
                  />
                )}
              </div>

            </div>
          )}
        </main>
      </div>
    </section>
  )
}
