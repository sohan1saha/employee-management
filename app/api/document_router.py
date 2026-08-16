"""
==============================================================================
StaffSync 360 - Employee Document Vault API Router
==============================================================================
"""

import os
import shutil
import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Request
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.deps import get_current_user, get_request_id, get_client_ip, validate_resource_access
from app.models.user import User
from app.models.employee import Employee
from app.models.document import EmployeeDocument
from app.schemas.document_schema import DocumentResponse
from app.services.audit_service import record_audit

router = APIRouter(prefix="/documents", tags=["Document Vault"])

STORAGE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "storage", "documents"))
os.makedirs(STORAGE_DIR, exist_ok=True)

ALLOWED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".docx", ".doc", ".txt"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
INTERMEDIATE_DANGEROUS = {"php", "phtml", "py", "sh", "bash", "exe", "bat", "cmd", "js", "vbs", "ps1", "jsp", "asp", "aspx"}


@router.post("/upload", response_model=DocumentResponse)
async def upload_document(
    request: Request,
    file: UploadFile = File(...),
    title: str = Form(...),
    document_type: str = Form("OTHER"),
    target_employee_id: Optional[int] = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Securely upload an employee document or certificate with strict path sanitization & MIME checking."""
    # Determine target employee ID and validate authorization boundary
    emp_id = target_employee_id if (target_employee_id and current_user.role in ["ADMIN", "MANAGER"]) else current_user.employee_id
    emp = validate_resource_access(db, current_user, emp_id)

    # Sanitize raw filename to prevent directory traversal attacks
    raw_name = os.path.basename(file.filename or "document.pdf")
    name_parts = raw_name.lower().split(".")

    # Reject dangerous double extensions (e.g. payload.php.pdf)
    if len(name_parts) > 2:
        for part in name_parts[1:-1]:
            if part in INTERMEDIATE_DANGEROUS:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Security policy violation: nested script extension '.{part}' is strictly prohibited."
                )

    # Validate file extension
    _, ext = os.path.splitext(raw_name)
    ext = ext.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file format '{ext}'. Allowed formats: PDF, PNG, JPG, JPEG, DOCX, TXT."
        )

    # Path traversal containment verification
    emp_storage = os.path.abspath(os.path.join(STORAGE_DIR, str(emp_id)))
    os.makedirs(emp_storage, exist_ok=True)

    safe_filename = f"{uuid.uuid4().hex[:12]}_{raw_name}"
    file_path = os.path.abspath(os.path.join(emp_storage, safe_filename))

    if not file_path.startswith(STORAGE_DIR):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Security policy violation: Path traversal sequence detected."
        )

    # Read and validate size
    content = await file.read()
    file_size = len(content)
    if file_size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File size exceeds maximum allowed threshold of 10MB."
        )

    # Security: Magic Byte Header Inspection to prevent disguised malicious binaries / polyglots
    DANGEROUS_SIGNATURES = [
        b"MZ",            # DOS / Windows Executable / DLL
        b"\x7fELF",       # Linux ELF Binary
        b"\xca\xfe\xba\xbe", # Java Class Bytecode / Mach-O Fat
        b"#!/",           # Shell script execution header
        b"<?php",         # PHP Script execution
    ]
    for sig in DANGEROUS_SIGNATURES:
        if content.startswith(sig):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Security policy violation: executable or script binaries are strictly prohibited."
            )

    # Format-specific signature verification
    if ext == ".pdf" and not content.startswith(b"%PDF-"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid PDF file: Missing standard PDF header signature."
        )
    elif ext == ".png" and not content.startswith(b"\x89PNG"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid PNG image: Missing standard PNG header signature."
        )
    elif ext in [".jpg", ".jpeg"] and not content.startswith(b"\xff\xd8"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JPEG image: Missing standard JPEG header signature."
        )

    # Write file to disk
    with open(file_path, "wb") as f:
        f.write(content)

    doc = EmployeeDocument(
        employee_id=emp_id,
        title=title.strip(),
        document_type=document_type.upper(),
        file_name=raw_name,
        file_size=file_size,
        mime_type=file.content_type or "application/octet-stream",
        file_path=file_path,
        uploaded_by=current_user.id
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    client_ip = get_client_ip(request)
    record_audit(
        db=db,
        action="DOCUMENT_UPLOADED",
        target_entity=f"Employee #{emp_id} Document: {title}",
        user_id=current_user.id,
        username=f"#{current_user.employee_id}",
        role=current_user.role,
        new_value=f"File: {raw_name} ({file_size / 1024:.1f} KB) | Type: {document_type}",
        client_ip=client_ip,
        request_id=get_request_id(request)
    )

    return doc.to_dict()


@router.get("/employee/{employee_id}", response_model=List[DocumentResponse])
def list_employee_documents(
    employee_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all documents belonging to a given employee."""
    if current_user.role == "EMPLOYEE" and current_user.employee_id != employee_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only view your own uploaded documents."
        )

    docs = db.query(EmployeeDocument).filter(EmployeeDocument.employee_id == employee_id).order_by(EmployeeDocument.id.desc()).all()
    return [d.to_dict() for d in docs]


@router.get("/{document_id}/download")
def download_document(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Download or view an uploaded document."""
    doc = db.query(EmployeeDocument).filter(EmployeeDocument.id == document_id).first()
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found."
        )

    if current_user.role == "EMPLOYEE" and doc.employee_id != current_user.employee_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You cannot download other employees' confidential documents."
        )

    if not os.path.exists(doc.file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Physical file was not found on the server storage."
        )

    return FileResponse(
        path=doc.file_path,
        media_type=doc.mime_type,
        filename=doc.file_name
    )


@router.delete("/{document_id}")
def delete_document(
    document_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a document."""
    doc = db.query(EmployeeDocument).filter(EmployeeDocument.id == document_id).first()
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found."
        )

    if current_user.role == "EMPLOYEE" and doc.employee_id != current_user.employee_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only delete your own documents."
        )

    # Remove physical file if present
    if os.path.exists(doc.file_path):
        try:
            os.remove(doc.file_path)
        except Exception:
            pass

    title = doc.title
    emp_id = doc.employee_id
    db.delete(doc)
    db.commit()

    client_ip = get_client_ip(request)
    record_audit(
        db=db,
        action="DOCUMENT_DELETED",
        target_entity=f"Employee #{emp_id} Document: {title}",
        user_id=current_user.id,
        username=f"#{current_user.employee_id}",
        role=current_user.role,
        new_value=f"Deleted document ID #{document_id}",
        client_ip=client_ip,
        request_id=get_request_id(request)
    )

    return {"message": "Document deleted successfully."}
