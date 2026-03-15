"""Tests for case activity log — db_log_activity and db_get_case_activities."""

import time
import uuid
from datetime import datetime, timezone

from src.api.v1.case.models import CaseActivityDB, CaseDB, db_get_case_activities, db_log_activity
from src.api.v1.company.models import CompanyDB
from src.api.v1.user.models import UserDB

# ─── Helpers ──────────────────────────────────────────────────────────────────


def _make_user(db, username="actor"):  # noqa ANN001
    db.add(UserDB(username=username, email=f"{username}@test.dev", password="x", is_active=True, is_admin=False))
    db.flush()
    return username


def _make_company(db):  # noqa ANN001
    cid = str(uuid.uuid4())
    db.add(CompanyDB(id=cid, name="Test Co", created_at=datetime.now(timezone.utc)))
    db.flush()
    return cid


def _make_case(db, company_id, user_id):  # noqa ANN001
    case_id = str(uuid.uuid4())
    db.add(CaseDB(
        id=case_id,
        responsible_person="Tester",
        status="open",
        customer="Acme",
        company_id=company_id,
        created_at=datetime.now(timezone.utc),
        user_id=user_id,
    ))
    db.flush()
    return case_id


# ─── db_log_activity ──────────────────────────────────────────────────────────


def test_log_activity_creates_row(db):  # noqa ANN001
    """db_log_activity inserts a row and db_get_case_activities returns it."""
    user_id = _make_user(db)
    company_id = _make_company(db)
    case_id = _make_case(db, company_id, user_id)

    db_log_activity(db, case_id, user_id, 'case_created')

    entries = db_get_case_activities(db, case_id)
    assert len(entries) == 1
    assert entries[0].case_id == case_id
    assert entries[0].action == 'case_created'
    assert entries[0].user_id == user_id
    assert entries[0].detail is None


def test_log_activity_stores_detail(db):  # noqa ANN001
    """Detail string is persisted and returned unchanged."""
    user_id = _make_user(db)
    company_id = _make_company(db)
    case_id = _make_case(db, company_id, user_id)

    db_log_activity(db, case_id, user_id, 'status_changed', 'open → closed')

    entries = db_get_case_activities(db, case_id)
    assert entries[0].detail == 'open → closed'


def test_log_activity_null_user_allowed(db):  # noqa ANN001
    """user_id may be None (e.g. system-generated events)."""
    user_id = _make_user(db)
    company_id = _make_company(db)
    case_id = _make_case(db, company_id, user_id)

    db_log_activity(db, case_id, None, 'document_uploaded', 'report.pdf')

    entries = db_get_case_activities(db, case_id)
    assert entries[0].user_id is None
    assert entries[0].detail == 'report.pdf'


# ─── db_get_case_activities ───────────────────────────────────────────────────


def test_get_activities_empty_for_new_case(db):  # noqa ANN001
    """Returns an empty list when no activity has been logged."""
    user_id = _make_user(db)
    company_id = _make_company(db)
    case_id = _make_case(db, company_id, user_id)

    assert db_get_case_activities(db, case_id) == []


def test_get_activities_returns_oldest_first(db):  # noqa ANN001
    """Multiple entries are returned in ascending created_at order."""
    user_id = _make_user(db)
    company_id = _make_company(db)
    case_id = _make_case(db, company_id, user_id)

    db_log_activity(db, case_id, user_id, 'case_created')
    time.sleep(0.01)
    db_log_activity(db, case_id, user_id, 'status_changed', 'open → pending')
    time.sleep(0.01)
    db_log_activity(db, case_id, user_id, 'status_changed', 'pending → closed')

    entries = db_get_case_activities(db, case_id)
    assert len(entries) == 3
    assert entries[0].action == 'case_created'
    assert entries[1].detail == 'open → pending'
    assert entries[2].detail == 'pending → closed'
    assert entries[0].created_at <= entries[1].created_at <= entries[2].created_at


def test_get_activities_scoped_to_case(db):  # noqa ANN001
    """Activity from one case does not appear in another case's log."""
    user_id = _make_user(db)
    company_id = _make_company(db)
    case_a = _make_case(db, company_id, user_id)
    case_b = _make_case(db, company_id, user_id)

    db_log_activity(db, case_a, user_id, 'case_created')

    assert db_get_case_activities(db, case_b) == []


def test_activity_cascade_deleted_with_case(db):  # noqa ANN001
    """Deleting a case removes its activity rows (CASCADE)."""
    user_id = _make_user(db)
    company_id = _make_company(db)
    case_id = _make_case(db, company_id, user_id)

    db_log_activity(db, case_id, user_id, 'case_created')
    assert len(db_get_case_activities(db, case_id)) == 1

    # Delete the case directly via ORM to trigger CASCADE
    row = db.query(CaseDB).filter(CaseDB.id == case_id).first()
    db.delete(row)
    db.commit()

    remaining = db.query(CaseActivityDB).filter(CaseActivityDB.case_id == case_id).all()
    assert remaining == []
