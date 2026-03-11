"""Seed script — wipes all data and inserts a fresh baseline dataset.

Hierarchy:
  super admin  (is_admin=True,  parent_id=NULL)
  └── company  (is_admin=True,  parent_id=super_admin.id)
       └── sub-user  (is_admin=False, parent_id=company.id)
            └── cases

Run via:  make seed
"""

import asyncio
import hashlib
import io
import random
from datetime import datetime, timezone

from dotenv import load_dotenv
from faker import Faker
from sqlalchemy import text
from sqlalchemy.orm import Session
from uuid_extensions import uuid7

load_dotenv()

from src.api.db.database import SessionLocal, create_tables  # noqa: E402
from src.api.v1.case.models import CaseDB  # noqa: E402
from src.api.v1.case.storage import BUCKET, _client, ensure_bucket  # noqa: E402
from src.api.v1.company.models import CompanyDB  # noqa: E402
from src.api.v1.user.models import UserDB  # noqa: E402

fake = Faker()
STATUSES = ["open", "pending", "in_progress", "closed"]


def _hash(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def _add_user(
    db: Session,
    *,
    username: str,
    email: str,
    full_name: str,
    password: str,
    is_admin: bool,
    parent_id: str | None,
) -> str:
    uid = str(uuid7())
    db.add(
        UserDB(
            id=uid,
            username=username,
            email=email,
            full_name=full_name,
            password=_hash(password),
            is_active=True,
            is_admin=is_admin,
            parent_id=parent_id,
        ),
    )
    db.flush()
    return uid


_DOC_TEMPLATES = [
    (
        "report.txt",
        lambda: (
            f"Case Report\n===========\n\n{fake.paragraph(nb_sentences=6)}\n\nFindings:\n{fake.paragraph(nb_sentences=4)}\n\nConclusion:\n{fake.paragraph(nb_sentences=3)}\n"  # noqa: E501
        ),
    ),
    (
        "notes.txt",
        lambda: (
            f"Internal Notes\n==============\n\n{fake.paragraph(nb_sentences=5)}\n\n- {fake.sentence()}\n- {fake.sentence()}\n- {fake.sentence()}\n"  # noqa: E501
        ),
    ),
    (
        "invoice.txt",
        lambda: (
            f"INVOICE\n=======\nDate: {fake.date()}\nRef:  INV-{fake.numerify('####')}\n\nDescription: {fake.bs()}\nAmount:      ${random.randint(500, 50000):,}.00\n\nNotes:\n{fake.paragraph(nb_sentences=2)}\n"  # noqa: E501
        ),
    ),
    (
        "contract.txt",
        lambda: (
            f"CONTRACT SUMMARY\n================\nParty A: {fake.company()}\nParty B: {fake.company()}\nDate:    {fake.date()}\n\nTerms:\n{fake.paragraph(nb_sentences=5)}\n\nSignatures pending.\n"  # noqa: E501
        ),
    ),
    (
        "evidence.txt",
        lambda: (
            f"Evidence Log\n============\nLogged: {fake.date_time().isoformat()}\nSource: {fake.url()}\n\n{fake.paragraph(nb_sentences=4)}\n"  # noqa: E501
        ),
    ),
]


def _upload_case_docs(case_ids: list[str]) -> int:
    """Upload 1-3 sample documents to MinIO for each case. Returns total uploaded."""
    total = 0
    for case_id in case_ids:
        docs = random.sample(_DOC_TEMPLATES, k=random.randint(1, 3))
        for filename, content_fn in docs:
            data = content_fn().encode()
            _client.put_object(
                BUCKET,
                f"cases/{case_id}/{filename}",
                io.BytesIO(data),
                length=len(data),
                content_type="text/plain",
            )
            total += 1
    return total


def _add_company(
    db: Session,
    *,
    name: str,
    email: str | None = None,
    phone: str | None = None,
    address: str | None = None,
    owner_id: str | None = None,
) -> str:
    cid = str(uuid7())
    db.add(
        CompanyDB(
            id=cid,
            name=name,
            email=email,
            phone=phone,
            address=address,
            owner_id=owner_id,
            created_at=datetime.now(timezone.utc),
        ),
    )
    db.flush()
    return cid


def _add_cases(db: Session, *, user_ids: list[str], n_companies: int = 5, company_ids: list[str]) -> list[str]:
    customers = [fake.company() for _ in range(n_companies)]
    case_pool = []
    for customer in customers:
        for _ in range(random.randint(10, 15)):
            case_pool.append(customer)
    random.shuffle(case_pool)

    # Collect sub-user full names for responsible_person
    from src.api.v1.user.models import UserDB as _UserDB  # local import to avoid circular

    names = [db.query(_UserDB).filter(_UserDB.id == uid).first().full_name for uid in user_ids]

    case_ids = []
    for customer in case_pool:
        cid = str(uuid7())
        case_ids.append(cid)
        db.add(
            CaseDB(
                id=cid,
                customer=customer,
                status=random.choice(STATUSES),
                responsible_person=random.choice(names),
                created_at=datetime.now(timezone.utc),
                user_id=random.choice(user_ids),
                company_id=random.choice(company_ids),
            ),
        )
    return case_ids


def _make_sub_users(db: Session, *, domain: str, parent_id: str, n: int = 5) -> list[str]:
    user_ids = []
    for _ in range(n):
        first = fake.first_name()
        last = fake.last_name()
        username = f"{first.lower()}.{last.lower()}{random.randint(1, 99)}"
        user_ids.append(
            _add_user(
                db,
                username=username,
                email=f"{username}@{domain}",
                full_name=f"{first} {last}",
                password=f"{username}123",
                is_admin=False,
                parent_id=parent_id,
            ),
        )
    return user_ids


def run() -> None:
    """Drop all rows and insert seed data."""
    create_tables()
    db = SessionLocal()

    try:
        # Schema migration: add column as nullable first (so existing rows don't fail)
        db.execute(
            text(
                "ALTER TABLE cases ADD COLUMN IF NOT EXISTS "
                "company_id UUID REFERENCES companies(id) ON DELETE SET NULL",
            ),
        )
        # Wipe all data so we can enforce NOT NULL safely
        db.execute(text("TRUNCATE TABLE companies, cases, users RESTART IDENTITY CASCADE"))
        # Now enforce NOT NULL (table is empty)
        db.execute(text("ALTER TABLE cases ALTER COLUMN company_id SET NOT NULL"))
        db.commit()

        # ── Level 0: Super admin ─────────────────────────────────────────────
        super_id = _add_user(
            db,
            username="superadmin",
            email="superadmin@kanapi.dev",
            full_name="Platform Admin",
            password="super123",
            is_admin=True,
            parent_id=None,
        )

        # ── Level 1: Companies ───────────────────────────────────────────────
        acme_id = _add_user(
            db,
            username="acme",
            email="admin@acme.dev",
            full_name="Acme Inc.",
            password="acme123",
            is_admin=True,
            parent_id=super_id,
        )

        globex_id = _add_user(
            db,
            username="globex",
            email="admin@globex.dev",
            full_name="Globex Corp.",
            password="globex123",
            is_admin=True,
            parent_id=super_id,
        )

        # ── Level 2: Sub-users (5 per company, Faker-generated) ──────────────
        acme_users = _make_sub_users(db, domain="acme.dev", parent_id=acme_id)
        globex_users = _make_sub_users(db, domain="globex.dev", parent_id=globex_id)

        # ── Static test user (non-admin, under Acme) ──────────────────────────
        test_user_id = _add_user(
            db,
            username="testuser",
            email="test@acme.dev",
            full_name="Test User",
            password="test123",
            is_admin=False,
            parent_id=acme_id,
        )

        # ── Companies (proper CompanyDB entities) ─────────────────────────────
        # Owner-level companies
        acme_co_id = _add_company(
            db,
            name="Acme Inc.",
            email="contact@acme.dev",
            phone="+1-800-226-3000",
            address="123 Main St, Springfield",
        )
        globex_co_id = _add_company(
            db,
            name="Globex Corp.",
            email="info@globex.dev",
            phone="+1-800-456-7890",
            address="1 Industrial Ave, Shelbyville",
        )
        # Client companies owned by Acme
        acme_client1_id = _add_company(db, name="Springfield Legal", email="legal@springfield.dev", owner_id=acme_co_id)
        acme_client2_id = _add_company(db, name="Burns & Associates", email="burns@associates.dev", owner_id=acme_co_id)
        # Client companies owned by Globex
        globex_client1_id = _add_company(
            db,
            name="Shelbyville Partners",
            email="partners@shelbyville.dev",
            owner_id=globex_co_id,
        )

        # ── Cases ────────────────────────────────────────────────────────────
        acme_case_ids = _add_cases(db, user_ids=acme_users + [test_user_id], company_ids=[acme_client1_id, acme_client2_id])
        globex_case_ids = _add_cases(db, user_ids=globex_users, company_ids=[globex_client1_id])

        db.commit()

        # ── MinIO documents ──────────────────────────────────────────────────
        ensure_bucket()
        acme_docs = _upload_case_docs(acme_case_ids)
        globex_docs = _upload_case_docs(globex_case_ids)

        # ── FGA tuples ───────────────────────────────────────────────────────
        admin_company_pairs = [
            (acme_id, acme_client1_id),
            (acme_id, acme_client2_id),
            (globex_id, globex_client1_id),
        ]
        asyncio.run(_seed_fga_tuples(db, admin_company_pairs))

        print("Seed complete.")
        print()
        print("  superadmin@kanapi.dev  / super123   (super admin)")
        print("  → 5 companies (Acme Inc., Globex Corp. + 3 clients)")
        print()
        print("  admin@acme.dev         / acme123    (company admin)")
        print(f"  → {len(acme_users)} sub-users, {len(acme_case_ids)} cases, {acme_docs} documents")
        print()
        print("  admin@globex.dev       / globex123  (company admin)")
        print(f"  → {len(globex_users)} sub-users, {len(globex_case_ids)} cases, {globex_docs} documents")
        print()
        print("  test@acme.dev          / test123    (regular user, under Acme)")

    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


async def _seed_fga_tuples(db: Session, admin_company_pairs: list[tuple[str, str]]) -> None:
    """Write FGA tuples for all seeded cases and admin-company relationships."""
    from openfga_sdk.client.models import ClientTuple, ClientWriteRequest

    from src.api.v1.auth.fga import get_fga_client

    client = await get_fga_client()

    tuples: list[ClientTuple] = []
    for case in db.query(CaseDB).all():
        tuples.append(ClientTuple(user=f'user:{case.user_id}', relation='creator', object=f'case:{case.id}'))
        tuples.append(ClientTuple(user=f'company:{case.company_id}', relation='company', object=f'case:{case.id}'))
    for admin_id, company_id in admin_company_pairs:
        tuples.append(ClientTuple(user=f'user:{admin_id}', relation='admin', object=f'company:{company_id}'))

    # FGA accepts up to 10 tuples per write request
    chunk_size = 10
    for i in range(0, len(tuples), chunk_size):
        try:
            await client.write(ClientWriteRequest(writes=tuples[i:i + chunk_size]))
        except Exception as e:
            print(f'  FGA write warning (chunk {i // chunk_size}): {e}')

    await client.close()
    n_cases = len(tuples) - len(admin_company_pairs)
    n_admin = len(admin_company_pairs)
    print(f'  FGA: wrote tuples for {n_cases} cases + {n_admin} admin-company relations')


if __name__ == "__main__":
    run()
