"""Create provider_links table for pluggable auth providers

Revision ID: 004_create_provider_links
Revises: 003_performance_indexes
Create Date: 2025-01-03 12:00:00.000000

"""

from typing import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "004_create_provider_links"
down_revision: str | None = "003_performance_indexes"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    from sqlalchemy import inspect

    # Get database connection to check existing tables
    conn = op.get_bind()
    inspector = inspect(conn)
    existing_tables = inspector.get_table_names()

    # Skip table creation if table already exists
    if "provider_links" in existing_tables:
        return

    # Create provider_links table
    op.create_table(
        "provider_links",
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("provider", sa.String(length=50), nullable=False),
        sa.Column("provider_user_id", sa.String(length=255), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint("provider", "provider_user_id", name="uq_provider_user"),
        comment="Links external auth providers to local users",
    )

    # Create index on user_id for faster lookups
    op.create_index("ix_provider_links_user_id", "provider_links", ["user_id"])

    # Create composite index for provider + provider_user_id lookups
    op.create_index(
        "ix_provider_links_provider_user",
        "provider_links",
        ["provider", "provider_user_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_provider_links_provider_user", table_name="provider_links")
    op.drop_index("ix_provider_links_user_id", table_name="provider_links")
    op.drop_table("provider_links")
