"""Seed fresh demo data with structured continuous Employee IDs across Corporate HQ and regional centers."""

from datetime import datetime, date, timedelta, timezone
from decimal import Decimal
from app.core.database import SessionLocal, engine, Base
import app.models  # Register models
from app.models.user import User
from app.models.employee import Employee
from app.models.leave import LeaveRequest
from app.models.payroll import PayrollRecord
from app.models.audit import AuditLog
from app.core.security import get_password_hash
from app.services.payroll_service import calculate_salary_breakdown


def seed_database(reset: bool = True):
    print("[+] Initializing and seeding fresh database...")
    if reset:
        print("[*] Clearing existing tables...")
        Base.metadata.drop_all(bind=engine)

    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        print("[*] Creating Fresh Master Employee Records...")
        # 1. Create Sample Employees with pattern: [CenterCode (2)][YY (2)][Seq (3)]
        # Central/Corporate HQ (99), Bangalore (10), Delhi (20), Mumbai (30), Kolkata (40)
        sample_employees = [
            # Central Corporate HQ (Code 99)
            Employee(
                eid=9924101,
                ename="Eleanor Vance",
                ecen="Corporate HQ",
                epos="Chief Executive Administrator",
                esal=Decimal('180000.00'),
                edoj=date(2024, 1, 10),
                email="eleanor.vance@staffsync.internal",
                status="ACTIVE"
            ),
            # Bangalore Center (Code 10)
            Employee(
                eid=1023101,
                ename="Sara Chen",
                ecen="Bangalore",
                epos="Engineering Manager",
                esal=Decimal('135000.00'),
                edoj=date(2023, 3, 15),
                email="sara.chen@staffsync.internal",
                status="ACTIVE"
            ),
            Employee(
                eid=1025102,
                ename="Alex Turner",
                ecen="Bangalore",
                epos="Senior Software Engineer",
                esal=Decimal('95000.00'),
                edoj=date(2025, 2, 1),
                email="alex.turner@staffsync.internal",
                status="ACTIVE"
            ),
            Employee(
                eid=1026103,
                ename="David Miller",
                ecen="Bangalore",
                epos="Lead UI/UX Designer",
                esal=Decimal('85000.00'),
                edoj=date(2026, 1, 15),
                email="david.miller@staffsync.internal",
                status="ACTIVE"
            ),
            # Delhi Center (Code 20)
            Employee(
                eid=2023101,
                ename="Vikram Malhotra",
                ecen="Delhi",
                epos="Operations Manager",
                esal=Decimal('125000.00'),
                edoj=date(2023, 5, 10),
                email="vikram.malhotra@staffsync.internal",
                status="ACTIVE"
            ),
            Employee(
                eid=2024102,
                ename="Priya Sharma",
                ecen="Delhi",
                epos="Financial Analyst",
                esal=Decimal('82000.00'),
                edoj=date(2024, 4, 12),
                email="priya.sharma@staffsync.internal",
                status="ACTIVE"
            ),
            Employee(
                eid=2025103,
                ename="Karan Mehra",
                ecen="Delhi",
                epos="QA Automation Lead",
                esal=Decimal('88000.00'),
                edoj=date(2025, 6, 20),
                email="karan.mehra@staffsync.internal",
                status="ACTIVE"
            ),
            # Mumbai Center (Code 30)
            Employee(
                eid=3023101,
                ename="Ananya Roy",
                ecen="Mumbai",
                epos="Regional Branch Manager",
                esal=Decimal('128000.00'),
                edoj=date(2023, 8, 1),
                email="ananya.roy@staffsync.internal",
                status="ACTIVE"
            ),
            Employee(
                eid=3024102,
                ename="Rohan Verma",
                ecen="Mumbai",
                epos="HR Operations Lead",
                esal=Decimal('80000.00'),
                edoj=date(2024, 9, 18),
                email="rohan.verma@staffsync.internal",
                status="ACTIVE"
            ),
            # Kolkata Center (Code 40)
            Employee(
                eid=4025101,
                ename="Siddharth Sen",
                ecen="Kolkata",
                epos="Cloud Solutions Architect",
                esal=Decimal('110000.00'),
                edoj=date(2025, 11, 5),
                email="siddharth.sen@staffsync.internal",
                status="ACTIVE"
            )
        ]
        db.add_all(sample_employees)
        db.commit()

        print("[*] Creating User Accounts with Linked Employee IDs...")
        # 2. Create Users for all employees
        users_list = [
            User(
                email="eleanor.vance@staffsync.internal",
                hashed_password=get_password_hash("admin123"),
                role="ADMIN",
                employee_id=9924101,
                is_active=True
            ),
            User(
                email="sara.chen@staffsync.internal",
                hashed_password=get_password_hash("manager123"),
                role="MANAGER",
                employee_id=1023101,
                is_active=True
            ),
            User(
                email="alex.turner@staffsync.internal",
                hashed_password=get_password_hash("employee123"),
                role="EMPLOYEE",
                employee_id=1025102,
                is_active=True
            ),
            User(
                email="david.miller@staffsync.internal",
                hashed_password=get_password_hash("employee123"),
                role="EMPLOYEE",
                employee_id=1026103,
                is_active=True
            ),
            User(
                email="vikram.malhotra@staffsync.internal",
                hashed_password=get_password_hash("manager123"),
                role="MANAGER",
                employee_id=2023101,
                is_active=True
            ),
            User(
                email="priya.sharma@staffsync.internal",
                hashed_password=get_password_hash("employee123"),
                role="EMPLOYEE",
                employee_id=2024102,
                is_active=True
            ),
            User(
                email="karan.mehra@staffsync.internal",
                hashed_password=get_password_hash("employee123"),
                role="EMPLOYEE",
                employee_id=2025103,
                is_active=True
            ),
            User(
                email="ananya.roy@staffsync.internal",
                hashed_password=get_password_hash("manager123"),
                role="MANAGER",
                employee_id=3023101,
                is_active=True
            ),
            User(
                email="rohan.verma@staffsync.internal",
                hashed_password=get_password_hash("employee123"),
                role="EMPLOYEE",
                employee_id=3024102,
                is_active=True
            ),
            User(
                email="siddharth.sen@staffsync.internal",
                hashed_password=get_password_hash("employee123"),
                role="EMPLOYEE",
                employee_id=4025101,
                is_active=True
            )
        ]
        db.add_all(users_list)
        db.commit()
        admin_user = users_list[0]

        print("[*] Generating Initial Payroll Records...")
        # 3. Generate Payroll for Current Month
        current_month = datetime.now(timezone.utc).strftime("%Y-%m")
        for emp in sample_employees:
            bd = calculate_salary_breakdown(emp.esal)
            payroll = PayrollRecord(
                employee_id=emp.eid,
                month_year=current_month,
                base_salary=bd["base_salary"],
                hra=bd["hra"],
                allowance=bd["allowance"],
                gross_salary=bd["gross_salary"],
                pf_deduction=bd["pf_deduction"],
                tax_deduction=bd["tax_deduction"],
                net_salary=bd["net_salary"],
                payment_status="PAID"
            )
            db.add(payroll)
        db.commit()

        print("[*] Creating Sample Leave Requests...")
        # 4. Create Sample Leave Requests
        sample_leaves = [
            LeaveRequest(
                employee_id=1025102,
                leave_type="SICK",
                start_date=date.today() + timedelta(days=2),
                end_date=date.today() + timedelta(days=4),
                days_count=3,
                reason="Medical recovery following viral flu.",
                status="PENDING"
            ),
            LeaveRequest(
                employee_id=3024102,
                leave_type="CASUAL",
                start_date=date.today() - timedelta(days=10),
                end_date=date.today() - timedelta(days=8),
                days_count=3,
                reason="Family vacation in Goa.",
                status="APPROVED",
                reviewed_by=admin_user.id,
                review_comment="Approved. Have a great vacation!"
            ),
            LeaveRequest(
                employee_id=2024102,
                leave_type="PTO",
                start_date=date.today() + timedelta(days=15),
                end_date=date.today() + timedelta(days=18),
                days_count=4,
                reason="Annual personal leave.",
                status="PENDING"
            )
        ]
        db.add_all(sample_leaves)
        db.commit()

        print("[*] Logging Initial System Audit Records...")
        # 5. Initial Audit Logs
        sample_audits = [
            AuditLog(
                user_id=admin_user.id,
                username=f"#{admin_user.employee_id}",
                role=admin_user.role,
                action="SYSTEM_INITIALIZED",
                target_entity="System Core",
                new_value="StaffSync 360 database schema and central codes initialized.",
                client_ip="127.0.0.1"
            ),
            AuditLog(
                user_id=admin_user.id,
                username=f"#{admin_user.employee_id}",
                role=admin_user.role,
                action="EMPLOYEE_CREATED",
                target_entity="Employee #9924101",
                new_value="Name: Eleanor Vance, Center: Corporate HQ, Pos: Chief Executive Administrator",
                client_ip="127.0.0.1"
            ),
            AuditLog(
                user_id=admin_user.id,
                username=f"#{admin_user.employee_id}",
                role=admin_user.role,
                action="PAYROLL_BATCH_GENERATED",
                target_entity=f"Month: {current_month}",
                new_value=f"Processed payroll for {len(sample_employees)} staff members across centers.",
                client_ip="127.0.0.1"
            )
        ]
        db.add_all(sample_audits)
        db.commit()

        print("[SUCCESS] Database successfully re-seeded with Employee ID logins!")
        print("\n--- Login Credentials (Employee ID & Password) ---")
        print("   Admin:    Employee ID: 9924101 | Password: admin123")
        print("   Manager:  Employee ID: 1023101 | Password: manager123")
        print("   Employee: Employee ID: 1025102 | Password: employee123")

    except Exception as e:
        db.rollback()
        print(f"Error seeding database: {e}")
        raise e
    finally:
        db.close()


if __name__ == "__main__":
    seed_database(reset=True)
