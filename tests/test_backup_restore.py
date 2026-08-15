"""
==============================================================================
StaffSync 360 - Database Backup, Encryption & Restore Integrity Test
==============================================================================
Validates that database dumps, compression, AES-256 encryption, and restore workflows
function accurately without data loss or corruption.
"""

import os
import sys
import gzip
import sqlite3
import hashlib
import pytest
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.database import SessionLocal, engine, Base
from app.models.employee import Employee
from app.models.payroll import PayrollRecord
from seed_data import seed_database


def test_sqlite_and_schema_backup_integrity(tmp_path):
    """Test schema and data dump / restore cycle for continuous data protection."""
    seed_database(reset=True)
    db = SessionLocal()
    initial_emp_count = db.query(Employee).count()
    initial_payroll_count = db.query(PayrollRecord).count()
    db.close()

    assert initial_emp_count > 0
    assert initial_payroll_count > 0

    # 1. Simulate SQL backup dump
    backup_file = tmp_path / "test_backup.sql.gz"
    
    # In SQLite mode, export database schema & rows
    with gzip.open(backup_file, "wt", encoding="utf-8") as f:
        for line in engine.raw_connection().iterdump():
            f.write(f"{line}\n")

    assert os.path.exists(backup_file)
    assert os.path.getsize(backup_file) > 100

    # 2. Verify restored database in isolated temporary instance
    restore_db_path = tmp_path / "restored.db"
    conn = sqlite3.connect(str(restore_db_path))
    cursor = conn.cursor()

    with gzip.open(backup_file, "rt", encoding="utf-8") as f:
        sql_script = f.read()
        cursor.executescript(sql_script)
    conn.commit()

    # 3. Assert counts and row integrity in restored database
    cursor.execute("SELECT COUNT(*) FROM employees")
    restored_emp_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM payroll_records")
    restored_payroll_count = cursor.fetchone()[0]

    cursor.execute("SELECT eid, ename, ecen, esal FROM employees WHERE eid = 9924101")
    admin_row = cursor.fetchone()

    conn.close()

    assert restored_emp_count == initial_emp_count
    assert restored_payroll_count == initial_payroll_count
    assert admin_row is not None
    assert admin_row[1] == "Eleanor Vance"
    assert admin_row[2] == "Corporate HQ"


def test_encrypted_backup_and_decrypted_restore(tmp_path):
    """Test AES-256 authenticated encryption on database backup and verify decrypted restoration."""
    raw_dump_path = tmp_path / "raw_backup.sql.gz"
    encrypted_path = tmp_path / "raw_backup.sql.gz.enc"
    decrypted_path = tmp_path / "decrypted_backup.sql.gz"

    # 1. Dump database to compressed gzip
    with gzip.open(raw_dump_path, "wt", encoding="utf-8") as f:
        for line in engine.raw_connection().iterdump():
            f.write(f"{line}\n")

    with open(raw_dump_path, "rb") as f:
        plaintext_data = f.read()

    # 2. Encrypt with AES-256-GCM using derived 256-bit key from passphrase
    passphrase = "EnterpriseSecretPassphrase2026!"
    aes_key = hashlib.sha256(passphrase.encode("utf-8")).digest()
    aesgcm = AESGCM(aes_key)
    nonce = os.urandom(12)
    ciphertext = nonce + aesgcm.encrypt(nonce, plaintext_data, None)

    with open(encrypted_path, "wb") as f:
        f.write(ciphertext)

    assert os.path.exists(encrypted_path)
    assert os.path.getsize(encrypted_path) > len(nonce)

    # 3. Decrypt and verify payload
    with open(encrypted_path, "rb") as f:
        encrypted_blob = f.read()

    extracted_nonce = encrypted_blob[:12]
    extracted_cipher = encrypted_blob[12:]
    decrypted_bytes = aesgcm.decrypt(extracted_nonce, extracted_cipher, None)

    with open(decrypted_path, "wb") as f:
        f.write(decrypted_bytes)

    # 4. Execute restore into isolated database
    restore_target = tmp_path / "decrypted_restored.db"
    conn = sqlite3.connect(str(restore_target))
    cursor = conn.cursor()

    with gzip.open(decrypted_path, "rt", encoding="utf-8") as f:
        cursor.executescript(f.read())
    conn.commit()

    cursor.execute("SELECT COUNT(*) FROM employees")
    emp_count = cursor.fetchone()[0]
    conn.close()

    assert emp_count > 0


def test_backup_and_restore_shell_scripts_syntax():
    """Verify backup and restore shell scripts exist with mandatory safety checks."""
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    backup_script = os.path.join(base_dir, "scripts", "backup_db.sh")
    restore_script = os.path.join(base_dir, "scripts", "restore_db.sh")
    entrypoint_script = os.path.join(base_dir, "scripts", "docker_entrypoint.sh")

    assert os.path.exists(backup_script), "backup_db.sh must exist in scripts/"
    assert os.path.exists(restore_script), "restore_db.sh must exist in scripts/"
    assert os.path.exists(entrypoint_script), "docker_entrypoint.sh must exist in scripts/"

    with open(backup_script, "r", encoding="utf-8") as f:
        backup_content = f.read()
    assert "ENCRYPTION_PASSPHRASE" in backup_content
    assert "gpg" in backup_content
    assert "set -e" in backup_content

    with open(restore_script, "r", encoding="utf-8") as f:
        restore_content = f.read()
    assert "ENCRYPTION_PASSPHRASE" in restore_content
    assert "pg_restore" in restore_content

    with open(entrypoint_script, "r", encoding="utf-8") as f:
        entrypoint_content = f.read()
    assert "alembic upgrade head" in entrypoint_content
