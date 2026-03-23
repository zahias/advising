"""Ported from course_mapping/tests/test_cell_color.py"""
import pytest
from app.services.progress_service import COMPLETION_COLOR_MAP, cell_color


@pytest.mark.parametrize("value,expected", [
    ("c",  f"background-color: {COMPLETION_COLOR_MAP['c']}"),
    ("cr", f"background-color: {COMPLETION_COLOR_MAP['cr']}"),
    ("nc", f"background-color: {COMPLETION_COLOR_MAP['nc']}"),
    (" C ", f"background-color: {COMPLETION_COLOR_MAP['c']}"),
    ("CR | 3", f"background-color: {COMPLETION_COLOR_MAP['cr']}"),
])
def test_cell_color_collapsed_and_full_values(value, expected):
    assert cell_color(value) == expected


def test_cell_color_non_string_returns_blank():
    assert cell_color(None) == ""
