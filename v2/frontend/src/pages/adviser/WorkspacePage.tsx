import { useEffect, useMemo, useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'

import { API_BASE_URL, DegreePlanResponse, apiFetch } from '../../lib/api'
import { useCourseCatalog, useMajors, usePeriods, useSessions, useStudentEligibility, useStudents, useTemplates } from '../../lib/hooks'

// New modular components
import { StudentProfileHeader } from '../../components/workspace/StudentProfileHeader'
import { CourseSelectionBuilder } from '../../components/workspace/CourseSelectionBuilder'
import { EligibilityTables } from '../../components/workspace/EligibilityTables'
import { ExceptionManagement } from '../../components/workspace/ExceptionManagement'
import { Tooltip } from '../../components/Tooltip'

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

const STATUS_DOT: Record<string, string> = {
  completed: '#22c55e',
  registered: '#eab308',
  available: '#3b82f6',
  advised: '#f97316',
  not_eligible: '#cbd5e1',
  failed: '#ef4444',
}
const STATUS_BG: Record<string, string> = {
  completed: '#f0fdf4',
  registered: '#fefce8',
  available: '#eff6ff',
  advised: '#fff7ed',
  failed: '#fef2f2',
}
const STATUS_BORDER: Record<string, string> = {
  completed: '#bbf7d0',
  registered: '#fde68a',
  available: '#bfdbfe',
  advised: '#fed7aa',
  failed: '#fecaca',
}

export function WorkspacePage() {
  const queryClient = useQueryClient()
  const [majorCode, setMajorCode] = useState('PBHL')
  const [query, setQuery] = useState('')
  const [selectedStudentId, setSelectedStudentId] = useState<string | undefined>()
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null)

  // Tabs: 'schedule', 'academic', 'exceptions', 'degree'
  const [activeTab, setActiveTab] = useState<'schedule' | 'academic' | 'exceptions' | 'degree'>('schedule')

  const [templateKey, setTemplateKey] = useState('default')
  const [bypassCourse, setBypassCourse] = useState('')
  const [bypassNote, setBypassNote] = useState('')
  const [hiddenCourses, setHiddenCourses] = useState<string[]>([])
  const [excludedCourses, setExcludedCourses] = useState<string[]>([])
  const [originalExcludedCourses, setOriginalExcludedCourses] = useState<string[]>([])
  const [formState, setFormState] = useState({ advised: [] as string[], optional: [] as string[], repeat: [] as string[], note: '' })

  const majors = useMajors()
  const periods = usePeriods(majorCode)
  const students = useStudents(majorCode, query)
  const courseCatalog = useCourseCatalog(majorCode)
  const student = useStudentEligibility(majorCode, selectedStudentId)
  const sessions = useSessions(majorCode, periods.data?.find((period) => period.is_active)?.period_code, selectedStudentId)
  const templates = useTemplates(majorCode)
  const activePeriod = periods.data?.find((period) => period.is_active)

  const degreePlan = useQuery({
    queryKey: ['degree-plan', majorCode, selectedStudentId],
    queryFn: () => apiFetch<DegreePlanResponse>(`/insights/${majorCode}/degree-plan/${selectedStudentId}`),
    enabled: Boolean(selectedStudentId),
  })

  useEffect(() => {
    if (!student.data) return
    setFormState({
      advised: student.data.selection.advised,
      optional: student.data.selection.optional,
      repeat: student.data.selection.repeat,
      note: student.data.selection.note,
    })
    setHiddenCourses(student.data.hidden_courses)
    setExcludedCourses(student.data.excluded_courses)
    setOriginalExcludedCourses(student.data.excluded_courses)
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

  async function handleSavePlacements() {
    if (!selectedStudentId) return
    const response = await authedFetch('/advising/exclusions', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ major_code: majorCode, student_ids: [selectedStudentId], course_codes: excludedCourses }),
    })
    if (!response.ok) {
      setMessage({ type: 'error', text: await response.text() })
      return
    }
    setMessage({ type: 'success', text: 'Intensive placement saved.' })
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
                majorCode={majorCode}
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
                  title="Build this student's course schedule for the semester. Select advised, optional, and repeat courses."
                >
                  Schedule Builder
                </button>
                <button
                  type="button"
                  className={`tab-btn ${activeTab === 'academic' ? 'active' : ''}`}
                  onClick={() => setActiveTab('academic')}
                  title="View the student's full eligibility record, including why courses are ineligible, and manage intensive course placement."
                >
                  Academic Record
                </button>
                <button
                  type="button"
                  className={`tab-btn ${activeTab === 'degree' ? 'active' : ''}`}
                  onClick={() => setActiveTab('degree')}
                  title="View the student's full degree plan map showing completed, registered, and remaining courses by year and semester."
                >
                  Degree Plan
                </button>
                <button
                  type="button"
                  className={`tab-btn ${activeTab === 'exceptions' ? 'active' : ''}`}
                  onClick={() => setActiveTab('exceptions')}
                  title="Grant requisite bypasses for specific courses or hide courses from the student's view."
                >
                  Exceptions & Overrides
                </button>
              </div>

              <div className="workspace-tab-content">
                {activeTab === 'schedule' && (
                  <CourseSelectionBuilder
                    eligibility={student.data.eligibility}
                    remainingCredits={student.data.credits_remaining}
                    formState={formState}
                    onChange={setFormState}
                    onSave={handleSaveSelection}
                  />
                )}

                {activeTab === 'academic' && (
                  <div className="stack">
                    {/* Intensive Course Placement */}
                    {intensiveCourses.length > 0 && (
                      <div className="panel stack">
                        <div className="flex-between">
                          <div>
                            <h3 style={{ margin: 0 }}>Intensive Course Placement <Tooltip text="Intensive courses require manual placement decisions. Mark a course as 'Excluded' to prevent it from appearing in this student's eligible list during intensive semesters." /></h3>
                            <p className="text-muted text-sm" style={{ margin: '4px 0 0' }}>Select which intensive course(s) apply to this student. Excluded courses are removed from their eligible course list.</p>
                          </div>
                          <div style={{ display: 'flex', gap: '0.5rem' }}>
                            <button type="button" className="btn-sm btn-outline" onClick={() => setExcludedCourses(originalExcludedCourses)} title="Reset to last saved placement">Reset</button>
                            <button type="button" className="btn-primary btn-sm" onClick={handleSavePlacements} title="Save the intensive course placement for this student">Save Placement</button>
                          </div>
                        </div>
                        <div className="placement-grid">
                          {intensiveCourses.map((course) => {
                            const isExcluded = excludedCourses.includes(course.course_code)
                            return (
                              <button
                                key={course.course_code}
                                type="button"
                                className={`placement-card ${isExcluded ? 'excluded' : 'active'}`}
                                onClick={() => setExcludedCourses(prev =>
                                  isExcluded ? prev.filter(c => c !== course.course_code) : [...prev, course.course_code]
                                )}
                                title={isExcluded ? 'Click to include this course for the student' : 'Click to exclude this course for the student'}
                              >
                                <span className="placement-card-code">{course.course_code}</span>
                                <span className="placement-card-title">{course.title}</span>
                                <span className="placement-card-status">{isExcluded ? '✗ Excluded' : '✓ Active'}</span>
                              </button>
                            )
                          })}
                        </div>
                      </div>
                    )}
                    <EligibilityTables
                      eligibility={student.data.eligibility}
                      intensiveCourses={intensiveCourses}
                    />
                  </div>
                )}

                {activeTab === 'degree' && (
                  <div className="stack">
                    {degreePlan.isLoading && (
                      <div className="panel" style={{ textAlign: 'center', padding: '3rem', color: 'var(--muted)' }}>Loading degree plan…</div>
                    )}
                    {degreePlan.isError && (
                      <div className="panel" style={{ textAlign: 'center', padding: '3rem', color: '#dc2626' }}>Could not load degree plan. The degree plan dataset may not be configured for this major.</div>
                    )}
                    {degreePlan.data && (
                      <>
                        <div className="legend-row bg-white p-3 rounded-xl border" style={{ display: 'flex', flexWrap: 'wrap', justifyContent: 'center', gap: '1.25rem' }}>
                          {degreePlan.data.legend.map((item) => (
                            <span key={item.status} style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', fontSize: '0.82rem', fontWeight: 500 }}>
                              <span style={{ width: '11px', height: '11px', borderRadius: '50%', background: STATUS_DOT[item.status] ?? '#cbd5e1', display: 'inline-block', flexShrink: 0 }} />
                              {item.label}
                            </span>
                          ))}
                        </div>
                        <div className="grid-2">
                          {degreePlan.data.years.map((year) => (
                            <div key={year.year_name} className="panel">
                              <div className="flex-between" style={{ borderBottom: '1px solid var(--line)', paddingBottom: '0.75rem', marginBottom: '1rem' }}>
                                <h3 style={{ margin: 0, color: 'var(--accent)' }}>{year.year_name}</h3>
                              </div>
                              <div className="degree-grid">
                                {year.semesters.map((semester) => (
                                  <div key={semester.semester_key} className="degree-card">
                                    <div className="flex-between">
                                      <strong style={{ fontSize: '0.85rem' }}>{semester.semester_key}</strong>
                                      <span className="badge badge-info">{semester.total_credits} cr</span>
                                    </div>
                                    <div style={{ marginTop: '0.5rem', display: 'flex', flexDirection: 'column', gap: '0.4rem' }}>
                                      {semester.courses.map((course) => (
                                        <div
                                          key={course.code}
                                          style={{ background: STATUS_BG[course.status] ?? '#f8f9fa', borderRadius: '8px', padding: '0.5rem 0.75rem', border: `1px solid ${STATUS_BORDER[course.status] ?? 'var(--line)'}`, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}
                                          title={`${course.code} — ${course.status.replace('_', ' ')}`}
                                        >
                                          <div>
                                            <div style={{ fontWeight: 700, fontSize: '0.75rem', fontFamily: 'monospace' }}>{course.code}</div>
                                            <div style={{ fontSize: '0.7rem', color: 'var(--muted)', maxWidth: '150px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{course.title}</div>
                                          </div>
                                          <span style={{ width: '12px', height: '12px', borderRadius: '50%', background: STATUS_DOT[course.status] ?? '#cbd5e1', flexShrink: 0, display: 'inline-block' }} />
                                        </div>
                                      ))}
                                    </div>
                                  </div>
                                ))}
                              </div>
                            </div>
                          ))}
                        </div>
                      </>
                    )}
                    {!degreePlan.data && !degreePlan.isLoading && !degreePlan.isError && (
                      <div className="blank-slate-panel panel">
                        <div className="blank-slate-content">
                          <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1" className="text-muted"><path d="M4 19.5v-15A2.5 2.5 0 0 1 6.5 2H20v20H6.5a2.5 2.5 0 0 1 0-5H20" /></svg>
                          <h3>Degree Plan Unavailable</h3>
                          <p className="text-muted">No degree plan data found for this student.</p>
                        </div>
                      </div>
                    )}
                  </div>
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
