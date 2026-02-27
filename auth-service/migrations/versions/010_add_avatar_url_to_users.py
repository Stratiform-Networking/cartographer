"""Add avatar_url to users table

Revision ID: 010_add_avatar_url_to_users
Revises: 009_add_health_poll_interval_to_user_plan_settings
Create Date: 2026-02-27 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "010_add_avatar_url_to_users"
down_revision: Union[str, None] = "009_add_health_poll_interval_to_user_plan_settings"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    from sqlalchemy import inspect

    conn = op.get_bind()
    inspector = inspect(conn)
    columns = {column["name"] for column in inspector.get_columns("users")}
    if "avatar_url" not in columns:
        op.add_column("users", sa.Column("avatar_url", sa.String(length=500), nullable=True))


def downgrade() -> None:
    from sqlalchemy import inspect

    conn = op.get_bind()
    inspector = inspect(conn)
    columns = {column["name"] for column in inspector.get_columns("users")}
    if "avatar_url" in columns:
        op.drop_column("users", "avatar_url")

