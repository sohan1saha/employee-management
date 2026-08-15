"""convert_float_to_numeric

Revision ID: 0002_convert_float_to_numeric
Revises: 0001_initial_schema
Create Date: 2026-08-16 01:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '0002_convert_float_to_numeric'
down_revision: Union[str, None] = '0001_initial_schema'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Safely cast and alter Float columns to Numeric(12, 2) for PostgreSQL / SQLite
    # 1. Employees Table
    with op.batch_alter_table('employees') as batch_op:
        batch_op.alter_column(
            'esal',
            existing_type=sa.Float(),
            type_=sa.Numeric(12, 2),
            existing_nullable=False,
            postgresql_using='esal::numeric(12,2)'
        )

    # 2. Payroll Records Table
    with op.batch_alter_table('payroll_records') as batch_op:
        for col_name in [
            'base_salary',
            'hra',
            'allowance',
            'gross_salary',
            'pf_deduction',
            'tax_deduction',
            'net_salary'
        ]:
            batch_op.alter_column(
                col_name,
                existing_type=sa.Float(),
                type_=sa.Numeric(12, 2),
                existing_nullable=False,
                postgresql_using=f'{col_name}::numeric(12,2)'
            )


def downgrade() -> None:
    with op.batch_alter_table('payroll_records') as batch_op:
        for col_name in [
            'base_salary',
            'hra',
            'allowance',
            'gross_salary',
            'pf_deduction',
            'tax_deduction',
            'net_salary'
        ]:
            batch_op.alter_column(
                col_name,
                existing_type=sa.Numeric(12, 2),
                type_=sa.Float(),
                existing_nullable=False
            )

    with op.batch_alter_table('employees') as batch_op:
        batch_op.alter_column(
            'esal',
            existing_type=sa.Numeric(12, 2),
            type_=sa.Float(),
            existing_nullable=False
        )
