# reporting.py

import pandas as pd
from io import BytesIO
from openpyxl import load_workbook
from openpyxl.styles import PatternFill, Font, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from typing import List


def _set_column_widths(ws, header_row: int, max_row: int) -> None:
    """Basic, readable widths + wrap for Justification."""
    widths = {}
    for col_idx, cell in enumerate(ws[header_row], start=1):
        header = str(cell.value or "")
        base = max(12, len(header) + 2)
        widths[col_idx] = base

    # Sample a few rows to expand widths
    sample_rows = range(header_row + 1, min(header_row + 20, max_row + 1))
    for r in sample_rows:
        for c in range(1, ws.max_column + 1):
            val = ws.cell(row=r, column=c).value
            if val is None:
                continue
            s = str(val)
            widths[c] = max(widths.get(c, 12), min(80, len(s) + 2))

    # Gentle presets
    header_map = {str(ws.cell(row=header_row, column=c).value or "").lower(): c for c in range(1, ws.max_column + 1)}
    def _set(col, w):
        if isinstance(col, int):
            idx = col
        else:
            idx = header_map.get(col.lower())
            if idx is None:
                return
        ws.column_dimensions[get_column_letter(idx)].width = w

    _set("Course Code", 16)
    _set("Action", 16)
    _set("Eligibility Status", 26)
    _set("Justification", 80)

    # Wrap and top-align Justification
    j_idx = header_map.get("justification")
    if j_idx:
        for r in range(header_row + 1, max_row + 1):
            cell = ws.cell(row=r, column=j_idx)
            cell.alignment = Alignment(wrap_text=True, vertical="top")


def apply_excel_formatting(
    output: BytesIO,
    student_name: str,
    student_id: int,
    credits_completed: int,
    standing: str,
    note: str,
    advised_credits: int,
    optional_credits: int,
) -> None:
    """
    Enhances the single-student advising report workbook contained in `output`.
    Adds a header block (student info), formats the header row, freezes panes,
    and color-codes the 'Action' column (Advised, Optional).
    """
    output.seek(0)
    wb = load_workbook(output)
    ws = wb.active

    # Insert student info block
    ws.insert_rows(1, amount=8)
    ws["A1"] = "Student Advising Report"
    ws["A3"] = "Name:"; ws["B3"] = student_name
    ws["A4"] = "ID:"; ws["B4"] = student_id
    ws["A5"] = "Credits Completed:"; ws["B5"] = credits_completed
    ws["A6"] = "Standing:"; ws["B6"] = standing
    ws["A7"] = "Advisor Note:"; ws["B7"] = note
    ws["A8"] = "Credits (Advised / Optional):"; ws["B8"] = f"{advised_credits} / {optional_credits}"

    title_font = Font(size=14, bold=True)
    ws["A1"].font = title_font

    # Header row formatting
    header_row = 10  # after inserting 8 rows
    ws.freeze_panes = f"A{header_row+1}"
    header_fill = PatternFill("solid", fgColor="4F81BD")
    header_font = Font(bold=True, color="FFFFFF")
    header_align = Alignment(horizontal="center", vertical="center")

    for cell in ws[header_row]:
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = header_align

    # Borders for data region
    thin = Side(style="thin", color="CCCCCC")
    max_row = ws.max_row
    max_col = ws.max_column
    for r in range(header_row, max_row + 1):
        for c in range(1, max_col + 1):
            ws.cell(row=r, column=c).border = Border(left=thin, right=thin, top=thin, bottom=thin)

    # AutoFilter on data
    ws.auto_filter.ref = f"A{header_row}:{get_column_letter(max_col)}{max_row}"

    # Conditional fill for Action column
    action_col_idx = None
    for idx, cell in enumerate(ws[header_row], start=1):
        if str(cell.value).strip().lower() == "action":
            action_col_idx = idx
            break
    if action_col_idx:
        fills = {
            "Advised": PatternFill("solid", fgColor="FFF2CC"),
            "Optional": PatternFill("solid", fgColor="FFE699"),
        }
        for r in range(header_row + 1, max_row + 1):
            val = str(ws.cell(row=r, column=action_col_idx).value or "")
            fill = fills.get(val)
            if fill:
                ws.cell(row=r, column=action_col_idx).fill = fill

    # Column widths + wrapping
    _set_column_widths(ws, header_row, max_row)

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
        counts = full_report[c].value_counts(dropna=False).to_dict()
        summary_rows.append({
            "Course": c,
            "Completed (c)": int(counts.get("c", 0)),
            "Registered (r)": int(counts.get("r", 0)),
            "Advised (a)": int(counts.get("a", 0)),
            "Eligible not chosen (na)": int(counts.get("na", 0)),
            "Not Eligible (ne)": int(counts.get("ne", 0)),
        })
    pd.DataFrame(summary_rows).to_excel(writer, index=False, sheet_name="Summary")
