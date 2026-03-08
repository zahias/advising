import { useMemo, useState } from 'react'
import { StudentEligibility } from '../../lib/api'

interface Props {
    eligibility: StudentEligibility['eligibility']
    formState: { advised: string[]; optional: string[]; repeat: string[]; note: string }
    onChange: (state: { advised: string[]; optional: string[]; repeat: string[]; note: string }) => void
    onSave: () => void
}

export function CourseSelectionBuilder({ eligibility, formState, onChange, onSave }: Props) {
    const [search, setSearch] = useState('')

    const availableCourses = useMemo(() => {
        const selected = new Set([...formState.advised, ...formState.optional, ...formState.repeat])
        return eligibility.filter((course) => {
            // Must not be already selected
            if (selected.has(course.course_code)) return false
            // Basic text search
            if (search && !course.course_code.toLowerCase().includes(search.toLowerCase()) && !course.title.toLowerCase().includes(search.toLowerCase())) return false
            // Eligible logic for new courses
            if (
                course.offered &&
                !course.completed &&
                !course.registered &&
                (course.eligibility_status === 'Eligible' || course.eligibility_status === 'Eligible (Bypass)')
            ) {
                return true
            }
            // Eligible logic for repeat courses
            if (course.completed || course.registered) {
                return true
            }
            return false
        })
    }, [eligibility, formState, search])

    const handleAdd = (courseCode: string, type: 'advised' | 'optional' | 'repeat') => {
        onChange({
            ...formState,
            advised: type === 'advised' ? [...formState.advised, courseCode] : formState.advised,
            optional: type === 'optional' ? [...formState.optional, courseCode] : formState.optional,
            repeat: type === 'repeat' ? [...formState.repeat, courseCode] : formState.repeat,
        })
    }

    const handleRemove = (courseCode: string, type: 'advised' | 'optional' | 'repeat') => {
        onChange({
            ...formState,
            advised: type === 'advised' ? formState.advised.filter((c) => c !== courseCode) : formState.advised,
            optional: type === 'optional' ? formState.optional.filter((c) => c !== courseCode) : formState.optional,
            repeat: type === 'repeat' ? formState.repeat.filter((c) => c !== courseCode) : formState.repeat,
        })
    }

    const getCourseDetails = (code: string) => eligibility.find((c) => c.course_code === code)

    return (
        <div className="course-selection-builder">
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
