import { StudentEligibilityItem } from '../../lib/hooks'

interface Props {
    student: {
        bypasses: Record<string, { note: string; advisor_name: string }>
        excluded_courses: string[]
    }
    eligibility: StudentEligibilityItem[]
    hiddenCourseOptions: string[]
    bypassCourse: string
    setBypassCourse: (val: string) => void
    bypassNote: string
    setBypassNote: (val: string) => void
    onBypassSave: () => void
    onBypassDelete: (courseCode: string) => void
    hiddenCourses: string[]
    setHiddenCourses: (val: string[]) => void
    onHiddenCoursesSave: () => void
}

export function ExceptionManagement({
    student,
    eligibility,
    hiddenCourseOptions,
    bypassCourse,
    setBypassCourse,
    bypassNote,
    setBypassNote,
    onBypassSave,
    onBypassDelete,
    hiddenCourses,
    setHiddenCourses,
    onHiddenCoursesSave,
}: Props) {

    // Custom multi-select helper for hidden courses (since listbox is better than native select)
    const toggleHiddenCourse = (code: string) => {
        if (hiddenCourses.includes(code)) {
            setHiddenCourses(hiddenCourses.filter(c => c !== code))
        } else {
            setHiddenCourses([...hiddenCourses, code])
        }
    }

    return (
        <div className="exception-management-container grid-2">

            {/* Bypasses */}
            <div className="panel stack">
                <div className="panel-header">
                    <h3>Requisite Bypasses</h3>
                    <p className="text-muted text-sm">Allow student to register for a course without meeting prerequisites</p>
                </div>

                <div className="form-grid">
                    <div className="form-group">
                        <label htmlFor="bypass-course">Course</label>
                        <select
                            id="bypass-course"
                            value={bypassCourse}
                            onChange={(e) => setBypassCourse(e.target.value)}
                            className="select-input"
                        >
                            <option value="">Select a course</option>
                            {eligibility.map((course) => (
                                <option key={course.course_code} value={course.course_code}>
                                    {course.course_code} - {course.title}
                                </option>
                            ))}
                        </select>
                    </div>
                    <div className="form-group">
                        <label htmlFor="bypass-note">Note</label>
                        <textarea
                            id="bypass-note"
                            rows={2}
                            value={bypassNote}
                            onChange={(e) => setBypassNote(e.target.value)}
                            placeholder="Why is this bypass granted?"
                            className="text-input"
                        />
                    </div>
                    <button
                        type="button"
                        className="btn-primary"
                        onClick={onBypassSave}
                        disabled={!bypassCourse}
                    >
                        Save Bypass
                    </button>
                </div>

                <div className="divider" />

                <div className="bypass-list">
                    <h4 className="list-title">Active Bypasses</h4>
                    {Object.entries(student.bypasses).length === 0 ? (
                        <p className="empty-state-sm">No active bypasses.</p>
                    ) : (
                        <div className="mini-list">
                            {Object.entries(student.bypasses).map(([courseCode, info]) => (
                                <div key={courseCode} className="mini-item card-sm">
                                    <div className="item-content">
                                        <strong>{courseCode}</strong>
                                        <p className="note-text">{info.note}</p>
                                        {info.advisor_name && <span className="advisor-tag">by {info.advisor_name}</span>}
                                    </div>
                                    <button type="button" className="btn-icon btn-danger" onClick={() => onBypassDelete(courseCode)} title="Remove bypass">
                                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M3 6h18" /><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6" /><path d="M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" /></svg>
                                    </button>
                                </div>
                            ))}
                        </div>
                    )}
                </div>
            </div>

            {/* Hidden Courses */}
            <div className="panel stack">
                <div className="panel-header">
                    <h3>Hidden Courses</h3>
                    <p className="text-muted text-sm">Hide specific courses from this student's eligibility view</p>
                </div>

                <div className="form-group">
                    <label>Select courses to hide</label>
                    <div className="hidden-courses-selector scrollable">
                        {hiddenCourseOptions.map((courseCode) => (
                            <label key={courseCode} className="checkbox-item">
                                <input
                                    type="checkbox"
                                    checked={hiddenCourses.includes(courseCode)}
                                    onChange={() => toggleHiddenCourse(courseCode)}
                                />
                                <span>{courseCode}</span>
                            </label>
                        ))}
                    </div>
                </div>

                <button type="button" className="btn-primary" onClick={onHiddenCoursesSave}>
                    Save Hidden Courses
                </button>

                <div className="divider" />

                <div className="admin-excluded">
                    <h4 className="list-title">Admin Excluded</h4>
                    <p className="text-muted text-sm">These courses are globally excluded by the system administrator.</p>
                    <div className="tags-container mt-2">
                        {student.excluded_courses.length === 0 ? (
                            <span className="text-muted text-sm">None</span>
                        ) : (
                            student.excluded_courses.map(code => (
                                <span key={code} className="tag tag-disabled">{code}</span>
                            ))
                        )}
                    </div>
                </div>
            </div>

        </div>
    )
}
