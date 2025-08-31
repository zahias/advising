# utils.py

import pandas as pd
import logging
from io import BytesIO
from typing import List, Tuple, Dict, Any

# ---------------- Logging ----------------

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


# ------------- Progress-cell normalization -------------

def _norm_cell(val: Any) -> str:
    """
    Normalize a progress cell to one of:
      - 'c'   -> completed
      - 'nc'  -> not completed
      - 'reg' -> currently registered  (BLANK / NaN)
    Any unexpected token is treated as 'nc'.
    """
    # IMPORTANT: in Excel -> pandas, blanks usually arrive as NaN
    if val is None or (isinstance(val, float) and pd.isna(val)) or pd.isna(val):
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


# ------------- Standing -------------------

def get_student_standing(total_credits_completed: float | int) -> str:
    """Preserves original app's buckets."""
    try:
        tc = float(total_credits_completed)
    except Exception:
        tc = 0.0
    if tc >= 60:
        return "Senior"
    if tc >= 30:
        return "Junior"
    return "Sophomore"


# ------------- Courses-table helpers -------------------

def parse_requirements(req_str: str) -> List[str]:
    if pd.isna(req_str) or req_str is None:
        return []
    s = str(req_str).strip()
    if not s or s.upper() == "N/A":
        return []
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
        if pd.isna(value) or str(value).strip() in ("", "N/A"):
            continue
        pieces.append(f"{prefix}: {str(value).strip()}")
    return "; ".join(pieces) if pieces else "None"


# ------------- Eligibility -----------------------------

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

    As agreed: *currently registered* satisfies requisites and is **noted**.
    """
    # Completed / Registered short-circuit
    if check_course_completed(student_row, course_code):
        return "Completed", "Already completed."
    if check_course_registered(student_row, course_code):
        return "Registered", "Already registered for this course."

    # Locate course metadata
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

    def _satisfies(token: str) -> bool:
        tok = token.strip()
        # Standing clauses
        if "standing" in tok.lower():
            return _standing_satisfies(tok, standing)
        # Course tokens: completed OR registered OR advised
        comp = check_course_completed(student_row, tok)
        reg = check_course_registered(student_row, tok)
        adv = tok in (advised_courses or [])
        if reg:
            notes.append(f"Requirement '{tok}' satisfied by current registration.")
        return comp or reg or adv

    # Apply to all requirement columns
    for col, label in [
        ("Prerequisite", "Prerequisite"),
        ("Concurrent", "Concurrent requirement"),
        ("Corequisite", "Corequisite"),
    ]:
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


# ------------- Styling for Streamlit tables --------------

def style_df(df: pd.DataFrame) -> "pd.io.formats.style.Styler":
    def _row_style(row):
        val = str(row.get("Action") or row.get("Eligibility Status") or "").lower()
        color = ""
        if "completed" in val:
            color = "#D5E8D4"  # green
        elif "advised" in val:
            color = "#FFF2CC"  # yellow
        elif "registered" in val:
            color = "#BDD7EE"  # blue
        elif "eligible (not chosen)" in val or val == "eligible":
            color = "#E1F0FF"  # light blue
        elif "not eligible" in val:
            color = "#F8CECC"  # red
        return [f"background-color: {color}"] * len(row)

    styled = df.style.apply(_row_style, axis=1)
    styled = styled.set_table_styles([{
        "selector": "th",
        "props": [("text-align", "left"), ("font-weight", "bold")]
    }])
    return styled


# ------------- Progress loader (merges Intensive sheet) ------------------

_BASE_ID_NAME = ["ID", "NAME"]
_NUMERIC_PREFS = ["# of Credits Completed", "# Registered", "# Remaining", "Total Credits"]

def _coalesce(a: pd.Series | None, b: pd.Series | None):
    if a is None and b is None:
        return None
    if a is None:
        return b
    if b is None:
        return a
    return a.combine_first(b)

def load_progress_excel(content: bytes | BytesIO | str) -> pd.DataFrame:
    """
    Load a progress report that may have two sheets:
      - 'Required Courses'
      - 'Intensive Courses'
    Returns a single DataFrame with all course columns merged on (ID, NAME).
    Works with bytes, BytesIO, or a file path.
    """
    io_obj = BytesIO(content) if isinstance(content, (bytes, bytearray)) else content
    sheets = pd.read_excel(io_obj, sheet_name=None)
    # Pick required/intensive by name; fallbacks if names differ slightly
    req_key = next((k for k in sheets.keys() if "required" in k.lower()), None)
    int_key = next((k for k in sheets.keys() if "intensive" in k.lower()), None)

    if req_key is None:
        # Fallback: take the first as "required"
        req_key = list(sheets.keys())[0]
    req_df = sheets[req_key].copy()

    if int_key is None:
        # No Intensive sheet -> return required only
        return req_df

    int_df = sheets[int_key].copy()

    # Make sure ID/NAME exist
    for col in _BASE_ID_NAME:
        if col not in req_df.columns:
            req_df[col] = None
        if col not in int_df.columns:
            int_df[col] = None

    # Separate course columns
    def course_cols(df: pd.DataFrame) -> List[str]:
        return [c for c in df.columns if c not in _BASE_ID_NAME + _NUMERIC_PREFS]

    req_courses = course_cols(req_df)
    int_courses = course_cols(int_df)

    # Merge on ID/NAME (outer, to be safe)
    merged = pd.merge(
        req_df[_BASE_ID_NAME + req_courses + [c for c in _NUMERIC_PREFS if c in req_df.columns]],
        int_df[_BASE_ID_NAME + int_courses + [c for c in _NUMERIC_PREFS if c in int_df.columns]],
        on=_BASE_ID_NAME,
        how="outer",
        suffixes=("", "_int"),
    )

    # Coalesce numeric preference columns (prefer Required sheet values)
    for col in _NUMERIC_PREFS:
        a = merged[col] if col in merged.columns else None
        b = merged[f"{col}_int"] if f"{col}_int" in merged.columns else None
        out = _coalesce(a, b)
        if out is not None:
            merged[col] = out
        # Drop the *_int helper if it exists
        if f"{col}_int" in merged.columns:
            merged.drop(columns=[f"{col}_int"], inplace=True, errors="ignore")

    return merged
