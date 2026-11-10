"""Prepare notification deliveries; does not contact WhatsApp.

Call plan_for_new_jobs(db, job_ids) only for newly imported job IDs.
The caller may commit or roll back the transaction.
"""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Delivery, Job, User
from app.matching.matcher import evaluate_match


def plan_for_new_jobs(db: Session, job_ids: list[int]) -> int:
    """Queue one pending delivery per consenting user and matching new job.

    Repeated calls do not duplicate existing deliveries. No WhatsApp messages
    are sent. Call db.commit() after this function to persist the changes.
    """
    ids = sorted(set(job_ids))
    if not ids:
        return 0

    jobs = db.scalars(select(Job).where(Job.id.in_(ids))).all()
    users = db.scalars(
        select(User).where(
            User.notifications_enabled.is_(True),
            User.consent_at.is_not(None),
        )
    ).all()

    existing = set(db.execute(
        select(Delivery.user_id, Delivery.job_id).where(Delivery.job_id.in_(ids))
    ).all())
    queued = 0

    for job in jobs:
        for user in users:
            if not user.query or not user.city:
                continue
            if (user.id, job.id) in existing:
                continue

            result = evaluate_match(user, job)
            # The revised matcher does NOT filter by the informational score.
            if not result.should_notify:
                continue

            db.add(Delivery(user_id=user.id, job_id=job.id, status="pending"))
            existing.add((user.id, job.id))
            queued += 1

    db.flush()
    return queued
