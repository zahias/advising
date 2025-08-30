# utils.py

import pandas as pd
import logging

# ---------- Logging ----------
logging.basicConfig(
    filename="app.log",
    filemode="a",
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger()

def log_info(msg: str):
    try:
        logger.info(msg)
    except Exception:
        pass

def log_error(msg: str):
    try:
        logger.error(msg)
    except Exception:
        pass

# ---------- Core helpers ----------

def get_student_standing(credits_completed: float) -> str:
    """
    Map total earned/registered credits to standing.
    NOTE: Historical behavior keeps <30 as Sophomore.
    """
    if credits_completed >= 60:
        return "Senior"
    elif credits_completed >= 30:
        return "Junior"
    else:
        return "Sophomore"

def is_course_offered(courses_df: pd.DataFrame, course_code: str) -> bool:
    """Return True if the 'Offered' field for the course is 'yes' (case-insensitive)."""
    try:
        offered = courses_df.loc[courses_df["Course Code"] == course_code, "Offered"]
        if offered.empty:
            return False
        return str(offered.iloc[0]).strip().lower() == "yes"
    except Exception:
        return False

def _norm_cell(x) -> str:
    """
    Normalize a progress cell to one of:
      - 'c'  -> completed
      - 'nc' -> not completed
      - 'reg'-> currently registered (empty cell in source)
    Any other token is treated as 'nc'.
    """
    if x is None:
        return "reg"
    s = str(x).strip().lower()
    if s == "":
        return "reg"
    if s == "c":
        return "c"
    if s == "nc":
        return "nc"
    return "nc"

def check_course_completed(student_row: pd.Series, course_code: str) -> bool:
    return _norm_cell(student_row.get(course_code)) == "c"

def check_course_registered(student_row: pd.Series, course_code: str) -> bool:
    return _norm_cell(student_row.get(course_code)) == "reg"

def build_requisites_str(course_info: pd.Series) -> str:
    """Build a human string for requisites."""
    pieces = []
    for key, prefix in [("Prerequisite", "Prereq"), ("Concurrent", "Conc"), ("Corequisite", "Coreq")]:
        val = course_info.get(key, "")
        if pd.isna(val):
            continue
        val = str(val).strip()
        if val and val.upper() != "N/A":
            pieces.append(f"{prefix}: {val}")
    return "; ".join(pieces) if pieces else "None"

def _parse_list(val: str) -> list:
    """Split a requisite cell into tokens."""
    if not isinstance(val, str) or not val.strip():
        return []
    # Split on commas/semicolons/and
    raw = []
    for token in val.replace(";", ",").replace(" and ", ",").split(","):
        t = token.strip()
        if t:
            raw.append(t)
    return raw

def check_eligibility(student_row: pd.Series, course_code: str, advised_courses: list, courses_df: pd.DataFrame):
    """
    Determine if a student is eligible to take a given course.
    Returns (status, justification)
      status ∈ {'Completed','Registered','Eligible','Not Eligible'}
    Rules:
      - Completed → Completed
      - Registered → Registered
      - Offered must be 'yes' (else Not Eligible)
      - Prereq: satisfied by COMPLETED or CURRENTLY REGISTERED (noted)
      - Concurrent/Coreq: satisfied by completed OR registered OR present in advised list
      - Standing requirements inside prerequisite text ('Junior', 'Senior') are enforced
    """
    # Look up course record
    row = courses_df[courses_df["Course Code"] == course_code]
    if row.empty:
        return "Not Eligible", "Course not found in table."
    info = row.iloc[0]

    # Quick exits for the course itself
    if check_course_completed(student_row, course_code):
        return "Completed", "Already completed."
    if check_course_registered(student_row, course_code):
        return "Registered", "Already registered for this course."

    reasons = []
    notes = []

    # Offered check
    if not is_course_offered(courses_df, course_code):
        reasons.append("Course not offered this term.")

    # Standing from numeric credits
    cc = student_row.get("# of Credits Completed", 0)
    cr = student_row.get("# Registered", 0)
    total = (cc if pd.notna(cc) else 0) + (cr if pd.notna(cr) else 0)
    standing = get_student_standing(total)

    # Parse requisites
    prereq_raw = str(info.get("Prerequisite", "") or "")
    conc_raw   = str(info.get("Concurrent", "") or "")
    coreq_raw  = str(info.get("Corequisite", "") or "")

    prereqs = _parse_list(prereq_raw)
    concs   = _parse_list(conc_raw)
    coreqs  = _parse_list(coreq_raw)

    # Standing words inside prerequisites
    low = prereq_raw.lower()
    if "senior" in low and standing != "Senior":
        reasons.append("Requires Senior standing.")
    if "junior" in low and standing not in ["Junior", "Senior"]:
        reasons.append("Requires Junior standing or above.")

    # Course code style requisites (simple heuristic: contains a digit)
    def _is_course_code(tok: str) -> bool:
        return any(ch.isdigit() for ch in tok)

    # Prerequisites: completed OR registered (registration satisfies, but we note it)
    for p in [t for t in prereqs if _is_course_code(t)]:
        if check_course_completed(student_row, p):
            continue
        if check_course_registered(student_row, p):
            notes.append(f"Prerequisite '{p}' satisfied by current registration.")
            continue
        # Being 'advised' for a prerequisite does not satisfy it
        reasons.append(f"Prerequisite '{p}' not completed or registered.")

    # Concurrent: completed OR registered OR advised
    for c in [t for t in concs if _is_course_code(t)]:
        if (check_course_completed(student_row, c) or
            check_course_registered(student_row, c) or
            (advised_courses and c in advised_courses)):
            continue
        reasons.append(f"Concurrent requirement '{c}' not completed, registered, or advised together.")

    # Corequisite: completed OR registered OR advised
    for c in [t for t in coreqs if _is_course_code(t)]:
        if (check_course_completed(student_row, c) or
            check_course_registered(student_row, c) or
            (advised_courses and c in advised_courses)):
            continue
        reasons.append(f"Corequisite '{c}' not completed, registered, or advised together.")

    if reasons:
        return "Not Eligible", " ".join(reasons)
    # Eligible: include any informational notes
    justification = " ".join(notes) if notes else ""
    return "Eligible", justification

# ---------- Table styling ----------
def style_df(df: pd.DataFrame):
    """
    Apply background colors:
      - Action contains 'Completed' -> light gray
      - Action contains 'Registered' -> light blue
      - Action contains 'Advised' -> light green
      - Action contains 'Optional' -> light yellow
      - Status == 'Eligible' -> pale green
      - Status == 'Not Eligible' -> light coral
    """
    def row_style(row):
        action = str(row.get("Action", ""))
        status = str(row.get("Eligibility Status", ""))
        if "Completed" in action:
            return ["background-color: lightgray"] * len(row)
        if "Registered" in action:
            return ["background-color: #BDD7EE"] * len(row)  # light blue
        if "Advised" in action:
            return ["background-color: lightgreen"] * len(row)
        if "Optional" in action:
            return ["background-color: #FFFACD"] * len(row)
        if status == "Eligible":
            return ["background-color: #E0FFE0"] * len(row)
        if status == "Not Eligible":
            return ["background-color: lightcoral"] * len(row)
        return [""] * len(row)

    styled = df.style.apply(row_style, axis=1)
    # Light column width hints (Streamlit may ignore widths)
    widths = {
        "Course Code": "80px",
        "Type": "80px",
        "Requisites": "260px",
        "Eligibility Status": "120px",
        "Justification": "220px",
        "Offered": "60px",
        "Action": "150px",
    }
    for col, w in widths.items():
        if col in df.columns:
            styled = styled.set_properties(subset=[col], **{"width": w})
    return styled
