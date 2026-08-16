"""
==============================================================================
StaffSync 360 - Comprehensive Automated Test Suite for New Enterprise Modules:
1. Daily Attendance & Check-In/Out
2. Performance Appraisals & 360 Feedback
3. Employee Document Vault
4. In-App Notifications & Automated Event Alerts
==============================================================================
"""

import io
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
from app.models.performance import PerformanceReview
from app.models.document import EmployeeDocument
from app.models.notification import Notification
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
        email="eleanor@staffsync.internal", status="ACTIVE"
    )
    # Seed Manager (Bangalore)
    mgr_emp = Employee(
        eid=1023101, ename="Sara Chen", ecen="Bangalore",
        epos="Regional Manager", esal=Decimal("140000.00"), edoj=date(2023, 5, 1),
        email="sara@staffsync.internal", status="ACTIVE"
    )
    # Seed Employee (Bangalore)
    staff_emp = Employee(
        eid=1025102, ename="Jordan Rivera", ecen="Bangalore",
        epos="Lead Engineer", esal=Decimal("120000.00"), edoj=date(2025, 2, 1),
        email="jordan@staffsync.internal", status="ACTIVE"
    )

    db.add_all([admin_emp, mgr_emp, staff_emp])
    db.commit()

    admin_user = User(
        employee_id=9924101, email="eleanor@staffsync.internal",
        hashed_password=get_password_hash("Admin@1234"), role="ADMIN", is_active=True
    )
    mgr_user = User(
        employee_id=1023101, email="sara@staffsync.internal",
        hashed_password=get_password_hash("Manager@1234"), role="MANAGER", is_active=True
    )
    staff_user = User(
        employee_id=1025102, email="jordan@staffsync.internal",
        hashed_password=get_password_hash("Employee@1234"), role="EMPLOYEE", is_active=True
    )
    db.add_all([admin_user, mgr_user, staff_user])
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
    token = create_access_token(subject=str(employee_id), role=role, session_id="test-session")
    return {"Authorization": f"Bearer {token}"}


# =============================================================================
# Test Suite 1: Attendance & Check-In/Out
# =============================================================================
def test_attendance_clock_in_and_clock_out(client, test_db):
    staff_headers = get_auth_header(1025102, "EMPLOYEE")

    # 1. Clock in
    res_in = client.post("/api/attendance/clock-in", json={"notes": "WFH Station"}, headers=staff_headers)
    assert res_in.status_code == 200
    data_in = res_in.json()
    assert data_in["employee_id"] == 1025102
    assert data_in["status"] == "PRESENT"
    assert data_in["clock_out"] is None

    # 2. Prevent duplicate clock in
    res_dup = client.post("/api/attendance/clock-in", json={}, headers=staff_headers)
    assert res_dup.status_code == 400

    # 3. Summary check
    res_sum = client.get("/api/attendance/summary", headers=staff_headers)
    assert res_sum.status_code == 200
    assert res_sum.json()["is_currently_clocked_in"] is True

    # 4. Clock out
    res_out = client.post("/api/attendance/clock-out", json={"notes": "Done for today"}, headers=staff_headers)
    assert res_out.status_code == 200
    data_out = res_out.json()
    assert data_out["clock_out"] is not None
    assert "total_hours" in data_out

    # 5. History check
    res_hist = client.get("/api/attendance/history", headers=staff_headers)
    assert res_hist.status_code == 200
    assert len(res_hist.json()) >= 1


# =============================================================================
# Test Suite 2: Performance Reviews & Appraisals
# =============================================================================
def test_performance_review_lifecycle(client, test_db):
    mgr_headers = get_auth_header(1023101, "MANAGER")
    staff_headers = get_auth_header(1025102, "EMPLOYEE")

    # 1. Manager authors appraisal
    review_payload = {
        "employee_id": 1025102,
        "review_period": "Q1 2026",
        "rating": 4.9,
        "goals_met": "EXCEEDED",
        "strengths": "High code quality and rapid delivery.",
        "areas_for_improvement": "Keep writing unit tests.",
        "manager_feedback": "Fantastic quarterly performance, Jordan!",
        "status": "FINALIZED"
    }
    res_create = client.post("/api/performance/reviews", json=review_payload, headers=mgr_headers)
    assert res_create.status_code == 200
    review_data = res_create.json()
    review_id = review_data["id"]
    assert review_data["rating"] == 4.9
    assert review_data["is_acknowledged"] is False

    # 2. Notification was generated for employee
    res_notif = client.get("/api/notifications", headers=staff_headers)
    assert res_notif.status_code == 200
    notif_list = res_notif.json()["notifications"]
    assert any("Performance Appraisal" in n["title"] for n in notif_list)

    # 3. Employee acknowledges appraisal
    res_ack = client.patch(
        f"/api/performance/reviews/{review_id}/acknowledge",
        json={"employee_comments": "Thank you Sara, looking forward to Q2 goals."},
        headers=staff_headers
    )
    assert res_ack.status_code == 200
    ack_data = res_ack.json()
    assert ack_data["is_acknowledged"] is True
    assert "Thank you Sara" in ack_data["employee_comments"]


