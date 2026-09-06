from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.document import JobStatus


class DocumentCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    content_type: str = Field(min_length=1, max_length=100)
    size_bytes: int = Field(ge=0)


class DocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    content_type: str
    size_bytes: int
    created_at: datetime


class JobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    document_id: int
    status: JobStatus
    error_message: str | None
    created_at: datetime
    completed_at: datetime | None


class ProcessResponse(BaseModel):
    job_id: int
    status: JobStatus
