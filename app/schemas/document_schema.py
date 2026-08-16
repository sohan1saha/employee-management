"""Pydantic schemas for Employee Document Management."""

from typing import Optional
from pydantic import BaseModel, ConfigDict


class DocumentResponse(BaseModel):
    id: int
    employee_id: int
    employee_name: Optional[str] = None
    title: str
    document_type: str
    file_name: str
    file_size: int
    mime_type: str
    uploaded_by: Optional[int] = None
    created_at: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
