from __future__ import annotations

import logging
import smtplib
import socket
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import httpx

logger = logging.getLogger(__name__)

_SMTP_TIMEOUT = 15  # seconds

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import Major
from app.services.period_service import current_period
from app.services.student_service import get_student_email, student_eligibility
from app.services.template_service import list_templates


def _graph_credentials() -> tuple[str, str, str] | None:
    """Return (tenant_id, client_id, client_secret) if all three are configured."""
    s = get_settings()
    if s.graph_tenant_id and s.graph_client_id and s.graph_client_secret:
        return s.graph_tenant_id, s.graph_client_id, s.graph_client_secret
    return None


def _send_via_resend(
    api_key: str,
    sender_email: str, recipient: str, subject: str, body: str,
    cc: str | None = None,
) -> dict:
    """Send email via Resend API (HTTPS, works everywhere, simplest setup)."""
    payload: dict = {
        'from': f'Advising <onboarding@resend.dev>',
        'to': [recipient],
        'reply_to': sender_email,
        'subject': subject,
        'text': body,
    }
    if cc:
        payload['cc'] = [cc]
    try:
        resp = httpx.post('https://api.resend.com/emails', json=payload, headers={
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json',
        }, timeout=15)
        if resp.status_code in (200, 201):
            logger.info('Email sent via Resend to %s (CC: %s)', recipient, cc or 'none')
            return {'success': True, 'message': f'Email sent to {recipient}.'}
        detail = resp.json().get('message', resp.text) if resp.headers.get('content-type', '').startswith('application/json') else resp.text
        logger.error('Resend API error (%d): %s', resp.status_code, detail)
        return {'success': False, 'message': f'Email API error ({resp.status_code}): {detail}'}
    except httpx.HTTPError as exc:
        logger.error('Resend HTTP error: %s', exc)
        return {'success': False, 'message': f'Email API request failed: {exc}'}


def _send_via_graph(
    tenant_id: str, client_id: str, client_secret: str,
    sender_email: str, recipient: str, subject: str, body: str,
    cc: str | None = None,
) -> dict:
    """Send email via Microsoft Graph API (HTTPS, works on all platforms)."""
    # 1. Get an OAuth2 token using client_credentials grant
    token_url = f'https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token'
    token_resp = httpx.post(token_url, data={
        'grant_type': 'client_credentials',
        'client_id': client_id,
        'client_secret': client_secret,
        'scope': 'https://graph.microsoft.com/.default',
    }, timeout=15)
    if token_resp.status_code != 200:
        detail = token_resp.json().get('error_description', token_resp.text)
        logger.error('Graph token request failed: %s', detail)
        return {'success': False, 'message': f'Graph API auth failed: {detail}'}
    access_token = token_resp.json()['access_token']

    # 2. Build the sendMail payload
    mail_body: dict = {
        'message': {
            'subject': subject,
            'body': {'contentType': 'Text', 'content': body},
            'toRecipients': [{'emailAddress': {'address': recipient}}],
        },
        'saveToSentItems': 'true',
    }
    if cc:
        mail_body['message']['ccRecipients'] = [{'emailAddress': {'address': cc}}]

    # 3. Send via Graph
    send_url = f'https://graph.microsoft.com/v1.0/users/{sender_email}/sendMail'
    send_resp = httpx.post(send_url, json=mail_body, headers={
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json',
    }, timeout=15)
    if send_resp.status_code in (200, 202):
        logger.info('Email sent via Graph API to %s (CC: %s)', recipient, cc or 'none')
        return {'success': True, 'message': f'Email sent to {recipient}.'}
    detail = send_resp.text
    logger.error('Graph sendMail failed (%d): %s', send_resp.status_code, detail)
    return {'success': False, 'message': f'Graph API error ({send_resp.status_code}): {detail}'}


def _send_via_smtp(
    smtp_email: str, smtp_password: str,
    recipient: str, subject: str, body: str,
    cc: str | None = None,
) -> dict:
    """Send email via direct SMTP (works locally and on platforms that allow outbound SMTP)."""
    message = MIMEMultipart()
    message['From'] = smtp_email
    message['To'] = recipient
    message['Subject'] = subject
    recipients = [recipient]
    if cc:
        message['Cc'] = cc
        recipients.append(cc)
    message.attach(MIMEText(body, 'plain'))

    smtp_host = 'smtp.office365.com'
    smtp_port = 587
    try:
        # Resolve to IPv4 — some cloud containers are IPv6-only
        try:
            infos = socket.getaddrinfo(smtp_host, smtp_port, socket.AF_INET, socket.SOCK_STREAM)
            connect_addr = infos[0][4][0] if infos else smtp_host
        except socket.gaierror:
            connect_addr = smtp_host

        logger.info('Connecting to %s:%d (%s) as %s', connect_addr, smtp_port, smtp_host, smtp_email)
        with smtplib.SMTP(connect_addr, smtp_port, timeout=_SMTP_TIMEOUT) as server:
            server.ehlo(smtp_host)
            server.starttls()
            server.ehlo(smtp_host)
            server.login(smtp_email, smtp_password)
            server.sendmail(smtp_email, recipients, message.as_string())
        logger.info('Email sent via SMTP to %s', recipient)
        return {'success': True, 'message': f'Email sent to {recipient}.'}
    except smtplib.SMTPAuthenticationError as exc:
        logger.error('SMTP auth failed for %s: %s', smtp_email, exc)
        return {'success': False, 'message': f'SMTP authentication failed: {exc}'}
    except smtplib.SMTPException as exc:
        logger.error('SMTP error: %s', exc)
        return {'success': False, 'message': f'SMTP error: {exc}'}
    except (OSError, socket.timeout) as exc:
        logger.error('SMTP connection error: %s', exc)
        return {'success': False, 'message': f'Could not connect to SMTP server: {exc}'}


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

    subject = str(email_data['subject'])
    body = str(email_data['preview_body'])
    s = get_settings()

    # Priority 1: Resend API (simplest — one API key, HTTPS)
    if s.resend_api_key:
        logger.info('Sending via Resend API for %s → %s', major.smtp_email, recipient)
        return _send_via_resend(
            api_key=s.resend_api_key,
            sender_email=major.smtp_email,
            recipient=recipient,
            subject=subject,
            body=body,
            cc=adviser_email,
        )

    # Priority 2: Microsoft Graph API (HTTPS, needs Azure AD app)
    graph_creds = _graph_credentials()
    if graph_creds:
        logger.info('Sending via Microsoft Graph API for %s → %s', major.smtp_email, recipient)
        return _send_via_graph(
            *graph_creds,
            sender_email=major.smtp_email,
            recipient=recipient,
            subject=subject,
            body=body,
            cc=adviser_email,
        )

    # Fallback to direct SMTP
    logger.info('Graph API not configured — falling back to SMTP for %s → %s', major.smtp_email, recipient)
    return _send_via_smtp(
        smtp_email=major.smtp_email,
        smtp_password=major.smtp_password,
        recipient=recipient,
        subject=subject,
        body=body,
        cc=adviser_email,
    )
