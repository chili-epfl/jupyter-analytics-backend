"""Changing DashboardInteraction signal to string

Revision ID: 61a9658a0a4d
Revises: 6244d32eb37c
Create Date: 2024-05-01 15:51:41.533506

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '61a9658a0a4d'
down_revision = '6244d32eb37c'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('DashboardEvent', schema=None) as batch_op:
        batch_op.alter_column('signal_origin',
               existing_type=postgresql.ENUM('RIGHT_DASHBOARD_SHOW_HIDE', 'TOC_DASHBOARD_SHOW_HIDE', 'NOTEBOOK_CELL_BUTTON', 'NOTEBOOK_TOOLBAR_BUTTON', 'TOC_OPEN_CELL_DASHBOARD', 'TOC_HEADING_CLICKED', 'TOC_COLLAPSE_HEADERS', 'BREADCRUMB_TO_NOTEBOOK', 'BREADCRUMB_TO_CELL', 'DASHBOARD_REFRESH_BUTTON', 'DASHBOARD_FILTER_TIME', 'CELL_DASHBOARD_FILTER_SORT', 'CELL_DASHBOARD_FILTER_CODE_INPUT', 'CELL_DASHBOARD_FILTER_CODE_OUTPUT', 'CELL_DASHBOARD_FILTER_EXECUTION', 'TOC_TOOLBAR_CODE', 'TOC_TOOLBAR_MARKDOWN', 'TOC_TOOLBAR_NUMBERED', 'TOC_TOOLBAR_SHOW_HIDE', 'TOC_TOOLBAR_REFRESH', name='dashboardclickorigin'),
               type_=sa.String(length=90),
               existing_nullable=False)

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('DashboardEvent', schema=None) as batch_op:
        batch_op.alter_column('signal_origin',
               existing_type=sa.String(length=90),
               type_=postgresql.ENUM('RIGHT_DASHBOARD_SHOW_HIDE', 'TOC_DASHBOARD_SHOW_HIDE', 'NOTEBOOK_CELL_BUTTON', 'NOTEBOOK_TOOLBAR_BUTTON', 'TOC_OPEN_CELL_DASHBOARD', 'TOC_HEADING_CLICKED', 'TOC_COLLAPSE_HEADERS', 'BREADCRUMB_TO_NOTEBOOK', 'BREADCRUMB_TO_CELL', 'DASHBOARD_REFRESH_BUTTON', 'DASHBOARD_FILTER_TIME', 'CELL_DASHBOARD_FILTER_SORT', 'CELL_DASHBOARD_FILTER_CODE_INPUT', 'CELL_DASHBOARD_FILTER_CODE_OUTPUT', 'CELL_DASHBOARD_FILTER_EXECUTION', 'TOC_TOOLBAR_CODE', 'TOC_TOOLBAR_MARKDOWN', 'TOC_TOOLBAR_NUMBERED', 'TOC_TOOLBAR_SHOW_HIDE', 'TOC_TOOLBAR_REFRESH', name='dashboardclickorigin'),
               existing_nullable=False)

    # ### end Alembic commands ###
