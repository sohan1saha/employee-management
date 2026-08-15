import io
from datetime import datetime
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT

from app.models.employee import Employee
from app.models.payroll import PayrollRecord
from app.services.audit_service import record_audit


def calculate_salary_breakdown(monthly_salary: float) -> Dict[str, float]:
    """Calculate salary breakdown components and deductions."""
    base_salary = round(monthly_salary * 0.50, 2)     # 50%
    hra = round(monthly_salary * 0.20, 2)             # 20%
    allowance = round(monthly_salary * 0.30, 2)       # 30%
    gross_salary = base_salary + hra + allowance

    # Deductions
    pf_deduction = round(base_salary * 0.12, 2)       # 12% of Basic

    # Progressive tax estimation
    if monthly_salary > 100000:
        tax_deduction = round(monthly_salary * 0.10, 2)
    elif monthly_salary > 50000:
        tax_deduction = round(monthly_salary * 0.05, 2)
    else:
        tax_deduction = 200.0  # Flat minimum professional tax

    net_salary = round(gross_salary - pf_deduction - tax_deduction, 2)

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
    """Run payroll batch for all active employees (or filtered by center)."""
    query = db.query(Employee).filter(Employee.status == "ACTIVE")
    if center and center != "ALL":
        query = query.filter(Employee.ecen == center)
    
    employees = query.all()
    created_records = []

    for emp in employees:
        # Check if payroll already exists for this employee for this month
        existing = db.query(PayrollRecord).filter(
            PayrollRecord.employee_id == emp.eid,
            PayrollRecord.month_year == month_year
        ).first()

        breakdown = calculate_salary_breakdown(emp.esal)

        if existing:
            # Update existing record
            existing.base_salary = breakdown["base_salary"]
            existing.hra = breakdown["hra"]
            existing.allowance = breakdown["allowance"]
            existing.gross_salary = breakdown["gross_salary"]
            existing.pf_deduction = breakdown["pf_deduction"]
            existing.tax_deduction = breakdown["tax_deduction"]
            existing.net_salary = breakdown["net_salary"]
            existing.payment_status = "PAID"
            existing.generated_at = datetime.utcnow()
            created_records.append(existing)
        else:
            # Create new payroll record
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
                payment_status="PAID"
            )
            db.add(record)
            created_records.append(record)

    db.commit()

    # Record Audit Log
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


import os
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# Register Unicode TrueType font that natively contains the Rupee symbol ₹
FONT_NAME = "Helvetica"
FONT_NAME_BOLD = "Helvetica-Bold"
CURRENCY_PREFIX = "₹"


