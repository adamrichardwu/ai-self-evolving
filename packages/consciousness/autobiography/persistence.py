from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from packages.infra.db.session import Base


class AutobiographicalEventRecord(Base):
    __tablename__ = "autobiographical_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    self_model_id: Mapped[str] = mapped_column(ForeignKey("self_models.id"), index=True)
    event_type: Mapped[str] = mapped_column(String(64), index=True)
    focus: Mapped[str] = mapped_column(Text)
    summary: Mapped[str] = mapped_column(Text)
    emotional_tone: Mapped[str] = mapped_column(String(32), default="neutral")
    salience: Mapped[str] = mapped_column(String(32), default="medium")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
