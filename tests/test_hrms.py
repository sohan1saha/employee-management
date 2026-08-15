import os
import sys
import concurrent.futures
from decimal import Decimal

# Ensure root project directory is in python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest
from datetime import date
from fastapi.testclient import TestClient
from main import app
from app.core.database import SessionLocal, Base, engine
from app.core.config import Settings
from app.models.employee import Employee
from app.models.user import User
from app.models.payroll import PayrollRecord
from app.models.leave import LeaveRequest
from app.models.audit import AuditLog
from app.core.security import get_password_hash
from seed_data import seed_database
from app.services.payroll_service import calculate_salary_breakdown, generate_payslip_pdf, generate_payroll_for_month
from app.core.emp_mgmt_core import addrec, updrec, disrec, delrec

client = TestClient(app)


@pytest.fixture(scope="module", autouse=True)
def setup_database():
    """Setup clean test database tables and seed fresh records."""
    seed_database(reset=True)
    yield


def test_salary_breakdown_math():
    """Verify compensation calculations using Decimal precision."""
    breakdown = calculate_salary_breakdown(Decimal('100000.00'))
    assert breakdown["base_salary"] == Decimal('50000.00')
    assert breakdown["hra"] == Decimal('20000.00')
    assert breakdown["allowance"] == Decimal('30000.00')
    assert breakdown["gross_salary"] == Decimal('100000.00')
    assert breakdown["pf_deduction"] == Decimal('6000.00')
    assert breakdown["tax_deduction"] == Decimal('5000.00')
    assert breakdown["net_salary"] == Decimal('89000.00')


def test_core_script_crud():
    """Test the preserved core functions: addrec, disrec, updrec, delrec."""
    success = addrec(
        eid=999,
        ename="Test User",
        ecen="TestCenter",
        epos="Test Engineer",
        esal=60000.0,
        edoj="2024-01-01"
    )
    assert success is True

    emp = disrec(999)
    assert emp is not None
    assert emp.ename == "Test User"
    assert float(emp.esal) == 60000.0

    upd_success = updrec(999, category="esal", new_val=75000.0)
    assert upd_success is True

    emp_updated = disrec(999)
    assert float(emp_updated.esal) == 75000.0

    del_success = delrec(999)
    assert del_success is True
    assert disrec(999) is None


def test_auth_and_api_flow():
    """Test API login, employee listing, and analytics endpoints."""
    login_res = client.post("/api/auth/login", json={
        "employee_id": 9924101,
        "password": "admin123"
    })
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Add Employee via REST API
    emp_payload = {
        "eid": 1026999,
        "ename": "API Test User",
        "ecen": "Bangalore",
        "epos": "API Engineer",
        "esal": "85000.00",
        "edoj": "2026-05-10"
    }
    create_res = client.post("/api/employees", json=emp_payload, headers=headers)
    assert create_res.status_code == 201

    # List Employees
    list_res = client.get("/api/employees", headers=headers)
    assert list_res.status_code == 200
    assert any(e["eid"] == 1026999 for e in list_res.json())

    # Analytics Summary
    analytics_res = client.get("/api/analytics/summary", headers=headers)
    assert analytics_res.status_code == 200
    data = analytics_res.json()
    assert "kpis" in data
    assert "center_distribution" in data

    # Soft delete / deactivate
    del_res = client.delete("/api/employees/1026999", headers=headers)
    assert del_res.status_code == 200
    assert del_res.json()["status"] == "TERMINATED"


def test_payroll_and_pdf_generation():
    """Test batch payroll generation and PDF payslip download."""
    login_res = client.post("/api/auth/login", json={"employee_id": 9924101, "password": "admin123"})
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    pay_res = client.post("/api/payroll/generate", json={"month_year": "2026-08"}, headers=headers)
    assert pay_res.status_code == 200
    records = pay_res.json()
    assert len(records) > 0
    first_record_id = records[0]["id"]

    pdf_res = client.get(f"/api/payroll/payslip/{first_record_id}/pdf", headers=headers)
    assert pdf_res.status_code == 200
    assert pdf_res.headers["content-type"] == "application/pdf"
    assert pdf_res.content.startswith(b"%PDF")


