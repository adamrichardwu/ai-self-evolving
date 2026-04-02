from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from packages.infra.db.session import Base


class SelfModelRecord(Base):
    __tablename__ = "self_models"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    agent_id: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    chosen_name: Mapped[str] = mapped_column(String(128))
    status: Mapped[str] = mapped_column(String(32), default="active")
    current_version: Mapped[int] = mapped_column(Integer, default=1)
    identity_json: Mapped[dict] = mapped_column(JSON)
    capability_json: Mapped[dict] = mapped_column(JSON)
    goals_json: Mapped[dict] = mapped_column(JSON)
    values_json: Mapped[dict] = mapped_column(JSON)
    affect_json: Mapped[dict] = mapped_column(JSON)
    attention_json: Mapped[dict] = mapped_column(JSON)
    metacognition_json: Mapped[dict] = mapped_column(JSON)
    social_json: Mapped[dict] = mapped_column(JSON)
    autobiography_json: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    snapshots: Mapped[list["SelfModelSnapshotRecord"]] = relationship(
        back_populates="self_model", cascade="all, delete-orphan"
    )


class SelfModelSnapshotRecord(Base):
    __tablename__ = "self_model_snapshots"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    self_model_id: Mapped[str] = mapped_column(ForeignKey("self_models.id"), index=True)
    version: Mapped[int] = mapped_column(Integer, index=True)
    snapshot_json: Mapped[dict] = mapped_column(JSON)
    update_reason: Mapped[str] = mapped_column(Text, default="manual_update")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


    self_model: Mapped[SelfModelRecord] = relationship(back_populates="snapshots")