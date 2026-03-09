import { useState } from 'react'
import { API_BASE_URL, StudentEligibility, TemplatePreview } from '../../lib/api'

interface Props {
  student: StudentEligibility
  activePeriod?: { semester: string; year: number }
  majorCode: string
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
  majorCode,
  templateKey,
  templates,
  onTemplateChange,
  onEmail,
  onRestoreLatest,
  onRecommend,
  onDownloadReport,
}: Props) {
  const [showPreview, setShowPreview] = useState(false)
  const [preview, setPreview] = useState<TemplatePreview | null>(null)
  const [previewLoading, setPreviewLoading] = useState(false)

  async function loadPreview() {
    if (showPreview) { setShowPreview(false); return }
    setPreviewLoading(true)
    try {
      const token = window.localStorage.getItem('advising_v2_token')
      const resp = await fetch(`${API_BASE_URL}/api/templates/preview?major_code=${encodeURIComponent(majorCode)}&student_id=${encodeURIComponent(student.student_id)}&template_key=${encodeURIComponent(templateKey)}`, {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      })
      if (resp.ok) {
        setPreview(await resp.json())
        setShowPreview(true)
      }
    } catch { /* ignore */ }
    setPreviewLoading(false)
  }

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
          <button type="button" className="btn-outline btn-sm" onClick={loadPreview} disabled={previewLoading}>
            {previewLoading ? '...' : showPreview ? 'Hide Preview' : '👁 Preview'}
          </button>
          <button type="button" className="btn-primary" onClick={onEmail}>Email Student</button>
        </div>
      </div>

      {showPreview && preview && (
        <div style={{ marginTop: '12px', padding: '16px', background: '#f8fafc', border: '1px solid #e2e8f0', borderRadius: '12px' }}>
          <div style={{ fontSize: '11px', textTransform: 'uppercase', fontWeight: 600, color: '#94a3b8', letterSpacing: '0.05em', marginBottom: '6px' }}>Email Preview</div>
          <div style={{ fontSize: '13px', fontWeight: 600, color: '#1e293b', marginBottom: '8px' }}>Subject: {preview.subject}</div>
          <div style={{ fontSize: '12px', color: '#475569', background: 'white', border: '1px solid #e2e8f0', borderRadius: '8px', padding: '12px', maxHeight: '200px', overflow: 'auto', fontFamily: 'monospace', whiteSpace: 'pre-wrap' }} dangerouslySetInnerHTML={{ __html: preview.preview_body }} />
        </div>
      )}
    </div>
  )
}
