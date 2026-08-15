"""Core Employee Management Module (Evolved from original script).

Preserves the original functions:
- addrec()
- updrec(eid)
- disrec(eid)
- delrec(eid)
- cli_menu()

Upgraded with robust database session handling, SQLite/MySQL compatibility,
validation, and automatic audit logging.
"""

import sys
from datetime import datetime, date
from app.core.database import SessionLocal, engine
from app.models.employee import Employee
from app.models.audit import AuditLog


def addrec(eid=None, ename=None, ecen=None, epos=None, esal=None, edoj=None):
    """Add a new employee record.
    Can be called interactively from CLI or programmatically with arguments.
    """
    db = SessionLocal()
    try:
        if eid is None:
            print("\n--- Add New Employee ---")
            eid_input = input("Enter Employee ID: ").strip()
            if not eid_input.isdigit():
                print("Error: Employee ID must be a number!")
                return False
            eid = int(eid_input)

            # Check if ID already exists
            existing = db.query(Employee).filter(Employee.eid == eid).first()
            if existing:
                print(f"Error: Employee with ID {eid} already exists!")
                return False

            ename = input("Enter Employee Name: ").strip()
            ecen = input("Enter Employee Centre: ").strip()
            epos = input("Enter Employee Position: ").strip()
            esal_input = input("Enter Employee Salary: ").strip()
            if not esal_input.isdigit():
                print("Error: Employee Salary must be a valid number!")
                return False
            esal = float(esal_input)

            edoj_str = input("Enter Employee Date of Joining (yyyy-mm-dd): ").strip()
            try:
                edoj = datetime.strptime(edoj_str, "%Y-%m-%d").date()
            except ValueError:
                print("Error: Invalid date format! Use YYYY-MM-DD.")
                return False
        else:
            if isinstance(edoj, str):
                edoj = datetime.strptime(edoj, "%Y-%m-%d").date()

        # Create Employee object matching the core schema
        emp = Employee(
            eid=eid,
            ename=ename,
            ecen=ecen,
            epos=epos,
            esal=esal,
            edoj=edoj,
            email=f"emp{eid}@staffsync.internal",
            status="ACTIVE"
        )
        db.add(emp)

        # Automatic Audit Log
        audit = AuditLog(
            user_id=1,
            username="CLI_ADMIN",
            action="EMPLOYEE_CREATED",
            target_entity=f"Employee #{eid}",
            new_value=f"Name: {ename}, Center: {ecen}, Pos: {epos}, Sal: {esal}, DOJ: {edoj}",
            client_ip="127.0.0.1"
        )
        db.add(audit)
        db.commit()
        print(f"Employee record for '{ename}' (ID: {eid}) added successfully!")
        return True
    except Exception as e:
        db.rollback()
        print(f"Error adding record: {e}")
        return False
    finally:
        db.close()


def updrec(eid, category=None, new_val=None):
    """Update employee details.
    Preserves original category menu while supporting programmatic updates.
    """
    db = SessionLocal()
    try:
        emp = db.query(Employee).filter(Employee.eid == eid).first()
        if not emp:
            print(f"INVALID Employee ID: {eid}")
            return False

        # Programmatic direct update
        if category is not None and new_val is not None:
            old_val = getattr(emp, category, "N/A")
            if category == "esal":
                new_val = float(new_val)
            elif category == "edoj" and isinstance(new_val, str):
                new_val = datetime.strptime(new_val, "%Y-%m-%d").date()
            setattr(emp, category, new_val)
            
            audit = AuditLog(
                user_id=1,
                username="CLI_ADMIN",
                action=f"UPDATE_{category.upper()}",
                target_entity=f"Employee #{eid}",
                old_value=f"{category}: {old_val}",
                new_value=f"{category}: {new_val}",
                client_ip="127.0.0.1"
            )
            db.add(audit)
            db.commit()
            return True

        # Interactive CLI update menu
        while True:
            print("\nUPDATE Categories:")
            print("\t1. Employee Name")
            print("\t2. Employee Centre")
            print("\t3. Employee Position")
            print("\t4. Employee Salary")
            print("\t5. Employee Date of Joining (yyyy-mm-dd)")
            print("\t6. Exit")
            chc_str = input("Enter your choice: ").strip()
            if not chc_str.isdigit():
                print("INVALID CHOICE")
                continue
            chc = int(chc_str)

            if chc == 1:
                print("Current Employee Name:", emp.ename)
                new_name = input("Enter Altered Employee Name: ").strip()
                emp.ename = new_name
                db.commit()
                print("Employee Name updated successfully!")
            elif chc == 2:
                print("Current Employee Centre:", emp.ecen)
                new_cen = input("Enter Altered Employee Centre: ").strip()
                emp.ecen = new_cen
                db.commit()
                print("Employee Centre updated successfully!")
            elif chc == 3:
                print("Current Employee Position:", emp.epos)
                new_pos = input("Enter Altered Employee Position: ").strip()
                emp.epos = new_pos
                db.commit()
                print("Employee Position updated successfully!")
            elif chc == 4:
                print("Current Employee Salary:", emp.esal)
                new_sal_str = input("Enter Altered Employee Salary: ").strip()
                if new_sal_str.isdigit():
                    emp.esal = float(new_sal_str)
                    db.commit()
                    print("Employee Salary updated successfully!")
                else:
                    print("Invalid salary format!")
            elif chc == 5:
                print("Current Employee Date of Joining (yyyy-mm-dd):", emp.edoj)
                new_doj_str = input("Enter Altered Employee Date of Joining (yyyy-mm-dd): ").strip()
                try:
                    emp.edoj = datetime.strptime(new_doj_str, "%Y-%m-%d").date()
                    db.commit()
                    print("Employee DOJ updated successfully!")
                except ValueError:
                    print("Invalid date format!")
            elif chc == 6:
                break
            else:
                print("INVALID CHOICE")
        return True
    except Exception as e:
        db.rollback()
        print(f"Error updating record: {e}")
        return False
    finally:
        db.close()


