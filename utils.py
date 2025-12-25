# utils.py

import pandas as pd
import logging
from io import BytesIO
from typing import List, Tuple, Dict, Any

# Import eligibility functions from standalone module to prevent circular imports
from eligibility_utils import (
    check_course_completed,
    check_course_registered,
    get_student_standing,
    parse_requirements,
    is_course_offered,
    build_requisites_str,
    get_corequisite_and_concurrent_courses,
    get_mutual_concurrent_pairs,
    check_eligibility,
)

# Re-export for backward compatibility
__all__ = [
    "check_course_completed",
    "check_course_registered", 
    "get_student_standing",
    "parse_requirements",
    "is_course_offered",
    "build_requisites_str",
    "get_corequisite_and_concurrent_courses",
    "get_mutual_concurrent_pairs",
    "check_eligibility",
    "style_df",
    "load_progress_excel",
    "log_info",
    "log_error",
    "calculate_course_curriculum_years",
    "calculate_student_curriculum_year",
]

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
    # Filter out empty/null entries before combine_first to avoid FutureWarning
    a_filtered = a.dropna() if hasattr(a, 'dropna') else a
    b_filtered = b.dropna() if hasattr(b, 'dropna') else b
    if len(a_filtered) == 0:
        return b
    if len(b_filtered) == 0:
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