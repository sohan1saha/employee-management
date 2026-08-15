"""
==============================================================================
StaffSync 360 - Database Backup & Restore Integrity Test
==============================================================================
Validates that database dumps, compression, and restore workflows function
accurately without data loss or corruption.
"""

import os
import sys
import gzip
import sqlite3
import pytest

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
        # Export all table definitions and data
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
