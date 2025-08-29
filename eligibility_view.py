# eligibility_view.py

import streamlit as st
import pandas as pd
from io import BytesIO
from utils import (
    check_course_completed,
    is_course_offered,
    check_eligibility,
    build_requisites_str,
    style_df,
    get_student_standing,
    ACTION_LABELS,
    log_info,
    log_error,
)
from reporting import apply_excel_formatting

def student_eligibility_view():
    st.header("Student Eligibility View")

    student_names = st.session_state.progress_df['NAME'].tolist()
    selected_name = st.selectbox("Select student", student_names)

    student_row = st.session_state.progress_df[st.session_state.progress_df['NAME'] == selected_name].iloc[0]
    selected_student_id = student_row['ID']

    # Ensure session selection bucket
    st.session_state.advising_selections.setdefault(selected_student_id, {'advised': [], 'optional': [], 'note': ''})

    credits_completed = int(student_row['# of Credits Completed'])
    total = credits_completed + int(student_row['# Registered'])
    standing = get_student_standing(total)

    # Build table
    rows = []
    eligible_codes = []
    for _, course_row in st.session_state.courses_df.iterrows():
        code = course_row['Course Code']
        ctype = course_row['Type']
        reqs = build_requisites_str(course_row)
        offered = 'Yes' if is_course_offered(st.session_state.courses_df, code) else 'No'

        status, justification = check_eligibility(student_row, course_row, standing)
        action = ACTION_LABELS["NOT_ELIGIBLE"]
        if check_course_completed(student_row, code):
            action = ACTION_LABELS["COMPLETED"]
            status = "Completed"
        elif code in st.session_state.advising_selections[selected_student_id]['advised']:
            action = ACTION_LABELS["ADVISED"]
        elif code in st.session_state.advising_selections[selected_student_id]['optional']:
            action = ACTION_LABELS["OPTIONAL"]
        elif status == "Eligible":
            action = ACTION_LABELS["ELIGIBLE_NOT_CHOSEN"]
            eligible_codes.append(code)

        rows.append({
            'Course Code': code,
            'Type': ctype,
            'Requisites': reqs,
            'Eligibility Status': status,
            'Justification': justification,
            'Offered': offered,
            'Action': action,
        })

    df = pd.DataFrame(rows)
    st.dataframe(style_df(df), use_container_width=True)

    # Advised/Optional controls — limited to eligible codes, never "not offered"
    advised = st.multiselect("Advised courses", options=eligible_codes,
                             default=st.session_state.advising_selections[selected_student_id]['advised'])
    optional = st.multiselect("Optional courses", options=eligible_codes,
                              default=st.session_state.advising_selections[selected_student_id]['optional'])
    note = st.text_input("Note", value=st.session_state.advising_selections[selected_student_id]['note'])
    st.session_state.advising_selections[selected_student_id] = {'advised': advised, 'optional': optional, 'note': note}

    # Credits (if present)
    advised_credits = optional_credits = None
    if 'Credits' in st.session_state.courses_df.columns:
        cdict = dict(zip(st.session_state.courses_df['Course Code'], st.session_state.courses_df['Credits']))
        advised_credits = sum(cdict.get(c, 0) for c in advised)
        optional_credits = sum(cdict.get(c, 0) for c in optional)

    # Download
    if st.button("Download Advising Report"):
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Advising', index=False)
        apply_excel_formatting(
            output,
            student_row['NAME'],
            student_row['ID'],
            credits_completed,
            standing,
            note,
            advised_credits,
            optional_credits,
        )
        st.download_button(
            label='Download',
            data=output.getvalue(),
            file_name=f'{student_row["NAME"].replace(" ", "_")}_Advising_Report.xlsx',
            mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        )
        log_info(f"Advising report downloaded for student ID {selected_student_id}.")
