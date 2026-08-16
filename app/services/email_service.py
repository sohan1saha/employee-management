"""
==============================================================================
StaffSync 360 - Notification & Email Dispatch Service
==============================================================================
Handles automated in-app alerts and asynchronous email dispatch for:
- Leave Application & Approval/Rejection
- Monthly Payroll Payslip Generation
- Performance Appraisals & Feedback
"""

import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional, List
from sqlalchemy.orm import Session
from app.core.config import settings
from app.models.notification import Notification
from app.models.user import User

logger = logging.getLogger("staffsync.notifications")


def create_in_app_notification(
    db: Session,
    user_id: int,
    title: str,
    message: str,
    category: str = "SYSTEM",
    action_url: Optional[str] = None
) -> Notification:
    """Create a persistent in-app notification for a user."""
    try:
        notif = Notification(
            user_id=user_id,
            title=title,
            message=message,
            category=category,
            action_url=action_url,
            is_read=False
        )
        db.add(notif)
        db.commit()
        db.refresh(notif)
        return notif
    except Exception as e:
        logger.error(f"Failed to create in-app notification for user {user_id}: {e}")
        db.rollback()
        return None


def notify_leave_status(
    db: Session,
    employee_id: int,
    leave_type: str,
    status: str,
    days_count: int,
    reviewer_name: str
):
    """Notify employee when their leave request status updates."""
    user = db.query(User).filter(User.employee_id == employee_id).first()
    if not user:
        return

    status_display = "approved" if status == "APPROVED" else "rejected"
    title = f"Leave Request {status.capitalize()}"
    message = (
        f"Your application for {days_count} day(s) of {leave_type} has been {status_display} "
        f"by {reviewer_name}."
    )
    create_in_app_notification(
        db=db,
        user_id=user.id,
        title=title,
        message=message,
        category="LEAVE",
        action_url="#leaves"
    )


def notify_payroll_generated(
    db: Session,
    employee_id: int,
    pay_period: str,
    net_salary: float
):
    """Notify employee when their monthly payslip is generated."""
    user = db.query(User).filter(User.employee_id == employee_id).first()
    if not user:
        return

    title = f"Payslip Available: {pay_period}"
    message = (
        f"Your official payroll record for {pay_period} has been processed. "
        f"Net Pay: ₹{net_salary:,.2f}. You can view and download your PDF payslip from the dashboard."
    )
    create_in_app_notification(
        db=db,
        user_id=user.id,
        title=title,
        message=message,
        category="PAYROLL",
        action_url="#payslips"
    )


def notify_performance_review(
    db: Session,
    employee_id: int,
    review_period: str,
    rating: float
):
    """Notify employee when a performance appraisal review is submitted."""
    user = db.query(User).filter(User.employee_id == employee_id).first()
    if not user:
        return

    title = f"Performance Appraisal: {review_period}"
    message = (
        f"Your manager has published your performance review for {review_period} "
        f"(Rating: {rating:.1f}/5.0). Please review and acknowledge in your dashboard."
    )
    create_in_app_notification(
        db=db,
        user_id=user.id,
        title=title,
        message=message,
        category="APPRAISAL",
        action_url="#performance"
    )


def send_email_async(
    to_email: str,
    subject: str,
    html_content: str
) -> bool:
    """
    Dispatch email using SMTP. Falls back gracefully to logged simulation when SMTP is unconfigured.
    """
    smtp_host = getattr(settings, "SMTP_HOST", None)
    smtp_port = getattr(settings, "SMTP_PORT", 587)
    smtp_user = getattr(settings, "SMTP_USER", None)
    smtp_pass = getattr(settings, "SMTP_PASSWORD", None)

    if not smtp_host or not smtp_user or not smtp_pass:
        logger.info(f"[SIMULATED EMAIL] To: {to_email} | Subject: {subject}")
        return True

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"StaffSync 360 <{smtp_user}>"
        msg["To"] = to_email
        msg.attach(MIMEText(html_content, "html"))

        with smtplib.SMTP(smtp_host, smtp_port, timeout=10) as server:
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.sendmail(smtp_user, to_email, msg.as_string())

        logger.info(f"[EMAIL SENT] Successfully dispatched to {to_email}")
        return True
    except Exception as e:
        logger.warning(f"[EMAIL WARNING] Could not send live email to {to_email}: {e}")
        return False
