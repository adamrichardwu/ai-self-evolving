from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import DateTime, Float, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from packages.infra.db.session import Base


class SocialRelationshipRecord(Base):
    __tablename__ = "social_relationships"
    __table_args__ = (UniqueConstraint("self_model_id", "counterpart_id"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    self_model_id: Mapped[str] = mapped_column(ForeignKey("self_models.id"), index=True)
    counterpart_id: Mapped[str] = mapped_column(String(128), index=True)
    counterpart_name: Mapped[str] = mapped_column(String(128), default="")
    relationship_type: Mapped[str] = mapped_column(String(64), default="user")
    trust_score: Mapped[float] = mapped_column(Float, default=0.5)
    familiarity_score: Mapped[float] = mapped_column(Float, default=0.1)
    interaction_count: Mapped[int] = mapped_column(Integer, default=0)
    last_interaction_summary: Mapped[str] = mapped_column(Text, default="")
    role_in_context: Mapped[str] = mapped_column(String(64), default="")
    social_obligations_json: Mapped[list[str]] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    last_interaction_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )