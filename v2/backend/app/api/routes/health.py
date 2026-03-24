from __future__ import annotations

import sys
from pathlib import Path

from fastapi import APIRouter

from app.core.config import get_settings

router = APIRouter(prefix='/health', tags=['health'])


@router.get('')
def health_check():
    s = get_settings()
    # Check if legacy modules are reachable
    root_dir = Path(__file__).resolve().parents[4]
    legacy_ok = (root_dir / 'eligibility_utils.py').exists()
    return {
        'status': 'ok',
        'cors_origins': s.cors_origins,
        'db_driver': 'postgresql' if 'postgresql' in s.database_url else 'sqlite',
        'root_dir': str(root_dir),
        'legacy_modules_found': legacy_ok,
        'cwd': str(Path.cwd()),
    }