def disrec(eid):
    """Display an employee's details."""
    db = SessionLocal()
    try:
        emp = db.query(Employee).filter(Employee.eid == eid).first()
        if emp:
            print("-" * 50)
            print(f"Employee ID:       {emp.eid}")
            print(f"Employee Name:     {emp.ename}")
            print(f"Employee Centre:   {emp.ecen}")
            print(f"Employee Position: {emp.epos}")
            print(f"Employee Salary:   Rs. {emp.esal:,.2f}")
            print(f"Employee DOJ:      {emp.edoj}")
            print(f"Employee Status:   {emp.status}")
            print("-" * 50)
            return emp
        else:
            print(f"INVALID Employee ID: {eid}")
            return None
    finally:
        db.close()


def delrec(eid):
    """Delete an employee record."""
    db = SessionLocal()
    try:
        emp = db.query(Employee).filter(Employee.eid == eid).first()
        if emp:
            emp_name = emp.ename
            # Log deletion audit
            audit = AuditLog(
                user_id=1,
                username="CLI_ADMIN",
                action="EMPLOYEE_DELETED",
                target_entity=f"Employee #{eid}",
                old_value=f"Name: {emp_name}, Pos: {emp.epos}, Sal: {emp.esal}",
                client_ip="127.0.0.1"
            )
            db.add(audit)
            db.delete(emp)
            db.commit()
            print(f"Employee Record for '{emp_name}' (ID: {eid}) Deleted successfully.")
            return True
        else:
            print(f"INVALID Employee ID: {eid}")
            return False
    except Exception as e:
        db.rollback()
        print(f"Error deleting record: {e}")
        return False
    finally:
        db.close()


def cli_menu():
    """Terminal Menu Loop (Preserving the exact menu from your original code)."""
    while True:
        print("\n" + "-" * 15, "EMPLOYEE MANAGEMENT MENU", "-" * 15)
        print("\t1. Add Record")
        print("\t2. Display Record")
        print("\t3. Update Record")
        print("\t4. Delete Record")
        print("\t5. Exit CLI")
        choice_str = input("Enter your choice: ").strip()
        if not choice_str.isdigit():
            print("Invalid Choice")
            continue
        choice = int(choice_str)

        if choice == 1:
            n_str = input("Number of Records to ADD: ").strip()
            if n_str.isdigit():
                n = int(n_str)
                for _ in range(n):
                    print("-" * 5)
                    addrec()
            else:
                print("Invalid number.")
        elif choice == 2:
            eid_str = input("Enter Employee ID: ").strip()
            if eid_str.isdigit():
                disrec(int(eid_str))
            else:
                print("Invalid Employee ID")
        elif choice == 3:
            eid_str = input("Enter Employee ID: ").strip()
            if eid_str.isdigit():
                updrec(int(eid_str))
            else:
                print("Invalid Employee ID")
        elif choice == 4:
            ask_str = input("Enter Employee ID: ").strip()
            if ask_str.isdigit():
                delrec(int(ask_str))
            else:
                print("Invalid Employee ID")
        elif choice == 5:
            print("Exiting CLI Mode. Goodbye!")
            break
        else:
            print("Invalid Choice")


if __name__ == "__main__":
    cli_menu()
