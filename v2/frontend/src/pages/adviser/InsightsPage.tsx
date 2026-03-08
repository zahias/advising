import { ChangeEvent, useEffect, useMemo, useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'

import {
  API_BASE_URL,
  AllStudentsInsightsResponse,
  CourseOfferingRecommendation,
  DegreePlanResponse,
  IndividualStudentInsight,
  PlannerSelectionState,
  QAARow,
  ScheduleConflictRow,
  apiFetch,
} from '../../lib/api'
import { useMajors, useStudents, useTemplates } from '../../lib/hooks'

type InsightTab = 'all' | 'individual' | 'qaa' | 'conflicts' | 'degree'
type MatrixTab = 'required' | 'intensive'

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

function summarizeStatuses(rows: AllStudentsInsightsResponse['rows'], courseCode: string) {
  const counts: Record<string, number> = {}
  rows.forEach((row) => {
    const code = row.courses[courseCode]
    if (!code) return
    counts[code] = (counts[code] || 0) + 1
  })
  return Object.entries(counts)
    .sort((left, right) => left[0].localeCompare(right[0]))
    .map(([code, count]) => `${code}:${count}`)
    .join(' | ')
}

export function InsightsPage() {
  const queryClient = useQueryClient()
  const [majorCode, setMajorCode] = useState('PBHL')
  const [tab, setTab] = useState<InsightTab>('all')
  const [matrixTab, setMatrixTab] = useState<MatrixTab>('required')
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedStudentId, setSelectedStudentId] = useState<string>('')
  const [selectedCourses, setSelectedCourses] = useState<string[]>([])
  const [templateKey, setTemplateKey] = useState('default')
  const [graduatingThreshold, setGraduatingThreshold] = useState(36)
  const [targetGroups, setTargetGroups] = useState(10)
  const [maxCoursesPerGroup, setMaxCoursesPerGroup] = useState(10)
  const [minStudents, setMinStudents] = useState(1)
  const [minCourses, setMinCourses] = useState(2)
  const [remainingMin, setRemainingMin] = useState<number | ''>('')
  const [remainingMax, setRemainingMax] = useState<number | ''>('')
  const [semesterFilter, setSemesterFilter] = useState('All Courses')
  const [pendingSimulatedCourses, setPendingSimulatedCourses] = useState<string[]>([])
  const [appliedSimulatedCourses, setAppliedSimulatedCourses] = useState<string[]>([])
  const [requiredColumns, setRequiredColumns] = useState<string[]>([])
  const [intensiveColumns, setIntensiveColumns] = useState<string[]>([])
  const [showAllRows, setShowAllRows] = useState(false)
  const [plannerThreshold, setPlannerThreshold] = useState(30)
  const [plannerMinEligible, setPlannerMinEligible] = useState(3)
  const [plannerSelection, setPlannerSelection] = useState<string[]>([])
  const [plannerMessage, setPlannerMessage] = useState('')
  const [pageMessage, setPageMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null)

  const majors = useMajors()
  const students = useStudents(majorCode, searchQuery)
  const allStudentsSearch = useStudents(majorCode, '')
  const templates = useTemplates(majorCode)

  const allStudents = useQuery({
    queryKey: ['all-students', majorCode, semesterFilter, appliedSimulatedCourses],
    queryFn: () => {
      const params = new URLSearchParams()
      params.set('semester_filter', semesterFilter)
      appliedSimulatedCourses.forEach((course) => params.append('simulated_courses', course))
      return apiFetch<AllStudentsInsightsResponse>(`/insights/${majorCode}/all-students?${params.toString()}`)
    },
  })
  const planner = useQuery({
    queryKey: ['planner', majorCode, plannerThreshold, plannerMinEligible],
    queryFn: () => apiFetch<CourseOfferingRecommendation[]>(`/insights/${majorCode}/course-planner?graduation_threshold=${plannerThreshold}&min_eligible_students=${plannerMinEligible}`),
  })
  const plannerState = useQuery({
    queryKey: ['planner-state', majorCode],
    queryFn: () => apiFetch<PlannerSelectionState>(`/insights/${majorCode}/course-planner-state`),
  })
  const individual = useQuery({
    queryKey: ['individual-student', majorCode, selectedStudentId, selectedCourses],
    queryFn: () => apiFetch<IndividualStudentInsight>(`/insights/${majorCode}/individual/${selectedStudentId}${selectedCourses.length ? `?${selectedCourses.map((course) => `courses=${encodeURIComponent(course)}`).join('&')}` : ''}`),
    enabled: Boolean(selectedStudentId),
  })
  const qaa = useQuery({
    queryKey: ['qaa', majorCode, graduatingThreshold],
    queryFn: () => apiFetch<QAARow[]>(`/insights/${majorCode}/qaa?graduating_threshold=${graduatingThreshold}`),
  })
  const conflicts = useQuery({
    queryKey: ['schedule-conflicts', majorCode, targetGroups, maxCoursesPerGroup, minStudents, minCourses],
    queryFn: () => apiFetch<ScheduleConflictRow[]>(`/insights/${majorCode}/schedule-conflicts?target_groups=${targetGroups}&max_courses_per_group=${maxCoursesPerGroup}&min_students=${minStudents}&min_courses=${minCourses}`),
  })
  const degreePlan = useQuery({
    queryKey: ['degree-plan', majorCode, selectedStudentId],
    queryFn: () => apiFetch<DegreePlanResponse>(`/insights/${majorCode}/degree-plan/${selectedStudentId}`),
    enabled: Boolean(selectedStudentId),
  })

  useEffect(() => {
    if (!templates.data?.length) return
    if (!templates.data.some((item) => item.template_key === templateKey)) {
      setTemplateKey(templates.data[0].template_key)
    }
  }, [templateKey, templates.data])

  useEffect(() => {
    if (!plannerState.data) return
    setPlannerThreshold(plannerState.data.graduation_threshold)
    setPlannerMinEligible(plannerState.data.min_eligible_students)
    setPlannerSelection(plannerState.data.selected_courses)
  }, [majorCode, plannerState.data])

  useEffect(() => {
    if (!allStudents.data) return
    setPendingSimulatedCourses(allStudents.data.simulated_courses)
  }, [majorCode, allStudents.data])

  useEffect(() => {
    if (!allStudents.data) return
    setRequiredColumns((current) => {
      const next = current.filter((course) => allStudents.data.required_courses.includes(course))
      return next.length ? next : allStudents.data.required_courses
    })
    setIntensiveColumns((current) => {
      const next = current.filter((course) => allStudents.data.intensive_courses.includes(course))
      return next.length ? next : allStudents.data.intensive_courses
    })
  }, [allStudents.data])

  const filteredRows = useMemo(() => {
    const rows = allStudents.data?.rows ?? []
    return rows.filter((row) => {
      if (remainingMin !== '' && row.remaining_credits < remainingMin) return false
      if (remainingMax !== '' && row.remaining_credits > remainingMax) return false
      return true
    })
  }, [allStudents.data?.rows, remainingMax, remainingMin])

  const visibleRows = showAllRows ? filteredRows : filteredRows.slice(0, 80)
  const matrixColumns = matrixTab === 'required' ? requiredColumns : intensiveColumns
  const matrixOptions = matrixTab === 'required' ? (allStudents.data?.required_courses ?? []) : (allStudents.data?.intensive_courses ?? [])
  const selectedStudentOptions = searchQuery ? (students.data ?? []) : (allStudentsSearch.data ?? [])

  const plannerImpact = useMemo(() => {
    const selected = new Set(plannerSelection)
    const matching = (planner.data ?? []).filter((item) => selected.has(item.course))
    return {
      eligible: matching.reduce((sum, item) => sum + item.currently_eligible, 0),
      graduating: matching.reduce((sum, item) => sum + item.graduating_students, 0),
    }
  }, [planner.data, plannerSelection])

  function toggleCourse(courseCode: string) {
    setSelectedCourses((current) => current.includes(courseCode) ? current.filter((item) => item !== courseCode) : [...current, courseCode])
  }

  function updateMatrixColumns(event: ChangeEvent<HTMLSelectElement>) {
    const next = getSelectedValues(event)
    if (matrixTab === 'required') {
      setRequiredColumns(next)
      return
    }
    setIntensiveColumns(next)
  }

  async function download(path: string, filename: string) {
    const response = await authedFetch(path)
    if (!response.ok) {
      setPageMessage({ type: 'error', text: await response.text() })
      return
    }
    const blob = await response.blob()
    const url = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = filename
    document.body.appendChild(link)
    link.click()
    link.remove()
    window.URL.revokeObjectURL(url)
  }

  async function handleSavePlanner() {
    const response = await authedFetch(`/insights/${majorCode}/course-planner-state`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        selected_courses: plannerSelection,
        graduation_threshold: plannerThreshold,
        min_eligible_students: plannerMinEligible,
      }),
    })
    const body = await response.json().catch(() => null)
    if (!response.ok) {
      setPlannerMessage(body?.detail || 'Planner save failed.')
      return
    }
    setPlannerMessage(`Saved ${body?.selected_courses?.length ?? 0} course offerings.`)
    queryClient.invalidateQueries({ queryKey: ['planner-state', majorCode] })
  }

  async function handleSendEmail() {
    if (!selectedStudentId) return
    const response = await authedFetch(`/emails/${majorCode}/${selectedStudentId}?template_key=${encodeURIComponent(templateKey)}`, { method: 'POST' })
    const body = await response.json().catch(() => null)
    if (!response.ok) {
      setPageMessage({ type: 'error', text: body?.detail || 'Email failed.' })
      return
    }
    setPageMessage({ type: 'success', text: body?.message || 'Email sent.' })
  }

  return (
    <section className="stack">
      <div className="page-header">
        <div>
          <div className="eyebrow">Adviser Interface</div>
          <h2>Insights</h2>
        </div>
        <label>
          <span>Major</span>
          <select value={majorCode} onChange={(event) => {
            setMajorCode(event.target.value)
            setSelectedStudentId('')
            setSelectedCourses([])
            setSemesterFilter('All Courses')
            setPendingSimulatedCourses([])
            setAppliedSimulatedCourses([])
            setPageMessage(null)
          }}>
            {majors.data?.map((major) => <option key={major.code}>{major.code}</option>)}
          </select>
        </label>
      </div>

      {pageMessage ? <div className={pageMessage.type === 'error' ? 'error-banner' : 'success-banner'}>{pageMessage.text}</div> : null}

      <div className="tab-row">
        <button type="button" className={tab === 'all' ? 'tab-button active' : 'tab-button'} onClick={() => setTab('all')}>All Students</button>
        <button type="button" className={tab === 'individual' ? 'tab-button active' : 'tab-button'} onClick={() => setTab('individual')}>Individual Student</button>
        <button type="button" className={tab === 'qaa' ? 'tab-button active' : 'tab-button'} onClick={() => setTab('qaa')}>QAA Sheet</button>
        <button type="button" className={tab === 'conflicts' ? 'tab-button active' : 'tab-button'} onClick={() => setTab('conflicts')}>Schedule Conflict</button>
        <button type="button" className={tab === 'degree' ? 'tab-button active' : 'tab-button'} onClick={() => setTab('degree')}>Degree Plan</button>
      </div>

      {tab === 'all' ? (
        <div className="stack">
          <div className="panel stack compact-panel">
            <h3>Course offering simulation</h3>
            <p>Select co-requisite or concurrent courses to simulate. Eligibility will be recalculated assuming eligible students register for them.</p>
            <label>
              <span>Simulation courses</span>
              <select multiple size={8} value={pendingSimulatedCourses} onChange={(event) => setPendingSimulatedCourses(getSelectedValues(event))}>
                {allStudents.data?.simulation_options.map((course) => <option key={course} value={course}>{course}</option>)}
              </select>
            </label>
            <div className="button-row">
              <button type="button" onClick={() => setAppliedSimulatedCourses(pendingSimulatedCourses)}>Apply simulation</button>
              <button type="button" onClick={() => { setPendingSimulatedCourses([]); setAppliedSimulatedCourses([]) }}>Clear simulation</button>
            </div>
            {appliedSimulatedCourses.length ? <p>Simulation active: {appliedSimulatedCourses.join(', ')}</p> : null}
          </div>

          <div className="panel stack compact-panel">
            <h3>Course offering planner</h3>
            <div className="field-row">
              <label><span>Graduating threshold</span><input type="number" value={plannerThreshold} onChange={(event) => setPlannerThreshold(Number(event.target.value || 30))} /></label>
              <label><span>Minimum eligible students</span><input type="number" value={plannerMinEligible} onChange={(event) => setPlannerMinEligible(Number(event.target.value || 3))} /></label>
            </div>
            <div className="scroll-table">
              <table>
                <thead><tr><th>Course</th><th>Score</th><th>Eligible</th><th>Graduating</th><th>Bottleneck</th><th>Cascading</th><th>Reason</th></tr></thead>
                <tbody>{planner.data?.map((item) => <tr key={item.course}><td>{item.course}</td><td>{item.priority_score.toFixed(1)}</td><td>{item.currently_eligible}</td><td>{item.graduating_students}</td><td>{item.bottleneck_score}</td><td>{item.cascading_eligible}</td><td>{item.reason}</td></tr>)}</tbody>
              </table>
            </div>
            <label>
              <span>Selected offerings</span>
              <select multiple size={8} value={plannerSelection} onChange={(event) => setPlannerSelection(getSelectedValues(event))}>
                {planner.data?.map((item) => <option key={item.course} value={item.course}>{item.course}</option>)}
              </select>
            </label>
            <div className="button-row">
              <button type="button" onClick={handleSavePlanner}>Save course offerings</button>
            </div>
            <p>Impact summary: serves {plannerImpact.eligible} currently eligible students, including {plannerImpact.graduating} graduating-soon students.</p>
            {plannerState.data?.saved_at ? <p>Last saved: {new Date(plannerState.data.saved_at).toLocaleString()}</p> : null}
            {plannerMessage ? <p>{plannerMessage}</p> : null}
          </div>

          <div className="panel stack">
            <div className="field-row">
              <label>
                <span>Minimum remaining credits</span>
                <input type="number" placeholder={String(allStudents.data?.remaining_range.min ?? 0)} value={remainingMin} onChange={(event) => setRemainingMin(event.target.value ? Number(event.target.value) : '')} />
              </label>
              <label>
                <span>Maximum remaining credits</span>
                <input type="number" placeholder={String(allStudents.data?.remaining_range.max ?? 0)} value={remainingMax} onChange={(event) => setRemainingMax(event.target.value ? Number(event.target.value) : '')} />
              </label>
              <label>
                <span>Semester filter</span>
                <select value={semesterFilter} onChange={(event) => setSemesterFilter(event.target.value)}>
                  {allStudents.data?.semester_options.map((option) => <option key={option}>{option}</option>)}
                </select>
              </label>
              <div className="button-slot"><button type="button" onClick={() => download(`/reports/${majorCode}/all-advised`, 'All_Advised_Students.xlsx')}>Download all advised workbook</button></div>
            </div>
            <div className="legend-row">{allStudents.data?.legend.map((item) => <span key={item.code}><strong>{item.code}</strong> {item.label}</span>)}</div>
            <div className="tab-row">
              <button type="button" className={matrixTab === 'required' ? 'tab-button active' : 'tab-button'} onClick={() => setMatrixTab('required')}>Required Courses</button>
              <button type="button" className={matrixTab === 'intensive' ? 'tab-button active' : 'tab-button'} onClick={() => setMatrixTab('intensive')}>Intensive Courses</button>
            </div>
            <label>
              <span>Visible course columns</span>
              <select multiple size={8} value={matrixColumns} onChange={updateMatrixColumns}>
                {matrixOptions.map((courseCode) => {
                  const info = allStudents.data?.course_metadata[courseCode]
                  return <option key={courseCode} value={courseCode}>{courseCode}{info?.suggested_semester ? ` · ${info.suggested_semester}` : ''}</option>
                })}
              </select>
            </label>
            <div className="button-row">
              <button type="button" onClick={() => setShowAllRows((current) => !current)}>{showAllRows ? 'Show fewer rows' : 'Show all rows'}</button>
            </div>
            <div className="scroll-table">
              <table>
                <thead>
                  <tr>
                    <th>Name</th>
                    <th>ID</th>
                    <th>Remaining</th>
                    <th>Standing</th>
                    <th>Status</th>
                    {matrixColumns.map((courseCode) => {
                      const info = allStudents.data?.course_metadata[courseCode]
                      const summary = summarizeStatuses(filteredRows, courseCode)
                      return <th key={courseCode} title={`${info?.title || courseCode}\n${info?.requisites || 'None'}\n${summary}`}>{courseCode}</th>
                    })}
                  </tr>
                </thead>
                <tbody>
                  {visibleRows.map((item) => (
                    <tr key={item.student_id}>
                      <td>{item.student_name}</td>
                      <td>{item.student_id}</td>
                      <td>{item.remaining_credits}</td>
                      <td>{item.standing}</td>
                      <td>{item.advising_status}</td>
                      {matrixColumns.map((courseCode) => <td key={`${item.student_id}-${courseCode}`}><span className={`status-pill status-${item.courses[courseCode] || 'blank'}`}>{item.courses[courseCode] || ''}</span></td>)}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {!showAllRows && filteredRows.length > visibleRows.length ? <p>Showing {visibleRows.length} of {filteredRows.length} students.</p> : null}
          </div>
        </div>
      ) : null}

      {tab === 'individual' ? (
        <div className="stack">
          <div className="panel stack compact-panel">
            <div className="field-row">
              <label><span>Search student</span><input value={searchQuery} onChange={(event) => setSearchQuery(event.target.value)} placeholder="Name or ID" /></label>
              <label><span>Select student</span><select value={selectedStudentId} onChange={(event) => setSelectedStudentId(event.target.value)}><option value="">Select student</option>{selectedStudentOptions.map((student) => <option key={student.student_id} value={student.student_id}>{student.student_name} - {student.student_id}</option>)}</select></label>
              <label><span>Email template</span><select value={templateKey} onChange={(event) => setTemplateKey(event.target.value)}>{templates.data?.map((template) => <option key={template.id} value={template.template_key}>{template.display_name}</option>)}</select></label>
              <div className="button-slot"><button type="button" onClick={() => download(`/reports/${majorCode}/individual/${selectedStudentId}${selectedCourses.length ? `?${selectedCourses.map((course) => `courses=${encodeURIComponent(course)}`).join('&')}` : ''}`, `Student_${selectedStudentId}.xlsx`)} disabled={!selectedStudentId}>Download individual report</button></div>
              <div className="button-slot"><button type="button" onClick={handleSendEmail} disabled={!selectedStudentId}>Send email</button></div>
            </div>
            <label>
              <span>Visible courses</span>
              <div className="course-chip-grid">{Object.keys(allStudents.data?.course_metadata ?? {}).slice(0, 220).map((courseCode) => <button key={courseCode} type="button" className={selectedCourses.includes(courseCode) ? 'chip active' : 'chip'} onClick={() => toggleCourse(courseCode)}>{courseCode}</button>)}</div>
            </label>
          </div>
          <div className="panel stack">
            <p>Legend: c completed, r registered, s simulated, a advised, ar advised-repeat, o optional, b bypass, na eligible not chosen, ne not eligible.</p>
            <div className="scroll-table">
              <table>
                <thead><tr><th>Course</th><th>Title</th><th>Status</th><th>Semester</th><th>Requisites</th></tr></thead>
                <tbody>{individual.data?.selected_courses.map((course) => <tr key={course}><td>{course}</td><td>{allStudents.data?.course_metadata[course]?.title || course}</td><td><span className={`status-pill status-${individual.data?.statuses[course] || 'blank'}`}>{individual.data?.statuses[course]}</span></td><td>{allStudents.data?.course_metadata[course]?.suggested_semester || ''}</td><td>{allStudents.data?.course_metadata[course]?.requisites || ''}</td></tr>)}</tbody>
              </table>
            </div>
          </div>
        </div>
      ) : null}

      {tab === 'qaa' ? (
        <div className="stack">
          <div className="panel stack compact-panel">
            <div className="field-row">
              <label><span>Graduating threshold</span><input type="number" value={graduatingThreshold} onChange={(event) => setGraduatingThreshold(Number(event.target.value || 36))} /></label>
              <div className="button-slot"><button type="button" onClick={() => download(`/reports/${majorCode}/qaa?graduating_threshold=${graduatingThreshold}`, `QAA_Sheet_${majorCode}.xlsx`)}>Download QAA workbook</button></div>
            </div>
          </div>
          <div className="panel scroll-table">
            <table>
              <thead><tr><th>Course</th><th>Name</th><th>Eligibility</th><th>Advised</th><th>Optional</th><th>Not Advised</th><th>Skipped Advising</th><th>Attended + Graduating</th><th>Skipped + Graduating</th></tr></thead>
              <tbody>{qaa.data?.map((item) => <tr key={item.course_code}><td>{item.course_code}</td><td>{item.course_name}</td><td>{item.eligibility}</td><td>{item.advised}</td><td>{item.optional}</td><td>{item.not_advised}</td><td>{item.skipped_advising}</td><td>{item.attended_graduating}</td><td>{item.skipped_graduating}</td></tr>)}</tbody>
            </table>
          </div>
        </div>
      ) : null}

      {tab === 'conflicts' ? (
        <div className="stack">
          <div className="panel stack compact-panel">
            <div className="field-row">
              <label><span>Target max groups</span><input type="number" value={targetGroups} onChange={(event) => setTargetGroups(Number(event.target.value || 10))} /></label>
              <label><span>Max courses per group</span><input type="number" value={maxCoursesPerGroup} onChange={(event) => setMaxCoursesPerGroup(Number(event.target.value || 10))} /></label>
              <label><span>Minimum students</span><input type="number" value={minStudents} onChange={(event) => setMinStudents(Number(event.target.value || 1))} /></label>
              <label><span>Minimum courses</span><input type="number" value={minCourses} onChange={(event) => setMinCourses(Number(event.target.value || 2))} /></label>
              <div className="button-slot"><button type="button" onClick={() => download(`/reports/${majorCode}/schedule-conflicts?target_groups=${targetGroups}&max_courses_per_group=${maxCoursesPerGroup}&min_students=${minStudents}&min_courses=${minCourses}`, `schedule_conflict_${majorCode}.csv`)}>Download CSV</button></div>
            </div>
          </div>
          <div className="panel scroll-table">
            <table>
              <thead><tr><th>Courses</th><th>Students</th><th>Course Count</th><th>Student IDs</th></tr></thead>
              <tbody>{conflicts.data?.map((item) => <tr key={item.group_name}><td>{item.group_name}</td><td>{item.student_count}</td><td>{item.course_count}</td><td>{item.student_ids.join(', ')}</td></tr>)}</tbody>
            </table>
          </div>
        </div>
      ) : null}

      {tab === 'degree' ? (
        <div className="stack">
          <div className="panel stack compact-panel">
            <div className="field-row">
              <label><span>Select student</span><select value={selectedStudentId} onChange={(event) => setSelectedStudentId(event.target.value)}><option value="">Select student</option>{selectedStudentOptions.map((student) => <option key={student.student_id} value={student.student_id}>{student.student_name} - {student.student_id}</option>)}</select></label>
            </div>
            {degreePlan.data?.student ? <p>{degreePlan.data.student.student_name} · {degreePlan.data.student.standing} · Remaining {degreePlan.data.student.remaining_credits}</p> : null}
            <div className="legend-row">{degreePlan.data?.legend.map((item) => <span key={item.status}>{item.icon} {item.label}</span>)}</div>
          </div>
          {degreePlan.data?.years.map((year) => (
            <div key={year.year_name} className="panel stack">
              <h3>{year.year_name}</h3>
              <div className="degree-grid">
                {year.semesters.map((semester) => (
                  <div key={semester.semester_key} className="degree-card">
                    <strong>{semester.semester_key}</strong>
                    <span>{semester.total_credits} credits</span>
                    <div className="mini-list">
                      {semester.courses.map((course) => <div key={course.code} className="mini-item"><div><strong>{course.code}</strong><p>{course.title}</p></div><span>{course.status}</span></div>)}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      ) : null}
    </section>
  )
}
