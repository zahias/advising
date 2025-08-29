# utils.py

import pandas as pd
import logging

# -------------------------------
# Centralized constants & colors
# -------------------------------

# Canonical 1-letter markers used in the wide "Full Student View"
STATUS_CODES = {
    "COMPLETED": "c",
    "ADVISED": "a",
    "ELIGIBLE_NOT_CHOSEN": "na",
    "NOT_ELIGIBLE": "ne",
}

# Human-readable action/legend labels (used in UI & Excel)
ACTION_LABELS = {
    "COMPLETED": "Completed",
    "ADVISED": "Advised",
    "OPTIONAL": "Optional",
    "ELIGIBLE_NOT_CHOSEN": "Eligible not chosen",
    "NOT_ELIGIBLE": "Not Eligible",
}

# One color system for both UI tables and Excel exports
# (hex without '#' so openpyxl PatternFill can reuse directly)
COLOR_MAP = {
    ACTION_LABELS["COMPLETED"]:       "C6EFCE",  # light green
    ACTION_LABELS["ADVISED"]:         "FFF2CC",  # light yellow
    ACTION_LABELS["OPTIONAL"]:        "FFFACD",  # lemon chiffon
    ACTION_LABELS["ELIGIBLE_NOT_CHOSEN"]: "E0FFE0",  # pale green
    ACTION_LABELS["NOT_ELIGIBLE"]:    "F8CBAD",  # light red
    # Eligibility status colors for on-screen (Eligible/Not Eligible/Completed)
    "Eligible":                       "E0FFE0",
    "Not Eligible":                   "F8CBAD",
    "Completed":                      "C6EFCE",
}

# -------------------------------
# Logging
# -------------------------------

logging.basicConfig(
    filename='app.log',
    filemode='a',
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO,
)
logger = logging.getLogger()

def log_info(message: str):
    try:
        logger.info(message)
    except Exception:
        pass

def log_error(message: str, exc: Exception = None):
    try:
        if exc:
            logger.error(f"{message}: {exc}")
        else:
            logger.error(message)
    except Exception:
        pass

# -------------------------------
# Domain helpers (unchanged API)
# -------------------------------

def get_student_standing(total_credits: int) -> str:
    """
    Standing bands:
      - <30   -> Sophomore
      - 30-59 -> Junior
      - >=60  -> Senior
    """
    if total_credits >= 60:
        return "Senior"
    if total_credits >= 30:
        return "Junior"
    return "Sophomore"

def check_course_completed(student_row: pd.Series, course_code: str) -> bool:
    """Return True if the progress report marks this course as completed ('c')."""
    val = str(student_row.get(course_code, "")).strip().lower()
    return val == STATUS_CODES["COMPLETED"]

def is_course_offered(courses_df: pd.DataFrame, course_code: str) -> bool:
    """Expect 'Offered' column to contain 'yes'/'no' (case-insensitive)."""
    row = courses_df[courses_df['Course Code'] == course_code]
    if row.empty:
        return False
    return str(row.iloc[0].get('Offered', '')).strip().lower() == 'yes'

def parse_requirements(req_str: str):
    """
    Parse requisites text into tokens; supports comma or '/' separated lists.
    Example: "PBHL201, PBHL202 / MATH200"
    """
    if not isinstance(req_str, str) or not req_str.strip():
        return []
    parts = []
    for chunk in req_str.replace('/', ',').split(','):
        code = chunk.strip()
        if code:
            parts.append(code)
    return parts

def build_requisites_str(course_row: pd.Series) -> str:
    """Render prerequisites/concurrent/corequisites into a single readable string."""
    bits = []
    for key, label in (('Prerequisite', 'Pre'), ('Concurrent', 'Con'), ('Corequisite', 'Co')):
        raw = str(course_row.get(key, '') or '').strip()
        if raw:
            bits.append(f"{label}: {raw}")
    return " | ".join(bits) if bits else ""

def check_eligibility(
    student_row: pd.Series,
    course_row: pd.Series,
    standing: str,
) -> tuple[str, str]:
    """
    Core rule engine:
    Returns (status, justification) where status in {'Eligible','Not Eligible','Completed'}.
    """
    code = course_row['Course Code']

    # Already completed?
    if check_course_completed(student_row, code):
        return "Completed", "Course already completed."

    # Offered this term?
    offered = str(course_row.get('Offered', '')).strip().lower() == 'yes'
    j = []
    if not offered:
        j.append("Course not offered.")

    # Standing requirement (if encoded in course table, optional)
    # Example: 'Min Standing' column with values 'Junior'/'Senior'
    min_standing = str(course_row.get('Min Standing', '')).strip()
    if min_standing:
        order = {'Sophomore': 0, 'Junior': 1, 'Senior': 2}
        if order.get(standing, 0) < order.get(min_standing, 0):
            j.append(f"Requires {min_standing} standing.")

    # Requisites
    def has(code_):
        return check_course_completed(student_row, code_)

    pre = parse_requirements(course_row.get('Prerequisite', ''))
    con = parse_requirements(course_row.get('Concurrent', ''))
    co  = parse_requirements(course_row.get('Corequisite', ''))

    missing_pre = [c for c in pre if not has(c)]
    # Concurrent/Coreq are advisory here; you can tighten rules if needed
    if missing_pre:
        j.append(f"Missing prerequisite(s): {', '.join(missing_pre)}.")

    status = "Eligible" if not missing_pre else "Not Eligible"
    if not offered and status == "Eligible":
        # keep Eligible but with justification that it's not offered
        pass
    if status != "Eligible":
        # make sure justification isn't empty
        if not j:
            j.append("Does not meet eligibility requirements.")

    return status, " ".join(j).strip()

def style_df(df: pd.DataFrame) -> pd.io.formats.style.Styler:
    """
    Color rows by the 'Eligibility Status' or 'Action' column using COLOR_MAP.
    Note: Streamlit's st.dataframe ignores widths from Styler; colors are kept.
    """
    styled = df.style

    def _row_color(row):
        key = None
        if 'Action' in row:
            key = str(row['Action'])
        elif 'Eligibility Status' in row:
            key = str(row['Eligibility Status'])
        color = COLOR_MAP.get(key)
        return [f'background-color: #{color}' if color else '' for _ in row.index]

    styled = styled.apply(_row_color, axis=1)

    # Suggestive widths (may be ignored by st.dataframe)
    widths = {
        'Course Code': '80px',
        'Type': '80px',
        'Requisites': '250px',
        'Eligibility Status': '120px',
        'Justification': '200px',
        'Offered': '60px',
        'Action': '150px',
    }
    for col, w in widths.items():
        if col in df.columns:
            styled = styled.set_properties(subset=[col], **{'width': w})
    return styled
