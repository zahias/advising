# reporting.py

from io import BytesIO
from typing import List

import pandas as pd
from openpyxl import load_workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side

def apply_excel_formatting(
    output: BytesIO,
    student_name: str,
    student_id: int,
    credits_completed: int,
    standing: str,
    note: str,
    advised_credits: int,
    optional_credits: int,
) -> BytesIO:
    """
    Format single-student report and color-code Action (includes Registered).
    """
    output.seek(0)
    wb = load_workbook(output)
    ws = wb.active

    # Header block
    ws.insert_rows(1, amount=8)
    ws["A1"] = "Student Advising Report"
    ws["A3"] = "Name:"; ws["B3"] = student_name
    ws["A4"] = "ID:"; ws["B4"] = student_id
    ws["A5"] = "Credits Completed:"; ws["B5"] = credits_completed
    ws["A6"] = "Standing:"; ws["B6"] = standing
    ws["A7"] = "Advisor Note:"; ws["B7"] = note
    ws["A8"] = "Credits (Advised / Optional):"; ws["B8"] = f"{advised_credits} / {optional_credits}"
    ws["A1"].font = Font(size=14, bold=True)

    # Header row styling
    header_row = 10
    ws.freeze_panes = f"A{header_row+1}"
    header_fill = PatternFill("solid", fgColor="4F81BD")
    header_font = Font(bold=True, color="FFFFFF")
    for cell in ws[header_row]:
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border = Border(left=Side(style="thick"), right=Side(style="thick"), top=Side(style="thick"), bottom=Side(style="thick"))

    # Borders for data cells
    thin = Side(style="thin", color="CCCCCC")
    for r in range(header_row + 1, ws.max_row + 1):
        for c in range(1, ws.max_column + 1):
            ws.cell(row=r, column=c).border = Border(left=thin, right=thin, top=thin, bottom=thin)

    # Color Action column including Registered
    action_col_idx = None
    for idx, cell in enumerate(ws[header_row], start=1):
        if str(cell.value).strip().lower() == "action":
            action_col_idx = idx
            break

    fills = {
        "Completed": PatternFill("solid", fgColor="C6E0B4"),
        "Advised": PatternFill("solid", fgColor="FFF2CC"),
        "Optional": PatternFill("solid", fgColor="FFE699"),
        "Eligible (not chosen)": PatternFill("solid", fgColor="E1F0FF"),
        "Eligible not chosen": PatternFill("solid", fgColor="E1F0FF"),
        "Not Eligible": PatternFill("solid", fgColor="F8CECC"),
        "Registered": PatternFill("solid", fgColor="BDD7EE"),
    }
    if action_col_idx:
        for r in range(header_row + 1, ws.max_row + 1):
            v = str(ws.cell(row=r, column=action_col_idx).value or "")
            for key, fill in fills.items():
                if key.lower() in v.lower():
                    ws.cell(row=r, column=action_col_idx).fill = fill
                    break

    # Auto width
    for col in ws.columns:
        letter = col[0].column_letter
        max_len = max(len(str(c.value)) if c.value is not None else 0 for c in col)
        ws.column_dimensions[letter].width = max_len + 2

    out = BytesIO()
    wb.save(out); out.seek(0)
    return out

def add_summary_sheet(writer, full_report: pd.DataFrame, course_cols: List[str]) -> None:
    """
    Summary counts for c (completed), r (registered), a (advised), na, ne.
    """
    rows = []
    for c in course_cols:
        vc = full_report[c].value_counts(dropna=False).to_dict()
        rows.append({
            "Course": c,
            "Completed (c)": int(vc.get("c", 0)),
            "Registered (r)": int(vc.get("r", 0)),
            "Advised (a)": int(vc.get("a", 0)),
            "Eligible not chosen (na)": int(vc.get("na", 0)),
            "Not Eligible (ne)": int(vc.get("ne", 0)),
        })
    pd.DataFrame(rows).to_excel(writer, index=False, sheet_name="Summary")
