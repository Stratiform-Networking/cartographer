"""Add performance indexes for notification service

Revision ID: 003_performance_indexes
Revises: 002_discord_link_context
Create Date: 2026-01-02

Performance optimization migration to support 200+ concurrent users.
Adds indexes for frequently queried columns in notification tables.

Impact: +10-15 concurrent users expected
Risk: Low (uses CONCURRENTLY to avoid table locks)
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "003_performance_indexes"
down_revision = "002_discord_link_context"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add performance indexes."""
    
    # User network preferences lookup (most frequent query)
    op.execute(
        """
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_user_network_prefs_user_network
        ON user_network_notification_prefs(user_id, network_id)
        """
    )
    
    # Global user preferences lookup
    op.execute(
        """
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_user_global_prefs_user
        ON user_global_notification_prefs(user_id)
        """
    )
    
    # Discord user link lookups (by user_id)
    op.execute(
        """
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_discord_links_user
        ON discord_user_links(user_id)
        """
    )
    
    # Discord user link lookups (by discord_user_id)
    op.execute(
        """
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_discord_links_discord_user
        ON discord_user_links(discord_user_id)
        """
    )


def downgrade() -> None:
    """Remove performance indexes."""
    
    op.execute("DROP INDEX CONCURRENTLY IF EXISTS idx_user_network_prefs_user_network")
    op.execute("DROP INDEX CONCURRENTLY IF EXISTS idx_user_global_prefs_user")
    op.execute("DROP INDEX CONCURRENTLY IF EXISTS idx_discord_links_user")
    op.execute("DROP INDEX CONCURRENTLY IF EXISTS idx_discord_links_discord_user")

