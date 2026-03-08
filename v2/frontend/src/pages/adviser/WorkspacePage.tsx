import { FormEvent, useMemo, useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'

import { API_BASE_URL } from '../../lib/api'
import { useMajors, usePeriods, useStudentEligibility, useStudents } from '../../lib/hooks'

export function WorkspacePage() {
  const queryClient = useQueryClient()
  const [majorCode, setMajorCode] = useState('PBHL')
  const [query, setQuery] = useState('')
  const [selectedStudentId, setSelectedStudentId] = useState<string | undefined>()
  const majors = useMajors()
  const periods = usePeriods(majorCode)
  const students = useStudents(majorCode, query)
  const student = useStudentEligibility(majorCode, selectedStudentId)
  const activePeriod = periods.data?.find((period) => period.is_active)
  const [formState, setFormState] = useState({ advised: '', optional: '', repeat: '', note: '' })

  async function handleSave(event: FormEvent) {
    event.preventDefault()
    if (!student.data || !activePeriod) return
    const token = window.localStorage.getItem('advising_v2_token')
    const response = await fetch(`${API_BASE_URL}/api/advising/selection`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...(token ? { Authorization: `Bearer ${token}` } : {}) },
      body: JSON.stringify({
        major_code: majorCode,
        period_code: activePeriod.period_code,
        student_id: student.data.student_id,
        student_name: student.data.student_name,
        selection: {
          advised: formState.advised.split(',').map((item) => item.trim()).filter(Boolean),
          optional: formState.optional.split(',').map((item) => item.trim()).filter(Boolean),
          repeat: formState.repeat.split(',').map((item) => item.trim()).filter(Boolean),
          note: formState.note,
        },
      }),
    })
    if (response.ok) {
      queryClient.invalidateQueries({ queryKey: ['student-eligibility', majorCode, selectedStudentId] })
    }
  }

  return (
    <section className="stack">
      <div className="page-header"><div><div className="eyebrow">Adviser Interface</div><h2>Workspace</h2></div><label><span>Major</span><select value={majorCode} onChange={(event) => setMajorCode(event.target.value)}>{majors.data?.map((major) => <option key={major.code}>{major.code}</option>)}</select></label></div>
      <div className="two-column">
        <div className="panel stack">
          <label><span>Student search</span><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Name or ID" /></label>
          <div className="student-list">{students.data?.map((item) => <button key={item.student_id} className={`student-pill ${selectedStudentId === item.student_id ? 'active' : ''}`} onClick={() => { setSelectedStudentId(item.student_id); setFormState({ advised: '', optional: '', repeat: '', note: '' }) }}>{item.student_name} · {item.student_id}</button>)}</div>
        </div>
        <div className="panel stack">
          {student.data ? (
            <>
              <div>
                <h3>{student.data.student_name}</h3>
                <p>{student.data.standing} · Remaining {student.data.credits_remaining}</p>
              </div>
              <form className="stack" onSubmit={handleSave}>
                <label><span>Advised (comma-separated)</span><input value={formState.advised} onChange={(event) => setFormState({ ...formState, advised: event.target.value })} /></label>
                <label><span>Optional</span><input value={formState.optional} onChange={(event) => setFormState({ ...formState, optional: event.target.value })} /></label>
                <label><span>Repeat</span><input value={formState.repeat} onChange={(event) => setFormState({ ...formState, repeat: event.target.value })} /></label>
                <label><span>Advisor note</span><textarea rows={4} value={formState.note} onChange={(event) => setFormState({ ...formState, note: event.target.value })} /></label>
                <button type="submit">Save selection</button>
              </form>
              <div className="eligibility-grid">{student.data.eligibility.slice(0, 12).map((course) => <article key={course.course_code} className="eligibility-card"><strong>{course.course_code}</strong><span>{course.title}</span><small>{course.eligibility_status}</small><p>{course.justification}</p></article>)}</div>
            </>
          ) : <p>Select a student to load eligibility.</p>}
        </div>
      </div>
    </section>
  )
}
