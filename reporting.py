# reporting.py

import pandas as pd
from io import BytesIO
from openpyxl import load_workbook
from openpyxl.styles import PatternFill, Font, Alignment, Border, Side
from utils import (
    check_course_completed,
    get_student_standing,
    check_eligibility,
    ACTION_LABELS,
    STATUS_CODES,
    COLOR_MAP,
)

def _fill_for(label: str) -> PatternFill:
    color = COLOR_MAP.get(label)
    if not color:
        return PatternFill(fill_type=None)
    return PatternFill(start_color=color, end_color=color, fill_type="solid")

def apply_excel_formatting(
    output: BytesIO,
    student_name: str,
    student_id: str,
    credits_completed: int,
    standing: str,
    note: str,
    advised_credits: int | float | None,
    optional_credits: int | float | None,
):
    """
    Enhances the Excel formatting for a single student's advising report.
    Inserts a student info block at the top, applies formatted header row with freeze panes,
    borders, alignment, and conditional fills for the "Action" column using centralized colors.
    """
    output.seek(0)
    wb = load_workbook(output)
    ws = wb.active

    # Insert student info block
    info = [
        ["Student", student_name],
        ["ID", student_id],
        ["Credits Completed", credits_completed],
        ["Standing", standing],
        ["Note", note or ""],
        ["Advised Credits", advised_credits if advised_credits is not None else ""],
        ["Optional Credits", optional_credits if optional_credits is not None else ""],
    ]
    ws.insert_rows(1, amount=len(info) + 1)
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=ws.max_column)
    ws.cell(1, 1, "Advising Report").font = Font(bold=True, size=14)
    for r, (k, v) in enumerate(info, start=2):
        ws.cell(r, 1, k).font = Font(bold=True)
        ws.cell(r, 2, v)

    # Header formatting
    header_row = len(info) + 1
    for c in range(1, ws.max_column + 1):
        cell = ws.cell(header_row, c)
        cell.font = Font(bold=True)
        cell.alignment = Alignment(horizontal="center", vertical="center")
    ws.freeze_panes = ws.cell(header_row + 1, 1)

    # Borders
    thin = Side(border_style="thin", color="999999")
    for row in ws.iter_rows(min_row=header_row, max_row=ws.max_row):
        for cell in row:
            cell.border = Border(top=thin, bottom=thin, left=thin, right=thin)
            if cell.row > header_row:
                cell.alignment = Alignment(vertical="top")

    # Conditional fill for the "Action" column
    action_col_idx = None
    for c in range(1, ws.max_column + 1):
        if str(ws.cell(header_row, c).value).strip().lower() == 'action':
            action_col_idx = c
            break

    if action_col_idx:
        fills = {
            ACTION_LABELS["COMPLETED"]: _fill_for(ACTION_LABELS["COMPLETED"]),
            ACTION_LABELS["ADVISED"]: _fill_for(ACTION_LABELS["ADVISED"]),
            ACTION_LABELS["OPTIONAL"]: _fill_for(ACTION_LABELS["OPTIONAL"]),
            ACTION_LABELS["ELIGIBLE_NOT_CHOSEN"]: _fill_for(ACTION_LABELS["ELIGIBLE_NOT_CHOSEN"]),
            ACTION_LABELS["NOT_ELIGIBLE"]: _fill_for(ACTION_LABELS["NOT_ELIGIBLE"]),
        }
        for row in ws.iter_rows(min_row=header_row + 1, max_row=ws.max_row):
            cell = row[action_col_idx - 1]
            if not cell.value:
                continue
            label = str(cell.value)
            if "completed" in label.lower():
                cell.fill = fills[ACTION_LABELS["COMPLETED"]]
            elif "advised" in label.lower():
                cell.fill = fills[ACTION_LABELS["ADVISED"]]
            elif "optional" in label.lower():
                cell.fill = fills[ACTION_LABELS["OPTIONAL"]]
            elif "eligible" in label.lower():
                cell.fill = fills[ACTION_LABELS["ELIGIBLE_NOT_CHOSEN"]]
            elif "not eligible" in label.lower():
                cell.fill = fills[ACTION_LABELS["NOT_ELIGIBLE"]]

    # Save back to buffer
    new_output = BytesIO()
    wb.save(new_output)
    new_output.seek(0)
    output.truncate(0)
    output.seek(0)
    output.write(new_output.read())
    output.seek(0)

def add_summary_sheet(writer, full_df: pd.DataFrame, course_cols: list[str]):
    """
    Build 'Summary' across students for wide export, using centralized codes/labels.
    Counts, per course:
      - Completed (c)
      - Advised (a)
      - Eligible not chosen (na)
      - Not Eligible (ne)
    """
    course_status_counts = {
        course: {"Completed": 0, "Advised": 0, "Eligible not chosen": 0, "Not Eligible": 0}
        for course in course_cols
    }
    for _, row in full_df.iterrows():
        for course in course_cols:
            val = str(row.get(course, "")).strip().lower()
            if val == STATUS_CODES["COMPLETED"]:
                course_status_counts[course]["Completed"] += 1
            elif val == STATUS_CODES["ADVISED"]:
                course_status_counts[course]["Advised"] += 1
            elif val == STATUS_CODES["ELIGIBLE_NOT_CHOSEN"]:
                course_status_counts[course]["Eligible not chosen"] += 1
            elif val == STATUS_CODES["NOT_ELIGIBLE"]:
                course_status_counts[course]["Not Eligible"] += 1

    summary_list = []
    for course, statuses in course_status_counts.items():
        summary_list.append({
            'Course Code': course,
            'Completed (c)': statuses['Completed'],
            'Advised (a)': statuses['Advised'],
            'Eligible not chosen (na)': statuses['Eligible not chosen'],
            'Not Eligible (ne)': statuses['Not Eligible'],
        })
    summary_df = pd.DataFrame(summary_list)
    summary_df.to_excel(writer, sheet_name='Summary', index=False)
