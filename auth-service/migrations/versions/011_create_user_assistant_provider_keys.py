"""Create user_assistant_provider_keys table.

Revision ID: 011_create_user_assistant_provider_keys
Revises: 010_add_avatar_url_to_users
Create Date: 2026-02-27 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "011_create_user_assistant_keys"
down_revision: Union[str, None] = "010_add_avatar_url_to_users"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    from sqlalchemy import inspect

    conn = op.get_bind()
    inspector = inspect(conn)
    tables = set(inspector.get_table_names())
    if "user_assistant_provider_keys" not in tables:
        op.create_table(
            "user_assistant_provider_keys",
            sa.Column("user_id", postgresql.UUID(as_uuid=False), nullable=False),
            sa.Column("provider", sa.String(length=32), nullable=False),
            sa.Column("encrypted_api_key", sa.String(length=4096), nullable=False),
            sa.Column("model", sa.String(length=255), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("user_id", "provider"),
        )


def downgrade() -> None:
    from sqlalchemy import inspect

    conn = op.get_bind()
    inspector = inspect(conn)
    tables = set(inspector.get_table_names())
    if "user_assistant_provider_keys" in tables:
        op.drop_table("user_assistant_provider_keys")
