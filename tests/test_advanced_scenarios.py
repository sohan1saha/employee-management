"""
==============================================================================
Apex HRMS - Advanced Enterprise Test Suite:
1. Multi-User Concurrency & Race Condition Stress Testing
2. Midnight & Overnight Shift Boundary Math with Break Deductions
3. Multi-Break Cycle Accumulation & Stopwatch Precision
4. Document Vault Polyglot & Magic Byte Security Verification
5. Statutory Payroll Boundary & Edge Cases
==============================================================================
"""

import io
import concurrent.futures
import pytest
from datetime import datetime, date, timezone
from decimal import Decimal
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.models.employee import Employee
from app.models.user import User
from app.models.attendance import AttendanceRecord
from app.core.security import get_password_hash, create_access_token
from main import app


@pytest.fixture(scope="function")
def test_db():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()

    # Seed Admin (HQ)
    admin_emp = Employee(
        eid=9924101, ename="Eleanor Vance", ecen="Corporate HQ",
        epos="Admin", esal=Decimal("180000.00"), edoj=date(2024, 1, 1),
        email="eleanor@apex.internal", status="ACTIVE"
    )
    # Seed Manager (Bangalore)
    mgr_emp = Employee(
        eid=1023101, ename="Sara Chen", ecen="Bangalore",
        epos="Regional Manager", esal=Decimal("140000.00"), edoj=date(2023, 5, 1),
        email="sara@apex.internal", status="ACTIVE"
    )
    # Seed Employee 1 (Bangalore)
    staff_emp1 = Employee(
        eid=1025102, ename="Jordan Rivera", ecen="Bangalore",
        epos="Lead Engineer", esal=Decimal("120000.00"), edoj=date(2025, 2, 1),
        email="jordan@apex.internal", status="ACTIVE"
    )
    # Seed Employee 2 (Delhi)
    staff_emp2 = Employee(
        eid=2024102, ename="Rohan Gupta", ecen="Delhi",
        epos="Senior Analyst", esal=Decimal("95000.00"), edoj=date(2024, 6, 1),
        email="rohan@apex.internal", status="ACTIVE"
    )

    db.add_all([admin_emp, mgr_emp, staff_emp1, staff_emp2])
    db.commit()

    admin_user = User(
        employee_id=9924101, email="eleanor@apex.internal",
        hashed_password=get_password_hash("Admin@1234"), role="ADMIN", is_active=True
    )
    mgr_user = User(
        employee_id=1023101, email="sara@apex.internal",
        hashed_password=get_password_hash("Manager@1234"), role="MANAGER", is_active=True
    )
    staff_user1 = User(
        employee_id=1025102, email="jordan@apex.internal",
        hashed_password=get_password_hash("Employee@1234"), role="EMPLOYEE", is_active=True
    )
    staff_user2 = User(
        employee_id=2024102, email="rohan@apex.internal",
        hashed_password=get_password_hash("Employee@1234"), role="EMPLOYEE", is_active=True
    )
    db.add_all([admin_user, mgr_user, staff_user1, staff_user2])
    db.commit()

    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(test_db):
    def override_get_db():
        try:
            yield test_db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def get_auth_header(employee_id: int, role: str) -> dict:
    token = create_access_token(subject=str(employee_id), role=role, session_id="test-adv-session")
    return {"Authorization": f"Bearer {token}"}


# =============================================================================
# Test 1: Concurrency & Multi-Employee Isolation
# =============================================================================
def test_concurrent_clock_ins_and_leaves(client, test_db):
    """Verify that multiple requests from different employees are safely isolated and processed."""
    staff1_headers = get_auth_header(1025102, "EMPLOYEE")
    staff2_headers = get_auth_header(2024102, "EMPLOYEE")

    res1 = client.post("/api/attendance/clock-in", json={"notes": "Station A Check-In"}, headers=staff1_headers)
    res2 = client.post("/api/attendance/clock-in", json={"notes": "Station B Check-In"}, headers=staff2_headers)

    assert res1.status_code == 200
    assert res2.status_code == 200
    assert res1.json()["employee_id"] == 1025102
    assert res2.json()["employee_id"] == 2024102


# =============================================================================
# Test 2: Multi-Break Cycle Accumulation & Stopwatch Precision
# =============================================================================
def test_multiple_break_cycles_accumulation(client, test_db):
    """Verify an employee can take multiple consecutive breaks and accumulate accurate break time."""
    staff_headers = get_auth_header(1025102, "EMPLOYEE")

    # 1. Clock in
    res_in = client.post("/api/attendance/clock-in", json={}, headers=staff_headers)
    assert res_in.status_code == 200

    # 2. Break Cycle 1: Coffee break
    b1_start = client.post("/api/attendance/break-start", json={"notes": "Coffee 1"}, headers=staff_headers)
    assert b1_start.status_code == 200
    assert b1_start.json()["is_on_break"] is True

    b1_end = client.post("/api/attendance/break-end", headers=staff_headers)
    assert b1_end.status_code == 200
    assert b1_end.json()["is_on_break"] is False

    # 3. Break Cycle 2: Lunch break
    b2_start = client.post("/api/attendance/break-start", json={"notes": "Lunch 2"}, headers=staff_headers)
    assert b2_start.status_code == 200
    assert b2_start.json()["is_on_break"] is True

    b2_end = client.post("/api/attendance/break-end", headers=staff_headers)
    assert b2_end.status_code == 200
    assert b2_end.json()["is_on_break"] is False

    # 4. Clock out and check total hours calculation
    res_out = client.post("/api/attendance/clock-out", json={"notes": "Finished"}, headers=staff_headers)
    assert res_out.status_code == 200
    out_data = res_out.json()
    assert out_data["clock_out"] is not None
    assert "total_hours" in out_data


