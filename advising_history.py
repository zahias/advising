# advising_history.py
# (snippet shows only functions that changed; rest of your file stays the same)

# ... existing imports ...
from course_exclusions import ensure_loaded as ensure_exclusions_loaded, get_for_student

# In _snapshot_student_course_rows, SKIP hidden courses for that student
def _snapshot_student_course_rows(student_row: pd.Series, advised: List[str], optional: List[str]) -> List[Dict[str, Any]]:
    ensure_exclusions_loaded()
    hidden = set(map(str, get_for_student(int(student_row.get("ID")))))
    courses_df = st.session_state.courses_df
    rows: List[Dict[str, Any]] = []
    for course_code in courses_df["Course Code"]:
        code = str(course_code)
        if code in hidden:
            continue  # <-- skip hidden
        info = courses_df.loc[courses_df["Course Code"] == course_code].iloc[0]
        offered = "Yes" if is_course_offered(courses_df, course_code) else "No"

        status, justification = check_eligibility(student_row, course_code, advised, courses_df)

        if check_course_completed(student_row, course_code):
            action = "Completed"; status = "Completed"
        elif check_course_registered(student_row, course_code):
            action = "Registered"
        elif course_code in advised:
            action = "Advised"
        elif course_code in optional:
            action = "Optional"
        elif status == "Not Eligible":
            action = "Not Eligible"
        else:
            action = "Eligible (not chosen)"

        rows.append({
            "Course Code": code,
            "Type": info.get("Type", ""),
            "Requisites": build_requisites_str(info),
            "Offered": offered,
            "Eligibility Status": status,
            "Justification": justification,
            "Action": action,
        })
    return rows
