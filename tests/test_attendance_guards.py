"""
==============================================================================
Apex HRMS - Attendance Anti-Manipulation & Concurrency Verification Test Suite
==============================================================================
"""

import pytest
from fastapi.testclient import TestClient
from main import app


@pytest.fixture
def client():
    return TestClient(app)


def test_attendance_state_machine_and_anti_tampering(client):
    """Verify strict attendance state machine guards and manipulation prevention."""
    # 1. Login as standard Employee 2025103 (Delhi)
    emp_login = client.post("/api/auth/login", json={"employee_id": 2025103, "password": "employee123"})
    assert emp_login.status_code == 200
    token = emp_login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Clean up any unclosed test sessions if left behind
    curr_res = client.get("/api/attendance/current", headers=headers)
    if curr_res.status_code == 200 and curr_res.json():
        client.post("/api/attendance/clock-out", headers=headers, json={})

    # Guard 1: Cannot start break without being clocked in
    break_no_clock = client.post("/api/attendance/break-start", headers=headers, json={"notes": "premature break"})
    assert break_no_clock.status_code == 400
    assert "No active clock-in session found" in break_no_clock.json()["detail"]

    # Guard 2: Cannot end break without being on break
    end_break_no_break = client.post("/api/attendance/break-end", headers=headers)
    assert end_break_no_break.status_code == 400

    # Guard 3: Cannot clock out without active clock-in
    clock_out_no_clock = client.post("/api/attendance/clock-out", headers=headers, json={})
    assert clock_out_no_clock.status_code == 400

    # Action: Legitimate Clock-In
    clock_in_res = client.post("/api/attendance/clock-in", headers=headers, json={"device_info": "MacBook Pro / Chrome"})
    assert clock_in_res.status_code == 200
    session_id = clock_in_res.json()["id"]

    # Guard 4: Strict Double Clock-in Rejection (Concurrency Race Guard)
    double_clock = client.post("/api/attendance/clock-in", headers=headers, json={"device_info": "iPhone 15"})
    assert double_clock.status_code == 400
    assert "Active shift already in progress" in double_clock.json()["detail"]

    # Action: Start Break
    start_b = client.post("/api/attendance/break-start", headers=headers, json={"notes": "Lunch"})
    assert start_b.status_code == 200
    assert start_b.json()["is_on_break"] is True

    # Guard 5: Cannot start another break while already on break
    double_break = client.post("/api/attendance/break-start", headers=headers, json={"notes": "Coffee"})
    assert double_break.status_code == 400
    assert "already on an active break session" in double_break.json()["detail"]

    # Action: End Break
    end_b = client.post("/api/attendance/break-end", headers=headers)
    assert end_b.status_code == 200
    assert end_b.json()["is_on_break"] is False

    # Guard 6: Cannot end break again after resuming work
    double_end_b = client.post("/api/attendance/break-end", headers=headers)
    assert double_end_b.status_code == 400
    assert "not currently on a break" in double_end_b.json()["detail"]

    # Action: Clock Out
    clock_out_res = client.post("/api/attendance/clock-out", headers=headers, json={"notes": "Day complete"})
    assert clock_out_res.status_code == 200
    assert clock_out_res.json()["clock_out"] is not None

    # Guard 7: Cannot clock out twice
    second_clock_out = client.post("/api/attendance/clock-out", headers=headers, json={})
    assert second_clock_out.status_code == 400
