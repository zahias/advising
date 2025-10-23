# reporting.py

from io import BytesIO
from typing import List, Optional

import pandas as pd
from openpyxl import load_workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter


# ============================================================
# Shared helpers
# ============================================================

def _thin_border() -> Border:
    return Border(
        left=Side(style="thin", color="CCCCCC"),
        right=Side(style="thin", color="CCCCCC"),
        top=Side(style="thin", color="CCCCCC"),
        bottom=Side(style="thin", color="CCCCCC"),
    )

def _style_header_row(ws, row_idx: int) -> None:
    """Style the header row with a blue background and white bold text."""
    hdr_fill = PatternFill("solid", fgColor="4F81BD")
    hdr_font = Font(bold=True, color="FFFFFF")
    hdr_align = Alignment(horizontal="center", vertical="center")
    for cell in ws[row_idx]:
        cell.fill = hdr_fill
        cell.font = hdr_font
        cell.alignment = hdr_align

def _auto_filter(ws, header_row: int) -> None:
    ws.auto_filter.ref = f"A{header_row}:{get_column_letter(ws.max_column)}{ws.max_row}"

def _apply_borders(ws, start_row: int) -> None:
    b = _thin_border()
    for r in range(start_row, ws.max_row + 1):
        for c in range(1, ws.max_column + 1):
            ws.cell(row=r, column=c).border = b

def _wrap_and_top_align(ws, col_idx: int, header_row: int) -> None:
    for r in range(header_row + 1, ws.max_row + 1):
        ws.cell(row=r, column=col_idx).alignment = Alignment(wrap_text=True, vertical="top")

def _find_header_row(ws) -> Optional[int]:
    """
    Try to find the table header by scanning for a row that contains 'Course Code'.
    Fall back to row 10 (common after we insert 8 rows above).
    """
    for r in range(1, min(25, ws.max_row) + 1):
        vals = [str(c.value or "").strip().lower() for c in ws[r]]
        if "course code" in vals:
            return r
    return 10 if ws.max_row >= 10 else 1


# ============================================================
# Single-student advising sheet (Eligibility → Download)
# ============================================================

def apply_excel_formatting(
    output: BytesIO,
    student_name: str,
    student_id: int | str,
    credits_completed: int,
    standing: str,
    note: str,
    advised_credits: int,
    optional_credits: int,
) -> None:
    """
    Enhance the single-student advising workbook:
      - Insert a header block with student details
      - Style header row, freeze panes
      - Add AutoFilter and borders
      - Wrap 'Justification', set readable widths
      - Color 'Action' for Advised / Optional
    """
    output.seek(0)
    wb = load_workbook(output)
    ws = wb.active  # sheet name is "Advising"

    # Insert info block above the table
    ws.insert_rows(1, amount=8)
    ws["A1"] = "Student Advising Report"
    ws["A3"] = "Name:"; ws["B3"] = student_name
    ws["A4"] = "ID:"; ws["B4"] = student_id
    ws["A5"] = "Credits Completed:"; ws["B5"] = credits_completed
    ws["A6"] = "Standing:"; ws["B6"] = standing
    ws["A7"] = "Advisor Note:"; ws["B7"] = note
    ws["A8"] = "Credits (Advised / Optional):"; ws["B8"] = f"{advised_credits} / {optional_credits}"
    ws["A1"].font = Font(size=14, bold=True)

    header_row = _find_header_row(ws)
    _style_header_row(ws, header_row)
    ws.freeze_panes = f"A{header_row + 1}"
    _auto_filter(ws, header_row)
    _apply_borders(ws, header_row)

    # Column widths + wrapping for Justification
    header_map = {str(ws.cell(row=header_row, column=c).value or ""): c for c in range(1, ws.max_column + 1)}

    def _w(name: str, width: float):
        col = header_map.get(name)
        if col:
            ws.column_dimensions[get_column_letter(col)].width = width

    _w("Course Code", 18)
    _w("Action", 16)
    _w("Eligibility Status", 28)
    _w("Justification", 80)

    jcol = header_map.get("Justification")
    if jcol:
        _wrap_and_top_align(ws, jcol, header_row)

    # Color ONLY Advised / Optional in Action
    action_col = header_map.get("Action")
    if action_col:
        fills = {
            "Advised": PatternFill("solid", fgColor="FFF2CC"),
            "Optional": PatternFill("solid", fgColor="FFE699"),
        }
        for r in range(header_row + 1, ws.max_row + 1):
            v = str(ws.cell(row=r, column=action_col).value or "")
            if v in fills:
                ws.cell(row=r, column=action_col).fill = fills[v]

    output.seek(0)
    wb.save(output)
    output.seek(0)


