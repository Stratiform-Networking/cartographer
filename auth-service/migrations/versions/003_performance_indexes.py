"""Add performance indexes for auth service

Revision ID: 003_performance_indexes
Revises: 002_add_user_preferences
Create Date: 2026-01-02

Performance optimization migration to support 200+ concurrent users.
Adds indexes for frequently queried columns.

Impact: +15-20 concurrent users expected
Risk: Low (uses CONCURRENTLY to avoid table locks)
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "003_performance_indexes"
down_revision = "002_add_user_preferences"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add performance indexes."""
    
    # Username lookups (login endpoint)
    # Use CONCURRENTLY to avoid locking the users table
    op.execute(
        """
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_users_username_active
        ON users(username) WHERE deleted_at IS NULL
        """
    )
    
    # Email lookups (invite, password reset)
    op.execute(
        """
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_users_email_active
        ON users(email) WHERE deleted_at IS NULL
        """
    )
    
    # Active invites lookup
    op.execute(
        """
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_invites_email_status
        ON invites(email, status)
        """
    )


def downgrade() -> None:
    """Remove performance indexes."""
    
    op.execute("DROP INDEX CONCURRENTLY IF EXISTS idx_users_username_active")
    op.execute("DROP INDEX CONCURRENTLY IF EXISTS idx_users_email_active")
    op.execute("DROP INDEX CONCURRENTLY IF EXISTS idx_invites_email_status")

