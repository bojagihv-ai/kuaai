from __future__ import annotations

import json
from datetime import datetime

from sqlmodel import Session

from app.models.entities import Job


def create_job(session: Session, product_key: str, message: str) -> Job:
    job = Job(product_key=product_key, message=message, status="pending", progress=0)
    session.add(job)
    session.commit()
    session.refresh(job)
    return job


def update_job(session: Session, job: Job, *, status: str, progress: int, message: str, result: dict | None = None) -> Job:
    job.status = status
    job.progress = progress
    job.message = message
    if result is not None:
        job.result_json = json.dumps(result)
    job.updated_at = datetime.utcnow()
    session.add(job)
    session.commit()
    session.refresh(job)
    return job
