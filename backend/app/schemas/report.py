from pydantic import BaseModel
from uuid import UUID
from datetime import datetime


class ReportOut(BaseModel):
    id: UUID
    filename: str
    file_size: int
    content_type: str
    status: str
    version: int=1
    is_latest: bool=True
    extracted_text: str | None = None
    uploaded_at: datetime
    extracted_at: datetime | None = None

    model_config = {"from_attributes": True}


class ReportListOut(BaseModel):
    reports: list[ReportOut]
    total: int