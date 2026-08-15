import os
import sys

# Ensure root project directory is in python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest
from datetime import date
from fastapi.testclient import TestClient
from main import app
from app.core.database import SessionLocal, Base, engine
from app.models.employee import Employee
from app.models.user import User
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
    """Verify compensation calculations."""
    breakdown = calculate_salary_breakdown(100000.0)
    assert breakdown["base_salary"] == 50000.0
    assert breakdown["hra"] == 20000.0
    assert breakdown["allowance"] == 30000.0
    assert breakdown["gross_salary"] == 100000.0
    assert breakdown["pf_deduction"] == 6000.0
    assert breakdown["tax_deduction"] == 5000.0
    assert breakdown["net_salary"] == 89000.0


def test_core_script_crud():
    """Test the preserved core functions: addrec, disrec, updrec, delrec."""
    # Test addrec programmatically
    success = addrec(
        eid=999,
        ename="Test User",
        ecen="TestCenter",
        epos="Test Engineer",
        esal=60000.0,
        edoj="2024-01-01"
    )
    assert success is True

    # Test disrec
    emp = disrec(999)
    assert emp is not None
    assert emp.ename == "Test User"
    assert emp.esal == 60000.0

    # Test updrec
    upd_success = updrec(999, category="esal", new_val=75000.0)
    assert upd_success is True

    emp_updated = disrec(999)
    assert emp_updated.esal == 75000.0

    # Test delrec
    del_success = delrec(999)
    assert del_success is True
    assert disrec(999) is None


def test_auth_and_api_flow():
    """Test API login, employee listing, and analytics endpoints."""
    # 1. Login with username or employee ID
    login_res = client.post("/api/auth/login", json={
        "employee_id": 9924101,
        "password": "admin123"
    })
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Add Employee via REST API
    emp_payload = {
        "eid": 1026999,
        "ename": "API Test User",
        "ecen": "Bangalore",
        "epos": "API Engineer",
        "esal": 85000.0,
        "edoj": "2026-05-10"
    }
    create_res = client.post("/api/employees", json=emp_payload, headers=headers)
    assert create_res.status_code == 201

    # 3. List Employees
    list_res = client.get("/api/employees", headers=headers)
    assert list_res.status_code == 200
    assert any(e["eid"] == 1026999 for e in list_res.json())

    # 4. Analytics Summary
    analytics_res = client.get("/api/analytics/summary", headers=headers)
    assert analytics_res.status_code == 200
    data = analytics_res.json()
    assert "kpis" in data
    assert "center_distribution" in data

    # 5. Cleanup
    del_res = client.delete("/api/employees/1026999", headers=headers)
    assert del_res.status_code == 200


def test_payroll_and_pdf_generation():
    """Test batch payroll generation and PDF payslip download."""
    # Login as admin
    login_res = client.post("/api/auth/login", json={"employee_id": 9924101, "password": "admin123"})
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Generate payroll
    pay_res = client.post("/api/payroll/generate", json={"month_year": "2026-08"}, headers=headers)
    assert pay_res.status_code == 200
    records = pay_res.json()
    assert len(records) > 0
    first_record_id = records[0]["id"]

    # Download PDF payslip
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

    # Submit leave for emp #1025102
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

    # Approve leave
    review_res = client.patch(
        f"/api/leaves/{leave_id}/status",
        json={"status": "APPROVED", "review_comment": "Approved by test runner"},
        headers=headers
    )
    assert review_res.status_code == 200
    assert review_res.json()["status"] == "APPROVED"

    # Verify audit logs captured the events
    audit_res = client.get("/api/audit/logs", headers=headers)
    assert audit_res.status_code == 200
    logs = audit_res.json()
    assert len(logs) > 0
    actions = [l["action"] for l in logs]
    assert any("LEAVE" in a or "PAYROLL" in a or "EMPLOYEE" in a for a in actions)


def test_manager_center_scoping_isolation():
    """Verify manager cannot access or mutate employee data outside their assigned center."""
    # Login as manager
    login_res = client.post("/api/auth/login", json={"employee_id": 1023101, "password": "manager123"})
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]
    mgr_headers = {"Authorization": f"Bearer {token}"}

    # 1. Check Analytics is scoped to Bangalore
    analytics_res = client.get("/api/analytics/summary", headers=mgr_headers)
    assert analytics_res.status_code == 200
    analytics_data = analytics_res.json()
    for c in analytics_data["center_distribution"]:
        assert c["center"] == "Bangalore"
    assert analytics_data["kpis"]["total_centers"] <= 1

    # 2. Check Employee Directory is scoped to Bangalore
    emp_list_res = client.get("/api/employees", headers=mgr_headers)
    assert emp_list_res.status_code == 200
    employees = emp_list_res.json()
    for emp in employees:
        assert emp["ecen"] == "Bangalore"

    # 3. Check Centers list only contains Bangalore
    centers_res = client.get("/api/employees/centers/list", headers=mgr_headers)
    assert centers_res.status_code == 200
    assert centers_res.json() == ["Bangalore"]

    # 4. Check that accessing non-Bangalore employee directly returns 403 Forbidden
    # Employee 2024102 is in Delhi
    emp2024102_res = client.get("/api/employees/2024102", headers=mgr_headers)
    assert emp2024102_res.status_code == 403

    # 5. Check that trying to create an employee in another center returns 403 Forbidden
    create_cross_res = client.post("/api/employees", json={
        "eid": 2026777,
        "ename": "Cross Center User",
        "ecen": "Delhi",
        "epos": "DevOps Engineer",
        "esal": 90000.0,
        "edoj": "2026-01-01"
    }, headers=mgr_headers)
    assert create_cross_res.status_code == 403

    # 6. Check that Manager can view center-scoped audit logs without 403 error
    audit_res = client.get("/api/audit/logs", headers=mgr_headers)
    assert audit_res.status_code == 200
    assert isinstance(audit_res.json(), list)


