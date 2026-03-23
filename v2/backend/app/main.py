from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import inspect as sa_inspect, text

from app.api.router import api_router
from app.core.config import get_settings
from app.db import Base, engine, SessionLocal
from app.services.bootstrap import seed_defaults

settings = get_settings()
app = FastAPI(title=settings.app_name)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)
app.include_router(api_router, prefix='/api')


@app.on_event('startup')
def on_startup() -> None:
    # Create tables first (essential for fresh databases like Neon)
    Base.metadata.create_all(bind=engine)

    # Add progress_version_id column to advising_periods if it doesn't exist yet
    existing_cols = {col['name'] for col in sa_inspect(engine).get_columns('advising_periods')}
    if 'progress_version_id' not in existing_cols:
        with engine.connect() as conn:
            conn.execute(text(
                'ALTER TABLE advising_periods '
                'ADD COLUMN progress_version_id INTEGER '
                'REFERENCES dataset_versions(id)'
            ))
            conn.commit()

    # Add per-major SMTP columns if they don't exist yet
    major_cols = {col['name'] for col in sa_inspect(engine).get_columns('majors')}
    with engine.connect() as conn:
        if 'smtp_email' not in major_cols:
            conn.execute(text('ALTER TABLE majors ADD COLUMN smtp_email VARCHAR(255)'))
        if 'smtp_password' not in major_cols:
            conn.execute(text('ALTER TABLE majors ADD COLUMN smtp_password VARCHAR(255)'))
        conn.commit()

    session = SessionLocal()
    try:
        seed_defaults(session)
    finally:
        session.close()
