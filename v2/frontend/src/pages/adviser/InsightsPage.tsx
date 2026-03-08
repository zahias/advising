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
    <section className="insights-container stack">
      <div className="page-header flex-between mb-4">
        <div>
          <div className="eyebrow text-muted">Data Intelligence</div>
          <h2>Actionable Insights</h2>
        </div>
        <div className="header-actions">
          <label className="inline-select">
            <span className="text-muted">Master Program:</span>
            <select className="select-input" value={majorCode} onChange={(event) => {
              setMajorCode(event.target.value)
              setSelectedStudentId('')
              setSelectedCourses([])
              setSemesterFilter('All Courses')
              setPendingSimulatedCourses([])
              setAppliedSimulatedCourses([])
              setPageMessage(null)
            }}>
              {majors.data?.map((major) => <option key={major.code} value={major.code}>{major.code}</option>)}
            </select>
          </label>
        </div>
      </div>

      {pageMessage && (
        <div className={`alert mb-4 ${pageMessage.type === 'error' ? 'alert-error' : 'alert-success'}`}>
          {pageMessage.text}
          <button type="button" className="close-btn" onClick={() => setPageMessage(null)}>&times;</button>
        </div>
      )}

      <div className="workspace-tabs-nav mb-4">
        <button type="button" className={`tab-btn ${tab === 'all' ? 'active' : ''}`} onClick={() => setTab('all')}>All Students Report</button>
        <button type="button" className={`tab-btn ${tab === 'individual' ? 'active' : ''}`} onClick={() => setTab('individual')}>Deep Dive: Individual</button>
        <button type="button" className={`tab-btn ${tab === 'qaa' ? 'active' : ''}`} onClick={() => setTab('qaa')}>QAA Projections</button>
        <button type="button" className={`tab-btn ${tab === 'conflicts' ? 'active' : ''}`} onClick={() => setTab('conflicts')}>Schedule Conflicts</button>
        <button type="button" className={`tab-btn ${tab === 'degree' ? 'active' : ''}`} onClick={() => setTab('degree')}>Degree Plan Maps</button>
      </div>

      {tab === 'all' && (
        <div className="stack">
          {/* SIMULATION & PLANNER CARDS DE-CLUTTERED */}
          <div className="grid-2">
            <div className="panel stack">
              <h3>Simulation Engine</h3>
              <p className="text-muted text-sm">Simulate corequisite or concurrent course offerings to project eligibility impacts instantly.</p>
              
              <div className="form-group mb-4">
                <label className="text-muted font-semibold text-sm mb-2 block">Available courses to simulate</label>
                <select className="select-input" multiple size={5} value={pendingSimulatedCourses} onChange={(event) => setPendingSimulatedCourses(getSelectedValues(event))}>
                  {allStudents.data?.simulation_options.map((course) => <option key={course} value={course}>{course}</option>)}
                </select>
              </div>
              
              <div className="flex-gap-4">
                <button type="button" className="btn-primary" onClick={() => setAppliedSimulatedCourses(pendingSimulatedCourses)}>Run Simulation</button>
                <button type="button" className="btn-secondary" onClick={() => { setPendingSimulatedCourses([]); setAppliedSimulatedCourses([]) }}>Clear</button>
              </div>
              
              {appliedSimulatedCourses.length > 0 && (
                <div className="success-banner mt-4 text-sm">
                  <strong>Active Simulation:</strong> {appliedSimulatedCourses.join(', ')}
                </div>
              )}
            </div>

            <div className="panel stack">
              <div className="flex-between">
                <h3>Course Offering Planner</h3>
                <button type="button" className="btn-secondary btn-sm" onClick={handleSavePlanner}>Save Plan</button>
              </div>
              <p className="text-muted text-sm">Target offerings based on bottleneck scores and graduating thresholds.</p>
              
              <div className="filter-bar mb-4 p-0 border-none justify-start">
                <div className="filter-group">
                  <label>Grad. Threshold</label>
                  <input type="number" value={plannerThreshold} onChange={(event) => setPlannerThreshold(Number(event.target.value || 30))} />
                </div>
                <div className="filter-group">
                  <label>Min Eligible</label>
                  <input type="number" value={plannerMinEligible} onChange={(event) => setPlannerMinEligible(Number(event.target.value || 3))} />
                </div>
              </div>
              
              <div className="form-group">
                <label className="text-muted font-semibold text-sm mb-2 block">Select Offerings to commit</label>
                <select className="select-input" multiple size={4} value={plannerSelection} onChange={(event) => setPlannerSelection(getSelectedValues(event))}>
                  {planner.data?.map((item) => <option key={item.course} value={item.course}>{item.course} (Score: {item.priority_score.toFixed(1)})</option>)}
                </select>
              </div>
              
              <div className="text-sm text-muted mt-2 border-t pt-2 border-gray-100">
                Plan Impact: Serves <strong>{plannerImpact.eligible}</strong> globally eligible students, including <strong>{plannerImpact.graduating}</strong> graduating seniors.
                {plannerMessage && <div className="text-accent font-semibold mt-1">{plannerMessage}</div>}
              </div>
            </div>
          </div>

          <div className="panel stack mt-4">
            <div className="flex-between items-center mb-4">
              <h3>Global Student Matrix</h3>
              <button type="button" className="btn-secondary" onClick={() => download(`/reports/${majorCode}/all-advised`, 'All_Advised_Students.xlsx')}>
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="mr-2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" x2="12" y1="15" y2="3"/></svg>
                Export Excel
              </button>
            </div>
            
            <div className="filter-bar">
              <div className="filter-group">
                <label>Min Remaining Cr.</label>
                <input type="number" placeholder={String(allStudents.data?.remaining_range.min ?? 0)} value={remainingMin} onChange={(event) => setRemainingMin(event.target.value ? Number(event.target.value) : '')} />
              </div>
              <div className="filter-group">
                <label>Max Remaining Cr.</label>
                <input type="number" placeholder={String(allStudents.data?.remaining_range.max ?? 0)} value={remainingMax} onChange={(event) => setRemainingMax(event.target.value ? Number(event.target.value) : '')} />
              </div>
              <div className="filter-group">
                <label>Semester Goal</label>
                <select value={semesterFilter} onChange={(event) => setSemesterFilter(event.target.value)}>
                  {allStudents.data?.semester_options.map((option) => <option key={option} value={option}>{option}</option>)}
                </select>
              </div>
              
              <div className="filter-group ml-auto">
                <div className="workspace-tabs-nav p-0 border-none gap-0 scale-90 origin-right">
                  <button type="button" className={`tab-btn bg-white border ${matrixTab === 'required' ? 'active shadow-sm' : ''}`} onClick={() => setMatrixTab('required')}>Required</button>
                  <button type="button" className={`tab-btn bg-white border ${matrixTab === 'intensive' ? 'active shadow-sm' : ''}`} onClick={() => setMatrixTab('intensive')}>Intensive</button>
                </div>
              </div>
            </div>
            
            <div className="legend-row mb-4 p-4 bg-gray-50 rounded-xl text-sm border">
               <span className="font-semibold text-muted mr-4">Legend:</span>
               {allStudents.data?.legend.map((item) => <span key={item.code} className="flex items-center gap-1"><span className={`status-pill w-8 status-${item.code}`}></span> {item.label}</span>)}
            </div>

            <div className="flex-between items-end mb-2">
               <p className="text-sm text-muted">Showing {visibleRows.length} of {filteredRows.length} students.</p>
               <button type="button" className="btn-outline btn-sm" onClick={() => setShowAllRows((current) => !current)}>{showAllRows ? 'Show Paginated (80 max)' : 'Show Full List'}</button>
            </div>

            <div className="premium-table-wrapper" style={{ maxHeight: '600px', overflowY: 'auto' }}>
              <table className="premium-table">
                <thead>
                  <tr>
                    <th className="sticky-col z-20 min-w-48 bg-gray-50 border-r">Student Name</th>
                    <th>ID</th>
                    <th>Remaining</th>
                    <th>Standing</th>
                    <th>Status</th>
                    {matrixColumns.map((courseCode) => {
                      const info = allStudents.data?.course_metadata[courseCode]
                      const summary = summarizeStatuses(filteredRows, courseCode)
                      return <th key={courseCode} title={`${info?.title || courseCode}\n${info?.requisites || 'None'}\n${summary}`} className="text-center min-w-24 border-l cursor-help hover:bg-gray-100">{courseCode}</th>
                    })}
                  </tr>
                </thead>
                <tbody>
                  {visibleRows.length === 0 ? (
                    <tr><td colSpan={5 + matrixColumns.length} className="text-center p-8 text-muted">No students found matching your filters.</td></tr>
                  ) : (
                    visibleRows.map((item) => (
                      <tr key={item.student_id}>
                        <td className="sticky-col bg-white font-medium border-r shadow-[1px_0_0_rgba(0,0,0,0.05)]">{item.student_name}</td>
                        <td className="mono text-muted text-sm">{item.student_id}</td>
                        <td className="text-center">{item.remaining_credits}</td>
                        <td className="text-center">{item.standing}</td>
                        <td className="text-center">{item.advising_status}</td>
                        {matrixColumns.map((courseCode) => (
                          <td key={`${item.student_id}-${courseCode}`} className="text-center border-l bg-gray-50/30">
                            {item.courses[courseCode] ? (
                               <span className={`status-pill status-${item.courses[courseCode]}`}>{item.courses[courseCode]}</span>
                            ) : (
                               <span className="text-gray-300">-</span>
                            )}
                          </td>
                        ))}
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {tab === 'individual' && (
        <div className="stack">
          <div className="filter-bar panel">
            <div className="filter-group flex-1">
              <label>Search Directory</label>
              <div className="search-box">
                 <svg className="search-icon h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/></svg>
                <input className="w-full pl-10" value={searchQuery} onChange={(event) => setSearchQuery(event.target.value)} placeholder="Name or ID" />
              </div>
            </div>
            <div className="filter-group flex-1">
              <label>Select Student Focus</label>
              <select value={selectedStudentId} onChange={(event) => setSelectedStudentId(event.target.value)}>
                <option value="">Select an enrolled student</option>
                {selectedStudentOptions.map((student) => <option key={student.student_id} value={student.student_id}>{student.student_name}</option>)}
              </select>
            </div>
            
            <div className="filter-group border-l pl-4 ml-2">
               <label>Communications</label>
               <div className="flex-gap-4">
                 <select value={templateKey} onChange={(event) => setTemplateKey(event.target.value)}>
                   {templates.data?.map((template) => <option key={template.id} value={template.template_key}>{template.display_name}</option>)}
                 </select>
                 <button type="button" className="btn-primary whitespace-nowrap" onClick={handleSendEmail} disabled={!selectedStudentId}>Send Mail</button>
               </div>
            </div>
          </div>

          {!selectedStudentId ? (
            <div className="blank-slate-panel panel rounded-2xl">
              <div className="blank-slate-content">
                <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1" className="text-muted"><path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/></svg>
                <h3>Select a Student profile</h3>
                <p className="text-muted">Use the search filters above to drill down into a specific student's eligibility and requisites map.</p>
              </div>
            </div>
          ) : (
            <div className="panel stack mt-2">
              <div className="flex-between mb-4">
                 <div>
                    <h3 className="mb-1">Academic Requisites Map</h3>
                    <p className="text-muted text-sm">Visualizing specific course overrides and statuses.</p>
                 </div>
                 <button type="button" className="btn-secondary" onClick={() => download(`/reports/${majorCode}/individual/${selectedStudentId}${selectedCourses.length ? `?${selectedCourses.map((course) => `courses=${encodeURIComponent(course)}`).join('&')}` : ''}`, `Student_${selectedStudentId}.xlsx`)}>
                   Export Individual Sheet
                 </button>
              </div>

               <div className="mb-4">
                <label className="text-muted font-semibold text-xs uppercase tracking-wider mb-2 block">Available Visibility Toggles</label>
                <div className="course-chip-grid">
                  {Object.keys(allStudents.data?.course_metadata ?? {}).slice(0, 50).map((courseCode) => (
                    <button key={courseCode} type="button" className={`chip ${selectedCourses.includes(courseCode) ? 'active' : ''}`} onClick={() => toggleCourse(courseCode)}>
                      {courseCode}
                    </button>
                  ))}
                  {Object.keys(allStudents.data?.course_metadata ?? {}).length > 50 && <span className="chip bg-transparent border-none text-muted">+{Object.keys(allStudents.data?.course_metadata ?? {}).length - 50} more... limit applied.</span>}
                </div>
              </div>

              <div className="premium-table-wrapper">
                <table className="premium-table">
                  <thead><tr><th>Course</th><th>Title</th><th>Status</th><th>Target Term</th><th>Requisites Tree</th></tr></thead>
                  <tbody>
                    {individual.data?.selected_courses.length === 0 ? (
                      <tr><td colSpan={5} className="text-center p-8 text-muted">Select courses from the toggles above to build the visibility map.</td></tr>
                    ) : (
                      individual.data?.selected_courses.map((course) => (
                        <tr key={course}>
                          <td className="font-semibold mono">{course}</td>
                          <td>{allStudents.data?.course_metadata[course]?.title || course}</td>
                          <td><span className={`status-pill status-${individual.data?.statuses[course] || 'blank'}`}>{individual.data?.statuses[course]}</span></td>
                          <td>{allStudents.data?.course_metadata[course]?.suggested_semester || '-'}</td>
                          <td className="text-sm text-gray-500">{allStudents.data?.course_metadata[course]?.requisites || 'None'}</td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      )}

      {tab === 'qaa' && (
        <div className="stack">
          <div className="filter-bar panel">
            <div className="filter-group">
              <label>Graduating Threshold Level</label>
              <input type="number" value={graduatingThreshold} onChange={(event) => setGraduatingThreshold(Number(event.target.value || 36))} />
            </div>
            <div className="filter-group ml-auto">
              <button type="button" className="btn-secondary" onClick={() => download(`/reports/${majorCode}/qaa?graduating_threshold=${graduatingThreshold}`, `QAA_Sheet_${majorCode}.xlsx`)}>
                 Export Workbook
              </button>
            </div>
          </div>

          <div className="panel premium-table-wrapper">
            <table className="premium-table">
              <thead>
                <tr>
                  <th>Course Data</th>
                  <th>Eligibility Pool</th>
                  <th className="bg-green-50/30">Advised Alloc.</th>
                  <th className="bg-yellow-50/30">Optional</th>
                  <th className="bg-red-50/30">Not Advised</th>
                  <th className="border-l">Bottlenecks (Not Advised & Grad)</th>
                </tr>
              </thead>
              <tbody>
                {qaa.data?.length === 0 ? (
                  <tr><td colSpan={6} className="text-center p-8 text-muted">No QAA projections generated for this program.</td></tr>
                ) : (
                  qaa.data?.map((item) => (
                  <tr key={item.course_code}>
                    <td>
                      <div className="font-semibold">{item.course_code}</div>
                      <div className="text-xs text-muted truncate max-w-xs" title={item.course_name}>{item.course_name}</div>
                    </td>
                    <td className="text-center text-lg">{item.eligibility}</td>
                    <td className="text-center font-medium bg-green-50/10">{item.advised}</td>
                    <td className="text-center bg-yellow-50/10">{item.optional}</td>
                    <td className="text-center bg-red-50/10">{item.not_advised}</td>
                    <td className="text-center border-l">
                      <div className="flex justify-center gap-4 text-sm">
                         <span title="Skipped Advising" className="text-gray-500 font-mono">SA:{item.skipped_advising}</span>
                         <span title="Graduating Warning" className="text-red-600 font-semibold font-mono">W:{item.skipped_graduating}</span>
                      </div>
                    </td>
                  </tr>
                )))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {tab === 'conflicts' && (
        <div className="stack">
          <div className="filter-bar panel">
            <div className="filter-group">
              <label>Target Groups Limit</label>
              <input type="number" value={targetGroups} onChange={(event) => setTargetGroups(Number(event.target.value || 10))} />
            </div>
            <div className="filter-group">
              <label>Max Courses / Group</label>
              <input type="number" value={maxCoursesPerGroup} onChange={(event) => setMaxCoursesPerGroup(Number(event.target.value || 10))} />
            </div>
            <div className="filter-group border-l pl-4 ml-2">
              <label>Minimums</label>
              <div className="flex-gap-4">
                 <input type="number" placeholder="Students" title="Min Students" className="w-24" value={minStudents} onChange={(event) => setMinStudents(Number(event.target.value || 1))} />
                 <input type="number" placeholder="Courses" title="Min Courses" className="w-24" value={minCourses} onChange={(event) => setMinCourses(Number(event.target.value || 2))} />
              </div>
            </div>
            <div className="filter-group ml-auto">
              <button type="button" className="btn-secondary" onClick={() => download(`/reports/${majorCode}/schedule-conflicts?target_groups=${targetGroups}&max_courses_per_group=${maxCoursesPerGroup}&min_students=${minStudents}&min_courses=${minCourses}`, `schedule_conflict_${majorCode}.csv`)}>Download CSV</button>
            </div>
          </div>

          <div className="panel premium-table-wrapper">
            <table className="premium-table">
              <thead><tr><th>Identified Conflict Clusters</th><th>At Risk Students</th><th>Course Matrix Count</th><th>Affected Student Roster (IDs)</th></tr></thead>
              <tbody>
                {conflicts.data?.length === 0 ? (
                  <tr><td colSpan={4} className="text-center p-8 text-muted">No schedule conflicts detected under the current constraints.</td></tr>
                ) : (
                  conflicts.data?.map((item) => (
                    <tr key={item.group_name}>
                      <td className="font-mono text-sm tracking-tighter" style={{ maxWidth: '300px' }}><div className="flex flex-wrap gap-1">{item.group_name.split(', ').map(c => <span key={c} className="bg-gray-100 px-2 py-0.5 rounded text-gray-700">{c}</span>)}</div></td>
                      <td className="text-center text-lg">{item.student_count}</td>
                      <td className="text-center text-muted">{item.course_count}</td>
                      <td className="text-xs text-muted" style={{ maxWidth: '400px' }}>{item.student_ids.join(', ')}</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {tab === 'degree' && (
        <div className="stack">
          <div className="filter-bar panel">
            <div className="filter-group flex-1 max-w-md">
              <label>Student Profile</label>
              <select value={selectedStudentId} onChange={(event) => setSelectedStudentId(event.target.value)} className="w-full">
                <option value="">Select an enrolled student</option>
                {selectedStudentOptions.map((student) => <option key={student.student_id} value={student.student_id}>{student.student_name} - {student.student_id}</option>)}
              </select>
            </div>
            
            {degreePlan.data?.student && (
              <div className="ml-8 border-l pl-4 py-1 flex flex-col justify-center">
                 <div className="font-semibold">{degreePlan.data.student.student_name}</div>
                 <div className="text-sm text-muted">{degreePlan.data.student.standing} • {degreePlan.data.student.remaining_credits} Cr. Remaining</div>
              </div>
            )}
          </div>

          {selectedStudentId && degreePlan.data ? (
            <div className="stack">
               <div className="legend-row bg-white p-3 rounded-xl border flex justify-center">{degreePlan.data?.legend.map((item) => <span key={item.status} className="text-sm font-medium"><span className="text-lg mr-1">{item.icon}</span> {item.label}</span>)}</div>
               
               <div className="grid-2">
                 {degreePlan.data?.years.map((year) => (
                   <div key={year.year_name} className="panel">
                     <div className="flex-between border-b pb-2 mb-4">
                       <h3 className="text-accent mb-0">{year.year_name}</h3>
                     </div>
                     <div className="degree-grid">
                       {year.semesters.map((semester) => (
                         <div key={semester.semester_key} className="degree-card !gap-2 !p-3">
                           <div className="flex-between">
                             <strong className="text-sm">{semester.semester_key}</strong>
                             <span className="badge badge-info">{semester.total_credits} cr</span>
                           </div>
                           <div className="mt-2 space-y-2">
                             {semester.courses.map((course) => (
                               <div key={course.code} className="bg-gray-50 rounded-lg p-2 border flex justify-between items-center group hover:bg-white transition-colors">
                                 <div>
                                   <div className="font-semibold text-xs mono mb-0.5">{course.code}</div>
                                   <div className="text-[10px] text-muted truncate max-w-[140px]" title={course.title}>{course.title}</div>
                                 </div>
                                 <span className="text-base" title={course.status}>{course.status.includes('Completed') ? '✅' : course.status.includes('Registered') ? '🔄' : '📝'}</span>
                               </div>
                             ))}
                           </div>
                         </div>
                       ))}
                     </div>
                   </div>
                 ))}
               </div>
            </div>
          ) : (
            <div className="blank-slate-panel panel rounded-2xl">
              <div className="blank-slate-content">
                <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1" className="text-muted"><path d="M4 19.5v-15A2.5 2.5 0 0 1 6.5 2H20v20H6.5a2.5 2.5 0 0 1 0-5H20"/></svg>
                <h3>View Degree Maps</h3>
                <p className="text-muted">Select a student from the dropdown to visually plot out their historic and projected academic term roadmap.</p>
              </div>
            </div>
          )}
        </div>
      )}
    </section>
  )
}
