import io
import os
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from app.models.employee import Employee
from app.models.payroll import PayrollRecord
from app.services.audit_service import record_audit

# Two decimal place quantization standard
TWOPLACES = Decimal('0.01')


def quantize_money(val: Any) -> Decimal:
    """Convert value to Decimal and quantize to 2 decimal places with standard financial rounding."""
    if val is None:
        return Decimal('0.00')
    if not isinstance(val, Decimal):
        val = Decimal(str(val))
    return val.quantize(TWOPLACES, rounding=ROUND_HALF_UP)


def calculate_salary_breakdown(monthly_salary: Any) -> Dict[str, Decimal]:
    """
    Calculate salary breakdown components and deductions with pure Decimal precision:
    - Base Salary: 50%
    - HRA: 20%
    - Special Allowance: 30%
    - PF Deduction: 12% of Basic
    - Progressive Income Tax
    """
    salary = quantize_money(monthly_salary)

    base_salary = (salary * Decimal('0.50')).quantize(TWOPLACES, rounding=ROUND_HALF_UP)
    hra = (salary * Decimal('0.20')).quantize(TWOPLACES, rounding=ROUND_HALF_UP)
    allowance = (salary * Decimal('0.30')).quantize(TWOPLACES, rounding=ROUND_HALF_UP)
    gross_salary = base_salary + hra + allowance

    # Deductions
    pf_deduction = (base_salary * Decimal('0.12')).quantize(TWOPLACES, rounding=ROUND_HALF_UP)

    # Progressive tax estimation (Decimal)
    if salary > Decimal('100000.00'):
        tax_deduction = (salary * Decimal('0.10')).quantize(TWOPLACES, rounding=ROUND_HALF_UP)
    elif salary > Decimal('50000.00'):
        tax_deduction = (salary * Decimal('0.05')).quantize(TWOPLACES, rounding=ROUND_HALF_UP)
    else:
        tax_deduction = Decimal('200.00')  # Minimum professional tax

    net_salary = gross_salary - pf_deduction - tax_deduction

    return {
        "base_salary": base_salary,
        "hra": hra,
        "allowance": allowance,
        "gross_salary": gross_salary,
        "pf_deduction": pf_deduction,
        "tax_deduction": tax_deduction,
        "net_salary": net_salary
    }


def generate_payroll_for_month(
    db: Session,
    month_year: str,
    center: Optional[str] = None,
    current_user: Optional[Dict[str, Any]] = None
) -> List[PayrollRecord]:
    """Run batch payroll calculation and persist Decimal records."""
    query = db.query(Employee).filter(Employee.status == "ACTIVE")
    if center and center != "ALL":
        query = query.filter(Employee.ecen == center)

    employees = query.all()
    created_records = []
    now = datetime.now(timezone.utc)

    for emp in employees:
        existing = db.query(PayrollRecord).filter(
            PayrollRecord.employee_id == emp.eid,
            PayrollRecord.month_year == month_year
        ).first()

        breakdown = calculate_salary_breakdown(emp.esal)

        if existing:
            # Update existing draft/calculated record
            existing.base_salary = breakdown["base_salary"]
            existing.hra = breakdown["hra"]
            existing.allowance = breakdown["allowance"]
            existing.gross_salary = breakdown["gross_salary"]
            existing.pf_deduction = breakdown["pf_deduction"]
            existing.tax_deduction = breakdown["tax_deduction"]
            existing.net_salary = breakdown["net_salary"]
            existing.payment_status = "PAID"
            existing.generated_at = now
            created_records.append(existing)
        else:
            record = PayrollRecord(
                employee_id=emp.eid,
                month_year=month_year,
                base_salary=breakdown["base_salary"],
                hra=breakdown["hra"],
                allowance=breakdown["allowance"],
                gross_salary=breakdown["gross_salary"],
                pf_deduction=breakdown["pf_deduction"],
                tax_deduction=breakdown["tax_deduction"],
                net_salary=breakdown["net_salary"],
                payment_status="PAID",
                generated_at=now
            )
            db.add(record)
            created_records.append(record)

    db.commit()

    username = current_user.get("username", "ADMIN") if current_user else "ADMIN"
    user_id = current_user.get("id") if current_user else 1
    record_audit(
        db=db,
        action="PAYROLL_BATCH_GENERATED",
        target_entity=f"Month: {month_year} (Processed: {len(created_records)} records)",
        user_id=user_id,
        username=username,
        new_value=f"Center: {center or 'ALL'}, Count: {len(created_records)}"
    )

    return created_records


# =============================================================================
# ReportLab PDF Payslip Generator with Cross-Platform Unicode Font Support
# =============================================================================

