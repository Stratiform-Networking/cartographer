"""Add health poll interval to user_plan_settings.

Revision ID: 009_add_health_poll_to_plan_sett
Revises: 008_create_user_plan_settings
Create Date: 2026-02-24
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = "009_add_health_poll_to_plan_sett"
down_revision: Union[str, None] = "008_create_user_plan_settings"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add health polling interval plan setting with free-tier default (60s)."""
    op.add_column(
        "user_plan_settings",
        sa.Column(
            "health_poll_interval_seconds",
            sa.Integer(),
            nullable=False,
            server_default="60",
        ),
    )


def downgrade() -> None:
    """Remove health polling interval plan setting."""
    op.drop_column("user_plan_settings", "health_poll_interval_seconds")
