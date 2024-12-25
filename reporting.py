# reporting.py

import pandas as pd
from io import BytesIO
from openpyxl.styles import PatternFill, Font
from openpyxl import load_workbook
from utils import check_course_completed, get_student_standing, check_eligibility  # Updated imports

def apply_excel_formatting(output, student_name, student_id, credits_completed, standing, note, advised_credits, optional_credits):
    """Apply formatting to the Excel report."""
    output.seek(0)
    wb = load_workbook(output)
    ws = wb.active
    ws.title = 'Advising Report'

    # Insert student info at the top
    ws.insert_rows(1, 9)  # Increased to accommodate new credit fields
    ws['A1'] = 'Student Name:'
    ws['B1'] = student_name
    ws['A2'] = 'Student ID:'
    ws['B2'] = student_id
    ws['A3'] = '# of Credits Completed:'
    ws['B3'] = credits_completed  # Updated to include the sum
    ws['A4'] = 'Standing:'
    ws['B4'] = standing
    ws['A5'] = 'Credits Advised:'
    ws['B5'] = advised_credits
    ws['A6'] = 'Credits Optional:'
    ws['B6'] = optional_credits
    ws['A7'] = 'Note:'
    ws['B7'] = note

    # Apply bold font to headers
    header_row = 9
    for cell in ws[header_row]:
        cell.font = Font(bold=True)

    # Find the 'Action' column
    action_col = None
    for idx, cell in enumerate(ws[header_row], start=1):
        if cell.value == 'Action':
            action_col = idx
            break

    # Apply color fills based on Action
    if action_col:
        for row in ws.iter_rows(min_row=header_row+1, max_row=ws.max_row, min_col=1, max_col=ws.max_column):
            action_val = row[action_col-1].value
            if action_val:
                fill = None
                if 'Completed' in action_val:
                    fill = PatternFill(start_color='D3D3D3', end_color='D3D3D3', fill_type='solid')
                elif 'Advised' in action_val:
                    fill = PatternFill(start_color='90EE90', end_color='90EE90', fill_type='solid')
                elif 'Optional' in action_val:
                    fill = PatternFill(start_color='FFFACD', end_color='FFFACD', fill_type='solid')
                elif 'Eligible (not chosen)' in action_val:
                    fill = PatternFill(start_color='E0FFE0', end_color='E0FFE0', fill_type='solid')
                elif 'Not Eligible' in action_val:
                    fill = PatternFill(start_color='F08080', end_color='F08080', fill_type='solid')
                if fill:
                    for c in row:
                        c.fill = fill

    # Auto-adjust column widths
    for column in ws.columns:
        max_length = 0
        column_letter = column[0].column_letter
        for cell in column:
            try:
                cell_length = len(str(cell.value))
                if cell_length > max_length:
                    max_length = cell_length
            except:
                pass
        adjusted_width = (max_length + 2)
        ws.column_dimensions[column_letter].width = adjusted_width

    # Save back to BytesIO
    new_output = BytesIO()
    wb.save(new_output)
    new_output.seek(0)
    return new_output

def add_summary_sheet(writer, courses_df, advising_selections, progress_df):
    """Add a summary sheet that counts statuses for each course."""
    # Initialize a dictionary to hold counts per course
    course_status_counts = {course: {'Completed': 0, 'Advised': 0, 'Eligible not chosen': 0, 'Not Eligible': 0} for course in courses_df['Course Code']}

    for _, student in progress_df.iterrows():
        sid = str(student['ID'])
        selections = advising_selections.get(sid, {})
        # Calculate total credits completed
        credits_completed_field = student.get('# of Credits Completed', 0)
        credits_registered_field = student.get('# Registered', 0)
        credits_completed = (credits_completed_field if pd.notna(credits_completed_field) else 0) + \
                            (credits_registered_field if pd.notna(credits_registered_field) else 0)
        standing = get_student_standing(credits_completed)

        for course in courses_df['Course Code']:
            # Check if course is completed
            if check_course_completed(student, course):
                course_status = 'Completed'
            # Check if course is advised
            elif course in selections.get('advised', []):
                course_status = 'Advised'
            else:
                # Determine eligibility
                eligibility_status, _ = check_eligibility(
                    student,
                    course,
                    selections.get('advised', []),
                    courses_df
                )
                if eligibility_status == 'Eligible':
                    course_status = 'Eligible not chosen'
                else:
                    course_status = 'Not Eligible'

            # Increment the count
            if course_status in course_status_counts[course]:
                course_status_counts[course][course_status] += 1

    # Convert the counts to a DataFrame
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

    # Write the summary sheet
    summary_df.to_excel(writer, sheet_name='Summary', index=False)
