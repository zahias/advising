"""Ported from course_mapping/tests/test_collapse_pass_fail.py"""
from app.services.progress_service import collapse_pass_fail_value


def test_marks_completed_credit_courses():
    assert collapse_pass_fail_value("A | 3") == "c"


def test_marks_zero_credit_as_not_completed():
    assert collapse_pass_fail_value("B | 0") == "nc"


def test_marks_zero_credit_fail_token():
    assert collapse_pass_fail_value("C | FAIL") == "nc"


def test_marks_pass_token():
    assert collapse_pass_fail_value("D | PASS") == "c"


def test_marks_current_registration():
    assert collapse_pass_fail_value("CR | PASS") == "cr"


def test_marks_nr_shorthand():
    assert collapse_pass_fail_value("NR") == "nc"


def test_leaves_unexpected_formats():
    assert collapse_pass_fail_value("In Progress") == "In Progress"


def test_passthrough_non_string():
    assert collapse_pass_fail_value(None) is None
