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
    log_info,
    log_error
)
from reporting import apply_excel_formatting

def student_eligibility_view():
    """Render the Student Eligibility View tab."""
    st.header('Student Eligibility View')

    # 1) Student selector
    student_list = (
        st.session_state.progress_df['ID'].astype(str)
        + ' - '
        + st.session_state.progress_df['NAME']
    )
    selected_student = st.selectbox(
        'Select a Student',
        student_list,
        help="Select a student to review."
    )
    selected_id = selected_student.split(' - ')[0]
    student_row = (
        st.session_state.progress_df
        .loc[st.session_state.progress_df['ID'] == int(selected_id)]
        .iloc[0]
        .to_dict()
    )

    # 2) Ensure session_state selections exist
    if selected_id not in st.session_state.advising_selections:
        st.session_state.advising_selections[selected_id] = {
            'advised': [], 'optional': [], 'note': ''
        }
    cur_advised  = st.session_state.advising_selections[selected_id]['advised']
    cur_optional = st.session_state.advising_selections[selected_id]['optional']
    cur_note     = st.session_state.advising_selections[selected_id]['note']

    # 3) Compute total credits + standing
    ccomp = student_row.get('# of Credits Completed', 0)
    creg  = student_row.get('# Registered', 0)
    total_cred = (ccomp if pd.notna(ccomp) else 0) + (creg if pd.notna(creg) else 0)
    standing = get_student_standing(total_cred)
    log_info(f"Student {selected_id} total credits {total_cred}, standing {standing}")

    # 4) Build eligibility map
    eligibility = {}
    justification = {}
    for code in st.session_state.courses_df['Course Code']:
        stat, just = check_eligibility(student_row, code, cur_advised,
                                       st.session_state.courses_df)
        eligibility[code] = stat
        justification[code] = just

    # 5) Which courses appear in the selectors?
    eligible_list = [
        c for c in st.session_state.courses_df['Course Code']
        if eligibility[c] == 'Eligible' or c in cur_advised or c in cur_optional
    ]

    # 6) Course selection form
    with st.form('course_selection_form'):
        st.subheader('Select Courses')

        # Advised
        advised_opts = [c for c in eligible_list if eligibility[c] == 'Eligible']
        default_adv  = [c for c in cur_advised if c in advised_opts]
        advised_sel  = st.multiselect(
            'Advised Courses',
            options=advised_opts,
            default=default_adv,
            key='advised_selection',
            help="Select strongly recommended courses."
        )

        # Optional
        opt_opts = [
            c for c in eligible_list
            if eligibility[c] == 'Eligible' and c not in advised_sel
        ]
        default_opt = [c for c in cur_optional if c in opt_opts]
        optional_sel = st.multiselect(
            'Optional Courses',
            options=opt_opts,
            default=default_opt,
            key='optional_selection',
            help="Select additional optional courses."
        )

        # Note
        note_input = st.text_area(
            'Advisor Note (Optional)',
            value=cur_note,
            key='note_field',
            help="Additional guidance for the student."
        )

        # Submit
        submitted = st.form_submit_button('Submit Selections')
        if submitted:
            st.session_state.advising_selections[selected_id]['advised'] = sorted(advised_sel)
            st.session_state.advising_selections[selected_id]['optional'] = sorted(optional_sel)
            st.session_state.advising_selections[selected_id]['note'] = note_input.strip()
            st.success('✅ Selections updated.')
            log_info(f"Updated selections for student {selected_id}")
            st.session_state.data_uploaded = True
            st.experimental_rerun()

    # 7) Credit totals
    if 'Credits' not in st.session_state.courses_df.columns:
        st.warning("⚠️ Missing 'Credits' column—cannot sum credits.")
        advised_cred = optional_cred = 'N/A'
        log_error("Missing Credits column", "Cannot compute advised/optional credits.")
    else:
        df = st.session_state.courses_df
        advised_cred  = df.loc[df['Course Code'].isin(advised_sel),  'Credits'].sum()
        optional_cred = df.loc[df['Course Code'].isin(optional_sel), 'Credits'].sum()

    # 8) Display student info
    st.markdown("### Student Information")
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.markdown(f"**Name:** {student_row['NAME']}")
    c2.markdown(f"**Credits Completed:** {total_cred}")
    c3.markdown(f"**Standing:** {standing}")
    c4.markdown(f"**Credits Advised:** {advised_cred}")
    c5.markdown(f"**Credits Optional:** {optional_cred}")

    # 9) Build and show eligibility table
    rows = []
    for code in st.session_state.courses_df['Course Code']:
        status = eligibility.get(code, 'Not Eligible')
        just   = justification.get(code, '')
        # course_info
        info   = st.session_state.courses_df.loc[
            st.session_state.courses_df['Course Code'] == code
        ].iloc[0]
        offered = 'Yes' if is_course_offered(st.session_state.courses_df, code) else 'No'
        ctype   = info['Type']
        reqs    = build_requisites_str(info)

        # Determine raw progress val
        val = str(student_row.get(code,'')).strip().upper()
        if val == 'C':
            action, status = 'Completed', 'Completed'
        elif val == 'NR':
            action, status = 'Registered', 'Registered'
        elif code in advised_sel:
            action = 'Advised'
        elif code in optional_sel:
            action = 'Optional'
        else:
            action = 'Eligible (not chosen)' if status=='Eligible' else 'Not Eligible'

        if status == 'Eligible' and not just:
            just = 'All requirements met.'

        rows.append({
            'Course Code': code,
            'Type': ctype,
            'Requisites': reqs,
            'Eligibility Status': status,
            'Justification': just,
            'Offered': offered,
            'Action': action
        })

    disp_df = pd.DataFrame(rows)
    req_df  = disp_df[disp_df['Type']=='Required'].copy()
    int_df  = disp_df[disp_df['Type']=='Intensive'].copy()

    st.markdown("### Course Eligibility")
    if not req_df.empty:
        st.markdown("**Required Courses**")
        st.dataframe(style_df(req_df), use_container_width=True)
    if not int_df.empty:
        st.markdown("**Intensive Courses**")
        st.dataframe(style_df(int_df), use_container_width=True)

    # 10) Download report
    st.subheader('Download Advising Report')
    if st.button('Download Student Report'):
        combined = pd.concat([req_df, int_df], ignore_index=True)
        buf = BytesIO()
        with pd.ExcelWriter(buf, engine='openpyxl') as w:
            combined.to_excel(w, sheet_name='Advising Report', index=False)
        formatted = apply_excel_formatting(
            buf,
            student_row['NAME'],
            student_row['ID'],
            total_cred,
            standing,
            st.session_state.advising_selections[selected_id]['note'],
            advised_cred,
            optional_cred
        )
        st.download_button(
            label='Download Advising Report',
            data=formatted.getvalue(),
            file_name=f"{student_row['NAME'].replace(' ','_')}_Advising_Report.xlsx",
            mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        log_info(f"Downloaded report for student {selected_id}")
