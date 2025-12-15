"""Migrate network_id from integer to UUID

Revision ID: 002_migrate_network_id_to_uuid
Revises: 001_create_notification_tables
Create Date: 2024-12-15 12:00:00.000000

This migration converts network_id columns from INTEGER to UUID
to match the backend's new UUID-based network IDs.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '002_migrate_network_id_to_uuid'
down_revision: Union[str, None] = '001_create_notification_tables'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Migrate network_id columns from INTEGER to UUID.
    
    For the notification service, we don't have foreign key constraints to the networks table
    (which is in the main backend database), so we can simply change the column type.
    
    Existing integer values will be converted to UUIDs using a deterministic mapping.
    """
    from sqlalchemy import inspect
    conn = op.get_bind()
    inspector = inspect(conn)
    
    # Check if tables exist and what type the columns are
    existing_tables = inspector.get_table_names()
    
    # user_network_notification_prefs table
    if 'user_network_notification_prefs' in existing_tables:
        columns = {col['name']: col for col in inspector.get_columns('user_network_notification_prefs')}
        if 'network_id' in columns:
            col_type = str(columns['network_id']['type'])
            if 'UUID' not in col_type.upper():
                # Column exists and is not UUID, need to migrate
                # Add new UUID column
                op.add_column('user_network_notification_prefs', 
                    sa.Column('new_network_id', postgresql.UUID(as_uuid=False), nullable=True))
                
                # For existing data, we need to generate UUIDs
                # Since these reference the backend's networks table which is also migrating,
                # the backend migration should provide a mapping. For now, we'll use a 
                # deterministic UUID generation based on the old integer ID
                # This ensures consistency if the backend provides the same mapping
                op.execute("""
                    UPDATE user_network_notification_prefs 
                    SET new_network_id = uuid_generate_v5(
                        'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11'::uuid, 
                        network_id::text
                    )
                    WHERE network_id IS NOT NULL
                """)
                
                # Drop old column and rename new one
                op.drop_index('ix_user_network_notification_prefs_network_id', 
                             table_name='user_network_notification_prefs', if_exists=True)
                op.drop_constraint('uq_user_network_notification_prefs_user_network', 
                                  'user_network_notification_prefs', type_='unique')
                op.drop_column('user_network_notification_prefs', 'network_id')
                op.alter_column('user_network_notification_prefs', 'new_network_id', 
                               new_column_name='network_id', nullable=False)
                
                # Recreate indexes and constraints
                op.create_index('ix_user_network_notification_prefs_network_id', 
                               'user_network_notification_prefs', ['network_id'], unique=False)
                op.create_unique_constraint('uq_user_network_notification_prefs_user_network',
                                           'user_network_notification_prefs', ['user_id', 'network_id'])
    
    # discord_user_links table - context_id column
    if 'discord_user_links' in existing_tables:
        columns = {col['name']: col for col in inspector.get_columns('discord_user_links')}
        if 'context_id' in columns:
            col_type = str(columns['context_id']['type'])
            if 'UUID' not in col_type.upper():
                # Column exists and is not UUID, need to migrate
                op.add_column('discord_user_links',
                    sa.Column('new_context_id', postgresql.UUID(as_uuid=False), nullable=True))
                
                # Convert existing integer context_ids to UUIDs
                op.execute("""
                    UPDATE discord_user_links 
                    SET new_context_id = uuid_generate_v5(
                        'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11'::uuid, 
                        context_id::text
                    )
                    WHERE context_id IS NOT NULL
                """)
                
                # Drop old column and rename
                op.drop_column('discord_user_links', 'context_id')
                op.alter_column('discord_user_links', 'new_context_id',
                               new_column_name='context_id', nullable=True)


def downgrade() -> None:
    """
    Revert network_id columns from UUID back to INTEGER.
    
    WARNING: This will lose the UUID values and generate new sequential integers.
    """
    from sqlalchemy import inspect
    conn = op.get_bind()
    inspector = inspect(conn)
    existing_tables = inspector.get_table_names()
    
    # user_network_notification_prefs table
    if 'user_network_notification_prefs' in existing_tables:
        columns = {col['name']: col for col in inspector.get_columns('user_network_notification_prefs')}
        if 'network_id' in columns:
            col_type = str(columns['network_id']['type'])
            if 'UUID' in col_type.upper():
                # Add temporary integer column
                op.add_column('user_network_notification_prefs',
                    sa.Column('old_network_id', sa.Integer(), nullable=True))
                
                # We can't reliably convert UUID back to integer, so we'd need the original mapping
                # For downgrade, we'll just use a sequence
                op.execute("""
                    UPDATE user_network_notification_prefs 
                    SET old_network_id = id  -- Use row ID as fallback
                """)
                
                op.drop_index('ix_user_network_notification_prefs_network_id',
                             table_name='user_network_notification_prefs', if_exists=True)
                op.drop_constraint('uq_user_network_notification_prefs_user_network',
                                  'user_network_notification_prefs', type_='unique')
                op.drop_column('user_network_notification_prefs', 'network_id')
                op.alter_column('user_network_notification_prefs', 'old_network_id',
                               new_column_name='network_id', nullable=False)
                op.create_index('ix_user_network_notification_prefs_network_id',
                               'user_network_notification_prefs', ['network_id'], unique=False)
                op.create_unique_constraint('uq_user_network_notification_prefs_user_network',
                                           'user_network_notification_prefs', ['user_id', 'network_id'])
    
    # discord_user_links table
    if 'discord_user_links' in existing_tables:
        columns = {col['name']: col for col in inspector.get_columns('discord_user_links')}
        if 'context_id' in columns:
            col_type = str(columns['context_id']['type'])
            if 'UUID' in col_type.upper():
                op.add_column('discord_user_links',
                    sa.Column('old_context_id', sa.Integer(), nullable=True))
                op.drop_column('discord_user_links', 'context_id')
                op.alter_column('discord_user_links', 'old_context_id',
                               new_column_name='context_id', nullable=True)

