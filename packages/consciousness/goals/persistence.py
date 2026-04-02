from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import DateTime, Float, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from packages.infra.db.session import Base


class GoalRecord(Base):
    __tablename__ = "goals"
    __table_args__ = (UniqueConstraint("self_model_id", "origin_key"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    self_model_id: Mapped[str] = mapped_column(ForeignKey("self_models.id"), index=True)
    origin_key: Mapped[str] = mapped_column(String(160), index=True)
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text, default="")
    goal_type: Mapped[str] = mapped_column(String(64), default="active_task")
    priority: Mapped[float] = mapped_column(Float, default=0.5)
    status: Mapped[str] = mapped_column(String(32), default="active")
    time_horizon: Mapped[str] = mapped_column(String(32), default="short")
    origin: Mapped[str] = mapped_column(String(64), default="runtime")
    success_criteria: Mapped[str] = mapped_column(Text, default="")
    progress_score: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    last_evaluated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


class GoalCheckpointRecord(Base):
    __tablename__ = "goal_checkpoints"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    goal_id: Mapped[str] = mapped_column(ForeignKey("goals.id"), index=True)
    event_type: Mapped[str] = mapped_column(String(64), default="progress_update")
    summary: Mapped[str] = mapped_column(Text, default="")
    score_delta: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )