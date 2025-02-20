# reporting.py

import pandas as pd
from io import BytesIO
from openpyxl import load_workbook
from openpyxl.styles import PatternFill, Font, Alignment, Border, Side
from utils import check_course_completed, get_student_standing, check_eligibility

def apply_excel_formatting(output, student_name, student_id, credits_completed, standing, note, advised_credits, optional_credits):
    """
    Enhances the Excel formatting for a single student's advising report.
    Inserts a student info block at the top, applies formatted header row with freeze panes,
    cell borders, center alignment, and conditional formatting for the "Action" column.
    """
    # Load the workbook from the BytesIO buffer
    output.seek(0)
    wb = load_workbook(output)
    ws = wb.active
    ws.title = "Advising Report"

    # --- Insert Student Information (Rows 1-7) ---
    ws.insert_rows(1, 7)
    info = [
        ("Student Name:", student_name),
        ("Student ID:", student_id),
        ("# of Credits Completed:", credits_completed),
        ("Standing:", standing),
        ("Credits Advised:", advised_credits),
        ("Credits Optional:", optional_credits),
        ("Note:", note)
    ]
    for idx, (label, value) in enumerate(info, start=1):
        ws[f"A{idx}"] = label
        ws[f"B{idx}"] = value
        ws[f"A{idx}"].font = Font(bold=True, size=12)
        ws[f"B{idx}"].font = Font(size=12)
        ws[f"A{idx}"].alignment = Alignment(horizontal="left", vertical="center")
        ws[f"B{idx}"].alignment = Alignment(horizontal="left", vertical="center")

    # --- Format Header Row for the Data Table ---
    header_row = 10  # Data table header row
    ws.freeze_panes = f"A{header_row+1}"  # Freeze header row
    header_fill = PatternFill(start_color="4F81BD", end_color="4F81BD", fill_type="solid")
    header_font = Font(bold=True, color="FFFFFF", size=12)
    header_alignment = Alignment(horizontal="center", vertical="center")
    thick_border = Border(
        left=Side(style="thick"),
        right=Side(style="thick"),
        top=Side(style="thick"),
        bottom=Side(style="thick")
    )
    for cell in ws[header_row]:
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = header_alignment
        cell.border = thick_border

    # --- Apply Formatting for Data Cells (Rows header_row+1 onward) ---
    thin_border = Border(
        left=Side(style="thin"),
        right=Side(style="thin"),
        top=Side(style="thin"),
        bottom=Side(style="thin")
    )
    data_alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    for row in ws.iter_rows(min_row=header_row+1, max_row=ws.max_row):
        for cell in row:
            cell.border = thin_border
            cell.alignment = data_alignment

    # --- Conditional Formatting for "Action" Column ---
    action_col_idx = None
    for idx, cell in enumerate(ws[header_row], start=1):
        if cell.value and "Action" in str(cell.value):
            action_col_idx = idx
            break

    fill_mapping = {
        "Completed": PatternFill(start_color="D3D3D3", end_color="D3D3D3", fill_type="solid"),
        "Advised": PatternFill(start_color="90EE90", end_color="90EE90", fill_type="solid"),
        "Optional": PatternFill(start_color="FFFACD", end_color="FFFACD", fill_type="solid"),
        "Eligible not chosen": PatternFill(start_color="E0FFE0", end_color="E0FFE0", fill_type="solid"),
        "Not Eligible": PatternFill(start_color="F08080", end_color="F08080", fill_type="solid")
    }
    if action_col_idx:
        for row in ws.iter_rows(min_row=header_row+1, max_row=ws.max_row):
            cell = row[action_col_idx-1]
            if cell.value:
                text = str(cell.value).lower()
                if "completed" in text:
                    cell.fill = fill_mapping["Completed"]
                elif "advised" in text:
                    cell.fill = fill_mapping["Advised"]
                elif "optional" in text:
                    cell.fill = fill_mapping["Optional"]
                elif "eligible" in text:
                    if "not chosen" in text or "na" in text:
                        cell.fill = fill_mapping["Eligible not chosen"]
                    else:
                        cell.fill = fill_mapping["Eligible not chosen"]
                elif "not eligible" in text:
                    cell.fill = fill_mapping["Not Eligible"]

    # --- Auto-adjust Column Widths ---
    for column in ws.columns:
        max_length = 0
        column_letter = column[0].column_letter
        for cell in column:
            try:
                cell_length = len(str(cell.value))
                if cell_length > max_length:
                    max_length = cell_length
            except Exception:
                pass
        ws.column_dimensions[column_letter].width = max_length + 2

    # --- Ensure All Worksheets Are Visible ---
    for sheet in wb.worksheets:
        sheet.sheet_state = "visible"
    wb.active = 0

    new_output = BytesIO()
    wb.save(new_output)
    new_output.seek(0)
    return new_output

def apply_full_report_formatting(output, base_cols_count):
    """
    Applies formatting to the full advising report Excel workbook so that it
    closely mimics the in-app view.
    - Assumes that the first row is the header row.
    - `base_cols_count` is the number of base columns (non-course columns).
    """
    output.seek(0)
    wb = load_workbook(output)
    ws = wb.active

    # Freeze the header row
    ws.freeze_panes = "A2"

    # Format header row (row 1)
    header_fill = PatternFill(start_color="4F81BD", end_color="4F81BD", fill_type="solid")
    header_font = Font(bold=True, color="FFFFFF", size=12)
    header_alignment = Alignment(horizontal="center", vertical="center")
    for cell in ws[1]:
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = header_alignment

    # Define conditional fill mapping based on cell value (for course columns)
    fill_mapping = {
        "c": PatternFill(start_color="D3D3D3", end_color="D3D3D3", fill_type="solid"),      # Completed
        "a": PatternFill(start_color="90EE90", end_color="90EE90", fill_type="solid"),      # Advised
        "na": PatternFill(start_color="E0FFE0", end_color="E0FFE0", fill_type="solid"),     # Eligible not chosen
        "ne": PatternFill(start_color="F08080", end_color="F08080", fill_type="solid")      # Not Eligible
    }

    thin_border = Border(
        left=Side(style="thin"),
        right=Side(style="thin"),
        top=Side(style="thin"),
        bottom=Side(style="thin")
    )
    data_alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

    # Apply formatting for all data cells (rows 2 onward)
    for row in ws.iter_rows(min_row=2, max_row=ws.max_row):
        for cell in row:
            cell.border = thin_border
            cell.alignment = data_alignment
            # For course columns (columns after the base columns), apply conditional fill
            if cell.column > base_cols_count:
                # Expect the value to be one of: c, a, na, ne
                if cell.value in fill_mapping:
                    cell.fill = fill_mapping[cell.value]

    # Auto-adjust column widths
    for column in ws.columns:
        max_length = 0
        column_letter = column[0].column_letter
        for cell in column:
            try:
                cell_length = len(str(cell.value))
                if cell_length > max_length:
                    max_length = cell_length
            except Exception:
                pass
        ws.column_dimensions[column_letter].width = max_length + 2

    # Ensure all sheets are visible
    for sheet in wb.worksheets:
        sheet.sheet_state = "visible"
    wb.active = 0

    new_output = BytesIO()
    wb.save(new_output)
    new_output.seek(0)
    return new_output

def add_summary_sheet(writer, courses_df, advising_selections, progress_df):
    """Add a summary sheet that aggregates course status counts across all students."""
    course_status_counts = {course: {'Completed': 0, 'Advised': 0, 'Eligible not chosen': 0, 'Not Eligible': 0} for course in courses_df['Course Code']}
    for _, student in progress_df.iterrows():
        sid = str(student['ID'])
        selections = advising_selections.get(sid, {})
        for course in courses_df['Course Code']:
            if check_course_completed(student, course):
                course_status = 'Completed'
            elif course in selections.get('advised', []):
                course_status = 'Advised'
            else:
                eligibility_status, _ = check_eligibility(student, course, selections.get('advised', []), courses_df)
                if eligibility_status == 'Eligible':
                    course_status = 'Eligible not chosen'
                else:
                    course_status = 'Not Eligible'
            if course_status in course_status_counts[course]:
                course_status_counts[course][course_status] += 1

    summary_list = []
    for course, statuses in course_status_counts.items():
        summary_list.append({
            'Course Code': course,
            'Completed (c)': statuses['Completed'],
            'Advised (a)': statuses['Advised'],
            'Eligible not chosen (na)': statuses['Eligible not chosen'],
            'Not Eligible (ne)': statuses['Not Eligible']
        })
    summary_df = pd.DataFrame(summary_list)
    summary_df.to_excel(writer, sheet_name='Summary', index=False)
