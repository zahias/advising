import { useCallback, useMemo, useRef } from 'react'
import { StudentEligibility } from '../../lib/api'
import { Tooltip } from '../Tooltip'

interface Props {
  eligibility: StudentEligibility['eligibility']
  remainingCredits?: number
  formState: { advised: string[]; optional: string[]; repeat: string[]; note: string }
  onChange: (state: { advised: string[]; optional: string[]; repeat: string[]; note: string }) => void
  onSave: () => void
}

type EligibilityItem = StudentEligibility['eligibility'][number]

function getCourseStatus(course: EligibilityItem): 'eligible' | 'ineligible' | 'completed' | 'registered' {
  if (course.registered) return 'registered'
  if (course.completed) return 'completed'
  if (course.eligibility_status === 'Eligible' || course.eligibility_status === 'Eligible (Bypass)') return 'eligible'
  return 'ineligible'
}

const STATUS_LABELS: Record<string, string> = {
  eligible: '✓ Eligible',
  ineligible: '✗ Not eligible',
  completed: '● Done',
  registered: '◎ Registered',
}

const STATUS_DOT: Record<string, string> = {
  eligible: '#22c55e',
  ineligible: '#cbd5e1',
  completed: '#94a3b8',
  registered: '#eab308',
}

export function CourseSelectionBuilder({ eligibility, remainingCredits = 0, formState, onChange, onSave }: Props) {
  const undoStack = useRef<Array<typeof formState>>([])

  const creditLookup = useMemo(() => {
    const map: Record<string, number> = {}
    for (const c of eligibility) {
      const cr = (c as any).credits
      map[c.course_code] = typeof cr === 'number' ? cr : 3
    }
    return map
  }, [eligibility])

  const advisedCredits = useMemo(
    () => [...formState.advised, ...formState.optional, ...formState.repeat].reduce((s, code) => s + (creditLookup[code] || 3), 0),
    [formState, creditLookup],
  )

  const creditPercent = remainingCredits > 0 ? Math.min(100, Math.round((advisedCredits / remainingCredits) * 100)) : 0

  const pushUndo = useCallback(() => {
    undoStack.current = [
      ...undoStack.current.slice(-19),
      { ...formState, advised: [...formState.advised], optional: [...formState.optional], repeat: [...formState.repeat] },
    ]
  }, [formState])

  const handleUndo = useCallback(() => {
    const prev = undoStack.current.pop()
    if (prev) onChange(prev)
  }, [onChange])

  const handleAdd = (courseCode: string, type: 'advised' | 'optional' | 'repeat') => {
    pushUndo()
    onChange({
      ...formState,
      advised: type === 'advised' ? [...formState.advised, courseCode] : formState.advised,
      optional: type === 'optional' ? [...formState.optional, courseCode] : formState.optional,
      repeat: type === 'repeat' ? [...formState.repeat, courseCode] : formState.repeat,
    })
  }

  const handleRemove = (courseCode: string, type: 'advised' | 'optional' | 'repeat') => {
    pushUndo()
    onChange({
      ...formState,
      advised: type === 'advised' ? formState.advised.filter((c) => c !== courseCode) : formState.advised,
      optional: type === 'optional' ? formState.optional.filter((c) => c !== courseCode) : formState.optional,
      repeat: type === 'repeat' ? formState.repeat.filter((c) => c !== courseCode) : formState.repeat,
    })
  }

  const selected = useMemo(() => new Set([...formState.advised, ...formState.optional, ...formState.repeat]), [formState])

  // Split courses: main (non-intensive) vs intensive
  const availableMain = useMemo(
    () => eligibility.filter((c) =>
      c.course_type.toLowerCase() !== 'intensive' &&
      !selected.has(c.course_code) &&
      (c.offered || c.completed || c.registered)
    ),
    [eligibility, selected],
  )

  const availableIntensive = useMemo(
    () => eligibility.filter((c) =>
      c.course_type.toLowerCase() === 'intensive' &&
      !selected.has(c.course_code) &&
      (c.offered || c.completed || c.registered)
    ),
    [eligibility, selected],
  )

  function CourseCard({ course }: { course: EligibilityItem }) {
    const status = getCourseStatus(course)
    const isIneligible = status === 'ineligible'
    const isCompleted = status === 'completed'
    const isRegistered = status === 'registered'
    return (
      <div className={`course-grid-card ${isIneligible ? 'course-grid-card--ineligible' : ''}`}>
        <div className="course-grid-card__header">
          <strong className="course-grid-card__code">{course.course_code}</strong>
          <span className="course-grid-card__dot" style={{ background: STATUS_DOT[status] }} title={STATUS_LABELS[status]} />
        </div>
        <span className="course-grid-card__title">{course.title}</span>
        {isIneligible && (
          <span className="course-grid-card__ineligible-label">
            ✗ Not eligible{course.justification ? <Tooltip text={course.justification} /> : null}
          </span>
        )}
        <div className="course-grid-card__actions">
          {!isIneligible && !isCompleted && !isRegistered && (
            <>
              <button type="button" className="btn-sm" onClick={() => handleAdd(course.course_code, 'advised')}>Advise</button>
              <button type="button" className="btn-sm btn-outline" onClick={() => handleAdd(course.course_code, 'optional')}>Optional</button>
            </>
          )}
          {(isCompleted || isRegistered) && (
            <button type="button" className="btn-sm btn-warning" onClick={() => handleAdd(course.course_code, 'repeat')}>Repeat</button>
          )}
        </div>
      </div>
    )
  }

  return (
    <div className="course-selection-builder">
      {/* Credit bar + save */}
      <div className="builder-topbar">
        <div className="credit-counter-bar">
          <div className="credit-counter-bar__labels">
            <span>
              Advising <strong style={{ color: '#0f172a', fontSize: '16px' }}>{advisedCredits}</strong> of <strong>{remainingCredits}</strong> remaining credits
            </span>
            <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
              <button type="button" onClick={handleUndo} disabled={undoStack.current.length === 0} className="btn-sm btn-outline" style={{ fontSize: '12px', padding: '2px 10px' }}>↩ Undo</button>
              <span style={{ fontSize: '12px', color: '#64748b' }}>{creditPercent}%</span>
            </div>
          </div>
          <div className="credit-bar-track">
            <div className="credit-bar-fill" style={{ width: `${creditPercent}%`, background: creditPercent > 100 ? '#ef4444' : creditPercent > 75 ? '#f59e0b' : '#22c55e' }} />
          </div>
        </div>
        <button type="button" className="btn-primary" onClick={onSave} style={{ flexShrink: 0 }}>Save Selections</button>
      </div>

      {/* Main builder grid: courses (left) + selections (right) */}
      <div className="builder-grid-new">

        {/* Left: Course Pool */}
        <div className="course-pool scrollable">

          {/* Required / main courses — 3 columns */}
          {availableMain.length === 0 ? (
            <p className="empty-state" style={{ padding: '1rem', color: '#94a3b8', fontSize: '0.85rem' }}>No courses to display.</p>
          ) : (
            <div className="course-3col-grid">
              {availableMain.map((course) => <CourseCard key={course.course_code} course={course} />)}
            </div>
          )}

          {/* Intensive — separate section below */}
          {availableIntensive.length > 0 && (
            <div className="intensive-section">
              <div className="intensive-divider">
                <span>Intensive Courses</span>
              </div>
              <div className="course-3col-grid">
                {availableIntensive.map((course) => <CourseCard key={course.course_code} course={course} />)}
              </div>
            </div>
          )}

        </div>

        {/* Right: Selections */}
        <div className="selected-column stack">

          {/* Advisor Note at TOP */}
          <div className="advisor-note" style={{ marginTop: 0 }}>
            <label htmlFor="adv-note" style={{ fontWeight: 600, fontSize: '0.85rem' }}>Advisor Note</label>
            <textarea
              id="adv-note"
              rows={3}
              value={formState.note}
              onChange={(e) => onChange({ ...formState, note: e.target.value })}
              placeholder="Add narrative notes for the student…"
            />
          </div>

          {/* Advised */}
          <div className="selection-group">
            <div className="group-header">
              <h4>Advised <span className="badge badge-primary">{formState.advised.length}</span> <Tooltip text="Primary courses you are recommending the student register for." /></h4>
            </div>
            <div className="selected-list">
              {formState.advised.length === 0 && <p className="empty-state-sm">None.</p>}
              {formState.advised.map((code) => {
                const c = eligibility.find((x) => x.course_code === code)
                return (
                  <div key={code} className="selected-item">
                    <span><strong>{code}</strong>{c ? ` — ${c.title}` : ''}</span>
                    <button type="button" onClick={() => handleRemove(code, 'advised')} className="remove-btn">&times;</button>
                  </div>
                )
              })}
            </div>
          </div>

          {/* Optional */}
          <div className="selection-group">
            <div className="group-header">
              <h4>Optional <span className="badge">{formState.optional.length}</span> <Tooltip text="Alternate courses if primary spots are unavailable." /></h4>
            </div>
            <div className="selected-list">
              {formState.optional.length === 0 && <p className="empty-state-sm">None.</p>}
              {formState.optional.map((code) => {
                const c = eligibility.find((x) => x.course_code === code)
                return (
                  <div key={code} className="selected-item">
                    <span><strong>{code}</strong>{c ? ` — ${c.title}` : ''}</span>
                    <button type="button" onClick={() => handleRemove(code, 'optional')} className="remove-btn">&times;</button>
                  </div>
                )
              })}
            </div>
          </div>

          {/* Repeat */}
          <div className="selection-group">
            <div className="group-header">
              <h4>Repeat <span className="badge badge-warning">{formState.repeat.length}</span> <Tooltip text="Courses to be re-taken (e.g. to improve grade)." /></h4>
            </div>
            <div className="selected-list">
              {formState.repeat.length === 0 && <p className="empty-state-sm">None.</p>}
              {formState.repeat.map((code) => {
                const c = eligibility.find((x) => x.course_code === code)
                return (
                  <div key={code} className="selected-item">
                    <span><strong>{code}</strong>{c ? ` — ${c.title}` : ''}</span>
                    <button type="button" onClick={() => handleRemove(code, 'repeat')} className="remove-btn">&times;</button>
                  </div>
                )
              })}
            </div>
          </div>

        </div>
      </div>
    </div>
  )
}
