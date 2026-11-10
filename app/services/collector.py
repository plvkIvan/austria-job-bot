from sqlalchemy.orm import Session
from app.db.models import Job
from app.sources.base import JobSource

async def collect(db: Session, source: JobSource) -> int:
    added = 0
    for item in await source.fetch():
        if db.query(Job).filter_by(source=item.source, external_id=item.external_id).first():
            continue
        db.add(Job(**vars(item)))
        added += 1
    db.commit()
    return added