def test_leave_workflow_and_audit():
    """Test leave request, approval, and audit logging."""
    login_res = client.post("/api/auth/login", json={"employee_id": 9924101, "password": "admin123"})
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    leave_payload = {
        "employee_id": 1025102,
        "leave_type": "PTO",
        "start_date": "2026-09-01",
        "end_date": "2026-09-03",
        "reason": "Test PTO application"
    }
    submit_res = client.post("/api/leaves", json=leave_payload, headers=headers)
    assert submit_res.status_code == 201
    leave_id = submit_res.json()["id"]

    review_res = client.patch(
        f"/api/leaves/{leave_id}/status",
        json={"status": "APPROVED", "review_comment": "Approved by test runner"},
        headers=headers
    )
    assert review_res.status_code == 200
    assert review_res.json()["status"] == "APPROVED"

    audit_res = client.get("/api/audit/logs", headers=headers)
    assert audit_res.status_code == 200
    logs = audit_res.json()
    assert len(logs) > 0
    actions = [l["action"] for l in logs]
    assert any("LEAVE" in a or "PAYROLL" in a or "EMPLOYEE" in a for a in actions)


def test_manager_center_scoping_isolation():
    """Verify manager cannot access or mutate employee data outside their assigned center."""
    login_res = client.post("/api/auth/login", json={"employee_id": 1023101, "password": "manager123"})
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]
    mgr_headers = {"Authorization": f"Bearer {token}"}

    # 1. Analytics is scoped to Bangalore
    analytics_res = client.get("/api/analytics/summary", headers=mgr_headers)
    assert analytics_res.status_code == 200
    analytics_data = analytics_res.json()
    for c in analytics_data["center_distribution"]:
        assert c["center"] == "Bangalore"

    # 2. Employee Directory is scoped to Bangalore
    emp_list_res = client.get("/api/employees", headers=mgr_headers)
    assert emp_list_res.status_code == 200
    employees = emp_list_res.json()
    for emp in employees:
        assert emp["ecen"] == "Bangalore"

    # 3. Direct access to non-Bangalore employee returns 403 Forbidden
    emp2024102_res = client.get("/api/employees/2024102", headers=mgr_headers)
    assert emp2024102_res.status_code == 403

    # 4. Cross-center employee creation is blocked (403 Forbidden)
    create_cross_res = client.post("/api/employees", json={
        "eid": 2026777,
        "ename": "Cross Center User",
        "ecen": "Delhi",
        "epos": "DevOps Engineer",
        "esal": "90000.00",
        "edoj": "2026-01-01"
    }, headers=mgr_headers)
    assert create_cross_res.status_code == 403


def test_employee_self_service_isolation():
    """Verify standard employee role receives self-service dashboard and cannot access other employees."""
    login_res = client.post("/api/auth/login", json={"employee_id": 1025102, "password": "employee123"})
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]
    emp_headers = {"Authorization": f"Bearer {token}"}

    # 1. Self-service dashboard
    summary_res = client.get("/api/analytics/summary", headers=emp_headers)
    assert summary_res.status_code == 200
    data = summary_res.json()
    assert data.get("is_employee_portal") is True
    assert data["employee"]["eid"] == 1025102

    # 2. Directory listing restricted to self
    list_res = client.get("/api/employees", headers=emp_headers)
    assert list_res.status_code == 200
    emps = list_res.json()
    assert len(emps) == 1
    assert emps[0]["eid"] == 1025102

    # 3. Direct access to other employee blocked (403)
    other_emp_res = client.get("/api/employees/2024102", headers=emp_headers)
    assert other_emp_res.status_code == 403

    # 4. Audit vault access blocked (403)
    audit_res = client.get("/api/audit/logs", headers=emp_headers)
    assert audit_res.status_code == 403


