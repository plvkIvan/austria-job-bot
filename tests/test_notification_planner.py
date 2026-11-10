"""Tests for preparing (not sending) job notifications."""
from datetime import datetime, timezone
from types import SimpleNamespace

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.db.models import Base, Delivery, Job, User
from app.services import notification_planner


def test_only_matching_consenting_users_and_no_duplicates(monkeypatch):
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    try:
        with Session(engine) as db:
            consenting = User(
                phone="user-1", query="Lagerarbeiter", city="Wien",
                notifications_enabled=True,
                consent_at=datetime.now(timezone.utc),
            )
            not_consenting = User(
                phone="user-2", query="Lagerarbeiter", city="Wien",
                notifications_enabled=False,
            )
            wrong_city = User(
                phone="user-3", query="Lagerarbeiter", city="Graz",
                notifications_enabled=True,
                consent_at=datetime.now(timezone.utc),
            )
            job = Job(
                source="demo", external_id="abc", title="Lagerarbeiter",
                city="Wien", url="https://example.com/job/abc",
            )
            db.add_all([consenting, not_consenting, wrong_city, job])
            db.commit()

            monkeypatch.setattr(
                notification_planner, "evaluate_match",
                lambda user, vacancy: SimpleNamespace(
                    should_notify=(user.city == vacancy.city and user.query == vacancy.title)
                ),
            )

            assert notification_planner.plan_for_new_jobs(db, [job.id]) == 1
            db.commit()
            assert notification_planner.plan_for_new_jobs(db, [job.id, job.id]) == 0
            db.commit()
            deliveries = db.scalars(select(Delivery)).all()
            assert len(deliveries) == 1
            assert deliveries[0].user_id == consenting.id
            assert deliveries[0].job_id == job.id
            assert deliveries[0].status == "pending"
    finally:
        engine.dispose()


def test_empty_job_list_does_nothing():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    try:
        with Session(engine) as db:
            assert notification_planner.plan_for_new_jobs(db, []) == 0
    finally:
        engine.dispose()
