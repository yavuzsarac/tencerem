from datetime import datetime, date, timezone
from decimal import Decimal
from uuid import uuid4
from sqlalchemy import String, DateTime, Date, ForeignKey, UniqueConstraint, CheckConstraint, JSON, Numeric
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def now_utc():
    return datetime.now(timezone.utc)

class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    email: Mapped[str] = mapped_column(String(254), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, onupdate=now_utc)

class UserPreferences(Base):
    __tablename__ = "user_preferences"
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    dietary_pattern: Mapped[str] = mapped_column(String(30), default="standard")
    allergies: Mapped[list[str]] = mapped_column(JSON, default=list)
    liked_ingredients: Mapped[list[str]] = mapped_column(JSON, default=list)
    disliked_ingredients: Mapped[list[str]] = mapped_column(JSON, default=list)
    goals: Mapped[list[str]] = mapped_column(JSON, default=list)
    default_servings: Mapped[int] = mapped_column(default=2)
    default_max_minutes: Mapped[int | None] = mapped_column(nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, onupdate=now_utc)
    __table_args__ = (CheckConstraint("default_servings BETWEEN 1 AND 12", name="ck_preferences_servings"),)

class AuthSession(Base):
    __tablename__ = "auth_sessions"
    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)

class PantryEntry(Base):
    __tablename__ = "pantry_entries"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    ingredient_id: Mapped[str] = mapped_column(String(80))
    quantity: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    unit: Mapped[str | None] = mapped_column(String(20), nullable=True)
    expiration_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, onupdate=now_utc)
    __table_args__ = (UniqueConstraint("user_id", "ingredient_id", name="uq_pantry_user_ingredient"),
        CheckConstraint("(quantity IS NULL AND unit IS NULL) OR (quantity IS NOT NULL AND quantity >= 0 AND unit IS NOT NULL)", name="ck_pantry_quantity_pair"),)
