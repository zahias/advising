# reporting.py

import pandas as pd
from io import BytesIO
from openpyxl import load_workbook
from openpyxl.styles import PatternFill, Font, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from typing import List, Optional


def _find_header_row(ws) -> Optional[int]:
    """
    Find the header row by scanning for a row containing 'Course Code' and 'Action'.
    Falls back to row 10 if not found.
    """
    for r in range(1, min(25, ws.max_row) + 1):
        vals = [str(c.value or "").strip().lower() for c in ws[r]]
        if "course code" in vals and "action" in vals:
            return r
    return 10 if ws.max_row >= 10 else 1


def _apply_header_style(ws, header_row: int) -> None:
    hdr_fill = PatternFill("solid", fgColor="4F81BD")
    hdr_font = Font(bold=True, color="FFFFFF")
    hdr_align = Alignment(horizontal="center", vertical="center")
    for cell in ws[header_row]:
        cell.fill = hdr_fill
        cell.font = hdr_font
        cell.alignment = hdr_align


def _add_borders(ws, start_row: int) -> None:
    thin = Side(style="thin", color="CCCCCC")
    max_row = ws.max_row
    max_col = ws.max_column
    for r in range(start_row, max_row + 1):
        for c in range(1, max_col + 1):
            ws.cell(row=r, column=c).border = Border(left=thin, right=thin, top=thin, bottom=thin)


def _set_column_widths(ws, header_row: int) -> None:
    header_map = {str(ws.cell(row=header_row, column=c).value or ""): c for c in range(1, ws.max_column + 1)}
    def _w(name: str, width: float):
        c = header_map.get(name)
        if c:
            ws.column_dimensions[get_column_letter(c)].width = width

    _w("Course Code", 18)
    _w("Action", 16)
    _w("Eligibility Status", 28)
    _w("Justification", 80)

    # Wrap Justification
    j = header_map.get("Justification")
    if j:
        for r in range(header_row + 1, ws.max_row + 1):
            ws.cell(row=r, column=j).alignment = Alignment(wrap_text=True, vertical="top")


def _color_action_cells(ws, header_row: int) -> None:
    """
    Color only Advised / Optional in Action column.
    """
    action_col = None
    for idx, cell in enumerate(ws[header_row], start=1):
        if str(cell.value).strip().lower() == "action":
            action_col = idx
            break
    if not action_col:
        return
    fills = {
        "Advised": PatternFill("solid", fgColor="FFF2CC"),
        "Optional": PatternFill("solid", fgColor="FFE699"),
    }
    for r in range(header_row + 1, ws.max_row + 1):
        val = str(ws.cell(row=r, column=action_col).value or "")
        fill = fills.get(val)
        if fill:
            ws.cell(row=r, column=action_col).fill = fill


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
    Enhances the single-student advising report.
    Adds a header block (student info), formats header, freezes panes,
    adds AutoFilter, wraps justification, sets widths, and colors Action (Advised/Optional).
    """
    output.seek(0)
    wb = load_workbook(output)
    ws = wb.active  # sheet name: "Advising"

    # Insert student info block
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
    _apply_header_style(ws, header_row)
    ws.freeze_panes = f"A{header_row+1}"
    _add_borders(ws, header_row)
    _color_action_cells(ws, header_row)

    from openpyxl.utils import get_column_letter as _gcl
    ws.auto_filter.ref = f"A{header_row}:{_gcl(ws.max_column)}{ws.max_row}"

    _set_column_widths(ws, header_row)

    output.seek(0)
    wb.save(output)
    output.seek(0)


def add_summary_sheet(writer, full_report: pd.DataFrame, course_cols: List[str]) -> None:
    """
    Add a 'Summary' sheet to a cohort report.
    Counts per-status for each course among the provided course columns.
    Recognized codes: c, r, a, na, ne
    """
    summary_rows = []
    for c in course_cols:
        counts = full_report[c].value_counts(dropna=False).to_dict() if c in full_report.columns else {}
        summary_rows.append({
            "Course": c,
            "Completed (c)": int(counts.get("c", 0)),
            "Registered (r)": int(counts.get("r", 0)),
            "Advised (a)": int(counts.get("a", 0)),
            "Eligible not chosen (na)": int(counts.get("na", 0)),
            "Not Eligible (ne)": int(counts.get("ne", 0)),
        })
    pd.DataFrame(summary_rows).to_excel(writer, index=False, sheet_name="Summary")
