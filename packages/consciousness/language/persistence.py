from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import DateTime, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from packages.infra.db.session import Base


class InnerThoughtRecord(Base):
    __tablename__ = "inner_thoughts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    self_model_id: Mapped[str] = mapped_column(ForeignKey("self_models.id"), index=True)
    thought_type: Mapped[str] = mapped_column(String(32), default="background_cycle")
    focus: Mapped[str] = mapped_column(Text)
    content: Mapped[str] = mapped_column(Text)
    salience_score: Mapped[float] = mapped_column(Float, default=0.0)
    source: Mapped[str] = mapped_column(String(32), default="background")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


class LanguageMessageRecord(Base):
    __tablename__ = "language_messages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    self_model_id: Mapped[str] = mapped_column(ForeignKey("self_models.id"), index=True)
    role: Mapped[str] = mapped_column(String(16), index=True)
    content: Mapped[str] = mapped_column(Text)
    channel: Mapped[str] = mapped_column(String(32), default="dialogue")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


class LanguageSummaryRecord(Base):
    __tablename__ = "language_summaries"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    self_model_id: Mapped[str] = mapped_column(ForeignKey("self_models.id"), index=True, unique=True)
    summary_text: Mapped[str] = mapped_column(Text, default="")
    message_count: Mapped[int] = mapped_column(default=0)
    last_focus: Mapped[str] = mapped_column(Text, default="")
    counterpart_name: Mapped[str] = mapped_column(String(128), default="")
    relationship_type: Mapped[str] = mapped_column(String(64), default="")
    identity_status: Mapped[str] = mapped_column(String(32), default="unanchored")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )