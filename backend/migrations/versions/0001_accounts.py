"""Accounts, opaque sessions, separate saved preferences and pantry.

Revision ID: 0001_accounts
Revises: None
"""
from alembic import op
import sqlalchemy as sa
revision="0001_accounts"
down_revision=None
branch_labels=None
depends_on=None

def upgrade():
    op.create_table("users",sa.Column("id",sa.String(36),primary_key=True),sa.Column("email",sa.String(254),nullable=False),sa.Column("password_hash",sa.String(255),nullable=False),sa.Column("created_at",sa.DateTime(timezone=True),nullable=False),sa.Column("updated_at",sa.DateTime(timezone=True),nullable=False),sa.UniqueConstraint("email",name="uq_users_email"))
    op.create_table("user_preferences",sa.Column("user_id",sa.String(36),sa.ForeignKey("users.id",ondelete="CASCADE"),primary_key=True),sa.Column("dietary_pattern",sa.String(30),nullable=False),sa.Column("allergies",sa.JSON(),nullable=False),sa.Column("liked_ingredients",sa.JSON(),nullable=False),sa.Column("disliked_ingredients",sa.JSON(),nullable=False),sa.Column("goals",sa.JSON(),nullable=False),sa.Column("default_servings",sa.Integer(),nullable=False),sa.Column("default_max_minutes",sa.Integer(),nullable=True),sa.Column("updated_at",sa.DateTime(timezone=True),nullable=False),sa.CheckConstraint("default_servings BETWEEN 1 AND 12",name="ck_preferences_servings"))
    op.create_table("auth_sessions",sa.Column("token_hash",sa.String(64),primary_key=True),sa.Column("user_id",sa.String(36),sa.ForeignKey("users.id",ondelete="CASCADE"),nullable=False),sa.Column("expires_at",sa.DateTime(timezone=True),nullable=False),sa.Column("created_at",sa.DateTime(timezone=True),nullable=False))
    op.create_index("ix_auth_sessions_user_id","auth_sessions",["user_id"])
    op.create_index("ix_auth_sessions_expires_at","auth_sessions",["expires_at"])
    op.create_table("pantry_entries",sa.Column("id",sa.String(36),primary_key=True),sa.Column("user_id",sa.String(36),sa.ForeignKey("users.id",ondelete="CASCADE"),nullable=False),sa.Column("ingredient_id",sa.String(80),nullable=False),sa.Column("quantity",sa.Numeric(18,6),nullable=True),sa.Column("unit",sa.String(20),nullable=True),sa.Column("expiration_date",sa.Date(),nullable=True),sa.Column("created_at",sa.DateTime(timezone=True),nullable=False),sa.Column("updated_at",sa.DateTime(timezone=True),nullable=False),sa.UniqueConstraint("user_id","ingredient_id",name="uq_pantry_user_ingredient"),sa.CheckConstraint("(quantity IS NULL AND unit IS NULL) OR (quantity IS NOT NULL AND quantity >= 0 AND unit IS NOT NULL)",name="ck_pantry_quantity_pair"))
    op.create_index("ix_pantry_entries_user_id","pantry_entries",["user_id"])

def downgrade():
    op.drop_table("pantry_entries")
    op.drop_table("auth_sessions")
    op.drop_table("user_preferences")
    op.drop_table("users")
