import { FormEvent, useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'

import { API_BASE_URL } from '../../lib/api'
import { useMajors, usePeriods } from '../../lib/hooks'

export function PeriodsPage() {
  const queryClient = useQueryClient()
  const [majorCode, setMajorCode] = useState('PBHL')
  const [semester, setSemester] = useState('Fall')
  const [year, setYear] = useState(new Date().getFullYear())
  const [advisorName, setAdvisorName] = useState('Default Adviser')
  const [message, setMessage] = useState<string | null>(null)
  const majors = useMajors()
  const periods = usePeriods(majorCode)

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    const token = window.localStorage.getItem('advising_v2_token')
    const response = await fetch(`${API_BASE_URL}/api/periods`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify({ major_code: majorCode, semester, year, advisor_name: advisorName }),
    })
    setMessage(response.ok ? 'Period created.' : await response.text())
    queryClient.invalidateQueries({ queryKey: ['periods', majorCode] })
  }

  async function handleActivate(periodCode: string) {
    const token = window.localStorage.getItem('advising_v2_token')
    const response = await fetch(`${API_BASE_URL}/api/periods/${periodCode}/activate`, {
      method: 'POST',
      headers: {
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
    })
    setMessage(response.ok ? 'Period activated.' : await response.text())
    queryClient.invalidateQueries({ queryKey: ['periods', majorCode] })
  }

  return (
    <section className="stack">
      <div className="page-header"><div><div className="eyebrow">Admin Panel</div><h2>Advising Periods</h2></div></div>
      <form className="panel stack" onSubmit={handleSubmit}>
        <div className="field-row">
          <label><span>Major</span><select value={majorCode} onChange={(event) => setMajorCode(event.target.value)}>{majors.data?.map((major) => <option key={major.code} value={major.code}>{major.code}</option>)}</select></label>
          <label><span>Semester</span><select value={semester} onChange={(event) => setSemester(event.target.value)}><option>Fall</option><option>Spring</option><option>Summer</option></select></label>
          <label><span>Year</span><input type="number" value={year} onChange={(event) => setYear(Number(event.target.value))} /></label>
          <label><span>Advisor</span><input value={advisorName} onChange={(event) => setAdvisorName(event.target.value)} /></label>
        </div>
        <button type="submit">Create active period</button>
        {message ? <div className="alert">{message}</div> : null}
      </form>
      <div className="panel">
        <h3>Period history</h3>
        <table><thead><tr><th>Code</th><th>Semester</th><th>Year</th><th>Advisor</th><th>Status</th><th>Action</th></tr></thead><tbody>{periods.data?.map((period) => <tr key={period.id}><td>{period.period_code}</td><td>{period.semester}</td><td>{period.year}</td><td>{period.advisor_name}</td><td>{period.is_active ? 'Active' : 'Inactive'}</td><td>{period.is_active ? 'Current' : <button type="button" onClick={() => handleActivate(period.period_code)}>Activate</button>}</td></tr>)}</tbody></table>
      </div>
    </section>
  )
}
