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
      - 'c'  -> completed
      - 'cr' -> currently registered (BLANK / NaN)
      - 'nc' -> not completed
    Any unexpected token is treated as 'nc'.
    """
    # IMPORTANT: in Excel -> pandas, blanks usually arrive as NaN
    if val is None or (isinstance(val, float) and pd.isna(val)) or pd.isna(val):
        return "cr"
    s = str(val).strip().lower()
    if s == "":
        return "cr"
    if s == "c":
        return "c"
    if s in {"cr", "reg"}:  # accept legacy 'reg' tokens for compatibility
        return "cr"
    if s == "nc":
        return "nc"
    return "nc"

def check_course_completed(row: pd.Series, course_code: str) -> bool:
    return _norm_cell(row.get(course_code)) == "c"

def check_course_registered(row: pd.Series, course_code: str) -> bool:
    return _norm_cell(row.get(course_code)) == "cr"


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

def get_corequisite_and_concurrent_courses(courses_df: pd.DataFrame) -> List[str]:
    """
    Returns a list of courses that appear as co-requisites or concurrent requirements
    for other courses. These are the only courses that make sense for simulation since
    prerequisites would already be completed before students take dependent courses.
    """
    coreq_concurrent_courses = set()
    
    for _, row in courses_df.iterrows():
        # Check Co-Requisites column
        if "Corequisite" in row and not pd.isna(row["Corequisite"]):
            coreqs = parse_requirements(row["Corequisite"])
            coreq_concurrent_courses.update(coreqs)
        
        # Check Concurrent column
        if "Concurrent" in row and not pd.isna(row["Concurrent"]):
            concurrents = parse_requirements(row["Concurrent"])
            coreq_concurrent_courses.update(concurrents)
    
    return sorted(list(coreq_concurrent_courses))


def get_mutual_concurrent_pairs(courses_df: pd.DataFrame) -> Dict[str, List[str]]:
    """
    Detect mutual concurrent/corequisite pairs where Course A requires Course B
    AND Course B requires Course A (either as concurrent or corequisite).
    
    Returns dict mapping course_code -> list of mutually required courses.
    """
    # Build a map of course -> courses it requires (concurrent/corequisite)
    requires_map = {}
    for _, row in courses_df.iterrows():
        course_code = row.get("Course Code", "")
        if not course_code:
            continue
        
        requirements = set()
        
        # Check Corequisite column
        if "Corequisite" in row and not pd.isna(row["Corequisite"]):
            coreqs = parse_requirements(row["Corequisite"])
            requirements.update(coreqs)
        
        # Check Concurrent column
        if "Concurrent" in row and not pd.isna(row["Concurrent"]):
            concurrents = parse_requirements(row["Concurrent"])
            requirements.update(concurrents)
        
        requires_map[course_code] = requirements
    
    # Find mutual pairs: A requires B AND B requires A
    mutual_pairs = {}
    for course_a, reqs_a in requires_map.items():
        mutual_courses = []
        for course_b in reqs_a:
            # Check if course_b also requires course_a
            if course_b in requires_map and course_a in requires_map[course_b]:
                mutual_courses.append(course_b)
        
        if mutual_courses:
            mutual_pairs[course_a] = mutual_courses
    
    return mutual_pairs


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
    registered_courses: List[str] = None,
    ignore_offered: bool = False,
    mutual_pairs: Dict[str, List[str]] = None,
) -> Tuple[str, str]:
    """
    Returns (status, justification).
    status in {'Eligible','Not Eligible','Completed','Registered'}

    As agreed: *currently registered* satisfies requisites and is **noted**.
    
    registered_courses: List of courses the student is registered for (including simulated).
                        Used for concurrent/corequisite checks only, NOT prerequisites.
    ignore_offered: If True, skip the "Course not offered" check. Used by Full Student View
                    for planning purposes where offered status doesn't matter.
    mutual_pairs: Dict mapping course_code -> list of mutually required courses.
                  If provided, mutual concurrent/corequisite pairs are treated as eligible.
    """
    if registered_courses is None:
        registered_courses = []
    if mutual_pairs is None:
        mutual_pairs = {}
    
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
    mutual_notes: List[str] = []

    # Offered? (skip check if ignore_offered=True for planning views)
    if not ignore_offered and not is_course_offered(courses_df, course_code):
        reasons.append("Course not offered.")

    def _satisfies_prerequisite(token: str) -> bool:
        tok = token.strip()
        if "standing" in tok.lower():
            return _standing_satisfies(tok, standing)
        comp = check_course_completed(student_row, tok)
        reg = check_course_registered(student_row, tok)
        adv = tok in (advised_courses or [])
        if reg:
            notes.append(f"Prerequisite '{tok}' satisfied by current registration.")
        return comp or reg or adv
    
    def _satisfies_concurrent_or_coreq(token: str, is_mutual: bool = False) -> bool:
        tok = token.strip()
        if "standing" in tok.lower():
            return _standing_satisfies(tok, standing)
        comp = check_course_completed(student_row, tok)
        reg = check_course_registered(student_row, tok)
        adv = tok in (advised_courses or [])
        sim = tok in (registered_courses or [])
        if reg or sim:
            notes.append(f"Requirement '{tok}' satisfied by current registration.")
        if is_mutual and not (comp or reg or adv or sim):
            mutual_notes.append(tok)
            return True
        return comp or reg or adv or sim

    # Prerequisites: Only completed or advised courses satisfy
    prereq_str = course_row["Prerequisite"].iloc[0] if "Prerequisite" in course_row.columns else ""
    prereqs = parse_requirements(prereq_str)
    for r in prereqs:
        if not _satisfies_prerequisite(r):
            reasons.append(f"Prerequisite '{r}' not satisfied.")
    
    # Get mutual courses for this course
    my_mutual_courses = mutual_pairs.get(course_code, [])
    
    # Concurrent/Corequisites: Completed, registered, advised, simulated, OR mutual pairs satisfy
    for col, label in [
        ("Concurrent", "Concurrent requirement"),
        ("Corequisite", "Corequisite"),
    ]:
        reqs = parse_requirements(course_row[col].iloc[0] if col in course_row.columns else "")
        for r in reqs:
            is_mutual = r in my_mutual_courses
            if not _satisfies_concurrent_or_coreq(r, is_mutual=is_mutual):
                reasons.append(f"{label} '{r}' not satisfied.")

    if reasons:
        just = "; ".join(reasons)
        if notes:
            just += " " + " ".join(notes)
        return "Not Eligible", just

    justification = "All requirements met."
    if mutual_notes:
        paired = ", ".join(mutual_notes)
        justification = f"Must be taken with: {paired}."
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


# ------------- Curriculum Year Calculation -------------------

def calculate_course_curriculum_years(courses_df: pd.DataFrame) -> Dict[str, int]:
    """
    Analyzes prerequisite chains to assign a curriculum year to each course.
    
    Curriculum Year 1: Courses with no prerequisites
    Curriculum Year 2: Courses whose prerequisites are all in Year 1
    Curriculum Year 3: Courses whose prerequisites include Year 2 courses
    And so on...
    
    Returns a dict mapping course_code -> curriculum_year (1, 2, 3, etc.)
    """
    course_years = {}
    
    # Build prerequisite map and standing requirements
    prereq_map = {}
    standing_requirements = {}
    
    for _, course_row in courses_df.iterrows():
        course_code = course_row["Course Code"]
        all_prereqs = parse_requirements(course_row.get("Prerequisite", ""))
        
        # Separate course prerequisites from standing requirements
        course_prereqs = []
        standing_req = None
        
        for p in all_prereqs:
            if "standing" in p.lower():
                standing_req = p
            else:
                course_prereqs.append(p)
        
        prereq_map[course_code] = course_prereqs
        standing_requirements[course_code] = standing_req
    
    # Recursively calculate curriculum year for each course
    def get_course_year(course_code: str, visited=None) -> int:
        if visited is None:
            visited = set()
        
        # Already calculated
        if course_code in course_years:
            return course_years[course_code]
        
        # Circular dependency detection
        if course_code in visited:
            return 1  # Default to Year 1 for circular dependencies
        
        visited.add(course_code)
        
        # Get prerequisites for this course
        prereqs = prereq_map.get(course_code, [])
        standing_req = standing_requirements.get(course_code)
        
        # Calculate base year from prerequisite courses
        max_prereq_year = 0
        for prereq_code in prereqs:
            if prereq_code in prereq_map:  # Only consider courses in our table
                prereq_year = get_course_year(prereq_code, visited.copy())
                max_prereq_year = max(max_prereq_year, prereq_year)
        
        # Determine minimum year based on standing requirement
        # Junior standing (30 credits) typically achievable by Year 2
        # Senior standing (60 credits) typically achievable by Year 3
        standing_year = 1
        if standing_req:
            if "senior" in standing_req.lower():
                standing_year = 3
            elif "junior" in standing_req.lower():
                standing_year = 2
        
        # The course year is the maximum of prerequisite-based year and standing-based year
        course_year = max(max_prereq_year + 1, standing_year)
        course_years[course_code] = course_year
        return course_year
    
    # Calculate year for all courses
    for course_code in prereq_map.keys():
        get_course_year(course_code)
    
    return course_years


def calculate_student_curriculum_year(student_row: pd.Series, courses_df: pd.DataFrame, course_curriculum_years: Dict[str, int] = None) -> int:
    """
    Determines which curriculum year a student is in based on their completed/registered courses.
    
    A student is in Curriculum Year N if they have completed (or are registered for) 
    all prerequisite chains needed to take Year N courses, but have not yet completed 
    the prerequisites for Year N+1.
    
    Args:
        student_row: Student's progress data
        courses_df: Courses table
        course_curriculum_years: Pre-calculated course years (optional, will calculate if not provided)
    
    Returns:
        Curriculum year (1, 2, 3, etc.)
    """
    if course_curriculum_years is None:
        course_curriculum_years = calculate_course_curriculum_years(courses_df)
    
    # Get all courses the student has completed or is registered for
    completed_or_registered = []
    for course_code in courses_df["Course Code"]:
        if check_course_completed(student_row, course_code) or check_course_registered(student_row, course_code):
            completed_or_registered.append(course_code)
    
    if not completed_or_registered:
        # No courses completed or registered -> Year 1
        return 1
    
    # Find the highest curriculum year of courses they've completed/registered
    max_year_completed = max(
        (course_curriculum_years.get(course, 1) for course in completed_or_registered),
        default=1
    )
    
    # Check if they can progress to the next year
    # They can progress if they've completed all Year N prerequisites needed for Year N+1
    next_year = max_year_completed + 1
    can_take_next_year = False
    
    for course_code, year in course_curriculum_years.items():
        if year == next_year:
            # Check if student is eligible for any Year N+1 course
            is_eligible_status, _ = check_eligibility(
                student_row,
                course_code,
                [],
                courses_df,
                ignore_offered=True
            )
            if is_eligible_status == "Eligible":
                can_take_next_year = True
                break
    
    # If they can take Year N+1 courses, they're in Year N+1
    # Otherwise they're in Year N
    return next_year if can_take_next_year else max_year_completed