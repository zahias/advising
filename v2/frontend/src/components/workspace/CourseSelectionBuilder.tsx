import { useCallback, useMemo, useRef, useState } from 'react'
import { StudentEligibility } from '../../lib/api'

interface Props {
    eligibility: StudentEligibility['eligibility']
    remainingCredits?: number
    formState: { advised: string[]; optional: string[]; repeat: string[]; note: string }
    onChange: (state: { advised: string[]; optional: string[]; repeat: string[]; note: string }) => void
    onSave: () => void
}

export function CourseSelectionBuilder({ eligibility, remainingCredits = 0, formState, onChange, onSave }: Props) {
    const [search, setSearch] = useState('')
    const undoStack = useRef<Array<{ advised: string[]; optional: string[]; repeat: string[]; note: string }>>([])

    const getCourseDetails = (code: string) => eligibility.find((c) => c.course_code === code)

    const creditLookup = useMemo(() => {
        const map: Record<string, number> = {}
        for (const c of eligibility) {
            const cr = c.course_code ? (eligibility.find(e => e.course_code === c.course_code) as any)?.credits : 0
            map[c.course_code] = typeof cr === 'number' ? cr : 0
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

    const availableCourses = useMemo(() => {
        const selected = new Set([...formState.advised, ...formState.optional, ...formState.repeat])
        return eligibility.filter((course) => {
            if (selected.has(course.course_code)) return false
            if (search && !course.course_code.toLowerCase().includes(search.toLowerCase()) && !course.title.toLowerCase().includes(search.toLowerCase())) return false
            if (
                course.offered &&
                !course.completed &&
                !course.registered &&
                (course.eligibility_status === 'Eligible' || course.eligibility_status === 'Eligible (Bypass)')
            ) {
                return true
            }
            if (course.completed || course.registered) {
                return true
            }
            return false
        })
    }, [eligibility, formState, search])

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
                {/* Left Column: Available Courses */}
                <div className="available-column stack">
                    <input
                        type="search"
                        placeholder="Search available courses..."
                        value={search}
                        onChange={(e) => setSearch(e.target.value)}
                        className="search-input"
                    />
                    <div className="course-list scrollable">
                        {availableCourses.length === 0 ? (
                            <p className="empty-state">No available courses match your search.</p>
                        ) : (
                            availableCourses.map((course) => {
                                const isRepeatable = course.completed || course.registered
                                return (
                                    <div key={course.course_code} className="course-card">
                                        <div className="course-info">
                                            <strong>{course.course_code}</strong>
                                            <span className="course-title">{course.title}</span>
                                            {isRepeatable && <span className="tag tag-warning">Completed/Registered</span>}
                                        </div>
                                        <div className="course-actions popup-on-hover">
                                            {!isRepeatable && (
                                                <>
                                                    <button type="button" onClick={() => handleAdd(course.course_code, 'advised')} className="btn-sm">Advise</button>
                                                    <button type="button" onClick={() => handleAdd(course.course_code, 'optional')} className="btn-sm btn-outline">Optional</button>
                                                </>
                                            )}
                                            {isRepeatable && (
                                                <button type="button" onClick={() => handleAdd(course.course_code, 'repeat')} className="btn-sm btn-warning">Repeat</button>
                                            )}
                                        </div>
                                    </div>
                                )
                            })
                        )}
                    </div>
                </div>

                {/* Right Column: Selected Courses & Notes */}
                <div className="selected-column stack">

                    <div className="selection-group">
                        <div className="group-header">
                            <h4>Advised <span className="badge badge-primary">{formState.advised.length}</span></h4>
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
                            <h4>Optional <span className="badge">{formState.optional.length}</span></h4>
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
                            <h4>Repeat <span className="badge badge-warning">{formState.repeat.length}</span></h4>
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
