from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import DateTime, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from packages.infra.db.session import Base


class ConsciousnessEvaluationRecord(Base):
    __tablename__ = "consciousness_evaluations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    self_model_id: Mapped[str] = mapped_column(ForeignKey("self_models.id"), index=True)
    evaluation_type: Mapped[str] = mapped_column(String(64), default="baseline")
    self_consistency: Mapped[float] = mapped_column(Float)
    identity_continuity: Mapped[float] = mapped_column(Float)
    metacognitive_accuracy: Mapped[float] = mapped_column(Float)
    motivational_stability: Mapped[float] = mapped_column(Float)
    social_modeling: Mapped[float] = mapped_column(Float)
    reflective_recovery: Mapped[float] = mapped_column(Float)
    overall_score: Mapped[float] = mapped_column(Float)
    evaluator_notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )