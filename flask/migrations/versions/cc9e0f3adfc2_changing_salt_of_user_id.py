"""Changing salt of user_id

Revision ID: cc9e0f3adfc2
Revises: 61a9658a0a4d
Create Date: 2024-05-07 15:24:33.544800

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import table, column
from sqlalchemy.dialects.postgresql import ENUM

# revision identifiers, used by Alembic.
revision = 'cc9e0f3adfc2'
down_revision = '61a9658a0a4d'
branch_labels = None
depends_on = None

from hashlib import sha256
from app.utils.utils import hash_user_id_with_salt
from app.models.auth import UserIdType

OLD_SALT = '5ea06c48dbb6a90cdee78f88b8a08e673efda3d28c8019e62e326ce817ee8900'
def hash_user_id_OLD_SALT(prehashed_id):
    return sha256(prehashed_id.encode('utf-8') + OLD_SALT.encode('utf-8')).hexdigest()

def upgrade():
    print("Starting upgrade()")
    start_index, end_index = 750000, 1000000
    scipers = ['ch-epfl-'+str(num).zfill(6) for num in range(start_index, end_index)]
    print("Scipers list created")
    mappings = {}
    for i, s in enumerate(scipers):
        if (i%50000 == 0): print('SCIPER number ',s)
        old_hashed_id = hash_user_id_OLD_SALT(s)
        new_hashed_id = hash_user_id_with_salt(s)
        mappings[old_hashed_id] = new_hashed_id
    print("Mappings generated with size : ",len(mappings.keys()))
    # Bind to the current connection
    bind = op.get_bind()
    print("After op.get_bind()")

    chunk_size = 200

    def process_chunk(rows, table, column):
        for row in rows:
            current_user_id = row[1]
            new_user_id = mappings.get(current_user_id, current_user_id)
            if current_user_id != new_user_id:
                bind.execute(
                    table.update().
                    where(table.c.id == row[0]).
                    values({column: new_user_id})
                )
        rows.close()

    def process_table(table_name, user_id_column):
        print('Start process_table...')
        table_ref = table(table_name, column('id', sa.Integer), column(user_id_column, sa.String))
        print('After table_ref')
        total_rows = bind.execute(sa.select(sa.func.count()).select_from(table_ref)).scalar()
        print(f"Processing table {table_name}, total rows: {total_rows}...")
        for offset in range(0, total_rows, chunk_size):
            result = bind.execute(sa.select(table_ref.c.id, table_ref.c[user_id_column]).offset(offset).limit(chunk_size))
            process_chunk(result, table_ref, user_id_column)
            del result  # Explicitly delete the result set reference
        print(f"...Processing table {table_name} done")

    #######################
    ##### EVENT TABLE #####
    #######################
    process_table('Event', 'user_id')

    ################################
    ##### DASHBOARDEVENT TABLE #####
    ################################
    process_table('DashboardEvent', 'dashboard_user_id')

    ############################
    ##### USERGROUPS TABLE #####
    ############################
    users = table('Users', column('user_id', sa.String))
    user_group_association = table('UserGroupAssociation', column('group_pk', sa.String), column('user_id', sa.String))
    total_user_group_associations = bind.execute(sa.select(sa.func.count()).select_from(user_group_association)).scalar()
    print(f"Processing UserGroupAssociation table, total rows: {total_user_group_associations}...")
    for offset in range(0, total_user_group_associations, chunk_size):
        result_group_association = bind.execute(sa.select(user_group_association.c.group_pk, user_group_association.c.user_id).offset(offset).limit(chunk_size))
        for row in result_group_association:
            current_user_id = row[1]
            new_user_id = mappings.get(current_user_id, current_user_id)
            user_exists = bind.execute(sa.select(users.c.user_id).where(users.c.user_id == new_user_id)).fetchone()
            if not user_exists:
                bind.execute(users.insert().values(user_id=new_user_id))
            bind.execute(
                user_group_association.update().
                where((user_group_association.c.group_pk == row[0]) & (user_group_association.c.user_id == current_user_id)).
                values(user_id=new_user_id)
            )
        result_group_association.close()
        del result_group_association
    print(f"Processing UserGroupAssociation table done...")

    ###########################
    ##### WHITELIST TABLE #####
    ###########################

    user_white_list = table('UserWhiteList', column('user_id', sa.String), column('user_id_type', ENUM(UserIdType, name='user_id_type', create_type=False)))
    white_list_association = table('WhiteListAssociation', column('user_id', sa.String), column('notebook_id',sa.String))
    total_whitelist_associations = bind.execute(sa.select(sa.func.count()).select_from(white_list_association)).scalar()
    user_ids_to_remove = set()
    print(f"Processing WhiteListAssociation table, total rows: {total_whitelist_associations}...")
    for offset in range(0, total_whitelist_associations, chunk_size):
        result_whitelistassociation = bind.execute(sa.select(white_list_association.c.user_id, white_list_association.c.notebook_id).offset(offset).limit(chunk_size))
        for row in result_whitelistassociation:
            current_user_id = row[0]
            new_user_id = mappings.get(current_user_id, current_user_id)
            if current_user_id != new_user_id:
                user_exists = bind.execute(sa.select(user_white_list.c.user_id).where(user_white_list.c.user_id == new_user_id)).fetchone()
                if not user_exists:
                    bind.execute(user_white_list.insert().values(user_id=new_user_id, user_id_type=UserIdType.SCIPER))
                    user_ids_to_remove.add(current_user_id)
                bind.execute(
                    white_list_association.update().
                    where((white_list_association.c.user_id == current_user_id) & (white_list_association.c.notebook_id == row[1])).
                    values(user_id=new_user_id)
                )
        result_whitelistassociation.close()
        del result_whitelistassociation
    print("\nBefore user_ids_to_remove deletion\n")
    for user_id in user_ids_to_remove:
        bind.execute(user_white_list.delete().where(user_white_list.c.user_id == user_id))
    print(f"Processing WhiteListAssociation table done...")

def downgrade():
    pass