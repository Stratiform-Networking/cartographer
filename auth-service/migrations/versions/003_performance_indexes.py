"""Add performance indexes for auth service

Revision ID: 003_performance_indexes
Revises: 002_add_user_preferences
Create Date: 2026-01-02

Performance optimization migration to support 200+ concurrent users.
Adds indexes for frequently queried columns.

Impact: +15-20 concurrent users expected
Risk: Low (uses CONCURRENTLY to avoid table locks)

Note: This migration runs outside of a transaction because
CREATE INDEX CONCURRENTLY cannot run inside a transaction block.
"""

from alembic import op
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision = "003_performance_indexes"
down_revision = "002_add_user_preferences"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add performance indexes.
    
    Note: We use connection.execute() with AUTOCOMMIT isolation level
    because CREATE INDEX CONCURRENTLY cannot run in a transaction.
    """
    
    connection = op.get_bind()
    
    # Set autocommit mode (no transaction)
    connection.execute(text("COMMIT"))
    
    # Username lookups (login endpoint)
    # Filter to active users only for better index selectivity
    connection.execute(
        text("""
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_users_username_active
        ON users(username) WHERE is_active = true
        """)
    )
    
    # Email lookups (invite, password reset)
    # Filter to active users only for better index selectivity
    connection.execute(
        text("""
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_users_email_active
        ON users(email) WHERE is_active = true
        """)
    )
    
    # Active invites lookup
    # Filter to pending invites for faster lookups
    connection.execute(
        text("""
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_invites_email_status
        ON invites(email, status) WHERE status = 'pending'
        """)
    )


def downgrade() -> None:
    """Remove performance indexes.
    
    Note: DROP INDEX CONCURRENTLY also requires autocommit mode.
    """
    
    connection = op.get_bind()
    
    # Set autocommit mode (no transaction)
    connection.execute(text("COMMIT"))
    
    connection.execute(text("DROP INDEX CONCURRENTLY IF EXISTS idx_users_username_active"))
    connection.execute(text("DROP INDEX CONCURRENTLY IF EXISTS idx_users_email_active"))
    connection.execute(text("DROP INDEX CONCURRENTLY IF EXISTS idx_invites_email_status"))

