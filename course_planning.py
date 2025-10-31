# course_planning.py
from __future__ import annotations

import pandas as pd
import streamlit as st
from typing import Dict, List, Tuple, Any
from collections import defaultdict

from utils import (
    check_course_completed,
    check_course_registered,
    check_eligibility,
    get_student_standing,
    parse_requirements,
    log_info,
    log_error,
)


def calculate_student_remaining_credits(student_row: pd.Series) -> int:
    """
    Calculate remaining credits for a student to complete their degree.
    
    Args:
        student_row: Row from progress_df containing student information
        
    Returns:
        Number of credits remaining (integer)
    """
    try:
        cr_remaining = float(student_row.get("# Remaining", 0) or 0)
        return int(cr_remaining)
    except Exception as e:
        log_error("Error calculating remaining credits", e)
        return 999


def get_student_eligibility_status(
    student_row: pd.Series,
    course_code: str,
    courses_df: pd.DataFrame,
    advised_courses: List[str] = None
) -> Tuple[str, str, List[str]]:
    """
    Get detailed eligibility status for a student and course.
    
    Returns:
        (status, justification, missing_prerequisites)
        - status: 'Eligible', 'Not Eligible', 'Completed', 'Registered'
        - justification: Human-readable explanation
        - missing_prerequisites: List of course codes that are missing (if not eligible)
    """
    if advised_courses is None:
        advised_courses = []
    
    status, justification = check_eligibility(student_row, course_code, advised_courses or [], courses_df)
    
    missing_prereqs = []
    
    if status == "Not Eligible":
        course_row = courses_df.loc[courses_df["Course Code"] == course_code]
        if not course_row.empty:
            course_info = course_row.iloc[0]
            
            for req_col in ["Prerequisite", "Concurrent", "Corequisite"]:
                req_val = course_info.get(req_col, "")
                
                parsed_reqs = parse_requirements(req_val)
                
                for req_course in parsed_reqs:
                    if req_course and not req_course.lower().startswith("standing"):
                        if not check_course_completed(student_row, req_course) and not check_course_registered(student_row, req_course):
                            missing_prereqs.append(req_course)
    
    return status, justification, missing_prereqs


def simulate_course_offerings(
    progress_df: pd.DataFrame,
    offered_courses: List[str],
    courses_df: pd.DataFrame
) -> pd.DataFrame:
    """
    Simulate student progress assuming they take all eligible offered courses.
    
    Args:
        progress_df: Original student progress data
        offered_courses: List of course codes being offered
        courses_df: Course catalog data
        
    Returns:
        Modified progress_df with simulated completions
    """
    if not offered_courses:
        return progress_df.copy()
    
    simulated_df = progress_df.copy()
    
    for idx, student_row in simulated_df.iterrows():
        for course_code in offered_courses:
            status, _, _ = get_student_eligibility_status(
                student_row, course_code, courses_df, []
            )
            
            if status == "Eligible":
                if pd.notna(student_row.get("Completed Courses", "")):
                    completed_str = str(student_row["Completed Courses"])
                    completed_set = set(c.strip() for c in completed_str.split(",") if c.strip())
                    
                    if course_code not in completed_set:
                        simulated_df.at[idx, "Completed Courses"] = f"{completed_str}, {course_code}"
                else:
                    simulated_df.at[idx, "Completed Courses"] = course_code
    
    return simulated_df