def test_employee_self_service_isolation():
    """Verify standard employee role receives self-service dashboard and cannot access other employees."""
    # Login as employee (1025102)
    login_res = client.post("/api/auth/login", json={"employee_id": 1025102, "password": "employee123"})
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]
    emp_headers = {"Authorization": f"Bearer {token}"}

    # 1. Check self-service dashboard
    summary_res = client.get("/api/analytics/summary", headers=emp_headers)
    assert summary_res.status_code == 200
    data = summary_res.json()
    assert data.get("is_employee_portal") is True
    assert data["employee"]["eid"] == 1025102
    assert "salary_breakdown" in data
    assert "holidays" in data
    assert "kpis" in data

    # 2. Check employee directory listing is restricted to self only
    list_res = client.get("/api/employees", headers=emp_headers)
    assert list_res.status_code == 200
    emps = list_res.json()
    assert len(emps) == 1
    assert emps[0]["eid"] == 1025102

    # 3. Check accessing another employee's profile directly returns 403 Forbidden
    other_emp_res = client.get("/api/employees/2024102", headers=emp_headers)
    assert other_emp_res.status_code == 403

    # 4. Check accessing Audit Vault returns 403 Forbidden
    audit_res = client.get("/api/audit/logs", headers=emp_headers)
    assert audit_res.status_code == 403


def test_recommended_employee_id_pattern():
    """Verify continuous pattern [CenterCode][YY][Seq] ID generation."""
    login_res = client.post("/api/auth/login", json={"employee_id": 9924101, "password": "admin123"})
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Next ID for Delhi (20) in year 2025
    delhi_res = client.get("/api/employees/next-id?center=Delhi&doj=2025-06-01", headers=headers)
    assert delhi_res.status_code == 200
    delhi_data = delhi_res.json()
    assert str(delhi_data["next_id"]).startswith("2025")
    first_delhi_id = delhi_data["next_id"]

    # 2. Create employee with that ID
    create_res = client.post("/api/employees", json={
        "eid": first_delhi_id,
        "ename": "Delhi Pattern Emp",
        "ecen": "Delhi",
        "epos": "Systems Engineer",
        "esal": 70000.0,
        "edoj": "2025-06-01"
    }, headers=headers)
    assert create_res.status_code == 201

    # 3. Next ID should increment continuously to next serial
    next_delhi_res = client.get("/api/employees/next-id?center=Delhi&doj=2025-06-01", headers=headers)
    assert next_delhi_res.status_code == 200
    assert next_delhi_res.json()["next_id"] == first_delhi_id + 1

    # 4. Cleanup
    client.delete(f"/api/employees/{first_delhi_id}", headers=headers)


def test_change_password_flow():
    """Verify password change validation, rejection of wrong old password, and successful update."""
    # Login as employee (1025102)
    login_res = client.post("/api/auth/login", json={"employee_id": 1025102, "password": "employee123"})
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Wrong old password should fail
    wrong_old = client.post("/api/auth/change-password", json={
        "old_password": "wrongpassword999",
        "new_password": "newpassword123",
        "confirm_password": "newpassword123"
    }, headers=headers)
    assert wrong_old.status_code == 400
    assert "incorrect" in wrong_old.json()["detail"].lower()

    # 2. Mismatched confirm password should fail
    mismatch = client.post("/api/auth/change-password", json={
        "old_password": "employee123",
        "new_password": "newpassword123",
        "confirm_password": "differentpass123"
    }, headers=headers)
    assert mismatch.status_code == 400
    assert "match" in mismatch.json()["detail"].lower()

    # 3. Successful change password
    success_change = client.post("/api/auth/change-password", json={
        "old_password": "employee123",
        "new_password": "employee_new_pass2026",
        "confirm_password": "employee_new_pass2026"
    }, headers=headers)
    assert success_change.status_code == 200

    # 4. Login with old password fails
    old_login = client.post("/api/auth/login", json={"employee_id": 1025102, "password": "employee123"})
    assert old_login.status_code == 401

    # 5. Login with new password succeeds
    new_login = client.post("/api/auth/login", json={"employee_id": 1025102, "password": "employee_new_pass2026"})
    assert new_login.status_code == 200
    new_token = new_login.json()["access_token"]

    # 6. Revert back to original password for demo convenience
    revert_res = client.post("/api/auth/change-password", json={
        "old_password": "employee_new_pass2026",
        "new_password": "employee123",
        "confirm_password": "employee123"
    }, headers={"Authorization": f"Bearer {new_token}"})
    assert revert_res.status_code == 200


def test_system_health_and_caching_layer():
    """Verify healthcheck endpoints, DB connectivity diagnostics, and cache service."""
    from app.services.cache_service import cache

    # 1. Test /healthz
    res = client.get("/healthz")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"

    # 2. Test /api/system/health
    res_sys = client.get("/api/system/health")
    assert res_sys.status_code == 200
    data = res_sys.json()
    assert data["status"] == "healthy"
    assert "database" in data
    assert "cache" in data

    # 3. Test Cache Service get/set/invalidate
    cache.set("test_key_emp", {"emp_count": 42}, ttl_seconds=60)
    cached_val = cache.get("test_key_emp")
    assert cached_val == {"emp_count": 42}

    cache.invalidate_prefix("test_key")
    assert cache.get("test_key_emp") is None






