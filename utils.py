# utils.py

import pandas as pd
import logging

# Configure logging
logging.basicConfig(
    filename='app.log',
    filemode='a',
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

logger = logging.getLogger()

def log_info(message):
    """Log an informational message."""
    logger.info(message)

def log_error(message, error):
    """Log an error message with exception details."""
    logger.error(f"{message}: {error}", exc_info=True)

def parse_requirements(req_str):
    """Parse requirement string into a list."""
    if pd.isna(req_str) or req_str.strip().upper() == 'N/A' or req_str.strip() == '':
        return []
    else:
        return [x.strip() for x in req_str.split(',')]

def get_student_standing(credits_completed):
    """Determine student standing based on credits."""
    if credits_completed >= 60:
        return 'Senior'
    elif credits_completed >= 30:
        return 'Junior'
    else:
        return 'Sophomore'

def check_course_completed(student_row, course_code):
    """Check if the student has completed the course."""
    return str(student_row.get(course_code, '')).lower() == 'c'

def is_course_offered(courses_df, course_code):
    """Check if the course is offered."""
    if courses_df.empty:
        return False
    offered_val = courses_df.loc[
        courses_df['Course Code'] == course_code, 'Offered'
    ]
    if offered_val.empty:
        return False
    return str(offered_val.values[0]).strip().lower() == 'yes'

def build_requisites_str(course_info):
    """Build a requisites string from course info."""
    pieces = []
    for key, prefix in [('Prerequisite', 'Prereq'), ('Concurrent', 'Conc'), ('Corequisite', 'Coreq')]:
        value = course_info.get(key, '')
        if pd.isna(value):
            continue
        value = str(value).strip()
        if value.upper() != 'N/A' and value != '':
            pieces.append(f"{prefix}: {value}")
    return "; ".join(pieces) if pieces else "None"

def check_eligibility(student_row, course_code, advised_courses, courses_df):
    """Check eligibility status and justification for a course."""
    course_info = courses_df[courses_df['Course Code'] == course_code]
    if course_info.empty:
        return 'Not Eligible', 'Course not found in table.'
    course_info = course_info.iloc[0]
    
    reasons = []
    credits = student_row['# of Credits Completed']
    credits_registered = student_row.get('# Registered', 0)
    credits_completed = (credits if pd.notna(credits) else 0) + (credits_registered if pd.notna(credits_registered) else 0)
    standing = get_student_standing(credits_completed)
    
    log_info(f"Checking eligibility for course '{course_code}' for student ID {student_row['ID']}:")
    log_info(f"Total Credits Completed: {credits_completed}, Standing: {standing}")
    
    # Check if already completed
    if check_course_completed(student_row, course_code):
        return 'Completed', 'Course already completed.'
    
    # Check if course is offered
    if not is_course_offered(courses_df, course_code):
        reasons.append('Course not offered.')
    
    # Check Prerequisites
    prerequisites = parse_requirements(course_info.get('Prerequisite', ''))
    for prereq in prerequisites:
        prereq_lower = prereq.lower()
        if 'junior standing' in prereq_lower:
            if standing not in ['Junior', 'Senior']:
                reasons.append('Junior standing not met.')
        elif 'senior standing' in prereq_lower:
            if standing != 'Senior':
                reasons.append('Senior standing not met.')
        else:
            if not check_course_completed(student_row, prereq):
                reasons.append(f'Prerequisite {prereq} not completed.')
    
    # Check Concurrent Requirements
    concurrent_courses = parse_requirements(course_info.get('Concurrent', ''))
    for conc in concurrent_courses:
        if not (check_course_completed(student_row, conc) or conc in advised_courses):
            reasons.append(f'Concurrent requirement {conc} not met.')
    
    # Check Corequisites
    corequisites = parse_requirements(course_info.get('Corequisite', ''))
    for coreq in corequisites:
        if coreq not in advised_courses:
            reasons.append(f'Corequisite {coreq} not met.')
    
    if not reasons:
        return 'Eligible', 'All requirements met.'
    else:
        return 'Not Eligible', '; '.join(reasons)

def highlight_row(row):
    """Apply background colors based on action/status."""
    action = row.get('Action', '')
    status = row.get('Eligibility Status', '')
    if 'Completed' in action:
        return ['background-color: lightgray'] * len(row)
    elif 'Advised' in action:
        return ['background-color: lightgreen'] * len(row)
    elif 'Optional' in action:
        return ['background-color: #fffacd'] * len(row)
    elif status == 'Eligible':
        return ['background-color: #e0ffe0'] * len(row)
    elif status == 'Not Eligible':
        return ['background-color: lightcoral'] * len(row)
    return [''] * len(row)

def style_df(df):
    """Apply styling to DataFrame."""
    styled = df.style.apply(highlight_row, axis=1)
    styled = styled.set_properties(**{'text-align': 'left'})
    styled = styled.set_table_styles([{
        'selector': 'th',
        'props': [('text-align', 'left'), ('font-weight', 'bold')]
    }])
    widths = {
        'Course Code': '80px',
        'Type': '80px',
        'Requisites': '250px',
        'Eligibility Status': '120px',
        'Justification': '200px',
        'Offered': '60px',
        'Action': '150px'
    }
    for col, w in widths.items():
        if col in df.columns:
            styled = styled.set_properties(subset=[col], **{'width': w})
    return styled