def analyze_course_eligibility_across_students(
    courses_df: pd.DataFrame,
    progress_df: pd.DataFrame,
    offered_courses: List[str] = None
) -> pd.DataFrame:
    """
    Generate a comprehensive eligibility analysis for all courses across all students.
    
    Args:
        courses_df: Course catalog
        progress_df: Student progress data
        offered_courses: List of courses selected to be offered (for simulation)
    
    Returns:
        DataFrame with columns:
        - Course Code
        - Course Title
        - Credits
        - Currently Eligible (count)
        - Currently Eligible (students - list of IDs)
        - One Course Away (count)
        - One Course Away (details - dict mapping student_id to missing prereq)
        - Two+ Courses Away (count)
        - Two+ Courses Away (details)
        - Priority Score (weighted by graduation proximity)
        - Impact Score (total students who could benefit)
        - Recommendation
    """
    log_info("Starting course eligibility analysis across all students")
    
    if offered_courses is None:
        offered_courses = []
    
    working_progress_df = simulate_course_offerings(progress_df, offered_courses, courses_df)
    
    results = []
    
    for _, course_row in courses_df.iterrows():
        course_code = str(course_row["Course Code"])
        course_title = str(course_row.get("Course Title", ""))
        credits = course_row.get("Credits", 0)
        
        eligible_students = []
        eligible_students_close_to_grad = []
        one_away_students = {}
        two_away_students = {}
        
        for _, student_row in working_progress_df.iterrows():
            student_id = student_row["ID"]
            student_name = student_row.get("NAME", "Unknown")
            remaining_credits = calculate_student_remaining_credits(student_row)
            
            status, _, missing_prereqs = get_student_eligibility_status(
                student_row, course_code, courses_df, []
            )
            
            if status == "Eligible":
                eligible_students.append({
                    "id": student_id,
                    "name": student_name,
                    "remaining_credits": remaining_credits
                })
                if remaining_credits <= 15:
                    eligible_students_close_to_grad.append(student_id)
            
            elif status == "Not Eligible":
                num_missing = len(set(missing_prereqs))
                
                if num_missing == 1:
                    one_away_students[student_id] = {
                        "name": student_name,
                        "missing_prereq": missing_prereqs[0],
                        "remaining_credits": remaining_credits
                    }
                elif num_missing >= 2:
                    two_away_students[student_id] = {
                        "name": student_name,
                        "missing_prereqs": list(set(missing_prereqs)),
                        "remaining_credits": remaining_credits
                    }
        
        num_eligible = len(eligible_students)
        num_one_away = len(one_away_students)
        num_two_away = len(two_away_students)
        
        priority_score = calculate_priority_score(
            eligible_students, one_away_students, two_away_students
        )
        
        impact_score = num_eligible + num_one_away * 0.7 + num_two_away * 0.3
        
        recommendation = generate_course_recommendation(
            course_code, course_title, num_eligible, num_one_away, num_two_away,
            eligible_students_close_to_grad, one_away_students
        )
        
        results.append({
            "Course Code": course_code,
            "Course Title": course_title,
            "Credits": credits,
            "Currently Eligible": num_eligible,
            "Eligible Students": eligible_students,
            "One Course Away": num_one_away,
            "One Away Details": one_away_students,
            "Two+ Courses Away": num_two_away,
            "Two+ Away Details": two_away_students,
            "Priority Score": round(priority_score, 2),
            "Impact Score": round(impact_score, 2),
            "Recommendation": recommendation
        })
    
    df_result = pd.DataFrame(results)
    log_info(f"Course eligibility analysis complete: {len(df_result)} courses analyzed")
    return df_result


def calculate_priority_score(
    eligible_students: List[Dict],
    one_away_students: Dict,
    two_away_students: Dict
) -> float:
    """
    Calculate priority score for offering a course.
    
    Higher scores indicate courses that should be prioritized for offering.
    Weights students closer to graduation more heavily.
    
    Args:
        eligible_students: List of dicts with student info including remaining_credits
        one_away_students: Dict of students one prerequisite away
        two_away_students: Dict of students two+ prerequisites away
        
    Returns:
        Priority score (float)
    """
    score = 0.0
    
    for student in eligible_students:
        remaining = student.get("remaining_credits", 999)
        if remaining <= 9:
            weight = 5.0
        elif remaining <= 15:
            weight = 3.0
        elif remaining <= 30:
            weight = 2.0
        else:
            weight = 1.0
        score += weight
    
    for student_id, info in one_away_students.items():
        remaining = info.get("remaining_credits", 999)
        if remaining <= 9:
            weight = 3.0
        elif remaining <= 15:
            weight = 2.0
        elif remaining <= 30:
            weight = 1.5
        else:
            weight = 0.7
        score += weight
    
    for student_id, info in two_away_students.items():
        remaining = info.get("remaining_credits", 999)
        if remaining <= 15:
            weight = 1.0
        else:
            weight = 0.3
        score += weight
    
    return score