# ============================================================
# Full cohort (Full Student View exports)
# ============================================================

# Code -> fill color for status grid in cohort exports (includes 'o' for Optional)
_CODE_FILL = {
    "c":  "C6E0B4",  # Completed
    "r":  "BDD7EE",  # Registered
    "a":  "FFF2CC",  # Advised
    "o":  "FFE699",  # Optional
    "na": "E1F0FF",  # Eligible not chosen
    "ne": "F8CECC",  # Not Eligible
}

def _apply_code_grid_colors(ws, course_cols: List[str], header_row: int = 1) -> None:
    """Color cells that contain status codes (c/r/a/o/na/ne) for the given course columns."""
    header = [str(c.value or "") for c in ws[header_row]]
    name_to_idx = {name: i + 1 for i, name in enumerate(header)}
    targets = [name_to_idx[c] for c in course_cols if c in name_to_idx]
    for r in range(header_row + 1, ws.max_row + 1):
        for c in targets:
            val = str(ws.cell(row=r, column=c).value or "").strip().lower()
            if val in _CODE_FILL:
                ws.cell(row=r, column=c).fill = PatternFill("solid", fgColor=_CODE_FILL[val])

def apply_full_report_formatting(*, output: BytesIO, sheet_name: str, course_cols: List[str]) -> None:
    """
    Format the 'Full Report' sheet used by the All Students export:
      - Style first row as header
      - Freeze panes below header
      - Borders
      - Color code c/r/a/o/na/ne in the provided course columns
      - AutoFilter
    """
    output.seek(0)
    wb = load_workbook(output)
    ws = wb[sheet_name]

    header_row = 1
    _style_header_row(ws, header_row)
    ws.freeze_panes = f"A{header_row + 1}"
    _apply_borders(ws, header_row)
    _apply_code_grid_colors(ws, course_cols, header_row)
    _auto_filter(ws, header_row)

    output.seek(0)
    wb.save(output)
    output.seek(0)

def apply_individual_compact_formatting(*, output: BytesIO, sheet_name: str, course_cols: List[str]) -> None:
    """
    Format the 'Student' sheet used by the Individual Student compact export:
      - Style first row as header
      - Freeze panes below header
      - Borders
      - Color code c/r/a/o/na/ne in the provided course columns
      - AutoFilter
    """
    output.seek(0)
    wb = load_workbook(output)
    ws = wb[sheet_name]

    header_row = 1
    _style_header_row(ws, header_row)
    ws.freeze_panes = f"A{header_row + 1}"
    _apply_borders(ws, header_row)
    _apply_code_grid_colors(ws, course_cols, header_row)
    _auto_filter(ws, header_row)

    output.seek(0)
    wb.save(output)
    output.seek(0)


# ============================================================
# Summary sheet for cohort export
# ============================================================

def add_summary_sheet(writer, full_report: pd.DataFrame, course_cols: List[str]) -> None:
    """
    Add a 'Summary' sheet to a cohort report.
    Counts per-status for each course among the provided course columns.
    Recognized codes: c, r, a, o, na, ne
    """
    summary_rows = []
    for c in course_cols:
        counts = full_report[c].value_counts(dropna=False).to_dict() if c in full_report.columns else {}
        summary_rows.append({
            "Course": c,
            "Completed (c)": int(counts.get("c", 0)),
            "Registered (r)": int(counts.get("r", 0)),
            "Advised (a)": int(counts.get("a", 0)),
            "Optional (o)": int(counts.get("o", 0)),   # NEW
            "Eligible not chosen (na)": int(counts.get("na", 0)),
            "Not Eligible (ne)": int(counts.get("ne", 0)),
        })
    pd.DataFrame(summary_rows).to_excel(writer, index=False, sheet_name="Summary")
