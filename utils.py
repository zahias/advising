# utils.py

import pandas as pd
import logging
from typing import List, Tuple, Dict, Any

# --- Logging -------------------------------------------------------------

logging.basicConfig(
    filename="app.log",
    filemode="a",
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

def log_info(message: str) -> None:
    try:
        logger.info(message)
    except Exception:
        pass

def log_error(message: str, error: Exception | str) -> None:
    try:
        logger.error(f"{message}: {error}", exc_info=isinstance(error, Exception))
    except Exception:
        pass

# --- Course cell normalization ------------------------------------------

def _norm_cell(val: Any) -> str:
    """
    Normalize a progress cell to one of:
      - 'c'  -> completed
      - 'nc' -> not completed
      - 'reg'-> currently registered (empty cell)
    Any unexpected token is treated as 'nc' to be conservative.
    """
    if val is None:
        return "reg"
    s = str(val).strip().lower()
    if s == "":
        return "reg"
    if s == "c":
        return "c"
    if s == "nc":
        return "nc"
    return "nc"

def check_course_completed(row: pd.Series, course_code: str) -> bool:
    return _norm_cell(row.get(course_code)) == "c"

def check_course_registered(row: pd.Series, course_code: str) -> bool:
    return _norm_cell(row.get(course_code)) == "reg"

# --- Standing ------------------------------------------------------------

def get_student_standing(total_credits_completed: float | int) -> str:
    """
    Maps credits to standing. Preserves original app's buckets.
    """
    try:
        tc = float(total_credits_completed)
    except Exception:
        tc = 0.0
    if tc >= 60:
        return "Senior"
    if tc >= 30:
        return "Junior"
    return "Sophomore"

# --- Courses table helpers ----------------------------------------------

def parse_requirements(req_str: str) -> List[str]:
    """
    Turn a free-text requirement like 'PBHL 201; Junior standing' into tokens.
    Splits on commas, semicolons, and 'and'.
    """
    if pd.isna(req_str) or req_str is None:
        return []
    s = str(req_str).strip()
    if not s or s.upper() == "N/A":
        return []
    # Split on delimiters
    parts = [p.strip() for chunk in s.replace(" and ", ",").split(",") for p in chunk.split(";")]
    return [p for p in parts if p]

def is_course_offered(courses_df: pd.DataFrame, course_code: str) -> bool:
    if courses_df.empty:
        return False
    row = courses_df.loc[courses_df["Course Code"] == course_code]
    if row.empty:
        return False
    return str(row["Offered"].iloc[0]).strip().lower() == "yes"

def build_requisites_str(course_info: pd.Series | Dict[str, Any]) -> str:
    pieces = []
    for key, prefix in [("Prerequisite", "Prereq"), ("Concurrent", "Conc"), ("Corequisite", "Coreq")]:
        value = course_info.get(key, "")
        if pd.isna(value) or str(value).strip() == "" or str(value).strip().upper() == "N/A":
            continue
        pieces.append(f"{prefix}: {str(value).strip()}")
    return "; ".join(pieces) if pieces else "None"

# --- Eligibility ---------------------------------------------------------

def _standing_satisfies(req: str, standing: str) -> bool:
    req_l = req.strip().lower()
    if "senior" in req_l:
        return standing == "Senior"
    if "junior" in req_l:
        return standing in ("Junior", "Senior")
    if "sophomore" in req_l:
        return standing in ("Sophomore", "Junior", "Senior")
    return False

def check_eligibility(
    student_row: pd.Series,
    course_code: str,
    advised_courses: List[str],
    courses_df: pd.DataFrame,
) -> Tuple[str, str]:
    """
    Returns (status, justification).
    status in {'Eligible','Not Eligible','Completed','Registered'}
    NOTE: As requested, 'currently registered' satisfies requisites.
          This is also *noted* in the justification.
    """
    # Completed and Registered checks
    if check_course_completed(student_row, course_code):
        return "Completed", "Already completed."
    if check_course_registered(student_row, course_code):
        return "Registered", "Already registered for this course."

    # Find course row
    course_row = courses_df.loc[courses_df["Course Code"] == course_code]
    if course_row.empty:
        return "Not Eligible", "Course not found in courses table."

    standing = get_student_standing(
        float(student_row.get("# of Credits Completed", 0)) + float(student_row.get("# Registered", 0))
    )
    reasons: List[str] = []
    notes: List[str] = []

    # Offered?
    if not is_course_offered(courses_df, course_code):
        reasons.append("Course not offered.")

    # Helper: does req satisfied? completed/registered/advised/standing
    def _satisfies(token: str) -> bool:
        tok = token.strip()
        # Standing clauses like "Junior standing"
        if "standing" in tok.lower():
            return _standing_satisfies(tok, standing)
        # Course codes satisfy if completed OR currently registered OR advised
        comp = check_course_completed(student_row, tok)
        reg = check_course_registered(student_row, tok)
        adv = tok in (advised_courses or [])
        if reg:
            notes.append(f"Requirement '{tok}' satisfied by current registration.")
        return comp or reg or adv

    # Prereq/Concurrent/Coreq
    for col, label in [("Prerequisite", "Prerequisite"), ("Concurrent", "Concurrent requirement"), ("Corequisite", "Corequisite")]:
        reqs = parse_requirements(course_row[col].iloc[0] if col in course_row.columns else "")
        for r in reqs:
            if not _satisfies(r):
                reasons.append(f"{label} '{r}' not satisfied.")

    if reasons:
        just = "; ".join(reasons)
        if notes:
            just += " " + " ".join(notes)
        return "Not Eligible", just

    justification = "All requirements met."
    if notes:
        justification += " " + " ".join(notes)

    return "Eligible", justification

# --- Styling for Streamlit tables ---------------------------------------

def style_df(df: pd.DataFrame) -> "pd.io.formats.style.Styler":
    """
    Color-code common Action/Status values. Widths are hints only (Streamlit may ignore).
    """
    def _row_style(row):
        val = str(row.get("Action") or row.get("Eligibility Status") or "").lower()
        color = ""
        if "completed" in val:
            color = "#D5E8D4"  # green
        elif "advised" in val:
            color = "#FFF2CC"  # light yellow
        elif "eligible (not chosen)" in val or val == "eligible":
            color = "#E1F0FF"  # light blue
        elif "registered" in val:
            color = "#BDD7EE"  # blue
        elif "not eligible" in val:
            color = "#F8CECC"  # red
        return [f"background-color: {color}"] * len(row)

    styled = df.style.apply(_row_style, axis=1)
    # Bold headers & basic alignment
    styled = styled.set_table_styles([{
        "selector": "th",
        "props": [("text-align", "left"), ("font-weight", "bold")]
    }])
    return styled
