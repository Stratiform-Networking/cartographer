"""Create notification tables

Revision ID: 001_create_notification_tables
Revises: 
Create Date: 2024-12-12 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001_create_notification_tables'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    from sqlalchemy import inspect
    from alembic import op
    
    # Get database connection to check existing tables
    conn = op.get_bind()
    inspector = inspect(conn)
    existing_tables = inspector.get_table_names()
    
    # Create notification_priority enum type
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE notification_priority AS ENUM ('low', 'medium', 'high', 'critical');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)
    
    # Skip table creation if tables already exist
    if 'user_network_notification_prefs' in existing_tables:
        return
    
    # Create user_network_notification_prefs table
    op.create_table(
        'user_network_notification_prefs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('network_id', sa.Integer(), nullable=False),
        sa.Column('email_enabled', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('discord_enabled', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('discord_user_id', sa.String(length=255), nullable=True),
        sa.Column('enabled_types', postgresql.JSON(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('type_priorities', postgresql.JSON(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('minimum_priority', postgresql.ENUM('low', 'medium', 'high', 'critical', name='notification_priority', create_type=False), nullable=False, server_default='medium'),
        sa.Column('quiet_hours_enabled', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('quiet_hours_start', sa.String(length=5), nullable=True),
        sa.Column('quiet_hours_end', sa.String(length=5), nullable=True),
        sa.Column('quiet_hours_timezone', sa.String(length=100), nullable=True),
        sa.Column('quiet_hours_bypass_priority', postgresql.ENUM('low', 'medium', 'high', 'critical', name='notification_priority', create_type=False), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        comment='Per-user notification preferences for networks'
    )
    op.create_index(op.f('ix_user_network_notification_prefs_user_id'), 'user_network_notification_prefs', ['user_id'], unique=False)
    op.create_index(op.f('ix_user_network_notification_prefs_network_id'), 'user_network_notification_prefs', ['network_id'], unique=False)
    op.create_unique_constraint('uq_user_network_notification_prefs_user_network', 'user_network_notification_prefs', ['user_id', 'network_id'])
    
    # Create user_global_notification_prefs table
    op.create_table(
        'user_global_notification_prefs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('email_enabled', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('discord_enabled', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('discord_user_id', sa.String(length=255), nullable=True),
        sa.Column('cartographer_up_enabled', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('cartographer_down_enabled', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('minimum_priority', postgresql.ENUM('low', 'medium', 'high', 'critical', name='notification_priority', create_type=False), nullable=False, server_default='medium'),
        sa.Column('quiet_hours_enabled', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('quiet_hours_start', sa.String(length=5), nullable=True),
        sa.Column('quiet_hours_end', sa.String(length=5), nullable=True),
        sa.Column('quiet_hours_timezone', sa.String(length=100), nullable=True),
        sa.Column('quiet_hours_bypass_priority', postgresql.ENUM('low', 'medium', 'high', 'critical', name='notification_priority', create_type=False), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id'),
        comment='Per-user global notification preferences'
    )
    op.create_index(op.f('ix_user_global_notification_prefs_user_id'), 'user_global_notification_prefs', ['user_id'], unique=True)
    
    # Create discord_user_links table
    op.create_table(
        'discord_user_links',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('discord_id', sa.String(length=255), nullable=False),
        sa.Column('discord_username', sa.String(length=255), nullable=False),
        sa.Column('discord_avatar', sa.String(length=500), nullable=True),
        sa.Column('access_token', sa.Text(), nullable=False),
        sa.Column('refresh_token', sa.Text(), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id'),
        sa.UniqueConstraint('discord_id'),
        comment='Discord OAuth links for users'
    )
    op.create_index(op.f('ix_discord_user_links_user_id'), 'discord_user_links', ['user_id'], unique=True)
    op.create_index(op.f('ix_discord_user_links_discord_id'), 'discord_user_links', ['discord_id'], unique=True)


def downgrade() -> None:
    op.drop_index(op.f('ix_discord_user_links_discord_id'), table_name='discord_user_links')
    op.drop_index(op.f('ix_discord_user_links_user_id'), table_name='discord_user_links')
    op.drop_table('discord_user_links')
    op.drop_index(op.f('ix_user_global_notification_prefs_user_id'), table_name='user_global_notification_prefs')
    op.drop_table('user_global_notification_prefs')
    op.drop_constraint('uq_user_network_notification_prefs_user_network', 'user_network_notification_prefs', type_='unique')
    op.drop_index(op.f('ix_user_network_notification_prefs_network_id'), table_name='user_network_notification_prefs')
    op.drop_index(op.f('ix_user_network_notification_prefs_user_id'), table_name='user_network_notification_prefs')
    op.drop_table('user_network_notification_prefs')
    
    # Drop enum type
    op.execute('DROP TYPE IF EXISTS notification_priority')
