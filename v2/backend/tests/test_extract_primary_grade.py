"""Ported from course_mapping/tests/test_extract_primary_grade.py"""
import pytest
from app.services.progress_service import extract_primary_grade_from_full_value


@pytest.mark.parametrize("value,expected", [
    ("F | 0, CR | 3", "CR | 3"),
    ("B- | 0, A | 3", "A | 3"),
    ("R | FAIL, P | PASS", "P | PASS"),
])
def test_extract_primary_grade(value, expected):
    assert extract_primary_grade_from_full_value(value) == expected
