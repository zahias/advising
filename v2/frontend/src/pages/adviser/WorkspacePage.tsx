import { ChangeEvent, FormEvent, useEffect, useMemo, useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'

import { API_BASE_URL, apiFetch } from '../../lib/api'
import { useCourseCatalog, useMajors, usePeriods, useSessions, useStudentEligibility, useStudents, useTemplates } from '../../lib/hooks'

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

export function WorkspacePage() {
  const queryClient = useQueryClient()
  const [majorCode, setMajorCode] = useState('PBHL')
  const [query, setQuery] = useState('')
  const [selectedStudentId, setSelectedStudentId] = useState<string | undefined>()
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null)
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
  }, [student.data])

  useEffect(() => {
    if (templates.data?.length && !templates.data.some((item) => item.template_key === templateKey)) {
      setTemplateKey(templates.data[0].template_key)
    }
  }, [templateKey, templates.data])

  const eligibleSelectable = useMemo(() => {
    if (!student.data) return []
    const selected = new Set([...formState.advised, ...formState.optional])
    return student.data.eligibility.filter((course) => (
      selected.has(course.course_code)
      || (
        course.offered
        && !course.completed
        && !course.registered
        && (course.eligibility_status === 'Eligible' || course.eligibility_status === 'Eligible (Bypass)')
      )
    ))
  }, [formState.advised, formState.optional, student.data])

  const repeatSelectable = useMemo(() => {
    if (!student.data) return []
    const selected = new Set(formState.repeat)
    return student.data.eligibility.filter((course) => selected.has(course.course_code) || course.completed || course.registered)
  }, [formState.repeat, student.data])

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

  async function handleSave(event: FormEvent) {
    event.preventDefault()
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
    setMessage({ type: 'success', text: 'Selection saved.' })
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
    setMessage({ type: 'success', text: `Recommended: ${response.courses.join(', ')}` })
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
    <section className="stack">
      <div className="page-header">
        <div>
          <div className="eyebrow">Adviser Interface</div>
          <h2>Workspace</h2>
        </div>
        <label>
          <span>Major</span>
          <select value={majorCode} onChange={(event) => { setMajorCode(event.target.value); setSelectedStudentId(undefined); setMessage(null) }}>
            {majors.data?.map((major) => <option key={major.code}>{major.code}</option>)}
          </select>
        </label>
      </div>
      {message ? <div className={`alert ${message.type === 'error' ? 'error' : ''}`}>{message.text}</div> : null}
      <div className="two-column workspace-layout">
        <div className="stack">
          <div className="panel stack">
            <label><span>Student search</span><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Name or ID" /></label>
            <div className="student-list">{students.data?.map((item) => <button type="button" key={item.student_id} className={`student-pill ${selectedStudentId === item.student_id ? 'active' : ''}`} onClick={() => setSelectedStudentId(item.student_id)}>{item.student_name} · {item.student_id}</button>)}</div>
          </div>
          {student.data ? (
            <>
              <div className="panel stack compact-panel">
                <div className="field-row">
                  <div><div className="eyebrow">Standing</div><strong>{student.data.standing}</strong></div>
                  <div><div className="eyebrow">Remaining</div><strong>{student.data.credits_remaining}</strong></div>
                  <div><div className="eyebrow">Current Period</div><strong>{activePeriod ? `${activePeriod.semester} ${activePeriod.year}` : 'Missing'}</strong></div>
                </div>
                <div className="button-row wrap-row">
                  <button type="button" onClick={handleRestoreLatest} disabled={!activePeriod}>Restore latest</button>
                  <button type="button" onClick={handleRecommend}>Recommend</button>
                  <button type="button" onClick={handleDownloadReport}>Download report</button>
                </div>
                <div className="field-row">
                  <label>
                    <span>Email template</span>
                    <select value={templateKey} onChange={(event) => setTemplateKey(event.target.value)}>
                      {templates.data?.map((template) => <option key={template.id} value={template.template_key}>{template.display_name}</option>)}
                    </select>
                  </label>
                  <div className="button-slot"><button type="button" onClick={handleSendEmail}>Email student</button></div>
                </div>
              </div>
              <div className="panel stack compact-panel">
                <h3>Saved sessions</h3>
                <div className="session-list">
                  {sessions.data?.length ? sessions.data.map((item) => (
                    <div key={item.id} className="session-item">
                      <strong>{item.title}</strong>
                      <span>{new Date(item.created_at).toLocaleString()}</span>
                    </div>
                  )) : <p>No saved sessions for this student yet.</p>}
                </div>
              </div>
            </>
          ) : null}
        </div>
        <div className="stack">
          {student.data ? (
            <>
              <div className="panel stack">
                <div>
                  <h3>{student.data.student_name}</h3>
                  <p>ID {student.data.student_id}</p>
                </div>
                <form className="stack" onSubmit={handleSave}>
                  <div className="field-row">
                    <label>
                      <span>Advised courses</span>
                      <select multiple size={8} value={formState.advised} onChange={(event) => {
                        const next = getSelectedValues(event)
                        setFormState((current) => ({
                          ...current,
                          advised: next,
                          optional: current.optional.filter((course) => !next.includes(course)),
                          repeat: current.repeat.filter((course) => !next.includes(course)),
                        }))
                      }}>
                        {eligibleSelectable.map((course) => <option key={course.course_code} value={course.course_code}>{course.course_code} · {course.title}</option>)}
                      </select>
                    </label>
                    <label>
                      <span>Optional courses</span>
                      <select multiple size={8} value={formState.optional} onChange={(event) => {
                        const next = getSelectedValues(event).filter((course) => !formState.advised.includes(course))
                        setFormState((current) => ({
                          ...current,
                          optional: next,
                          repeat: current.repeat.filter((course) => !next.includes(course)),
                        }))
                      }}>
                        {eligibleSelectable.filter((course) => !formState.advised.includes(course.course_code) || formState.optional.includes(course.course_code)).map((course) => <option key={course.course_code} value={course.course_code}>{course.course_code} · {course.title}</option>)}
                      </select>
                    </label>
                    <label>
                      <span>Repeat courses</span>
                      <select multiple size={8} value={formState.repeat} onChange={(event) => {
                        const next = getSelectedValues(event).filter((course) => !formState.advised.includes(course) && !formState.optional.includes(course))
                        setFormState((current) => ({ ...current, repeat: next }))
                      }}>
                        {repeatSelectable.map((course) => <option key={course.course_code} value={course.course_code}>{course.course_code} · {course.title}</option>)}
                      </select>
                    </label>
                  </div>
                  <label><span>Advisor note</span><textarea rows={5} value={formState.note} onChange={(event) => setFormState({ ...formState, note: event.target.value })} /></label>
                  <button type="submit">Save selections</button>
                </form>
              </div>
              <div className="field-row three-col-layout">
                <div className="panel stack compact-panel">
                  <h3>Requisite bypasses</h3>
                  <label>
                    <span>Course</span>
                    <select value={bypassCourse} onChange={(event) => setBypassCourse(event.target.value)}>
                      <option value="">Select a course</option>
                      {student.data.eligibility.map((course) => <option key={course.course_code} value={course.course_code}>{course.course_code}</option>)}
                    </select>
                  </label>
                  <label><span>Note</span><textarea rows={3} value={bypassNote} onChange={(event) => setBypassNote(event.target.value)} /></label>
                  <button type="button" onClick={handleBypassSave}>Save bypass</button>
                  <div className="mini-list">
                    {Object.entries(student.data.bypasses).map(([courseCode, info]) => (
                      <div key={courseCode} className="mini-item">
                        <div>
                          <strong>{courseCode}</strong>
                          <p>{info.note}</p>
                        </div>
                        <button type="button" onClick={() => handleBypassDelete(courseCode)}>Remove</button>
                      </div>
                    ))}
                  </div>
                </div>
                <div className="panel stack compact-panel">
                  <h3>Hidden courses</h3>
                  <label>
                    <span>Per-student hidden courses</span>
                    <select multiple size={10} value={hiddenCourses} onChange={(event) => setHiddenCourses(getSelectedValues(event))}>
                      {hiddenCourseOptions.map((courseCode) => <option key={courseCode} value={courseCode}>{courseCode}</option>)}
                    </select>
                  </label>
                  <button type="button" onClick={handleHiddenCoursesSave}>Save hidden courses</button>
                  <p>Excluded by admin: {student.data.excluded_courses.length ? student.data.excluded_courses.join(', ') : 'None'}</p>
                </div>
                <div className="panel stack compact-panel">
                  <h3>Eligibility summary</h3>
                  <p>Advised credits: {student.data.advised_credits + student.data.repeat_credits}</p>
                  <p>Optional credits: {student.data.optional_credits}</p>
                  <p>Visible required: {requiredCourses.length}</p>
                  <p>Visible intensive: {intensiveCourses.length}</p>
                </div>
              </div>
              <div className="panel stack">
                <h3>Required courses</h3>
                <div className="scroll-table">
                  <table>
                    <thead><tr><th>Code</th><th>Title</th><th>Status</th><th>Action</th><th>Justification</th></tr></thead>
                    <tbody>
                      {requiredCourses.map((course) => <tr key={course.course_code}><td>{course.course_code}</td><td>{course.title}</td><td>{course.eligibility_status}</td><td>{course.action || '—'}</td><td>{course.justification}</td></tr>)}
                    </tbody>
                  </table>
                </div>
              </div>
              <div className="panel stack">
                <h3>Intensive courses</h3>
                <div className="scroll-table">
                  <table>
                    <thead><tr><th>Code</th><th>Title</th><th>Status</th><th>Action</th><th>Justification</th></tr></thead>
                    <tbody>
                      {intensiveCourses.map((course) => <tr key={course.course_code}><td>{course.course_code}</td><td>{course.title}</td><td>{course.eligibility_status}</td><td>{course.action || '—'}</td><td>{course.justification}</td></tr>)}
                    </tbody>
                  </table>
                </div>
              </div>
            </>
          ) : <div className="panel"><p>Select a student to load eligibility, selections, sessions, bypasses, and hidden-course settings.</p></div>}
        </div>
      </div>
    </section>
  )
}
