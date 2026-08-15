from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.employee import Employee
from app.models.leave import LeaveRequest
from app.models.payroll import PayrollRecord


def get_dashboard_analytics(db: Session, center: Optional[str] = None) -> Dict[str, Any]:
    """Compute company-wide or center-scoped workforce metrics."""
    emp_query = db.query(Employee)
    if center and center != "ALL":
        emp_query = emp_query.filter(Employee.ecen == center)

    # 1. Total employees by status
    total_employees = emp_query.count()
    active_employees = emp_query.filter(Employee.status == "ACTIVE").count()
    on_leave_employees = emp_query.filter(Employee.status == "ON_LEAVE").count()

    # 2. Monthly payroll burn rate (sum of esal for active employees)
    payroll_query = db.query(func.sum(Employee.esal)).filter(Employee.status == "ACTIVE")
    if center and center != "ALL":
        payroll_query = payroll_query.filter(Employee.ecen == center)
    total_monthly_payroll = payroll_query.scalar() or 0.0

    # 3. Pending leave requests
    leave_query = db.query(LeaveRequest).join(Employee).filter(LeaveRequest.status == "PENDING")
    if center and center != "ALL":
        leave_query = leave_query.filter(Employee.ecen == center)
    pending_leaves = leave_query.count()

    # 4. Center-wise aggregation
    center_agg = db.query(
        Employee.ecen,
        func.count(Employee.eid).label("headcount"),
        func.sum(Employee.esal).label("total_payroll"),
        func.avg(Employee.esal).label("avg_salary")
    ).filter(Employee.status == "ACTIVE")

    if center and center != "ALL":
        center_agg = center_agg.filter(Employee.ecen == center)

    center_stats = center_agg.group_by(Employee.ecen).all()

    centers_data = [
        {
            "center": stat.ecen,
            "headcount": stat.headcount,
            "total_payroll": round(float(stat.total_payroll or 0), 2),
            "avg_salary": round(float(stat.avg_salary or 0), 2)
        }
        for stat in center_stats
    ]

    # 5. Position distribution
    pos_agg = db.query(
        Employee.epos,
        func.count(Employee.eid).label("count")
    ).filter(Employee.status == "ACTIVE")

    if center and center != "ALL":
        pos_agg = pos_agg.filter(Employee.ecen == center)

    position_stats = pos_agg.group_by(Employee.epos).all()

    positions_data = [
        {"position": stat.epos, "count": stat.count}
        for stat in position_stats
    ]

    return {
        "kpis": {
            "total_employees": total_employees,
            "active_employees": active_employees,
            "on_leave_employees": on_leave_employees,
            "monthly_payroll_burn": round(float(total_monthly_payroll), 2),
            "pending_leaves": pending_leaves,
            "total_centers": len(centers_data)
        },
        "center_distribution": centers_data,
        "position_distribution": positions_data
    }


def get_employee_dashboard_analytics(db: Session, employee_id: int) -> Dict[str, Any]:
    """Compute personalized metrics and quick self-service information for an individual employee."""
    emp = db.query(Employee).filter(Employee.eid == employee_id).first()
    if not emp:
        return {"is_employee_portal": True, "error": "Employee record not found"}

    from app.services.payroll_service import calculate_salary_breakdown
    salary_breakdown = calculate_salary_breakdown(emp.esal)

    # Leaves summary
    leaves = db.query(LeaveRequest).filter(LeaveRequest.employee_id == employee_id).order_by(LeaveRequest.id.desc()).all()
    approved_leaves = [l for l in leaves if l.status == "APPROVED"]
    pending_leaves = [l for l in leaves if l.status == "PENDING"]
    days_taken = sum(l.days_count for l in approved_leaves)
    total_allowance = 24
    balance_days = max(0, total_allowance - days_taken)

    # Recent payslips
    payslips = db.query(PayrollRecord).filter(PayrollRecord.employee_id == employee_id).order_by(PayrollRecord.id.desc()).limit(5).all()

    # Center holiday calendar
    holidays = [
        {"name": "Republic Day", "date": "2026-01-26", "type": "National"},
        {"name": "Labor Day", "date": "2026-05-01", "type": "Statutory"},
        {"name": "Independence Day", "date": "2026-08-15", "type": "National"},
        {"name": "Gandhi Jayanti", "date": "2026-10-02", "type": "National"},
        {"name": "Diwali Festival", "date": "2026-11-08", "type": "Festival"},
        {"name": "Christmas Day", "date": "2026-12-25", "type": "Public"}
    ]

    return {
        "is_employee_portal": True,
        "employee": emp.to_dict(),
        "salary_breakdown": salary_breakdown,
        "kpis": {
            "monthly_gross": emp.esal,
            "monthly_net": salary_breakdown["net_salary"],
            "leave_balance": balance_days,
            "days_taken": days_taken,
            "pending_leaves": len(pending_leaves),
            "status": emp.status,
            "joining_date": str(emp.edoj)
        },
        "recent_leaves": [l.to_dict() for l in leaves[:5]],
        "recent_payslips": [p.to_dict() for p in payslips],
        "holidays": holidays
    }