def generate_course_recommendation(
    course_code: str,
    course_title: str,
    num_eligible: int,
    num_one_away: int,
    num_two_away: int,
    eligible_close_to_grad: List,
    one_away_details: Dict
) -> str:
    """
    Generate a smart recommendation for whether to offer a course.
    
    Returns:
        Human-readable recommendation string
    """
    if num_eligible == 0 and num_one_away == 0:
        return "⚪ Low Priority - No students currently eligible or close to eligible"
    
    close_count = len(eligible_close_to_grad)
    
    if close_count >= 3:
        return f"🔴 Critical - {num_eligible} eligible ({close_count} near graduation)"
    
    if num_eligible >= 5:
        return f"🟠 High Priority - {num_eligible} students eligible"
    
    if num_one_away >= 5:
        prereqs = set()
        for info in one_away_details.values():
            prereqs.add(info.get("missing_prereq", ""))
        prereqs_str = ", ".join(sorted(prereqs)[:3])
        return f"🟡 Medium Priority - {num_one_away} students one course away (need: {prereqs_str})"
    
    if num_eligible > 0:
        return f"🟢 Standard - {num_eligible} students eligible"
    
    return "⚪ Low Priority - Limited student demand"


def analyze_prerequisite_chains(
    courses_df: pd.DataFrame,
    progress_df: pd.DataFrame
) -> Dict[str, Any]:
    """
    Analyze prerequisite chains to identify bottleneck courses and critical paths.
    
    Returns:
        Dict containing:
        - bottleneck_courses: Courses that unlock many downstream courses
        - critical_path_courses: Courses needed to prevent student delays
        - prerequisite_graph: Mapping of courses to their prerequisites
    """
    log_info("Analyzing prerequisite chains")
    
    prereq_graph = {}
    downstream_count = defaultdict(int)
    
    for _, course_row in courses_df.iterrows():
        course_code = course_row["Course Code"]
        prereqs = []
        
        for req_col in ["Prerequisite", "Concurrent", "Corequisite"]:
            req_val = course_row.get(req_col, "")
            
            parsed_reqs = parse_requirements(req_val)
            
            for req_course in parsed_reqs:
                if req_course and not req_course.lower().startswith("standing"):
                    prereqs.append(req_course)
                    downstream_count[req_course] += 1
        
        prereq_graph[course_code] = prereqs
    
    bottleneck_courses = sorted(
        [(course, count) for course, count in downstream_count.items()],
        key=lambda x: x[1],
        reverse=True
    )[:10]
    
    critical_courses = []
    critical_course_students = defaultdict(list)
    
    for _, student_row in progress_df.iterrows():
        remaining = calculate_student_remaining_credits(student_row)
        student_id = student_row["ID"]
        student_name = student_row.get("NAME", "Unknown")
        
        for course_code in prereq_graph:
            status, _, missing = get_student_eligibility_status(
                student_row, course_code, courses_df, []
            )
            if status == "Not Eligible" and missing and len(missing) > 0:
                for prereq in missing:
                    if prereq and not check_course_completed(student_row, prereq):
                        critical_courses.append((prereq, student_id, course_code))
                        critical_course_students[prereq].append({
                            "id": student_id,
                            "name": student_name,
                            "remaining_credits": remaining
                        })
    
    critical_course_counts = defaultdict(int)
    for course, _, _ in critical_courses:
        critical_course_counts[course] += 1
    
    critical_path_courses = sorted(
        [(course, count) for course, count in critical_course_counts.items()],
        key=lambda x: x[1],
        reverse=True
    )[:10]
    
    critical_path_courses_detail = sorted(
        [(course, students) for course, students in critical_course_students.items()],
        key=lambda x: len(x[1]),
        reverse=True
    )
    
    return {
        "bottleneck_courses": bottleneck_courses,
        "critical_path_courses": critical_path_courses,
        "critical_path_courses_detail": critical_path_courses_detail,
        "prerequisite_graph": prereq_graph
    }