def init_pdf_fonts():
    global FONT_NAME, FONT_NAME_BOLD, CURRENCY_PREFIX
    font_candidates = [
        ("C:/Windows/Fonts/segoeui.ttf", "C:/Windows/Fonts/segoeuib.ttf"),
        ("C:/Windows/Fonts/arial.ttf", "C:/Windows/Fonts/arialbd.ttf"),
        ("C:/Windows/Fonts/calibri.ttf", "C:/Windows/Fonts/calibrib.ttf"),
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
    # Fallback to ASCII Rs. if no Unicode TTF is registered
    FONT_NAME = "Helvetica"
    FONT_NAME_BOLD = "Helvetica-Bold"
    CURRENCY_PREFIX = "Rs. "


init_pdf_fonts()


def generate_payslip_pdf(payroll: PayrollRecord) -> io.BytesIO:
    """Generate a styled, corporate PDF payslip using ReportLab with clean Rupee symbol support."""
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
    
    # Custom styles using TrueType Unicode font
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
    net_pay_style = ParagraphStyle(
        'NetPay',
        fontName=FONT_NAME_BOLD,
        fontSize=15,
        leading=18,
        textColor=colors.HexColor("#059669"),
        alignment=TA_RIGHT
    )

    story = []

    # Header
    story.append(Paragraph("STAFFSYNC 360 ENTERPRISE", title_style))
    story.append(Paragraph(f"Official Payslip — Billing Period: {payroll.month_year}", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#CBD5E1"), spaceAfter=15))

    # Employee Information Table
    emp = payroll.employee
    emp_info_data = [
        [
            Paragraph(f"<b>Employee ID:</b> {payroll.employee_id}", body_style),
            Paragraph(f"<b>Date of Joining:</b> {emp.edoj if emp else 'N/A'}", body_style)
        ],
        [
            Paragraph(f"<b>Employee Name:</b> {emp.ename if emp else 'N/A'}", body_style),
            Paragraph(f"<b>Designation:</b> {emp.epos if emp else 'N/A'}", body_style)
        ],
        [
            Paragraph(f"<b>Center / Branch:</b> {emp.ecen if emp else 'N/A'}", body_style),
            Paragraph(f"<b>Payment Status:</b> <font color='#059669'><b>{payroll.payment_status}</b></font>", body_style)
        ]
    ]

    emp_table = Table(emp_info_data, colWidths=[260, 260])
    emp_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor("#E2E8F0")),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
        ('PADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(emp_table)
    story.append(Spacer(1, 15))

    # Earnings & Deductions Breakdown
    story.append(Paragraph("Salary & Compensation Breakdown", section_title))

    breakdown_data = [
        [
            Paragraph("<b>Earnings Component</b>", body_style),
            Paragraph("<b>Amount (INR)</b>", body_right_style),
            Paragraph("<b>Deduction Component</b>", body_style),
            Paragraph("<b>Amount (INR)</b>", body_right_style)
        ],
        [
            Paragraph("Basic Pay (50%)", body_style),
            Paragraph(f"{CURRENCY_PREFIX}{payroll.base_salary:,.2f}", body_right_style),
            Paragraph("Provident Fund (PF 12%)", body_style),
            Paragraph(f"{CURRENCY_PREFIX}{payroll.pf_deduction:,.2f}", body_right_style)
        ],
        [
            Paragraph("House Rent Allowance (HRA 20%)", body_style),
            Paragraph(f"{CURRENCY_PREFIX}{payroll.hra:,.2f}", body_right_style),
            Paragraph("Income / Professional Tax", body_style),
            Paragraph(f"{CURRENCY_PREFIX}{payroll.tax_deduction:,.2f}", body_right_style)
        ],
        [
            Paragraph("Special Allowance (30%)", body_style),
            Paragraph(f"{CURRENCY_PREFIX}{payroll.allowance:,.2f}", body_right_style),
            Paragraph("", body_style),
            Paragraph("", body_right_style)
        ],
        [
            Paragraph("<b>Total Gross Earnings</b>", body_bold_style),
            Paragraph(f"<b>{CURRENCY_PREFIX}{payroll.gross_salary:,.2f}</b>", body_bold_right_style),
            Paragraph("<b>Total Deductions</b>", body_bold_style),
            Paragraph(f"<b>{CURRENCY_PREFIX}{(payroll.pf_deduction + payroll.tax_deduction):,.2f}</b>", body_bold_right_style)
        ]
    ]

    breakdown_table = Table(breakdown_data, colWidths=[150, 110, 150, 110])
    breakdown_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#EDE9FE")),
        ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor("#F1F5F9")),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
        ('PADDING', (0, 0), (-1, -1), 6),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    story.append(breakdown_table)
    story.append(Spacer(1, 15))

    # Net Salary Summary Callout
    net_summary_data = [
        [
            Paragraph("<b>NET TAKE-HOME PAY</b><br/><font size=8 color='#64748B'>Direct bank transfer to registered account</font>", body_style),
            Paragraph(f"<b>{CURRENCY_PREFIX}{payroll.net_salary:,.2f}</b>", net_pay_style)
        ]
    ]
    net_table = Table(net_summary_data, colWidths=[320, 200])
    net_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#ECFDF5")),
        ('BOX', (0, 0), (-1, -1), 1.5, colors.HexColor("#10B981")),
        ('PADDING', (0, 0), (-1, -1), 10),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    story.append(net_table)
    story.append(Spacer(1, 30))

    # Signature / Verification Footer
    footer_data = [
        [
            Paragraph("<i>This is a computer-generated payslip and requires no physical signature.</i>", subtitle_style),
            Paragraph("<b>Authorized Signatory</b><br/>StaffSync 360 HR Team", ParagraphStyle('Sign', fontName=FONT_NAME, alignment=TA_RIGHT, fontSize=9, leading=12))
        ]
    ]
    footer_table = Table(footer_data, colWidths=[340, 180])
    story.append(footer_table)

    # Build document
    doc.build(story)
    buffer.seek(0)
    return buffer
