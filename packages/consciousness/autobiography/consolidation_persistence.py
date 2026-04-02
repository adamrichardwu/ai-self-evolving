from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from packages.infra.db.session import Base


class AutobiographicalConsolidationRecord(Base):
    __tablename__ = "autobiographical_consolidations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    self_model_id: Mapped[str] = mapped_column(ForeignKey("self_models.id"), index=True)
    event_count: Mapped[int] = mapped_column(Integer)
    summary: Mapped[str] = mapped_column(Text)
    narrative_delta: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
