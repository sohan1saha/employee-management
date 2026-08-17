"""
Test Suite verifying creation of new Kolkata Branch Manager with scoped authority.
"""

import pytest
from fastapi.testclient import TestClient
from main import app


@pytest.fixture
def client():
    return TestClient(app)


def test_create_kolkata_branch_manager(client):
    # 1. Login as Admin
    admin_login = client.post("/api/auth/login", json={"employee_id": 9924101, "password": "admin123"})
    assert admin_login.status_code == 200
    admin_token = admin_login.json()["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    # 2. Get next recommended ID for Kolkata
    next_id_res = client.get("/api/employees/next-id?center=Kolkata", headers=admin_headers)
    assert next_id_res.status_code == 200
    kolkata_eid = next_id_res.json()["next_id"]
    assert str(kolkata_eid).startswith("40")  # Kolkata code is 40

    # 3. Create Kolkata Branch Manager
    create_payload = {
        "eid": kolkata_eid,
        "ename": "Debashis Banerjee",
        "ecen": "Kolkata",
        "epos": "Regional General Manager",
        "esal": 140000.0,
        "edoj": "2026-08-17",
        "system_role": "MANAGER",
        "initial_password": "manager123"
    }
    create_res = client.post("/api/employees", json=create_payload, headers=admin_headers)
    assert create_res.status_code == 201
    assert create_res.json()["eid"] == kolkata_eid
    assert create_res.json()["ecen"] == "Kolkata"

    # 4. Login as newly created Kolkata Manager
    mgr_login = client.post("/api/auth/login", json={"employee_id": kolkata_eid, "password": "manager123"})
    assert mgr_login.status_code == 200
    mgr_data = mgr_login.json()
    assert mgr_data["user"]["role"] == "MANAGER"
    mgr_token = mgr_data["access_token"]
    mgr_headers = {"Authorization": f"Bearer {mgr_token}"}

    # 5. Verify Manager Scope & Power
    # A. Scoped centers list should only contain "Kolkata"
    centers_res = client.get("/api/employees/centers/list", headers=mgr_headers)
    assert centers_res.status_code == 200
    assert centers_res.json() == ["Kolkata"]

    # B. Should be able to view Kolkata employees
    emps_res = client.get("/api/employees", headers=mgr_headers)
    assert emps_res.status_code == 200
    for emp in emps_res.json():
        assert emp["ecen"] == "Kolkata"

    # C. Cannot add employee to Delhi or Bangalore (Restricted to Kolkata only)
    cross_add = client.post(
        "/api/employees",
        json={
            "ename": "Out of Bounds",
            "ecen": "Delhi",
            "epos": "Engineer",
            "esal": 50000.0,
            "edoj": "2026-08-17"
        },
        headers=mgr_headers
    )
    assert cross_add.status_code == 403
