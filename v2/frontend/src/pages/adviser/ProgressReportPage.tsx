import { useState } from 'react'

import { API_BASE_URL, ExtraCourseRow, ProgressCellData } from '../../lib/api'
import { useProgressReport, useStaleness } from '../../lib/hooks'
import { useMajorContext } from '../../lib/MajorContext'

type ViewMode = 'full' | 'primary' | 'collapsed'
type Tab = 'required' | 'intensive' | 'extra'

function statusClass(status: ProgressCellData['status']): string {
  switch (status) {
    case 'pass': return 'grade-pass'
    case 'cr':   return 'grade-cr'
    case 'nc':   return 'grade-nc'
    default:     return ''
  }
}

function cellText(cell: ProgressCellData | undefined, mode: ViewMode): string {
  if (!cell || cell.status === 'empty') return ''
  if (mode === 'full')      return cell.raw
  if (mode === 'primary')   return cell.primary
  // collapsed: show short status text like original
  if (cell.status === 'pass') return 'c'
  if (cell.status === 'cr')   return 'cr'
  if (cell.status === 'nc')   return 'nc'
  return ''
}

async function downloadReport(majorCode: string) {
  const token = window.localStorage.getItem('advising_v2_token')
  const res = await fetch(`${API_BASE_URL}/api/reports/${majorCode}/progress-report`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  })
  if (!res.ok) { alert(await res.text()); return }
  const blob = await res.blob()
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `progress_report_${majorCode}.xlsx`
  document.body.appendChild(a); a.click()
  a.remove(); URL.revokeObjectURL(url)
}