FONT_NAME = "Helvetica"
FONT_NAME_BOLD = "Helvetica-Bold"
CURRENCY_PREFIX = "₹"


def init_pdf_fonts():
    """Register TrueType Unicode fonts for Linux/Docker and Windows environments."""
    global FONT_NAME, FONT_NAME_BOLD, CURRENCY_PREFIX

    font_candidates = [
        # Linux / Docker Debian fonts
        ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
        ("/usr/share/fonts/truetype/freefont/FreeSans.ttf", "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf"),
        # Windows system fonts
        ("C:/Windows/Fonts/segoeui.ttf", "C:/Windows/Fonts/segoeuib.ttf"),
        ("C:/Windows/Fonts/arial.ttf", "C:/Windows/Fonts/arialbd.ttf"),
        ("C:/Windows/Fonts/Nirmala.ttf", "C:/Windows/Fonts/NirmalaB.ttf")
    ]

    for regular, bold in font_candidates:
        if os.path.exists(regular) and os.path.exists(bold):
            try:
                pdfmetrics.registerFont(TTFont('AppFont', regular))
                pdfmetrics.registerFont(TTFont('AppFont-Bold', bold))
                FONT_NAME = 'AppFont'
                FONT_NAME_BOLD = 'AppFont-Bold'
                CURRENCY_PREFIX = "₹"
                return
            except Exception:
                continue

    FONT_NAME = "Helvetica"
    FONT_NAME_BOLD = "Helvetica-Bold"
    CURRENCY_PREFIX = "Rs. "


init_pdf_fonts()


def format_inr(val: Any) -> str:
    """Format decimal amount with Indian Rupee formatting."""
    d = quantize_money(val)
    return f"{CURRENCY_PREFIX}{d:,.2f}"


