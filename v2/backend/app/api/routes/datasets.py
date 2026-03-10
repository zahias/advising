from __future__ import annotations

from io import BytesIO

pandas_imported = False
try:
    import pandas as pd
    pandas_imported = True
except ImportError:
    pass

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import Response, StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import ensure_major_access, get_db, require_admin, require_staff
from app.models import DatasetVersion, User
from app.schemas.admin import DatasetVersionResponse
from app.services.audit import log_event
from app.services.dataset_service import get_active_dataset, upload_dataset
from app.services.storage import StorageService

_TEMPLATE_COLUMNS: dict[str, dict[str, list[str]]] = {
    'courses': {
        'Courses': ['Course Code', 'Course Title', 'Credits', 'Course Type', 'Semester Offered', 'Prerequisites', 'Corequisites'],
    },
    'progress': {
        'Required Courses': ['ID', 'NAME'],
        'Intensive Courses': ['ID', 'NAME'],
    },
    'email_roster': {
        'Email Roster': ['Student ID', 'Student Name', 'Email'],
    },
}

router = APIRouter(prefix='/datasets', tags=['datasets'])


@router.get('/{major_code}', response_model=list[DatasetVersionResponse])
def list_dataset_versions(major_code: str, user: User = Depends(require_staff), db: Session = Depends(get_db)) -> list[DatasetVersion]:
    ensure_major_access(major_code, db, user)
    return list(
        db.scalars(
            select(DatasetVersion).where(DatasetVersion.major.has(code=major_code)).order_by(DatasetVersion.created_at.desc())
        )
    )


@router.get('/templates/{dataset_type}')
def download_template(dataset_type: str, user: User = Depends(require_staff)) -> Response:
    """Download a blank XLSX template for the given dataset type."""
    sheets = _TEMPLATE_COLUMNS.get(dataset_type)
    if not sheets:
        raise HTTPException(status_code=400, detail=f'No template available for dataset type: {dataset_type}')
    import pandas as pd
    buf = BytesIO()
    with pd.ExcelWriter(buf, engine='openpyxl') as writer:
        for sheet_name, columns in sheets.items():
            pd.DataFrame(columns=columns).to_excel(writer, sheet_name=sheet_name, index=False)
    buf.seek(0)
    filename = f'{dataset_type}_template.xlsx'
    return Response(
        content=buf.read(),
        media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        headers={'Content-Disposition': f'attachment; filename="{filename}"'},
    )


@router.get('/{major_code}/{dataset_type}/download')
def download_current_file(major_code: str, dataset_type: str, user: User = Depends(require_staff), db: Session = Depends(get_db)) -> StreamingResponse:
    """Download the currently active uploaded file for a dataset type."""
    ensure_major_access(major_code, db, user)
    version = get_active_dataset(db, major_code, dataset_type)
    if not version:
        raise HTTPException(status_code=404, detail='No active file for this dataset type.')
    storage = StorageService()
    content = storage.get_bytes(version.storage_key)
    filename = version.original_filename or f'{dataset_type}.xlsx'
    media_type = 'text/csv' if filename.lower().endswith('.csv') else 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    return StreamingResponse(
        iter([content]),
        media_type=media_type,
        headers={'Content-Disposition': f'attachment; filename="{filename}"'},
    )


@router.delete('/{version_id}', status_code=204)
def delete_dataset_version(version_id: int, user: User = Depends(require_admin), db: Session = Depends(get_db)):
    version = db.get(DatasetVersion, version_id)
    if not version:
        raise HTTPException(status_code=404, detail='Dataset version not found.')
    if version.is_active:
        raise HTTPException(status_code=400, detail='Cannot delete the active version. Activate another version first.')
    log_event(db, user.id, 'dataset.deleted', 'dataset_version', str(version_id), {'dataset_type': version.dataset_type})
    db.delete(version)
    db.commit()


@router.post('/{version_id}/activate', response_model=DatasetVersionResponse)
def activate_dataset_version(version_id: int, user: User = Depends(require_admin), db: Session = Depends(get_db)):
    from sqlalchemy import update
    version = db.get(DatasetVersion, version_id)
    if not version:
        raise HTTPException(status_code=404, detail='Dataset version not found.')
    # Deactivate all versions of same type for same major
    db.execute(
        update(DatasetVersion)
        .where(DatasetVersion.major_id == version.major_id, DatasetVersion.dataset_type == version.dataset_type)
        .values(is_active=False)
    )
    version.is_active = True
    log_event(db, user.id, 'dataset.activated', 'dataset_version', str(version_id), {'dataset_type': version.dataset_type})
    db.commit()
    db.refresh(version)
    return version


@router.post('/upload', response_model=DatasetVersionResponse)
async def upload_dataset_route(
    major_code: str = Form(...),
    dataset_type: str = Form(...),
    file: UploadFile = File(...),
    user: User = Depends(require_staff),
    db: Session = Depends(get_db),
) -> DatasetVersion:
    try:
        version = upload_dataset(
            db,
            major_code=major_code,
            dataset_type=dataset_type,
            filename=file.filename,
            content=await file.read(),
            user_id=user.id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    # Store uploader info in metadata so it surfaces in the version list
    version.metadata_json = {**version.metadata_json, 'uploaded_by': user.full_name or user.email}
    log_event(db, user.id, 'dataset.uploaded', 'dataset_version', str(version.id), {'major_code': major_code, 'dataset_type': dataset_type})
    db.commit()
    db.refresh(version)
    return version