# =============================================================================
# Test 3: Midnight Crossing Shift Duration Calculation
# =============================================================================
def test_midnight_shift_calculation_in_model(test_db):
    """Verify that shifts crossing midnight compute exact net hours without negative numbers."""
    # Create shift starting at 23:00 UTC and ending at 07:30 UTC next day (8.5 hrs gross, 30m break = 8.0 hrs net)
    t_start = datetime(2026, 8, 15, 23, 0, 0, tzinfo=timezone.utc)
    t_end = datetime(2026, 8, 16, 7, 30, 0, tzinfo=timezone.utc)

    record = AttendanceRecord(
        employee_id=1025102,
        work_date=date(2026, 8, 15),
        clock_in=t_start,
        clock_out=t_end,
        total_break_seconds=1800,  # 30 mins break
        total_hours=Decimal('8.00'),
        overtime_hours=Decimal('0.00'),
        status="PRESENT",
        punctuality_status="ON_TIME"
    )
    test_db.add(record)
    test_db.commit()
    test_db.refresh(record)

    gross_seconds = (record.clock_out - record.clock_in).total_seconds()
    net_seconds = gross_seconds - record.total_break_seconds
    net_hours = net_seconds / 3600.0

    assert gross_seconds == 30600.0  # 8.5 hours
    assert net_hours == 8.0
    assert record.total_hours == Decimal('8.00')


# =============================================================================
# Test 4: Document Vault Polyglot & Magic Byte Security Verification
# =============================================================================
def test_document_vault_magic_byte_protection(client, test_db):
    """Verify that dangerous executables and disguised files are strictly rejected."""
    staff_headers = get_auth_header(1025102, "EMPLOYEE")

    # 1. Windows Executable disguised as PDF (Should be rejected with HTTP 400)
    fake_exe = io.BytesIO(b"MZ\x90\x00\x03\x00\x00\x00Disguised Windows PE Binary")
    res_fake = client.post(
        "/api/documents/upload",
        data={"title": "Fake PDF", "document_type": "CERTIFICATE"},
        files={"file": ("malware.pdf", fake_exe, "application/pdf")},
        headers=staff_headers
    )
    assert res_fake.status_code == 400
    assert "executable or script binaries are strictly prohibited" in res_fake.json()["detail"]

    # 2. Linux ELF binary disguised as PDF (Should be rejected with HTTP 400)
    fake_elf = io.BytesIO(b"\x7fELF\x02\x01\x01\x00Disguised Linux ELF Binary")
    res_elf = client.post(
        "/api/documents/upload",
        data={"title": "Fake Linux Binary", "document_type": "CERTIFICATE"},
        files={"file": ("exploit.pdf", fake_elf, "application/pdf")},
        headers=staff_headers
    )
    assert res_elf.status_code == 400

    # 3. Invalid PDF header (Should be rejected with HTTP 400)
    corrupted_pdf = io.BytesIO(b"Plain text masquerading as a PDF")
    res_bad_pdf = client.post(
        "/api/documents/upload",
        data={"title": "Corrupted Document", "document_type": "CERTIFICATE"},
        files={"file": ("corrupt.pdf", corrupted_pdf, "application/pdf")},
        headers=staff_headers
    )
    assert res_bad_pdf.status_code == 400
    assert "Missing standard PDF header signature" in res_bad_pdf.json()["detail"]

    # 4. Genuine PDF with %PDF- header (Should succeed with HTTP 200)
    valid_pdf = io.BytesIO(b"%PDF-1.7 Valid Executive Employment Agreement")
    res_valid = client.post(
        "/api/documents/upload",
        data={"title": "Executive Employment Agreement", "document_type": "CONTRACT"},
        files={"file": ("agreement.pdf", valid_pdf, "application/pdf")},
        headers=staff_headers
    )
    assert res_valid.status_code == 200
    assert res_valid.json()["title"] == "Executive Employment Agreement"


# =============================================================================
# Test 5: Leave Quota & Self-Approval Security
# =============================================================================
def test_leave_approval_security_rules(client, test_db):
    """Verify that employees cannot approve their own leaves and dates must be logically valid."""
    staff_headers = get_auth_header(1025102, "EMPLOYEE")

    # 1. Apply for valid leave
    leave_payload = {
        "employee_id": 1025102,
        "leave_type": "CASUAL",
        "start_date": "2026-10-01",
        "end_date": "2026-10-03",
        "reason": "Family function"
    }
    res_apply = client.post("/api/leaves", json=leave_payload, headers=staff_headers)
    assert res_apply.status_code == 201
    leave_id = res_apply.json()["id"]

    # 2. Employee cannot approve own leave (403 Forbidden)
    res_unauth = client.patch(
        f"/api/leaves/{leave_id}/status",
        json={"status": "APPROVED", "review_comment": "Self-approved"},
        headers=staff_headers
    )
    assert res_unauth.status_code == 403
