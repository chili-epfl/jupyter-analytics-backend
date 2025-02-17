"""Increasing user_id columns string size

Revision ID: 01d8648b5f3b
Revises: 041998d0e01b
Create Date: 2024-01-29 14:17:04.661313

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '01d8648b5f3b'
down_revision = '041998d0e01b'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('DashboardEvent', schema=None) as batch_op:
        batch_op.alter_column('dashboard_user_id',
               existing_type=sa.VARCHAR(length=50),
               type_=sa.String(length=100),
               existing_nullable=False)
        batch_op.alter_column('notebook_id',
               existing_type=sa.VARCHAR(length=50),
               type_=sa.String(length=60),
               existing_nullable=True)

    with op.batch_alter_table('UserWhiteList', schema=None) as batch_op:
        batch_op.alter_column('user_id',
               existing_type=sa.VARCHAR(length=60),
               type_=sa.String(length=100),
               existing_nullable=False)

    with op.batch_alter_table('WhiteListAssociation', schema=None) as batch_op:
        batch_op.alter_column('user_id',
               existing_type=sa.VARCHAR(length=60),
               type_=sa.String(length=100),
               existing_nullable=True)

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('WhiteListAssociation', schema=None) as batch_op:
        batch_op.alter_column('user_id',
               existing_type=sa.String(length=100),
               type_=sa.VARCHAR(length=60),
               existing_nullable=True)

    with op.batch_alter_table('UserWhiteList', schema=None) as batch_op:
        batch_op.alter_column('user_id',
               existing_type=sa.String(length=100),
               type_=sa.VARCHAR(length=60),
               existing_nullable=False)

    with op.batch_alter_table('DashboardEvent', schema=None) as batch_op:
        batch_op.alter_column('notebook_id',
               existing_type=sa.String(length=60),
               type_=sa.VARCHAR(length=50),
               existing_nullable=True)
        batch_op.alter_column('dashboard_user_id',
               existing_type=sa.String(length=100),
               type_=sa.VARCHAR(length=50),
               existing_nullable=False)

    # ### end Alembic commands ###
