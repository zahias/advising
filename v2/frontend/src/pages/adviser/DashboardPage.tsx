import { useState } from 'react'

import { useDashboard, useMajors } from '../../lib/hooks'
import { StatCard } from '../../components/StatCard'

export function DashboardPage() {
  const [majorCode, setMajorCode] = useState('PBHL')
  const majors = useMajors()
  const dashboard = useDashboard(majorCode)
  return (
    <section className="stack">
      <div className="page-header"><div><div className="eyebrow">Adviser Interface</div><h2>Dashboard</h2></div><label><span>Major</span><select value={majorCode} onChange={(event) => setMajorCode(event.target.value)}>{majors.data?.map((major) => <option key={major.code}>{major.code}</option>)}</select></label></div>
      <div className="stats-grid">
        <StatCard label="Students" value={dashboard.data?.total_students ?? 0} detail="Loaded from active dataset" />
        <StatCard label="Advised" value={dashboard.data?.advised_students ?? 0} detail="Saved in active period" />
        <StatCard label="Not Advised" value={dashboard.data?.not_advised_students ?? 0} detail="Still pending" />
        <StatCard label="Progress" value={`${dashboard.data?.progress_percent ?? 0}%`} detail="Roster completion" />
      </div>
      <div className="two-column">
        <div className="panel"><h3>Graduating soon, not advised</h3><ul>{dashboard.data?.graduating_soon_unadvised.map((name) => <li key={name}>{name}</li>)}</ul></div>
        <div className="panel"><h3>Recent activity</h3><ul>{dashboard.data?.recent_activity.map((item) => <li key={item.created_at}>{item.student_name} · {new Date(item.created_at).toLocaleString()}</li>)}</ul></div>
      </div>
    </section>
  )
}
