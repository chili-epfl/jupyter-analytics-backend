"""Update event_type for polymorphism

Revision ID: 19c2f19cd3ac
Revises: 25baa146fc70
Create Date: 2023-12-05 17:10:40.044622

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '19c2f19cd3ac'
down_revision = '25baa146fc70'
branch_labels = None
depends_on = None


def upgrade():
    # update event_type for CellClickEvent rows
    op.execute("UPDATE \"Event\" SET event_type='CellClickEvent' WHERE id IN (SELECT id FROM \"CellClickEvent\")")

    # update event_type for NotebookClickEvent rows
    op.execute("UPDATE \"Event\" SET event_type='NotebookClickEvent' WHERE id IN (SELECT id FROM \"NotebookClickEvent\")")


def downgrade():
    # update event_type for CellClickEvent and NotebookClickEvent rows back to 'ClickEvent'
    op.execute("UPDATE \"Event\" SET event_type='ClickEvent' WHERE id IN (SELECT id FROM \"CellClickEvent\")")
    op.execute("UPDATE \"Event\" SET event_type='ClickEvent' WHERE id IN (SELECT id FROM \"NotebookClickEvent\")")

