# reporting.py

import pandas as pd
from io import BytesIO
from openpyxl import load_workbook
from openpyxl.styles import PatternFill, Font, Alignment, Border, Side
from utils import check_course_completed, check_course_registered, get_student_standing, check_eligibility

# ---- Single-student sheet formatting ----
def apply_excel_formatting(output: BytesIO, student_name, student_id, credits_completed, standing, note, advised_credits, optional_credits):
    """
    Enhance the Excel generated for a single student:
      - Insert student info block
      - Style header row
      - Freeze header
      - Color 'Action' column values
    This function edits the BytesIO buffer in place.
    """
    output.seek(0)
    wb = load_workbook(output)
    ws = wb.active
    ws.title = "Advising Report"

    # Insert top info block
    ws.insert_rows(1, 7)
    info = [
        ("Student Name:", student_name),
        ("Student ID:", student_id),
        ("# of Credits Completed:", credits_completed),
        ("Standing:", standing),
        ("Credits Advised:", advised_credits),
        ("Credits Optional:", optional_credits),
        ("Note:", note),
    ]
    for idx, (label, value) in enumerate(info, start=1):
        ws.cell(row=idx, column=1, value=label)
        ws.cell(row=idx, column=2, value=str(value))

    # Header styling
    header_row = 10
    ws.freeze_panes = f"A{header_row+1}"
    header_fill = PatternFill(start_color="4F81BD", end_color="4F81BD", fill_type="solid")
    header_font = Font(bold=True, color="FFFFFF", size=12)
    header_alignment = Alignment(horizontal="center", vertical="center")
    thick_border = Border(left=Side(style="thick"), right=Side(style="thick"), top=Side(style="thick"), bottom=Side(style="thick"))

    for cell in ws[header_row]:
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = header_alignment
        cell.border = thick_border

    # Column autosize (simple)
    for column in ws.columns:
        max_len = 0
        col_letter = column[0].column_letter
        for c in column:
            try:
                l = len(str(c.value))
                if l > max_len:
                    max_len = l
            except Exception:
                pass
        ws.column_dimensions[col_letter].width = max_len + 2

    # Conditional fills for Action column
    fills = {
        "Completed": PatternFill(fill_type="solid", fgColor="D9D9D9"),
        "Registered": PatternFill(fill_type="solid", fgColor="BDD7EE"),
        "Advised": PatternFill(fill_type="solid", fgColor="C6EFCE"),
        "Optional": PatternFill(fill_type="solid", fgColor="FFF2CC"),
        "Eligible (not chosen)": PatternFill(fill_type="solid", fgColor="E0FFE0"),
        "Not Eligible": PatternFill(fill_type="solid", fgColor="F4CCCC"),
    }

    # Find Action column index
    header = [cell.value for cell in ws[header_row]]
    try:
        action_col_idx = header.index("Action") + 1
    except ValueError:
        action_col_idx = None

    if action_col_idx:
        for r in range(header_row + 1, ws.max_row + 1):
            val = str(ws.cell(row=r, column=action_col_idx).value or "")
            # Normalize typical variants
            if val.lower().startswith("eligible") and "not chosen" in val.lower():
                key = "Eligible (not chosen)"
            else:
                key = val
            fill = fills.get(key)
            if fill:
                for c in range(1, ws.max_column + 1):
                    ws.cell(row=r, column=c).fill = fill

    # Ensure sheet is visible
    for sh in wb.worksheets:
        sh.sheet_state = "visible"

    output.seek(0)
    wb.save(output)
    output.seek(0)

# ---- Cohort summary ----
def add_summary_sheet(writer, courses_df, advising_selections, progress_df):
    """
    Add a 'Summary' sheet that aggregates course status counts across all students.
    Status buckets: Completed (c), Registered (r), Advised (a), Eligible not chosen (na), Not Eligible (ne)
    """
    counts = {c: {"Completed": 0, "Registered": 0, "Advised": 0, "Eligible not chosen": 0, "Not Eligible": 0}
              for c in courses_df["Course Code"]}

    for _, student in progress_df.iterrows():
        sid = str(student["ID"])
        sels = advising_selections.get(sid, {})
        advised = set(sels.get("advised", []))
        optional = set(sels.get("optional", []))
        chosen = advised | optional
        for course in courses_df["Course Code"]:
            if check_course_completed(student, course):
                bucket = "Completed"
            elif check_course_registered(student, course):
                bucket = "Registered"
            elif course in chosen:
                bucket = "Advised"
            else:
                status, _ = check_eligibility(student, course, list(chosen), courses_df)
                bucket = "Eligible not chosen" if status == "Eligible" else "Not Eligible"
            counts[course][bucket] += 1

    summary_rows = []
    for course, d in counts.items():
        summary_rows.append(
            {
                "Course Code": course,
                "Completed (c)": d["Completed"],
                "Registered (r)": d["Registered"],
                "Advised (a)": d["Advised"],
                "Eligible not chosen (na)": d["Eligible not chosen"],
