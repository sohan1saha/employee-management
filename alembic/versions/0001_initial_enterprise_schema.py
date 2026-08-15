"""initial_enterprise_schema

Revision ID: 0001_initial_schema
Revises: 
Create Date: 2026-08-16 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '0001_initial_schema'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Employees Table with Decimal Numeric(12,2) and Constraints
    op.create_table(
        'employees',
        sa.Column('eid', sa.Integer(), primary_key=True, index=True),
        sa.Column('ename', sa.String(length=100), nullable=False, index=True),
        sa.Column('ecen', sa.String(length=60), nullable=False, index=True),
        sa.Column('epos', sa.String(length=80), nullable=False),
        sa.Column('esal', sa.Numeric(12, 2), nullable=False),
        sa.Column('edoj', sa.Date(), nullable=False),
        sa.Column('email', sa.String(length=120), nullable=False, unique=True, index=True),
        sa.Column('status', sa.String(length=20), server_default='ACTIVE', nullable=False, index=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.CheckConstraint('esal >= 0', name='chk_employee_salary_positive')
    )
    op.create_index('ix_emp_center_status', 'employees', ['ecen', 'status'])

    # 2. Users Table with Lockout and Audit Columns
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('employee_id', sa.Integer(), sa.ForeignKey('employees.eid'), nullable=False, unique=True, index=True),
        sa.Column('email', sa.String(length=120), nullable=False, unique=True, index=True),
        sa.Column('hashed_password', sa.String(length=255), nullable=False),
        sa.Column('role', sa.String(length=20), server_default='EMPLOYEE', nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default='1', nullable=False),
        sa.Column('failed_login_attempts', sa.Integer(), server_default='0', nullable=False),
        sa.Column('locked_until', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False)
    )

    # 3. Payroll Records Table with High Precision Numeric & Unique Constraint
    op.create_table(
        'payroll_records',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('employee_id', sa.Integer(), sa.ForeignKey('employees.eid'), nullable=False, index=True),
        sa.Column('month_year', sa.String(length=7), nullable=False, index=True),
        sa.Column('base_salary', sa.Numeric(12, 2), nullable=False),
        sa.Column('hra', sa.Numeric(12, 2), nullable=False),
        sa.Column('allowance', sa.Numeric(12, 2), nullable=False),
        sa.Column('gross_salary', sa.Numeric(12, 2), nullable=False),
        sa.Column('pf_deduction', sa.Numeric(12, 2), nullable=False),
        sa.Column('tax_deduction', sa.Numeric(12, 2), nullable=False),
        sa.Column('net_salary', sa.Numeric(12, 2), nullable=False),
        sa.Column('payment_status', sa.String(length=20), server_default='PAID', nullable=False, index=True),
        sa.Column('approved_by', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('approved_at', sa.DateTime(), nullable=True),
        sa.Column('generated_at', sa.DateTime(), nullable=False),
        sa.UniqueConstraint('employee_id', 'month_year', name='uq_payroll_emp_month')
    )
    op.create_index('ix_payroll_month_center', 'payroll_records', ['month_year'])

    # 4. Leave Requests Table
    op.create_table(
        'leave_requests',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('employee_id', sa.Integer(), sa.ForeignKey('employees.eid'), nullable=False, index=True),
        sa.Column('leave_type', sa.String(length=30), nullable=False),
        sa.Column('start_date', sa.Date(), nullable=False),
        sa.Column('end_date', sa.Date(), nullable=False),
        sa.Column('days_count', sa.Integer(), nullable=False),
        sa.Column('reason', sa.Text(), nullable=False),
        sa.Column('status', sa.String(length=20), server_default='PENDING', nullable=False, index=True),
        sa.Column('applied_at', sa.DateTime(), nullable=False),
        sa.Column('reviewed_by', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('review_comment', sa.Text(), nullable=True)
    )
    op.create_index('ix_leave_emp_status', 'leave_requests', ['employee_id', 'status'])

    # 5. Audit Logs Table (Append-Only)
    op.create_table(
        'audit_logs',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('username', sa.String(length=50), nullable=False),
        sa.Column('role', sa.String(length=20), nullable=True),
        sa.Column('action', sa.String(length=60), nullable=False, index=True),
        sa.Column('target_entity', sa.String(length=100), nullable=False),
        sa.Column('old_value', sa.Text(), nullable=True),
        sa.Column('new_value', sa.Text(), nullable=True),
        sa.Column('client_ip', sa.String(length=45), server_default='127.0.0.1', nullable=False),
        sa.Column('user_agent', sa.String(length=255), nullable=True),
        sa.Column('request_id', sa.String(length=36), nullable=True, index=True),
        sa.Column('timestamp', sa.DateTime(), nullable=False, index=True)
    )
    op.create_index('ix_audit_action_timestamp', 'audit_logs', ['action', 'timestamp'])

    # 6. Employee Sequences Table (Atomic Concurrency)
    op.create_table(
        'employee_sequences',
        sa.Column('prefix', sa.String(length=10), primary_key=True),
        sa.Column('last_sequence', sa.Integer(), nullable=False, server_default='100'),
        sa.Column('updated_at', sa.DateTime(), nullable=False)
    )


def downgrade() -> None:
    op.drop_table('employee_sequences')
    op.drop_table('audit_logs')
    op.drop_table('leave_requests')
    op.drop_table('payroll_records')
    op.drop_table('users')
    op.drop_table('employees')
