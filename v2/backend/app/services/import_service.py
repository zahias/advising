from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from sqlalchemy.orm import Session

from app.models import BackupRun, EmailRosterEntry, Major
from app.services.dataset_service import upload_dataset
from app.services.storage import StorageService


LEGACY_DEFAULTS = {
    'courses': 'courses_table.xlsx',
    'progress': 'progress_report.xlsx',
    'email_roster': 'email_roster.json',
}


def import_legacy_snapshot(session: Session, *, major_code: str, import_root: str, user_id: Optional[int]) -> dict:
    root = Path(import_root)
    major_root = root / major_code
    if not major_root.exists():
        raise ValueError(f'Legacy folder not found: {major_root}')
    major = session.query(Major).filter(Major.code == major_code).one_or_none()
    if not major:
        raise ValueError(f'Unknown major: {major_code}')
    storage = StorageService()
    imported: dict[str, str] = {}
    archive_manifest: dict[str, str] = {}
    for dataset_type, filename in LEGACY_DEFAULTS.items():
        path = major_root / filename
        if not path.exists():
            continue
        file_bytes = path.read_bytes()
        archive_key = f'legacy-imports/{major_code}/{filename}'
        storage.put_bytes(archive_key, file_bytes)
        archive_manifest[dataset_type] = archive_key
        if dataset_type == 'email_roster' and filename.endswith('.json'):
            payload = json.loads(file_bytes.decode('utf-8'))
            session.query(EmailRosterEntry).filter(EmailRosterEntry.major_id == major.id).delete()
            for student_id, email in payload.items():
                if not student_id or not email:
                    continue
                session.add(
                    EmailRosterEntry(
                        major_id=major.id,
                        student_id=str(student_id),
                        student_name=None,
                        email=str(email).strip().lower(),
                    )
                )
            imported[dataset_type] = filename
            continue
        upload_dataset(session, major_code=major_code, dataset_type=dataset_type, filename=filename, content=file_bytes, user_id=user_id)
        imported[dataset_type] = filename
    backup = BackupRun(status='completed', storage_key=None, manifest={'major_code': major_code, 'archive_manifest': archive_manifest, 'imported': imported}, notes='Legacy snapshot imported')
    session.add(backup)
    session.commit()
    return {'major_code': major_code, 'imported': imported, 'archive_manifest': archive_manifest}
