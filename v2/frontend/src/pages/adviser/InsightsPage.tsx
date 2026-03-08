import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'

import { apiFetch } from '../../lib/api'
import { useMajors } from '../../lib/hooks'

export function InsightsPage() {
  const [majorCode, setMajorCode] = useState('PBHL')
  const majors = useMajors()
  const planner = useQuery({ queryKey: ['planner', majorCode], queryFn: () => apiFetch<any[]>(`/insights/${majorCode}/course-planner`) })
  const allStudents = useQuery({ queryKey: ['all-students', majorCode], queryFn: () => apiFetch<any[]>(`/insights/${majorCode}/all-students`) })
  const qaa = useQuery({ queryKey: ['qaa', majorCode], queryFn: () => apiFetch<any[]>(`/insights/${majorCode}/qaa`) })
  const conflicts = useQuery({ queryKey: ['schedule-conflicts', majorCode], queryFn: () => apiFetch<any[]>(`/insights/${majorCode}/schedule-conflicts`) })

  return (
    <section className="stack">
      <div className="page-header"><div><div className="eyebrow">Adviser Interface</div><h2>Insights</h2></div><label><span>Major</span><select value={majorCode} onChange={(event) => setMajorCode(event.target.value)}>{majors.data?.map((major) => <option key={major.code}>{major.code}</option>)}</select></label></div>
      <div className="two-column">
        <div className="panel"><h3>Course offering planner</h3><ul>{planner.data?.slice(0, 8).map((item) => <li key={item.course}>{item.course} · score {item.priority_score}</li>)}</ul></div>
        <div className="panel"><h3>All students</h3><div className="scroll-table"><table><thead><tr><th>Name</th><th>Standing</th><th>Status</th></tr></thead><tbody>{allStudents.data?.slice(0, 20).map((item) => <tr key={item.student_id}><td>{item.student_name}</td><td>{item.standing}</td><td>{item.advising_status}</td></tr>)}</tbody></table></div></div>
      </div>
      <div className="two-column">
        <div className="panel"><h3>QAA snapshot</h3><div className="scroll-table"><table><thead><tr><th>Name</th><th>Remaining</th><th>Status</th></tr></thead><tbody>{qaa.data?.slice(0, 12).map((item) => <tr key={item.student_id}><td>{item.student_name}</td><td>{item.remaining_credits}</td><td>{item.advising_status}</td></tr>)}</tbody></table></div></div>
        <div className="panel"><h3>Schedule conflict groups</h3><ul>{conflicts.data?.map((item) => <li key={item.group_name}>{item.group_name} · {item.student_count} students</li>)}</ul></div>
      </div>
    </section>
  )
}
