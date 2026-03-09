import { useCallback, useMemo, useRef, useState } from 'react'
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
    ineligible: '✗ Ineligible',
    completed: '● Completed',
    registered: '◎ Registered',
}

export function CourseSelectionBuilder({ eligibility, remainingCredits = 0, formState, onChange, onSave }: Props) {
    const [search, setSearch] = useState('')
    const [showIneligible, setShowIneligible] = useState(true)
    const undoStack = useRef<Array<{ advised: string[]; optional: string[]; repeat: string[]; note: string }>>([])

    const getCourseDetails = (code: string) => eligibility.find((c) => c.course_code === code)

    const creditLookup = useMemo(() => {
        const map: Record<string, number> = {}
        for (const c of eligibility) {
            const cr = (c as any).credits
            map[c.course_code] = typeof cr === 'number' ? cr : 3
        }
        return map
    }, [eligibility])

    const advisedCredits = useMemo(() => {
        return [...formState.advised, ...formState.optional, ...formState.repeat]
            .reduce((sum, code) => sum + (creditLookup[code] || 3), 0)
    }, [formState, creditLookup])

    const creditPercent = remainingCredits > 0 ? Math.min(100, Math.round((advisedCredits / remainingCredits) * 100)) : 0

    const pushUndo = useCallback(() => {
        undoStack.current = [...undoStack.current.slice(-19), { ...formState, advised: [...formState.advised], optional: [...formState.optional], repeat: [...formState.repeat] }]
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

    const groupedCourses = useMemo(() => {
        const q = search.toLowerCase()
        const groups: Record<string, EligibilityItem[]> = {}
        for (const course of eligibility) {
            if (selected.has(course.course_code)) continue
            if (!course.offered && !course.completed && !course.registered) continue
            const status = getCourseStatus(course)
            if (!showIneligible && status === 'ineligible') continue
            if (q && !course.course_code.toLowerCase().includes(q) && !course.title.toLowerCase().includes(q)) continue
            const group = (course as any).course_type || 'Other'
            if (!groups[group]) groups[group] = []
            groups[group].push(course)
        }
        return groups
    }, [eligibility, selected, search, showIneligible])

    const totalVisible = Object.values(groupedCourses).reduce((s, g) => s + g.length, 0)

    const ineligibleCount = useMemo(
        () => eligibility.filter(c =>
            !selected.has(c.course_code) &&
            (c.offered || c.completed || c.registered) &&
            getCourseStatus(c) === 'ineligible'
        ).length,
        [eligibility, selected]
    )

    return (
        <div className="course-selection-builder">
            {/* Credit Counter Bar */}
            <div className="credit-counter-bar" style={{ padding: '12px 16px', background: '#f8fafc', borderRadius: '12px', border: '1px solid #e2e8f0', marginBottom: '16px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                    <span style={{ fontSize: '13px', fontWeight: 600, color: '#475569' }}>
                        Advising <strong style={{ color: '#0f172a', fontSize: '16px' }}>{advisedCredits}</strong> of <strong>{remainingCredits}</strong> remaining credits
                    </span>
                    <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                        <button type="button" onClick={handleUndo} disabled={undoStack.current.length === 0} className="btn-sm btn-outline" style={{ fontSize: '12px', padding: '2px 10px' }} title="Undo last change">
                            ↩ Undo
                        </button>
                        <span style={{ fontSize: '12px', color: '#64748b' }}>{creditPercent}%</span>
                    </div>
                </div>
                <div style={{ height: '6px', background: '#e2e8f0', borderRadius: '3px', overflow: 'hidden' }}>
                    <div style={{ height: '100%', width: `${creditPercent}%`, background: creditPercent > 100 ? '#ef4444' : creditPercent > 75 ? '#f59e0b' : '#22c55e', borderRadius: '3px', transition: 'width 0.3s ease' }} />
                </div>
            </div>

            <div className="builder-header">
                <h3>Schedule Builder</h3>
                <button type="button" className="btn-primary" onClick={onSave}>Save Selections</button>
            </div>

            <div className="builder-grid">
                {/* Left Column: All Courses */}
                <div className="available-column stack">
                    <input
                        type="search"
                        placeholder="Search courses by code or title…"
                        value={search}
                        onChange={(e) => setSearch(e.target.value)}
                        className="search-input"
                    />
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '2px 0' }}>
                        <span style={{ fontSize: '12px', color: '#64748b' }}>{totalVisible} course{totalVisible !== 1 ? 's' : ''}</span>
                        {ineligibleCount > 0 && (
                            <button
                                type="button"
                                className="show-ineligible-toggle"
                                onClick={() => setShowIneligible(v => !v)}
                            >
                                {showIneligible ? 'Hide' : 'Show'} {ineligibleCount} ineligible
                            </button>
                        )}
                    </div>
                    <div className="course-list scrollable">
                        {totalVisible === 0 ? (
                            <p className="empty-state">No courses match your search.</p>
                        ) : (
                            Object.entries(groupedCourses).sort(([a], [b]) => a.localeCompare(b)).map(([group, courses]) => (
                                <div key={group} className="course-group">
                                    <div className="course-group-header">{group}</div>
                                    {courses.map((course) => {
                                        const status = getCourseStatus(course)
                                        const isIneligible = status === 'ineligible'
                                        const isCompleted = status === 'completed'
                                        const isRegistered = status === 'registered'
                                        const reason = course.justification
                                        return (
                                            <div key={course.course_code} className={`course-card${isIneligible ? ' course-card-ineligible' : ''}`}>
                                                <div className="course-info">
                                                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '8px' }}>
                                                        <strong>{course.course_code}</strong>
                                                        <span className={`course-status-badge status-${status}`}>{STATUS_LABELS[status]}</span>
                                                    </div>
                                                    <span className="course-title">{course.title}</span>
                                                    {isIneligible && reason && (
                                                        <span className="ineligible-reason">{reason}</span>
                                                    )}
                                                </div>
                                                <div className="course-actions" style={{ display: 'flex', gap: '6px', marginTop: '8px' }}>
                                                    {!isIneligible && !isCompleted && !isRegistered && (
                                                        <>
                                                            <button type="button" onClick={() => handleAdd(course.course_code, 'advised')} className="btn-sm">Advise</button>
                                                            <button type="button" onClick={() => handleAdd(course.course_code, 'optional')} className="btn-sm btn-outline">Optional</button>
                                                        </>
                                                    )}
                                                    {(isCompleted || isRegistered) && (
                                                        <button type="button" onClick={() => handleAdd(course.course_code, 'repeat')} className="btn-sm btn-warning">Repeat</button>
                                                    )}
                                                    {isIneligible && (
                                                        <span style={{ fontSize: '11px', color: '#94a3b8', fontStyle: 'italic' }}>Cannot advise — not yet eligible</span>
                                                    )}
                                                </div>
                                            </div>
                                        )
                                    })}
                                </div>
                            ))
                        )}
                    </div>
                </div>

                {/* Right Column: Selections & Notes */}
                <div className="selected-column stack">

                    <div className="selection-group">
                        <div className="group-header">
                            <h4>Advised <span className="badge badge-primary">{formState.advised.length}</span> <Tooltip text="Primary courses you are recommending the student register for this semester." /></h4>
                        </div>
                        <div className="selected-list">
                            {formState.advised.length === 0 && <p className="empty-state-sm">No courses advised.</p>}
                            {formState.advised.map((code) => {
                                const c = getCourseDetails(code)
                                return (
                                    <div key={code} className="selected-item">
                                        <span><strong>{code}</strong> {c?.title}</span>
                                        <button type="button" onClick={() => handleRemove(code, 'advised')} className="remove-btn" title="Remove">&times;</button>
                                    </div>
                                )
                            })}
                        </div>
                    </div>

                    <div className="selection-group">
                        <div className="group-header">
                            <h4>Optional <span className="badge">{formState.optional.length}</span> <Tooltip text="Courses the student may register for if spots are available or as alternates." /></h4>
                        </div>
                        <div className="selected-list">
                            {formState.optional.length === 0 && <p className="empty-state-sm">No optional courses.</p>}
                            {formState.optional.map((code) => {
                                const c = getCourseDetails(code)
                                return (
                                    <div key={code} className="selected-item">
                                        <span><strong>{code}</strong> {c?.title}</span>
                                        <button type="button" onClick={() => handleRemove(code, 'optional')} className="remove-btn" title="Remove">&times;</button>
                                    </div>
                                )
                            })}
                        </div>
                    </div>

                    <div className="selection-group">
                        <div className="group-header">
                            <h4>Repeat <span className="badge badge-warning">{formState.repeat.length}</span> <Tooltip text="Courses the student has completed or is registered in but needs to re-take (e.g. to improve grade)." /></h4>
                        </div>
                        <div className="selected-list">
                            {formState.repeat.length === 0 && <p className="empty-state-sm">No repeat courses.</p>}
                            {formState.repeat.map((code) => {
                                const c = getCourseDetails(code)
                                return (
                                    <div key={code} className="selected-item">
                                        <span><strong>{code}</strong> {c?.title}</span>
                                        <button type="button" onClick={() => handleRemove(code, 'repeat')} className="remove-btn" title="Remove">&times;</button>
                                    </div>
                                )
                            })}
                        </div>
                    </div>

                    <div className="advisor-note">
                        <label htmlFor="adv-note">Advisor Note</label>
                        <textarea
                            id="adv-note"
                            rows={3}
                            value={formState.note}
                            onChange={(e) => onChange({ ...formState, note: e.target.value })}
                            placeholder="Add narrative notes for the student..."
                        />
                    </div>

                </div>
            </div>
        </div>
    )
}