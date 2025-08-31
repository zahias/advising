# utils.py

import logging
from io import BytesIO
from typing import Any, Dict, List, Tuple

import numpy as np
import pandas as pd

# ---------------- Logging ----------------

logging.basicConfig(
    filename="app.log",
    filemode="a",
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

def log_info(msg: str) -> None:
    try:
        logger.info(msg)
    except Exception:
        pass

def log_error(msg: str, err: Exception | str) -> None:
    try:
        logger.error(f"{msg}: {err}", exc_info=isinstance(err, Exception))
    except Exception:
        pass


# ------------- Progress report loading (supports 2 sheets) --------------

_BASE_COLS = [
    "ID",
    "NAME",
    "# of Credits Completed",
    "# Registered",
    "# Remaining",
    "Total Credits",
]

def _split_base_and_courses(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    base_cols = [c for c in _BASE_COLS if c in df.columns]
    course_cols = [c for c in df.columns if c not in base_cols]
    # ensure ID/NAME present for merges
    if "ID" not in df.columns or "NAME" not in df.columns:
        raise ValueError("Progress report must include 'ID' and 'NAME' columns.")
    base = df[["ID", "NAME"] + [c for c in _BASE_COLS if c not in ("ID", "NAME") and c in df.columns]]
    courses = df[["ID", "NAME"] + course_cols]
    return base, courses

def load_progress_excel(content: bytes | BytesIO | str) -> pd.DataFrame:
    """
    Accepts bytes/BytesIO/path to an Excel file.
    If it contains 'Required Courses' and 'Intensive Courses' sheets, it merges them
    into one DataFrame (union of course columns). Otherwise reads the first sheet.
    """
    xls = pd.ExcelFile(BytesIO(content) if isinstance(content, (bytes, BytesIO)) else content)
    sheets = set(xls.sheet_names)
    if {"Required Courses", "Intensive Courses"}.issubset(sheets):
        req = pd.read_excel(xls, sheet_name="Required Courses")
        intl = pd.read_excel(xls, sheet_name="Intensive Courses")
        base_req, req_courses = _split_base_and_courses(req)
        _, intl_courses = _split_base_and_courses(intl)
        # drop any base columns that might linger in the course dfs
        to_drop = [c for c in _BASE_COLS if c in req_courses.columns]
        req_courses = req_courses.drop(columns=to_drop, errors="ignore")
        to_drop = [c for c in _BASE_COLS if c in intl_courses.columns]
        intl_courses = intl_courses.drop(columns=to_drop, errors="ignore")
        # left-merge on ID+NAME
        merged = base_req.merge(req_courses, on=["ID", "NAME"], how="left")
        merged = merged.merge(intl_courses, on=["ID", "NAME"], how="left")
        return merged
    # fallback: first sheet
    return pd.read_excel(xls)


# ---------------- Standing & cell normalization ----------------

def get_student_standing(total_credits_completed: float | int) -> str:
    try:
        x = float(total_credits_completed)
    except Exception:
        x = 0.0
    if x >= 60:
        return "Senior"
    if x >= 30:
        return "Junior"
    return "Sophomore"

def _norm_cell(val: Any) -> str:
    """
    Canonicalize a progress-cell value.
    - 'c' or 'C' -> 'c' (Completed)
    - 'nc'/'NC' or any other token -> 'nc' (Not completed)
    - NaN / None / '' -> 'reg' (Currently registered)
    """
    # treat NaN/None/'' as registered
    if val is None:
        return "reg"
    # pandas NaN
    if isinstance(val, float) and np.isnan(val):
        return "reg"
    # pandas NA/NaT
    try:
        import pandas as _pd
        if _pd.isna(val):
            return "reg"
    except Exception:
        pass
    s = str(val).strip().lower()
    if s == "":
        return "reg"
    if s == "c":
        return "c"
    if s == "nc":
        return "nc"
    # unknown tokens → conservative: not completed
    return "nc"

def check_course_completed(row: pd.Series, course_code: str) -> bool:
    return _norm_cell(row.get(course_code)) == "c"

def check_course_registered(row: pd.Series, course_code: str) -> bool:
    return _norm_cell(row.get(course_code)) == "reg"


# ---------------- Courses table helpers ----------------

def is_course_offered(courses_df: pd.DataFrame, course_code: str) -> bool:
    if courses_df.empty:
        return False
    row = courses_df.loc[courses_df["Course Code"] == course_code]
    if row.empty:
        return False
    return str(row["Offered"].iloc[0]).strip().lower() == "yes"

def parse_requirements(req_str: str) -> List[str]:
    if pd.isna(req_str) or req_str is None:
        return []
    s = str(req_str).strip()
    if not s or s.upper() == "N/A":
        return []
    # split on commas/semicolons and the word 'and'
    parts = [p.strip() for chunk in s.replace(" and ", ",").split(",") for p in chunk.split(";")]
    return [p for p in parts if p]

def build_requisites_str(course_info: pd.Series | Dict[str, Any]) -> str:
    pieces = []
    for key, prefix in [("Prerequisite", "Prereq"), ("Concurrent", "Conc"), ("Corequisite", "Coreq")]:
        v = course_info.get(key, "")
        if pd.isna(v):
            continue
        v = str(v).strip()
        if v and v.upper() != "N/A":
            pieces.append(f"{prefix}: {v}")
    return "; ".join(pieces) if pieces else "None"


# ---------------- Eligibility engine ----------------

def _standing_satisfies(token: str, standing: str) -> bool:
    t = token.lower()
    if "senior" in t:
        return standing == "Senior"
    if "junior" in t:
        return standing in {"Junior", "Senior"}
    if "sophomore" in t:
        return standing in {"Sophomore", "Junior", "Senior"}
    return False

def check_eligibility(
    student_row: pd.Series,
    course_code: str,
    advised_courses: List[str],
    courses_df: pd.DataFrame,
) -> Tuple[str, str]:
    """
    Returns (status, justification).
    - Completed -> ('Completed', 'Already completed.')
    - Registered -> ('Registered', 'Already registered for this course.')
    - Otherwise -> 'Eligible' / 'Not Eligible'
    NOTE: 'Registered' **satisfies** prerequisites, concurrent, and corequisites,
    and that satisfaction is **noted** in the justification text.
    """
    if check_course_completed(student_row, course_code):
        return "Completed", "Already completed."
    if check_course_registered(student_row, course_code):
        return "Registered", "Already registered for this course."

    row = courses_df.loc[courses_df["Course Code"] == course_code]
    if row.empty:
        return "Not Eligible", "Course not found in courses table."
    row = row.iloc[0]

    credits_c = student_row.get("# of Credits Completed", 0)
    credits_r = student_row.get("# Registered", 0)
    total = (credits_c if pd.notna(credits_c) else 0) + (credits_r if pd.notna(credits_r) else 0)
    standing = get_student_standing(total)

    reasons: List[str] = []
    notes: List[str] = []

    # Offered?
    if not is_course_offered(courses_df, course_code):
        reasons.append("Course not offered.")

    def _satisfies(token: str) -> bool:
        tok = token.strip()
        # standing tokens
        if "standing" in tok.lower():
            return _standing_satisfies(tok, standing)
        # course tokens: completed OR registered OR advised
        if check_course_completed(student_row, tok):
            return True
        if check_course_registered(student_row, tok):
            notes.append(f"Requirement '{tok}' satisfied by current registration.")
            return True
        return tok in (advised_courses or [])

    # Prereqs
    for p in parse_requirements(row.get("Prerequisite", "")):
        if not _satisfies(p):
            reasons.append(f"Prerequisite '{p}' not satisfied.")

    # Concurrent
    for c in parse_requirements(row.get("Concurrent", "")):
        if not _satisfies(c):
            reasons.append(f"Concurrent requirement '{c}' not satisfied.")

    # Coreq
    for c in parse_requirements(row.get("Corequisite", "")):
        if not _satisfies(c):
            reasons.append(f"Corequisite '{c}' not satisfied.")

    if reasons:
        msg = "; ".join(reasons)
        if notes:
            msg += " " + " ".join(notes)
        return "Not Eligible", msg

    just = "All requirements met."
    if notes:
        just += " " + " ".join(notes)
    return "Eligible", just


# ---------------- Styling ----------------

def style_df(df: pd.DataFrame) -> "pd.io.formats.style.Styler":
    def _row_style(row):
        val = str(row.get("Action") or row.get("Eligibility Status") or "").lower()
        color = ""
        if "completed" in val:
            color = "#D5E8D4"      # green
        elif "registered" in val:
            color = "#BDD7EE"      # blue
        elif "advised" in val:
            color = "#FFF2CC"      # light yellow
        elif "eligible (not chosen)" in val or val == "eligible":
            color = "#E1F0FF"      # light blue
        elif "not eligible" in val:
            color = "#F8CECC"      # red
        return [f"background-color: {color}"] * len(row)

    styled = df.style.apply(_row_style, axis=1)
    styled = styled.set_table_styles([{"selector": "th", "props": [("text-align", "left"), ("font-weight", "bold")]}])
    return styled
