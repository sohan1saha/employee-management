"""
==============================================================================
Apex HRMS - Security & Vulnerability Test Suite for Document Vault & Proxy IPs
==============================================================================
"""

import io
import pytest
from fastapi.testclient import TestClient
from main import app
from app.api.deps import get_client_ip
from fastapi import Request


@pytest.fixture
def client():
    return TestClient(app)


def test_client_ip_resolution_with_reverse_proxies():
    """Verify that get_client_ip extracts real client IP through Cloudflare, X-Forwarded-For, and fallbacks."""
    # 1. Cloudflare header
    req1 = Request({"type": "http", "headers": [(b"cf-connecting-ip", b"203.0.113.195"), (b"x-forwarded-for", b"198.51.100.1, 10.0.0.1")]})
    assert get_client_ip(req1) == "203.0.113.195"

    # 2. X-Forwarded-For multi-hop proxy (must extract the leftmost public client IP)
    req2 = Request({"type": "http", "headers": [(b"x-forwarded-for", b"198.51.100.42, 172.16.0.10, 10.0.0.1")]})
    assert get_client_ip(req2) == "198.51.100.42"

    # 3. X-Real-IP
    req3 = Request({"type": "http", "headers": [(b"x-real-ip", b"192.0.2.77")]})
    assert get_client_ip(req3) == "192.0.2.77"


def test_document_vault_path_traversal_sanitization(client):
    """Verify that path traversal attempts in filename (../../etc/passwd) are sanitized."""
    # Login as Admin
    login_res = client.post("/api/auth/login", json={"employee_id": 9924101, "password": "admin123"})
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Legitimate PDF content
    fake_pdf = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF"
    
    # Path traversal payload in filename
    res = client.post(
        "/api/documents/upload",
        headers=headers,
        data={"title": "Path Traversal Test", "document_type": "OTHER", "target_employee_id": 9924101},
        files={"file": ("../../../../etc/passwd.pdf", io.BytesIO(fake_pdf), "application/pdf")}
    )
    assert res.status_code == 200
    uploaded_doc = res.json()
    # The saved file_name must be sanitized to basename only
    assert uploaded_doc["file_name"] == "passwd.pdf"
    assert ".." not in uploaded_doc["file_name"]


def test_document_vault_nested_double_extension_rejection(client):
    """Verify that double extensions with dangerous scripts (e.g. payload.php.pdf) are blocked."""
    login_res = client.post("/api/auth/login", json={"employee_id": 9924101, "password": "admin123"})
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    fake_pdf = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF"

    # Attack: .php.pdf
    res_php = client.post(
        "/api/documents/upload",
        headers=headers,
        data={"title": "PHP Shell Disguise", "document_type": "OTHER"},
        files={"file": ("exploit.php.pdf", io.BytesIO(fake_pdf), "application/pdf")}
    )
    assert res_php.status_code == 400
    assert "nested script extension '.php' is strictly prohibited" in res_php.json()["detail"]

    # Attack: .sh.png
    fake_png = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"
    res_sh = client.post(
        "/api/documents/upload",
        headers=headers,
        data={"title": "Bash Script Disguise", "document_type": "OTHER"},
        files={"file": ("rootkit.sh.png", io.BytesIO(fake_png), "image/png")}
    )
    assert res_sh.status_code == 400
    assert "nested script extension '.sh' is strictly prohibited" in res_sh.json()["detail"]


def test_document_vault_idor_cross_employee_access_denial(client):
    """Verify that standard employees cannot view or download documents of other employees."""
    # 1. Admin uploads document for Employee 1023101 (Bangalore)
    admin_login = client.post("/api/auth/login", json={"employee_id": 9924101, "password": "admin123"})
    admin_token = admin_login.json()["access_token"]
    
    fake_pdf = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF"
    upload_res = client.post(
        "/api/documents/upload",
        headers={"Authorization": f"Bearer {admin_token}"},
        data={"title": "Secret Contract", "document_type": "CONTRACT", "target_employee_id": 1023101},
        files={"file": ("contract.pdf", io.BytesIO(fake_pdf), "application/pdf")}
    )
    assert upload_res.status_code == 200
    doc_id = upload_res.json()["id"]

    # 2. Login as different Employee 2024102 (Delhi)
    emp_login = client.post("/api/auth/login", json={"employee_id": 2024102, "password": "employee123"})
    assert emp_login.status_code == 200
    emp_token = emp_login.json()["access_token"]
    emp_headers = {"Authorization": f"Bearer {emp_token}"}

    # 3. Employee 2024102 attempts to list Employee 1023101's documents -> Forbidden
    list_res = client.get("/api/documents/employee/1023101", headers=emp_headers)
    assert list_res.status_code == 403

    # 4. Employee 2024102 attempts to download Document ID of Employee 1023101 -> Forbidden
    download_res = client.get(f"/api/documents/{doc_id}/download", headers=emp_headers)
    assert download_res.status_code == 403

    # 5. Employee 2024102 attempts to delete Document ID of Employee 1023101 -> Forbidden
    delete_res = client.delete(f"/api/documents/{doc_id}", headers=emp_headers)
    assert delete_res.status_code == 403