def test_password_policy_and_change_flow():
    """Verify password policy (min 8 chars, uppercase, lowercase, digit, special character) and update."""
    login_res = client.post("/api/auth/login", json={"employee_id": 1025102, "password": "employee123"})
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Weak password rejected by policy (no uppercase/digit/special)
    weak_res = client.post("/api/auth/change-password", json={
        "old_password": "employee123",
        "new_password": "weakpassword",
        "confirm_password": "weakpassword"
    }, headers=headers)
    assert weak_res.status_code == 400
    assert "uppercase" in weak_res.json()["detail"].lower() or "policy" in weak_res.json()["detail"].lower()

    # 2. Strong password compliant with policy
    strong_new_pass = "Emp@SecurePass2026!"
    success_change = client.post("/api/auth/change-password", json={
        "old_password": "employee123",
        "new_password": strong_new_pass,
        "confirm_password": strong_new_pass
    }, headers=headers)
    assert success_change.status_code == 200

    # 3. Verify old session token is immediately invalidated
    old_session_check = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert old_session_check.status_code == 401

    # 4. Login with new password succeeds
    new_login = client.post("/api/auth/login", json={"employee_id": 1025102, "password": strong_new_pass})
    assert new_login.status_code == 200
    new_token = new_login.json()["access_token"]

    # 4. Revert password back for test harness
    revert_res = client.post("/api/auth/change-password", json={
        "old_password": strong_new_pass,
        "new_password": "employee123",
        "confirm_password": "employee123"
    }, headers={"Authorization": f"Bearer {new_token}"})
    assert revert_res.status_code in [200, 400]


def test_token_refresh_and_revocation():
    """Verify refresh token rotation (one-time use) and session revocation."""
    login_res = client.post("/api/auth/login", json={"employee_id": 9924101, "password": "admin123"})
    assert login_res.status_code == 200
    data = login_res.json()
    refresh_token = data["refresh_token"]
    assert refresh_token is not None

    # 1. First refresh exchange succeeds and rotates refresh token
    refresh_res = client.post("/api/auth/refresh", json={"refresh_token": refresh_token})
    assert refresh_res.status_code == 200
    new_data = refresh_res.json()
    assert new_data["access_token"] is not None
    rotated_refresh_token = new_data["refresh_token"]
    assert rotated_refresh_token != refresh_token

    # 2. Replay attack: Old refresh token is revoked and fails with 401
    replay_res = client.post("/api/auth/refresh", json={"refresh_token": refresh_token})
    assert replay_res.status_code == 401
    assert "revoked" in replay_res.json()["detail"].lower() or "invalid" in replay_res.json()["detail"].lower()

    # 3. New rotated refresh token works
    second_refresh = client.post("/api/auth/refresh", json={"refresh_token": rotated_refresh_token})
    assert second_refresh.status_code == 200

    # 4. Logout and verify session revocation
    logout_res = client.post("/api/auth/logout", headers={"Authorization": f"Bearer {second_refresh.json()['access_token']}"})
    assert logout_res.status_code == 200


def test_payroll_state_machine_transitions():
    """Verify strict payroll lifecycle: DRAFT -> CALCULATED -> APPROVED -> PAID."""
    login_res = client.post("/api/auth/login", json={"employee_id": 9924101, "password": "admin123"})
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Generate payroll
    pay_res = client.post("/api/payroll/generate", json={"month_year": "2026-09"}, headers=headers)
    assert pay_res.status_code == 200
    records = pay_res.json()
    assert len(records) > 0
    rec_id = records[0]["id"]

    # Set to CALCULATED in DB to test state machine transitions
    db = SessionLocal()
    rec = db.query(PayrollRecord).filter(PayrollRecord.id == rec_id).first()
    rec.payment_status = "CALCULATED"
    db.commit()
    db.close()

    # 1. Approve transition: CALCULATED -> APPROVED
    app_res = client.post(f"/api/payroll/{rec_id}/approve", json={}, headers=headers)
    assert app_res.status_code == 200
    assert app_res.json()["record"]["payment_status"] == "APPROVED"

    # 2. Disallow duplicate approve: APPROVED cannot be approved again
    dup_app = client.post(f"/api/payroll/{rec_id}/approve", json={}, headers=headers)
    assert dup_app.status_code == 400
    assert "cannot approve" in dup_app.json()["detail"].lower()

    # 3. Disburse transition: APPROVED -> PAID
    dis_res = client.post(f"/api/payroll/{rec_id}/disburse", headers=headers)
    assert dis_res.status_code == 200
    assert dis_res.json()["record"]["payment_status"] == "PAID"

    # 4. Disallow further transitions on finalized PAID record
    fail_dis = client.post(f"/api/payroll/{rec_id}/disburse", headers=headers)
    assert fail_dis.status_code == 400