# =============================================================================
# Test Suite 3: Document Vault & Storage
# =============================================================================
def test_document_vault_upload_and_download(client, test_db):
    staff_headers = get_auth_header(1025102, "EMPLOYEE")

    # 1. Upload mock PDF document
    file_bytes = b"%PDF-1.4 Mock Document Certificate Content For Testing"
    files = {"file": ("degree_certificate.pdf", io.BytesIO(file_bytes), "application/pdf")}
    data = {
        "title": "B.Tech Graduation Certificate",
        "document_type": "CERTIFICATE"
    }

    res_upload = client.post(
        "/api/documents/upload",
        data=data,
        files=files,
        headers=staff_headers
    )
    assert res_upload.status_code == 200
    doc_info = res_upload.json()
    doc_id = doc_info["id"]
    assert doc_info["title"] == "B.Tech Graduation Certificate"
    assert doc_info["document_type"] == "CERTIFICATE"

    # 2. List documents
    res_list = client.get("/api/documents/employee/1025102", headers=staff_headers)
    assert res_list.status_code == 200
    assert len(res_list.json()) >= 1

    # 3. Download document
    res_dl = client.get(f"/api/documents/{doc_id}/download", headers=staff_headers)
    assert res_dl.status_code == 200
    assert res_dl.content == file_bytes

    # 4. Delete document
    res_del = client.delete(f"/api/documents/{doc_id}", headers=staff_headers)
    assert res_del.status_code == 200

    # 5. Verify deleted
    res_check = client.get(f"/api/documents/{doc_id}/download", headers=staff_headers)
    assert res_check.status_code == 404


# =============================================================================
# Test Suite 4: Notification Center Feed & Mark Read
# =============================================================================
def test_notifications_feed_and_state(client, test_db):
    staff_headers = get_auth_header(1025102, "EMPLOYEE")

    # 1. Direct notification creation
    staff_user = test_db.query(User).filter(User.employee_id == 1025102).first()
    notif = Notification(
        user_id=staff_user.id,
        title="Security Alert",
        message="New sign-in from Bangalore branch.",
        category="SECURITY",
        is_read=False
    )
    test_db.add(notif)
    test_db.commit()

    # 2. Fetch notifications feed
    res_feed = client.get("/api/notifications", headers=staff_headers)
    assert res_feed.status_code == 200
    feed_data = res_feed.json()
    assert feed_data["unread_count"] >= 1

    # 3. Mark single notification as read
    res_read = client.patch(f"/api/notifications/{notif.id}/read", headers=staff_headers)
    assert res_read.status_code == 200
    assert res_read.json()["is_read"] is True

    # 4. Mark all as read
    res_all = client.post("/api/notifications/mark-all-read", headers=staff_headers)
    assert res_all.status_code == 200


# =============================================================================
# Test Suite 5: Manager Attendance & Personal Leave Permissions from Admin
# =============================================================================
def test_manager_attendance_and_leave_workflow(client, test_db):
    mgr_headers = get_auth_header(1023101, "MANAGER")
    admin_headers = get_auth_header(9924101, "ADMIN")

    # 1. Manager Clock-In and Clock-Out
    res_in = client.post("/api/attendance/clock-in", json={"notes": "Manager On-Duty Shift"}, headers=mgr_headers)
    assert res_in.status_code == 200
    assert res_in.json()["employee_id"] == 1023101

    res_sum = client.get("/api/attendance/summary", headers=mgr_headers)
    assert res_sum.status_code == 200
    assert res_sum.json()["is_currently_clocked_in"] is True

    res_out = client.post("/api/attendance/clock-out", json={"notes": "Shift Finished"}, headers=mgr_headers)
    assert res_out.status_code == 200
    assert res_out.json()["clock_out"] is not None

    # 2. Manager applies for personal leave
    leave_payload = {
        "employee_id": 1023101,
        "leave_type": "PTO",
        "start_date": "2026-09-01",
        "end_date": "2026-09-05",
        "reason": "Executive Annual Leave"
    }
    res_leave = client.post("/api/leaves", json=leave_payload, headers=mgr_headers)
    assert res_leave.status_code == 201
    leave_id = res_leave.json()["id"]

    # 3. Verify Admin received in-app notification of Manager's leave request
    res_admin_notif = client.get("/api/notifications", headers=admin_headers)
    assert res_admin_notif.status_code == 200
    admin_notifs = res_admin_notif.json()["notifications"]
    assert any("Manager Leave Request: Sara Chen" in n["title"] for n in admin_notifs)

    # 4. Manager CANNOT approve their own leave request (Forbidden 403)
    res_self_approve = client.patch(
        f"/api/leaves/{leave_id}/status",
        json={"status": "APPROVED", "review_comment": "Self-approved"},
        headers=mgr_headers
    )
    assert res_self_approve.status_code == 403
    assert "cannot approve or reject your own leave" in res_self_approve.json()["detail"]

    # 5. Admin approves Manager's leave request (Success 200)
    res_admin_approve = client.patch(
        f"/api/leaves/{leave_id}/status",
        json={"status": "APPROVED", "review_comment": "Approved by HQ Admin"},
        headers=admin_headers
    )
    assert res_admin_approve.status_code == 200
    assert res_admin_approve.json()["status"] == "APPROVED"

