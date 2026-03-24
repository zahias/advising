from __future__ import annotations

import logging
import smtplib
import socket
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

logger = logging.getLogger(__name__)

_SMTP_TIMEOUT = 15  # seconds — prevents hanging when SMTP host is unreachable

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Major
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


def send_student_email(session: Session, *, major_code: str, student_id: str, template_key: str = 'default', adviser_email: str | None = None) -> dict:
    major = session.scalar(select(Major).where(Major.code == major_code))
    if not major or not major.smtp_email or not major.smtp_password:
        logger.warning('SMTP credentials not configured for major %s — email not sent.', major_code)
        return {'success': False, 'message': f'SMTP credentials are not configured for {major_code}.'}
    email_data = build_student_email(session, major_code=major_code, student_id=student_id, template_key=template_key)
    recipient = email_data.get('recipient')
    if not recipient:
        logger.warning('No email roster entry for student %s in %s — email not sent.', student_id, major_code)
        return {'success': False, 'message': 'No email roster entry found for this student.'}
    message = MIMEMultipart()
    message['From'] = major.smtp_email
    message['To'] = recipient
    message['Subject'] = str(email_data['subject'])
    recipients = [recipient]
    if adviser_email:
        message['Cc'] = adviser_email
        recipients.append(adviser_email)
    message.attach(MIMEText(str(email_data['preview_body']), 'plain'))
    try:
        logger.info('Connecting to smtp.office365.com:587 as %s → sending to %s (CC: %s)', major.smtp_email, recipient, adviser_email or 'none')
        with smtplib.SMTP('smtp.office365.com', 587, timeout=_SMTP_TIMEOUT) as server:
            server.starttls()
            server.login(major.smtp_email, major.smtp_password)
            server.sendmail(major.smtp_email, recipients, message.as_string())
        logger.info('Email accepted by SMTP server for %s', recipient)
        return {'success': True, 'message': f'Email sent to {recipient}.'}
    except smtplib.SMTPAuthenticationError as exc:
        logger.error('SMTP auth failed for %s: %s', major.smtp_email, exc)
        return {'success': False, 'message': f'SMTP authentication failed: {exc}'}
    except smtplib.SMTPException as exc:
        logger.error('SMTP error: %s', exc)
        return {'success': False, 'message': f'SMTP error: {exc}'}
    except (OSError, socket.timeout) as exc:
        logger.error('SMTP connection error: %s', exc)
        return {'success': False, 'message': f'Could not connect to SMTP server: {exc}'}
