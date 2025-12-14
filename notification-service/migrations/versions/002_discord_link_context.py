"""Add context fields to discord_user_links for per-network and global Discord linking

Revision ID: 002_discord_link_context
Revises: 001_create_notification_tables
Create Date: 2024-12-13 12:00:00.000000

This migration allows users to link different Discord accounts per-network and globally.
Each network can have its own Discord link, separate from the global Discord link.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '002_discord_link_context'
down_revision: Union[str, None] = '001_create_notification_tables'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    from sqlalchemy import inspect
    
    # Get database connection to check existing columns
    conn = op.get_bind()
    inspector = inspect(conn)
    
    # Check if context_type column already exists (migration already applied)
    columns = [col['name'] for col in inspector.get_columns('discord_user_links')]
    if 'context_type' in columns:
        # Migration already applied, skip
        return
    
    # Add context columns to discord_user_links
    op.add_column('discord_user_links', sa.Column('context_type', sa.String(length=20), nullable=False, server_default='global'))
    op.add_column('discord_user_links', sa.Column('context_id', sa.Integer(), nullable=True))
    
    # Remove old unique constraints (user_id and discord_id were unique)
    # Use try/except since constraints might not exist
    try:
        op.drop_constraint('discord_user_links_user_id_key', 'discord_user_links', type_='unique')
    except Exception:
        pass
    try:
        op.drop_constraint('discord_user_links_discord_id_key', 'discord_user_links', type_='unique')
    except Exception:
        pass
    
    # Drop old unique indexes (may not exist)
    try:
        op.drop_index('ix_discord_user_links_user_id', table_name='discord_user_links')
    except Exception:
        pass
    try:
        op.drop_index('ix_discord_user_links_discord_id', table_name='discord_user_links')
    except Exception:
        pass
    
    # Create new indexes (non-unique, since same discord_id can be used in multiple contexts)
    op.execute("CREATE INDEX IF NOT EXISTS ix_discord_user_links_user_id ON discord_user_links (user_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_discord_user_links_discord_id ON discord_user_links (discord_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_discord_user_links_context ON discord_user_links (context_type, context_id)")
    
    # Create unique constraint: one Discord link per user per context
    # user_id + context_type + context_id must be unique (handles null context_id for global)
    op.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS uq_discord_user_links_user_context 
        ON discord_user_links (user_id, context_type, COALESCE(context_id, -1))
    """)
    
    # Update existing records: mark them as global context
    op.execute("""
        UPDATE discord_user_links 
        SET context_type = 'global', context_id = NULL 
        WHERE context_type = 'global' OR context_type IS NULL
    """)


def downgrade() -> None:
    # Drop new indexes and constraints
    op.execute("DROP INDEX IF EXISTS uq_discord_user_links_user_context")
    op.drop_index('ix_discord_user_links_context', table_name='discord_user_links')
    op.drop_index('ix_discord_user_links_discord_id', table_name='discord_user_links')
    op.drop_index('ix_discord_user_links_user_id', table_name='discord_user_links')
    
    # Delete non-global links (since we're reverting to single-link model)
    op.execute("DELETE FROM discord_user_links WHERE context_type != 'global'")
    
    # Drop context columns
    op.drop_column('discord_user_links', 'context_id')
    op.drop_column('discord_user_links', 'context_type')
    
    # Recreate original unique constraints
    op.create_index('ix_discord_user_links_user_id', 'discord_user_links', ['user_id'], unique=True)
    op.create_index('ix_discord_user_links_discord_id', 'discord_user_links', ['discord_id'], unique=True)
    op.create_unique_constraint('discord_user_links_user_id_key', 'discord_user_links', ['user_id'])
    op.create_unique_constraint('discord_user_links_discord_id_key', 'discord_user_links', ['discord_id'])