def generate_payslip_pdf(payroll: PayrollRecord) -> io.BytesIO:
    """Generate a styled, corporate PDF payslip using ReportLab with native Rupee symbol."""
    init_pdf_fonts()
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        'DocTitle',
        fontName=FONT_NAME_BOLD,
        fontSize=20,
        leading=24,
        textColor=colors.HexColor("#0F172A"),
        alignment=TA_CENTER,
        spaceAfter=4
    )
    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        fontName=FONT_NAME,
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#64748B"),
        alignment=TA_CENTER,
        spaceAfter=15
    )
    section_title = ParagraphStyle(
        'SectionTitle',
        fontName=FONT_NAME_BOLD,
        fontSize=12,
        leading=16,
        textColor=colors.HexColor("#1E293B"),
        spaceBefore=10,
        spaceAfter=6
    )
    body_style = ParagraphStyle(
        'BodyDark',
        fontName=FONT_NAME,
        fontSize=9,
        leading=13,
        textColor=colors.HexColor("#334155")
    )
    body_bold_style = ParagraphStyle(
        'BodyDarkBold',
        fontName=FONT_NAME_BOLD,
        fontSize=9,
        leading=13,
        textColor=colors.HexColor("#0F172A")
    )
    body_right_style = ParagraphStyle(
        'BodyDarkRight',
        fontName=FONT_NAME,
        fontSize=9,
        leading=13,
        textColor=colors.HexColor("#334155"),
        alignment=TA_RIGHT
    )
    body_bold_right_style = ParagraphStyle(
        'BodyDarkBoldRight',
        fontName=FONT_NAME_BOLD,
        fontSize=9,
        leading=13,
        textColor=colors.HexColor("#0F172A"),
        alignment=TA_RIGHT
    )

    elements = []

    # Header
    elements.append(Paragraph("STAFFSYNC 360 ENTERPRISE", title_style))
    elements.append(Paragraph(f"Official Payslip Statement — Cycle: <b>{payroll.month_year}</b>", subtitle_style))
    elements.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#6366F1"), spaceBefore=0, spaceAfter=15))

    # Employee Details Grid
    emp = payroll.employee
    emp_details = [
        [
            Paragraph("<b>Employee ID:</b>", body_style),
            Paragraph(f"#{payroll.employee_id}", body_bold_style),
            Paragraph("<b>Payment Cycle:</b>", body_style),
            Paragraph(f"{payroll.month_year}", body_bold_style)
        ],
        [
            Paragraph("<b>Employee Name:</b>", body_style),
            Paragraph(f"{emp.ename if emp else 'N/A'}", body_bold_style),
            Paragraph("<b>Payment Status:</b>", body_style),
            Paragraph(f"<font color='#059669'><b>{payroll.payment_status}</b></font>", body_bold_style)
        ],
        [
            Paragraph("<b>Regional Branch:</b>", body_style),
            Paragraph(f"{emp.ecen if emp else 'N/A'}", body_style),
            Paragraph("<b>Designation:</b>", body_style),
            Paragraph(f"{emp.epos if emp else 'N/A'}", body_style)
        ],
        [
            Paragraph("<b>Work Email:</b>", body_style),
            Paragraph(f"{emp.email if emp else 'N/A'}", body_style),
            Paragraph("<b>Date of Joining:</b>", body_style),
            Paragraph(f"{emp.edoj.strftime('%d-%b-%Y') if emp and emp.edoj else 'N/A'}", body_style)
        ]
    ]

    t_emp = Table(emp_details, colWidths=[110, 155, 110, 155])
    t_emp.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor("#E2E8F0")),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
    ]))
    elements.append(t_emp)
    elements.append(Spacer(1, 15))

    # Earnings & Deductions Breakdown
    elements.append(Paragraph("COMPENSATION BREAKDOWN & DEDUCTIONS", section_title))

    breakdown_data = [
        [
            Paragraph("<b>Earnings Component</b>", body_bold_style),
            Paragraph("<b>Amount (INR)</b>", body_bold_right_style),
            Paragraph("<b>Deduction Component</b>", body_bold_style),
            Paragraph("<b>Amount (INR)</b>", body_bold_right_style)
        ],
        [
            Paragraph("Basic Pay (50%)", body_style),
            Paragraph(format_inr(payroll.base_salary), body_right_style),
            Paragraph("Provident Fund (PF 12%)", body_style),
            Paragraph(format_inr(payroll.pf_deduction), body_right_style)
        ],
        [
            Paragraph("House Rent Allowance (HRA 20%)", body_style),
            Paragraph(format_inr(payroll.hra), body_right_style),
            Paragraph("Income / Professional Tax", body_style),
            Paragraph(format_inr(payroll.tax_deduction), body_right_style)
        ],
        [
            Paragraph("Special / Flexi Allowance (30%)", body_style),
            Paragraph(format_inr(payroll.allowance), body_right_style),
            Paragraph("Other Statutory Deductions", body_style),
            Paragraph(format_inr(Decimal('0.00')), body_right_style)
        ],
        [
            Paragraph("<b>Gross Earnings:</b>", body_bold_style),
            Paragraph(f"<b>{format_inr(payroll.gross_salary)}</b>", body_bold_right_style),
            Paragraph("<b>Total Deductions:</b>", body_bold_style),
            Paragraph(f"<b><font color='#DC2626'>{format_inr(payroll.pf_deduction + payroll.tax_deduction)}</font></b>", body_bold_right_style)
        ]
    ]

    t_breakdown = Table(breakdown_data, colWidths=[165, 100, 165, 100])
    t_breakdown.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#EEF2FF")),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor("#CBD5E1")),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
        ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor("#F1F5F9")),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
    ]))
    elements.append(t_breakdown)
    elements.append(Spacer(1, 15))

    # Net Take-Home Pay Box
    net_box_data = [
        [
            Paragraph("<b>NET DISBURSED TAKE-HOME PAY:</b>", ParagraphStyle('NetLbl', fontName=FONT_NAME_BOLD, fontSize=11, textColor=colors.HexColor("#065F46"))),
            Paragraph(f"<b>{format_inr(payroll.net_salary)}</b>", ParagraphStyle('NetVal', fontName=FONT_NAME_BOLD, fontSize=14, alignment=TA_RIGHT, textColor=colors.HexColor("#065F46")))
        ]
    ]
    t_net = Table(net_box_data, colWidths=[330, 200])
    t_net.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#D1FAE5")),
        ('BOX', (0, 0), (-1, -1), 1.5, colors.HexColor("#10B981")),
        ('TOPPADDING', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ('LEFTPADDING', (0, 0), (-1, -1), 12),
        ('RIGHTPADDING', (0, 0), (-1, -1), 12),
    ]))
    elements.append(t_net)
    elements.append(Spacer(1, 20))

    # Footer
    footer_style = ParagraphStyle(
        'FooterStyle',
        fontName=FONT_NAME,
        fontSize=8,
        leading=11,
        textColor=colors.HexColor("#94A3B8"),
        alignment=TA_CENTER
    )
    elements.append(Paragraph(
        f"This document is an electronically verified payslip generated automatically by StaffSync 360 on {payroll.generated_at.strftime('%d-%b-%Y %H:%M:%S UTC') if payroll.generated_at else 'N/A'}. No physical signature required.",
        footer_style
    ))

    doc.build(elements)
    buffer.seek(0)
    return buffer
