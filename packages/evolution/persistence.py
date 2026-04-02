from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from packages.infra.db.session import Base


class EvolutionRunRecord(Base):
    __tablename__ = "evolution_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    self_model_id: Mapped[str] = mapped_column(ForeignKey("self_models.id"), index=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    objective: Mapped[str] = mapped_column(Text, default="improve self-consistency and adaptive behavior")
    strategy_status: Mapped[str] = mapped_column(String(32), default="draft")
    promoted: Mapped[bool] = mapped_column(Boolean, default=False)
    rollback_required: Mapped[bool] = mapped_column(Boolean, default=False)
    baseline_overall_score: Mapped[float] = mapped_column(Float, default=0.0)
    candidate_overall_score: Mapped[float] = mapped_column(Float, default=0.0)
    score_delta: Mapped[float] = mapped_column(Float, default=0.0)
    baseline_benchmark_score: Mapped[float] = mapped_column(Float, default=0.0)
    benchmark_score: Mapped[float] = mapped_column(Float, default=0.0)
    utility_score: Mapped[float] = mapped_column(Float, default=0.0)
    verdict: Mapped[str] = mapped_column(String(32), default="needs_review")
    hypothesis_title: Mapped[str] = mapped_column(String(255), default="")
    hypothesis_description: Mapped[str] = mapped_column(Text, default="")
    variant_id: Mapped[str] = mapped_column(String(36), default="")
    active_policy_json: Mapped[dict] = mapped_column(JSON, default=dict)
    mutations_json: Mapped[list] = mapped_column(JSON, default=list)
    benchmark_results_json: Mapped[list] = mapped_column(JSON, default=list)
    evaluator_notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )