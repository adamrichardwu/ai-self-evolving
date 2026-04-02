from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import DateTime, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from packages.infra.db.session import Base


class RuntimeTraceRecord(Base):
    __tablename__ = "runtime_traces"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    self_model_id: Mapped[str] = mapped_column(ForeignKey("self_models.id"), index=True)
    action_taken: Mapped[str] = mapped_column(String(64), default="background_thought")
    current_focus: Mapped[str] = mapped_column(Text, default="")
    dominant_goal: Mapped[str] = mapped_column(Text, default="")
    identity_status: Mapped[str] = mapped_column(String(32), default="unanchored")
    counterpart_name: Mapped[str] = mapped_column(String(128), default="")
    relationship_type: Mapped[str] = mapped_column(String(64), default="")
    summary_text: Mapped[str] = mapped_column(Text, default="")
    assistant_text: Mapped[str] = mapped_column(Text, default="")
    thought_focus: Mapped[str] = mapped_column(Text, default="")
    cycle_confidence: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )