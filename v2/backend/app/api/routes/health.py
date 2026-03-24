from __future__ import annotations

from fastapi import APIRouter

from app.core.config import get_settings

router = APIRouter(prefix='/health', tags=['health'])


@router.get('')
def health_check():
    s = get_settings()
    return {
        'status': 'ok',
        'cors_origins': s.cors_origins,
        'db_driver': 'postgresql' if 'postgresql' in s.database_url else 'sqlite',
    }
