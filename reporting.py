# reporting.py

import pandas as pd
from io import BytesIO
from openpyxl import load_workbook
from openpyxl.styles import PatternFill, Font, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from typing import List

def _auto_fit(ws, header_row: int = 1, wrap_cols: List[int] = None):
    """Auto-fit columns based on content length and optionally wrap text."""
    wrap_cols = wrap_cols or []
    for col_idx in range(1, ws.max_column + 1):
        max_len = 0
        for row in range(1, ws.max_row + 1):
            v = ws.cell(row=row, column=col_idx).value
            if v is None:
                continue
            try:
                vlen = len(str(v))
                if vlen > max_len:
                    max_len = vlen
            except Exception:
                pass
        width = min(max(10, max_len + 2), 60)
        ws.column_dimensions[get_column_letter(col_idx)].width = width

    for col_idx in wrap_cols:
        for r in range(header_row + 1, ws.max_row + 1):
            ws.cell(row=r, column=col_idx).alignment = Alignment(wrap_text=True, vertical="top")

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
    and color-codes the 'Action' column (Advised/Optional). Also auto-fits columns.
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

    # Header row formatting (assumes headers now start at row 10)
    header_row = 10
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

    # Conditional fill for Action column (only Advised / Optional in export now)
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

    # Auto-fit columns; wrap Justification if present
    # Find 'Justification' col to wrap
    just_col = None
    for idx, cell in enumerate(ws[header_row], start=1):
        if str(cell.value).strip().lower() == "justification":
            just_col = idx
            break
    _auto_fit(ws, header_row=header_row, wrap_cols=[just_col] if just_col else [])

    output.seek(0)
    wb.save(output)
    output.seek(0)

def add_summary_sheet(writer, full_report: pd.DataFrame, course_cols: List[str]) -> None:
    """
    Add a 'Summary' sheet to a cohort report.
    Counts per-status for each course among the provided course columns.
    Recognized codes: c, r, a, o, na, ne
    """
    summary_rows = []
    for c in course_cols:
        counts = full_report[c].value_counts(dropna=False).to_dict()
        summary_rows.append({
            "Course": c,
            "Completed (c)": int(counts.get("c", 0)),
            "Registered (r)": int(counts.get("r", 0)),
            "Advised (a)": int(counts.get("a", 0)),
            "Optional (o)": int(counts.get("o", 0)),
            "Eligible not chosen (na)": int(counts.get("na", 0)),
            "Not Eligible (ne)": int(counts.get("ne", 0)),
        })
    pd.DataFrame(summary_rows).to_excel(writer, index=False, sheet_name="Summary")

def apply_full_report_formatting(output: BytesIO, sheet_name: str, course_cols: List[str]) -> None:
    """
    Color the compact codes (c,r,a,o,na,ne) in the 'Full Report' sheet.
    """
    output.seek(0)
    wb = load_workbook(output)
    ws = wb[sheet_name]

    # find first row with headers
    header_row = 1
    # color map
    code_to_fill = {
        "c": "C6E0B4",  # green
        "r": "BDD7EE",  # blue
        "a": "FFF2CC",  # yellow
        "o": "FFE699",  # orange
        "na":"E1F0FF",  # light blue-tint
        "ne":"F8CECC",  # red
    }

    # header styling
    header_fill = PatternFill("solid", fgColor="4F81BD")
    header_font = Font(bold=True, color="FFFFFF")
    header_align = Alignment(horizontal="center", vertical="center")
    for cell in ws[header_row]:
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = header_align
    thin = Side(style="thin", color="CCCCCC")
    for r in range(header_row, ws.max_row + 1):
        for c in range(1, ws.max_column + 1):
            ws.cell(row=r, column=c).border = Border(left=thin, right=thin, top=thin, bottom=thin)

    # color code the selected course cols
    headers = [str(cell.value).strip() for cell in ws[header_row]]
    col_indexes = [headers.index(c) + 1 for c in course_cols if c in headers]
    for col in col_indexes:
        for r in range(header_row + 1, ws.max_row + 1):
            val = str(ws.cell(row=r, column=col).value or "").lower()
            fg = code_to_fill.get(val)
            if fg:
                ws.cell(row=r, column=col).fill = PatternFill("solid", fgColor=fg)

    _auto_fit(ws, header_row=header_row)
    output.seek(0)
    wb.save(output)
    output.seek(0)

def apply_individual_compact_formatting(output: BytesIO, sheet_name: str, course_cols: List[str]) -> None:
    """
    Color the compact codes (c,r,a,o,na,ne) for the single-student exported grid.
    """
    output.seek(0)
    wb = load_workbook(output)
    ws = wb[sheet_name]

    header_row = 1
    header_fill = PatternFill("solid", fgColor="4F81BD")
    header_font = Font(bold=True, color="FFFFFF")
    header_align = Alignment(horizontal="center", vertical="center")
    for cell in ws[header_row]:
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = header_align
    thin = Side(style="thin", color="CCCCCC")
    for r in range(header_row, ws.max_row + 1):
        for c in range(1, ws.max_column + 1):
            ws.cell(row=r, column=c).border = Border(left=thin, right=thin, top=thin, bottom=thin)

    code_to_fill = {
        "c": "C6E0B4",
        "r": "BDD7EE",
        "a": "FFF2CC",
        "o": "FFE699",
        "na":"E1F0FF",
        "ne":"F8CECC",
    }
    headers = [str(cell.value).strip() for cell in ws[header_row]]
    col_indexes = [headers.index(c) + 1 for c in course_cols if c in headers]
    for col in col_indexes:
        for r in range(header_row + 1, ws.max_row + 1):
            val = str(ws.cell(row=r, column=col).value or "").lower()
            fg = code_to_fill.get(val)
            if fg:
                ws.cell(row=r, column=col).fill = PatternFill("solid", fgColor=fg)

    _auto_fit(ws, header_row=header_row)
    output.seek(0)
    wb.save(output)
    output.seek(0)
