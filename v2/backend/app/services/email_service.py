from __future__ import annotations

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.services.period_service import current_period
from app.services.student_service import get_student_email, student_eligibility
from app.services.template_service import list_templates


def build_student_email(session: Session, *, major_code: str, student_id: str, template_key: str = 'default') -> dict:
    payload = student_eligibility(session, major_code, student_id)
    period = current_period(session, major_code)
    templates = {template.template_key: template for template in list_templates(session, major_code)}
    template = templates.get(template_key) or templates.get('default')
    if template is None:
        raise ValueError(f'No email template configured for {major_code}')
    semester = period.semester if period else 'Current'
    year = str(period.year) if period else ''
    advisor_name = period.advisor_name if period else ''
    subject = template.subject_template.format(
        major=major_code,
        student_name=payload.student_name,
        semester=semester,
        year=year,
        advisor_name=advisor_name,
    )
    body = template.body_template.format(
        student_name=payload.student_name,
        major=major_code,
        semester=semester,
        year=year,
        advisor_name=advisor_name,
    )
    lines = [body, '', 'Advised Courses:']
    lines.extend(f'- {course}' for course in payload.selection.advised)
    if payload.selection.optional:
        lines.extend(['', 'Optional Courses:'])
        lines.extend(f'- {course}' for course in payload.selection.optional)
    if payload.selection.repeat:
        lines.extend(['', 'Repeat Courses:'])
        lines.extend(f'- {course}' for course in payload.selection.repeat)
    if payload.selection.note:
        lines.extend(['', 'Advisor Note:', payload.selection.note])
    preview_body = '\n'.join(lines)
    return {
        'success': True,
        'recipient': get_student_email(session, major_code, student_id),
        'subject': subject,
        'preview_body': preview_body,
        'template_key': template.template_key if template else template_key,
        'variables': {
            'student_name': payload.student_name,
            'major': major_code,
            'semester': semester,
            'year': year,
            'advisor_name': advisor_name,
        },
    }


def send_student_email(session: Session, *, major_code: str, student_id: str, template_key: str = 'default') -> dict:
    settings = get_settings()
    if not settings.smtp_email or not settings.smtp_password:
        return {'success': False, 'message': 'SMTP credentials are not configured.'}
    email_data = build_student_email(session, major_code=major_code, student_id=student_id, template_key=template_key)
    recipient = email_data.get('recipient')
    if not recipient:
        return {'success': False, 'message': 'No email roster entry found for this student.'}
    message = MIMEMultipart()
    message['From'] = settings.smtp_email
    message['To'] = recipient
    message['Subject'] = str(email_data['subject'])
    message.attach(MIMEText(str(email_data['preview_body']), 'plain'))
    with smtplib.SMTP('smtp.office365.com', 587) as server:
        server.starttls()
        server.login(settings.smtp_email, settings.smtp_password)
        server.sendmail(settings.smtp_email, [recipient], message.as_string())
    return {'success': True, 'message': f'Email sent to {recipient}.'}
