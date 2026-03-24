from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import get_settings

settings = get_settings()

# Neon / Render provide postgresql:// URLs; SQLAlchemy needs the +psycopg driver
# suffix to use the installed psycopg v3 (not the legacy psycopg2).
_url = settings.database_url
if _url.startswith('postgresql://'):
    _url = _url.replace('postgresql://', 'postgresql+psycopg://', 1)

connect_args = {'check_same_thread': False} if _url.startswith('sqlite') else {}
engine = create_engine(_url, future=True, pool_pre_ping=True, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


class Base(DeclarativeBase):
    pass
