"""
Test Suite verifying multi-center isolation on Audit Trail:
- Admin has global visibility across all audit records.
- Branch Managers are strictly scoped to audit trails of their assigned center and junior employees.
"""

import pytest
from fastapi.testclient import TestClient
from main import app


from seed_data import seed_database


@pytest.fixture(scope="module", autouse=True)
def setup_database():
    seed_database(reset=True)
    yield


@pytest.fixture
def client():
    return TestClient(app)


def test_audit_scoping_manager_vs_admin(client):
    # 1. Admin logs in and inspects audit logs
    admin_login = client.post("/api/auth/login", json={"employee_id": 9924101, "password": "admin123"})
    assert admin_login.status_code == 200
    admin_token = admin_login.json()["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    all_logs_res = client.get("/api/audit/logs", headers=admin_headers)
    assert all_logs_res.status_code == 200
    admin_logs = all_logs_res.json()
    assert isinstance(admin_logs, list)

    # 2. Bangalore Manager logs in (Sara Chen #1023101)
    blr_login = client.post("/api/auth/login", json={"employee_id": 1023101, "password": "manager123"})
    assert blr_login.status_code == 200
    blr_token = blr_login.json()["access_token"]
    blr_headers = {"Authorization": f"Bearer {blr_token}"}

    blr_logs_res = client.get("/api/audit/logs", headers=blr_headers)
    assert blr_logs_res.status_code == 200
    blr_logs = blr_logs_res.json()

    # Verify that Bangalore manager does NOT see Delhi or Mumbai scoped target records
    for log in blr_logs:
        target = log.get("target_entity", "")
        old_val = log.get("old_value") or ""
        new_val = log.get("new_value") or ""
        combined = f"{target} {old_val} {new_val}"
        # If it specifically names Delhi or Mumbai and doesn't belong to Bangalore/actor, it must be excluded
        if "Delhi" in combined or "Mumbai" in combined:
            assert "Bangalore" in combined or log["username"] == "#1023101"

    # 3. Delhi Manager logs in (Vikram Malhotra #2023101)
    delhi_login = client.post("/api/auth/login", json={"employee_id": 2023101, "password": "manager123"})
    assert delhi_login.status_code == 200
    delhi_token = delhi_login.json()["access_token"]
    delhi_headers = {"Authorization": f"Bearer {delhi_token}"}

    delhi_logs_res = client.get("/api/audit/logs", headers=delhi_headers)
    assert delhi_logs_res.status_code == 200
    delhi_logs = delhi_logs_res.json()

    for log in delhi_logs:
        target = log.get("target_entity", "")
        old_val = log.get("old_value") or ""
        new_val = log.get("new_value") or ""
        combined = f"{target} {old_val} {new_val}"
        if "Bangalore" in combined:
            assert "Delhi" in combined or log["username"] == "#2023101"

    # 4. Standard Employee (Alex Turner #1025102) is blocked from audit vault
    emp_login = client.post("/api/auth/login", json={"employee_id": 1025102, "password": "employee123"})
    assert emp_login.status_code == 200
    emp_token = emp_login.json()["access_token"]
    emp_headers = {"Authorization": f"Bearer {emp_token}"}

    emp_audit_res = client.get("/api/audit/logs", headers=emp_headers)
    assert emp_audit_res.status_code == 403
