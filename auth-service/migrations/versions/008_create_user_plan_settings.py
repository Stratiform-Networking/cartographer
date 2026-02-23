"""Create user_plan_settings table for centralized plan-derived values.

Revision ID: 008_create_user_plan_settings
Revises: 007_create_password_reset_tokens
Create Date: 2026-02-23

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "008_create_user_plan_settings"
down_revision: Union[str, None] = "007_create_password_reset_tokens"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create user_plan_settings table."""
    op.create_table(
        "user_plan_settings",
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("plan_id", sa.String(length=50), nullable=False, server_default="free"),
        sa.Column("owned_networks_limit", sa.Integer(), nullable=False, server_default="1"),
        sa.Column(
            "assistant_daily_chat_messages_limit",
            sa.Integer(),
            nullable=False,
            server_default="5",
        ),
        sa.Column(
            "automatic_full_scan_min_interval_seconds",
            sa.Integer(),
            nullable=False,
            server_default="7200",
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("user_id"),
    )

    op.execute(
        sa.text(
            """
            INSERT INTO user_plan_settings (
                user_id,
                plan_id,
                owned_networks_limit,
                assistant_daily_chat_messages_limit,
                automatic_full_scan_min_interval_seconds
            )
            SELECT
                u.id,
                'free',
                1,
                5,
                7200
            FROM users u
            WHERE NOT EXISTS (
                SELECT 1 FROM user_plan_settings ups WHERE ups.user_id = u.id
            )
            """
        )
    )


def downgrade() -> None:
    """Drop user_plan_settings table."""
    op.drop_table("user_plan_settings")