export function ProgressReportPage() {
  const { majorCode, setMajorCode, allowedMajors } = useMajorContext()
  const [tab, setTab] = useState<Tab>('required')
  const [viewMode, setViewMode] = useState<ViewMode>('primary')
  const [search, setSearch] = useState('')
  const [slotSelections, setSlotSelections] = useState<Record<string, string>>({})
  const [savingKey, setSavingKey] = useState<string | null>(null)

  const report = useProgressReport(majorCode)
  const staleness = useStaleness(majorCode)

  const courses = tab === 'required'
    ? (report.data?.required_courses ?? [])
    : (report.data?.intensive_courses ?? [])

  const filtered = (report.data?.students ?? []).filter(s => {
    if (!search) return true
    const q = search.toLowerCase()
    return s.student_name.toLowerCase().includes(q) || s.student_id.toLowerCase().includes(q)
  })

  const extraCourses: ExtraCourseRow[] = report.data?.extra_courses ?? []
  const asmtTypes: string[] = report.data?.assignment_types ?? []
  const filteredExtra = extraCourses.filter(r => {
    if (!search) return true
    const q = search.toLowerCase()
    return r.student_name.toLowerCase().includes(q) || r.student_id.toLowerCase().includes(q) || r.course.toLowerCase().includes(q)
  })

  async function handleAssignSlot(row: ExtraCourseRow) {
    const key = `${row.student_id}|${row.course}`
    const slot = slotSelections[key]
    if (!slot) return
    setSavingKey(key)
    try {
      const token = localStorage.getItem('advising_v2_token')
      const res = await fetch(`${API_BASE_URL}/api/course-config/${majorCode}/assignments`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...(token ? { Authorization: `Bearer ${token}` } : {}) },
        body: JSON.stringify({ student_id: row.student_id, assignment_type: slot, course_code: row.course }),
      })
      if (res.ok) {
        report.refetch()
        setSlotSelections(prev => { const n = { ...prev }; delete n[key]; return n })
      } else {
        alert(await res.text())
      }
    } finally {
      setSavingKey(null)
    }
  }

  return (
    <section className="settings-container stack" style={{ maxWidth: '100%', padding: '0 1.5rem' }}>
      {/* Header */}
      <div className="page-header flex-between mb-4" style={{ flexWrap: 'wrap', gap: '0.75rem' }}>
        <div>
          <div className="eyebrow text-muted">Analytics</div>
          <h2 style={{ margin: 0 }}>Progress Report</h2>
        </div>
        <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center', flexWrap: 'wrap' }}>
          <label className="inline-select">
            <span className="text-muted">Program:</span>
            <select className="select-input" value={majorCode} onChange={(e) => setMajorCode(e.target.value)}>
              {allowedMajors.map((m) => <option key={m.code}>{m.code}</option>)}
            </select>
          </label>
          <button
            type="button"
            className="btn-primary btn-sm"
            style={{ flexShrink: 0 }}
            onClick={() => downloadReport(majorCode)}
          >
            ↓ Export Excel
          </button>
        </div>
      </div>

      {/* Staleness banner */}
      {staleness.data?.stale && (
        <div className="alert mb-4" style={{ background: '#fefce8', border: '1px solid #fde047', color: '#854d0e' }}>
          <strong>Data may be stale.</strong>{' '}
          The course catalog was updated after the last progress upload. Go to Settings to re-upload the progress report.
        </div>
      )}

      {/* No data placeholder */}
      {report.isError && (
        <div className="panel" style={{ textAlign: 'center', padding: '3rem', color: 'var(--muted)' }}>
          Could not load progress data. Upload a progress report in Settings first.
        </div>
      )}

      {report.isLoading && (
        <div className="panel" style={{ textAlign: 'center', padding: '3rem', color: 'var(--muted)' }}>
          Loading…
        </div>
      )}

      {report.data && (
        <>
          {/* Controls */}
          <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center', marginBottom: '1rem', flexWrap: 'wrap' }}>
            {/* Tabs */}
            <div style={{ display: 'flex', gap: '0', border: '1px solid var(--line)', borderRadius: '10px', overflow: 'hidden' }}>
              {(['required', 'intensive', 'extra'] as Tab[]).map(t => (
                <button
                  key={t}
                  type="button"
                  onClick={() => setTab(t)}
                  style={{
                    padding: '0.4rem 1rem',
                    fontSize: '0.82rem',
                    fontWeight: tab === t ? 700 : 400,
                    background: tab === t ? 'var(--accent)' : 'white',
                    color: tab === t ? 'white' : 'var(--ink)',
                    border: 'none',
                    borderRadius: 0,
                    cursor: 'pointer',
                    textTransform: 'capitalize',
                  }}
                >
                  {t === 'extra' ? `Extra (${extraCourses.length})` : t}
                </button>
              ))}
            </div>

            {/* View mode (grid tabs only) */}
            {tab !== 'extra' && (
            <div style={{ display: 'flex', gap: '0', border: '1px solid var(--line)', borderRadius: '10px', overflow: 'hidden' }}>
              {(['full', 'primary', 'collapsed'] as ViewMode[]).map(m => (
                <button
                  key={m}
                  type="button"
                  onClick={() => setViewMode(m)}
                  style={{
                    padding: '0.4rem 0.9rem',
                    fontSize: '0.82rem',
                    fontWeight: viewMode === m ? 700 : 400,
                    background: viewMode === m ? '#334155' : 'white',
                    color: viewMode === m ? 'white' : 'var(--ink)',
                    border: 'none',
                    borderRadius: 0,
                    cursor: 'pointer',
                    textTransform: 'capitalize',
                  }}
                >
                  {m}
                </button>
              ))}
            </div>
            )}

            {/* Search */}
            <input
              type="search"
              className="search-input"
              style={{ maxWidth: '220px' }}
              placeholder="Search student…"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />

            {/* Legend */}
            <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center', marginLeft: 'auto' }}>
              {[
                { cls: 'grade-pass', label: 'Pass' },
                { cls: 'grade-cr', label: 'CR' },
                { cls: 'grade-nc', label: 'NC / Fail' },
              ].map(({ cls, label }) => (
                <span key={cls} style={{ display: 'flex', alignItems: 'center', gap: '4px', fontSize: '0.75rem' }}>
                  <span className={cls} style={{ display: 'inline-block', width: '14px', height: '14px', borderRadius: '3px' }} />
                  {label}
                </span>
              ))}
            </div>
          </div>

          {/* Extra Courses Tab */}
          {tab === 'extra' && (
            <>
              <div style={{ fontSize: '0.78rem', color: 'var(--muted)', marginBottom: '0.5rem' }}>
                {filteredExtra.length} unassigned extra course{filteredExtra.length !== 1 ? 's' : ''}
                {asmtTypes.length > 0 && ` · assign to: ${asmtTypes.join(', ')}`}
              </div>
              {filteredExtra.length === 0 ? (
                <div className="panel" style={{ textAlign: 'center', padding: '2rem', color: 'var(--muted)' }}>
                  No unassigned extra courses.
                </div>
              ) : (
                <div style={{ overflowX: 'auto', border: '1px solid var(--line)', borderRadius: '14px' }}>
                  <table style={{ borderCollapse: 'collapse', fontSize: '0.78rem', whiteSpace: 'nowrap', width: '100%' }}>
                    <thead>
                      <tr style={{ background: '#f8fafc' }}>
                        {['Student', 'Course', 'Grade', 'Year', 'Semester', 'Assign to Slot'].map(h => (
                          <th key={h} style={{ padding: '0.5rem 0.85rem', textAlign: 'left', fontWeight: 600, borderRight: '1px solid var(--line)' }}>{h}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {filteredExtra.map((row, ri) => {
                        const key = `${row.student_id}|${row.course}`
                        const currentSlot = slotSelections[key] ?? ''
                        return (
                          <tr key={key} style={{ background: ri % 2 === 0 ? 'white' : '#fafafa', borderBottom: '1px solid var(--line)' }}>
                            <td style={{ padding: '0.45rem 0.85rem', borderRight: '1px solid var(--line)' }}>
                              <div style={{ fontWeight: 600 }}>{row.student_name}</div>
                              <div style={{ color: 'var(--muted)', fontFamily: 'monospace', fontSize: '0.72rem' }}>{row.student_id}</div>
                            </td>
                            <td style={{ padding: '0.45rem 0.6rem', fontFamily: 'monospace', borderRight: '1px solid var(--line)' }}>{row.course}</td>
                            <td style={{ padding: '0.45rem 0.6rem', textAlign: 'center', borderRight: '1px solid var(--line)' }}>{row.grade}</td>
                            <td style={{ padding: '0.45rem 0.6rem', textAlign: 'center', borderRight: '1px solid var(--line)' }}>{row.year}</td>
                            <td style={{ padding: '0.45rem 0.6rem', textAlign: 'center', borderRight: '1px solid var(--line)' }}>{row.semester}</td>
                            <td style={{ padding: '0.3rem 0.6rem', borderRight: '1px solid var(--line)' }}>
                              <div style={{ display: 'flex', gap: '0.4rem', alignItems: 'center' }}>
                                <select
                                  value={currentSlot}
                                  onChange={e => setSlotSelections(prev => ({ ...prev, [key]: e.target.value }))}
                                  style={{ fontSize: '0.78rem', padding: '0.2rem 0.4rem', border: '1px solid var(--line)', borderRadius: '6px' }}
                                >
                                  <option value=''>— choose slot —</option>
                                  {asmtTypes.map(t => <option key={t} value={t}>{t}</option>)}
                                </select>
                                <button
                                  type='button'
                                  disabled={!currentSlot || savingKey === key}
                                  onClick={() => handleAssignSlot(row)}
                                  style={{
                                    fontSize: '0.75rem', padding: '0.2rem 0.6rem',
                                    background: currentSlot ? 'var(--accent)' : '#e2e8f0',
                                    color: currentSlot ? 'white' : 'var(--muted)',
                                    border: 'none', borderRadius: '6px', cursor: currentSlot ? 'pointer' : 'default',
                                  }}
                                >
                                  {savingKey === key ? '…' : 'Assign'}
                                </button>
                              </div>
                            </td>
                          </tr>
                        )
                      })}
                    </tbody>
                  </table>
                </div>
              )}
            </>
          )}

          {/* Summary counts */}
          {tab !== 'extra' && (
          <div style={{ fontSize: '0.78rem', color: 'var(--muted)', marginBottom: '0.5rem' }}>
            {filtered.length} student{filtered.length !== 1 ? 's' : ''} &middot; {courses.length} courses
          </div>
          )}

          {/* Grid */}
          {tab !== 'extra' && (courses.length === 0 ? (
            <div className="panel" style={{ textAlign: 'center', padding: '2rem', color: 'var(--muted)' }}>
              No {tab} courses found.
            </div>
          ) : (
            <div style={{ overflowX: 'auto', border: '1px solid var(--line)', borderRadius: '14px' }}>
              <table style={{ borderCollapse: 'collapse', fontSize: '0.78rem', whiteSpace: 'nowrap', width: '100%' }}>
                <thead>
                  <tr style={{ background: '#f8fafc' }}>
                    <th style={{
                      position: 'sticky', left: 0, zIndex: 2,
                      background: '#f8fafc', borderRight: '2px solid var(--line)',
                      padding: '0.5rem 0.85rem', textAlign: 'left', fontWeight: 700, minWidth: '200px',
                    }}>
                      Student
                    </th>
                    <th style={{ padding: '0.5rem 0.6rem', textAlign: 'center', fontWeight: 600, borderRight: '1px solid var(--line)' }}>Credits Done</th>
                    <th style={{ padding: '0.5rem 0.6rem', textAlign: 'center', fontWeight: 600, borderRight: '1px solid var(--line)' }}>Registered</th>
                    <th style={{ padding: '0.5rem 0.6rem', textAlign: 'center', fontWeight: 600, borderRight: '2px solid var(--line)' }}>Remaining</th>
                    {courses.map(c => (
                      <th key={c} style={{ padding: '0.5rem 0.5rem', textAlign: 'center', fontWeight: 600, minWidth: '70px', borderRight: '1px solid var(--line)', writingMode: 'vertical-rl', transform: 'rotate(180deg)', maxHeight: '90px' }}>
                        {c}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {filtered.length === 0 && (
                    <tr>
                      <td colSpan={4 + courses.length} style={{ textAlign: 'center', color: 'var(--muted)', padding: '2rem' }}>
                        {search ? 'No students match your search.' : 'No student data.'}
                      </td>
                    </tr>
                  )}
                  {filtered.map((student, ri) => {
                    const cells = tab === 'required' ? student.required : student.intensive
                    return (
                      <tr key={student.student_id} style={{ background: ri % 2 === 0 ? 'white' : '#fafafa', borderBottom: '1px solid var(--line)' }}>
                        <td style={{
                          position: 'sticky', left: 0, zIndex: 1,
                          background: ri % 2 === 0 ? 'white' : '#fafafa',
                          borderRight: '2px solid var(--line)',
                          padding: '0.45rem 0.85rem',
                        }}>
                          <div style={{ fontWeight: 600 }}>{student.student_name}</div>
                          <div style={{ color: 'var(--muted)', fontFamily: 'monospace', fontSize: '0.72rem' }}>{student.student_id}</div>
                        </td>
                        <td style={{ textAlign: 'center', padding: '0.45rem 0.6rem', borderRight: '1px solid var(--line)' }}>{student.credits_completed}</td>
                        <td style={{ textAlign: 'center', padding: '0.45rem 0.6rem', borderRight: '1px solid var(--line)' }}>{student.credits_registered}</td>
                        <td style={{ textAlign: 'center', padding: '0.45rem 0.6rem', borderRight: '2px solid var(--line)' }}>{student.credits_remaining}</td>
                        {courses.map(c => {
                          const cell = cells[c]
                          const cls = statusClass(cell?.status ?? 'empty')
                          const text = cellText(cell, viewMode)
                          return (
                            <td
                              key={c}
                              className={cls}
                              title={cell?.raw ?? ''}
                              style={{
                                textAlign: 'center',
                                padding: viewMode === 'collapsed' ? '0' : '0.4rem 0.5rem',
                                borderRight: '1px solid var(--line)',
                                minWidth: '70px',
                                height: viewMode === 'collapsed' ? '28px' : undefined,
                                fontSize: '0.72rem',
                              }}
                            >
                              {text}
                            </td>
                          )
                        })}
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          ))}\n        </>
      )}
    </section>
  )
}
