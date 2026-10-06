from __future__ import annotations

import io
from types import SimpleNamespace

import pandas as pd
import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

import app.services.dataset_service as dataset_service
import app.services.student_service as student_service
from app.db import Base
from app.models import CourseExclusion, Major
from app.services.placement_service import (
    bulk_placement_from_file,
    normalize_student_id,
    save_manual_placement,
)

COURSES = pd.DataFrame([
    {'Course Code': 'ARAB101', 'Title': 'Arabic I', 'Type': 'Intensive', 'Prerequisite': '', 'Offered': 'Yes', 'Credits': 3},
    {'Course Code': 'ARAB201', 'Title': 'Arabic II', 'Type': 'Intensive', 'Prerequisite': 'ARAB101', 'Offered': 'Yes', 'Credits': 3},
    {'Course Code': 'ARAB301', 'Title': 'Arabic III', 'Type': 'Intensive', 'Prerequisite': 'ARAB201', 'Offered': 'Yes', 'Credits': 3},
    {'Course Code': 'ENGL100', 'Title': 'English I', 'Type': 'Intensive', 'Prerequisite': '', 'Offered': 'Yes', 'Credits': 3},
    {'Course Code': 'BIOL201', 'Title': 'Biology', 'Type': 'Required', 'Prerequisite': '', 'Offered': 'Yes', 'Credits': 3},
])

PROGRESS = pd.DataFrame([
    {'ID': '1001', 'NAME': 'Alice', '# of Credits Completed': 30, '# Registered': 0,
     'ARAB101': 'nc', 'ARAB201': 'nc', 'ARAB301': 'nc', 'ENGL100': 'nc', 'BIOL201': 'nc'},
    {'ID': '1002', 'NAME': 'Bob', '# of Credits Completed': 30, '# Registered': 0,
     'ARAB101': 'nc', 'ARAB201': 'nc', 'ARAB301': 'nc', 'ENGL100': 'nc', 'BIOL201': 'nc'},
])


@pytest.fixture()
def db(monkeypatch):
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    session.add(Major(code='TEST', name='Test'))
    session.commit()

    frames = {'courses': COURSES, 'progress': PROGRESS}
    fake = lambda _s, _m, kind: frames.get(kind, pd.DataFrame()).copy()  # noqa: E731
    monkeypatch.setattr(dataset_service, 'dataset_dataframe', fake)
    monkeypatch.setattr(student_service, 'dataset_dataframe', fake)
    monkeypatch.setattr(student_service, 'current_period', lambda _s, _m: SimpleNamespace(id=1))
    yield session
    session.close()


def _xlsx(rows: list[dict]) -> bytes:
    buf = io.BytesIO()
    pd.DataFrame(rows).to_excel(buf, index=False)
    return buf.getvalue()


def _exclusions(session, student_id: str) -> set[str]:
    return {r.course_code for r in session.scalars(select(CourseExclusion).where(CourseExclusion.student_id == student_id))}


def test_normalize_student_id_handles_excel_floats():
    assert normalize_student_id(202012345.0) == '202012345'
    assert normalize_student_id('202012345.0') == '202012345'
    assert normalize_student_id(float('nan')) == ''
    assert normalize_student_id(' 42 ') == '42'


def test_bulk_upload_with_blank_cells_uses_clean_ids(db):
    # The blank row makes Excel/pandas read the ID column as floats
    content = _xlsx([
        {'ID': 1001, 'placement_course': 'arab201'},
        {'ID': None, 'placement_course': None},
        {'ID': 9999, 'placement_course': 'ARAB101'},
    ])
    result = bulk_placement_from_file(db, 'TEST', content)

    assert result['processed'] == 1
    assert any('9999' in e for e in result['errors'])
    assert _exclusions(db, '1001') == {'ARAB101', 'ENGL100'}
    assert _exclusions(db, '1001.0') == set()


def test_bulk_upload_preserves_non_intensive_exclusions(db):
    db.add(CourseExclusion(major_id=1, student_id='1001', course_code='BIOL201'))
    db.commit()
    bulk_placement_from_file(db, 'TEST', _xlsx([{'ID': '1001', 'course': 'ARAB301'}]))
    assert _exclusions(db, '1001') == {'BIOL201', 'ARAB101', 'ARAB201', 'ENGL100'}


def test_bulk_upload_skips_manual_placements_unless_overwrite(db):
    save_manual_placement(db, 'TEST', '1001', ['ARAB101'])
    content = _xlsx([{'ID': '1001', 'course': 'ARAB301'}])

    result = bulk_placement_from_file(db, 'TEST', content)
    assert result['skipped_manual'] == ['1001']
    assert _exclusions(db, '1001') == {'ARAB101'}

    result = bulk_placement_from_file(db, 'TEST', content, overwrite_manual=True)
    assert result['processed'] == 1
    assert _exclusions(db, '1001') == {'ARAB101', 'ARAB201', 'ENGL100'}


def test_eligibility_treats_placed_out_courses_as_satisfied(db):
    bulk_placement_from_file(db, 'TEST', _xlsx([{'ID': '1001', 'course': 'ARAB201'}]))
    resp = student_service.student_eligibility(db, 'TEST', '1001')

    by_code = {c.course_code: c for c in resp.eligibility}
    assert 'ARAB101' not in by_code and 'ENGL100' not in by_code
    assert by_code['ARAB201'].eligibility_status == 'Eligible'
    assert 'placement' in by_code['ARAB201'].justification
    assert by_code['ARAB301'].eligibility_status == 'Not Eligible'

    placement = {c.course_code: c for c in resp.intensive_placement}
    assert set(placement) == {'ARAB101', 'ARAB201', 'ARAB301', 'ENGL100'}
    assert placement['ARAB101'].excluded and placement['ARAB101'].placed_out
    assert placement['ENGL100'].excluded and not placement['ENGL100'].placed_out
    assert not placement['ARAB201'].excluded
    assert resp.placement.source == 'upload'
    assert resp.placement.placement_courses == ['ARAB201']


def test_manual_placement_can_reactivate_a_course(db):
    bulk_placement_from_file(db, 'TEST', _xlsx([{'ID': '1001', 'course': 'ARAB201'}]))
    save_manual_placement(db, 'TEST', '1001', [])
    resp = student_service.student_eligibility(db, 'TEST', '1001')

    assert {'ARAB101', 'ENGL100'} <= {c.course_code for c in resp.eligibility}
    assert resp.placement.source == 'manual'
    assert resp.placement.placement_courses == ['ARAB101', 'ENGL100']


def test_manual_placement_rejects_non_intensive_course(db):
    with pytest.raises(ValueError):
        save_manual_placement(db, 'TEST', '1001', ['BIOL201'])