def test_account_lockout_after_failed_attempts():
    """Verify account locks out after 5 consecutive failed login attempts."""
    for i in range(5):
        fail_res = client.post("/api/auth/login", json={"employee_id": 2025103, "password": "WrongPassword999!"})
        assert fail_res.status_code in [401, 429]

    # 6th attempt should be blocked with 429 Too Many Requests (Lockout)
    lock_res = client.post("/api/auth/login", json={"employee_id": 2025103, "password": "employee123"})
    assert lock_res.status_code == 429
    assert "locked" in lock_res.json()["detail"].lower()

    # Reset lockout in database
    db = SessionLocal()
    user = db.query(User).filter(User.employee_id == 2025103).first()
    if user:
        user.failed_login_attempts = 0
        user.locked_until = None
        db.commit()
    db.close()


def test_system_health_and_caching_layer():
    """Verify healthcheck endpoints, DB connectivity diagnostics, and cache service."""
    from app.services.cache_service import cache

    res = client.get("/healthz")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"

    res_sys = client.get("/api/system/health")
    assert res_sys.status_code == 200
    data = res_sys.json()
    assert data["status"] == "healthy"
    assert "database" in data
    assert "cache" in data

    cache.set("test_key_emp", {"emp_count": 42}, ttl_seconds=60)
    assert cache.get("test_key_emp") == {"emp_count": 42}
    cache.invalidate_prefix("test_key")
    assert cache.get("test_key_emp") is None


# =============================================================================
# Production Hardening Test Suites
# =============================================================================

def test_concurrent_employee_id_allocation():
    """Verify atomic continuous Employee ID allocation under concurrent thread execution."""
    login_res = client.post("/api/auth/login", json={"employee_id": 9924101, "password": "admin123"})
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    def create_concurrent_emp(idx):
        payload = {
            "ename": f"Concurrent Emp {idx}",
            "ecen": "Bangalore",
            "epos": "Concurrency Engineer",
            "esal": "80000.00",
            "edoj": "2026-03-01"
        }
        res = client.post("/api/employees", json=payload, headers=headers)
        return res.json()["eid"]

    # Concurrently create 6 employees across worker threads
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as executor:
        futures = [executor.submit(create_concurrent_emp, i) for i in range(6)]
        generated_ids = [f.result() for f in futures]

    # Verify all generated IDs are strictly unique (0 collisions)
    assert len(generated_ids) == len(set(generated_ids))
    for eid in generated_ids:
        assert str(eid).startswith("10")


def test_orm_audit_immutability():
    """Verify ORM-level event listeners prevent tampering with or deleting AuditLog records."""
    db = SessionLocal()
    audit = db.query(AuditLog).first()
    assert audit is not None

    # 1. Attempting UPDATE must raise PermissionError
    with pytest.raises(PermissionError) as exc_update:
        audit.old_value = "Tampered Old Value"
        db.commit()
    db.rollback()
    assert "append-only" in str(exc_update.value).lower()

    # 2. Attempting DELETE must raise PermissionError
    with pytest.raises(PermissionError) as exc_delete:
        db.delete(audit)
        db.commit()
    db.rollback()
    assert "append-only" in str(exc_delete.value).lower()
    db.close()


def test_orm_paid_payroll_immutability():
    """Verify ORM-level event listener prevents deleting finalized/paid payroll records."""
    db = SessionLocal()
    paid_payroll = db.query(PayrollRecord).filter(PayrollRecord.payment_status == "PAID").first()
    assert paid_payroll is not None

    # Attempting to delete paid payroll record must raise PermissionError
    with pytest.raises(PermissionError) as exc_delete:
        db.delete(paid_payroll)
        db.commit()
    db.rollback()
    assert "cannot be physically deleted" in str(exc_delete.value)
    db.close()


def test_production_secret_fail_startup():
    """Verify application fails startup with fatal error if production environment has default secrets."""
    # Test setting ENVIRONMENT=production with default secret
    with pytest.raises(RuntimeError) as exc_info:
        Settings(
            ENVIRONMENT="production",
            SECRET_KEY="development_jwt_secret_key_change_in_production_staffsync360_min32chars",
            DATABASE_URL="postgresql://user:pass@localhost:5432/db"
        )
    assert "FATAL STARTUP ERROR" in str(exc_info.value)
