import json
import logging
import time
from contextlib import asynccontextmanager

from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, Query, Request, Response, status
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db, initialize_database
from app.metrics import HTTP_REQUESTS, HTTP_REQUEST_DURATION
from app.models.document import Document, Job, JobStatus
from app.schemas import DocumentCreate, DocumentResponse, JobResponse, ProcessResponse
from app.services.processing import process_job

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("scalability-lab")


@asynccontextmanager
async def lifespan(_: FastAPI):
    initialize_database()
    yield


app = FastAPI(title="Scalability Lab API", version="0.1.0", lifespan=lifespan)


@app.middleware("http")
async def observe_request(request: Request, call_next) -> Response:
    started_at = time.perf_counter()
    response = await call_next(request)
    duration = time.perf_counter() - started_at
    path = request.url.path
    HTTP_REQUESTS.labels(request.method, path, str(response.status_code)).inc()
    HTTP_REQUEST_DURATION.labels(request.method, path).observe(duration)
    logger.info(json.dumps({
        "service": "api",
        "environment": "local",
        "method": request.method,
        "path": path,
        "status_code": response.status_code,
        "duration_ms": round(duration * 1000, 2),
    }))
    return response


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/ready")
def ready(db: Session = Depends(get_db)) -> dict[str, str]:
    try:
        db.execute(select(1))
    except Exception as exc:
        raise HTTPException(status_code=503, detail="database unavailable") from exc
    return {"status": "ready"}


@app.get("/metrics")
def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.post("/documents", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
def create_document(payload: DocumentCreate, db: Session = Depends(get_db)) -> Document:
    document = Document(**payload.model_dump())
    db.add(document)
    db.commit()
    db.refresh(document)
    return document


@app.get("/documents", response_model=list[DocumentResponse])
def list_documents(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> list[Document]:
    statement = select(Document).order_by(Document.id).offset(offset).limit(limit)
    return list(db.scalars(statement))


@app.get("/documents/{document_id}", response_model=DocumentResponse)
def get_document(document_id: int, db: Session = Depends(get_db)) -> Document:
    document = db.get(Document, document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="document not found")
    return document


@app.post("/documents/{document_id}/process", response_model=ProcessResponse, status_code=202)
def process_document(
    document_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> ProcessResponse:
    if db.get(Document, document_id) is None:
        raise HTTPException(status_code=404, detail="document not found")
    job = Job(document_id=document_id, status=JobStatus.QUEUED)
    db.add(job)
    db.commit()
    db.refresh(job)
    background_tasks.add_task(process_job, job.id)
    return ProcessResponse(job_id=job.id, status=job.status)


@app.get("/jobs/{job_id}", response_model=JobResponse)
def get_job(job_id: int, db: Session = Depends(get_db)) -> Job:
    job = db.get(Job, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="job not found")
    return job
