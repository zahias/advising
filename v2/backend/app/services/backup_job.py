from __future__ import annotations

import gzip
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db import SessionLocal
from app.models import BackupRun
from app.services.storage import StorageService


def _count_storage_files(local_root: Path) -> dict[str, int]:
    """Return a compact count of stored files per category folder."""
    counts: dict[str, int] = {}
    if local_root.exists():
        for child in local_root.iterdir():
            if child.is_dir():
                counts[child.name] = sum(1 for _ in child.rglob('*') if _.is_file())
    return counts


def run_backup(triggered_by: str = 'scheduled') -> BackupRun:
    settings = get_settings()
    storage = StorageService()
    timestamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    dump_path = Path('/tmp') / f'advising-v2-{timestamp}.sql.gz'
    database_url = settings.database_url
    with dump_path.open('wb') as handle:
        proc = subprocess.run(['pg_dump', database_url], check=True, capture_output=True)
        handle.write(gzip.compress(proc.stdout))
    key = f'backups/{timestamp}/database.sql.gz'
    storage.put_bytes(key, dump_path.read_bytes(), 'application/gzip')
    storage_counts = _count_storage_files(storage.local_root)
    session: Session = SessionLocal()
    try:
        run = BackupRun(
            status='completed',
            storage_key=key,
            manifest={
                'timestamp': timestamp,
                'triggered_by': triggered_by,
                'storage_file_counts': storage_counts,
            },
            notes=f'Backup triggered by {triggered_by}',
        )
        session.add(run)
        session.commit()
        session.refresh(run)
        return run
    finally:
        session.close()


if __name__ == '__main__':
    run = run_backup()
    print(json.dumps({'backup_run_id': run.id, 'storage_key': run.storage_key}))
