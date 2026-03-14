"""Major code mapping configuration — maps MAJOR column values in progress files to DB majors."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_admin
from app.models import Major, MajorCodeMapping, User
from app.schemas.advising import MajorCodeMappingCreate, MajorCodeMappingResponse, MajorCodeMappingUpdate

router = APIRouter(prefix='/major-mappings', tags=['major-mappings'])


def _to_response(m: MajorCodeMapping) -> MajorCodeMappingResponse:
    return MajorCodeMappingResponse(
        id=m.id,
        file_code=m.file_code,
        major_id=m.major_id,
        major_code=m.major.code,
        major_name=m.major.name,
        id_year_min=m.id_year_min,
        id_year_max=m.id_year_max,
    )


@router.get('', response_model=list[MajorCodeMappingResponse])
def list_mappings(
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> list[MajorCodeMappingResponse]:
    """List all major code mappings ordered by file_code."""
    rows = db.scalars(
        select(MajorCodeMapping).order_by(MajorCodeMapping.file_code, MajorCodeMapping.id)
    ).all()
    return [_to_response(r) for r in rows]


@router.post('', response_model=MajorCodeMappingResponse, status_code=201)
def create_mapping(
    body: MajorCodeMappingCreate,
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> MajorCodeMappingResponse:
    """Create a new major code mapping rule."""
    major = db.scalar(select(Major).where(Major.id == body.major_id))
    if not major:
        raise HTTPException(status_code=404, detail=f'Major id={body.major_id} not found.')

    mapping = MajorCodeMapping(
        file_code=body.file_code.strip().upper(),
        major_id=body.major_id,
        id_year_min=body.id_year_min,
        id_year_max=body.id_year_max,
    )
    db.add(mapping)
    db.commit()
    db.refresh(mapping)
    return _to_response(mapping)


@router.put('/{mapping_id}', response_model=MajorCodeMappingResponse)
def update_mapping(
    mapping_id: int,
    body: MajorCodeMappingUpdate,
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> MajorCodeMappingResponse:
    """Update an existing major code mapping rule."""
    mapping = db.get(MajorCodeMapping, mapping_id)
    if not mapping:
        raise HTTPException(status_code=404, detail=f'Mapping id={mapping_id} not found.')

    major = db.scalar(select(Major).where(Major.id == body.major_id))
    if not major:
        raise HTTPException(status_code=404, detail=f'Major id={body.major_id} not found.')

    mapping.file_code = body.file_code.strip().upper()
    mapping.major_id = body.major_id
    mapping.id_year_min = body.id_year_min
    mapping.id_year_max = body.id_year_max
    db.commit()
    db.refresh(mapping)
    return _to_response(mapping)


@router.delete('/{mapping_id}', status_code=204)
def delete_mapping(
    mapping_id: int,
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> Response:
    """Delete a major code mapping rule."""
    mapping = db.get(MajorCodeMapping, mapping_id)
    if mapping:
        db.delete(mapping)
        db.commit()
    return Response(status_code=204)
