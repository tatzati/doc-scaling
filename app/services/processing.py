import time
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.config import get_settings
from app.db.session import SessionLocal
from app.metrics import JOB_DURATION, JOBS_PROCESSED
from app.models.document import Job, JobStatus


def process_job(job_id: int) -> None:
    started_at = time.perf_counter()
    db: Session = SessionLocal()
    try:
        job = db.get(Job, job_id)
        if job is None:
            return
        job.status = JobStatus.PROCESSING
        db.commit()

        time.sleep(get_settings().processing_delay_seconds)

        job.status = JobStatus.COMPLETED
        job.completed_at = datetime.now(timezone.utc)
        db.commit()
        JOBS_PROCESSED.labels(status=JobStatus.COMPLETED.value).inc()
    except Exception as exc:
        db.rollback()
        job = db.get(Job, job_id)
        if job is not None:
            job.status = JobStatus.FAILED
            job.error_message = str(exc)
            db.commit()
        JOBS_PROCESSED.labels(status=JobStatus.FAILED.value).inc()
    finally:
        JOB_DURATION.observe(time.perf_counter() - started_at)
        db.close()
