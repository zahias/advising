import { StudentEligibility } from '../../lib/api'

interface Props {
  student: StudentEligibility
  activePeriod?: { semester: string; year: number }
  templateKey: string
  templates: { id: number; template_key: string; display_name: string }[]
  onTemplateChange: (key: string) => void
  onEmail: () => void
  onRestoreLatest: () => void
  onRecommend: () => void
  onDownloadReport: () => void
}

export function StudentProfileHeader({
  student,
  activePeriod,
  templateKey,
  templates,
  onTemplateChange,
  onEmail,
  onRestoreLatest,
  onRecommend,
  onDownloadReport,
}: Props) {
  return (
    <div className="student-profile-header">
      <div className="profile-main">
        <div className="profile-identity">
          <h3>{student.student_name}</h3>
          <p>ID <span className="mono">{student.student_id}</span></p>
        </div>
        <div className="profile-stats">
          <div className="stat-group">
            <div className="eyebrow">Standing</div>
            <div className="stat-value">{student.standing}</div>
          </div>
          <div className="stat-group">
            <div className="eyebrow">Remaining</div>
            <div className="stat-value">{student.credits_remaining}</div>
          </div>
          <div className="stat-group">
            <div className="eyebrow">Current Period</div>
            <div className="stat-value">{activePeriod ? `${activePeriod.semester} ${activePeriod.year}` : 'Missing'}</div>
          </div>
        </div>
      </div>

      <div className="profile-actions">
        <div className="action-row">
          <button type="button" className="btn-secondary" onClick={onRestoreLatest} disabled={!activePeriod}>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8" /><path d="M3 3v5h5" /><path d="M12 7v5l4 2" /></svg>
            Restore Latest
          </button>
          <button type="button" className="btn-secondary" onClick={onRecommend}>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="m12 3-1.912 5.813a2 2 0 0 1-1.275 1.275L3 12l5.813 1.912a2 2 0 0 1 1.275 1.275L12 21l1.912-5.813a2 2 0 0 1 1.275-1.275L21 12l-5.813-1.912a2 2 0 0 1-1.275-1.275L12 3Z" /></svg>
            Recommend
          </button>
          <button type="button" className="btn-secondary" onClick={onDownloadReport}>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" /><polyline points="7 10 12 15 17 10" /><line x1="12" x2="12" y1="15" y2="3" /></svg>
            Download Report
          </button>
        </div>
        <div className="action-row email-row">
          <select value={templateKey} onChange={(e) => onTemplateChange(e.target.value)} className="select-sm">
            {templates.map((t) => <option key={t.id} value={t.template_key}>{t.display_name}</option>)}
          </select>
          <button type="button" className="btn-primary" onClick={onEmail}>Email Student</button>
        </div>
      </div>
    </div>
  )
}
