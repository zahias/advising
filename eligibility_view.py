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


def _safe_defaults(options, defaults):
    """Return (valid_defaults, dropped_defaults) ensuring defaults ⊆ options."""
    defaults = defaults or []
    optset = set(options or [])
    valid = [d for d in defaults if d in optset]
    dropped = [d for d in defaults if d not in optset]
    return valid, dropped


def student_eligibility_view():
    st.header("Student Eligibility View")

    student_names = st.session_state.progress_df['NAME'].tolist()
    selected_name = st.selectbox("Select student", student_names)

    student_row = st.session_state.progress_df[
        st.session_state.progress_df['NAME'] == selected_name
    ].iloc[0]
    selected_student_id = student_row['ID']

    # Ensure session selection bucket
    st.session_state.advising_selections.setdefault(
        selected_student_id, {'advised': [], 'optional': [], 'note': ''}
    )

    credits_completed = int(student_row['# of Credits Completed'])
    total = credits_completed + int(student_row['# Registered'])
    standing = get_student_standing(total)

    # Build table rows + track currently-eligible courses
    rows = []
    eligible_codes = []
    for _, course_row in st.session_state.courses_df.iterrows():
        code = course_row['Course Code']
        ctype = course_row['Type']
        reqs = build_requisites_str(course_row)
        offered = 'Yes' if is_course_offered(st.session_state.courses_df, code) else 'No'

        status, justification = check_eligibility(student_row, course_row, standing)

        # Determine "Action" label
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
        else:
            action = ACTION_LABELS["NOT_ELIGIBLE"]

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

    # --- Safe defaults for multiselects (prevents StreamlitAPIException) ---
    current_sel = st.session_state.advising_selections[selected_student_id]
    valid_advised, dropped_advised = _safe_defaults(eligible_codes, current_sel.get('advised'))
    valid_optional, dropped_optional = _safe_defaults(eligible_codes, current_sel.get('optional'))

    if dropped_advised or dropped_optional:
        with st.expander("Previously selected but not currently eligible"):
            if dropped_advised:
                st.caption(f"Advised (kept in memory, not selectable now): {', '.join(dropped_advised)}")
            if dropped_optional:
                st.caption(f"Optional (kept in memory, not selectable now): {', '.join(dropped_optional)}")

    advised = st.multiselect(
        "Advised courses",
        options=eligible_codes,
        default=valid_advised,
        help="Only courses currently eligible appear here. Previously saved but not eligible now are shown above."
    )
    optional = st.multiselect(
        "Optional courses",
        options=eligible_codes,
        default=valid_optional
    )
    note = st.text_input("Note", value=current_sel.get('note') or "")

    st.session_state.advising_selections[selected_student_id] = {
        'advised': advised,
        'optional': optional,
        'note': note
    }

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
