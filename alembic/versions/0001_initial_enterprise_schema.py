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
    # 1. Employees Table
    op.create_table(
        'employees',
        sa.Column('eid', sa.Integer(), primary_key=True, index=True),
        sa.Column('ename', sa.String(length=100), nullable=False, index=True),
        sa.Column('ecen', sa.String(length=50), nullable=False, index=True),
        sa.Column('epos', sa.String(length=50), nullable=False),
        sa.Column('esal', sa.Float(), nullable=False),
        sa.Column('edoj', sa.Date(), nullable=False),
        sa.Column('email', sa.String(length=120), nullable=True),
        sa.Column('status', sa.String(length=20), server_default='ACTIVE', nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True)
    )

    # 2. Users Table
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('employee_id', sa.Integer(), sa.ForeignKey('employees.eid', ondelete='CASCADE'), nullable=True, unique=True),
        sa.Column('email', sa.String(length=120), nullable=False, unique=True, index=True),
        sa.Column('hashed_password', sa.String(length=255), nullable=False),
        sa.Column('role', sa.String(length=20), server_default='EMPLOYEE', nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default='1', nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True)
    )

    # 3. Payroll Records Table
    op.create_table(
        'payroll_records',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('employee_id', sa.Integer(), sa.ForeignKey('employees.eid', ondelete='CASCADE'), nullable=False),
        sa.Column('month_year', sa.String(length=7), nullable=False, index=True),
        sa.Column('base_salary', sa.Float(), nullable=False),
        sa.Column('hra', sa.Float(), nullable=False),
        sa.Column('allowance', sa.Float(), nullable=False),
        sa.Column('gross_salary', sa.Float(), nullable=False),
        sa.Column('pf_deduction', sa.Float(), nullable=False),
        sa.Column('tax_deduction', sa.Float(), nullable=False),
        sa.Column('net_salary', sa.Float(), nullable=False),
        sa.Column('payment_status', sa.String(length=20), server_default='PAID', nullable=False),
        sa.Column('generated_at', sa.DateTime(), nullable=True)
    )

    # 4. Leave Requests Table
    op.create_table(
        'leave_requests',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('employee_id', sa.Integer(), sa.ForeignKey('employees.eid', ondelete='CASCADE'), nullable=False),
        sa.Column('leave_type', sa.String(length=20), nullable=False),
        sa.Column('start_date', sa.Date(), nullable=False),
        sa.Column('end_date', sa.Date(), nullable=False),
        sa.Column('days_count', sa.Integer(), nullable=False),
        sa.Column('reason', sa.Text(), nullable=False),
        sa.Column('status', sa.String(length=20), server_default='PENDING', nullable=False),
        sa.Column('applied_at', sa.DateTime(), nullable=True),
        sa.Column('reviewed_by', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('review_comment', sa.String(length=255), nullable=True)
    )

    # 5. Audit Logs Table
    op.create_table(
        'audit_logs',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('username', sa.String(length=50), nullable=False),
        sa.Column('action', sa.String(length=50), nullable=False, index=True),
        sa.Column('target_entity', sa.String(length=100), nullable=False),
        sa.Column('old_value', sa.Text(), nullable=True),
        sa.Column('new_value', sa.Text(), nullable=True),
        sa.Column('client_ip', sa.String(length=45), nullable=True),
        sa.Column('timestamp', sa.DateTime(), nullable=True, index=True)
    )


def downgrade() -> None:
    op.drop_table('audit_logs')
    op.drop_table('leave_requests')
    op.drop_table('payroll_records')
    op.drop_table('users')
    op.drop_table('employees')
