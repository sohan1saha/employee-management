"""Employee Document and Certificate Storage Model."""

from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, BigInteger
from sqlalchemy.orm import relationship
from app.core.database import Base


class EmployeeDocument(Base):
    __tablename__ = "employee_documents"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    employee_id = Column(Integer, ForeignKey("employees.eid", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(150), nullable=False)
    document_type = Column(String(50), default="OTHER", nullable=False)  # ID_PROOF, CONTRACT, CERTIFICATE, TAX_FORM, RESUME, OTHER
    file_name = Column(String(255), nullable=False)
    file_size = Column(BigInteger, nullable=False)  # in bytes
    mime_type = Column(String(100), nullable=False)
    file_path = Column(String(500), nullable=False)
    uploaded_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    employee = relationship("Employee", backref="documents")
    uploader = relationship("User", foreign_keys=[uploaded_by])

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "employee_id": self.employee_id,
            "employee_name": self.employee.ename if self.employee else None,
            "title": self.title,
            "document_type": self.document_type,
            "file_name": self.file_name,
            "file_size": self.file_size,
            "mime_type": self.mime_type,
            "uploaded_by": self.uploaded_by,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }
