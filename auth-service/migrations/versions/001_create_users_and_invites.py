"""Create users and invites tables

Revision ID: 001_create_users_and_invites
Revises: 
Create Date: 2024-12-13 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001_create_users_and_invites'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    from sqlalchemy import inspect
    
    # Get database connection to check existing tables
    conn = op.get_bind()
    inspector = inspect(conn)
    existing_tables = inspector.get_table_names()
    
    # Create user_role enum type
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE user_role AS ENUM ('owner', 'admin', 'member');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)
    
    # Create invite_status enum type
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE invite_status AS ENUM ('pending', 'accepted', 'expired', 'revoked');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)
    
    # Skip table creation if tables already exist
    if 'users' in existing_tables:
        return
    
    # Create users table (compatible with cartographer-cloud format)
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('username', sa.String(length=50), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('hashed_password', sa.String(length=255), nullable=False),
        sa.Column('first_name', sa.String(length=100), nullable=False),
        sa.Column('last_name', sa.String(length=100), nullable=False),
        sa.Column('role', postgresql.ENUM('owner', 'admin', 'member', name='user_role', create_type=False), 
                  nullable=False, server_default='member'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('is_verified', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('last_login_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        comment='User accounts - compatible with cartographer-cloud format'
    )
    op.create_index('ix_users_username', 'users', ['username'], unique=True)
    op.create_index('ix_users_email', 'users', ['email'], unique=True)
    
    # Create invites table
    op.create_table(
        'invites',
        sa.Column('id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('role', postgresql.ENUM('owner', 'admin', 'member', name='user_role', create_type=False),
                  nullable=False, server_default='member'),
        sa.Column('status', postgresql.ENUM('pending', 'accepted', 'expired', 'revoked', name='invite_status', create_type=False),
                  nullable=False, server_default='pending'),
        sa.Column('token', sa.String(length=255), nullable=False),
        sa.Column('invited_by_id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('invited_by_username', sa.String(length=50), nullable=False),
        sa.Column('invited_by_name', sa.String(length=200), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('accepted_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        comment='User invitations for self-hosted instance'
    )
    op.create_index('ix_invites_email', 'invites', ['email'], unique=False)
    op.create_index('ix_invites_token', 'invites', ['token'], unique=True)


def downgrade() -> None:
    op.drop_index('ix_invites_token', table_name='invites')
    op.drop_index('ix_invites_email', table_name='invites')
    op.drop_table('invites')
    
    op.drop_index('ix_users_email', table_name='users')
    op.drop_index('ix_users_username', table_name='users')
    op.drop_table('users')
    
    # Drop enum types
    op.execute('DROP TYPE IF EXISTS invite_status')
    op.execute('DROP TYPE IF EXISTS user_role')
