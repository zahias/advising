"""Ported from course_mapping/tests/test_process_progress_report.py"""
import pandas as pd
import pytest

from app.services.progress_service import process_progress_report


@pytest.fixture
def base_courses():
    target_courses = {"REQ101": 3}
    intensive_courses = {"INT101": 0, "INT202": 0}
    target_rules = {"REQ101": [{"Credits": 3, "PassingGrades": "A,B", "FromOrd": 0, "ToOrd": 99}]}
    intensive_rules = {
        "INT101": [{"Credits": 0, "PassingGrades": "P", "FromOrd": 0, "ToOrd": 99}],
        "INT202": [{"Credits": 0, "PassingGrades": "P", "FromOrd": 0, "ToOrd": 99}],
    }
    return target_courses, intensive_courses, target_rules, intensive_rules


def test_intensive_includes_students_without_intensive_rows(base_courses):
    target_courses, intensive_courses, target_rules, intensive_rules = base_courses
    df = pd.DataFrame([{
        "ID": "123", "NAME": "Alice Example",
        "Course": "REQ101", "Grade": "A", "Year": "2023", "Semester": "Fall",
    }])
    _, int_df, _, _ = process_progress_report(
        df, target_courses, intensive_courses, target_rules, intensive_rules,
        assignment_types=["S.C.E", "F.E.C"],
    )
    assert list(int_df.columns) == ["ID", "NAME", "INT101", "INT202"]
    assert int_df.loc[0, "INT101"] == "NR"
    assert int_df.loc[0, "INT202"] == "NR"


def test_required_includes_students_without_required_rows(base_courses):
    target_courses, intensive_courses, target_rules, intensive_rules = base_courses
    # Use single-element intensive_courses to simplify fixture
    target_c = {"REQ101": 3}
    int_c = {"INT101": 0}
    t_rules = {"REQ101": [{"Credits": 3, "PassingGrades": "A,B", "FromOrd": 0, "ToOrd": 99}]}
    i_rules = {"INT101": [{"Credits": 0, "PassingGrades": "P", "FromOrd": 0, "ToOrd": 99}]}
    df = pd.DataFrame([
        {"ID": "123", "NAME": "Alice Example", "Course": "INT101", "Grade": "P", "Year": "2023", "Semester": "Fall"},
        {"ID": "456", "NAME": "Bob Example", "Course": "REQ101", "Grade": "A", "Year": "2023", "Semester": "Fall"},
    ])
    req_df, _, _, _ = process_progress_report(
        df, target_c, int_c, t_rules, i_rules, assignment_types=["S.C.E", "F.E.C"],
    )
    assert list(req_df.columns) == ["ID", "NAME", "REQ101"]
    alice_row = req_df[req_df["ID"] == "123"].iloc[0]
    assert alice_row["REQ101"] == "NR"
